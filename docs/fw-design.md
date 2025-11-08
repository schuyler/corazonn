# Heartbeat Installation - ESP32 Firmware Design

## System Overview
ESP32 firmware samples 4 optical pulse sensors at 50Hz, detects heartbeats using adaptive threshold algorithm, calculates inter-beat intervals, and transmits timing data via OSC over WiFi to Linux audio server.

**Data Flow**: Analog sensors → ADC sampling → Moving average filter → Adaptive threshold detection → IBI calculation → OSC transmission

---

## Firmware Architecture

### Main Components
1. **Initialization**: WiFi setup, GPIO configuration, state initialization
2. **Sampling Loop**: 50Hz timer-driven ADC reads across all sensors
3. **Signal Processing**: Per-sensor moving average and baseline tracking
4. **Beat Detection**: Adaptive threshold crossing with refractory period
5. **OSC Transmission**: UDP packet construction and WiFi transmission
6. **Status Indication**: LED feedback for system state

### Execution Model
- **Main loop**: Non-blocking polling architecture
- **Timing**: `millis()` for beat intervals, loop delay for 50Hz cadence
- **Concurrency**: Single-threaded, no interrupts or RTOS tasks
- **Watchdog**: Hardware watchdog timer (8 second timeout)

---

## Configuration Constants

### Network Configuration
```cpp
const char* WIFI_SSID = "your-network-name";
const char* WIFI_PASSWORD = "your-password";
const IPAddress SERVER_IP(192, 168, 1, 100);  // Linux audio server
const int SERVER_PORT = 8000;                  // OSC receive port
const unsigned long WIFI_RETRY_INTERVAL_MS = 5000;  // Retry every 5 sec
```

### Hardware Configuration
```cpp
const int SENSOR_PINS[4] = {32, 33, 34, 35};  // GPIO for analog inputs
const int STATUS_LED_PIN = 2;                 // Built-in LED
const int ADC_RESOLUTION = 12;                // 12-bit (0-4095)
```

### Signal Processing Parameters
```cpp
const int SAMPLE_RATE_HZ = 50;                // Per sensor
const int SAMPLE_INTERVAL_MS = 20;            // 1000 / 50
const int MOVING_AVG_SAMPLES = 5;             // 100ms smoothing window
const float BASELINE_DECAY_RATE = 0.1;        // Baseline leak rate toward center (10% per 3 sec)
const int BASELINE_DECAY_INTERVAL = 150;      // Apply decay every 150 samples (3 seconds)
```

### Beat Detection Parameters
```cpp
const float THRESHOLD_FRACTION = 0.6;         // 60% of signal range
const int MIN_SIGNAL_RANGE = 50;              // ADC units, below = invalid
const unsigned long REFRACTORY_PERIOD_MS = 300;  // 200 BPM max (also rate limits to 200 msg/min/sensor)
const int FLAT_SIGNAL_THRESHOLD = 5;          // ADC units variance = "flat"
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;  // 1 sec flat = disconnected (50 samples)
```

### Debug Levels
```cpp
#define DEBUG_LEVEL 0  // 0=production, 1=testing, 2=verbose
// 0: WiFi status only
// 1: Beat timestamps + BPM
// 2: Raw ADC values every 100ms
```

---

## Data Structures

### Sensor State
```cpp
struct SensorState {
  int pin;                          // GPIO pin number
  int rawSamples[MOVING_AVG_SAMPLES];  // Circular buffer for moving average
  int sampleIndex;                  // Current position in circular buffer
  int smoothedValue;                // Output of moving average
  
  // Baseline tracking (exponential decay)
  int minValue;                     // Minimum, decays upward toward center
  int maxValue;                     // Maximum, decays downward toward center
  int samplesSinceDecay;            // Counter for decay interval
  
  // Beat detection state
  bool aboveThreshold;              // Currently above threshold?
  unsigned long lastBeatTime;       // millis() of last detected beat
  unsigned long lastIBI;            // Inter-beat interval in ms
  bool firstBeatDetected;           // Have we sent first beat yet?
  
  // Disconnection detection
  bool isConnected;                 // Sensor shows valid signal?
  int lastRawValue;                 // For flat signal detection
  int flatSampleCount;              // Consecutive flat samples
};

SensorState sensors[4];
```

