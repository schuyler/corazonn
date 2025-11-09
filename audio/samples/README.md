# Audio Sample Library - Heartbeat Installation Phase 1

## Overview

This directory contains audio samples used in the heartbeat-triggered percussion system.

**Starter pack status:** 4 basic samples included and pre-processed
**Total samples:** 96 (across all categories, expandable)
**Format:** WAV (uncompressed), 48kHz, mono, 16-bit

---

## Directory Structure

```
audio/samples/
├── README.md                         # This file
├── percussion/
│   ├── starter/                      # Phase 1 starter pack (included)
│   │   ├── kick-01.wav              # Sensor 0 (low frequency anchor)
│   │   ├── snare-01.wav             # Sensor 1 (mid-range punctuation)
│   │   ├── hat-01.wav               # Sensor 2 (high-frequency texture)
│   │   └── clap-01.wav              # Sensor 3 (percussive accent)
│   └── [expansion]/                 # User additions (not in starter pack)
├── tonal/                            # Future: melodic samples
├── ambient/                          # Future: texture samples
└── oneshots/                         # Future: effect samples
```

---

## Phase 1: Starter Pack (Included)

### Pre-Configured Samples

All starter pack samples are pre-configured for immediate use:

| File | Duration | Format | License | Use Case |
|------|----------|--------|---------|----------|
| `kick-01.wav` | ~0.5s | WAV, 48kHz, mono, 16-bit | CC0 | Sensor 0 (left speaker) |
| `snare-01.wav` | ~0.3s | WAV, 48kHz, mono, 16-bit | CC0 | Sensor 1 (left-center) |
| `hat-01.wav` | ~0.2s | WAV, 48kHz, mono, 16-bit | CC0 | Sensor 2 (right-center) |
| `clap-01.wav` | ~0.4s | WAV, 48kHz, mono, 16-bit | CC0 | Sensor 3 (right speaker) |

### Source Information

Samples sourced from Freesound.org (CC0 licensed):
- All samples under Creative Commons Zero (public domain)
- Ready to use without attribution required
- Pre-normalized to -6dBFS (safe headroom for mixing)

### Mapping to Sensors

In the current Phase 1 implementation:

```
Sensor 0 → kick-01.wav    → Left speaker (pan: 0.0)
Sensor 1 → snare-01.wav   → Left-center (pan: 0.33)
Sensor 2 → hat-01.wav     → Right-center (pan: 0.67)
Sensor 3 → clap-01.wav    → Right speaker (pan: 1.0)
```

Each sample triggers once per heartbeat (IBI) at its respective sensor position.

---

## Adding More Samples

### Step 1: Acquire Samples

Recommended sources with filtering for 48kHz+:

**Freesound.org:**
- Search: `percussion samples wav`
- Filters: License = CC0, Format = WAV
- Recommended: Sample rate 48000Hz+, Mono preferred
- Download limit: 15 downloads/day (register free account)

**Other sources:**
- BBC Sound Effects Library (CC-BY, high quality)
- Zapsplat (free downloads, CC0 option)
- Your own recordings (iPhone Voice Memos work well)

### Step 2: Process Samples

Convert any samples to the required format:

```bash
# Install sox if not already installed
sudo apt-get install sox

# Navigate to samples directory
cd /home/user/corazonn/audio/samples/percussion

# Process a single sample
sox "my-sample.wav" \
  -r 48000 \
  -c 1 \
  "my-sample-processed.wav"

# Normalize to -6dBFS peak
sox "my-sample-processed.wav" \
  "my-sample-final.wav" \
  norm -6

# Verify format
soxi "my-sample-final.wav"
```

**Expected output:**
```
Input File: 'my-sample-final.wav'
Channels: 1
Sample Rate: 48000
Precision: 16-bit
Duration: 00:00:XX
```

### Step 3: Place and Test

1. Move processed sample to appropriate directory:
   ```bash
   mv my-sample-final.wav percussion/my-category/
   ```

2. Edit `heartbeat-main.pd` to use new sample:
   - Open patch in Pure Data
   - Find sound-engine subpatch
   - Change sample filename in `[read -resize ...]` message box
   - Reload patch to test

3. Verify in Pure Data console:
   - Should print: `read NNNNN samples into table sample-X`
   - If error: "couldn't open ..." - check file path

---

## Sample Format Requirements

### For Phase 1 (Current)

**Mandatory:**
- Format: WAV (PCM, uncompressed)
- Sample rate: 48000 Hz
- Channels: 1 (mono)
- Bit depth: 16-bit
- Duration: 0.1 - 2.0 seconds (short percussion samples)
- Peak level: -6dBFS (normalized)

**Why these specs:**
- 48kHz matches audio interface sample rate (no resampling)
- Mono saves memory (samples loaded into RAM)
- 16-bit sufficient for percussion (high SNR)
- -6dBFS headroom prevents clipping when 4 channels mix

### For Phase 2+ (Future)

Planned extensions:
- Support 24-bit samples
- Multi-sample support per sensor (randomly select)
- Longer samples (up to 10 seconds for ambient/texture)
- Stereo samples for rich textures

