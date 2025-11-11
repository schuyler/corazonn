# Amor Sequencer & Launchpad Integration Design

**Version:** 1.0
**Date:** 2025-11-11
**Status:** Design Phase

---

## Problem Statement

Current Amor system is stateless: each PPG sensor triggers a fixed audio sample. No dynamic sample selection, no ambient loop control, no visual feedback during performance.

**Requirements:**
- Select different samples per PPG sensor during performance
- Layer ambient loops (nature sounds, pads)
- Visual feedback on controller showing beat pulses and active selections
- Maintain ambient aesthetic (sustained samples, not percussive)

---

## Solution Architecture

Add two components:
1. **Sequencer** - Stateful coordinator maintaining sample selections and loop status
2. **Launchpad Bridge** - Bidirectional MIDI ↔ OSC translator

**Design principle:** Sequencer owns musical state and decision-making. Launchpad Bridge is pure I/O translation.

---

## System Architecture

```
ESP32 Units (×4) → Processor (8000→8001) → /beat/{ppg_id}
                                                ↓
                    ┌───────────────────────────┼────────────┐
                    ↓                           ↓            ↓
                Sequencer (8001 in)         Viewer      Lighting (8002)
                    ↓                                        ↑
              [State Machine]                                │
                    ↓                                        │
            ┌───────┴────────┐                              │
            ↓                ↓                               │
        Audio (8004)    Launchpad (8005)                    │
                            ↑                                │
                    Launchpad Bridge (8003 in, 8005 out)    │
                            ↑                                │
                      USB MIDI Controller ──────────────────┘
                      (Novation Launchpad Mini MK3)
```

---

## Port Allocation

| Port | Direction | Purpose |
|------|-----------|---------|
| 8000 | ESP32 → Processor | Raw PPG data (existing) |
| 8001 | Processor → All | Beat predictions broadcast (existing) |
| 8002 | Sequencer → Lighting | Enhanced pulse commands with color |
| 8003 | Launchpad → Sequencer | Control messages (button presses) |
| 8004 | Sequencer → Audio | Play commands with voice management |
| 8005 | Sequencer → Launchpad | LED feedback |

**Key change:** Sequencer intercepts beats and coordinates downstream actions, replacing Processor as direct controller of Audio and Lighting.

---

## Component: Sequencer (amor/sequencer.py)

### Purpose
Central coordinator that maintains musical state and translates heartbeat predictions into playback commands.

### State
```python
sample_map: dict[int, int]      # PPG ID (0-3) → selected column (0-7)
loop_status: dict[int, bool]    # Loop ID (0-31) → active/inactive
voice_limit: int = 3            # Max concurrent instances per sample
```

### Responsibilities

**On beat received** (from Processor on 8001):
1. Look up selected sample for that PPG: `sample_id = sample_map[ppg_id]`
2. Send `/play/{ppg_id} [sample_id, voice_limit]` to Audio (8004)
3. Calculate hue from BPM, send `/lighting/pulse/{ppg_id} [hue, intensity]` to Lighting (8002)
4. Send LED pulse feedback to Launchpad Bridge (8005)

**On control message** (from Launchpad Bridge on 8003):
1. Update state (`sample_map` or `loop_status`)
2. Send loop start/stop commands to Audio (8004)
3. Send LED state updates to Launchpad Bridge (8005)

**On startup:**
1. Load YAML config (`amor/config/samples.yaml`)
2. Initialize state (all PPGs → column 0, all loops off)
3. Start OSC servers on 8001 (ReusePort), 8003

### OSC Protocol

**Input on 8001** (from Processor):
```
/beat/{ppg_id} [timestamp, bpm, intensity]
  ppg_id: 0-3
  timestamp: float (Unix seconds)
  bpm: float
  intensity: float (0.0-1.0)
```

**Input on 8003** (from Launchpad Bridge):
```
/select/{ppg_id} [column]
  ppg_id: 0-3, column: 0-7
  Action: Update sample_map, send LED feedback

/loop/toggle [loop_id]
  loop_id: 0-31 (rows 4-7, columns 0-7)
  Action: Toggle loop_status, send start/stop command

/loop/momentary [loop_id] [state]
  loop_id: 0-31, state: 1 (pressed) or 0 (released)
  Action: Start/stop loop based on button state
```