### System State
```cpp
struct SystemState {
  bool wifiConnected;
  unsigned long lastWiFiCheckTime;
  unsigned long loopCounter;        // For debug output throttling
} system;
```

---

## Algorithm Specifications

### Moving Average Filter
**Purpose**: Smooth high-frequency noise from ADC and sensor

**Implementation**:
- Circular buffer of last 5 samples per sensor
- On each new sample: 
  1. Replace oldest sample in buffer
  2. Calculate mean of all 5 samples
  3. Use mean as smoothed value

**Characteristics**:
- Lag: 50ms (half window size)
- Attenuation: ~13dB at 10Hz
- Computational cost: 5 additions + 1 division per sample

### Adaptive Baseline Tracking
**Purpose**: Handle varying signal amplitudes between users

**Implementation** (exponential decay):
- Track running min/max that slowly decay toward signal center
- On each sample:
  - If current value < min: `minValue = currentValue` (instant expansion)
  - If current value > max: `maxValue = currentValue` (instant expansion)
- Every 150 samples (3 seconds):
  - `minValue += (smoothedValue - minValue) * 0.1` (leak upward 10%)
  - `maxValue -= (maxValue - smoothedValue) * 0.1` (leak downward 10%)

**Characteristics**:
- Fast response to signal increases (instant)
- Slow adaptation to signal decreases (3 sec time constant)
- No additional memory overhead (just two integers)
- Handles gradual amplitude changes over time

**Edge Cases**:
- Signal range < 50 ADC units → mark sensor disconnected
- Prevents false beats from noise on flat signals

### Beat Detection Algorithm
**Threshold Calculation**:
```
threshold = minValue + (maxValue - minValue) * THRESHOLD_FRACTION
```
- Default: 60% of signal range above baseline
- Tunable via THRESHOLD_FRACTION (try 0.5-0.7)

**Detection Logic**:
1. Compare smoothed value to threshold
2. **Rising edge**: If was below threshold, now above → potential beat
3. **Refractory check**: If time since last beat < 300ms → ignore (debounce)
4. **Valid beat**: Record timestamp, calculate IBI, send OSC message
5. Update state: `aboveThreshold = true`, `lastBeatTime = now`
6. **Falling edge**: When crosses back below threshold → `aboveThreshold = false`

**Why rising edge only**: Prevents double-triggering on single pulse

### Inter-Beat Interval Calculation
```
if (firstBeatDetected) {
  IBI = currentBeatTime - lastBeatTime
  // Send OSC message
} else {
  // First beat: just record time, don't send
  firstBeatDetected = true
}
lastBeatTime = currentBeatTime
```
- Units: milliseconds
- First beat after startup: No message sent (no reference point)
- Second and subsequent beats: Valid IBI sent
- After long disconnection: IBI may be large (accurate time since last beat)

---

## OSC Protocol Specification

### Message Format
**Heartbeat event**:
```
Address: /heartbeat/N
Arguments: <int32> ibi_ms
Example: /heartbeat/0 847
```
- N: Sensor index (0-3)
- ibi_ms: Milliseconds since previous beat on this sensor

**No BPM messages**: Server calculates BPM as `60000 / ibi_ms` if needed

### Transmission Behavior
- **Trigger**: Sent immediately when beat detected
- **Protocol**: UDP (fire-and-forget, no ACK)
- **Timing**: Non-blocking send, doesn't wait for confirmation
- **Failure mode**: If WiFi down, message dropped silently

