# Amor ESP32 Firmware

PPG sensor firmware for the Amor heartbeat installation. Samples a PPG (photoplethysmography) sensor at 50Hz and transmits bundles of 5 samples via WiFi/OSC to the sensor processor.

## Quick Start

### 1. Configure WiFi and Server Settings

Copy the configuration template and edit with your settings:

```bash
cp include/config.h.example include/config.h
```

Edit `include/config.h`:
- Set `WIFI_SSID` and `WIFI_PASSWORD`
- Set `SERVER_IP` (IP of sensor processor machine)
- Set `PPG_ID` (0, 1, 2, or 3 - unique per unit)
- Set `PPG_GPIO` (32 for ESP32-WROOM, 4 for ESP32-S3)

**Note:** Firmware tested on ESP32-WROOM. ESP32-S3 support is present but requires environment-specific testing before production deployment.

Example:
```cpp
#define WIFI_SSID "MyNetwork"
#define WIFI_PASSWORD "MyPassword"
#define SERVER_IP "192.168.1.100"
#define SERVER_PORT 8000
#define PPG_ID 0
#define PPG_GPIO 32           // For ESP32-WROOM
```

### 2. Build and Upload

Install PlatformIO if not already installed:

```bash
pip install platformio
```

Build for ESP32:

```bash
cd /home/user/corazonn/firmware/amor
pio run -e esp32dev
```

Upload to connected ESP32:

```bash
pio run -e esp32dev -t upload
```

Monitor serial output (debug information):

```bash
pio device monitor
```

#### Serial Statistics

The firmware prints statistics to serial output every 5 seconds:

```
[12.3s] PPG_ID=0 | WiFi: OK (192.168.1.42, -65dBm) | Sent: 123 bundles (615 samples) | ADC: 2048±156 (1892-2204) | Rate: 10.0 msg/s
```

**Statistics breakdown:**
- `[12.3s]`: Uptime in seconds
- `PPG_ID`: Unit identifier (0-3)
- `WiFi`: Status (OK or DOWN), IP address, signal strength (RSSI in dBm)
- `Sent`: Total bundles and samples transmitted since boot
- `ADC`: Mean ± standard deviation (min-max range) of sampled ADC values. Standard deviation indicates signal quality: higher stddev suggests stronger PPG signal with better contrast between pulse peaks and troughs
- `Rate`: Message transmission rate (messages per second)

### 3. Verify with Test Script

Run the OSC receiver to verify the firmware sends packets:

```bash
cd /home/user/corazonn
python3 testing/osc_receiver.py
```

This listens on port 8000 and displays incoming OSC messages with timestamps and sample values.

## Hardware Setup

### Wiring

- **PPG Sensor Signal** → GPIO pin (GPIO 32 for WROOM, GPIO 4 for S3)
- **PPG Sensor GND** → ESP32 GND
- **PPG Sensor 5V** → ESP32 5V

### LED Feedback

- **Status LED** on GPIO 2 (configurable via `LED_PIN` in config.h)
  - Blinking: WiFi connecting or disconnected
  - Solid: WiFi connected and sampling

## Behavior

**Sampling:**
- Reads PPG sensor at 50Hz (every 20ms)
- Buffers 5 samples (100ms duration)
- Sends OSC bundle every 100ms

**OSC Output:**
```
Route: /ppg/{ppg_id}
Args: [sample1, sample2, sample3, sample4, sample5, timestamp_ms]
Destination: {SERVER_IP}:{SERVER_PORT}
```

**WiFi Resilience:**
- Continues sampling even when WiFi is down
- Automatically reconnects every 5 seconds
- Drops samples during WiFi outage (no buffering)

## Admin Commands

The firmware listens for OSC admin commands on port 8006 (configurable via `ADMIN_PORT`).

**Remote Restart:**
```bash
# Send restart command to specific ESP32 unit
oscsend <ESP32_IP> 8006 /restart
```

Example:
```bash
# Restart unit at 192.168.1.42
oscsend 192.168.1.42 8006 /restart
```

The restart command is checked every 5 seconds (low overhead). When received, the ESP32 logs the restart request and reboots immediately using `ESP.restart()`.

## Configuration Details

See `include/config.h.example` for all available configuration options:

**Core settings:**
- `SAMPLE_RATE_HZ`: 50 (reference value)
- `SAMPLE_INTERVAL_MS`: 20ms (1000/SAMPLE_RATE_HZ - **must be manually updated** if rate changes)
- `BUNDLE_SIZE`: 5 samples
- `BUNDLE_INTERVAL_MS`: 100ms (BUNDLE_SIZE × SAMPLE_INTERVAL_MS - **must be manually updated**)
- ADC resolution: 12-bit (0-4095)
- WiFi reconnect interval: 5 seconds

**Important:** If you change `SAMPLE_RATE_HZ`, you must manually recalculate and update `SAMPLE_INTERVAL_MS` and `BUNDLE_INTERVAL_MS` to match.

## Troubleshooting

**No OSC messages received:**
- Check WiFi connection (LED should be solid)
- Verify SERVER_IP and SERVER_PORT in config.h
- Check sensor processor is listening on port 8000
- Monitor serial output for debug messages

**Poor signal quality:**
- Ensure good finger contact with PPG sensor
- Check for ambient light interference
- Reduce movement artifacts

**Build fails:**
- Confirm `config.h` exists (copy from `config.h.example`)
- Verify PlatformIO is installed: `pio --version`
- Check for typos in config.h

## References

- Technical Reference: `/home/user/corazonn/docs/firmware/amor-technical-reference.md`
- Sensor Processor: `amor/processor.py`
