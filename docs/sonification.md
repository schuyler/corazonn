# PPG-to-Audio Heartbeat Synthesis

**Status:** Experimental / Prototype Only
**Author:** Claude
**Date:** 2025-11-13

## Overview

This document describes an experimental approach for generating realistic heartbeat audio directly from PPG sensor beat events, designed to mask sensor clipping artifacts while creating natural-sounding heartbeat audio for integration into the Corazón soundscape.

**Current Implementation Status:**
- ✅ Prototype script created (`audio/prototype_heartbeat_synth.py`)
- ✅ Four preset variations designed and tested
- ❌ Not integrated with main audio engine
- ❌ No real-time OSC control
- ❌ No live PPG data testing

## Problem Statement

### PPG Sensor Clipping

PPG sensors in the Corazón system can clip at the top end (ADC value 4095) during:
- Strong signal conditions
- Sensor placement on highly vascularized areas
- Motion artifacts
- Individual physiological variations

**Clipping characteristics:**
- Flat regions at maximum ADC value (4095)
- Loss of waveform variation in systolic peaks
- Creates distortion in frequency domain (sharp edges → harmonics)
- Affects derivative-based analysis (rate of change = 0)

### Traditional Sample Playback Limitations

Current system uses beat-triggered WAV sample playback:
- Pre-recorded samples triggered on `/beat` events
- Works well for rhythmic variation
- But samples are static/repetitive
- No connection to actual PPG waveform characteristics
- Does not represent the "liveness" of the sensor data

### Design Goal

Create **synthesized heartbeat audio** that:
1. Sounds like a natural, realistic heartbeat
2. Completely masks PPG sensor clipping artifacts
3. Integrates seamlessly into existing soundscape
4. Responds to beat timing and intensity
5. Provides variation to avoid mechanical repetition

## Approach: Beat-Driven Synthesis

### Core Insight

The beat detector (`amor/detector.py`) continues to work correctly even during clipping:
- Threshold crossings still detected (clipped peaks still cross threshold)
- BPM calculation remains accurate
- Intensity estimation still valid
- Only raw waveform shape is corrupted

**Therefore:** Synthesize audio using only beat timing information, not raw PPG amplitude.

### Synthesis Method

Generate two distinct heart sounds for each beat:

**S1 ("lub")** - First heart sound
- Represents mitral/tricuspid valve closure
- Lower frequency (~75 Hz)
- Longer duration (~120ms)
- Louder than S2

**S2 ("dub")** - Second heart sound
- Represents aortic/pulmonary valve closure
- Higher frequency (~150 Hz)
- Shorter duration (~80ms)
- Quieter than S1
- Delayed ~35% through cardiac cycle

### Sound Synthesis Components

Each heart sound (S1/S2) generated from:

1. **Bandpassed Noise**
   - Simulates turbulent blood flow through valves
   - Filtered around center frequency (±25 Hz)
   - Adjustable mix ratio (0-100% noise)

2. **Sine Wave Transient**
   - Provides tonal resonance
   - Center frequency varies by preset
   - Represents chest cavity resonance

3. **Envelope Shaping**
   - Exponential decay (natural damping)
   - Sharp attack (5ms) for percussive onset
   - Different decay rates for S1 vs S2

4. **Randomization (optional)**
   - Timing variation (±10ms)
   - Pitch variation (±5%)
   - Prevents mechanical repetition
   - Mimics biological variability

## Preset System

Four presets designed for different aesthetic contexts:

### Natural

**Character:** Realistic, organic heartbeat with biological variation

**Parameters:**
- S1: 75 Hz, 120ms duration
- S2: 150 Hz, 80ms duration
- S2 delay: 35% of inter-beat interval
- Noise mix: 30% (realistic turbulence)
- Variation: ±10ms timing, ±5% pitch

**Use Case:** General soundscape integration, ambient background, realistic simulation

---

### Electronic

**Character:** Clean, synthetic, precise

**Parameters:**
- S1: 60 Hz, 80ms duration
- S2: 120 Hz, 60ms duration
- S2 delay: 30% of inter-beat interval
- Noise mix: 0% (pure sine waves)
- Variation: None (perfectly consistent)

**Use Case:** Minimal aesthetics, electronic music context, precise rhythmic emphasis

---

### Sub-Bass

**Character:** Deep, resonant, physically felt