### Network Layer
- **Transport**: UDP over WiFi
- **Destination**: Fixed IP and port (configured at compile time)
- **Packet size**: ~24 bytes per message (small, no fragmentation)
- **No discovery**: ESP32 doesn't search for server, sends to fixed address

---

## Disconnection Detection

### Criteria
Sensor marked disconnected if:
1. **Flat signal**: `abs(currentRawValue - lastRawValue) < 5` for 50 consecutive samples (1 second)
2. **Insufficient range**: `(maxValue - minValue) < 50` for 1 second

### Algorithm
```cpp
// On each sample:
if (abs(rawValue - lastRawValue) < FLAT_SIGNAL_THRESHOLD) {
  flatSampleCount++;
} else {
  flatSampleCount = 0;
}

if (flatSampleCount >= 50) {  // 1 second at 50Hz
  isConnected = false;
}

// Also check range
if ((maxValue - minValue) < MIN_SIGNAL_RANGE) {
  isConnected = false;
}
```

### Behavior When Disconnected
- Stop sending OSC messages for that sensor
- Continue sampling (allows auto-reconnection)
- No error messages sent to server (clean silence)

### Reconnection
- Automatically detected when signal range returns
- Baseline tracking resets
- Next valid beat resumes OSC transmission
- IBI may be large (time since last beat before disconnect)

---

## WiFi Management

### Initial Connection
```
1. WiFi.begin(SSID, PASSWORD)
2. Wait up to 30 seconds for connection
3. If timeout → halt, blink LED rapidly (error state)
4. If success → proceed to main loop
```

### Connection Monitoring
- Check `WiFi.status()` every 5 seconds (non-blocking)
- If disconnected:
  - Set `wifiConnected = false`
  - Attempt reconnection in background
  - Continue sampling sensors
  - OSC sends will fail silently

### Reconnection Logic
- `WiFi.reconnect()` called when disconnect detected
- Non-blocking operation
- No timeout for reconnection (keep trying indefinitely)
- When reconnected, resume OSC transmission

### Static IP (Optional Enhancement)
Not in initial version, but consideration:
```cpp
WiFi.config(localIP, gateway, subnet);
```
- Faster connection (no DHCP negotiation)
- More reliable in crowded networks
- Requires manual network configuration

---

## Status LED Behavior

### LED States
| State | Behavior | Meaning |
|-------|----------|---------|
| Off | Solid off | Boot/initialization |
| Rapid blink (10Hz) | 50ms on/off | WiFi connecting (not error) |
| Solid on | Constant | WiFi connected, awaiting beats |
| Single blink | 50ms pulse | Beat detected on any sensor |

### Implementation
```cpp
unsigned long ledOnTime = 0;
const int LED_PULSE_DURATION = 50;  // 50ms for visibility

void updateLED() {
  if (!wifiConnected) {
    // Rapid blink while connecting
    digitalWrite(STATUS_LED_PIN, (millis() / 50) % 2);
  } else if (beatDetectedThisLoop) {
    // Pulse on beat
    digitalWrite(STATUS_LED_PIN, HIGH);
    ledOnTime = millis();
  } else if (millis() - ledOnTime < LED_PULSE_DURATION) {
    // Keep on during pulse
    digitalWrite(STATUS_LED_PIN, HIGH);
  } else {
    // Solid on when idle and connected
    digitalWrite(STATUS_LED_PIN, HIGH);
  }
}
```

### Beat Pulse Duration
- LED turns on when beat detected
- Stays on for 50ms (clearly visible)
- Returns to solid on state

---

## Debug Output Levels

### Level 0: Production
**Serial output**:
- Boot message with firmware version
- WiFi connection status (IP address)
- Critical errors only

**Use case**: Festival deployment, clean serial monitor

### Level 1: Testing
**Additional output**:
- Each beat timestamp: `[0] Beat at 12847ms, IBI=856ms`
- Disconnection events: `[2] Sensor disconnected`
- Reconnection events: `[2] Sensor reconnected`
- WiFi reconnection attempts