**Output on 8004** (to Audio):
```
/play/{ppg_id} [sample_id, voice_limit]
  sample_id: 0-7 (column index)
  voice_limit: 2-3

/loop/start [loop_id]
  loop_id: 0-31

/loop/stop [loop_id]
  loop_id: 0-31
```

**Output on 8002** (to Lighting):
```
/lighting/pulse/{ppg_id} [hue, intensity]
  hue: 0-360 (BPM-derived: 40 BPM = blue/240°, 120 BPM = red/0°)
  intensity: 0.0-1.0
```

**Output on 8005** (to Launchpad Bridge):
```
/led/{row}/{col} [color, mode]
  row: 0-7, col: 0-7
  color: 0-127 (Launchpad palette index)
  mode: 0 (static), 1 (pulse), 2 (flash)
```

### Beat Pulse LED Feedback (Option 3c)
On receiving `/beat/{ppg_id}`:
- All buttons in row `ppg_id`: flash briefly (dim color, 100ms)
- Selected button in that row: pulse brighter (200ms fade)
- Color derived from BPM (matches lighting controller)

---

## Component: Launchpad Bridge (amor/launchpad.py)

### Purpose
Pure I/O translator between Launchpad Mini MK3 MIDI and OSC protocol. No musical logic.

### Responsibilities

**MIDI → OSC** (button presses):
1. Open Launchpad Mini MK3 USB MIDI ports
2. Enter Programmer Mode (SysEx: `F0 00 20 29 02 0D 0E 01 F7`)
3. Listen for MIDI Note On/Off messages
4. Translate to OSC control messages → Sequencer (8003)

**OSC → MIDI** (LED feedback):
1. Listen on port 8005 for LED commands
2. Translate to MIDI Note On velocity (simple) or SysEx RGB (advanced)
3. Handle pulse/flash modes via timed callbacks

**On startup:**
1. Detect and connect to Launchpad
2. Initialize LED grid (column 0 selected for PPG rows, all loops off)

### Grid Mapping

Launchpad 8×8 grid maps to MIDI notes 11-18, 21-28, ..., 81-88:

```
Row 0 (PPG 0): Sample selection (8 columns)
Row 1 (PPG 1): Sample selection (8 columns)
Row 2 (PPG 2): Sample selection (8 columns)
Row 3 (PPG 3): Sample selection (8 columns)
Row 4: Latching loops 0-7
Row 5: Latching loops 8-15
Row 6: Momentary loops 16-23
Row 7: Momentary loops 24-31
```

**Note calculation:**
- MIDI note = `(row + 1) * 10 + (col + 1)`
- Row/col from note: `row = (note // 10) - 1`, `col = (note % 10) - 1`

**Loop ID calculation:**
- `loop_id = (row - 4) * 8 + col` (range 0-31)

### Button Behavior

**PPG rows (0-3):** Radio button selection
- Press button → deselect old, select new
- Send `/select/{ppg_id} [column]` to Sequencer

**Loop rows 4-5:** Latching toggles
- Press button → toggle on/off
- Send `/loop/toggle [loop_id]` to Sequencer

**Loop rows 6-7:** Momentary triggers
- Press → send `/loop/momentary [loop_id] [1]`
- Release → send `/loop/momentary [loop_id] [0]`

### LED Colors

**PPG rows:**
- Unselected: Dim blue (palette 45)
- Selected static: Bright cyan (palette 37)
- Beat flash (all): Medium purple (palette 49)
- Beat pulse (selected): Bright magenta (palette 53)

**Loop rows:**
- Inactive: Off (palette 0)
- Active latching: Green (palette 21)
- Active momentary (pressed): Yellow (palette 13)

---

## Configuration: amor/config/samples.yaml

### Structure

