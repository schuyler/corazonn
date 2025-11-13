# Audio Configuration

Configuration file: `amor/config/samples.yaml`

## Audio Sample Organization

### Directory Structure

```
sounds/
├── ppg/              # PPG sensor samples (32 files)
│   ├── tubular_bell_C.wav
│   ├── singing_bowl_low.wav
│   ├── water_drop_1.wav
│   └── ...
└── loops/            # Ambient loops (32 files)
    ├── latching/     # Optional subdirectory
    └── momentary/    # Optional subdirectory
```

### Audio File Requirements

- **Format:** WAV
- **Channels:** Mono
- **Sample Rate:** 44.1kHz or 48kHz
- **Bit Depth:** 16-bit

## Configuration Sections

### Voice Limit

```yaml
voice_limit: 3
```

Maximum concurrent voices (reserved for future use).

### Global Acquisition Sample

```yaml
acquire_sample: sounds/ppg/acquire_ack.wav
```

Playback confirmation when rhythm is acquired.

### PPG Samples

Maps 4 PPG sensors to 8 samples each (32 total).

```yaml
ppg_samples:
  0:  # PPG 0 (panned hard left)
    - sounds/ppg/tubular_bell_C.wav
    - sounds/ppg/tubular_bell_D.wav
    - sounds/ppg/tubular_bell_E.wav
    - sounds/ppg/tubular_bell_F.wav
    - sounds/ppg/tubular_bell_G.wav
    - sounds/ppg/tubular_bell_A.wav
    - sounds/ppg/tubular_bell_B.wav
    - sounds/ppg/tubular_bell_C2.wav

  1:  # PPG 1 (panned center-left)
    - sounds/ppg/singing_bowl_low.wav
    # ... 7 more samples

  2:  # PPG 2 (panned center-right)
    - sounds/ppg/water_drop_1.wav
    # ... 7 more samples

  3:  # PPG 3 (panned hard right)
    - sounds/ppg/harmonic_1.wav
    # ... 7 more samples
```

**Note:** PPG IDs 4-7 inherit pan positions from 0-3 respectively.

### Ambient Loops

32 loops total: 16 latching (toggle on/off) + 16 momentary (press/release).

```yaml
ambient_loops:
  latching:   # Loops 0-15
    - sounds/loops/ambient_pad_1.wav
    - sounds/loops/ambient_pad_2.wav
    # ... 14 more loops

  momentary:  # Loops 16-31
    - sounds/loops/texture_1.wav
    - sounds/loops/texture_2.wav
    # ... 14 more loops
```

**Limits:**
- Max 6 concurrent latching loops
- Max 4 concurrent momentary loops

## Audio Effects Configuration

### Enable/Disable Effects

```yaml
audio_effects:
  enable: false  # Set to true to enable effects
```

### Effect Chains

Apply per-PPG effect chains:

```yaml
audio_effects:
  enable: true
  ppg_effects:
    0:  # Effects for PPG 0
      - type: delay
        delay_seconds: 0.3
        feedback: 0.3
        mix: 0.25

      - type: reverb
        room_size: 0.7
        damping: 0.5
        wet_level: 0.3
        dry_level: 1.0

    1:  # Effects for PPG 1
      - type: chorus
        rate_hz: 1.5
        depth: 0.3
        mix: 0.4
```

### Available Effect Types

#### Reverb

```yaml
type: reverb
room_size: 0.0-1.0     # Room dimensions
damping: 0.0-1.0       # High frequency absorption
wet_level: 0.0-1.0     # Effect signal level
dry_level: 0.0-1.0     # Original signal level
width: 0.0-1.0         # Stereo width (optional)
```

#### Delay

```yaml
type: delay
delay_seconds: 0.1-2.0  # Delay time
feedback: 0.0-0.99      # Feedback amount
mix: 0.0-1.0            # Wet/dry mix
```

#### Chorus

```yaml
type: chorus
rate_hz: 0.1-10.0      # LFO rate
depth: 0.0-1.0         # Modulation depth
centre_delay_ms: 7     # Base delay (optional)
feedback: -1.0-1.0     # Feedback (optional)
mix: 0.0-1.0           # Wet/dry mix
```

#### Phaser

```yaml
type: phaser
rate_hz: 0.1-10.0      # LFO rate
depth: 0.0-1.0         # Modulation depth
centre_frequency_hz: 1300  # Center frequency (optional)
feedback: -1.0-1.0     # Feedback (optional)
mix: 0.0-1.0           # Wet/dry mix
```

#### Low-Pass Filter

```yaml
type: lowpass
cutoff_frequency_hz: 20-20000  # Cutoff frequency
```

### BPM-Synchronized Parameters

Parameters can respond dynamically to detected BPM:

#### Range Scaling

```yaml
room_size:
  bpm_min: 60          # BPM at minimum value
  bpm_max: 120         # BPM at maximum value
  range: [0.5, 0.9]    # [value at bpm_min, value at bpm_max]
```

#### Beat Subdivision

```yaml
delay_seconds:
  bpm_sync: true
  subdivisions: 1.0    # 1.0=quarter, 0.5=eighth, 2.0=half, 0.25=sixteenth
```

#### Rate Scaling

```yaml
rate_hz:
  bpm_sync: true
  scale: 0.015         # rate_hz = (bpm / 60) * scale
```

## Command-Line Options

```bash
python -m amor.audio [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | 8001 | OSC beat event port |
| `--control-port` | 8003 | OSC control bus port |
| `--sounds-dir` | `sounds` | Sound file directory |
| `--enable-panning` | disabled | Enable stereo panning |
| `--enable-intensity-scaling` | disabled | Enable intensity-based volume scaling |
| `--config` | `amor/config/samples.yaml` | Configuration file path |

### Examples

```bash
# Basic usage
python -m amor.audio

# Custom configuration
python -m amor.audio --config custom_samples.yaml

# Enable spatial and dynamic features
python -m amor.audio --enable-panning --enable-intensity-scaling

# Custom ports
python -m amor.audio --port 9001 --control-port 9003
```
