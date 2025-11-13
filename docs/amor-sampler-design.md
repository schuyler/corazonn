# Amor PPG Sampler Design

**Version:** 1.0
**Date:** 2025-11-13
**Status:** Design Phase

---

## Overview

Add live PPG sampling/looping to enable layered performances with fewer than 4 participants. Capture real sensor data, loop through virtual channels, let beat detection work on sampled rhythms.

**Use case:** Record heartbeat from PPG 0, loop on virtual channel 4, free hands for live interaction.

---

## Architecture

**Extend from 4 to 8 PPG channels:**
- Channels 0-3: Real ESP32 sensors
- Channels 4-7: Virtual channels (sampled loops)

Virtual channels processed identically to real sensors through beat detection.

**Audio routing (modulo-4 bank mapping):**
```
Channel N → Sample bank (N % 4)
  0,4 → bank 0 (row 0)  |  Pan: -1.0 (hard left)
  1,5 → bank 1 (row 1)  |  Pan: -0.33 (center-left)
  2,6 → bank 2 (row 2)  |  Pan:  0.33 (center-right)
  3,7 → bank 3 (row 3)  |  Pan:  1.0 (hard right)
```

Recording from PPG 0 and playing on channel 5 uses **bank 1 samples**, not bank 0.

---

## System Component Changes

### Processor (amor/processor.py)
- Extend to 8 PPGSensor instances
- Accept `/ppg/{0-7}` messages
- No other changes (SO_REUSEPORT allows sampler to coexist)

### Audio Engine (amor/audio.py)
- Routing table: 8 entries with modulo-4 bank mapping
- Pan positions: duplicate 0-3 for 4-7
- Handle `/route/{4-7}` messages

### Sequencer (amor/sequencer.py)
- Add sampler state: `recording_source`, `assignment_mode`, `recording_buffer`, `active_virtuals`
- Handle `/scene [0-7]` for sampler control
- Translate to `/sampler/*` OSC messages
- Send scene LED commands to Launchpad

### Launchpad Bridge (amor/launchpad.py)
- Add `_set_scene_led(scene_id, color)` method
- Scene MIDI notes: [8, 24, 40, 56, 72, 88, 104, 120]
- Handle `/led/scene/{scene_id}` OSC messages
- LED colors: red=recording, blinking green=assignment, solid green=playing

---

## Sampler Module (amor/sampler.py)

### Components

**PPGRecorder:**
- Listens on PORT_PPG (8000, SO_REUSEPORT) for `/ppg/{0-3}`
- Records to `data/sampler_YYYYMMDD_HHMMSS_ppg{N}.bin`
- Binary format: same as capture.py (PPGL magic, version 1)
- Max duration: 60 seconds

**VirtualChannel:**
- Loads binary file, replays in loop
- Sends `/ppg/{4-7}` to port 8000
- Independent thread per channel (max 4 concurrent)
- Uses replay.py timing logic

**SamplerController:**
- Listens on PORT_CONTROL (8003)
- State machine: idle → recording → assignment_mode
- Coordinates recorder and virtual channels
- Sends status updates for LED feedback

### State Machine

1. `idle`: No recording, no assignment pending
2. `recording(source_ppg)`: Capturing data from PPG N
3. `assignment_mode(buffer_path)`: Waiting for destination selection

**Transitions:**
- idle + scene press → recording
- recording + same scene → assignment_mode
- assignment_mode + scene 4-7 → idle, start playback
- active virtual + same scene → stop playback

---

## OSC Protocol

**Launchpad → Sequencer (PORT_CONTROL):**
```
/scene [scene_id] [state]  # scene_id: 0-7, state: 1=press/0=release
```

**Sequencer → Sampler (PORT_CONTROL):**
```
/sampler/record/toggle [source_ppg]  # 0-3: start/stop recording
/sampler/assign [dest_channel]       # 4-7: assign buffer, start playback
/sampler/toggle [dest_channel]       # 4-7: toggle playback
```

**Sampler → Sequencer (PORT_CONTROL):**
```
/sampler/status/recording [source_ppg] [active]    # 1=started, 0=stopped
/sampler/status/assignment [active]                # 1=entered, 0=exited
/sampler/status/playback [dest_channel] [active]   # 1=playing, 0=stopped
```

**Sequencer → Launchpad (PORT_CONTROL, broadcast):**
```
/led/scene/{scene_id} [color] [mode]  # mode: 0=static, 1=pulse, 2=blink
```

---

## Launchpad Control Workflow

**Scene 0-3: Record from PPG 0-3**
1. Press Scene 0 → recording PPG 0 (red LED)
2. Press Scene 0 → stop recording, assignment mode (blinking green)

**Scene 4-7: Playback on virtual channels 4-7**
3. Press Scene 4 → assign to channel 4, playback starts (solid green, Scene 0 off)
4. Press Scene 4 → stop playback (LED off)

**LED states:**
Recording=red | Assignment=blinking green (~2Hz) | Playing=solid green | Idle=off

---

## Implementation Notes

**Threading:**
- Main thread: OSC servers (PORT_PPG + PORT_CONTROL)
- Recording thread: active during recording only
- Playback threads: one per virtual channel (max 4)

**File format:** Reuse capture.py (PPGL magic, version 1, PPG ID, records)

**Timing:** Replay uses relative timing from original recording. No quantization or beat alignment.

**Error handling:**
- 60s limit: auto-stop, enter assignment mode
- Assignment without recording: no-op
- Virtual already playing: stop old, start new
- File I/O errors: log warning, skip playback

**Concurrent playback:** 4 channels × 10 msg/sec = 40 OSC msg/sec (~2 KB/sec, negligible)

---

## Testing Strategy

**Unit:** PPGRecorder file format, VirtualChannel timing, state transitions, modulo-4 routing

**Integration:** Record from emulator, replay verification, beat detection, concurrent channels, assignment workflow

**Manual:** Real heartbeat recording, 2-3 virtual layers, audio routing verification, stereo panning

---

## Implementation Phases

1. Processor extension (8 channels, validation)
2. Audio extension (8-channel routing, modulo-4 mapping, pan positions)
3. Sampler module (recording, playback, state machine)
4. Sequencer integration (state tracking, OSC translation)
5. Launchpad extension (scene LED control)
6. Integration testing (end-to-end workflow)

---

## Summary

Virtual PPG channels enable layered performances by capturing and looping biometric data.

**Key decisions:**
- 8 total channels (4 real + 4 virtual) with identical beat detection
- Modulo-4 audio routing reuses existing 4 sample banks
- File-based storage in `data/` (persistent, no cleanup)
- Scene button control (8 buttons = 4 sources + 4 destinations)
- Independent playback via threading (max 4 concurrent)
- Beat detection on sampled data (no quantization, predictor handles artifacts)

Sampler runs as separate process, communicates via OSC on established control bus.
