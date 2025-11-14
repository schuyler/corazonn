# Launchpad Control Button Modes

## Overview

Control buttons (top row, 8 buttons) implement modal control for the Launchpad.
When a control mode is active, the grid buttons (8×8) change function to allow
direct selection of settings rather than cycling through options.

## Launchpad Mark 1 Button Mapping

**Hardware:** Novation Launchpad Mark 1 (dual red+green LEDs, 5 colors)

**Top Row (8 round buttons):**
- Left 4 buttons (arrows): Up, Down, Left, Right - currently unassigned
- Right 4 buttons (modes):
  - Session → Control 0: Lighting Program Select
  - Mixer → Control 2: PPG Sample Bank Select
  - User 1 → Control 1: BPM Multiplier
  - User 2 → Control 3: Audio Effects Assignment

**LED Colors Available:**
- Red, Green, Amber/Yellow, Orange, Yellow-Green
- 3 brightness levels per color (low, medium, full)

## Control Flow

1. Press control button → mode activates, control LED lights up
2. Grid buttons change function (mode-specific layout)
3. Scene buttons (right side) are disabled
4. Press grid button → selection made, mode remains active
5. Press same control button → mode deactivates, normal operation resumes

## Mode Exclusivity

- Only one control mode can be active at a time
- Activating a new mode automatically deactivates the previous mode
- When no mode is active, launchpad operates in normal mode (PPG selection, loops, recording/playback)

## Control Button Modes

### Control 0: Lighting Program Select

Select one of 6 available lighting programs.

**Grid Layout:**
```
Row 0: [Prog0] [Prog1] [Prog2] [Prog3] [Prog4] [Prog5] [ --- ] [ --- ]
Row 1-7: unused/off
```

**Programs:**
- 0: soft_pulse
- 1: rotating_gradient
- 2: breathing_sync
- 3: convergence
- 4: wave_chase
- 5: intensity_reactive

**Behavior:**
- Press row 0, column 0-5 → select corresponding lighting program
- Selection persists after exiting mode
- Current program indicated by LED color/brightness

### Control 1: BPM Multiplier

Apply tempo multiplier to beat events.

**Grid Layout:**
```
Row 0: [0.25x] [0.5x] [0.75x] [1x] [1.5x] [2x] [3x]
Row 1-7: unused/off
```

**Behavior:**
- Press row 0, column 0-6 → select BPM multiplier
- Multiplier affects all beat-driven audio and lighting
- Default: 1x (no multiplication)
- Selection persists after exiting mode
- Current multiplier indicated by LED color/brightness

### Control 2: PPG Sample Bank Select

Select sample bank for each PPG (0-7, including virtual PPGs 4-7).

**Grid Layout:**
```
Row 0: [Bank0] [Bank1] [Bank2] [Bank3] [Bank4] [Bank5] [Bank6] [Bank7]  ← PPG 0
Row 1: [Bank0] [Bank1] [Bank2] [Bank3] [Bank4] [Bank5] [Bank6] [Bank7]  ← PPG 1
Row 2: [Bank0] [Bank1] [Bank2] [Bank3] [Bank4] [Bank5] [Bank6] [Bank7]  ← PPG 2
Row 3: [Bank0] [Bank1] [Bank2] [Bank3] [Bank4] [Bank5] [Bank6] [Bank7]  ← PPG 3
Row 4: [Bank0] [Bank1] [Bank2] [Bank3] [Bank4] [Bank5] [Bank6] [Bank7]  ← PPG 4 (virtual)
Row 5: [Bank0] [Bank1] [Bank2] [Bank3] [Bank4] [Bank5] [Bank6] [Bank7]  ← PPG 5 (virtual)
Row 6: [Bank0] [Bank1] [Bank2] [Bank3] [Bank4] [Bank5] [Bank6] [Bank7]  ← PPG 6 (virtual)
Row 7: [Bank0] [Bank1] [Bank2] [Bank3] [Bank4] [Bank5] [Bank6] [Bank7]  ← PPG 7 (virtual)
```

**Behavior:**
- Press row N, column M → set PPG N to sample bank M
- Each PPG can be on a different bank independently
- Allows accessing 8 banks × 8 samples per bank = 64 samples per PPG
- Sample banks persist after exiting mode
- Current bank for each PPG indicated by LED color/brightness on that row

### Control 3: Audio Effects Assignment

Toggle effects for each PPG (0-7, including virtual PPGs 4-7).
Effects can be stacked - multiple effects can be active simultaneously per PPG.

