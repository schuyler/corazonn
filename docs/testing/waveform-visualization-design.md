# Real-Time Pulse Waveform Visualization - Design

## Overview

Enables real-time visualization of actual PulseSensor waveform data with EKG-style plotting. This requires creating a new firmware build that combines WiFi/OSC capabilities with sensor reading and adds high-frequency waveform sampling.

**Key Components:**
- New firmware build: Merges WiFi/OSC + sensor reading + waveform sampling
- Visualization: Python tool to receive and plot waveform data in real-time
- Protocol: New `/waveform/{id}` OSC message format for batched samples

## Current State

**Existing Firmware Builds:**

1. **`firmware/heartbeat_phase1/`** - WiFi + OSC infrastructure
   - Connects to WiFi, sends OSC messages
   - Generates FAKE IBI test data (800-999ms sequence)
   - No actual sensor reading
   - Sends to `/heartbeat/{sensor_id}` at 1 Hz

2. **`firmware/esp32_test/`** - PulseSensor reading
   - Reads ADC from GPIO 12 (PulseSensor)
   - Simple threshold-based beat detection
   - Samples at 50 Hz
   - NO WiFi (uses Serial only)
   - Note: GPIO 12 is ADC2, incompatible with WiFi

**This Design Proposes:**

3. **`firmware/ekg_waveform/`** (NEW) - Combined functionality
   - WiFi + OSC (from heartbeat_phase1)
   - PulseSensor ADC reading (from esp32_test, moved to ADC1 pin)
   - Real beat detection and IBI calculation
   - NEW: 200 Hz waveform sampling with batched transmission
   - Sends both `/heartbeat/{id}` (real IBI) and `/waveform/{id}` (samples)

## Prerequisites

**Hardware:**
- ESP32 development board
- PulseSensor connected to ADC1 pin (GPIO 34-39, not GPIO 12)
- WiFi network access

**Software:**
- Existing WiFi/OSC code from `heartbeat_phase1`
- Beat detection logic from `esp32_test` (adapted for ADC1)
- New waveform batching and transmission code

## Requirements

### Functional Requirements

**FR1: ADC Sampling**
- Sample PulseSensor analog output at 200 Hz (5ms intervals)
- Read from ADC1 pin (GPIO 34-39 for WiFi compatibility)
- Run IBI detection in parallel with waveform sampling

**FR2: Data Batching**
- Buffer 40 samples (200ms worth of data)
- Transmit batch every 200ms via OSC
- Include timestamp for synchronization

**FR3: OSC Transmission**
- New address pattern: `/waveform/{sensor_id}` for waveform batches
- Payload: timestamp (int32) + 40 sample values (blob of int16)
- Implement `/heartbeat/{sensor_id}` with REAL IBI values (on beat detection)

**FR4: Visualization**
- Real-time scrolling waveform plot
- Display last 10 seconds of data (2000 samples)
- Auto-scaling Y-axis based on ADC range
- Single sensor view (CLI selectable)

### Non-Functional Requirements

**NFR1: Network Efficiency**
- Maximum 5 messages/sec per sensor (200ms batching)
- Total bandwidth: ~550 bytes/sec per sensor (5 waveform msgs + 1 heartbeat msg)

**NFR2: Timing Accuracy**
- Sample timing jitter < 10% (0.5ms variance at 5ms intervals)
- Use hardware timer for consistent ADC reads

**NFR3: Compatibility**
- Use same `/heartbeat/{sensor_id}` protocol format (but with real data)
- Compatible with existing test receivers (e.g., `testing/osc_receiver.py`)
- Cross-platform visualization (macOS, Linux, Windows)

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────┐
│ ESP32 Firmware                                               │
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐ │
│  │ PulseSensor │───>│ ADC Sampler  │───>│ Sample Buffer  │ │
│  │  (Analog)   │    │  (200 Hz)    │    │  (40 samples)  │ │
│  └─────────────┘    └──────────────┘    └────────┬───────┘ │
│                                                   │         │
│                     ┌──────────────┐              │         │
│                     │ IBI Detector │<─────────────┘         │
│                     │  (existing)  │                        │
│                     └──────┬───────┘                        │
│                            │                                │
│  ┌─────────────────────────┴──────────┐                     │
│  │        OSC Transmitter             │                     │
│  │  /heartbeat/{id}  /waveform/{id}   │                     │
│  └──────────────┬─────────────────────┘                     │
└─────────────────┼───────────────────────────────────────────┘
                  │ UDP (WiFi)
                  v
