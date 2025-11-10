# Signal Processing API

## Baseline Tracking

### updateBaseline()

**Signature:**
```cpp
void updateBaseline();
```

**Purpose:** Track running min/max with exponential decay toward current signal level

**Called from:** Main loop, same interval as ADC sampling (every 20ms)

**Requirements:**

**R9: Instant Expansion**
- IF `sensor.smoothedValue < sensor.minValue`: Set `sensor.minValue = sensor.smoothedValue`
- IF `sensor.smoothedValue > sensor.maxValue`: Set `sensor.maxValue = sensor.smoothedValue`
- Baseline expands immediately when signal exceeds previous range

**R10: Periodic Decay**
- MUST increment `sensor.samplesSinceDecay++` each call
- IF `sensor.samplesSinceDecay >= BASELINE_DECAY_INTERVAL` (150 samples = 3 seconds):
  - Apply decay toward current signal level (smoothedValue):
    - `sensor.minValue += (sensor.smoothedValue - sensor.minValue) * BASELINE_DECAY_RATE`
    - `sensor.maxValue -= (sensor.maxValue - sensor.smoothedValue) * BASELINE_DECAY_RATE`
  - Reset counter: `sensor.samplesSinceDecay = 0`

**R11: Integer Arithmetic**
- Decay calculation uses float multiplication, then cast to int
- Example: `sensor.minValue += (int)((sensor.smoothedValue - sensor.minValue) * 0.1)`

**Pseudocode:**
```
function updateBaseline():
    # Instant expansion
    if sensor.smoothedValue < sensor.minValue:
        sensor.minValue = sensor.smoothedValue
    if sensor.smoothedValue > sensor.maxValue:
        sensor.maxValue = sensor.smoothedValue

    # Periodic decay toward current signal level
    sensor.samplesSinceDecay++
    if sensor.samplesSinceDecay >= BASELINE_DECAY_INTERVAL:
        sensor.minValue += (sensor.smoothedValue - sensor.minValue) * BASELINE_DECAY_RATE
        sensor.maxValue -= (sensor.maxValue - sensor.smoothedValue) * BASELINE_DECAY_RATE
        sensor.samplesSinceDecay = 0
```

**Key Parameters:**
```cpp
const float BASELINE_DECAY_RATE = 0.1;      // 10% decay per interval
const int BASELINE_DECAY_INTERVAL = 150;    // Apply every 150 samples (3 seconds @ 50Hz)
```

**Behavior:**
- **Fast adaptation**: Immediately expands to capture signal variations
- **Slow relaxation**: Decays toward signal center over 3-second intervals
- **Handles varying amplitude**: Adapts to different signal strengths without manual tuning
- **Prevents threshold drift**: Baseline centers on actual signal, not fixed ADC values

---

## Disconnection Detection

### checkDisconnection()

**Signature:**
```cpp
void checkDisconnection(int rawValue);
```

**Purpose:** Detect flat signal indicating sensor disconnected

**Parameters:**
- `rawValue`: Current ADC reading (for variance check)

**Called from:** Main loop, same interval as ADC sampling (every 20ms)

**Requirements:**

**R12: Flat Signal Detection**
- Calculate variance: `int variance = abs(rawValue - sensor.lastRawValue)`
- IF `variance < FLAT_SIGNAL_THRESHOLD` (5 ADC units):
  - Increment `sensor.flatSampleCount++`
- ELSE:
  - Reset `sensor.flatSampleCount = 0`

**R13: Disconnection Threshold**
- IF `sensor.flatSampleCount >= 50` (1 second @ 50Hz):
  - Set `sensor.isConnected = false`
  - MUST print "Sensor disconnected" to serial ONCE (not every sample)

**R14: Range Check**
- Calculate signal range: `int range = sensor.maxValue - sensor.minValue`
- IF `range < MIN_SIGNAL_RANGE` (50 ADC units):
  - Set `sensor.isConnected = false`