**Grid Layout:**
```
Column:  [Clear] [Reverb] [Phaser] [Delay] [Chorus] [LowPass] [ --- ] [ --- ]
Row 0:   toggle effect for PPG 0
Row 1:   toggle effect for PPG 1
Row 2:   toggle effect for PPG 2
Row 3:   toggle effect for PPG 3
Row 4:   toggle effect for PPG 4 (virtual)
Row 5:   toggle effect for PPG 5 (virtual)
Row 6:   toggle effect for PPG 6 (virtual)
Row 7:   toggle effect for PPG 7 (virtual)
```

**Available Effects:**
- Column 0: Clear all effects (disable all for that PPG)
- Column 1: Reverb - spatial depth with BPM-responsive room size
- Column 2: Phaser - sweeping filter with intensity-controlled rate
- Column 3: Delay - BPM-synced echoes
- Column 4: Chorus - gentle shimmer that breathes with heart rate
- Column 5: LowPass - inverse calming filter (darkens as BPM increases)

**Behavior:**
- Press row N, column 0 → disable all effects for PPG N
- Press row N, column 1-5 → toggle that effect for PPG N
- Multiple effects can be active simultaneously (they process serially)
- Effect processing order: reverb → phaser → delay → chorus → lowpass
- Effects configuration persists after exiting mode
- Active effects indicated by lit LED, inactive effects are off

## Normal Mode (No Control Active)

When no control mode is active:

**Grid Rows 0-3 (PPG Selection):**
- Radio button selection for sample within current bank
- Row N = PPG N, columns = samples 0-7 in selected bank

**Grid Rows 4-5 (Latching Loops):**
- Toggle loops 0-15 on/off

**Grid Rows 6-7 (Momentary Loops):**
- Trigger loops 16-31 while held

**Scene Buttons 0-3:**
- Toggle recording from PPG 0-3 (overwrites single buffer per PPG)
- Recorded buffers archived to disk

**Scene Buttons 4-7:**
- In assignment mode: assign buffer to virtual channel 4-7
- When channel playing: stop playback

## Implementation Notes

### State Management

The sequencer maintains:
- `active_control_mode`: int (None, 0, 1, 2, 3) - which control mode is active
- `current_lighting_program`: int (0-5) - selected lighting program
- `current_bpm_multiplier`: float (0.25-8.0) - selected multiplier
- `ppg_sample_banks`: dict[int, int] - PPG ID → bank ID (0-7)

### OSC Protocol Extensions

**From Launchpad Bridge → Sequencer:**
- `/control [control_id] [state]` - existing message, state=1 toggles mode

**From Sequencer → Audio/Lighting:**
- `/lighting/program [program_id]` - switch lighting program
- `/bpm/multiplier [multiplier]` - set BPM multiplier
- `/ppg/bank [ppg_id] [bank_id]` - switch sample bank for PPG

**From Sequencer → Launchpad Bridge:**
- `/led/control/{control_id} [color, mode]` - set control button LED (indicate active mode)
- Existing `/led/{row}/{col}` messages update grid to show mode-specific layouts

### LED Feedback

**Control Button LEDs:**
- Active mode: bright color (e.g., green)
- Inactive: dim/off

**Grid Button LEDs (in control modes):**
- Available options: dim blue
- Currently selected: bright cyan
- Unused positions: off

### Mode Transitions

When entering control mode:
1. Set `active_control_mode` to control button ID
2. Disable scene button handling
3. Light up control button LED
4. Update all grid LEDs to show mode-specific layout
5. Highlight current selection

When exiting control mode:
1. Set `active_control_mode` to None
2. Re-enable scene button handling
3. Turn off control button LED
4. Restore normal grid LED state (PPG selections, loop status)

When switching between control modes:
1. Exit current mode (restore state)
2. Enter new mode (apply new layout)

## Design Decisions

**Rejected Options:**
- Loop bank switching - adds complexity, 32 loops sufficient
- Master tempo presets - BPM multiplier more flexible
- Metronome toggle - not needed for this system
- Global mute - external mixer handles this
- Recording arm toggle - unnecessary complication
- Clear/undo functions - overwrite workflow is simpler

**Why Grid Buttons for Modes:**
- 8×8 grid provides enough space for all options
- Direct visual mapping (see all choices at once)
- Scene buttons remain dedicated to recording/playback workflow
- Prevents modal confusion (scene buttons always do the same thing)

**Why Modal vs. Permanent Assignment:**
- 8 control buttons insufficient for all functions as direct controls
- Modal approach multiplies available functions (8 × 64 = 512 possible mappings)
- LED feedback makes mode state clear
- Toggle on/off workflow is fast and intuitive
