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
ESP32 Units (×4) → Processor (8000→8001) → /beat/{ppg_id} (broadcast)
                                                ↓
                    ┌───────────────────────────┼──────────────────┐
                    ↓                           ↓                  ↓
                Audio (8001)              Launchpad Bridge    Lighting (8002)
                    ↑                           ↑
                    │ /route/{ppg_id}           │ /beat/{ppg_id}
                    │ /loop/*                   │ (LED pulses)
                    │                           │
                Sequencer ←───────────────── Launchpad Bridge
              (State Machine)   /select        (MIDI ↔ OSC)
                    ↓           /loop/*             ↑
                    │ /led/*                        │
                    └───────────────────────────────┘
                                                    │
                                          Launchpad Mini MK3 (USB)
```

---

## Port Allocation

| Port | Direction | Purpose |
|------|-----------|---------|
| 8000 | ESP32 → Processor | Raw PPG data (existing) |
| 8001 | Processor → All | Beat predictions broadcast (existing) |
| 8002 | Processor → Lighting | Beat events (existing, unchanged) |
| 8003 | Launchpad → Sequencer | Control messages (button presses) |
| 8004 | Sequencer → Audio | Routing updates and loop control |
| 8005 | Sequencer → Launchpad | LED feedback |

**Key change:** Audio and Lighting listen to beats directly on 8001. Sequencer only sends routing updates when selections change.

---

## Component: Sequencer (amor/sequencer.py)

### Purpose
State manager for sample selections and loop status. Translates Launchpad input to routing updates for audio engine.

### State
```python
sample_map: dict[int, int]      # PPG ID (0-3) → selected column (0-7)
loop_status: dict[int, bool]    # Loop ID (0-31) → active/inactive
voice_limit: int = 3            # Max concurrent instances per sample
```

### Responsibilities

**On control message** (from Launchpad Bridge on 8003):
1. Update state (`sample_map` or `loop_status`)
2. Send routing update `/route/{ppg_id} [sample_id]` to Audio (8004)
3. Send loop start/stop commands to Audio (8004)
4. Send LED state updates to Launchpad Bridge (8005)

**On startup:**
1. Load YAML config (`amor/config/samples.yaml`)
2. Initialize state (all PPGs → column 0, all loops off)
3. Send initial routing to Audio: `/route/{0-3} [0]`
4. Start OSC server on 8003

### OSC Protocol

**Input on 8003** (from Launchpad Bridge):
```
/select/{ppg_id} [column]
  ppg_id: 0-3, column: 0-7
  Action: Update sample_map, send routing update to Audio, update LEDs

/loop/toggle [loop_id]
  loop_id: 0-31 (rows 4-7, columns 0-7)
  Action: Toggle loop_status, send start/stop to Audio, update LEDs

/loop/momentary [loop_id] [state]
  loop_id: 0-31, state: 1 (pressed) or 0 (released)
  Action: Send start/stop to Audio based on state, update LEDs
```

**Output on 8004** (to Audio):
```
/route/{ppg_id} [sample_id]
  ppg_id: 0-3
  sample_id: 0-7 (column index)
  Sent only when selection changes

/loop/start [loop_id]
  loop_id: 0-31

/loop/stop [loop_id]
  loop_id: 0-31
```

**Output on 8005** (to Launchpad Bridge):
```
/led/{row}/{col} [color, mode]
  row: 0-7, col: 0-7
  color: 0-127 (Launchpad palette index)
  mode: 0 (static), 1 (pulse), 2 (flash)
```

### Note on LED Beat Feedback

Sequencer doesn't receive beats. For beat pulse feedback (Option 3c), Launchpad Bridge must listen to beats directly on port 8001 (ReusePort) and handle LED pulses internally.

---

## Component: Launchpad Bridge (amor/launchpad.py)

### Purpose
Pure I/O translator between Launchpad Mini MK3 MIDI and OSC protocol. Handles button presses and LED feedback including beat pulses.

### Responsibilities

**MIDI → OSC** (button presses):
1. Open Launchpad Mini MK3 USB MIDI ports
2. Enter Programmer Mode (SysEx: `F0 00 20 29 02 0D 0E 01 F7`)
3. Listen for MIDI Note On/Off messages
4. Translate to OSC control messages → Sequencer (8003)

**OSC → MIDI** (LED state feedback):
1. Listen on port 8005 for LED commands from Sequencer
2. Translate to MIDI Note On velocity or SysEx RGB
3. Update LED states (selection changes, loop on/off)

**OSC → MIDI** (beat pulse feedback):
1. Listen on port 8001 for `/beat/{ppg_id}` messages (ReusePort, shares with viewer/audio)
2. On beat: flash entire row briefly, pulse selected button brighter
3. Handle pulse/flash timing via callbacks

**On startup:**
1. Detect and connect to Launchpad
2. Start OSC servers on 8001 (ReusePort) and 8005
3. Initialize LED grid (column 0 selected for PPG rows, all loops off)

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

**1. Listen on two ports:**
- Port 8001: Receive `/beat/{ppg_id}` messages (ReusePort, shared with viewer/launchpad)
- Port 8004: Receive routing and loop control from Sequencer

**2. Maintain routing table:**
```python
routing: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}  # PPG ID → sample ID
```

**3. Handle routing updates** (port 8004):
```
/route/{ppg_id} [sample_id]
  Update routing[ppg_id] = sample_id
```

**4. Handle beat triggers** (port 8001):
```
/beat/{ppg_id} [timestamp, bpm, intensity]
  Look up routing[ppg_id], play that sample with voice limiting
```

**5. Handle loop control** (port 8004):
```
/loop/start [loop_id]
/loop/stop [loop_id]
```

**6. Implement voice management:**

Track active streams per `(ppg_id, sample_id)` tuple. When voice limit reached, stop oldest stream before starting new one.

**Why voice limiting?** Sustained samples (tubular bells, singing bowls) have long decay. At 60-90 BPM with 4 sensors, you'd trigger 4-6 samples per second. Without limiting, you'd have 50+ overlapping instances within 10 seconds. Voice limit 2-3 allows polyrhythmic shimmer without mud.

**Alternative (Option C):** Envelope restart - fade out current instance when new trigger arrives. More "gated" feel. Requires envelope control (rtmixer). Not implemented in v1.0.

**7. Loop management:**

Latching loops play continuously until stopped. Momentary loops start on press, stop on release. All loops layer freely (no ducking). Optional: add fade-out on stop (500ms) for smooth transitions.

**8. Load samples from YAML:** Replace fixed filenames (`ppg_0.wav`, etc.) with dynamic loading from config.

**9. Optional: Quantization**

If implementing tempo sync, audio engine can buffer incoming beats and wait for next quantum before playing. Sequencer doesn't need to know about quantization - it only updates routing.

---

## Lighting Controller Integration

**No changes required.** Lighting controller continues to:
- Listen on port 8002 for `/beat/{ppg_id}` messages from Processor
- Calculate hue from BPM
- Pulse bulbs on beat

Sequencer doesn't coordinate lighting in this design. Future enhancement could add sample-specific colors or Launchpad color overrides, but v1.0 keeps lighting independent.

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

### Why Routing Updates Instead of Beat Proxying?

**Alternative considered:** Sequencer receives all beats on 8001, proxies to Audio with sample ID.

**Rejected because:**
- 60-90 messages/minute traffic vs 4 messages when selection changes
- Adds latency (beat → sequencer → audio instead of beat → audio directly)
- Audio can't work without sequencer
- Quantization requires buffering in sequencer even if audio does the work

**Chosen design:**
- Audio listens to beats directly (like viewer, lighting already do)
- Sequencer only sends routing updates when buttons pressed
- Audio maintains routing table
- Quantization can be audio's decision (buffer beat, wait for quantum)

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
- Routing updates sent to Audio when selection changes
- LED state updates sent to Launchpad

**Launchpad Bridge:**
- MIDI note → row/col conversion
- Row/col → loop ID calculation
- Button press → correct OSC message
- Beat received → LED pulse on correct row

**Audio Engine:**
- Routing table updated when `/route/{ppg_id}` received
- Correct sample played when beat received
- Voice limiting works correctly

### Integration Tests

**Sequencer + Mock Launchpad:**
- Send `/select/{ppg_id}` control messages
- Verify state updated
- Verify routing sent to Audio
- Verify LED state updates sent

**Audio + Mock Processor + Mock Sequencer:**
- Set routing via `/route/{ppg_id}`
- Inject `/beat/{ppg_id}` messages
- Verify correct sample plays based on routing

**Launchpad Bridge + Mock Processor:**
- Inject `/beat/{ppg_id}` messages on port 8001
- Verify LEDs pulse correctly

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

**Phase 1:** Sequencer core - state management, OSC servers, control message handlers, YAML config loading

**Phase 2:** Launchpad bridge - MIDI I/O, Programmer Mode, button → OSC translation, LED commands, beat pulse feedback

**Phase 3:** Audio engine - dual port listening (8001 + 8004), routing table, voice limiting, loop management, YAML config

**Phase 4:** Integration - end-to-end testing with real Launchpad and PPG sensors

---

## Known Limitations & Future Work

**Limitations:** Voice limiting only (no envelope restart), fixed color palette, requires restart for config changes, approximate LED pulse timing

**Future:** Envelope control (Option C), color customization, live config reload, sample preview, tempo sync/quantization, sequence recording, multi-launchpad support

---

## Dependencies

**New:** `mido`, `python-rtmidi`, `PyYAML`

**Existing:** `pythonosc`, `sounddevice`, `soundfile`, `numpy`, `python-kasa` (lighting only)

---

## Summary

This design adds interactive control to Amor via Launchpad Mini MK3 while maintaining the existing processor/audio/lighting architecture. Key decisions:

1. **Routing updates, not beat proxying:** Sequencer sends `/route/{ppg_id}` only when selections change. Audio listens to beats directly, maintains routing table. Minimal message traffic, no added latency.

2. **Voice limiting:** Prevents mud from overlapping sustained samples (tubular bells, singing bowls). Limit 2-3 concurrent instances per sample allows polyrhythmic shimmer without thickness.

3. **LED feedback Option 3c:** Launchpad Bridge listens to beats on port 8001 (ReusePort). Row flashes on beat, selected button pulses brighter. Shows both heartbeat activity and current selection.

4. **YAML config:** Sample paths in configuration file, not code. Easy to swap sound libraries, validation at startup.

5. **Clean separation:** Launchpad Bridge is pure I/O translation. Sequencer is pure state management. Audio handles timing and quantization decisions independently.

Implementation proceeds in phases: Sequencer core → Launchpad bridge → Audio mods → Integration.
