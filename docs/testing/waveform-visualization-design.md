# Real-Time Pulse Waveform Visualization - Design

## Overview

Extends the Phase 1 heartbeat system to transmit and visualize the actual pulse waveform from PulseSensor ADC readings, not just inter-beat intervals. Enables real-time EKG-style visualization of cardiac pulse shape.

**Key Changes:**
- Firmware: Add 200 Hz ADC sampling with batched OSC transmission
- Visualization: New Python tool to receive and plot waveform data
- Protocol: New OSC message format for waveform batches

## Requirements

### Functional Requirements

**FR1: ADC Sampling**
- Sample PulseSensor analog output at 200 Hz (5ms intervals)
- Read from analog pin (GPIO 34 or similar on ESP32)
- Maintain existing IBI detection in parallel

**FR2: Data Batching**
- Buffer 40 samples (200ms worth of data)
- Transmit batch every 200ms via OSC
- Include timestamp for synchronization

**FR3: OSC Transmission**
- New address pattern: `/waveform/{sensor_id}`
- Payload: timestamp (int32) + 40 sample values (int32 array or blob)
- Maintain existing `/heartbeat/{sensor_id}` messages (1 Hz IBI)

**FR4: Visualization**
- Real-time scrolling waveform plot
- Display last 10 seconds of data (2000 samples)
- Auto-scaling Y-axis based on ADC range
- Single sensor view (CLI selectable)

### Non-Functional Requirements

**NFR1: Network Efficiency**
- Maximum 5 messages/sec per sensor (200ms batching)
- Total bandwidth: ~800 bytes/sec per sensor at 200 Hz

**NFR2: Timing Accuracy**
- Sample timing jitter < 10% (0.5ms variance at 5ms intervals)
- Use hardware timer for consistent ADC reads

**NFR3: Compatibility**
- Preserve existing `/heartbeat/{sensor_id}` protocol
- Backward compatible with current receivers
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
// Use hardware timer for precise 200 Hz sampling
hw_timer_t* adc_timer = NULL;
const int SAMPLE_RATE_HZ = 200;
const int TIMER_INTERVAL_US = 1000000 / SAMPLE_RATE_HZ;  // 5000 us

// Interrupt handler
void IRAM_ATTR onTimer() {
    int adc_value = analogRead(PULSE_SENSOR_PIN);
    waveform_buffer.add(adc_value);
}
```

**Configuration:**
- GPIO pin: 34 (or user-configurable)
- ADC resolution: 12-bit (0-4095)
- Timer: Use `hw_timer_t` for consistent intervals
- ISR-safe buffer: Ring buffer with atomic operations

### Sample Buffer

**Structure:**
```cpp
struct WaveformBatch {
    uint32_t timestamp_ms;      // millis() when batch started
    int16_t samples[40];        // 40 ADC readings (12-bit ADC, max 4095)
    uint8_t count;              // Number of valid samples (normally 40)
};
```

**Batching Logic:**
- ISR adds samples to ring buffer
- Main loop checks if 40 samples accumulated
- When full, copy to WaveformBatch and send
- Continue sampling during transmission

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
    msg.add((uint8_t*)batch.samples, sizeof(batch.samples));

    udp.beginPacket(SERVER_IP, SERVER_PORT);
    msg.send(udp);
    udp.endPacket();
    msg.empty();
}
```

### IBI Detection Integration

**Existing IBI code continues to run:**
- PulseSensor library has its own beat detection
- Reads same analog pin at its own rate (~500 Hz internally)
- Sends `/heartbeat/{id}` messages when beat detected
- **No changes needed** - runs in parallel

**Alternative:** Use waveform samples for IBI detection
- Process the 200 Hz samples for peak detection
- More efficient (one ADC path instead of two)
- Phase 2 enhancement

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
- Ring buffer: 50 samples × 2 bytes = 100 bytes (allows some overflow)
- WaveformBatch: 40 samples × 4 bytes + overhead = ~200 bytes
- Total: <500 bytes additional RAM

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

## Migration Path

**Phase 1: Firmware development**
1. Add ADC sampling code (timer + ISR)
2. Implement batching logic
3. Add waveform OSC transmission
4. Test with simulator

**Phase 2: Visualization development**
1. Create waveform_viewer.py skeleton
2. Implement OSC reception and parsing
3. Add matplotlib plotting
4. Test with simulated data

**Phase 3: Integration**
1. Test with real hardware
2. Tune sample rate if needed
3. Validate timing accuracy
4. Performance testing with 4 sensors

**Phase 4: Optimization (optional)**
1. Use waveform samples for IBI detection (eliminate dual-path)
2. Add filtering (high-pass to remove DC offset)
3. Compression for slower networks

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