┌──────────────────────────────────────────────────────────────┐
│ Waveform Viewer (Python)                                     │
│                                                              │
│  ┌──────────────────┐    ┌─────────────┐   ┌─────────────┐ │
│  │ OSC Receiver     │───>│ Data Buffer │──>│  matplotlib │ │
│  │ (ThreadingOSC)   │    │ (10s ring)  │   │  Animation  │ │
│  └──────────────────┘    └─────────────┘   └─────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Firmware Changes

### ADC Sampling (200 Hz)

**Hardware Timer Setup:**
```cpp
#include <driver/adc.h>

// Use hardware timer for precise 200 Hz sampling
hw_timer_t* adc_timer = NULL;
const int SAMPLE_RATE_HZ = 200;
const int TIMER_INTERVAL_US = 1000000 / SAMPLE_RATE_HZ;  // 5000 us
const int PULSE_SENSOR_PIN = 34;  // GPIO 34 = ADC1_CHANNEL_6

// Interrupt handler (ISR-safe)
void IRAM_ATTR onTimer() {
    // Use ISR-safe ADC read (NOT analogRead which uses mutex locks)
    int adc_value = adc1_get_raw(ADC1_CHANNEL_6);  // GPIO 34
    xRingbufferSendFromISR(waveform_ringbuf, &adc_value, sizeof(int16_t), NULL);
}
```

**ADC Configuration (in setup()):**
```cpp
#include <driver/adc.h>

void setup() {
    // Configure ADC1 for ISR-safe reading
    adc1_config_width(ADC_WIDTH_BIT_12);  // 12-bit resolution (0-4095)
    adc1_config_channel_atten(ADC1_CHANNEL_6, ADC_ATTEN_DB_11);  // 0-3.3V range

    // ... rest of setup
}
```

**GPIO Pin Mapping (ADC1 channels - WiFi compatible):**

| GPIO | ADC1 Channel | Notes |
|------|-------------|-------|
| 36 | ADC1_CHANNEL_0 | Input only, no pull-up/down |
| 37 | ADC1_CHANNEL_1 | Input only, no pull-up/down |
| 38 | ADC1_CHANNEL_2 | Input only, no pull-up/down |
| 39 | ADC1_CHANNEL_3 | Input only, no pull-up/down |
| 32 | ADC1_CHANNEL_4 | Can be output |
| 33 | ADC1_CHANNEL_5 | Can be output |
| **34** | **ADC1_CHANNEL_6** | **RECOMMENDED** - Input only |
| 35 | ADC1_CHANNEL_7 | Input only, no pull-up/down |

**Configuration Details:**
- **Recommended pin:** GPIO 34 (ADC1_CHANNEL_6)
- **ADC resolution:** 12-bit (0-4095)
- **ADC attenuation:** 11dB (0-3.3V input range, matches PulseSensor output)
- **Timer:** ESP32 `hw_timer_t` for consistent 5ms intervals
- **ISR-safe buffer:** ESP-IDF ring buffer (`xRingbufferCreate`, `xRingbufferSendFromISR`)

### Sample Buffer

**Structure:**
```cpp
struct WaveformBatch {
    uint32_t timestamp_ms;      // millis() when batch started
    int16_t samples[40];        // 40 ADC readings (12-bit ADC, max 4095)
    uint8_t count;              // Number of valid samples (normally 40)
};
```

**ESP-IDF Ring Buffer Implementation:**

```cpp
#include "freertos/ringbuf.h"

// Global ring buffer handle
RingbufHandle_t waveform_ringbuf;

void setup() {
    // Create ring buffer: 100 samples * 2 bytes = 200 bytes
    // Allows buffer overflow during WiFi delays
    waveform_ringbuf = xRingbufferCreate(200, RINGBUF_TYPE_NOSPLIT);
    if (waveform_ringbuf == NULL) {
        Serial.println("Failed to create ring buffer");
        while(1);  // Halt on error
    }

    // ... configure ADC, timer, etc.
}
```

**Batching Logic:**

Main loop reads samples from ring buffer and batches them:

```cpp
void loop() {
    static WaveformBatch batch;
    static size_t batch_index = 0;

    // Check if sample available in ring buffer
    size_t item_size;
    int16_t* sample = (int16_t*)xRingbufferReceive(waveform_ringbuf, &item_size, 0);

    if (sample != NULL) {
        // Add sample to batch
        batch.samples[batch_index++] = *sample;

        // Return buffer item to ring buffer
        vRingbufferReturnItem(waveform_ringbuf, (void*)sample);

        // Check if batch is full (40 samples accumulated)
        if (batch_index >= 40) {
            batch.timestamp_ms = millis();  // Record timestamp
            batch.count = batch_index;

            // Send OSC message
            sendWaveformOSC(batch);

            // Reset for next batch
            batch_index = 0;
        }
    }

    // Also check for beat detection, WiFi, etc.
    // ...
}
```

