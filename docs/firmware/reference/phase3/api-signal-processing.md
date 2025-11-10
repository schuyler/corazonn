# API: Baseline Tracking & Signal Processing

Adaptive min/max baseline tracking with exponential decay.

---

## 6.3 Baseline Tracking

**Function:** `updateBaseline()`

**Signature:**
```cpp
void updateBaseline(int sensorIndex);
```

**Purpose:** Adaptive min/max tracking with exponential decay to maintain dynamic threshold

**Parameters:**
- `sensorIndex`: Index 0-3 into sensors array

**Algorithm Overview:**

The baseline tracking maintains a dynamic range (min/max) of the signal that adapts to:
1. **Instant expansion** — When signal exceeds current bounds, expand immediately
2. **Exponential decay** — Slowly decay bounds back toward signal center to track drifting baseline

This allows the threshold to remain optimal even as sensor contact quality varies.

**Requirements:**

**R12: Instant Expansion**
```cpp
int smoothed = sensors[sensorIndex].smoothedValue;

// Expand range immediately if signal exceeds current bounds
if (smoothed < sensors[sensorIndex].minValue) {
  sensors[sensorIndex].minValue = smoothed;
}
if (smoothed > sensors[sensorIndex].maxValue) {
  sensors[sensorIndex].maxValue = smoothed;
}
```
- MUST respond instantly to signal increases
- Ensures threshold doesn't clip valid beats
- Prevents missing beats due to too-high threshold

**R13: Exponential Decay**
```cpp
sensors[sensorIndex].samplesSinceDecay++;

if (sensors[sensorIndex].samplesSinceDecay >= BASELINE_DECAY_INTERVAL) {
  // Decay min upward toward center
  sensors[sensorIndex].minValue +=
    (smoothed - sensors[sensorIndex].minValue) * BASELINE_DECAY_RATE;

  // Decay max downward toward center
  sensors[sensorIndex].maxValue -=
    (sensors[sensorIndex].maxValue - smoothed) * BASELINE_DECAY_RATE;

  sensors[sensorIndex].samplesSinceDecay = 0;
}
```
- MUST apply decay every 150 samples (3 seconds at 50Hz)
- Decay rate: 10% toward current signal per interval
- Prevents baseline from drifting too far from signal
- Allows adaptation to changing conditions (temperature, contact quality)

**R14: Range Check**
```cpp
int range = sensors[sensorIndex].maxValue - sensors[sensorIndex].minValue;
if (range < MIN_SIGNAL_RANGE) {
  sensors[sensorIndex].isConnected = false;
}
```
- Mark disconnected if range too small (likely noise, not pulse)
- Prevents false beats on flat signals
- `MIN_SIGNAL_RANGE` = 50 ADC units typical

**Timing:**
- Call once per sampling cycle (every 20ms)
- Decay applied every 150 samples (every 3 seconds)
- Processing: <2ms per sensor

**Example Usage:**
```cpp
void loop() {
  static unsigned long lastSampleTime = 0;
  unsigned long currentTime = millis();

  if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = currentTime;

    for (int i = 0; i < NUM_SENSORS; i++) {
      readAndFilterSensor(i);     // Get smoothed value
      updateBaseline(i);           // Update min/max with decay
      detectBeat(i);               // Use updated baseline for threshold
    }
  }
}
```

**State Updates:**
- `sensors[i].minValue` — Updated with instant expansion and decay
- `sensors[i].maxValue` — Updated with instant expansion and decay
- `sensors[i].samplesSinceDecay` — Incremented each cycle, reset on decay
- `sensors[i].isConnected` — Set false if range too small

**Decay Algorithm Explanation:**

The exponential decay moves the min/max toward the current signal value gradually:

```
Before decay:  minValue=2200, maxValue=2800, smoothed=2500
Decay rate: 0.1 (10%)

New minValue = 2200 + (2500 - 2200) * 0.1 = 2200 + 30 = 2230
New maxValue = 2800 - (2800 - 2500) * 0.1 = 2800 - 30 = 2770

Effect: Range narrows by 60 units every 3 seconds, eventually centering on signal
```

This creates a self-adjusting threshold that tracks baseline drift while remaining sensitive to beats.

---

## Related Documentation

- [Configuration](configuration.md) — Decay rate, interval, and range threshold constants
- [API: Sensors](api-sensors.md) — Provides smoothed value input
- [API: Beat Detection](api-beat-detection.md) — Uses updated min/max for threshold calculation
- [Implementation](implementation.md) — Function call order in loop()

---

**Next Step:** Use baseline in [API: Beat Detection](api-beat-detection.md)
