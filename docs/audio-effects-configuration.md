# Audio Effects Configuration Guide

Real-time biometric-responsive audio effects for the Amor audio engine. Effects process mono samples before panning, with parameters dynamically controlled by heartbeat data (BPM, intensity).

## Quick Start

### 1. Install Dependencies

```bash
pip install pedalboard  # Required for effects
# or
uv pip install -e ".[audio]"  # Includes pedalboard
```

### 2. Enable Effects

Edit `amor/config/samples.yaml`:

```yaml
audio_effects:
  enable: true  # Change from false
```

### 3. Run Audio Engine

```bash
python -m amor.audio
```

Effects will be loaded at startup. Check console for confirmation:
```
Audio effects processor initialized
  PPG 0: 2 effect(s) loaded - DelayEffect, ReverbEffect
  PPG 1: 2 effect(s) loaded - ChorusEffect, LowPassFilterEffect
```

## Available Effects

### Reverb - Spatial Depth
Creates room ambience with BPM-responsive size.

```yaml
- type: reverb
  room_size:
    bpm_min: 60       # Resting heart rate
    bpm_max: 120      # Excited heart rate
    range: [0.5, 0.9] # Small room → cathedral
  damping: 0.5        # High frequency absorption (0.0-1.0)
  wet_level: 0.35     # Effect signal level
  dry_level: 0.65     # Original signal level
```

**BPM Mapping:** `room_size = linear_map(bpm, 60, 120, 0.5, 0.9)`

At rest (60 BPM) → small room. Excited (120 BPM) → cathedral space.

### Delay - BPM-Synced Echoes
Rhythmic echoes locked to heartbeat timing.

```yaml
- type: delay
  delay_seconds:
    bpm_sync: true      # Sync to heart rhythm
    subdivisions: 1.0   # 1.0=quarter, 0.5=eighth, 2.0=half note
  feedback: 0.3         # Echo repetition amount (0.0-1.0)
  mix: 0.25             # Dry/wet balance
```

**BPM Mapping:** `delay_seconds = (60 / bpm) * subdivisions`

At 60 BPM: 1.0 sec delay. At 90 BPM: 0.67 sec delay. Creates rhythmic space that breathes with the heart.

### Chorus - Gentle Shimmer
Subtle modulation that breathes with heart rate.

```yaml
- type: chorus
  rate_hz:
    bpm_sync: true      # Sync rate to heartbeat
    scale: 0.015        # Very slow: (bpm/60) * scale
  depth: 0.4            # Modulation depth (0.0-1.0)
  centre_delay_ms: 7.0  # Center delay time
  feedback: 0.0         # Feedback amount
  mix: 0.4              # Dry/wet balance
```

**BPM Mapping:** `rate_hz = (bpm / 60) * scale`

At 90 BPM with scale=0.015: ~0.022 Hz (45 second cycle). Organic shimmer without aggression.

### Phaser - Sweeping Filter
Notch filter with intensity-controlled rate.

```yaml
- type: phaser
  rate:
    base: 0.5           # Base LFO rate (Hz)
    intensity_scale: 1.5 # Multiplier for intensity
  depth: 0.8            # Sweep depth (0.0-1.0)
  feedback: 0.3         # Resonance amount
  mix: 0.4              # Dry/wet balance
```

**Intensity Mapping:** `rate_hz = base + (intensity * intensity_scale)`

Weak signal (intensity=0.3) = 0.95 Hz. Strong signal (intensity=0.8) = 1.7 Hz.

### LowPass Filter - Inverse Calming
Darkens sound as heart rate increases (soothing response).

```yaml
- type: lowpass
  cutoff_hz:
    bpm_min: 60
    bpm_max: 120
    range: [10000, 4000]  # Bright → warm (inverse!)
```

**Inverse BPM Mapping:** `cutoff_hz = linear_map(bpm, 60, 120, 10000, 4000)`

Resting (60 BPM) → 10kHz (bright). Excited (120 BPM) → 4kHz (warm/mellow). Installation soothes agitation.