**Key Points:**
- **ISR-safe:** `xRingbufferSendFromISR()` in timer interrupt, `xRingbufferReceive()` in main loop
- **No mutex needed:** ESP-IDF ring buffer handles synchronization
- **Overflow handling:** If ring buffer fills (WiFi delay), oldest samples dropped automatically
- **Non-blocking:** Main loop receives with 0 timeout, continues immediately if no data

### OSC Message Format

**Waveform Message:**
```
Address: /waveform/{sensor_id}
Arguments:
  [0]: timestamp (int32) - millis() at batch start
  [1]: samples (blob) - 40 × int16_t (80 bytes)
```

**Why blob instead of array:**
- More efficient encoding (80 bytes vs ~400 bytes for OSC array)
- Easier to parse on receiver side
- Standard OSC type

**Transmission:**
```cpp
void sendWaveformOSC(const WaveformBatch& batch) {
    char address[24];
    snprintf(address, sizeof(address), "/waveform/%d", SENSOR_ID);

    OSCMessage msg(address);
    msg.add((int32_t)batch.timestamp_ms);

    // Samples sent as blob in little-endian format (ESP32 native byte order)
    // Receiver must unpack with matching endianness: struct.unpack('<40h', blob)
    msg.add((uint8_t*)batch.samples, sizeof(batch.samples));  // 80 bytes

    udp.beginPacket(SERVER_IP, SERVER_PORT);
    msg.send(udp);
    udp.endPacket();
    msg.empty();
}
```

### IBI Detection Implementation

**Approach:** Adapt threshold-based detection from `esp32_test`

**Current esp32_test implementation:**
- Threshold-based rising edge detection (GPIO 12, 50 Hz sampling)
- Refractory period to prevent double-counting (300ms minimum)
- Tracks time between beats for IBI calculation

**New implementation for ekg_waveform:**
- Use the 200 Hz waveform samples for beat detection
- Apply same threshold logic (adjust threshold value as needed)
- Calculate IBI from time between detected peaks
- Send `/heartbeat/{id}` message when beat detected
- **Single ADC path** - efficient, no redundant sampling

**Integrated Data Flow:**

Beat detection runs in main loop, processing same samples used for batching:

```cpp
void loop() {
    static WaveformBatch batch;
    static size_t batch_index = 0;

    // Beat detection state
    static bool lastAboveThreshold = false;
    static unsigned long lastBeatTime = 0;
    const int THRESHOLD = 2200;  // Tune based on sensor/attenuation
    const int REFRACTORY_MS = 300;  // Min 300ms between beats

    // Read sample from ring buffer (non-blocking)
    size_t item_size;
    int16_t* sample_ptr = (int16_t*)xRingbufferReceive(waveform_ringbuf, &item_size, 0);

    if (sample_ptr != NULL) {
        int16_t sample = *sample_ptr;

        // 1. BEAT DETECTION: Process sample for peak detection
        if (sample > THRESHOLD && !lastAboveThreshold) {
            unsigned long now = millis();
            if (now - lastBeatTime > REFRACTORY_MS) {
                int ibi = now - lastBeatTime;
                sendHeartbeatOSC(ibi);  // Send real IBI to /heartbeat/{id}
                lastBeatTime = now;
            }
        }
        lastAboveThreshold = (sample > THRESHOLD);

        // 2. BATCHING: Add same sample to waveform batch
        batch.samples[batch_index++] = sample;

        // Return buffer item
        vRingbufferReturnItem(waveform_ringbuf, (void*)sample_ptr);

        // 3. TRANSMISSION: Send batch when 40 samples collected
        if (batch_index >= 40) {
            batch.timestamp_ms = millis();
            batch.count = batch_index;
            sendWaveformOSC(batch);  // Send waveform to /waveform/{id}
            batch_index = 0;
        }
    }

    // Also check WiFi status, LED updates, etc.
}
```

**Key Design Points:**
- **Single read path:** Each sample read once from ring buffer
- **Dual purpose:** Same sample used for beat detection AND waveform transmission
- **Non-destructive:** Beat detection doesn't consume samples (batching handles that)
- **Independent rates:** Beats send when detected (variable), waveform sends every 200ms (fixed)