**Use case**: Multi-person testing, validating timing

### Level 2: Verbose Debug
**Additional output**:
- Raw ADC values every 100ms: `[0]=2456 [1]=2391 [2]=0 [3]=2678`
- Baseline values every 1s: `[0] min=2200 max=2800 thresh=2560`
- OSC transmission confirmation: `Sent /heartbeat/0 856`

**Use case**: Algorithm tuning, troubleshooting sensor issues

### Throttling
- Debug output uses `loopCounter` to limit frequency
- Raw values: Only every 100ms (not every 20ms sample)
- Prevents serial buffer overflow

---

## Startup Sequence

### Boot Process
```
1. Serial.begin(115200)
2. Print firmware version and build date
3. Initialize GPIO (analog inputs, LED output)
4. Initialize sensor state structs:
   - Pre-fill moving average buffers with first ADC reading
   - Set minValue = maxValue = first reading
   - Zero all counters
5. WiFi.begin(SSID, PASSWORD)
6. Attempt connection (indefinite retry):
   - Blink LED while connecting (10Hz)
   - Check every 500ms
   - If connected: break, proceed
   - If failed: retry every 5 seconds
   - Never halt (festival resilience)
7. Print assigned IP address
8. Initialize UDP for OSC
9. Enable watchdog timer (3 seconds)
10. Turn LED solid on
11. Enter main loop
```

### Moving Average Initialization
```cpp
// On startup for each sensor:
int firstReading = analogRead(pin);
for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
  rawSamples[i] = firstReading;
}
smoothedValue = firstReading;
minValue = maxValue = firstReading;
```
Prevents invalid data during buffer fill period.

---

## Main Loop Structure

```
unsigned long lastSampleTime = 0;

Loop iteration:
  1. Check if 20ms elapsed since last sample
     if (millis() - lastSampleTime >= SAMPLE_INTERVAL_MS):
       lastSampleTime = millis()
       
       2. Read all 4 analog inputs
       3. For each sensor:
          a. Add raw value to moving average buffer
          b. Calculate smoothed value
          c. Update baseline min/max (expand or decay)
          d. Check for disconnection (flat signal)
          e. If connected:
             - Calculate threshold
             - Check for beat (rising edge + refractory)
             - If beat detected: calculate IBI, send OSC (skip if first beat)
       4. Update LED state (50ms pulse or solid)
       5. Feed watchdog
       6. Debug output (if enabled)
       
  7. Check WiFi status (every 5 seconds, non-blocking)
  8. Loop continues without delay (WiFi background tasks run)
```

### Timing Precision
- Target: 20ms per sample cycle
- Actual: 20-22ms typical (ADC + WiFi overhead)
- Non-blocking: WiFi can process in background
- Beat timestamp uses `millis()` (1ms resolution)

---

## Error Handling & Recovery

### Watchdog Timer
- **Timeout**: 3 seconds
- **Purpose**: Recover from hung WiFi or infinite loops
- **Behavior**: Hardware reset, full reboot
- **Feed location**: End of main loop (every 20ms)

### WiFi Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Initial connection fails | Status check every 500ms | Retry indefinitely every 5 sec, LED blinks |
| Connection drops during operation | `WiFi.status()` check | Background reconnection, keep sampling |
| Server unreachable | None (UDP) | Messages dropped, no error |

### Sensor Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Disconnected | Flat signal 1 sec | Stop sending, auto-resume when reconnected |
| Poor contact | Signal range < 50 | Treated as disconnected |
| Excessive noise | Moving average smooths | May need threshold tuning |
| Double beats | Refractory period | Max 200 BPM enforced |

### Memory Safety
- No dynamic allocation (all arrays fixed size)
- No recursion
- Stack usage < 2KB (well within ESP32 limits)
- Heap fragmentation not a concern

---

