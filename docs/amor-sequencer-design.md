# Amor Sequencer & Launchpad Integration Design

**Version:** 1.0
**Date:** 2025-11-11
**Status:** Design Phase

---

## Overview

Extends the Amor heartbeat installation with interactive sample selection and ambient loop control via Novation Launchpad Mini MK3. Adds stateful sequencer to translate heartbeat predictions into musical choices with visual feedback.

**Problem:** Current system is stateless (beat detected → fixed sample). Need dynamic sample selection per PPG sensor and ambient loop layering.

**Solution:** Sequencer module maintains musical state (sample selections, active loops). Launchpad bridge translates MIDI button presses to OSC control messages and beat predictions to LED feedback.

---

## Architecture

```
┌──────────────┐
│ ESP32 Units  │
│ (×4 PPG)     │
└──────┬───────┘
       │ /ppg/{0-3} [samples, timestamp]
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Processor (amor/processor.py)                          │
│ Port 8000 in, Port 8001 out                              │
└──────────────────────┬───────────────────────────────────┘
                       │ /beat/{0-3} [timestamp, bpm, intensity]
                       │
       ┌───────────────┼───────────────┬──────────────┐
       │               │               │              │
       ▼               ▼               ▼              ▼
┌──────────┐   ┌──────────────┐   ┌─────────┐   ┌──────────┐
│ Viewer   │   │ Sequencer    │   │ Lighting│   │ Audio    │
│ (8001)   │   │ (8001 in)    │   │ (8002)  │   │ (8004 in)│
└──────────┘   │              │   └─────▲───┘   └────▲─────┘
               │              │         │            │
               │    State:    │         │            │
               │    - sample  │         │            │
               │      map     │         │            │
               │    - loop    ├─────────┴────────────┘
               │      status  │ /play/{ppg_id} [sample_id, voice_limit]
               │              │ /loop/start [loop_id]
               │              │ /loop/stop [loop_id]
               │              │ /lighting/pulse/{ppg_id} [color]
               └──────▲───┬───┘
                      │   │ /led/{row}/{col} [color, mode]
                 8003 │   │ 8005
                      │   ▼
               ┌──────┴────────┐
               │ Launchpad     │
               │ Bridge        │
               │ (MIDI ↔ OSC)  │
               └───────────────┘
                      │
                      ▼
               ┌──────────────┐
               │ Launchpad    │
               │ Mini MK3     │
               │ (USB MIDI)   │
               └──────────────┘
```

---

## Port Allocation

| Port | Direction | Purpose |
|------|-----------|---------|
| 8000 | ESP32 → Processor | Raw PPG data |
| 8001 | Processor → All | Beat predictions (broadcast) |
| 8002 | Processor → Lighting | Beat events (legacy, will deprecate) |
| 8003 | Launchpad → Sequencer | Control messages (button presses) |
| 8004 | Sequencer → Audio | Play commands with voice management |
| 8005 | Sequencer → Launchpad | LED feedback |

**Note:** Sequencer replaces Processor as source for Lighting commands (sends enhanced `/lighting/pulse` with color info).

---

## Component: Sequencer (amor/sequencer.py)

### Purpose
Stateful coordinator that receives beat predictions, maintains sample/loop selections, and broadcasts play commands to audio and lighting with appropriate parameters.

### Responsibilities
1. Listen on port 8001 for `/beat/{ppg_id}` from Processor
2. Listen on port 8003 for control messages from Launchpad Bridge
3. Maintain state:
   - `sample_map: dict[int, int]` - PPG ID → selected column (0-7)
   - `loop_status: dict[int, bool]` - Loop ID (0-31) → active/inactive
4. On beat received:
   - Look up selected sample for that PPG
   - Send `/play/{ppg_id}` to Audio (8004) with sample ID and voice limit
   - Send `/lighting/pulse/{ppg_id}` to Lighting (8002) with BPM-derived color
   - Send LED feedback to Launchpad (8005)
5. On control message:
   - Update state
   - Send loop start/stop to Audio
   - Send LED state updates to Launchpad

### State Structure
```python
class SequencerState:
    # Sample selection: which column (0-7) is active for each PPG row (0-3)
    sample_map: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}  # Default: column 0

    # Loop status: rows 4-7, columns 0-7 = 32 possible loops
    # loop_id = (row - 4) * 8 + col, range 0-31
    loop_status: dict[int, bool] = {}  # True = playing, False/absent = stopped

    # Voice limits per sample (configurable)
    voice_limit: int = 3  # Max concurrent instances per sample
```

