# Beat Timing Fix - Future Timestamp Prediction

## Problem

Beat playback sounds jerky with inconsistent timing despite steady BPM reports.

**Root cause**: Predictor runs at 50Hz (20ms update interval), creating temporal quantization.
When IBI doesn't divide evenly by 20ms, beats alternate between too short and too long:

```
At 82 BPM (730ms IBI):
- Short beat: 31 updates × 20ms = 620ms
- Long beat:  41 updates × 20ms = 820ms
- Average:    720ms (correct, but sounds terrible)
```

## Current Behavior

Predictor emits beats when `phase >= 1.0` with `timestamp = time.time()` at the moment of detection.
This creates 20ms quantization in beat timing.

## Solution Overview

**Predictor**: Emit beats BEFORE phase reaches 1.0, with future timestamp predicting when
phase will cross 1.0. Use dynamic threshold to provide constant lookahead time regardless of BPM.

**Audio engine**: Convert Unix timestamp to rtmixer stream time and schedule playback.

**Lighting**: Accept future timestamps, compensate for device latency (configurable per-device).

**Viewer/Launchpad**: Accept future timestamps, react immediately (timing not critical).

## Detailed Design

### 1. Predictor - Dynamic Threshold for Constant Lookahead

**Problem**: Fixed threshold (e.g., 0.95) gives different lookahead times at different BPMs:
- 60 BPM (1000ms IBI): 0.95 threshold → 50ms lookahead
- 120 BPM (500ms IBI): 0.95 threshold → 25ms lookahead
- 150 BPM (400ms IBI): 0.95 threshold → 20ms lookahead

**Solution**: Calculate threshold dynamically to maintain constant lookahead:

```python
# New constant at top of predictor.py:
BEAT_PREDICTION_LOOKAHEAD_MS = 150  # Lookahead buffer (accounts for occasional ~100ms update delays)

# In update() method, calculate dynamic threshold:
lookahead_threshold = 1.0 - (BEAT_PREDICTION_LOOKAHEAD_MS / self.ibi_estimate_ms)

# Emit when phase crosses threshold:
if (self.phase >= lookahead_threshold and
    not self.beat_emitted_this_cycle and
    self.confidence > CONFIDENCE_EMISSION_MIN):

    # Calculate exact future timestamp when phase will cross 1.0
    phase_remaining = max(0.0, 1.0 - self.phase)
    time_until_beat_ms = phase_remaining * self.ibi_estimate_ms
    future_timestamp = timestamp_s + (time_until_beat_ms / 1000.0)

    beat_message = self._emit_beat(future_timestamp)
    self.beat_emitted_this_cycle = True
```

**Duplicate Prevention**: Add `beat_emitted_this_cycle` flag to __init__, set True on emission,
reset to False when phase wraps past 1.0.

**Edge Cases**:
- **Phase skips threshold** (0.90 → 1.10): Emits with `phase_remaining=0` (immediate playback)
- **Very high BPM** (threshold < 0.0): Clamp to emit at phase=1.0 (degrade to current behavior)
- **Observation during prediction window**: Small timing error acceptable (self-correcting)

**Update Loop Delay Issue**:
Testing revealed that the 50Hz update loop is occasionally delayed by ~100ms (cause unknown -
could be OS scheduler, Python GC, I/O blocking, or lock contention). When this happens, phase
advances from below threshold (0.85) to well past it (0.99) in a single update, leaving only
0.6-0.8ms lookahead instead of the expected 100ms. This causes audible timing jitter.

The fix: increase lookahead from 100ms to 150ms. This provides a 50ms buffer for delays:
- Normal updates (20ms): Detect at phase ~0.82, emit with ~130ms lookahead ✓
- Delayed update (100ms): Detect at phase ~0.94, emit with ~50ms lookahead ✓ (acceptable)
- Extreme delay (>150ms): Degrade to immediate playback (rare edge case)

**Important**: We cannot "backdate" timestamps when phase overshoots - phase represents our
best prediction of beat timing, and if phase=0.999, the beat truly is 0.8ms away. Emitting
with a fabricated future timestamp would desynchronize from the rhythm model.

### 2. Audio Engine - Unix Time to Stream Time Conversion

**CRITICAL CORRECTION**: rtmixer's `start` parameter uses **stream time in seconds** (from PortAudio's
Pa_GetStreamTime), NOT frame counts. The start parameter must be in the same time domain as `mixer.time`.

