# Amor Simulator Package

Emulated hardware components for integration testing without physical devices.

## Components

### PPG Sensor Emulator (`ppg_emulator.py`)

Simulates ESP32 PPG sensors sending heart rate data via OSC.

**Features:**
- Realistic cardiac waveform generation
- Configurable BPM, noise levels
- Dropout injection for testing error handling
- OSC message transmission at 10 Hz (5-sample bundles @ 50 Hz)

**Usage:**
```bash
# Single sensor
python3 -m amor.simulator.ppg_emulator --ppg-id 0 --bpm 75

# Multiple sensors (different terminals)
python3 -m amor.simulator.ppg_emulator --ppg-id 0 --bpm 72
python3 -m amor.simulator.ppg_emulator --ppg-id 1 --bpm 68
python3 -m amor.simulator.ppg_emulator --ppg-id 2 --bpm 75
python3 -m amor.simulator.ppg_emulator --ppg-id 3 --bpm 80
```

**API:**
```python
from amor.simulator.ppg_emulator import PPGEmulator

emulator = PPGEmulator(ppg_id=0, bpm=75.0)
emulator.set_bpm(80.0)
emulator.trigger_dropout(beats=2)
emulator.run()
```

### Launchpad Emulator (`launchpad_emulator.py`)

Simulates Launchpad Mini MK3 MIDI controller without hardware.

**Features:**
- OSC-based button press emulation
- LED state tracking from sequencer
- Interactive CLI mode
- Programmatic API for automated tests

**Usage:**
```bash
# Interactive mode
python3 -m amor.simulator.launchpad_emulator --interactive

# Background mode (for scripting)
python3 -m amor.simulator.launchpad_emulator
```

**Interactive Commands:**
```
p <ppg_id> <col>   - Press PPG button (e.g., 'p 0 3')
t <loop_id>        - Toggle loop (e.g., 't 5')
m <loop_id>        - Momentary loop (e.g., 'm 16')
s                  - Show LED grid
q                  - Quit
```

**API:**
```python
from amor.simulator.launchpad_emulator import LaunchpadEmulator

emulator = LaunchpadEmulator()
emulator.start()

# Simulate button presses
emulator.press_ppg_button(ppg_id=0, column=3)
emulator.toggle_loop(loop_id=5)
emulator.press_momentary_loop(loop_id=16, duration=0.5)

# Inspect state
led_state = emulator.get_led_state(row=0, col=3)
selected_col = emulator.get_ppg_selection(ppg_id=0)
```

### Kasa Bulb Emulator (`kasa_emulator.py`)

Simulates TP-Link Kasa smart bulbs with python-kasa protocol support.

**Features:**
- Kasa protocol implementation (encrypted TCP)
- HSV state tracking
- Multi-bulb support
- Statistics and inspection

**Setup (Loopback Aliases):**

Multi-bulb mode requires multiple loopback IP addresses. Setup varies by platform:

```bash
# Modern Linux (using ip command - recommended)
sudo ip addr add 127.0.0.2/8 dev lo
sudo ip addr add 127.0.0.3/8 dev lo
sudo ip addr add 127.0.0.4/8 dev lo

# Verify:
ip addr show lo | grep 127.0.0

# To remove later:
sudo ip addr del 127.0.0.2/8 dev lo
sudo ip addr del 127.0.0.3/8 dev lo
sudo ip addr del 127.0.0.4/8 dev lo
```

```bash
# Older Linux / macOS (using ifconfig)
sudo ifconfig lo:1 127.0.0.2 up
sudo ifconfig lo:2 127.0.0.3 up
sudo ifconfig lo:3 127.0.0.4 up

# Verify:
ifconfig | grep 127.0.0

# To remove later (Linux):
sudo ifconfig lo:1 down
sudo ifconfig lo:2 down
sudo ifconfig lo:3 down

# To remove later (macOS):
sudo ifconfig lo0 -alias 127.0.0.2
sudo ifconfig lo0 -alias 127.0.0.3
sudo ifconfig lo0 -alias 127.0.0.4
```

**Windows:**
Loopback aliases are not easily supported. Instead, run emulators on different ports:

