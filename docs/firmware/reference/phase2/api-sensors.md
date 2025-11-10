# Sensor API

## Sensor Initialization and Data Filtering

### initializeSensor()

**Signature:**
```cpp
void initializeSensor();
```

**Purpose:** Initialize ADC, pre-fill moving average buffer, set initial baseline

**Called from:** `setup()` after WiFi initialization

**Requirements:**

**R1: ADC Configuration**
- MUST call `analogSetAttenuation(ADC_11db)` for 0-3.3V range
- MUST call `analogReadResolution(12)` for 12-bit resolution
- MUST configure `SENSOR_PIN` (GPIO 32)
- Note: Some ESP32 cores may require `adcAttachPin(SENSOR_PIN)` to be called first for per-pin configuration

**R2: Initial Reading**
- MUST read first ADC sample: `int firstReading = analogRead(SENSOR_PIN)`
- MUST print first reading to serial for debugging

**R3: Moving Average Initialization**
- MUST pre-fill `rawSamples[]` array with first reading
- Prevents invalid data during buffer fill period
- Loop: `for (int i = 0; i < MOVING_AVG_SAMPLES; i++) sensor.rawSamples[i] = firstReading`

**R4: Baseline Initialization**
- MUST set `sensor.minValue = firstReading`
- MUST set `sensor.maxValue = firstReading`
- MUST set `sensor.smoothedValue = firstReading`

**R5: Connection State**
- MUST set `sensor.isConnected = true` (assume connected at start)
- MUST set `sensor.lastRawValue = firstReading`
- MUST set `sensor.lastBeatTime = millis()` (prevents false refractory rejection on first beat)

**Pseudocode:**
```
function initializeSensor():
    analogSetAttenuation(ADC_11db)
    analogReadResolution(12)
    # Note: Some ESP32 cores may require: adcAttachPin(SENSOR_PIN) first

    firstReading = analogRead(SENSOR_PIN)
    Serial.print("First ADC reading: ")
    Serial.println(firstReading)

    for i in 0 to MOVING_AVG_SAMPLES-1:
        sensor.rawSamples[i] = firstReading

    sensor.smoothedValue = firstReading
    sensor.minValue = firstReading
    sensor.maxValue = firstReading
    sensor.isConnected = true
    sensor.lastRawValue = firstReading
    sensor.lastBeatTime = millis()  # Prevents false refractory rejection on first beat
```

---

## Moving Average Filter

### updateMovingAverage()

**Signature:**
```cpp
void updateMovingAverage(int rawValue);
```

**Purpose:** Add new sample to circular buffer and calculate smoothed value

**Parameters:**
- `rawValue`: Current ADC reading (0-4095)

**Called from:** Main loop, once per sampling interval (every 20ms)

**Requirements:**

**R6: Circular Buffer Update**
- MUST replace oldest sample in buffer: `sensor.rawSamples[sensor.sampleIndex] = rawValue`
- MUST increment index: `sensor.sampleIndex = (sensor.sampleIndex + 1) % MOVING_AVG_SAMPLES`
- Modulo wraps index to 0 after reaching end

**R7: Calculate Mean**
- MUST sum all samples in buffer
- MUST divide by `MOVING_AVG_SAMPLES` to get mean
- MUST store result in `sensor.smoothedValue`

**R8: No Filtering on First Fill**
- First 5 samples after initialization will gradually replace pre-filled values
- Moving average automatically adapts (no special case needed)

**Pseudocode:**
```
function updateMovingAverage(rawValue):
    sensor.rawSamples[sensor.sampleIndex] = rawValue
    sensor.sampleIndex = (sensor.sampleIndex + 1) % MOVING_AVG_SAMPLES

    sum = 0
    for i in 0 to MOVING_AVG_SAMPLES-1:
        sum += sensor.rawSamples[i]

    sensor.smoothedValue = sum / MOVING_AVG_SAMPLES
```

---

## Integration in Main Loop

**Typical loop cycle:**
```cpp
void loop() {
    unsigned long currentTime = millis();
    if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
        lastSampleTime = currentTime;

        // 1. Read raw ADC value
        int rawValue = analogRead(SENSOR_PIN);

        // 2. Apply moving average filter
        updateMovingAverage(rawValue);

        // 3. Continue with signal processing (baseline, beat detection, etc.)
    }
}
```

---

## Signal Characteristics

**Expected ADC Values (PulseSensor):**
- No finger: 0-500 (or noisy constant)
- Light contact: 1500-2500
- Good contact: 2000-3500
- Range: Typically 500-1500 ADC units difference between min/max

**Sampling Rate:** 50 Hz (every 20ms)
- Nyquist frequency: 25 Hz
- Adequate for heartbeat signal (1-3 Hz fundamental)

**Moving Average Window:** 100ms (5 samples @ 50Hz)
- Smooth noise without excessive lag
- One complete heartbeat pulse: 400-1000ms
- Filter passes beat signal while attenuating high-frequency noise

---

## Related Documentation

- **[Configuration](configuration.md)** - Sampling parameters and constants
- **[Signal Processing API](api-signal-processing.md)** - Baseline tracking after filtering
- **[Beat Detection API](api-beat-detection.md)** - Uses smoothedValue for detection
- **[Implementation](implementation.md)** - Integration in setup() and loop()

---

## Initialization Flow

```
setup():
  connectWiFi()
  udp.begin(0)
  initializeSensor()  ← Initializes ADC, buffers, baseline
    └─ analogSetAttenuation()
    └─ analogReadResolution()
    └─ analogRead() - first reading
    └─ pre-fill rawSamples[]

loop():
  analogRead(SENSOR_PIN) - every 20ms
  updateMovingAverage(rawValue) - calculate smoothed value
  updateBaseline() - track min/max
  checkDisconnection() - detect flat signal
  detectBeat() - use smoothedValue for threshold
```