**Future Enhancement:**
- More sophisticated peak detection (slope analysis, adaptive threshold)
- Filter out motion artifacts
- Heart rate variability metrics

## Visualization Tool

### Component: WaveformViewer

**Responsibilities:**
1. Receive OSC waveform batches
2. Reconstruct continuous timeline from batched samples
3. Plot scrolling waveform in real-time
4. Auto-scale to ADC range

### Data Buffer

**Structure:**
```python
from collections import deque

class WaveformBuffer:
    def __init__(self, window_seconds=10, sample_rate=200):
        self.max_samples = window_seconds * sample_rate  # 2000 samples
        self.timestamps = deque(maxlen=self.max_samples)
        self.values = deque(maxlen=self.max_samples)
        self.lock = threading.Lock()

    def add_batch(self, base_timestamp, samples):
        """Add 40 samples with calculated timestamps."""
        with self.lock:
            for i, value in enumerate(samples):
                # Calculate timestamp for this sample
                # base_timestamp is in ms, each sample is 5ms apart
                t = base_timestamp + (i * 5)
                self.timestamps.append(t)
                self.values.append(value)
```

### OSC Handler

**Using ThreadingOSCUDPServer:**

> **Note:** The NEW `waveform_viewer.py` tool uses `ThreadingOSCUDPServer` to allow concurrent OSC message reception while matplotlib runs its animation loop. This is different from the existing `testing/osc_receiver.py` which uses `BlockingOSCUDPServer` (single-threaded). The existing receiver remains unchanged and compatible.

```python
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher

def handle_waveform(address, timestamp, blob):
    """Handle incoming waveform batch."""
    # Parse blob as 40 × int16
    samples = struct.unpack('<40h', blob)  # Little-endian 16-bit ints

    # Validate sensor ID from address
    match = re.match(r'/waveform/(\d)', address)
    if match and int(match.group(1)) == target_sensor_id:
        buffer.add_batch(timestamp, samples)
```

### Plotting with matplotlib

**Animation setup:**
```python
import matplotlib.pyplot as plt
import matplotlib.animation as animation

fig, ax = plt.subplots()
line, = ax.plot([], [], lw=2)

def init():
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('ADC Value')
    ax.set_title(f'Pulse Waveform - Sensor {sensor_id}')
    return line,

def update(frame):
    with buffer.lock:
        if len(buffer.timestamps) > 0:
            # Convert timestamps to relative seconds
            t0 = buffer.timestamps[0]
            times = [(t - t0) / 1000.0 for t in buffer.timestamps]
            values = list(buffer.values)

            line.set_data(times, values)

            # Auto-scale axes
            if times:
                ax.set_xlim(0, max(times))
                ax.set_ylim(min(values) - 100, max(values) + 100)

    return line,

ani = animation.FuncAnimation(fig, update, init_func=init,
                             interval=33, blit=True)  # 30 FPS
plt.show()
```

### CLI Interface

```bash
python waveform_viewer.py --sensor-id 0 --port 8000 --window 10
```

**Arguments:**
- `--sensor-id` (required): 0-3, which sensor to display
- `--port` (default: 8000): OSC listen port
- `--window` (default: 10): Seconds of history to display

## Data Flow

### Normal Operation

1. **ESP32 Timer Interrupt (every 5ms)**
   - Read ADC value from PulseSensor pin
   - Add to ring buffer (ISR-safe)

2. **ESP32 Main Loop**
   - Check if 40 samples accumulated (200ms elapsed)
   - If yes:
     - Copy samples to WaveformBatch
     - Record timestamp
     - Send via OSC
     - Reset counter

3. **Network Transmission**
   - UDP packet: ~100 bytes (OSC overhead + 80 byte blob)
   - Arrives at viewer within 1-10ms on local network

4. **Viewer OSC Thread**
   - Receive batch
   - Parse timestamp and blob
   - Acquire lock, append 40 samples to deque
   - Release lock

5. **Viewer Animation Thread (30 FPS)**
   - Every 33ms, acquire lock
   - Copy buffer data
   - Release lock
   - Update plot line data
   - matplotlib redraws

### Timing Considerations

**Sample timeline:**
```
ESP32 time:   0ms    5ms   10ms   15ms  ... 195ms  200ms
Samples:      [0]    [1]   [2]    [3]  ...  [39]   send
                                                   [0]
```

