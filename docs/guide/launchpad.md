# Launchpad Control Scheme

Novation Launchpad Mark 1 controller for the Amor biofeedback sequencer.

## Button Layout

**Top Row Control Buttons:**
- Left 4: Up, Down, Left, Right (unassigned)
- **Session** → Lighting Program Select
- **User 1** → BPM Multiplier
- **Mixer** → PPG Sample Bank Select
- **User 2** → Audio Effects Assignment

**Grid:** 8×8 buttons, function changes based on active control mode

**Scene Buttons:** 8 side buttons for recording and playback

## Using Control Modes

1. Press control button to activate mode (LED lights up)
2. Grid displays mode-specific options
3. Press grid button to make selection
4. Press same control button again to exit
5. Only one mode active at a time

## Lighting Program Select (Session)

Row 0 shows 6 programs: soft_pulse, rotating_gradient, breathing_sync, convergence, wave_chase, intensity_reactive. Press to select.

## BPM Multiplier (User 1)

Row 0 shows 8 multipliers: 0.25x, 0.5x, 1x, 1.5x, 2x, 3x, 4x, 8x. Affects all beat-driven audio and lighting.

## PPG Sample Bank Select (Mixer)

Each row (0-7) controls one PPG, columns (0-7) select sample bank. Each PPG independent, allows access to 64 samples per PPG (8 banks × 8 samples).

## Audio Effects Assignment (User 2)

Columns: Clear, Reverb, Phaser, Delay, Chorus, LowPass
Rows 0-7: Toggle effects for PPGs 0-7

- Column 0: Clear all effects for that PPG
- Columns 1-5: Toggle individual effects (stackable)
- Process order: reverb → phaser → delay → chorus → lowpass

**Effect Details:**
- **Reverb**: BPM-responsive room size
- **Phaser**: Intensity-controlled sweeping filter
- **Delay**: BPM-synced echoes
- **Chorus**: Heart rate-responsive shimmer
- **LowPass**: Inverse calming filter

## Normal Mode (No Control Active)

**Grid Rows 0-3:** PPG sample selection (radio buttons, 8 samples per bank)

**Grid Rows 4-5:** Latching loops 0-15 (toggle on/off)

**Grid Rows 6-7:** Momentary loops 16-31 (active while held)

**Scene 0-3:** Toggle recording from PPG 0-3 (overwrites buffer, archived to disk)

**Scene 4-7:** Virtual channel playback (assign buffer or stop playback)

## LED Feedback

**Control Buttons:** Bright when active, dim/off when inactive

**Grid Buttons:** Dim blue (available), bright cyan (selected), off (unused)

## Running the Sequencer

```bash
python -m amor.sequencer
```

Changes to control modes take effect immediately. Sample bank and effect selections persist across mode changes.
