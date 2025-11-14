# Freesound Sample Library

Download and manage audio samples from Freesound.org for the heartbeat installation.

## Overview

The Freesound integration provides tools for downloading, organizing, and querying a curated library of 60+ high-quality audio samples organized by timbral families. Samples are selected for optimal pitch-shifting quality in heartbeat-synchronized installations.

## Installation

```bash
# Install Freesound dependencies
pip install -e ".[freesound]"
```

Dependencies:
- `freesound-python` - Official Freesound API client
- `python-dotenv` - Environment variable management

## Configuration

### 1. Get API Token

Visit https://freesound.org/apiv2/apply to get your API token:
1. Log in to your Freesound account
2. Apply for API access (instant approval)
3. Copy your **API Token**

### 2. Configure Environment

```bash
# Create .env file from template
cp .env.example .env

# Edit .env and add your API token
FREESOUND_API_TOKEN=your_api_token_here
```

The `.env` file is gitignored and should never be committed.

## Sample Library Structure

### Directory Organization

```
audio/library/
├── 01_Metallic_Bells/
│   ├── SingingBowl_C2_122650.wav
│   ├── TubularBell_C4_374273.wav
│   └── ...
├── 02_Wooden_Percussion/
│   ├── Kalimba_C4_331047.wav
│   ├── Marimba_G4_255689.wav
│   └── ...
├── 03_Synth_Tones/
├── 04_Natural_Organic/
├── 05_String_Resonance/
├── metadata.json          # Complete sample metadata
└── attribution.txt        # License compliance
```

### Naming Convention

Files are named: `INSTRUMENT_PITCH_ID.ext`

- **INSTRUMENT**: Descriptive name (e.g., SingingBowl, Kalimba, Cello)
- **PITCH**: Musical pitch if known (e.g., C4, D, G) or X if unknown
- **ID**: Freesound sound ID for tracking
- **ext**: Original file extension (wav, flac, aif, ogg)

### Timbral Families

| Family | Description | Sample Count |
|--------|-------------|--------------|
| `01_Metallic_Bells` | Singing bowls, tubular bells, gongs, hand bells | ~15 |
| `02_Wooden_Percussion` | Kalimba, marimba, xylophone, tongue drums | ~12 |
| `03_Synth_Tones` | Analog bass, ambient pads, plucks, pure tones | ~18 |
| `04_Natural_Organic` | Water drops, crotales, bamboo, stone | ~10 |
| `05_String_Resonance` | Cello, violin, pizzicato, harmonics | ~12 |

All samples are selected for:
- Clear pitch content suitable for pitch-shifting
- 0.8-10+ second sustain for heartbeat timing (50-80 BPM)
- High audio quality (24-bit preferred, 44.1kHz+ sample rate)
- CC0 or CC-BY licensing

## Downloading Samples

### Download All Samples

```bash
./audio/download_freesound_library.py download
```

This downloads all 60+ samples organized in `audio/freesound_ids.yaml`. Rate-limited to 29 requests/minute (Freesound restriction). Expect ~3-5 minutes for full library.

### Download Specific Family

```bash
# Download only metallic bells
./audio/download_freesound_library.py download --family 01_Metallic_Bells

# Test with 5 samples
./audio/download_freesound_library.py download --limit 5
```

### Verify Downloads

```bash
# Check which samples are present/missing
./audio/download_freesound_library.py verify
```

### Update Metadata

```bash
# Re-fetch metadata for existing files
./audio/download_freesound_library.py update-metadata
```

## Querying the Library

### Show Statistics

```bash
./audio/query_library.py stats
```

Displays:
- Total sample count
- Breakdown by timbral family
- License distribution
- Duration/sample rate/bit depth statistics

### List All Samples

```bash
# Basic list
./audio/query_library.py list

# Verbose output with full metadata
./audio/query_library.py list -v
```

### Filter Samples

```bash
# Find sustained pads over 5 seconds
./audio/query_library.py list --min-duration 5.0 --tag sustained --tag pad

# Find metallic samples in C4
./audio/query_library.py list --family 01_Metallic_Bells --pitch C4

# Find all CC0 samples
./audio/query_library.py list --license CC0

# Combine filters
./audio/query_library.py list \
  --family 05_String_Resonance \
  --min-duration 3.0 \
  --max-duration 10.0 \
  --instrument Cello
```

### Export Filtered Results

```bash
# Export to JSON for programmatic use
./audio/query_library.py list \
  --family 03_Synth_Tones \
  --min-duration 5.0 \
  --output synth_pads.json
```

### Show Sample Details

```bash
# Show full metadata for specific Freesound ID
./audio/query_library.py show 122650
```

Displays:
- Technical specs (sample rate, bit depth, duration)
- License and attribution info
- Tags and descriptions
- Audio features (loudness, brightness, etc.)
- User ratings and download counts

## Metadata Structure

### metadata.json Format