**Viewer reconstruction:**
- Batch arrives with `timestamp=T`
- Sample 0 was taken at time T
- Sample 1 was taken at time T+5
- Sample 39 was taken at time T+195

**Latency budget:**
- Sampling to batch send: 200ms (batching delay)
- Network transmission: 1-10ms
- Plot update: 0-33ms (animation frame)
- **Total: ~200-250ms** end-to-end latency

## Implementation Notes

### Memory Usage (ESP32)

**Sample buffer:**
- Ring buffer: 100 samples × 2 bytes = 200 bytes (ESP-IDF ring buffer allocation)
- WaveformBatch struct: 40 samples × 2 bytes (int16_t) + 4 bytes (timestamp) + 1 byte (count) = 85 bytes (~88 with padding)
- Total: ~300 bytes additional RAM

**Still well within ESP32 limits** (320 KB SRAM)

### Network Bandwidth

**Per sensor:**
- 5 packets/sec × ~100 bytes/packet = 500 bytes/sec
- Plus existing heartbeat: 1 pkt/sec × 50 bytes = 50 bytes/sec
- **Total: ~550 bytes/sec = 4.4 Kbps**

**For 4 sensors:** ~18 Kbps (negligible on WiFi)

### Error Handling

**Firmware:**
- If WiFi disconnects, samples accumulate in buffer
- When buffer full, drop oldest samples (ring behavior)
- On reconnect, transmission resumes with current data
- No attempt to recover lost samples (real-time system)

**Viewer:**
- Missing packets create gaps in waveform
- Display continues (deque handles gaps gracefully)
- No error indication unless gap exceeds threshold (>1 second)

### Testing Strategy

**Unit Tests:**
- Blob packing/unpacking (struct format correct)
- Timestamp calculation (5ms intervals accurate)
- Buffer overflow behavior (ring eviction works)

**Integration Tests:**
- Use simulator to send known waveform (sine wave)
- Verify received samples match transmitted
- Check timing accuracy (measure timestamp deltas)

**Hardware Tests:**
- Connect PulseSensor, verify realistic waveform shape
- Check for ADC noise/artifacts
- Validate 200 Hz timing with oscilloscope or logic analyzer

## Implementation Path

**Phase 1: Create new firmware build (`firmware/ekg_waveform/`)**
1. Copy platformio.ini and WiFi/OSC code from `heartbeat_phase1`
2. Port ADC reading and beat detection from `esp32_test` (change pin to GPIO 34)
3. Add hardware timer for 200 Hz sampling
4. Implement sample batching (ring buffer + WaveformBatch struct)
5. Add waveform OSC transmission (`/waveform/{id}`)
6. Connect beat detection to send real IBI via `/heartbeat/{id}`
7. Test compilation

**Phase 2: Visualization development**
1. Create `testing/waveform_viewer.py` skeleton
2. Implement OSC reception using ThreadingOSCUDPServer
3. Add blob parsing and buffer management
4. Implement matplotlib scrolling plot
5. Add CLI arguments (sensor-id, port, window)
6. Test with simulated OSC data

**Phase 3: Hardware integration**
1. Flash ekg_waveform firmware to ESP32
2. Connect PulseSensor to GPIO 34
3. Verify waveform data arrives and plots correctly
4. Tune threshold and sample rate if needed
5. Validate IBI detection accuracy
6. Performance test (check timing jitter, network reliability)

**Phase 4: Enhancements (optional)**
1. Add filtering to waveform display (bandpass, baseline correction)
2. Overlay detected beats on waveform plot
3. Display calculated BPM alongside waveform
4. Export functionality (CSV, screenshots)
5. Multi-sensor split-pane view

## Future Enhancements

**Visualization:**
- Multi-sensor split-pane view
- Overlay IBI markers on waveform
- BPM calculation from peaks
- Export to CSV or video

**Signal Processing:**
- Real-time filtering (bandpass 0.5-15 Hz)
- Baseline wander correction
- R-peak detection visualization
- Heart rate variability metrics

**Firmware:**
- Adaptive sample rate based on heart rate
- Compression (delta encoding)
- Local storage during WiFi outages

## References

- PulseSensor Playground: https://github.com/WorldFamousElectronics/PulseSensor_Playground
- OSC specification: http://opensoundcontrol.org/spec-1_0
- ESP32 ADC docs: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/adc.html
- matplotlib animation: https://matplotlib.org/stable/api/animation_api.html
- Existing OSC protocol: `docs/firmware/guides/phase1-04-osc-messaging.md`