---

## Usage in Pure Data

### Current Implementation (Phase 1)

Samples load automatically when patch starts:

```pd
[loadbang]
|
[t b b b b]          # Trigger 4 parallel loads
|   |   |   |
|   |   |   [read -resize clap-01.wav sample-3(
|   |   |   |
|   |   |   [soundfiler]
|   |   |   |
|   |   |   [s sample-3-length]
|   |   |
|   |   [read -resize hat-01.wav sample-2(
|   |   ...
|   [read -resize snare-01.wav sample-1(
|   ...
[read -resize kick-01.wav sample-0(
```

Each sample is loaded into a table (`sample-0`, `sample-1`, `sample-2`, `sample-3`).

When a heartbeat arrives:
1. Valid IBI triggers `[r ibi-valid-N]`
2. Sample playback starts from table
3. Envelope applied (5ms attack, 40ms sustain, 5ms release)
4. Panned to sensor position (0.0-1.0 across stereo field)
5. Mixed with other channels and output to stereo

### Customizing Sample Mapping

To change which sample plays for each sensor:

1. Open `/home/user/corazonn/audio/patches/sound-engine.pd`
2. Find the `[read -resize ...]` message boxes
3. Change filenames:
   - Line ~3: Change `kick-01.wav` to your kick sample
   - Line ~8: Change `snare-01.wav` to your snare sample
   - Line ~13: Change `hat-01.wav` to your hi-hat sample
   - Line ~18: Change `clap-01.wav` to your clap sample
4. Save and reload in Pure Data

---

## Audio Quality Considerations

### Why -6dBFS Normalization?

Provides headroom for 4 simultaneous samples:
- Single sample: -6dBFS
- 2 simultaneous: -6 + -6 = -12dB effective (safe)
- 3 simultaneous: -18dB effective (very safe)
- 4 simultaneous: -24dB effective (headroom for transient peaks)

Pure Data limiter (`[clip~]`) prevents clipping if all 4 sensors fire within same audio block.

### Sample Duration

- **Kick:** 400-600ms (low-frequency fundamental rings longer)
- **Snare:** 200-400ms (quick decay)
- **Hat:** 100-300ms (short, bright)
- **Clap:** 200-500ms (complex, decays quickly)

Samples longer than ~2 seconds waste disk space and memory. Phase 1 uses one-shot percussion.

### Monitoring Sample Loading

In Pure Data console, you should see:
```
read 48000 samples into table sample-0
read 44032 samples into table sample-1
read 22016 samples into table sample-2
read 38400 samples into table sample-3
```

If samples don't load:
- Check `[declare -path ../samples/percussion/starter]` in main patch
- Verify files exist: `ls /home/user/corazonn/audio/samples/percussion/starter/`
- Check Pd console for "couldn't open" errors

---

## Future Phases

### Phase 2: Multi-Sample Support
- Multiple variations per sensor
- Random selection from bank
- Example: 3 kick samples, randomly pick one

### Phase 3: Tonal Samples
- Melodic instruments (piano, strings)
- Pitch control based on heartbeat rate
- Example: BPM affects pitch

### Phase 4: Ambient Textures
- Long-form pads and textures
- Crossfade between layers
- Example: Calm texture at low BPM, busy texture at high BPM

---

## Troubleshooting

### "Couldn't open ..." error in Pd console

**Solution:** Verify file paths:
```bash
# Check files exist
ls -la /home/user/corazonn/audio/samples/percussion/starter/

# Check Pd is finding samples
# In Pd: File → Open and browse to patches/
# Verify relative path works: ../samples/percussion/starter/
```

### Sample plays but sounds distorted

**Solution:** Check normalization:
```bash
# Check current peak level
sox "sample.wav" -n stat -freq

# If peak > -6dBFS, re-normalize
sox "sample.wav" "sample-norm.wav" norm -6
```

### Sample format incorrect (wrong sample rate)

**Solution:** Convert to 48kHz:
```bash
sox "sample.wav" -r 48000 "sample-48k.wav"
```

### Sample too loud or too quiet

**Solution:** Adjust normalization:
```bash
# Normalize to -3dBFS (louder, less headroom)
sox "sample.wav" "sample-loud.wav" norm -3

# Normalize to -10dBFS (quieter, more headroom)
sox "sample.wav" "sample-quiet.wav" norm -10
```

---

## Performance Notes

- **Memory usage:** 4 × 96000 samples (max) ≈ 1.5 MB per sensor = 6MB total
- **Disk space:** Negligible (~100KB per sample)
- **Load time:** <100ms (nearly instant)
- **CPU impact:** Minimal (<5% for playback)

---

## License

Starter pack samples: CC0 (Creative Commons Zero)
- Free to use, modify, distribute without attribution
- Original sources credited in individual file metadata

---

## Questions?

See main README: `/home/user/corazonn/audio/README.md`

For audio interface issues: Run `./scripts/detect-audio-interface.sh`

For sample processing help: See Phase 1 TRD at `../docs/audio/reference/phase1-trd.md`
