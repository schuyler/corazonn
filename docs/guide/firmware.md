# Firmware Configuration

Configuration file: `firmware/amor/include/config.h`

## Setup

Copy the example configuration:

```bash
cd firmware/amor
cp include/config.h.example include/config.h
```

**Note:** `config.h` is gitignored and must be created for each deployment.

## Required Configuration

### WiFi Settings

```c
#define WIFI_SSID "your_network_name"
#define WIFI_PASSWORD "your_password"
```

Network credentials for ESP32 connectivity.

### Server Settings

```c
#define SERVER_IP "192.168.1.100"     // Host running amor.audio/lighting
#define SERVER_PORT 8000               // PPG data port (PORT_PPG)
#define ADMIN_PORT 8006                // Admin command port (PORT_ESP32_ADMIN)
```

- `SERVER_IP` - IP address of computer running Amor sensor processor
- `SERVER_PORT` - OSC port for PPG data broadcast (default: 8000)
- `ADMIN_PORT` - OSC port for admin commands (default: 8006)

### Unit Identification

```c
#define PPG_ID 0                       // Unique ID: 0, 1, 2, or 3
```

Each ESP32 sensor must have a unique ID (0-3). This maps to:
- Zone assignments in lighting.yaml
- Sample banks in samples.yaml
- Pan positions (0=left, 1=center-left, 2=center-right, 3=right)

## GPIO Configuration

### Pin Selection

Choose ONE GPIO pin based on your ESP32 variant:

```c
// ESP32-WROOM (original ESP32)
#define PPG_GPIO 32                    // ADC1_CH4 (GPIO 32)

// ESP32-S3
// #define PPG_GPIO 4                  // ADC1_CH3 (GPIO 4)
```

**Pin Requirements:**
- Must be ADC1 channel (ADC2 conflicts with WiFi)
- 12-bit resolution (0-4095)
- Analog input capable

**Common ADC1 Pins:**
- ESP32-WROOM: GPIO 32, 33, 34, 35, 36, 39
- ESP32-S3: GPIO 1-10

## Timing Configuration

### Sample Rate

```c
#define SAMPLE_RATE_HZ 50              // Samples per second (fixed)
#define SAMPLE_INTERVAL_MS 20          // 1000 / SAMPLE_RATE_HZ
```

PPG sampling frequency. Fixed at 50Hz for all conditions. This provides sufficient temporal resolution for heartbeat detection.

### Bundle Settings

```c
#define BUNDLE_SIZE 5                  // Samples per OSC bundle
#define BUNDLE_INTERVAL_MS 100         // Bundle transmission interval
```

Controls OSC data transmission:
- `BUNDLE_SIZE` - Number of samples grouped per OSC message (5 samples)
- `BUNDLE_INTERVAL_MS` - Time between bundle transmissions (100ms)

**Relationship:** `BUNDLE_INTERVAL_MS = SAMPLE_INTERVAL_MS × BUNDLE_SIZE`

Note: When WiFi is connected, firmware transmits bundles every 100ms. Sampling continues regardless of WiFi status, but disconnected samples are not buffered. Signal quality filtering is handled by the processor (detector.py).

## Optional Features

### Status LED

```c
#define LED_PIN 2                      // Status LED GPIO

// Uncomment to enable LED feedback
// #define ENABLE_LED
```

Visual feedback for connection and data transmission status.

### OSC Admin Listener

```c
// Uncomment to enable admin commands
// #define ENABLE_OSC_ADMIN
```

Allows remote firmware control via OSC (experimental).

### Hardware Watchdog

```c
// Uncomment to enable watchdog timer
// #define ENABLE_WATCHDOG
```

Automatic reset on firmware hang (use with caution during development).

## Building and Flashing

### Prerequisites

Install PlatformIO:

```bash
pip install platformio
```

### Build

```bash
cd firmware/amor
pio run
```

### Flash

```bash
pio run --target upload
```

### Monitor Serial Output

```bash
pio device monitor
```

## Network Configuration

### Static IP Recommendation

For SERVER_IP, use a static IP or DHCP reservation to prevent connection loss on network changes.

### Firewall Requirements

Ensure firewall allows:
- Outbound UDP to `SERVER_IP:SERVER_PORT` (PPG data)
- Outbound UDP to `SERVER_IP:ADMIN_PORT` (admin commands, if enabled)

## Troubleshooting

### Connection Issues

Check serial monitor for:
- WiFi connection status
- Server reachability
- OSC transmission confirmations

### ADC Noise

If readings are noisy:
- Verify analog ground connection
- Add capacitor (0.1µF) across sensor input
- Check cable shielding
- Reduce `SAMPLE_RATE_HZ` if needed
