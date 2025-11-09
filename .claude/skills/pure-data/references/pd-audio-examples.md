# Pure Data Audio Code Examples

Raw .pd format examples for audio signal processing.

See also: [Fundamentals](pd-audio-fundamentals.md), [Objects](pd-audio-objects.md), [Routing](pd-audio-routing.md)

## Basic Tilde Objects

### Sine Wave Oscillator with Amplitude Control

Visual representation:
```
[osc~ 440]
   |
[*~ 0.05]
   |
[dac~]
```

Raw .pd format:
```
#X obj 59 197 osc~ 440;
#X obj 59 226 *~ 0.05;
#X obj 59 256 dac~;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
```

Key elements:
- `#X obj 59 197 osc~ 440`: Oscillator at 440 Hz (A note)
- `#X obj 59 226 *~ 0.05`: Multiply signal by amplitude (0.05)
- `#X obj 59 256 dac~`: Audio output (both channels if 2 inlets connected)
- `#X connect 0 0 1 0`: Connect outlet 0 of obj 0 to inlet 0 of obj 1

### Signal Routing with Line~ (Ramp Generator)

Visual representation:
```
[osc~ 440]
     |
[line~]
     |
[*~]
     |
[dac~]
```

Raw .pd format:
```
#X obj 89 140 osc~ 440;
#X obj 137 334 line~;
#X obj 89 371 *~;
#X obj 89 413 dac~;
#X msg 114 174 0.1 2000;
#X connect 0 0 2 0;
#X connect 1 0 2 1;
#X connect 2 0 3 0;
#X connect 4 0 1 0;
```

Key elements:
- `#X obj 137 334 line~`: Generates smoothed ramp to target value over time
- `#X msg 114 174 0.1 2000`: Message "0.1 2000" = reach 0.1 amplitude over 2000ms
- `line~` ramp modulates amplitude via multiply object

### Nonlocal Signal Routing with send~/receive~

Visual representation:
```
Left window:             Right window:
[inlet~]                 [inlet~]
  |                        |
[process~]              [receive~
  |                      prev-real]
[send~                   |
 prev-real]          [use signal]
```

Raw .pd format:
```
// In processing subpatch (left):
#X obj 21 437 *~;
#X obj 139 538 send~ prev-imag;
#X obj 139 568 send~ prev-real;
#X connect 1 0 4 0;
#X connect 1 0 5 0;

// In analysis subpatch (right):
#X obj 23 12 receive~ prev-real;
#X obj 81 35 receive~ prev-imag;
#X obj 53 199 *~ ;
#X obj 22 199 *~;
#X connect 0 0 8 0;
#X connect 1 0 9 0;
```

Key elements:
- `#X obj 139 568 send~ prev-real`: Send signal to named bus "prev-real"
- `#X obj 23 12 receive~ prev-real`: Receive from bus "prev-real"
- Multiple `receive~` objects can listen to same `send~`
- Each `receive~` picks up one `send~` at a time (can switch sources via message)

## Arithmetic Operations

### Multiplying Two Signals

Raw .pd format:
```
#X obj 85 174 osc~ 440;
#X obj 110 251 dbtorms;
#X obj 85 321 *~ 0;
#X obj 73 403 dac~;
#X obj 110 284 floatatom 8 0 0 0 - - - 0;
#X connect 0 0 2 0;
#X connect 2 0 3 0;
#X connect 4 0 2 1;
#X connect 1 0 4 0;
```

Key elements:
- `#X obj 85 321 *~ 0`: Multiplier with control argument "0" (expects message at right inlet)
- Without control argument (e.g., `*~`): expects audio signal at right inlet
- `#X connect 4 0 2 1`: Connect control floatatom to right inlet (auto-promoted to signal)

## Table-Based Operations

### Reading from Table with Interpolation

Raw .pd format:
```
#X obj 75 100 phasor~ 440;
#X obj 75 130 tabread4~ mytable;
#X obj 75 160 dac~;
#X array mytable 2048 float;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
```

Key elements:
- `#X obj 75 130 tabread4~ mytable`: Read from array with 4-point interpolation
- `#X array mytable 2048 float`: Define array "mytable" with 2048 samples
- `phasor~` generates index ramp (0-1) for table lookup
- `tabread~` for no interpolation, `tabread4~` for smooth interpolation

## Delay Line Implementation

### Basic Delay (delwrite~/delread4~)

Raw .pd format:
```
#X obj 71 108 inlet~;
#X obj 102 173 delwrite~ G05-d2 1000;
#X obj 163 78 inlet~;
#X obj 163 123 delread4~ G05-d2;
#X obj 163 195 outlet~;
#X connect 0 0 1 0;
#X connect 0 0 2 0;
#X connect 2 0 3 0;
#X connect 3 0 4 0;
```

Key elements:
- `#X obj 102 173 delwrite~ G05-d2 1000`: Write to delay line "G05-d2" (1000 sample buffer)
- `#X obj 163 123 delread4~ G05-d2`: Read from same delay line with interpolation
- Delay line name must match between `delwrite~` and `delread4~`
- Right inlet of `delread4~` sets delay time in milliseconds
- Minimum delay: one block (64 samples default, ~1.33ms at 48kHz)
