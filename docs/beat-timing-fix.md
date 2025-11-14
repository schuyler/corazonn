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

## Solution

**Predictor**: Emit beats slightly BEFORE phase reaches 1.0, with future timestamp predicting when
phase will cross 1.0:

```python
# When phase > 0.95 (one update before crossing):
time_until_crossing = (1.0 - phase) × ibi_estimate
future_timestamp = time.time() + time_until_crossing
```

**Audio engine**: Use rtmixer's `start` parameter to schedule playback at the predicted timestamp:

```python
# Calculate frames until beat time
frames_until_beat = (timestamp - time.time()) × sample_rate
mixer.play_buffer(stereo_sample, channels=2, start=frames_until_beat)
```

## Components Requiring Changes

1. **amor/predictor.py** - HeartbeatPredictor.update()
   - Emit beat when phase > threshold (e.g., 0.95)
   - Calculate future timestamp when phase will cross 1.0
   - Sub-millisecond precision via interpolation

2. **amor/audio.py** - AudioEngine.handle_beat_message()
   - Accept future timestamps (already validates as OK)
   - Convert timestamp to rtmixer frame count
   - Use `mixer.play_buffer(buffer, channels, start=frames)`

## Benefits

- Eliminates 20ms quantization jitter
- Allows audio system to compensate for ~11ms buffer latency
- Other components (lighting, launchpad LEDs) can schedule their own latency compensation
- Predictor does what its name implies: predicts future beats

## Phase Correction Status

Phase correction weight reduced from 0.10 to 0.0 (disabled) during debugging.
Should restore to 0.05 after timing fix is complete and tested.

## Notes

- All beat consumers listen on PORT_BEATS (8001) via SO_REUSEPORT
- Consumers: audio engine, lighting controller, viewer, launchpad LED effects
- Only audio engine currently needs modification for scheduling
- Other components can continue immediate reaction or add their own scheduling later