### OSC Input (Port 8001)
```
/beat/{ppg_id} [timestamp, bpm, intensity]
  - From: Processor
  - ppg_id: 0-3
  - timestamp: float (Unix seconds)
  - bpm: float
  - intensity: float (0.0-1.0)
```

### OSC Input (Port 8003)
```
/select/{ppg_id} [column]
  - From: Launchpad Bridge
  - ppg_id: 0-3
  - column: 0-7
  - Action: Update sample_map, send LED feedback

/loop/toggle [loop_id]
  - From: Launchpad Bridge
  - loop_id: 0-31 (row 4-7, col 0-7)
  - Action: Toggle loop_status, send play/stop command

/loop/momentary [loop_id] [state]
  - From: Launchpad Bridge
  - loop_id: 0-31
  - state: 1 (pressed) or 0 (released)
  - Action: Start on press, stop on release
```

### OSC Output (Port 8004 → Audio)
```
/play/{ppg_id} [sample_id, voice_limit]
  - ppg_id: 0-3
  - sample_id: 0-7 (column index)
  - voice_limit: 2-3 (max concurrent instances)

/loop/start [loop_id]
  - loop_id: 0-31
  - Audio loads and plays loop from config

/loop/stop [loop_id]
  - loop_id: 0-31
  - Audio fades out and stops loop
```

### OSC Output (Port 8002 → Lighting)
```
/lighting/pulse/{ppg_id} [hue, intensity]
  - ppg_id: 0-3
  - hue: 0-360 (derived from BPM, same as current lighting logic)
  - intensity: 0.0-1.0 (from beat message)
```

### OSC Output (Port 8005 → Launchpad)
```
/led/{row}/{col} [color, mode]
  - row: 0-7
  - col: 0-7
  - color: 0-127 (Launchpad color palette index)
  - mode: 0 (static), 1 (pulse), 2 (flash)
```

### Implementation Notes
- Use `amor.osc.ReusePortThreadingOSCUDPServer` for port 8001 (share with viewer)
- Use `amor.osc.MessageStatistics` for monitoring
- Load sample config from `amor/config/samples.yaml` on startup
- Map BPM to hue using existing formula from lighting controller
- Beat pulse logic (Option 3c):
  - On `/beat/{ppg_id}`, send LED updates:
    - All buttons in row `ppg_id`: `/led/{row}/{col} [dim_color, 2]` (flash)
    - Selected button: `/led/{row}/{selected_col} [bright_color, 1]` (pulse)
  - Color derived from BPM (same as lighting)

---

## Component: Launchpad Bridge (amor/launchpad.py)

### Purpose
Bidirectional translator between Launchpad Mini MK3 MIDI messages and OSC control/feedback. Handles button press events and LED control.

### Responsibilities
1. Open Launchpad Mini MK3 MIDI ports (USB)
2. Listen for MIDI note on/off messages (button presses)
3. Translate to OSC control messages → Sequencer (8003)
4. Listen on port 8005 for LED commands from Sequencer
5. Translate to MIDI SysEx/CC for LED control
6. Handle Launchpad session mode vs programmer mode

### Launchpad Grid Mapping
```
Launchpad 8×8 grid (MIDI notes 11-18, 21-28, ..., 81-88):

Row 0 (PPG 0): Notes 11-18 → Columns 0-7 → Sample selection
Row 1 (PPG 1): Notes 21-28 → Columns 0-7 → Sample selection
Row 2 (PPG 2): Notes 31-38 → Columns 0-7 → Sample selection
Row 3 (PPG 3): Notes 41-48 → Columns 0-7 → Sample selection
Row 4 (Loop):  Notes 51-58 → Columns 0-7 → Latching loops (0-7)
Row 5 (Loop):  Notes 61-68 → Columns 0-7 → Latching loops (8-15)
Row 6 (Loop):  Notes 71-78 → Columns 0-7 → Momentary loops (16-23)
Row 7 (Loop):  Notes 81-88 → Columns 0-7 → Momentary loops (24-31)
```

**MIDI Note Calculation:**
```python
def note_to_row_col(note: int) -> tuple[int, int]:
    """Convert Launchpad MIDI note to row/column."""
    row = (note // 10) - 1
    col = (note % 10) - 1
    return row, col

def row_col_to_note(row: int, col: int) -> int:
    """Convert row/column to Launchpad MIDI note."""
    return ((row + 1) * 10) + (col + 1)
```

