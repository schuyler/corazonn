# Heartbeat Synthesis Prototype

## Overview

This prototype demonstrates real-time heartbeat synthesis that masks PPG sensor clipping. The synthesis is driven only by beat timing (BPM + intensity), making it immune to raw signal clipping artifacts.

## Generated Files

Four preset variations have been generated for evaluation:

- **heartbeat_natural.wav** - Realistic heartbeat with noise and variation
- **heartbeat_electronic.wav** - Clean, synthetic sound (pure sine waves)
- **heartbeat_sub-bass.wav** - Deep, bass-heavy heartbeat
- **heartbeat_percussive.wav** - Sharp, rhythmic sound with high noise content

All files: 10 seconds duration, 72 BPM (±10% variation), 48kHz sample rate

## Usage

### Generate Custom Audio

```bash
# Basic usage (natural preset, 20s duration, 70 BPM)
python3 audio/prototype_heartbeat_synth.py

# Custom parameters
python3 audio/prototype_heartbeat_synth.py --duration 30 --bpm 85 --preset sub-bass

# All options
python3 audio/prototype_heartbeat_synth.py \
    --duration 60 \
    --bpm 90 \
    --preset percussive \
    --sample-rate 48000 \
    --output my_heartbeat.wav
```

### Available Presets

| Preset | S1 Freq | S2 Freq | Noise Mix | Character |
|--------|---------|---------|-----------|-----------|
| **natural** | 75 Hz | 150 Hz | 30% | Realistic, organic variation |
| **electronic** | 60 Hz | 120 Hz | 0% | Clean, synthetic, pure tones |
| **sub-bass** | 45 Hz | 90 Hz | 10% | Deep, resonant, felt more than heard |
| **percussive** | 100 Hz | 200 Hz | 60% | Sharp, rhythmic, drum-like |

## How It Works

### Synthesis Approach

Each heartbeat consists of two sounds:
1. **S1 ("lub")** - First heart sound (mitral/tricuspid valve closure)
2. **S2 ("dub")** - Second heart sound (aortic/pulmonary valve closure)

Both sounds are synthesized using:
- **Bandpassed noise** (turbulent blood flow)
- **Sine wave** (resonant frequencies)
- **Exponential decay envelope** (natural damping)
- **Sharp attack** (percussive onset)

### Parameters from Beat Events

- **BPM** → Controls S1-S2 timing (S2 at ~35% of inter-beat interval)
- **Intensity** → Controls amplitude and noise content
- **Variation** → Randomizes timing (±10ms) and pitch (±5%) for realism

### Clipping Immunity

The synthesis uses **only beat timing** from the detector, not raw PPG amplitude:
- Beat detector works despite clipping (threshold crossings still occur)
- No PPG waveform shape information used
- Clipping artifacts completely masked

## Preset Characteristics

### Natural
Best for realistic heartbeat simulation. Uses 30% noise mixed with sine waves, includes timing/pitch variation to mimic biological variability. S1 at 75 Hz (chest resonance), S2 at 150 Hz (higher valve).

**Use case:** General soundscape integration, ambient background

### Electronic
Pure sine waves, no variation. Clean and synthetic. Lower frequencies (60/120 Hz) for smooth, tonal quality.

**Use case:** Minimal, electronic music context, precise rhythm

### Sub-Bass
Emphasizes low frequencies (45/90 Hz) with longer duration. Felt physically more than heard. 10% noise for texture.

**Use case:** Immersive installations, body-resonance effects

### Percussive
Short duration (50ms S1, 40ms S2), high noise content (60%), higher frequencies (100/200 Hz). Sharp, drum-like quality.

**Use case:** Rhythmic emphasis, beat-driven soundscapes

## Next Steps

### Listen and Evaluate

1. Play each preset WAV file
2. Consider which fits your soundscape aesthetic
3. Note any parameter adjustments needed

### Integration Path

Once satisfied with the prototype:

1. Extract synthesis engine to `amor/heartbeat_synth.py`
2. Integrate with `amor/audio.py` playback system
3. Add OSC control for enable/disable per channel
4. Support preset switching in real-time

### Potential Enhancements

- **Real PPG data testing** - Feed actual captured PPG through beat detector
- **Additional presets** - "woody", "metallic", "breathy" variations
- **Dynamic parameters** - BPM → more aggressive sound at high heart rates
- **Effects routing** - Reverb/delay integration with existing effects chain
- **Per-channel presets** - Different sounds for different PPG channels

## Technical Details

### File Structure

```
audio/
├── prototype_heartbeat_synth.py    # Main script
├── heartbeat_natural.wav           # Generated preset samples
├── heartbeat_electronic.wav
├── heartbeat_sub-bass.wav
├── heartbeat_percussive.wav
└── HEARTBEAT_PROTOTYPE_README.md   # This file
```

### Dependencies

- **numpy** - Array operations, signal generation
- **scipy** - Bandpass filtering
- **soundfile** - WAV file I/O

### Synthesis Parameters

Each preset defines:
- `s1_freq`, `s1_duration` - S1 synthesis parameters
- `s2_freq`, `s2_duration` - S2 synthesis parameters
- `s2_delay_ratio` - S2 timing as fraction of IBI
- `noise_mix` - 0-1, noise vs sine content
- `variation_ms` - Timing randomization
- `pitch_variation` - Frequency randomization

## Questions?

Refine parameters, try different approaches, or proceed with integration based on your assessment of these prototypes.