## Performance Characteristics

### CPU Usage (Estimated)
- ADC sampling: 1-2% (4 sensors * 50Hz * 20µs)
- Signal processing: 2-3% (moving avg, baseline, threshold)
- WiFi/OSC: 5-10% (variable, spiky during transmission)
- Main loop overhead: 1-2%
- **Total: 10-20% average, 30% peak**

### Memory Usage
- Program flash: ~200KB (with OSC library)
- Static RAM: ~2KB (sensor state structs: 4 sensors × ~120 bytes each)
- Stack: ~2KB maximum
- **Total: ~4KB RAM used of 320KB available (1.25%)**

### Network Bandwidth
- 4 sensors * 60-180 BPM average = 240-720 messages/minute
- 24 bytes per message = 5-17 KB/minute
- **Negligible network load**

### Latency Budget
| Stage | Typical | Maximum |
|-------|---------|---------|
| ADC sample | 20µs | 50µs |
| Moving average | 5µs | 10µs |
| Beat detection | 10µs | 20µs |
| OSC message build | 50µs | 100µs |
| UDP transmission | 1-5ms | 20ms |
| **Total: Beat to network** | **<10ms** | **<25ms** |

---

## Tuning Parameters

### Threshold Fraction
**Default**: 0.6 (60% above baseline)

**Symptoms requiring adjustment**:
- Too low (0.4-0.5): Noise triggers false beats
- Too high (0.7-0.8): Weak signals miss beats

**Tuning process**:
1. Enable Level 2 debug, observe baseline values
2. Watch for missed beats (gaps > 2 seconds)
3. Adjust in 0.05 increments
4. Test with multiple signal strengths

### Minimum Signal Range
**Default**: 50 ADC units

**Symptoms**:
- Too low (<30): False beats from noise
- Too high (>100): Weak but valid signals ignored

**Tuning**: Measure typical signal amplitude, set threshold to 20-30% of range

### Refractory Period
**Default**: 300ms (200 BPM max)

**Dual purpose**:
1. Prevents double-triggers on single pulse
2. Rate limits OSC messages: max 200 messages/min per sensor, 800/min total system

**Adjustment**:
- Athletes: Reduce to 250ms (240 BPM)
- General population: 300ms appropriate
- Noise issues: Increase to 350ms (caution: may miss real beats)

### Baseline Window
**Default**: 3 seconds (150 samples)

**Trade-offs**:
- Shorter (1-2s): Faster adaptation, less stable
- Longer (5-10s): More stable, slower adaptation
- 3s balances initial lock-on vs signal changes

---

## Testing & Validation

### Unit Tests (Development Phase)

**Test 1: Single sensor smoke test**
- Connect one sensor to GPIO 32
- Apply finger, observe serial output at Level 2
- Verify: Raw ADC oscillates, smoothed value follows, beats detected
- Expected BPM: 50-100 at rest

**Test 2: Threshold adaptation**
- Vary finger pressure (changes amplitude)
- Observe baseline min/max adjustment
- Verify: Beats still detected across range

**Test 3: Refractory period**
- Tap sensor rapidly by hand
- Verify: Beats limited to 200 BPM (300ms minimum)

**Test 4: Disconnection detection**
- Remove finger for 2 seconds
- Verify: Messages stop, LED continues
- Reapply finger
- Verify: Messages resume

**Test 5: WiFi resilience**
- Start with WiFi connected
- Disable WiFi access point
- Verify: ESP32 attempts reconnection, sampling continues
- Re-enable WiFi
- Verify: Connection resumes, OSC transmission resumes

### Integration Tests

**Test 6: Multi-sensor independence**
- Connect all 4 sensors
- Apply 4 different heartbeats (or simulate with function generator)
- Verify: Each sensor sends independent IBI values
- Expected: No crosstalk, each channel accurate

