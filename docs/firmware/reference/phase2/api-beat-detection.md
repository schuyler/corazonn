# Beat Detection API

## Beat Detection and IBI Calculation

### detectBeat()

**Signature:**
```cpp
void detectBeat();
```

**Purpose:** Detect heartbeat using adaptive threshold with refractory period

**Called from:** Main loop, same interval as ADC sampling (every 20ms)

**Requirements:**

**R17: Threshold Calculation**
- Calculate threshold: `int threshold = sensor.minValue + (int)((sensor.maxValue - sensor.minValue) * THRESHOLD_FRACTION)`
- Threshold is 60% of signal range above baseline (configurable via THRESHOLD_FRACTION)

**R18: Rising Edge Detection**
- IF `sensor.smoothedValue >= threshold` AND `sensor.aboveThreshold == false`:
  - Potential beat detected (rising edge)
  - Check refractory period BEFORE updating state

**R19: Refractory Period Check (MUST pass BEFORE setting aboveThreshold)**
- IF potential beat detected:
  - Calculate time since last beat: `unsigned long timeSinceLastBeat = millis() - sensor.lastBeatTime`
  - IF `timeSinceLastBeat < REFRACTORY_PERIOD_MS` (300ms):
    - Ignore beat (too soon, likely noise or double-trigger)
    - Return WITHOUT setting `sensor.aboveThreshold` or sending OSC

**R20: Valid Beat Handling**
- IF potential beat AND refractory period passed:
  - IF `sensor.firstBeatDetected == false`:
    - Set `sensor.firstBeatDetected = true`
    - Record timestamp: `sensor.lastBeatTime = millis()`
    - Print "First beat detected" to serial
    - Do NOT send OSC message (no reference IBI)
    - Return
  - ELSE (second and subsequent beats):
    - Calculate IBI: `unsigned long ibi = millis() - sensor.lastBeatTime`
    - Update timestamp: `sensor.lastBeatTime = millis()`
    - Store IBI: `sensor.lastIBI = ibi`
    - Send OSC message: `sendHeartbeatOSC((int)ibi)`
    - Print beat info to serial

**R21: Falling Edge Detection**
- IF `sensor.smoothedValue < threshold` AND `sensor.aboveThreshold == true`:
  - Set `sensor.aboveThreshold = false` (ready for next beat)

**Pseudocode:**
```
function detectBeat():
    if NOT sensor.isConnected:
        return  # No detection when disconnected

    threshold = sensor.minValue + (sensor.maxValue - sensor.minValue) * THRESHOLD_FRACTION

    # Rising edge
    if sensor.smoothedValue >= threshold AND NOT sensor.aboveThreshold:
        # Potential beat detected
        timeSinceLastBeat = millis() - sensor.lastBeatTime

        # R19: Refractory Period Check (BEFORE setting state)
        if timeSinceLastBeat < REFRACTORY_PERIOD_MS:
            return  # Ignore this beat, do NOT update state

        # Valid beat - now safe to update state
        sensor.aboveThreshold = true  # Set AFTER refractory check

        if NOT sensor.firstBeatDetected:
            sensor.firstBeatDetected = true
            sensor.lastBeatTime = millis()
            Serial.println("First beat detected")
        else:
            ibi = millis() - sensor.lastBeatTime
            sensor.lastBeatTime = millis()
            sensor.lastIBI = ibi
            sendHeartbeatOSC(ibi)
            ledPulseTime = millis()  # Trigger LED pulse
            Serial.print("Beat detected, IBI=")
            Serial.print(ibi)
            Serial.print("ms, BPM=")
            Serial.println(60000 / ibi)

    # Falling edge
    if sensor.smoothedValue < threshold AND sensor.aboveThreshold:
        sensor.aboveThreshold = false
```

---

## Parameters

**Beat Detection:**
```cpp
const float THRESHOLD_FRACTION = 0.6;               // 60% of signal range above baseline
const int MIN_SIGNAL_RANGE = 50;                    // Minimum ADC range for valid signal
const unsigned long REFRACTORY_PERIOD_MS = 300;     // 300ms = max 200 BPM
```

**Rationale:**
- 60% threshold: Empirically effective for PulseSensor (tunable 50-70%)
- Min range 50: Prevents false beats from noise on flat signals
- 300ms refractory: Prevents double-triggers, limits to physiological max (200 BPM)

---

## State Tracking