```yaml
voice_limit: 3

ppg_samples:
  0:  # Row 0 - Tubular bells
    - sounds/ppg/tubular_bell_C.wav
    - sounds/ppg/tubular_bell_D.wav
    # ... 8 total samples
  1:  # Row 1 - Singing bowls / wind chimes
    - sounds/ppg/singing_bowl_low.wav
    # ... 8 total samples
  2:  # Row 2 - Water / wood / metal transients
    - sounds/ppg/water_drop_1.wav
    # ... 8 total samples
  3:  # Row 3 - Harmonics / drones
    - sounds/ppg/harmonics/harmonic_1.wav
    # ... 8 total samples

ambient_loops:
  latching:  # 16 loops for rows 4-5
    - sounds/loops/rain_light.wav
    - sounds/loops/ocean_waves.wav
    - sounds/loops/forest_ambience.wav
    - sounds/loops/pad_Am.wav
    # ... 16 total loops

  momentary:  # 16 loops for rows 6-7
    - sounds/loops/riser_buildup.wav
    - sounds/loops/fx_thunder.wav
    - sounds/loops/stinger_1.wav
    # ... 16 total loops
```

**Total samples:** 32 PPG samples (4 rows × 8 columns) + 32 ambient loops

**Validation requirements:**
- Exactly 4 PPG sample banks
- Exactly 8 samples per bank
- Exactly 16 latching loops
- Exactly 16 momentary loops
- All file paths exist

---

## Audio Engine Integration (amor/audio.py)

### Required Changes

**1. Change input port:** 8001 → 8004

**2. Remove old handler:** `/beat/{ppg_id}` (no longer receives beats directly)

**3. Add new handlers:**
- `/play/{ppg_id} [sample_id, voice_limit]`
- `/loop/start [loop_id]`
- `/loop/stop [loop_id]`

**4. Implement voice management:**

Track active streams per `(ppg_id, sample_id)` tuple. When voice limit reached, stop oldest stream before starting new one.

**Why voice limiting?** Sustained samples (tubular bells, singing bowls) have long decay. At 60-90 BPM with 4 sensors, you'd trigger 4-6 samples per second. Without limiting, you'd have 50+ overlapping instances within 10 seconds. Voice limit 2-3 allows polyrhythmic shimmer without mud.

**Alternative (Option C):** Envelope restart - fade out current instance when new trigger arrives. More "gated" feel. Requires envelope control (rtmixer). Not implemented in v1.0.

**5. Loop management:**

Latching loops play continuously until stopped. Momentary loops start on press, stop on release. All loops layer freely (no ducking). Optional: add fade-out on stop (500ms) for smooth transitions.

**6. Load samples from YAML:** Replace fixed filenames (`ppg_0.wav`, etc.) with dynamic loading from config.

---

## Lighting Controller Integration

### Required Changes

**Continue listening on port 8002** but handle new route:

```
/lighting/pulse/{ppg_id} [hue, intensity]
```

**Key difference:** Hue is pre-calculated by Sequencer (from BPM). Lighting controller no longer needs to derive color from BPM.

**Why this change?**
- Sequencer becomes single source of truth for beat interpretation
- Enables future enhancements: sample-specific colors, user color overrides via Launchpad
- Simplifies lighting controller logic

**Backward compatibility:** Can keep old `/beat/{ppg_id}` handler if needed, but Sequencer won't send it.

---

## Design Rationale

### Why Separate Sequencer + Launchpad Bridge?

**Alternative considered:** Single module handling both MIDI and state.

**Rejected because:**
- Mixing MIDI I/O with musical logic makes testing harder
- Can't easily swap controllers (e.g., APC40, Push)
- Sequencer can run without Launchpad for testing

**Chosen design:**
- Launchpad Bridge: Pure I/O, no state, easily swappable
- Sequencer: Pure logic, testable with mock OSC messages
- Clean separation of concerns

### Why Voice Limiting (Option B) Over Envelope Restart (Option C)?

**Option B (voice limiting):**
- Simpler implementation (sounddevice native)
- Allows natural shimmer/cluster effects (good for bells)
- Sustains overlap until voice limit reached

**Option C (envelope restart):**
- Requires envelope control (rtmixer or manual fade)
- More "gated" feel - each trigger cuts previous
- Better for rhythmic clarity

**Decision:** Start with Option B for simplicity. Add Option C later if voice limiting sounds too harsh/choppy.

### Why Sequencer Coordinates Lighting?

**Alternative considered:** Processor sends beats to Lighting directly (current design), Sequencer only controls Audio.