**Test 7: OSC timing validation**
- Use Wireshark or OSC monitor on server
- Measure timestamp accuracy
- Verify: Message arrives <25ms after beat
- Verify: IBI values match expected (±5ms)

**Test 8: Extended duration**
- Run for 30+ minutes
- Monitor for: Memory leaks, WiFi drops, watchdog resets
- Expected: Zero failures, stable operation

**Test 9: Hot-swap ESP32**
- Sensors connected to breadboard
- ESP32 #1 running, heartbeats detected
- Swap to ESP32 #2 (same firmware)
- Verify: Seamless transition, no server-side disruption

### Acceptance Criteria
- [ ] Single sensor: Beats detected within 3 seconds of finger application
- [ ] BPM accuracy: ±5 BPM vs smartphone heart rate app
- [ ] Multi-sensor: All 4 sensors operate simultaneously without interference
- [ ] Latency: Beat to OSC message <25ms (95th percentile)
- [ ] Reliability: Zero crashes over 1-hour continuous operation
- [ ] Disconnection: Messages stop within 1 second of sensor removal
- [ ] Reconnection: Messages resume within 3 seconds of sensor reapplication
- [ ] WiFi recovery: Auto-reconnect within 30 seconds of access point restoration

---

## Known Limitations

### Hardware Limitations
- ADC resolution: 12-bit (4096 levels), adequate but not clinical-grade
- ADC linearity: ±2% typical, may cause slight BPM error
- GPIO 34-35: Input-only, no pullup/pulldown available
- WiFi and Bluetooth: Cannot use simultaneously (ADC2 conflict)

### Algorithm Limitations
- Moving average lag: 50ms delay in signal
- Baseline adaptation: Slow to respond to sudden amplitude changes
- Threshold fixed fraction: May not be optimal for all users
- No beat-to-beat variability: Only reports interval, not waveform shape

### Environmental Limitations
- Optical sensors: Sensitive to ambient light (cover recommended)
- Cold hands: Reduced peripheral blood flow affects signal quality
- Movement: Large motions create artifacts (participants should lie still)
- WiFi range: ESP32 limited to ~30m from access point

### Protocol Limitations
- UDP unreliable: Packets may drop without notification
- No server acknowledgment: ESP32 doesn't know if messages received
- Fixed destination: Cannot dynamically discover server
- No error reporting: Server must infer disconnection from missing messages

---

## Future Enhancements

### Potential Improvements (Not in v1.0)

**Waveform transmission**: Send full pulse shape (20 samples per beat) for:
- Heart rate variability (HRV) analysis
- Pulse transit time measurement
- Richer audio synthesis

**Bluetooth fallback**: Use BLE when WiFi unavailable (requires code restructuring)

**Onboard BPM calculation**: Send both IBI and BPM for convenience

**Beat prediction**: Use Kalman filter to predict next beat for tighter audio sync

**Adaptive refractory**: Adjust based on recent IBI history

**Quality metrics**: Send signal-to-noise ratio with each beat

**Multi-server**: Broadcast OSC to multiple destinations

**Configuration interface**: Web server for WiFi credentials and tuning parameters

**SD card logging**: Record all data for post-analysis

**Time synchronization**: NTP to provide absolute timestamps

---

## Development Roadmap

### Phase 1: Single Sensor (Days 1-2)
- [ ] Basic ADC sampling at 50Hz
- [ ] Moving average filter
- [ ] Simple threshold (fixed value)
- [ ] Beat detection with refractory
- [ ] Serial output only (no OSC)
- [ ] Test with one person

### Phase 2: Algorithm Refinement (Day 3)
- [ ] Adaptive baseline tracking
- [ ] Disconnection detection
- [ ] Threshold tuning with multiple people
- [ ] Extended duration testing (15+ minutes)

### Phase 3: Multi-Sensor (Day 4)
- [ ] Expand to 4 sensors
- [ ] Independent state tracking
- [ ] Test with multiple people
- [ ] Validate no crosstalk