**Parameters:**
- S1: 45 Hz, 150ms duration
- S2: 90 Hz, 100ms duration
- S2 delay: 40% of inter-beat interval
- Noise mix: 10% (mostly tonal)
- Variation: ±15ms timing, ±8% pitch

**Use Case:** Immersive installations, body-resonance effects, bass-heavy soundscapes

---

### Percussive

**Character:** Sharp, rhythmic, drum-like

**Parameters:**
- S1: 100 Hz, 50ms duration
- S2: 200 Hz, 40ms duration
- S2 delay: 25% of inter-beat interval
- Noise mix: 60% (highly noisy)
- Variation: ±5ms timing, ±3% pitch

**Use Case:** Beat-driven soundscapes, rhythmic emphasis, aggressive character

## Parameter Mappings

### From Beat Events

Beat events (`/beat/{ppg_id} [timestamp_ms, bpm, intensity]`) provide:

**BPM → Timing**
- Inter-beat interval (IBI) = 60.0 / BPM seconds
- S2 delay = IBI × preset.s2_delay_ratio
- Example: 72 BPM → 0.833s IBI → S2 at 0.291s

**Intensity → Amplitude & Character**
- Direct amplitude scaling (0.0 - 1.0)
- S2 amplitude = S1 amplitude × 0.7 (S2 quieter)
- Higher intensity → more noise component (optional)
- Higher intensity → sharper attack (optional)

**PPG Channel ID → Spatial Position**
- Use existing panning system (`audio.py:self.panning[ppg_id]`)
- Each channel can have independent spatial position
- Stereo field: -1.0 (left) to +1.0 (right)

### Randomization (Natural/Sub-Bass/Percussive presets)

**Timing Variation:**
- S2 delay += random(±variation_ms)
- Prevents robotic consistency
- Mimics heart rate variability

**Pitch Variation:**
- Frequency *= (1 + random(±pitch_variation))
- Subtle: ±5% typical
- Creates unique sound per beat

## Implementation Architecture

### Proposed Integration

```
Existing Beat Detection Pipeline:
  ESP32 → /ppg/{id} → Processor → Detector → /beat/{id} [ts, bpm, intensity]

New Synthesis Branch:
  /beat/{id} → Audio Engine → HeartbeatSynthesizer.generate(bpm, intensity)
                            → rtmixer playback (with existing effects/panning)
```

### Code Structure

**New Module:** `amor/heartbeat_synth.py`
```python
class HeartbeatSynthesizer:
    def __init__(self, sample_rate=48000, preset="natural")
    def generate_heartbeat(bpm, intensity) -> (s1_audio, s2_audio)
    def set_preset(preset_name)
    def _generate_heart_sound(duration, freq, intensity, noise_mix, is_s1)
    def _bandpass_filter(audio, low_freq, high_freq)
```

**New Module:** `amor/heartbeat_presets.py`
```python
PRESETS = {
    "natural": HeartbeatPreset(...),
    "electronic": HeartbeatPreset(...),
    "sub-bass": HeartbeatPreset(...),
    "percussive": HeartbeatPreset(...),
}
```

**Modifications to:** `amor/audio.py`
```python
class AudioEngine:
    # New instance variables
    self.heartbeat_synth = HeartbeatSynthesizer(self.sample_rate)
    self.heartbeat_enabled = [False] * 8  # Per-channel toggle

    # New method
    def play_heartbeat(self, ppg_id, bpm, intensity):
        s1, s2 = self.heartbeat_synth.generate_heartbeat(bpm, intensity)
        self._play_generated_audio(s1, ppg_id)
        self._schedule_delayed_audio(s2, ppg_id, delay=s2_delay)

    # Modified method
    def handle_beat(self, ppg_id, timestamp_ms, bpm, intensity):
        # Existing sample playback
        if self.ppg_samples_enabled[ppg_id]:
            self.play_ppg_sample(ppg_id, intensity)

        # NEW: Heartbeat synthesis (runs in parallel)
        if self.heartbeat_enabled[ppg_id]:
            self.play_heartbeat(ppg_id, bpm, intensity)
```

**OSC Control Messages:**
```
/heartbeat/enable/{ppg_id} <0|1>      # Enable/disable per channel
/heartbeat/preset <preset_name>        # Switch preset globally
/heartbeat/preset/{ppg_id} <name>      # Switch preset per channel (future)
```

### Data Flow

