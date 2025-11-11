# Audio Engine Architecture: rtmixer Approach

**Date:** 2025-11-11
**Status:** Proposed for next iteration

---

## Current Implementation Limitation

The initial audio engine implementation (amor/audio.py) uses `sounddevice.OutputStream` with `.write()` for playback. This approach has a critical limitation:

**Problem:** `OutputStream.write()` queues audio data sequentially within each stream. When multiple beats from the same PPG arrive before the previous sample finishes playing (e.g., 100 BPM with samples that have 5-10 second sustain like tubular bells), subsequent beats are queued instead of overlapping.

**Impact:** Long sustain samples (tubular bells, gongs, singing bowls) don't overlap properly - you hear 1 second of sound followed by 9 seconds of silence as queued beats wait.

---

## Proposed Solution: python-rtmixer

### Why rtmixer?

**python-rtmixer** (https://python-rtmixer.readthedocs.io/) is designed specifically for "reliable low-latency audio playback" with concurrent buffer mixing.

**Key advantages:**
1. **True concurrent mixing** - Multiple buffers play simultaneously without queueing
2. **Low latency** - C-based lock-free callback architecture
3. **Action-based API** - Queue playback, track active buffers, cancel if needed
4. **Built on PortAudio** - Same backend as sounddevice (already in use)
5. **Actively maintained** - Last updated 2024

### Architecture: Separation of Concerns

```
Beat OSC message arrives
    ↓
Load mono sample (from pre-loaded samples)
    ↓
Pan mono → stereo using numpy (constant-power pan law)
    ↓
rtmixer.play_buffer(stereo_data, channels=2)
    ↓
rtmixer mixes all concurrent stereo buffers in C callback
    ↓
Stereo audio output
```

**Division of responsibility:**
- **rtmixer:** Low-latency concurrent mixing (the hard part)
- **Our code:** Mono → stereo panning (trivial numpy operations)

### Stereo Panning Implementation

Although rtmixer explicitly doesn't support panning, we handle it before sending to the mixer:

```python
def pan_mono_to_stereo(mono_data, pan):
    """
    Convert mono PCM to stereo with constant-power panning.

    Args:
        mono_data: 1D numpy array (mono samples)
        pan: -1.0 (hard left) to 1.0 (hard right)

    Returns:
        2D numpy array shape (samples, 2) for stereo
    """
    angle = (pan + 1.0) * np.pi / 4.0
    left_gain = np.cos(angle)
    right_gain = np.sin(angle)

    stereo = np.zeros((len(mono_data), 2), dtype=np.float32)
    stereo[:, 0] = mono_data * left_gain   # Left channel
    stereo[:, 1] = mono_data * right_gain  # Right channel

    return stereo
```

**Pan positions for 4 PPGs:**
```python
ppg_pans = {
    0: -1.0,   # Person 1: Hard left
    1: -0.33,  # Person 2: Center-left
    2: 0.33,   # Person 3: Center-right
    3: 1.0     # Person 4: Hard right
}
```

**Performance:** Panning a 1-second mono sample to stereo takes ~10 microseconds. Negligible CPU overhead even with 40+ overlapping voices.

### Benefits Over Current Implementation

| Feature | Current (OutputStream.write) | Proposed (rtmixer) |
|---------|------------------------------|---------------------|
| Same-PPG overlapping | ✗ Queues sequentially | ✓ True concurrent playback |
| Different-PPG mixing | ✓ Works | ✓ Works |
| Long sustain samples | ✗ Broken (queueing) | ✓ Full overlapping |
| Stereo panning | ✗ Hardcoded mono | ✓ Per-PPG stereo positioning |
| Latency | ~11ms | <15ms (comparable) |
| Complexity | Medium | Low (library handles mixing) |

### Spatial Audio Design

With stereo panning, four heartbeats are spatially separated across the stereo field:

```
Left                    Center                   Right
│                         │                         │
PPG 0                 PPG 1   PPG 2             PPG 3
(person 1)          (person 2) (person 3)     (person 4)
```

**Artistic benefits:**
- Four tubular bells ringing simultaneously are distinguishable (not muddy soup)
- Listener can focus attention on individual heartbeats
- Creates sense of "four bodies in space"
- Long overlapping sustains remain clear and separated

---

## Implementation Notes

### Dependencies

```bash
pip install python-rtmixer soundfile numpy python-osc
```

### Sample Format

- **Store as mono WAV files** (44.1kHz, 16-bit)
- Pan to stereo on-the-fly (more flexible, half the storage)
- rtmixer requires `float32` dtype (convert with `.astype(np.float32)`)

### rtmixer API

```python
# Initialize stereo mixer
mixer = rtmixer.Mixer(channels=2, samplerate=44100, blocksize=512)
mixer.start()

# On each beat:
stereo_sample = pan_mono_to_stereo(mono_samples[ppg_id], ppg_pans[ppg_id])
action = mixer.play_buffer(stereo_sample, channels=2)

# Action object can be used to cancel playback if needed
# mixer.cancel(action)
```

### Future Enhancements

With this architecture, dynamic audio features become trivial:

1. **BPM-responsive panning:**
   ```python
   pan = ppg_pans[ppg_id] + (bpm - 80) * 0.01  # Pan moves with heart rate
   ```

2. **Intensity-based volume:**
   ```python
   stereo_sample *= intensity  # Louder for stronger heartbeat
   ```

3. **Configurable pan positions:**
   ```python
   # Load from config file, adjust at runtime
   ```

---

## Migration Path

1. Keep current implementation for basic functionality testing
2. Implement rtmixer version on new branch
3. Verify concurrent playback with long sustain samples
4. Test with actual tubular bell/gong samples (5-10s sustain)
5. Replace current implementation once verified

---

## References

- **python-rtmixer:** https://python-rtmixer.readthedocs.io/
- **GitHub:** https://github.com/spatialaudio/python-rtmixer
- **Technical Reference:** docs/firmware/amor-technical-reference.md (Section 3)
- **Current Implementation:** amor/audio.py

---

**Next steps:** Merge current implementation, open fresh branch for rtmixer refactor.
