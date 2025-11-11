# Audio Engine - Beat Playback

OSC server that receives beat events from sensor processor and plays corresponding sound samples. Part of the Amor Phase 2 system.

## Quick Start

### 1. Install Dependencies

```bash
cd audio
pip3 install -r requirements.txt
```

### 2. Generate Sample Audio Files

```bash
python3 generate_ppg_samples.py
```

This creates 4 WAV files (44.1kHz, 16-bit, mono) in `sounds/`:
- `ppg_0.wav` - 440 Hz (Violin A4)
- `ppg_1.wav` - 523 Hz (Piano C5)
- `ppg_2.wav` - 659 Hz (Flute E5)
- `ppg_3.wav` - 784 Hz (Trumpet G5)

### 3. Run the Engine

```bash
python3 -m amor.audio
```

The engine starts listening on port 8001 for beat events. It will print status as beats are received and played.

## Usage

### Basic Invocation

```bash
# Default: port 8001, sounds/ directory
python3 -m amor.audio

# Custom port and sounds directory
python3 -m amor.audio --port 8001 --sounds-dir /path/to/sounds
```

### Command-Line Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | int | 8001 | UDP port for beat input |
| `--sounds-dir` | str | sounds | Directory containing ppg_0.wav through ppg_3.wav |

### Exit

Press `Ctrl+C` to gracefully shutdown. Statistics are printed on exit.

## OSC Message Format

Beat events arrive as OSC messages on `/beat/{ppg_id}` with 3 arguments:

```
Address: /beat/{ppg_id}
Arguments: [timestamp, bpm, intensity]

timestamp (float)  Unix time in seconds (from sensor processor)
bpm (float)        Heart rate in beats per minute
intensity (float)  Signal strength 0.0-1.0 (reserved for future use)
```

### Example: Beat from PPG Sensor 0

```
/beat/0  1699723852.345  72.5  0.8
```

## Beat Handling

### Timestamp Validation

The engine validates all received timestamps:

- **Valid**: timestamp < 500ms old → beat is played
- **Invalid**: timestamp >= 500ms old → beat is dropped

This ensures only fresh beats are played. Stale beats indicate network or processing delays.

### Concurrent Playback

Each PPG sensor has an independent audio stream. Multiple beats can overlap without stopping each other:

- PPG 0 beat plays on stream 0
- PPG 1 beat plays on stream 1
- PPG 2 beat plays on stream 2
- PPG 3 beat plays on stream 3

This allows all 4 sensors to send beats simultaneously without interference.

### Message Validation

Messages are validated in order:

1. Address matches `/beat/[0-3]` pattern
2. Exactly 3 arguments provided
3. All arguments are numbers
4. PPG ID is in range 0-3
5. Timestamp is non-negative
6. Timestamp is < 500ms old

Invalid messages are dropped and logged.

## Testing

### Unit Tests

Run the full test suite:

```bash
python3 -m pytest test_amor/audio.py -v
```

Or with unittest:

```bash
python3 test_amor/audio.py
```

Test coverage includes:
- Timestamp validation (fresh, stale, boundary cases)
- Concurrent playback (multiple sensors, overlapping beats)
- Message validation (format, types, ranges)
- Statistics tracking
- Error handling (missing files, invalid ports)

### Test Without Sensor Processor

Use the test OSC sender script to simulate beat events:

```bash
# In one terminal, start the audio engine
python3 -m amor.audio

# In another terminal, send test beats
python3 scripts/test_osc_sender.py --port 8001 --sensors 4
```

This sends random beat events from 4 simulated sensors at realistic BPM values.

### Custom Beat Generation

Generate test beat events from Python:

```python
from pythonosc import udp_client
import time

client = udp_client.SimpleUDPClient("127.0.0.1", 8001)

# Send a beat from PPG 0 (timestamp, bpm, intensity)
now = time.time()
client.send_message("/beat/0", [now, 72.0, 0.8])
```

## Statistics

On shutdown (`Ctrl+C`), the engine prints statistics:

```
============================================================
AUDIO ENGINE STATISTICS
============================================================
Total messages: 245
Valid: 220
Dropped: 25
Played: 220
============================================================
```

**Interpretation:**

- `Total messages`: All OSC messages received
- `Valid`: Messages with timestamp < 500ms old
- `Dropped`: Messages with stale timestamp or validation errors
- `Played`: Successfully played beats (should equal valid)

**Ratio**: `Played / Total` indicates timestamp freshness. A ratio < 0.8 suggests network/processing delays.

## Troubleshooting

### Port Already in Use

```
ERROR: Port 8001 already in use
```

Find and kill the process:

```bash
lsof -ti:8001 | xargs kill
```

Or use a different port:

```bash
python3 -m amor.audio --port 9001
```

### Missing WAV Files

```
ERROR: Missing WAV file: /path/to/sounds/ppg_0.wav
```

Generate samples:

```bash
python3 generate_ppg_samples.py
```

Or provide your own WAV files (44.1kHz, 16-bit, mono):

```bash
python3 -m amor.audio --sounds-dir /path/to/your/sounds
```

### No Audio Output

Check audio driver:

```bash
# Detect available audio interfaces
bash scripts/detect-audio-interface.sh
```

Verify beats are being received:

```bash
# Look for "BEAT PLAYED:" messages in console output
python3 -m amor.audio
```

### High Drop Rate

Stale beats indicate delayed timestamps from sensor processor:

```bash
# Check statistics ratio on shutdown
# Played / Total should be > 0.8
```

Common causes:
- Sensor processor backlog or delay
- Network congestion
- System CPU overload

Solutions:
- Check sensor processor logs
- Monitor network latency
- Reduce other system load

## File Structure

```
audio/
├── amor/audio.py           # OSC server, beat handling, audio playback
├── test_amor/audio.py      # Unit tests (pytest/unittest)
├── generate_ppg_samples.py   # Generate test WAV files
├── scripts/
│   ├── test_osc_sender.py    # Send test beat events to engine
│   └── detect-audio-interface.sh  # Find audio devices
├── sounds/                   # WAV files (4 samples)
│   ├── ppg_0.wav
│   ├── ppg_1.wav
│   ├── ppg_2.wav
│   └── ppg_3.wav
└── README.md                 # This file
```

## Architecture

```
Sensor Processor (amor/processor.py)
  ↓ OSC /beat/{0-3} on port 8001
Audio Engine (this component)
  ├─ Message Validation
  ├─ Timestamp Validation
  └─ Concurrent Audio Playback (4 independent streams)
      ↓
  Audio Output (speakers/headphones)
```

The engine decouples beat reception from playback using 4 independent audio streams. This prevents beats from stopping each other.

## Reference

- **Code Documentation**: `amor/audio.py` module docstring and class docstrings
- **Tests**: `test_amor/audio.py` for usage examples and validation rules
- **Sensor Processor**: `/testing/README.md` for overall Amor system architecture