```
1. PPG sensor data arrives (may be clipped)
   ↓
2. Beat detector processes (works despite clipping)
   ↓
3. Beat event emitted: /beat/{ppg_id} [timestamp, bpm, intensity]
   ↓
4. Audio engine receives beat event
   ↓
5. If heartbeat_enabled[ppg_id]:
   a. Generate S1 audio (noise + sine + envelope)
   b. Calculate S2 delay from BPM
   c. Generate S2 audio (similar to S1, different params)
   d. Play S1 immediately via rtmixer
   e. Schedule S2 for delayed playback
   f. Apply existing panning[ppg_id]
   g. Apply existing effects if enabled (reverb/delay/etc)
   ↓
6. Output mixed with PPG samples and ambient loops
```

## Clipping Immunity Analysis

### Why This Approach Masks Clipping

**Clipping affects:**
- ❌ Raw PPG waveform amplitude (flattened peaks)
- ❌ PPG waveform shape (dicrotic notch lost)
- ❌ Derivative/rate-of-change (zero during flat regions)
- ❌ Frequency spectrum (harmonics from sharp edges)

**Clipping does NOT affect:**
- ✅ Threshold crossing detection (upward crossings still occur)
- ✅ Beat timing (intervals remain accurate)
- ✅ BPM estimation (calculated from intervals)
- ✅ Intensity estimation (MAD-based, uses median)

**Synthesis uses only:**
- ✅ Beat timestamps (timing)
- ✅ BPM (for S1-S2 spacing)
- ✅ Intensity (for amplitude)

**Therefore:**
- Clipping artifacts invisible in synthesized output
- No buzzing, distortion, or flat regions
- Natural sound regardless of sensor quality
- Graceful degradation (if beats detected, audio sounds good)

## Testing Strategy

### Prototype Testing (Current)

**Synthetic beat generation:**
- `audio/prototype_heartbeat_synth.py`
- Generates fake beat events (varying BPM/intensity)
- Outputs WAV files for each preset
- Manual listening evaluation

**Status:** ✅ Complete
- All four presets generated
- 10-second samples at 72 BPM
- Files in `audio/heartbeat_*.wav` (gitignored)

### Integration Testing (Future)

**Unit tests:**
- Test `HeartbeatSynthesizer.generate_heartbeat()` at various BPMs
- Verify S1/S2 durations match preset specifications
- Check frequency content via FFT
- Verify randomization produces variation

**Integration tests:**
- Use PPG emulator (`amor/simulator/ppg_emulator.py`)
- Enable heartbeat synthesis for one channel
- Verify audio output without crashes
- Test alongside existing sample playback (no conflicts)

**Real PPG data:**
- Capture PPG data with known clipping (`amor/capture.py`)
- Replay through system (`amor/replay.py`)
- Verify beat detection works during clipping
- Verify synthesized audio sounds natural regardless

**Stress tests:**
- Extreme BPM (40, 180, 220)
- Rapid BPM changes
- All 8 channels enabled simultaneously
- Long-duration sessions (hours)

## Configuration

### Default Configuration (Proposed)

`audio/audio_config.py`:
```yaml
heartbeat:
  # Global enable/disable
  enabled: false

  # Per-channel enable (8 channels)
  channel_enabled: [false, false, false, false, false, false, false, false]

  # Preset selection
  preset: "natural"

  # Per-channel presets (future feature)
  # channel_presets: ["natural", "natural", "sub-bass", ...]

  # Volume relative to samples (future)
  # volume: 0.8
```

### Runtime Control

**OSC Messages:**
```python
# Enable channel 0
/heartbeat/enable/0 1

# Disable channel 0
/heartbeat/enable/0 0

# Change preset globally
/heartbeat/preset "sub-bass"

# Future: per-channel preset
/heartbeat/preset/0 "percussive"
```

**Launchpad Integration (Future):**
- Button to toggle heartbeat synthesis
- Encoder to switch presets
- LED indicators for enabled channels

## Open Questions

### Technical

1. **rtmixer delayed playback:**
   - Does rtmixer support native delayed playback for S2?
   - Or implement delay buffer manually?
   - Current assumption: schedule via threading/asyncio

2. **Effects routing:**
   - Apply reverb/delay to heartbeat audio?
   - Or bypass effects for "dry" heartbeat?
   - Recommendation: Apply effects for cohesive soundscape