**R15: Reconnection Detection**
- IF `sensor.isConnected == false` AND signal shows variation:
  - IF `sensor.flatSampleCount == 0` AND `range >= MIN_SIGNAL_RANGE`:
    - Set `sensor.isConnected = true`
    - MUST print "Sensor reconnected" to serial
    - Reset baseline: `minValue = maxValue = smoothedValue`

**R16: Update Last Value**
- MUST update `sensor.lastRawValue = rawValue` at end (for next comparison)

**Pseudocode:**
```
function checkDisconnection(rawValue):
    variance = abs(rawValue - sensor.lastRawValue)

    if variance < FLAT_SIGNAL_THRESHOLD:
        sensor.flatSampleCount++
    else:
        sensor.flatSampleCount = 0

    range = sensor.maxValue - sensor.minValue

    # Check for disconnection
    wasConnected = sensor.isConnected
    if sensor.flatSampleCount >= 50 OR range < MIN_SIGNAL_RANGE:
        sensor.isConnected = false
        if wasConnected:
            Serial.println("Sensor disconnected")

    # Check for reconnection
    if NOT sensor.isConnected AND sensor.flatSampleCount == 0 AND range >= MIN_SIGNAL_RANGE:
        sensor.isConnected = true
        Serial.println("Sensor reconnected")
        sensor.minValue = sensor.smoothedValue
        sensor.maxValue = sensor.smoothedValue

    sensor.lastRawValue = rawValue
```

**Key Parameters:**
```cpp
const int FLAT_SIGNAL_THRESHOLD = 5;            // ADC variance < 5 = flat
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;  // 1 second flat = disconnected
const int MIN_SIGNAL_RANGE = 50;                // Minimum ADC range for valid signal
```

**Behavior:**
- **Flat signal detection**: Counts consecutive samples with < 5 ADC units variance
- **Range check**: Also monitors overall signal amplitude
- **1-second timeout**: Requires 1 second of flat signal before disconnection
- **Auto-reconnection**: Detects when signal returns to valid range
- **Baseline reset**: When reconnecting, resets baseline to new signal level

---

## Integration in Main Loop

**Typical signal processing pipeline:**
```cpp
void loop() {
    unsigned long currentTime = millis();
    if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
        lastSampleTime = currentTime;

        int rawValue = analogRead(SENSOR_PIN);
        updateMovingAverage(rawValue);      // Smooth signal

        updateBaseline();                   // Track min/max with decay

        checkDisconnection(rawValue);       // Detect sensor removal

        detectBeat();                       // Threshold detection
    }
}
```

---

## Signal Quality Monitoring

**Connected State:**
- Signal range (max - min) > 50 ADC units
- Signal varies (variance > 5 between samples)
- Steady variation pattern consistent with heartbeat

**Disconnected State:**
- Signal flat (variance < 5 for 1 second)
- Signal range < 50 ADC units
- No pulse waveform visible

**Noise Characteristics:**
- High-frequency noise (50Hz sampling filters)
- Ambient light changes (slow decay handles)
- Movement artifacts (refractory period mitigates)

---

## Related Documentation

- **[Configuration](configuration.md)** - Parameters and thresholds
- **[Sensor API](api-sensors.md)** - Moving average filter before baseline
- **[Beat Detection API](api-beat-detection.md)** - Uses baseline for threshold calculation
- **[Implementation](implementation.md)** - Integration in main loop
- **[Operations](operations.md)** - Troubleshooting disconnection issues

---

## Threshold Calculation (Beat Detection)

Baseline tracking provides min/max values used for adaptive beat detection:

```cpp
// In detectBeat()
int threshold = sensor.minValue + (int)((sensor.maxValue - sensor.minValue) * THRESHOLD_FRACTION);
```

The threshold is calculated as 60% of the signal range above baseline minimum. This approach:
- Adapts to varying signal amplitudes
- Prevents missed beats on weak signals
- Reduces false beats from noise on strong signals
- Requires no manual calibration per user