```bash
# Terminal 1: Zone 0
python -m amor.simulator.kasa_emulator --ip 127.0.0.1 --port 9999 --name "Zone 0"

# Terminal 2: Zone 1
python -m amor.simulator.kasa_emulator --ip 127.0.0.1 --port 9998 --name "Zone 1"

# Terminal 3: Zone 2
python -m amor.simulator.kasa_emulator --ip 127.0.0.1 --port 9997 --name "Zone 2"

# Terminal 4: Zone 3
python -m amor.simulator.kasa_emulator --ip 127.0.0.1 --port 9996 --name "Zone 3"
```

Then update `amor/config/lighting.test.yaml` to use these ports.

**Usage:**
```bash
# Single bulb
python3 -m amor.simulator.kasa_emulator --ip 127.0.0.1 --name "Test Bulb"

# Multi-bulb mode (4 zones)
python3 -m amor.simulator.kasa_emulator --multi
```

**API:**
```python
from amor.simulator.kasa_emulator import KasaBulbEmulator

emulator = KasaBulbEmulator(ip="127.0.0.1", port=9999, name="Test")
emulator.run()  # Blocking

# State inspection
state = emulator.get_state()
print(f"HSV: {state['hue']}, {state['saturation']}, {state['brightness']}")
```

## Integration Testing

### Using Procfile

The `Procfile.test` orchestrates all emulators + amor components:

```bash
# Install honcho (Procfile runner)
pip install honcho

# Run full integration test environment
honcho -f Procfile.test start

# Run specific components
honcho -f Procfile.test start ppg0,processor,audio
```

### Manual Testing

```bash
# Terminal 1: Start emulated PPG sensors
python3 -m amor.simulator.ppg_emulator --ppg-id 0 --bpm 72 &
python3 -m amor.simulator.ppg_emulator --ppg-id 1 --bpm 68 &

# Terminal 2: Start processor
python3 -m amor.processor

# Terminal 3: Start emulated Launchpad
python3 -m amor.simulator.launchpad_emulator --interactive

# Terminal 4: Start emulated bulbs (requires loopback setup)
python3 -m amor.simulator.kasa_emulator --multi

# Terminal 5: Start audio/sequencer/lighting with test config
python3 -m amor.audio &
python3 -m amor.sequencer &
python3 -m amor.lighting --config amor/config/lighting.test.yaml
```

## Test Scenarios

### End-to-End Beat Flow

1. Start all components via Procfile.test
2. PPG emulators → processor → beat detection
3. Beats routed to audio engine and lighting
4. Verify audio playback and bulb state changes

### Sequencer Control

1. Start emulated Launchpad in interactive mode
2. Press PPG selection buttons: `p 0 5`
3. Toggle loops: `t 3`
4. Verify LED state updates: `s`

### Error Recovery

1. Trigger dropouts in PPG: `emulator.trigger_dropout(beats=2)`
2. Stop/restart components
3. Verify graceful recovery and reconnection

## Architecture Notes

- All emulators use OSC/TCP protocols matching real hardware
- No hardware dependencies for CI/CD integration
- Emulators expose same interfaces as production hardware
- State inspection APIs for automated test assertions

## Protocol Verification

To verify the Kasa emulator works with python-kasa library:

```bash
# Install python-kasa (if not already installed)
pip install 'python-kasa>=0.6.0'

# Terminal 1: Start emulator
python3 -m amor.simulator.kasa_emulator

# Terminal 2: Run protocol test
python3 testing/test_kasa_protocol.py
```

The test verifies that the emulator responds correctly to IotBulb.set_hsv() commands from the python-kasa library.

## Troubleshooting

**Kasa emulator connection issues:**
- Verify loopback aliases are configured: `ifconfig | grep 127.0.0`
- Check no other process is using port 9999: `lsof -i :9999`
- Run protocol test to verify compatibility: `python3 testing/test_kasa_protocol.py`

**PPG emulator not sending data:**
- Verify processor is listening on port 8000
- Check firewall rules for UDP port 8000

**Launchpad LED state not updating:**
- Verify sequencer is running and sending to port 8005
- Check emulator started successfully: look for "listening" message