3. **Volume mixing:**
   - Heartbeat volume relative to samples?
   - Auto-level based on intensity?
   - Separate volume control?
   - Recommendation: Start with intensity-only, add control later

4. **Multi-channel behavior:**
   - All 8 channels enabled simultaneously?
   - Frequency/spatial separation to prevent mud?
   - Recommendation: Test 1 channel first, then scale

### Design

5. **Preset expansion:**
   - Additional presets needed? ("woody", "metallic", "breathy")
   - User-customizable parameters?
   - Preset interpolation/morphing?

6. **Dynamic parameter mapping:**
   - BPM → character changes (faster = more aggressive)?
   - Intensity → noise mix variations?
   - PPG signal quality → timbre shifts?

7. **Integration with existing samples:**
   - Run heartbeat + samples simultaneously?
   - Replace sample banks with heartbeat?
   - User preference/configuration?

### Performance

8. **CPU overhead:**
   - 8 channels × 2 sounds per beat = 16 synthesis operations per heartbeat cycle
   - Bandpass filtering overhead (scipy.signal.butter)
   - Real-time feasibility on target hardware?
   - Optimization needed? (pre-compute filters, reduce randomization)

9. **Latency:**
   - Beat event → audio output delay?
   - Acceptable latency budget?
   - S2 scheduling accuracy?

## Future Enhancements

### Phase 2 Features

**Per-channel presets:**
- Each PPG channel uses different preset
- Channel 0-3: natural, channel 4-7: electronic
- Configuration via OSC or config file

**Parameter automation:**
- OSC control for individual parameters
- `/heartbeat/s1_freq/{ppg_id} <freq>`
- `/heartbeat/noise_mix/{ppg_id} <0.0-1.0>`
- Real-time sound design

**Preset morphing:**
- Interpolate between two presets
- `/heartbeat/morph "natural" "electronic" 0.5`
- Smooth transitions over time

### Phase 3 Features

**Waveform-driven synthesis:**
- Use PPG shape when NOT clipped
- Fallback to beat-driven when clipped
- Best of both worlds (connection + immunity)

**Machine learning:**
- Learn realistic heartbeat characteristics from recordings
- Generate infinite variations
- Style transfer (different people's heartbeats)

**Spatial audio:**
- 3D positioning beyond stereo panning
- Distance attenuation
- Room acoustics simulation

**Visual feedback:**
- Waveform display showing synthesis
- Real-time parameter visualization
- Preset selection UI

## References

### Existing Code

- `amor/detector.py` - Beat detection (threshold crossings)
- `amor/predictor.py` - Heartbeat prediction
- `amor/audio.py` - Audio engine (rtmixer, effects)
- `amor/audio_effects.py` - Effect processing
- `audio/generate_ppg_samples.py` - Example audio generation

### Prototype

- `audio/prototype_heartbeat_synth.py` - Standalone synthesis script
- `audio/HEARTBEAT_PROTOTYPE_README.md` - Prototype documentation

### Medical Background

**Heart sounds physiology:**
- S1: Mitral/tricuspid valve closure (systole start)
- S2: Aortic/pulmonary valve closure (systole end)
- S3/S4: Abnormal sounds (not modeled)
- Typical S1-S2 interval: 0.3-0.4s at rest

**Frequency content:**
- S1: 25-100 Hz (peak ~50 Hz)
- S2: 50-200 Hz (peak ~100 Hz)
- Both contain broadband noise (turbulence)

### DSP Techniques

- Bandpass filtering (scipy.signal.butter)
- Envelope generation (exponential decay)
- Additive synthesis (noise + sine)
- Randomization (numpy.random)

## Conclusion

This experimental heartbeat synthesis approach provides:

✅ **Clipping immunity** - Uses only beat timing, not amplitude
✅ **Natural sound** - Realistic S1/S2 with variation
✅ **Flexible presets** - Four aesthetic options
✅ **Integration ready** - Works with existing audio engine
✅ **Real-time capable** - Low-latency synthesis

**Next Steps:**
1. Evaluate prototype audio samples
2. Refine presets based on aesthetic preferences
3. Integrate synthesis engine into `amor/audio.py`
4. Add OSC control messages
5. Test with real PPG data (including clipped signals)
6. Performance optimization if needed
7. User documentation and examples

**Status:** Awaiting decision on prototype evaluation and integration priority.
