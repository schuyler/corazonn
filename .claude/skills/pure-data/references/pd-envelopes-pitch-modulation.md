# Pitch and Portamento

**Related envelope techniques:**
- [Envelope Basics](pd-envelopes-basics.md) - Foundation with line~ and vline~
- [ADSR Envelopes](pd-envelopes-adsr.md) - Reusable envelope generators
- [dB Conversions and Quartic Envelopes](pd-envelopes-dbtable-conversions.md) - Logarithmic control and curved envelopes
- [Envelope Reference](pd-envelopes-reference.md) - General techniques and summary

---

## D05: Pitch Envelopes

**Source**: `D05.envelope.pitch.pd`

### Use Case
Envelope control of oscillator pitch, including discrete jumps. Unlike amplitude envelopes, pitch envelopes often need to jump to zero on retrigger rather than slide from the current value.

### ADSR for Pitch

```
[tgl]  <- positive = slide from current, negative = jump to zero first
|
[adsr 20 200 100 100 1000]  <- pitch envelope (arbitrary units)
|
[+~ 69]  <- add base pitch (A4)
|
[tabread4~ mtof]  <- convert MIDI note to frequency
|
[osc~]
```

### Negative Trigger Behavior

```
# Positive trigger (1)
[tgl] = 1  <- envelope slides from current value
|
[adsr]

# Negative trigger (-1)
[tgl] = -1  <- envelope jumps to zero, then attacks
|
[adsr]
```

This is handled internally by the `adsr` abstraction:

```
[inlet]
|
[moses]  <- test if value is negative
|      \
|       [t b b]  <- if negative, bang twice
|       |     \
|       |      [0(  <- first zero the output
|       |      |
|       [b]    |  <- then trigger attack
```

### MIDI-to-Frequency Table (mtof)

```
[tabread4~ mtof]  <- 4-point interpolation
```

**Table specs**:
- Range: 0-127 (MIDI note numbers)
- Formula: f = 440 * 2^((n-69)/12)
- Index 0 → 0 (for safety)
- Index 69 → 440 Hz (A4)
- Index 127 → 12543.9 Hz

### Table Generation

```
[until 129]
|
[f]  <- counter
|
[mtof]  <- built-in MIDI-to-frequency converter
|
[tabwrite mtof]
```

### Alternative: mtof~ Object

```
[adsr 20 200 100 100 1000]
|
[+~ 69]
|
[mtof~]  <- real-time conversion (more CPU)
|
[osc~]
```

### Practical Applications
- Pitch drops on note attacks (natural for some instruments)
- Vibrato depth envelopes
- Pitch-bend effects
- Extreme: dive bombs, rise effects

### Example: Pitch Drop Effect

```
[1(  <- attack trigger
|
[adsr 20 200 100 100 1000]  <- quick attack, slow decay
|
[+~ 69]
|
[mtof~]
|
[osc~]
```

This creates a characteristic pitch "drop" as notes start - the pitch envelope adds 20 units quickly, then decays to 100 over 200ms.

### Raw Pd Implementation

```pd
#N canvas 529 38 615 731 12;
#X obj 68 308 tgl 21 0 empty empty empty 0 -10 0 12;
#X obj 68 341 adsr 100 50 200 90 1000;
#X obj 68 375 dbtorms~;
#X obj 68 419 *~;
#X obj 68 460 output~;
#X obj 68 255 r trigger;
#X floatatom 68 281 3 0 0 0 - - - 0;

# Pitch envelope section
#X obj 260 308 tgl 21 0 empty empty empty 0 -10 0 12;
#X obj 260 341 adsr 20 200 100 100 1000;
#X obj 260 378 +~ 69;
#X obj 260 409 tabread4~ mtof;
#X obj 260 436 osc~;
#X obj 260 488 output~;
#X obj 260 255 r trigger2;
#X floatatom 260 281 3 0 0 0 - - - 0;

# Amplitude envelope modulation
#X connect 5 0 0 0;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X connect 2 0 3 1;

# Pitch envelope with negative trigger support
#X connect 13 0 7 0;
#X connect 7 0 8 0;
#X connect 8 0 9 0;
#X connect 9 0 10 0;
#X connect 10 0 11 0;
#X connect 11 0 12 0;

# Messages for testing
#X msg 51 171 ; trigger 1 ; trigger2 1;
#X msg 224 171 ; trigger 1 ; trigger2 -1;
```