### MIDI Input Handling
```python
def handle_note_on(note, velocity):
    row, col = note_to_row_col(note)

    if row in [0, 1, 2, 3]:  # PPG sample selection
        ppg_id = row
        send_osc("/select/{ppg_id}", [col])

    elif row in [4, 5]:  # Latching loops
        loop_id = (row - 4) * 8 + col
        send_osc("/loop/toggle", [loop_id])

    elif row in [6, 7]:  # Momentary loops
        loop_id = (row - 4) * 8 + col
        send_osc("/loop/momentary", [loop_id, 1])

def handle_note_off(note, velocity):
    row, col = note_to_row_col(note)

    if row in [6, 7]:  # Momentary release
        loop_id = (row - 4) * 8 + col
        send_osc("/loop/momentary", [loop_id, 0])
```

### OSC Input (Port 8005 from Sequencer)
```
/led/{row}/{col} [color, mode]
  - Set LED at row/col to color with mode (static/pulse/flash)
```

### LED Control via MIDI
Launchpad Mini MK3 uses MIDI Note velocity or SysEx for LED control:

**Simple method (MIDI Note On):**
```python
def set_led(row, col, color, mode):
    """Set LED color using MIDI Note On velocity."""
    note = row_col_to_note(row, col)
    # Launchpad velocity maps to color palette (0-127)
    midi_out.send_message([0x90, note, color])  # Note On, channel 0
```

**Advanced method (SysEx for RGB):**
```python
def set_led_rgb(row, col, r, g, b):
    """Set LED to custom RGB using SysEx."""
    note = row_col_to_note(row, col)
    sysex = [0xF0, 0x00, 0x20, 0x29, 0x02, 0x0D, 0x03,
             0x03, note, r, g, b, 0xF7]
    midi_out.send_message(sysex)
```

**Pulse/Flash modes:**
- Pulse: Send with higher velocity, let Launchpad fade naturally, or implement timer
- Flash: Send high velocity, wait 100ms, send low velocity (or off)
- Implement as timed callbacks in bridge event loop

### Libraries
- **python-rtmidi** or **mido**: MIDI I/O
- **pythonosc**: OSC I/O

### Implementation Notes
- Use `mido` for MIDI (simpler API than rtmidi)
- Launchpad must be in **Programmer Mode** for direct note access
  - Enter via SysEx: `F0 00 20 29 02 0D 0E 01 F7`
  - Exit on disconnect or send: `F0 00 20 29 02 0D 0E 00 F7`
- Handle USB disconnection gracefully (poll for device, reconnect)
- LED feedback timing: debounce rapid updates (max 60 LED msgs/sec to avoid MIDI overflow)

---

## Configuration: amor/config/samples.yaml