### Phase 4: OSC Integration (Day 5)
- [ ] WiFi connection
- [ ] OSC library integration
- [ ] Message formatting
- [ ] Server-side validation

### Phase 5: Reliability (Day 6)
- [ ] Watchdog timer
- [ ] WiFi reconnection logic
- [ ] Error handling
- [ ] Hot-swap testing

### Phase 6: Polish (Day 7)
- [ ] LED behavior refinement
- [ ] Debug level cleanup
- [ ] Documentation
- [ ] Final acceptance testing

---

## Library Dependencies

### Required Libraries
```cpp
#include <WiFi.h>           // Built-in ESP32
#include <WiFiUdp.h>        // Built-in ESP32
#include <OSCMessage.h>     // Install via Library Manager
```

### Installation
```
Arduino IDE → Tools → Manage Libraries → Search "OSC"
Install: "OSC" by Adrian Freed (CNMat)
Version: 1.3.7 or newer
```

### Alternative: Manual OSC
If library unavailable, OSC format is simple:
```
UDP packet format:
  /heartbeat/N\0\0,i\0\0<4-byte int32>
```
Can implement manually with WiFiUdp.beginPacket/write/endPacket

---

## Code Organization

### File Structure (Single .ino file)
```
1. Header comments (project, version, date)
2. #includes
3. Configuration constants
4. Data structures (SensorState, SystemState)
5. Global variables
6. setup() function
7. loop() function
8. Helper functions:
   - initializeSensor()
   - readAndFilterSensor()
   - updateBaseline()
   - detectBeat()
   - sendOSC()
   - checkWiFi()
   - updateLED()
   - debugPrint()
```

### Naming Conventions
- Constants: `UPPER_SNAKE_CASE`
- Variables: `camelCase`
- Functions: `camelCase()`
- Structs: `PascalCase`

### Comment Strategy
- High-level algorithm descriptions at function level
- Inline comments for non-obvious logic
- No comments for self-explanatory code
- References to this design doc for detailed explanations

---

## Version History

### v1.0 (Target: Day 7)
- Initial release
- 4 sensor support
- Adaptive threshold beat detection
- OSC over WiFi
- Basic error handling

### Future Versions
- v1.1: Tuning refinements based on festival feedback
- v1.2: Waveform transmission (if needed)
- v2.0: Multi-server support, web configuration

---

## Appendix: Sample Serial Output

### Level 1 (Testing)
```
Heartbeat Installation Firmware v1.0
Connecting to WiFi: your-network-name...
Connected! IP: 192.168.1.42
OSC target: 192.168.1.100:8000
Starting heartbeat detection...

[0] First beat detected at 3421ms (no message sent)
[1] First beat detected at 3856ms (no message sent)
[0] Beat at 4287ms, IBI=866ms
[2] First beat detected at 4501ms (no message sent)
[0] Beat at 5156ms, IBI=869ms
[1] Beat at 5234ms, IBI=1378ms
[2] Beat at 5389ms, IBI=888ms
[3] First beat detected at 5672ms (no message sent)
...
[2] Sensor disconnected
[2] Sensor reconnected
[2] Beat at 45123ms, IBI=892ms
```

### Level 2 (Debug)
```
[0]=2456 [1]=2391 [2]=0 [3]=2678
[0]=2467 [1]=2401 [2]=0 [3]=2689
[0]=2489 [1]=2423 [2]=0 [3]=2701
[0] min=2200 max=2800 thresh=2560
[0]=2512 [1]=2445 [2]=0 [3]=2715
[0] BEAT at 3421ms, IBI=0ms
Sent OSC: /heartbeat/0 0
[0]=2534 [1]=2467 [2]=0 [3]=2728
...
```

---

*Document Version: 1.0*
*Last Updated: 2025-11-06*
*Companion to: heartbeat-input-hardware-design.md*
*Implementation: ESP32 Arduino framework*