---

## D06: Portamento (Pitch Sliding)

**Source**: `D06.envelope.portamento.pd`

### Use Case
Smooth pitch sliding between notes. Traditional synthesizer portamento effect.

### Basic Pattern

```
[48(  <- target MIDI note
|
[pack f 100]  <- pack with glide time (100ms)
|
[line~]  <- ramp to target pitch
|
[mtof~]  <- convert to frequency
|
[osc~]
```

### Complete Implementation

```
# Note buttons
[msg 36( [msg 48( [msg 60( [msg 72( [msg 84(
|        |        |        |        |
+--------+--------+--------+--------+
|
[f]  <- store current note
|
[pack f 100]  <- pack with portamento time
|        |
|        [f 100]  <- portamento time control
|        |
|        [100(  <- glide time in ms
|
[line~]
|
[mtof~]
|
[osc~]
```

### Variable Glide Time

```
[floatatom]  <- adjust portamento speed (ms)
|
[pack f $1]  <- use variable time
```

Typical values:
- **0ms**: Instant (no portamento)
- **50-100ms**: Fast glide
- **200-500ms**: Moderate glide
- **1000+ms**: Slow, obvious slide

### Difference from Pitch Envelopes
- **Portamento**: Slides between discrete note targets
- **Pitch envelope**: Continuous envelope shape applied to pitch
- Portamento uses the note value itself as the target
- No attack/decay/sustain/release structure

### Legato vs Non-Legato
This example shows "always-on" portamento. For proper legato:

```
[makenote 100 500]  <- generate note on/off
|
[poly 8]  <- voice allocation
|
[pack f 100]  <- portamento when legato
```

Or detect overlapping notes:

```
[noteout]
|
[swap]  <- detect if previous note still held
|
[select]  <- if held, use portamento time, else 0
```

### Frequency-Space Portamento

For portamento in frequency (Hz) rather than pitch (MIDI):

```
[440(  <- frequency target
|
[pack f 100]
|
[line~]  <- linear frequency ramp
|
[osc~]
```

This sounds different - linear in frequency space is exponential in pitch space, creating an accelerating slide effect.

### Raw Pd Implementation

```pd
#N canvas 617 93 541 482 12;
#X obj 245 166 msg 36;
#X obj 245 166 msg 48;
#X obj 245 166 msg 60;
#X obj 245 166 msg 72;
#X floatatom 312 213 4 0 0 0 - - - 0;
#X floatatom 245 205 6 0 0 0 - - - 0;
#X obj 245 244 pack f 100;
#X obj 245 275 line~;
#X obj 245 305 mtof~;
#X obj 245 334 osc~;
#X obj 245 376 output~;

# Note values sent to pack
#X connect 0 0 5 0;
#X connect 1 0 5 0;
#X connect 2 0 5 0;
#X connect 3 0 5 0;

# Portamento time control
#X connect 4 0 6 1;

# Pack note with time and send to line~
#X connect 5 0 6 0;
#X connect 6 0 7 0;

# Convert MIDI pitch to frequency
#X connect 7 0 8 0;

# Generate audio at swept frequency
#X connect 8 0 9 0;
#X connect 9 0 10 0;
```

Legato portamento (only slide when notes overlap):

```pd
#X obj 100 100 noteout;
#X obj 100 140 swap;
#X obj 100 180 select 0;

# Detect if previous note still held
#X connect 0 0 1 0;
#X connect 1 0 2 0;

# If no overlap: glide time = 0 (instant)
# If overlap: glide time = 100ms (legato slide)
```