### Structure
```yaml
# Sample voice management
voice_limit: 3  # Max concurrent instances per sample

# PPG sample banks (rows 0-3, columns 0-7)
ppg_samples:
  0:  # PPG sensor 0 / Row 0
    - sounds/ppg/tubular_bell_C.wav
    - sounds/ppg/tubular_bell_D.wav
    - sounds/ppg/tubular_bell_E.wav
    - sounds/ppg/tubular_bell_F.wav
    - sounds/ppg/tubular_bell_G.wav
    - sounds/ppg/tubular_bell_A.wav
    - sounds/ppg/tubular_bell_B.wav
    - sounds/ppg/tubular_bell_C2.wav
  1:  # PPG sensor 1 / Row 1
    - sounds/ppg/singing_bowl_low.wav
    - sounds/ppg/singing_bowl_mid.wav
    - sounds/ppg/singing_bowl_high.wav
    - sounds/ppg/tingsha.wav
    - sounds/ppg/windchime_1.wav
    - sounds/ppg/windchime_2.wav
    - sounds/ppg/kalimba_C.wav
    - sounds/ppg/kalimba_E.wav
  2:  # PPG sensor 2 / Row 2
    - sounds/ppg/water_drop_1.wav
    - sounds/ppg/water_drop_2.wav
    - sounds/ppg/wood_block.wav
    - sounds/ppg/temple_block.wav
    - sounds/ppg/finger_cymbal.wav
    - sounds/ppg/triangle.wav
    - sounds/ppg/glass_clink.wav
    - sounds/ppg/bell_tree.wav
  3:  # PPG sensor 3 / Row 3
    - sounds/ppg/harmonics/harmonic_1.wav
    - sounds/ppg/harmonics/harmonic_2.wav
    - sounds/ppg/harmonics/harmonic_3.wav
    - sounds/ppg/harmonics/harmonic_5.wav
    - sounds/ppg/harmonics/harmonic_7.wav
    - sounds/ppg/harmonics/harmonic_9.wav
    - sounds/ppg/drone_C.wav
    - sounds/ppg/drone_G.wav

# Ambient loops (rows 4-7, columns 0-7 = 32 slots)
ambient_loops:
  latching:  # Rows 4-5 (loop IDs 0-15)
    - sounds/loops/rain_light.wav
    - sounds/loops/rain_heavy.wav
    - sounds/loops/ocean_waves.wav
    - sounds/loops/forest_ambience.wav
    - sounds/loops/night_crickets.wav
    - sounds/loops/wind_gentle.wav
    - sounds/loops/birds_dawn.wav
    - sounds/loops/stream_flowing.wav
    - sounds/loops/pad_Am.wav
    - sounds/loops/pad_Em.wav
    - sounds/loops/pad_Dm.wav
    - sounds/loops/drone_deep.wav
    - sounds/loops/texture_shimmer.wav
    - sounds/loops/texture_granular.wav
    - sounds/loops/bells_distant.wav
    - sounds/loops/voices_ah.wav

  momentary:  # Rows 6-7 (loop IDs 16-31)
    - sounds/loops/riser_buildup.wav
    - sounds/loops/riser_sweep_up.wav
    - sounds/loops/sweep_down.wav
    - sounds/loops/fx_reverse_cymbal.wav
    - sounds/loops/fx_thunder.wav
    - sounds/loops/fx_wind_gust.wav
    - sounds/loops/transition_whoosh.wav
    - sounds/loops/impact_low.wav
    - sounds/loops/stinger_1.wav
    - sounds/loops/stinger_2.wav
    - sounds/loops/glitch_texture.wav
    - sounds/loops/noise_white.wav
    - sounds/loops/noise_pink.wav
    - sounds/loops/sub_pulse.wav
    - sounds/loops/bass_rumble.wav
    - sounds/loops/drone_dissonant.wav
```

### Loading & Validation
```python
import yaml
from pathlib import Path

def load_config(config_path: str = "amor/config/samples.yaml"):
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Validate structure
    assert "ppg_samples" in config
    assert all(i in config["ppg_samples"] for i in range(4))
    assert all(len(samples) == 8 for samples in config["ppg_samples"].values())

    assert "ambient_loops" in config
    assert len(config["ambient_loops"]["latching"]) == 16
    assert len(config["ambient_loops"]["momentary"]) == 16

    # Validate file existence
    for ppg_id, samples in config["ppg_samples"].items():
        for sample in samples:
            assert Path(sample).exists(), f"Missing: {sample}"

    for category in ["latching", "momentary"]:
        for loop in config["ambient_loops"][category]:
            assert Path(loop).exists(), f"Missing: {loop}"

    return config
```

---

## Audio Engine Integration

### Updated Responsibilities
Audio engine (`amor/audio.py`) must be modified to:

1. **Listen on port 8004** (instead of 8001)
2. **Handle new OSC routes:**
   - `/play/{ppg_id} [sample_id, voice_limit]`
   - `/loop/start [loop_id]`
   - `/loop/stop [loop_id]`
3. **Implement voice limiting** per sample
4. **Load samples from YAML config** instead of fixed filenames

### Voice Management Implementation
```python
class VoiceManager:
    """Manages concurrent sample instances with voice limiting."""

    def __init__(self, voice_limit: int = 3):
        self.voice_limit = voice_limit
        # Track active streams per (ppg_id, sample_id)
        self.active_voices: dict[tuple[int, int], list[sd.OutputStream]] = {}

    def play_sample(self, ppg_id: int, sample_id: int, audio_data: np.ndarray):
        """Play sample with voice limiting."""
        key = (ppg_id, sample_id)

        # Remove finished streams
        if key in self.active_voices:
            self.active_voices[key] = [s for s in self.active_voices[key] if s.active]

        # Check voice limit
        if key in self.active_voices and len(self.active_voices[key]) >= self.voice_limit:
            # Stop oldest voice
            oldest = self.active_voices[key].pop(0)
            oldest.stop()
            oldest.close()

        # Start new voice
        stream = sd.OutputStream(
            samplerate=44100,
            channels=len(audio_data.shape),
            callback=make_callback(audio_data)
        )
        stream.start()

        if key not in self.active_voices:
            self.active_voices[key] = []
        self.active_voices[key].append(stream)
```