**Rejected because:**
- Duplicates BPM→hue calculation logic
- Future features (sample-specific colors, Launchpad color control) require Sequencer awareness

**Chosen design:**
- Sequencer is single coordinator for all beat-triggered actions
- Lighting receives pre-processed color info
- Enables future: "hold Launchpad button to change that sensor's color"

### Why YAML Config Over Code?

**Alternative considered:** Hardcode sample paths in audio.py.

**Rejected because:**
- Every sample change requires code edit and restart
- Can't easily try different sound libraries
- No validation of file existence at startup

**Chosen design:**
- YAML config loaded at startup
- Validation fails early if files missing
- Easy to swap entire sample libraries (e.g., "use meditative sounds" vs "use nature sounds")

---

## Testing Strategy

### Unit Tests

**Sequencer:**
- State updates on control messages
- Correct sample selected on beat received
- BPM→hue calculation matches lighting controller

**Launchpad Bridge:**
- MIDI note → row/col conversion
- Row/col → loop ID calculation
- Button press → correct OSC message

### Integration Tests

**Sequencer + Mock Processor:**
- Inject `/beat/{ppg_id}` messages
- Verify `/play/{ppg_id}` sent to Audio
- Verify LED feedback sent to Launchpad

**Sequencer + Mock Launchpad:**
- Send `/select/{ppg_id}` control messages
- Verify state updated
- Verify LED state updates sent

**End-to-End (Manual):**
1. Press Launchpad button → verify LED lights
2. Trigger heartbeat (test script or real sensor) → verify sample plays
3. Verify LED pulses on beat
4. Toggle loop → verify loop starts/stops
5. Test momentary loop (hold/release)

### Test Scripts

- `testing/test_beat_injection.py` - Send `/beat/{ppg_id}` messages to port 8001
- `testing/test_launchpad_control.py` - Send `/select` and `/loop/*` messages to port 8003

---

## Implementation Phases

**Phase 1: Sequencer Core**
- State management
- OSC servers and clients
- Handle `/beat/{ppg_id}` → log state
- Handle control messages → update state
- Load YAML config

**Phase 2: Launchpad Bridge**
- MIDI I/O (mido library)
- Enter Programmer Mode
- Button press → OSC messages
- OSC LED commands → MIDI output
- Pulse/flash timing

**Phase 3: Audio Engine Modifications**
- Port change (8001 → 8004)
- New OSC handlers
- Voice limiting implementation
- Loop management
- YAML config loading

**Phase 4: Integration**
- Update lighting controller
- End-to-end testing
- Real Launchpad testing
- Real PPG sensor testing

---

## Known Limitations & Future Work

### Limitations
1. Voice management Option B only (no envelope restart in v1.0)
2. Fixed color palette (no runtime customization)
3. No sample hotswap (requires restart to reload config)
4. LED pulse timing approximate (MIDI velocity, not PWM)

### Future Enhancements
1. **Envelope control (Option C):** Fade-out on retrigger using rtmixer
2. **Color customization:** Hold side button + press pad to assign color
3. **Live config reload:** Watch YAML file for changes
4. **Sample preview:** Press+hold to preview without triggering
5. **Tempo sync:** Quantize beats to global tempo grid
6. **Recording:** Save button sequences for playback
7. **Multi-launchpad:** Support multiple controllers for expanded control

---

## Dependencies

**New:** `mido`, `python-rtmidi`, `PyYAML`

**Existing:** `pythonosc`, `sounddevice`, `soundfile`, `numpy`, `python-kasa` (lighting only)

---

## Summary

This design adds interactive control to Amor via Launchpad Mini MK3 while maintaining the existing processor/audio/lighting architecture. Key decisions:

1. **Sequencer as coordinator:** Centralizes musical state and decision-making
2. **Voice limiting:** Prevents mud from overlapping sustained samples
3. **LED feedback Option 3c:** Row flash + selected button pulse shows both beat and selection
4. **YAML config:** Easy sample library management without code changes
5. **Clean separation:** Launchpad Bridge is pure I/O, Sequencer is pure logic

Implementation proceeds in phases: Sequencer core → Launchpad bridge → Audio mods → Integration.
