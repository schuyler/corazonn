# API: Beat Detection Algorithm

Core beat detection with rising edge detection and refractory period.

---

## 6.4 Beat Detection

**Function:** `detectBeat()`

**Signature:**
```cpp
void detectBeat(int sensorIndex);
```

**Purpose:** Detect heartbeat pulses using rising edge threshold crossing with refractory period enforcement

**Parameters:**
- `sensorIndex`: Index 0-3 into sensors array

**Algorithm Overview:**

Beat detection uses:
1. **Dynamic threshold** — 60% of signal range (min to max)
2. **Rising edge detection** — Only trigger on transition from below to above threshold
3. **Refractory period** — Enforce minimum 300ms between beats (max 200 BPM)
4. **IBI calculation** — Calculate inter-beat interval time

**Requirements:**

**R15: Skip If Disconnected**
```cpp
if (!sensors[sensorIndex].isConnected) {
  return;  // Don't attempt detection on disconnected sensor
}
```
- Skip processing if sensor marked disconnected
- Prevents false beats on noise

**R16: Threshold Calculation**
```cpp
int threshold = sensors[sensorIndex].minValue +
  (sensors[sensorIndex].maxValue - sensors[sensorIndex].minValue) * THRESHOLD_FRACTION;
```
- Calculate as fraction of signal range above baseline
- Default: 60% of range
- Formula: `threshold = minValue + (range * 0.6)`
- Example: If minValue=2200, maxValue=2800, then range=600, threshold=2200+(600*0.6)=2560

**R17: Rising Edge Detection**
```cpp
bool currentlyAbove = (sensors[sensorIndex].smoothedValue >= threshold);

if (currentlyAbove && !sensors[sensorIndex].aboveThreshold) {
  // Rising edge detected
  // ... check refractory, calculate IBI ...
}

// Update state for next iteration
sensors[sensorIndex].aboveThreshold = currentlyAbove;
```
- Trigger only on transition from below to above
- Prevents double-triggering on single beat
- Falling edge (above→below) just updates state, no action

**R18: Refractory Period Check**
```cpp
unsigned long now = millis();
unsigned long timeSinceLastBeat = now - sensors[sensorIndex].lastBeatTime;

if (timeSinceLastBeat < REFRACTORY_PERIOD_MS) {
  return;  // Too soon after last beat, ignore
}
```
- Enforces minimum time between beats (300ms = max 200 BPM)
- Prevents noise from triggering false beats
- Also rate-limits OSC messages
- Configuration: `REFRACTORY_PERIOD_MS = 300`

**R19: IBI Calculation and OSC Transmission**
```cpp
// Calculate inter-beat interval
unsigned long ibi = now - sensors[sensorIndex].lastBeatTime;

if (sensors[sensorIndex].firstBeatDetected) {
  // Send OSC message with real IBI
  sendHeartbeatOSC(sensorIndex, (int)ibi);

  // Set flag for LED feedback
  system.beatDetectedThisLoop = true;

  #if DEBUG_LEVEL >= 1
    Serial.print("[");
    Serial.print(sensorIndex);
    Serial.print("] Beat at ");
    Serial.print(now);
    Serial.print("ms, IBI=");
    Serial.print(ibi);
    Serial.println("ms");
  #endif
} else {
  // First beat: just record time, don't send (no reference point)
  sensors[sensorIndex].firstBeatDetected = true;

  #if DEBUG_LEVEL >= 1
    Serial.print("[");
    Serial.print(sensorIndex);
    Serial.print("] First beat at ");
    Serial.print(now);
    Serial.println("ms (no message sent)");
  #endif
}

// Update beat tracking
sensors[sensorIndex].lastBeatTime = now;
sensors[sensorIndex].lastIBI = ibi;
```

**Requirements:**
- First beat after startup or reconnection: Record time only, no OSC sent
- Subsequent beats: Calculate IBI, send OSC message
- IBI is time since last beat on THIS sensor (independent per sensor)
- Set `beatDetectedThisLoop` for LED feedback

**Reconnection Behavior:**
After disconnection, `firstBeatDetected` remains true, so next beat will send OSC with potentially large IBI (accurate time since last beat before disconnect). This is intentional — provides true inter-beat interval.

**Timing:**
- Call once per sampling cycle (every 20ms)
- Decision logic: <5ms per sensor
- OSC transmission: ~10-15ms (non-blocking)

**Example Usage:**
```cpp
void loop() {
  static unsigned long lastSampleTime = 0;
  unsigned long currentTime = millis();

  if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = currentTime;

    system.beatDetectedThisLoop = false;

    for (int i = 0; i < NUM_SENSORS; i++) {
      readAndFilterSensor(i);     // Sample + filter
      updateBaseline(i);          // Update min/max
      detectBeat(i);              // Detect beats + send OSC
    }

    updateLED();  // LED responds to ANY sensor beat
  }
}
```

**Output Data:**
- `sensors[i].aboveThreshold` — Updated for next cycle
- `sensors[i].lastBeatTime` — Updated when beat detected
- `sensors[i].lastIBI` — Updated when beat detected
- `sensors[i].firstBeatDetected` — Set true after first beat
- `system.beatDetectedThisLoop` — Set true when beat detected

**State Transitions:**

```
TRACKING (below threshold)
  ↓
  Signal rises above threshold (rising edge)
  ↓
  Check refractory period
  ├─ Too soon → Ignore, stay TRACKING
  └─ OK → Calculate IBI
       ├─ First beat → Record time, set firstBeatDetected=true, stay TRACKING
       └─ Later beat → Send OSC, update lastBeatTime, stay TRACKING
  ↓
TRACKING (above threshold)
  ↓
  Signal falls below threshold (falling edge)
  ↓
  Just update state, stay TRACKING
```

**Debug Output:**
- Level 1: Beat detection events with timestamp and IBI
- Level 2: Threshold values, min/max range, beat detection details

---

## Related Documentation

- [Configuration](configuration.md) — Threshold fraction, refractory period, debug levels
- [API: Signal Processing](api-signal-processing.md) — Provides min/max values
- [API: Sensors](api-sensors.md) — Provides smoothed signal value
- [API: Messaging](api-messaging.md) — sendHeartbeatOSC() called from here
- [Implementation](implementation.md) — Function integration in main loop

---

**Next Step:** Implement OSC transmission with [API: Messaging](api-messaging.md)