**Sensor Beat Detection State:**
```cpp
struct BeatDetectionState {
    bool aboveThreshold;        // Currently above threshold? (for edge detection)
    unsigned long lastBeatTime; // millis() of last beat (for refractory period)
    unsigned long lastIBI;      // Inter-beat interval (ms) from last beat pair
    bool firstBeatDetected;     // Have we sent first beat? (first beat has no IBI)
};
```

**State Transitions:**
1. **Initialization**: `aboveThreshold=false`, `firstBeatDetected=false`
2. **First Beat**: Signal crosses threshold, record `lastBeatTime`, set `firstBeatDetected=true`
3. **Subsequent Beats**: Signal crosses threshold, calculate IBI, send OSC
4. **Rising Edge**: `aboveThreshold=false` → `true` (crossing upward)
5. **Falling Edge**: `aboveThreshold=true` → `false` (crossing downward)

---

## Inter-Beat Interval (IBI) Calculation

**IBI Formula:**
```cpp
unsigned long ibi = millis() - sensor.lastBeatTime;  // milliseconds
unsigned long bpm = 60000 / ibi;                      // beats per minute
```

**Example:**
- IBI = 847ms → BPM = 60000/847 = 70.8 BPM
- IBI = 800ms → BPM = 60000/800 = 75 BPM
- IBI = 600ms → BPM = 60000/600 = 100 BPM

**Refractory Period Limits:**
- Minimum IBI: 300ms (refractory period) = 200 BPM maximum
- Physical maximum: ~200 BPM (elite athletes during intense exercise)
- Typical range: 60-100 BPM at rest

---

## OSC Transmission

**Called on Valid Beat:**
```cpp
sendHeartbeatOSC((int)ibi);
```

**Message Format:**
- Address: `/heartbeat/{SENSOR_ID}`
- Data: IBI in milliseconds (real heartbeat data, not test values)

**Phase 1 Difference:**
- Phase 1: Periodic 1Hz test messages with fixed 1000ms values
- Phase 2: Event-driven messages with real IBI from heartbeat detection

---

## LED Pulse Trigger

**On Valid Beat:**
```cpp
ledPulseTime = millis();  // Trigger 50ms pulse in updateLED()
```

Used to provide visual feedback of detected heartbeats.

---

## Integration in Main Loop

```cpp
void loop() {
    // ... ADC sampling, moving average, baseline, disconnection ...

    detectBeat();  // Detect heartbeats on smoothed signal

    // ... LED update ...
}
```

**Called every 20ms (once per sample interval):**
- Processes smoothed ADC value
- Detects rising/falling edges
- Calculates IBI on valid beats
- Transmits OSC with real data

---

## Tuning for Different Conditions

**Symptom: Missed Beats**
- Problem: Threshold too high for weak signals
- Solution: Reduce `THRESHOLD_FRACTION` (0.6 → 0.5)
- Verify: Baseline min/max values in debug output

**Symptom: False Beats (extra detections)**
- Problem: Threshold too low, noise triggers beats
- Solution: Increase `THRESHOLD_FRACTION` (0.6 → 0.7)
- Verify: No detections when finger removed

**Symptom: Double Beats (two detections per heartbeat)**
- Problem: Refractory period too short
- Solution: Increase `REFRACTORY_PERIOD_MS` (300ms → 350ms)
- Verify: Only one OSC message per heartbeat

**Symptom: BPM Inaccurate**
- Problem: Poor sensor contact or movement
- Solution: Improve physical sensor placement, hold still
- Verify: Compare to smartphone app simultaneously

---

## Related Documentation

- **[Configuration](configuration.md)** - Detection parameters and thresholds
- **[Signal Processing API](api-signal-processing.md)** - Baseline calculation for threshold
- **[Messaging API](api-messaging.md)** - OSC transmission
- **[Status API](api-status.md)** - LED pulse trigger
- **[Operations](operations.md)** - Troubleshooting and tuning guide

---

## Debug Output Example

**Serial Output on Beat:**
```
First beat detected
Beat detected, IBI=847ms, BPM=70
Beat detected, IBI=856ms, BPM=70
Beat detected, IBI=843ms, BPM=71
```

**Debug Output (Level 1):**
```
Smoothed: 2456 Min: 1500 Max: 3100 Threshold: 2460
Smoothed: 2498 Min: 1500 Max: 3100 Threshold: 2460
Smoothed: 2876 Min: 1500 Max: 3100 Threshold: 2460  ← Crosses threshold
Smoothed: 3001 Min: 1500 Max: 3100 Threshold: 2460  ← Above threshold
Smoothed: 2689 Min: 1500 Max: 3100 Threshold: 2460
Smoothed: 2234 Min: 1500 Max: 3100 Threshold: 2460  ← Falls below threshold
```