### Loop Management
```python
class LoopManager:
    """Manages ambient loop playback with start/stop control."""

    def __init__(self):
        self.active_loops: dict[int, sd.OutputStream] = {}

    def start_loop(self, loop_id: int, audio_data: np.ndarray):
        """Start looping sample."""
        if loop_id in self.active_loops:
            return  # Already playing

        stream = sd.OutputStream(
            samplerate=44100,
            channels=len(audio_data.shape),
            callback=make_looping_callback(audio_data)
        )
        stream.start()
        self.active_loops[loop_id] = stream

    def stop_loop(self, loop_id: int, fade_ms: int = 500):
        """Stop loop with optional fade-out."""
        if loop_id not in self.active_loops:
            return

        stream = self.active_loops.pop(loop_id)
        # TODO: Implement fade-out before stop
        stream.stop()
        stream.close()
```

---

## Lighting Controller Integration

### Updated Input
Lighting controller should:

1. **Continue listening on port 8002** for compatibility
2. **Handle new route:** `/lighting/pulse/{ppg_id} [hue, intensity]`
3. **Use provided hue** instead of calculating from BPM (Sequencer does this now)

### Why This Change?
- Sequencer becomes central coordinator for beat interpretation
- Lighting gets pre-processed color info
- Allows future enhancements (e.g., sample-specific colors, user color overrides via Launchpad)

---

## LED Feedback Colors

### Color Palette Strategy
Launchpad Mini MK3 has 128-color palette. Map to installation aesthetics:

**PPG Rows (0-3):**
- Unselected: Dim blue (palette index 45)
- Selected (static): Bright cyan (palette index 37)
- Beat flash (all): Medium purple (palette index 49), 100ms flash
- Beat pulse (selected): Bright magenta (palette index 53), 200ms fade

**Loop Rows (4-7):**
- Inactive: Off (palette index 0)
- Active (latching): Green (palette index 21)
- Active (momentary, pressed): Yellow (palette index 13)

**BPM-derived colors (optional future):**
Map BPM to Launchpad color for beat flashes:
- 40-60 BPM: Blue (45)
- 60-80 BPM: Purple (49)
- 80-100 BPM: Pink (53)
- 100-120 BPM: Red (5)

---

## Startup Sequence

### 1. Sequencer
```bash
python -m amor.sequencer
```
- Load config from `amor/config/samples.yaml`
- Start OSC servers on 8001 (reuse), 8003
- Initialize state (all PPGs → column 0, all loops off)
- Print "Sequencer ready, listening for beats and controls"

### 2. Launchpad Bridge
```bash
python -m amor.launchpad
```
- Detect Launchpad Mini MK3 via MIDI
- Enter Programmer Mode (SysEx)
- Start OSC server on 8005
- Initialize LED grid (all PPG rows: column 0 selected)
- Print "Launchpad bridge ready"

### 3. Audio Engine (Modified)
```bash
python -m amor.audio
```
- Load samples from `amor/config/samples.yaml`
- Pre-load all 32 samples + 32 loops into memory
- Start OSC server on 8004
- Print "Audio engine ready, {N} samples loaded"

### 4. Existing Components
- Processor (already running on 8001 output)
- Lighting controller (update to accept new route)
- Viewer (optional, unchanged)

---

## Testing Strategy

### Unit Tests
1. **Sequencer state management:**
   - Sample selection updates
   - Loop toggle logic
   - Voice limit enforcement

2. **Launchpad MIDI/OSC translation:**
   - Note-to-row/col conversion
   - Button press → OSC message
   - OSC LED command → MIDI output

### Integration Tests
1. **Sequencer + Mock Launchpad:**
   - Send control messages via OSC
   - Verify state updates
   - Verify outgoing play commands

2. **Sequencer + Mock Processor:**
   - Inject `/beat/{ppg_id}` messages
   - Verify correct sample selected
   - Verify LED feedback sent

3. **End-to-End (Manual):**
   - Press Launchpad button
   - Verify LED lights up
   - Trigger heartbeat via test script
   - Verify correct sample plays
   - Verify LED pulses

### Test Scripts
```python
# test_sequencer_state.py - Mock beat injection
from pythonosc import udp_client
import time

client = udp_client.SimpleUDPClient("127.0.0.1", 8001)
while True:
    client.send_message("/beat/0", [time.time(), 72.0, 0.5])
    time.sleep(60/72)  # 72 BPM
```

