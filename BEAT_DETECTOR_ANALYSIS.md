# Beat Detector Problems - Root Cause Analysis

## TL;DR

The firmware power management changes (commit 93573fa, Nov 12) introduced **sample timing jitter** that breaks the beat predictor's phase tracking. The aggressive use of light sleep (threshold lowered from 5ms to 1ms) causes variable wake times, and the firmware's timing implementation propagates this jitter instead of correcting it.

## Timeline

1. **Nov 12**: Firmware power management changes (93573fa)
   - Added light sleep to ACTIVE state
   - Changed from stddev to MAD for signal quality
   - Lowered light sleep threshold from 5ms to 1ms

2. **Nov 13**: Beat timing error noted (86aef67)
   - Documented 20ms quantization jitter in predictor

3. **Nov 14**: Beat predictor autonomous emission fix (f044e93)
   - Attempted to fix quantization with background threading
   - **BUT** this fix assumes samples arrive at consistent 20ms intervals

## The Problem

### Firmware Timing Implementation (BROKEN)

```cpp
// In activeStateLoop():
unsigned long nextSampleTime = lastSampleTime + SAMPLE_INTERVAL_MS;  // +20ms
if (currentTime < nextSampleTime) {
    unsigned long sleepTimeMs = nextSampleTime - currentTime;
    if (sleepTimeMs > 1) {  // CHANGED FROM 5ms to 1ms - MORE AGGRESSIVE
        esp_light_sleep_start();  // Variable wake time!
    }
}

// In samplePPG():
if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = currentTime;  // PROPAGATES JITTER
    // take sample
}
```

### Why This Breaks Beat Detection

1. **Light Sleep Jitter**
   - ESP32 light sleep has variable wake times (±1-3ms typical)
   - Firmware now uses light sleep for ANY wait >1ms (was >5ms)
   - More aggressive sleep = more opportunities for jitter

2. **Jitter Propagation**
   - `lastSampleTime = currentTime` locks in whatever time the loop wakes up
   - Instead of maintaining a fixed 20ms grid, timing drifts
   - Expected: 0, 20, 40, 60, 80, 100ms
   - Actual: 0, 21, 42, 62, 84, 106ms (jitter compounds)

3. **Phase Tracking Failure**
   - Beat predictor assumes samples arrive at 50Hz (20ms intervals)
   - Predictor advances phase by: `phase += time_delta_ms / ibi_estimate_ms`
   - Irregular intervals cause phase drift
   - Confidence degrades, beats become erratic

4. **Autonomous Emission Makes It Worse**
   - New predictor (f044e93) emits beats via background thread
   - Thread uses system time: `next_beat_time = last_beat_time + (ibi_ms / 1000.0)`
   - But phase updates use ESP32 timestamps with jitter
   - **CLOCK DOMAIN INTERACTION**: System time (steady) vs ESP32 time (jittery)

## Evidence

### From firmware code (main.cpp:773-794):
```cpp
if (sleepTimeMs > 1) {  // VERY AGGRESSIVE - was 5ms
    unsigned long sleepStart = millis();
    esp_light_sleep_start();
    unsigned long actualSleep = millis() - sleepStart;

    if (actualSleep < sleepTimeMs - 2) {  // 2ms tolerance
        Serial.print("WARNING: ACTIVE sleep short, only ");
        delay(sleepTimeMs - actualSleep);  // Try to compensate
    }
}
```

The compensation happens AFTER the jitter, which means:
- Loop wakes at t=21ms (1ms late)
- Detects short sleep, delays to compensate
- But samplePPG() still sees currentTime=21ms+ and sets lastSampleTime=21ms+
- Jitter is locked in

### From predictor (predictor.py:230-232):
```python
# Advance phase
time_delta_ms = time_delta_s * 1000.0
phase_increment = time_delta_ms / self.ibi_estimate_ms
self.phase += phase_increment
```

With jittery time_delta_ms values (19ms, 21ms, 20ms, 22ms instead of consistent 20ms), phase tracking becomes unreliable.

### From beat timing doc (beat-timing-fix.md):
> Beat playback sounds jerky with inconsistent timing despite steady BPM reports.

This was attributed to 20ms quantization, but the firmware jitter makes it worse.

## Why stddev→MAD Change Matters

Secondary issue: The signal quality metric changed from standard deviation to MAD (Median Absolute Deviation). This is orthogonal to the timing issue but causes different sensors to be activated:

- Old: stddev threshold 70/100
- New: MAD threshold 40/40

MAD is more robust to outliers but may allow weaker signals through, which combined with timing jitter causes more "acquire/lose lock" cycling.

## Root Causes

1. **Primary**: Light sleep timing jitter accumulation due to `lastSampleTime = currentTime`
2. **Secondary**: Lower sleep threshold (1ms vs 5ms) causes more sleep/wake cycles
3. **Interaction**: New autonomous predictor expects steady sample timing but gets jitter

## Solutions

### Option 1: Fix Firmware Timing (RECOMMENDED)

Change sample timing to maintain a fixed grid:

```cpp
// Initialize once at startup:
unsigned long sampleGridBase = millis();
unsigned long sampleCount = 0;

// In samplePPG():
unsigned long currentTime = millis();
unsigned long nextScheduledSample = sampleGridBase + (sampleCount * SAMPLE_INTERVAL_MS);

if (currentTime >= nextScheduledSample) {
    lastSampleTime = nextScheduledSample;  // Fixed grid, not actual time
    sampleCount++;
    // take sample
}
```

This maintains 20ms intervals regardless of light sleep jitter.

### Option 2: Increase Sleep Threshold

Revert to 5ms threshold to reduce sleep cycles:

```cpp
if (sleepTimeMs > 5) {  // Was 1ms
```

Less aggressive sleeping = less jitter, but less power savings.

### Option 3: Use Delay Instead of Light Sleep in ACTIVE

Only use light sleep in IDLE state, use regular delay() in ACTIVE:

```cpp
if (sleepTimeMs > 1) {
    delay(sleepTimeMs);  // Precise but burns more power
}
```

### Option 4: Predictor Jitter Compensation

Make predictor robust to timing jitter by:
- Smoothing time_delta values
- Detecting and compensating for irregular intervals
- Relaxing phase correction constraints

This is less ideal because it treats symptoms, not the root cause.

## Recommended Fix

**Implement Option 1** (fixed sample grid) because:
1. Maintains power savings from light sleep
2. Provides consistent 20ms intervals regardless of wake jitter
3. No changes needed to predictor code
4. Aligns with predictor's assumptions

The sample timestamps sent over OSC will be on a perfect 20ms grid, making phase tracking reliable.

## Testing Plan

1. Flash firmware with fixed timing
2. Monitor serial output for "WARNING: Sleep short" messages
3. Verify sample timestamps are exactly 20ms apart
4. Test beat predictor lock acquisition and stability
5. Measure power consumption to ensure savings maintained

## Impact Assessment

- **Severity**: HIGH - breaks core beat detection functionality
- **Affected Systems**: All 4 PPG sensors running power management firmware
- **User Impact**: Erratic beats, frequent acquire/release cycles, poor rhythm tracking
- **Power Impact**: Fix maintains power savings while restoring timing
