# Heartbeat Installation - Audio Pipeline

Phase 1 audio processing for heartbeat-triggered percussion with spatial positioning.

## Quick Start

### Prerequisites
- Pure Data 0.52+ with mrpeach and cyclone externals
- Python 3.8+ with python-osc library
- USB audio interface (or built-in audio for testing)
- 4 percussion samples (provided in `samples/percussion/starter/`)

### Installation

1. **Install Pure Data and dependencies:**
   ```bash
   cd scripts
   ./install-dependencies.sh
   ```

2. **Configure audio interface:**
   ```bash
   cd scripts
   ./detect-audio-interface.sh
   ```

3. **Verify installation:**
   ```bash
   pd -version  # Should show Pd-0.52-1 or newer
   ```

### Running the Patch

1. **Start Pure Data with main patch:**
   ```bash
   cd patches
   pd heartbeat-main.pd
   ```

2. **In a separate terminal, run test OSC sender:**
   ```bash
   cd scripts
   python3 test-osc-sender.py --port 8000 --sensors 4
   ```

3. **You should hear:**
   - 4 different percussion sounds (kick, snare, hat, clap)
   - Spatial positioning (sensor 0 = left, sensor 3 = right)
   - Triggering at heartbeat rate (~60-100 BPM per sensor)

### Integration with ESP32 Simulator

For full system testing with realistic heartbeat patterns:

```bash
# Terminal 1: Start Pure Data patch
cd patches
pd heartbeat-main.pd

# Terminal 2: Run ESP32 simulator
cd ../testing
python3 esp32_simulator.py --port 8000 --sensors 4 --bpm 60,72,58,80
```

### Monitoring Lighting Output

To verify lighting OSC messages are being sent:

```bash
# Terminal 3: Monitor lighting bridge port
cd ../testing
python3 osc_receiver.py --port 8001
```

You should see `/light/N/pulse` messages with IBI values.

## Architecture

### Patch Structure

```
heartbeat-main.pd (main patch)
├── osc-input (subpatch)         - Receives OSC on port 8000
├── sensor-process.pd (×4)       - IBI validation and processing
├── sound-engine (subpatch)      - Sample playback (4 channels)
├── spatial-mixer (subpatch)     - Stereo panning and mixing
└── lighting-output.pd (×4)      - Sends OSC to port 8001
```

### Data Flow

```
ESP32 Sensors (×4)
    ↓ OSC/UDP :8000
    ↓ /heartbeat/N <ibi>
Pure Data Patch
    ├→ Audio Synthesis → USB Audio Interface → Speakers
    └→ OSC/UDP :8001 → Python Lighting Bridge → LEDs
```

### Sample Mapping

- **Sensor 0** (left): kick-01.wav
- **Sensor 1** (left-center): snare-01.wav
- **Sensor 2** (right-center): hat-01.wav
- **Sensor 3** (right): clap-01.wav

## Customization

### Changing Samples

1. Add your samples to `samples/percussion/` directory (see `samples/README.md` for format requirements)
2. Edit `heartbeat-main.pd` and update `[declare -path]` or sample filenames in sound-engine subpatch
3. Reload patch in Pure Data

### Adjusting Panning

Edit `spatial-mixer` subpatch in `heartbeat-main.pd`:
- Sensor positions use constant-power panning law
- Modify pan values (0.0 = full left, 1.0 = full right)
- Current positions: 0.0, 0.33, 0.67, 1.0

### Changing Sample Envelopes

In `sound-engine` subpatch, find `[vline~]` objects:
- Format: `[attack_time sustain_time, release_time release_delay(`
- Default: `[1 5, 0 5 40(` = 5ms attack, 40ms sustain, 5ms release

## Troubleshooting

### No Audio Output

1. **Check DSP is on:**
   - Pure Data menu: Media → Audio ON (or Ctrl+/)
   - Pd console should show "DSP ON"

2. **Check audio interface:**
   ```bash
   aplay -l  # List audio devices
   speaker-test -c 2 -D hw:1,0  # Test output (adjust card number)
   ```

3. **Check sample files:**
   - Pd console: Look for "couldn't open..." errors
   - Verify samples exist in `samples/percussion/starter/`
   - Check `[declare -path]` in main patch

### OSC Not Received

1. **Check port binding:**
   ```bash
   sudo netstat -uln | grep 8000
   # Should show: 0.0.0.0:8000
   ```

2. **Check firewall:**
   ```bash
   sudo ufw allow 8000/udp
   ```

3. **Check Pd console:**
   - Should print "VALID-IBI" messages when receiving
   - If no output, OSC receiver not working

### Audio Glitches/Clicks

1. **Increase audio buffer:**
   - Pure Data menu: Media → Audio Settings
   - Try buffer size 128 or 256 (default 64)

2. **Check CPU usage:**
   ```bash
   top -p $(pgrep pd)
   # Should be < 30%
   ```

### Wrong Stereo Positioning

1. **Verify speaker connections:**
   - Swap L/R cables if reversed
   - Test with `speaker-test -c 2`

2. **Check panning calculations:**
   - Use headphones for clear separation
   - Sensor 0 should be hard left, sensor 3 hard right

### Lighting OSC Not Sent

1. **Check udpsend connection:**
   - Pd console should show "Lighting-OSC-connected-to-port-8001"

2. **Verify lighting bridge is listening:**
   ```bash
   sudo netstat -uln | grep 8001
   # If nothing, lighting bridge not running
   ```

## Documentation

- **Technical Reference:** `../docs/audio/reference/phase1-trd.md`
- **Task Breakdown:** `../docs/audio/tasks/phase1-audio.md`
- **Sample Library Guide:** `samples/README.md`

## Performance

- **Expected latency:** < 50ms (heartbeat event → audio output)
- **CPU usage:** < 30% (on modern hardware)
- **Stability:** Runs 30+ minutes without glitches

## Phase 1 Limitations

This is the MVP implementation with intentional simplifications:
- Single sample per sensor (no variety)
- Fixed spatial positions (no movement)
- Basic limiting only (no advanced effects)
- No Launchpad control
- No BPM-based parameter mapping

See Phase 2 documentation for planned enhancements.
