# API: Sensor Initialization & Filtering

Functions for hardware sampling and moving average filtering.

---

## 6.1 Sensor Initialization

**Function:** `initializeSensor()`

**Signature:**
```cpp
void initializeSensor(int sensorIndex);
```

**Purpose:** Initialize sensor state on startup

**Parameters:**
- `sensorIndex`: Index 0-3 into sensors array

**Requirements:**

**R6: Initial Reading**
```cpp
int firstReading = analogRead(sensors[sensorIndex].pin);
```
- MUST read ADC immediately after GPIO configuration
- Provides valid starting value for buffers

**R7: Buffer Pre-fill**
```cpp
for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
  sensors[sensorIndex].rawSamples[i] = firstReading;
}
```
- MUST fill entire moving average buffer with first reading
- Prevents invalid calculations during buffer fill
- Allows immediate filtering

**R8: State Initialization**
```cpp
sensors[sensorIndex].sampleIndex = 0;
sensors[sensorIndex].smoothedValue = firstReading;
sensors[sensorIndex].minValue = firstReading;
sensors[sensorIndex].maxValue = firstReading;
sensors[sensorIndex].aboveThreshold = false;
sensors[sensorIndex].lastBeatTime = 0;
sensors[sensorIndex].lastIBI = 0;
sensors[sensorIndex].firstBeatDetected = false;
sensors[sensorIndex].isConnected = true;  // Assume connected initially
sensors[sensorIndex].lastRawValue = firstReading;
sensors[sensorIndex].flatSampleCount = 0;
sensors[sensorIndex].samplesSinceDecay = 0;
```

**Call Location:** In `setup()` after GPIO configuration, before main loop

**Example Usage:**
```cpp
void setup() {
  // ... GPIO configuration ...

  for (int i = 0; i < NUM_SENSORS; i++) {
    sensors[i].pin = SENSOR_PINS[i];
    initializeSensor(i);
  }
}
```

---

## 6.2 Signal Sampling and Filtering

**Function:** `readAndFilterSensor()`

**Signature:**
```cpp
void readAndFilterSensor(int sensorIndex);
```

**Purpose:** Read ADC, update moving average, store smoothed value

**Parameters:**
- `sensorIndex`: Index 0-3 into sensors array

**Requirements:**

**R9: ADC Read**
```cpp
int rawValue = analogRead(sensors[sensorIndex].pin);
```
- Read current ADC value from sensor pin
- 12-bit resolution: 0-4095

**R10: Moving Average Update**
```cpp
// Store in circular buffer
sensors[sensorIndex].rawSamples[sensors[sensorIndex].sampleIndex] = rawValue;
sensors[sensorIndex].sampleIndex = (sensors[sensorIndex].sampleIndex + 1) % MOVING_AVG_SAMPLES;

// Calculate average
int sum = 0;
for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
  sum += sensors[sensorIndex].rawSamples[i];
}
sensors[sensorIndex].smoothedValue = sum / MOVING_AVG_SAMPLES;
```
- MUST maintain circular buffer correctly
- MUST calculate mean of all samples
- Smoothed value used for all downstream processing

**R11: Disconnection Check**
```cpp
// Check for flat signal
if (abs(rawValue - sensors[sensorIndex].lastRawValue) < FLAT_SIGNAL_THRESHOLD) {
  sensors[sensorIndex].flatSampleCount++;
} else {
  sensors[sensorIndex].flatSampleCount = 0;
}

// Mark disconnected after 1 second flat
if (sensors[sensorIndex].flatSampleCount >= 50) {  // 50 samples at 50Hz = 1 sec
  sensors[sensorIndex].isConnected = false;
}

sensors[sensorIndex].lastRawValue = rawValue;
```
- Detect lack of signal variation
- Reset counter on any significant change
- Require sustained flatness (1 second) before marking disconnected

**Timing:**
- Call once per sampling cycle (every 20ms for 50Hz)
- Total processing: <5ms per sensor

**Example Usage:**
```cpp
void loop() {
  static unsigned long lastSampleTime = 0;
  unsigned long currentTime = millis();

  if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = currentTime;

    for (int i = 0; i < NUM_SENSORS; i++) {
      readAndFilterSensor(i);  // Sample and filter
    }
  }
}
```

**Output Data:**
- Updated `sensors[i].smoothedValue` — Filtered signal ready for threshold calculation
- Updated `sensors[i].isConnected` — Connection status
- Updated `sensors[i].lastRawValue` — For next iteration

---

## Related Documentation

- [Configuration](configuration.md) — Buffer sizes and timing constants
- [API: Signal Processing](api-signal-processing.md) — Process smoothed value for beat detection
- [API: Beat Detection](api-beat-detection.md) — Uses smoothed value for threshold crossing
- [Implementation](implementation.md) — Where these functions are called in loop()

---

**Next Step:** Implement signal processing with [API: Signal Processing](api-signal-processing.md)
