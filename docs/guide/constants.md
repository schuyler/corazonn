# Constants Reference

Tunable constants defined in Python source code. Changes require code modification and process restart.

## OSC Port Assignments

File: `amor/osc.py`

```python
PORT_PPG = 8000            # PPG data broadcast (ESP32 → Processor)
PORT_BEATS = 8001          # Beat events (Processor → Audio)
PORT_BEATS_LIGHTING = 8002 # Beat events (Processor → Lighting)
PORT_CONTROL = 8003        # Control bus (Sequencer ↔ Audio ↔ Launchpad)
PORT_ESP32_ADMIN = 8006    # ESP32 admin commands
```

**Usage:**
- ESP32 sensors transmit to `PORT_PPG`
- Beat detector broadcasts to `PORT_BEATS` and `PORT_BEATS_LIGHTING`
- Sequencer communicates via `PORT_CONTROL`

## Stereo Pan Positions

File: `amor/osc.py`

```python
PPG_PANS = {
    0: -1.0,     # Hard left
    1: -0.33,    # Center-left
    2: 0.33,     # Center-right
    3: 1.0,      # Hard right
}
```

**Range:** -1.0 (left) to 1.0 (right)

**Note:** PPG IDs 4-7 inherit pan positions from 0-3 respectively.

## ADC Range

File: `amor/osc.py`

```python
ADC_MIN = 0
ADC_MAX = 4095           # 12-bit resolution
```

Expected range for ESP32 ADC readings.

## Sampling Rate

File: `amor/osc.py`

```python
SAMPLE_RATE_HZ = 50      # PPG sensor sampling frequency
```

Must match firmware `SAMPLE_RATE_HZ` in `config.h`.

## Audio Engine Constants

File: `amor/audio.py`

### Timestamp Threshold

```python
TIMESTAMP_THRESHOLD_MS = 500
```

Drop beat events older than 500ms to prevent delayed playback.

### Loop Limits

```python
# LoopManager class
LATCHING_MAX_ID = 15         # Loops 0-15 are latching
LATCHING_LIMIT = 6           # Max concurrent latching loops
MOMENTARY_LIMIT = 4          # Max concurrent momentary loops
```

**Loop Types:**
- Latching (0-15): Toggle on/off, limited to 6 concurrent
- Momentary (16-31): Play while pressed, limited to 4 concurrent

## Lighting Engine Constants

File: `amor/lighting.py`

```python
TIMESTAMP_THRESHOLD_MS = 500
```

Drop beat events older than 500ms to prevent delayed lighting effects.

## Sequencer Constants

File: `amor/sequencer.py`

### State Management

```python
STATE_VERSION = 1                    # State file format version
ASSIGNMENT_TIMEOUT_SEC = 30          # Sample assignment timeout
```

### LED Colors

Launchpad RGB values for visual feedback:

```python
LED_COLOR_UNSELECTED = 45            # Dim blue (sampler grid)
LED_COLOR_SELECTED = 37              # Bright cyan (sampler grid)
LED_COLOR_LOOP_OFF = 0               # Off (loop button)
LED_COLOR_LOOP_LATCHING = 21         # Green (active latching loop)
LED_COLOR_LOOP_MOMENTARY = 13        # Yellow (active momentary loop)
LED_COLOR_RECORDING = 5              # Red (recording in progress)
LED_COLOR_PLAYING = 21               # Green (playback in progress)
```

**Note:** Values are Launchpad-specific RGB palette indices.

## Sampler Constants

File: `amor/sampler.py`

### Binary Format

```python
# PPGRecorder class
MAGIC = b'PPGL'                      # File magic header
VERSION = 1                          # Format version
HEADER_SIZE = 8                      # Bytes: magic + version
RECORD_SIZE = 24                     # Bytes: timestamp (4) + samples (5×4)
```

### Recording Limits

```python
MAX_DURATION_SEC = 60                # Auto-stop recording after 60 seconds
```

## Configuration File Paths

### Default Paths

```python
# Audio engine
DEFAULT_CONFIG = "amor/config/samples.yaml"
DEFAULT_SOUNDS_DIR = "sounds"

# Lighting engine
DEFAULT_CONFIG = "amor/config/lighting.yaml"

# Sequencer
DEFAULT_CONFIG = "amor/config/samples.yaml"
DEFAULT_STATE_PATH = "amor/state/sequencer_state.json"
```

## Summary Tables

### Port Reference

| Port | Name | Direction | Purpose |
|------|------|-----------|---------|
| 8000 | `PORT_PPG` | ESP32 → Host | PPG sensor data |
| 8001 | `PORT_BEATS` | Host → Audio | Beat timing events |
| 8002 | `PORT_BEATS_LIGHTING` | Host → Lighting | Beat timing events |
| 8003 | `PORT_CONTROL` | Bidirectional | Control bus |
| 8006 | `PORT_ESP32_ADMIN` | Host → ESP32 | Admin commands |

### Loop ID Mapping

| Loop ID | Type | Behavior | Limit |
|---------|------|----------|-------|
| 0-15 | Latching | Toggle on/off | 6 concurrent |
| 16-31 | Momentary | Press/release | 4 concurrent |

### Pan Position Mapping

| PPG ID | Pan | Position |
|--------|-----|----------|
| 0, 4 | -1.0 | Hard left |
| 1, 5 | -0.33 | Center-left |
| 2, 6 | 0.33 | Center-right |
| 3, 7 | 1.0 | Hard right |