```python
# test_launchpad_control.py - Mock button presses
from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 8003)

# Select column 3 for PPG 0
client.send_message("/select/0", [3])

# Toggle loop 5 (row 4, col 5)
client.send_message("/loop/toggle", [5])
```

---

## Implementation Checklist

### Phase 1: Core Sequencer
- [ ] Create `amor/sequencer.py` skeleton
- [ ] Implement state structure (sample_map, loop_status)
- [ ] OSC server on 8001 (reuse port) + 8003
- [ ] Handle `/beat/{ppg_id}` → log state
- [ ] Handle `/select/{ppg_id}` → update state
- [ ] Handle `/loop/toggle` and `/loop/momentary`
- [ ] OSC clients for 8004 (audio), 8002 (lighting), 8005 (launchpad)
- [ ] Beat → play command logic
- [ ] Beat → lighting command with BPM→hue conversion
- [ ] Load YAML config

### Phase 2: Launchpad Bridge
- [ ] Create `amor/launchpad.py` skeleton
- [ ] Detect Launchpad via `mido`
- [ ] Enter Programmer Mode
- [ ] Handle MIDI Note On/Off → OSC (8003)
- [ ] OSC server on 8005 for LED commands
- [ ] OSC `/led/{row}/{col}` → MIDI velocity
- [ ] Implement pulse/flash timing
- [ ] Graceful USB disconnect handling

### Phase 3: Audio Engine Modifications
- [ ] Change input port from 8001 → 8004
- [ ] Add `/play/{ppg_id} [sample_id, voice_limit]` handler
- [ ] Add `/loop/start [loop_id]` handler
- [ ] Add `/loop/stop [loop_id]` handler
- [ ] Implement VoiceManager class
- [ ] Implement LoopManager class
- [ ] Load samples from YAML config
- [ ] Remove old `/beat/{ppg_id}` handler

### Phase 4: Integration
- [ ] Update lighting controller for `/lighting/pulse` route
- [ ] Create `amor/config/samples.yaml`
- [ ] Test sequencer + mock inputs
- [ ] Test launchpad bridge + mock inputs
- [ ] Test audio engine with new protocol
- [ ] End-to-end test with real Launchpad
- [ ] End-to-end test with real PPG sensors

---

## File Structure

```
corazonn/
├── amor/
│   ├── __init__.py
│   ├── osc.py                      # Existing shared utilities
│   ├── processor.py                # Existing (unchanged)
│   ├── viewer.py                   # Existing (unchanged)
│   ├── audio.py                    # MODIFIED: new port, new handlers
│   ├── sequencer.py                # NEW: state management
│   ├── launchpad.py                # NEW: MIDI ↔ OSC bridge
│   └── config/
│       └── samples.yaml            # NEW: sample/loop configuration
├── sounds/
│   ├── ppg/                        # PPG sample banks (4 × 8)
│   └── loops/                      # Ambient loops (32)
├── lighting/
│   └── lighting_controller.py      # MODIFIED: new OSC route
├── testing/
│   ├── test_sequencer_state.py     # NEW: mock beat injection
│   └── test_launchpad_control.py   # NEW: mock button presses
└── docs/
    ├── amor-technical-reference.md # Existing
    └── amor-sequencer-design.md    # This document
```

---

## Dependencies

Add to `requirements.txt`:
```
mido>=1.3.0           # MIDI I/O
python-rtmidi>=1.5.0  # MIDI backend for mido
PyYAML>=6.0           # Config file parsing
```

Existing dependencies (unchanged):
```
pythonosc>=1.8.0
sounddevice>=0.4.6
soundfile>=0.12.1
python-kasa>=0.5.0
numpy>=1.21.0
```

---

## Known Limitations & Future Work

### Limitations
1. **Voice management Option B only** - no envelope restart (Option C) in v1.0
2. **Fixed color palette** - no runtime color customization via Launchpad
3. **No sample hotswap** - requires restart to reload YAML config
4. **LED pulse timing approximate** - MIDI velocity, not precise PWM control

### Future Enhancements
1. **Envelope control (Option C):** Add fade-out on retrigger using rtmixer
2. **Launchpad color modes:** Hold side button + press pad to change color scheme
3. **Live config reload:** Watch `samples.yaml` for changes
4. **Sample preview:** Press+hold button to preview sample without triggering
5. **Tempo sync:** Quantize beat triggers to global tempo grid
6. **Recording:** Save button press sequences for playback
7. **Multi-launchpad:** Support 2+ Launchpads for expanded control

---

**End of Design Document**
