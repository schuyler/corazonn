# Audio Processing

Quick reference for audio-rate operations in Pure Data.

## Convert Control to Audio Rate

```
[r control-value]
|
[sig~]  # Converts to constant audio signal
|
[*~ some-audio-signal]
```

**Example**: Scaling a phasor by sample length.

## Convert Audio to Control Rate

```
[r~ audio-signal]
|
[snapshot~]  # Samples at control rate
|
[print VALUE]
```

**Trigger**: `[snapshot~]` outputs when it receives a bang in left inlet.

## Apply Envelope

```
[r trigger]
|
[1 5, 0 50(  # Attack 5ms, release 50ms
|
[vline~]
|
[*~ audio-signal]
```

**`[vline~]` vs `[line~]`**:
- `[vline~]`: Sample-accurate timing, better for envelopes
- `[line~]`: Block-accurate timing, fine for most uses

## Implement Fade In/Out

```
[r fade-trigger]
|
[0 2000(  # Fade to 0 over 2000ms
|
[line~]
|
[*~ audio-signal]
```

**For reconnection fading**: See project-patterns.md "Disconnection Detection and Fade-Out".

## Pan Audio to Stereo

```
[r~ mono-audio]
|
[t a a]
|    |
|    [expr sin(PAN*1.5708)]  # Right
|    |
|    [*~]
|
[expr cos(PAN*1.5708)]       # Left
|
[*~]
```

**PAN values**: 0.0 = left, 0.5 = center, 1.0 = right

**Constant power**: Ensures equal loudness at all pan positions.

---

**Related documentation**:
- See common-tasks-sample-playback.md for envelope message formats
- See common-tasks-message-routing.md for trigger patterns