```json
{
  "library_version": "1.0",
  "total_samples": 67,
  "generated_date": "2025-11-13T17:30:00Z",
  "samples": [
    {
      "file_path": "audio/library/01_Metallic_Bells/SingingBowl_C2_122650.wav",
      "freesound_id": 122650,
      "freesound_url": "https://freesound.org/s/122650/",
      "username": "juskiddink",
      "name": "Titanium Singing Bowl",
      "license": "Attribution 3.0",
      "timbral_family": "01_Metallic_Bells",
      "subfamily": "A_Singing_Bowls",
      "instrument": "SingingBowl",
      "pitch": "C2",
      "duration_sec": 84.2,
      "samplerate": 44100,
      "bitdepth": 24,
      "channels": 2,
      "tags": ["singing-bowl", "resonance", "meditation"],
      "audio_features": {
        "loudness": -18.3,
        "brightness": 0.42
      }
    }
  ]
}
```

### Key Fields for Bank Curation

- `timbral_family` / `subfamily` - Categorical organization
- `duration_sec` - For filtering by sustain length
- `pitch` - Musical pitch (may be null)
- `tags` - User-provided descriptors
- `audio_features` - Computed acoustic properties
- `license` - CC0 (public domain) vs CC-BY (attribution required)

## Sample Selection Criteria

Samples are curated from `docs/freesounds/plan.md` based on:

### Pitch-Shifting Quality
- Simple to moderate harmonic content
- Clear fundamental frequency
- Stable pitch throughout sustain
- Non-vibrato or slow/wide vibrato only

### Duration
- 0.8-2s ideal for 60 BPM heartbeat
- 2-10s for slower tempos or overlapping layers
- Longer sustains provide flexibility

### Recording Quality
- WAV/FLAC lossless formats
- 24-bit preferred (16-bit acceptable)
- 44.1kHz+ sample rate (48kHz+ ideal)
- Low noise floor, no clipping

### Licensing
- CC0 (public domain) preferred for maximum flexibility
- CC-BY (Attribution) acceptable with proper credits
- CC-BY-NC (NonCommercial) avoided for commercial installations

## Attribution

### Generating Attribution

Attribution is automatically generated in `audio/library/attribution.txt` during download. This file includes all required credits for CC-BY samples.

### Required Attribution Format

For CC-BY samples:
```
"sound_name" by username (http://freesound.org/s/sound_id/) licensed under CC-BY 4.0
```

For CC0 samples, attribution is optional but recommended.

## API Rate Limits

Freesound enforces rate limits:
- **General API**: 60 requests/minute, 2000/day
- **Downloads (restricted)**: 30 requests/minute, 500/day

The download script respects these limits automatically:
- Rate limited to 29 requests/minute
- Exponential backoff on errors
- Auto-retry on transient failures

## Troubleshooting

### Authentication Errors

Verify that your `FREESOUND_API_TOKEN` is correctly set in `.env`. API tokens don't expire and can be reused across multiple sessions.

### Missing Samples

```bash
# Verify library completeness
./audio/download_freesound_library.py verify

# Re-download missing samples
./audio/download_freesound_library.py download
```

Existing files are skipped automatically.

### Rate Limiting

If you hit rate limits (HTTP 429 errors):
- Wait 1 minute before retrying
- Use `--limit` flag to download in smaller batches
- Download families separately over multiple sessions

### Sample Not Found (404)

Some sample IDs in `audio/freesound_ids.yaml` may have been deleted by users. These are logged but skipped. Check Freesound.org directly to confirm availability.

## Advanced Usage

### Adding New Samples

1. Find samples on Freesound.org matching quality criteria
2. Add entries to `audio/freesound_ids.yaml`:

```yaml
01_Metallic_Bells:
  A_Singing_Bowls:
    - id: 123456
      pitch: "E4"
      instrument: "CrystalBowl"
      description: "Clear sustained resonance"
```

3. Run download to fetch new samples:

```bash
./audio/download_freesound_library.py download
```

### Custom Queries

Load `metadata.json` directly in Python for advanced filtering:

```python
import json

with open('audio/library/metadata.json') as f:
    metadata = json.load(f)

# Find long sustained samples
long_samples = [
    s for s in metadata['samples']
    if s.get('duration_sec', 0) > 10.0
]

# Find samples with specific tags
meditative = [
    s for s in metadata['samples']
    if 'meditation' in s.get('tags', [])
]
```

### Integration with Audio Engine

To load samples in `amor/audio.py`:

```python
import json
from pathlib import Path

# Load metadata
metadata_path = Path('audio/library/metadata.json')
with open(metadata_path) as f:
    metadata = json.load(f)

# Get all singing bowl files
singing_bowls = [
    s['file_path'] for s in metadata['samples']
    if s['instrument'] == 'SingingBowl'
]
```

## Reference Documentation

Detailed sample selection criteria and Freesound API documentation:

- `docs/freesounds/plan.md` - Complete sample curation guide with specific IDs
- `docs/freesounds/access.md` - Freesound API technical reference
- `audio/freesound_ids.yaml` - Master sample ID list

## File Locations

| File | Purpose |
|------|---------|
| `audio/download_freesound_library.py` | Download script with OAuth2 |
| `audio/query_library.py` | Query and filter tool |
| `audio/freesound_ids.yaml` | Curated sample ID list |
| `audio/library/` | Downloaded samples (gitignored) |
| `audio/library/metadata.json` | Complete sample metadata |
| `audio/library/attribution.txt` | License compliance |
| `.env` | API credentials (gitignored) |
| `.env.example` | Credential template |