## Per-PPG Configuration

Each PPG sensor (0-3) has an independent effect chain. Effects process serially: output of effect N feeds input of effect N+1.

### Example: Meditative Bells (PPG 0)

```yaml
ppg_effects:
  0:  # Tubular bells
    - type: delay          # First: rhythmic echoes
      delay_seconds:
        bpm_sync: true
        subdivisions: 1.0
      feedback: 0.3
      mix: 0.25
    - type: reverb         # Second: spatial depth
      room_size:
        bpm_min: 60
        bpm_max: 120
        range: [0.5, 0.9]
      damping: 0.5
      wet_level: 0.35
      dry_level: 0.65
```

Signal flow: Sample → Delay → Reverb → Pan → Speakers

### Example: Breathing Bowls (PPG 1)

```yaml
ppg_effects:
  1:  # Singing bowls
    - type: chorus         # Gentle shimmer
      rate_hz:
        bpm_sync: true
        scale: 0.015
      depth: 0.4
      mix: 0.4
    - type: lowpass        # Calming warmth
      cutoff_hz:
        bpm_min: 60
        bpm_max: 120
        range: [10000, 4000]
```

High heart rate triggers both shimmer and warmth for calming effect.

## Fixed vs Dynamic Parameters

### Fixed Parameters
Use a simple number for static behavior:

```yaml
- type: reverb
  room_size: 0.6  # Always medium room, no BPM mapping
  damping: 0.5
```

### Dynamic Parameters
Use mapping config for biometric control:

```yaml
- type: reverb
  room_size:
    bpm_min: 60
    bpm_max: 120
    range: [0.5, 0.9]  # Maps BPM to room size
```

Mix fixed and dynamic as needed.

## Troubleshooting

### "Audio effects unavailable"
```
INFO: Audio effects unavailable (install pedalboard to enable)
```

**Solution:** `pip install pedalboard>=0.9.0`

### "Audio effects disabled in config"
Effects are off. Edit `amor/config/samples.yaml`:

```yaml
audio_effects:
  enable: true  # Change this
```

### "WARNING: Unknown effect type"
Check effect name spelling in config. Available: `reverb`, `delay`, `chorus`, `phaser`, `lowpass`.

### Effects not audible
1. Check effect `mix` parameter (0.0 = no effect, 1.0 = full effect)
2. Verify BPM values are in expected range (40-180)
3. Check console for "BEAT PLAYED" messages with effect processing

### Performance issues
- Reduce effect chain length (max 3 effects recommended)
- Disable unused PPG effect chains (set to `[]`)
- Lower wet/mix levels to reduce processing

## Performance Notes

- **Processing overhead:** ~1-3ms per effect per beat
- **Graceful degradation:** Effects skip if processing fails, audio continues
- **Thread safety:** OSC messages processed serially, no race conditions
- **Memory:** Mono→stereo conversion happens per effect (minimal overhead)

## Configuration Tips

### Meditative Installations
- Use subtle mix levels (0.2-0.4)
- Prefer slow modulation (chorus scale < 0.02)
- Use inverse lowpass mapping for calming response
- Long delay subdivisions (2.0) for spacious rhythms

### Dynamic Installations
- Higher mix levels (0.5-0.7)
- Faster modulation (chorus scale > 0.05)
- Shorter delay subdivisions (0.5) for rhythmic energy
- Direct BPM mappings that amplify excitement

### Clean Transients
Percussive sounds (water drops, wood blocks) work well with minimal effects:

```yaml
ppg_effects:
  2:  # Water/wood/metal
    - type: reverb
      room_size: 0.4
      wet_level: 0.2  # Very subtle
```

## Reference

- **Code:** `amor/audio_effects.py` - Effect implementations
- **Integration:** `amor/audio.py` - AudioEngine integration
- **Config:** `amor/config/samples.yaml` - Full configuration examples
- **Architecture:** Similar to LightingProgram callback pattern