```python
# WRONG (from original doc):
# frames_until_beat = (timestamp - time.time()) × sample_rate
# mixer.play_buffer(stereo_sample, channels=2, start=frames_until_beat)

# CORRECT:
def handle_beat_message(self, ppg_id, timestamp, bpm, intensity):
    # ... existing validation and sample preparation ...

    # Convert Unix timestamp to rtmixer stream time
    current_stream_time = self.mixer.time       # PortAudio stream time (seconds)
    current_unix_time = time.time()             # Unix time (seconds)
    time_until_beat = timestamp - current_unix_time  # How long until beat (seconds)
    target_stream_time = current_stream_time + time_until_beat  # Target in stream domain

    # Schedule playback at future stream time
    self.mixer.play_buffer(
        stereo_sample,
        channels=2,
        start=target_stream_time,
        allow_belated=True  # Play immediately if timing can't be met
    )
```

**Timing Notes**:
- PortAudio stream time is monotonic with unspecified origin (only deltas matter)
- ~1ms localhost UDP latency reduces effective lookahead slightly (acceptable)
- rtmixer rounds to nearest audio sample (~0.023ms at 44.1kHz)
- `allow_belated=True` handles edge case of past timestamps gracefully

### 3. Lighting Controller - Latency Compensation

**Accept future timestamps and compensate for device latency**:

```python
# In lighting.py __init__:
self.device_latency_ms = 80  # Global config, tune to slowest device

# Update timestamp validation to accept future timestamps:
def validate_timestamp(self, timestamp_ms):
    """Validate timestamp - allow future timestamps within reasonable window."""
    now_ms = time.time() * 1000.0
    age_ms = now_ms - timestamp_ms

    # Allow future timestamps up to 200ms ahead (generous prediction window)
    # Reject past timestamps older than 500ms (stale)
    is_valid = (-200.0 <= age_ms < self.TIMESTAMP_THRESHOLD_MS)
    return is_valid, age_ms

# In handle_beat_message:
def handle_beat_message(self, ppg_id, timestamp_ms, bpm, intensity):
    # ... existing validation ...

    # Calculate when to send lighting command
    timestamp_s = timestamp_ms / 1000.0
    time_until_beat_ms = (timestamp_s - time.time()) * 1000.0
    delay_ms = time_until_beat_ms - self.device_latency_ms

    if delay_ms < 0:
        print(f"WARNING: Late beat prediction (needed {-delay_ms:.0f}ms ago), "
              f"sending immediately - PPG {ppg_id}")
    elif delay_ms > 0:
        time.sleep(delay_ms / 1000.0)

    # Call program's on_beat handler
    # ... existing program execution ...
```

**Future Enhancement**: Per-device latency configuration when needed.

### 4. Viewer and Launchpad - Accept Future Timestamps

**Changes**: Update timestamp validation to accept future timestamps (similar to lighting).
**Behavior**: React immediately - sub-frame timing not critical for visualization.

```python
# Similar validation update in viewer.py and launchpad.py:
# Accept future timestamps up to 200ms ahead
```

### 5. Processor - No Changes Required

The processor already passes through timestamps unchanged:
```python
# Line 456 in processor.py:
timestamp_ms = int(timestamp * 1000)
self.beats_client.send_message(f"/beat/{ppg_id}", msg_data)
```

When predictor emits future timestamp, processor broadcasts it directly.

## Implementation Order

1. **Predictor** - Dynamic threshold, future timestamps, duplicate prevention
2. **Audio** - Stream time conversion, scheduled playback
3. **Lighting** - Validation update, latency compensation
4. **Viewer/Launchpad** - Validation updates only
5. **Re-enable phase correction** - Restore PHASE_CORRECTION_WEIGHT from 0.0 to 0.05
6. **Test** - Verify timing, no duplicates, proper compensation

## Testing Strategy

1. **Simulated beats** - Inject test beats at known BPMs, verify timing precision
2. **Duplicate detection** - Monitor for duplicate emissions during phase wrap
3. **Edge cases** - Test very slow (40 BPM) and very fast (180 BPM) rates
4. **Latency measurement** - Measure actual smart light latency, update config
5. **Phase correction interaction** - Verify predictions remain stable with observations

## Benefits

- Eliminates 20ms quantization jitter
- Constant 100ms lookahead regardless of BPM
- Audio compensates for ~11ms buffer latency via scheduling
- Lighting compensates for device-specific latency (50-150ms typical)
- Predictor truly predicts future beats (lives up to its name)
- All components work with future timestamps consistently

## Phase Correction Status

Phase correction weight reduced from 0.10 to 0.0 (disabled) during debugging.
**Restore to 0.05 after timing fix is complete and tested.**

## Configuration Parameters

```python
# predictor.py
BEAT_PREDICTION_LOOKAHEAD_MS = 150  # Lookahead buffer (accounts for occasional ~100ms update delays)

# lighting.py (or config file)
device_latency_ms = 80  # Measured per-device, start with global value
```

## Notes

- All beat consumers listen on PORT_BEATS (8001) via SO_REUSEPORT
- Consumers: audio engine, lighting controller, viewer, launchpad LED effects
- All consumers must handle future timestamps after this fix
- ~1ms localhost UDP latency is negligible compared to 100ms lookahead window
