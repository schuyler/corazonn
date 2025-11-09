# dB Conversions and Quartic Envelopes

**Related envelope techniques:**
- [Envelope Basics](pd-envelopes-basics.md) - Foundation with line~ and vline~
- [ADSR Envelopes](pd-envelopes-adsr.md) - Reusable envelope generators
- [Pitch and Portamento](pd-envelopes-pitch-modulation.md) - Pitch-based envelope techniques
- [Envelope Reference](pd-envelopes-reference.md) - General techniques and summary

---

## D03: Decibel (dB) Conversion

**Source**: `D03.envelope.dB.pd`

### Use Case
Logarithmic amplitude control for more natural-sounding volume changes. Human perception of loudness is logarithmic, so dB envelopes sound more uniform than linear.

### Pattern with Table Lookup

```
[adsr 100 100 200 70 300]  <- values in dB (0-100 range)
|
[tabread4~ dbtorms]  <- 4-point interpolation from lookup table
|
[*~]  <- multiply with audio signal
```

### Table Range
- Input: 0-120 (index values)
- Output: 0-10 (amplitude multipliers)
- 1 → true zero
- 120 → 10 (20 dB boost for headroom)
- Each step ≈ 1 dB

### Table Generation (from make-table subpatch)

```
[until 123]
|
[f]  <- counter 0-122
|
[moses 2]  <- special case: send 0 for index 0 and 1
|        \
|         [dbtorms]  <- built-in dB to RMS converter
|         |
[tabwrite dbtorms]
```

### Alternative: dbtorms~ Object

```
[adsr 100 100 200 70 300]
|
[dbtorms~]  <- real-time conversion (more CPU than table lookup)
|
[*~]
```

### CPU Efficiency Notes
- `tabread4~` is faster than `dbtorms~`
- Critical for embedded systems or high polyphony
- `dbtorms~` is simpler and fine for most applications

### Sonic Character
The "slur effect" on retrigger is more pronounced with dB envelopes: retriggering from sustain level only rises 30 dB instead of 100 dB, making the attack sound slower. To compensate, consider boosting retriggered notes compared to isolated ones.

### Raw Pd Implementation

```pd
#N canvas 0 0 500 400 12;
#X obj 46 147 osc~ 440;
#X obj 64 228 adsr 100 100 200 70 300;
#X obj 91 334 tabread4~ dbtorms;
#X obj 46 393 *~;
#X obj 46 428 output~;

# Envelope in dB (0-100) sent to table lookup
#X connect 1 0 2 0;

# dB-to-RMS conversion applied to audio
#X connect 2 0 3 1;
#X connect 0 0 3 0;
#X connect 3 0 4 0;

# Table generation subpatch (in D03)
#N canvas 0 0 450 300 (subpatch) 0;
#X array dbtorms 121 float 1;
#X restore;

# Initialize table with dbtorms values
#X obj 100 300 until 122;
#X obj 120 330 f;
#X obj 150 330 + 1;
#X obj 120 360 dbtorms;
#X obj 120 390 tabwrite dbtorms;
```

---

## D04: Quartic Envelopes

**Source**: `D04.envelope.quartic.pd`

### Use Case
Natural-sounding pitch and amplitude sweeps. Quartic (4th power) curves sound more uniform to human perception than linear ramps.

### Perceptual Problem with Linear Envelopes
Both pitch and amplitude perception are logarithmic. Linear ramps sound uneven - changes are more noticeable at lower values than higher values.

### Quartic Solution Pattern

```
[line~ target time]  <- linear ramp
|
[*~]  <- square
||
[*~]  <- square again (now 4th power)
||
[result~]
```

### Frequency Envelope Implementation

```
[r freq]  <- target frequency
|
[unpack]
|
[sqrt]  <- take 4th root (sqrt twice)
|
[sqrt]
|
[line~]  <- linear ramp in transformed space
|
[*~]  <- square
||
[*~]  <- square again
||
[osc~]  <- oscillator with quartic frequency sweep
```

### Amplitude Envelope Implementation

```
[r amp]  <- target amplitude
|
[unpack]
|
[sqrt]  <- take 4th root
|
[sqrt]
|
[line~]
|
[*~]  <- square
||
[*~]  <- square again
||
[*~ osc~]  <- apply quartic amplitude envelope
```

### Complete Example Messages

```
# Amplitude sweeps
[amp 1 5000(      <- slow attack to full volume
[amp 0.5 1000(    <- quick decay to half volume
[amp 0 1000(      <- quick release

# Frequency sweeps
[freq 880 1000(   <- rise to A5 in 1 second
[freq 220 1000(   <- drop to A3 in 1 second
```

### Mathematical Explanation
- **Forward transform**: Take 4th root of target value (sqrt twice)
- **Linear interpolation**: `line~` ramps in transformed space
- **Inverse transform**: Raise to 4th power (square twice)
- Result: Perceptually uniform sweep

### CPU Cost
Four additional `*~` objects per envelope (two for forward, two for inverse transform).

### When to Use
- Pitch glides or vibrato depth changes
- Amplitude swells or fades
- Any parameter sweep that needs to sound "even"
- Not needed for parameters with linear perception (e.g., filter cutoff in Hz)

### Raw Pd Implementation

Frequency envelope (quartic):

```pd
#N canvas 520 54 686 681 12;
#X obj 65 355 line~;
#X obj 207 294 r freq;
#X obj 207 349 unpack;
#X obj 207 374 sqrt;
#X obj 207 400 sqrt;
#X obj 207 427 line~;
#X obj 207 459 *~;
#X obj 207 489 *~;
#X obj 207 516 osc~;
#X obj 260 549 *~;
#X obj 260 581 output~;

# Frequency in arrives with target and time
#X connect 1 0 2 0;
#X connect 2 0 3 0;

# Take 4th root (sqrt twice) for target
#X connect 3 0 4 0;
#X connect 4 0 5 0;

# Linear ramp in transformed space
#X connect 5 0 6 0;
#X connect 5 0 6 1;

# Square twice to get 4th power
#X connect 6 0 7 0;
#X connect 6 0 7 1;

# Apply to oscillator
#X connect 7 0 8 0;
#X connect 8 0 9 0;
#X connect 9 0 10 0;
```

Amplitude envelope (quartic):

```pd
#X obj 117 330 r amp;
#X obj 117 357 unpack;
#X obj 117 384 sqrt;
#X obj 117 400 sqrt;
#X obj 117 420 line~;
#X obj 146 459 *~;
#X obj 146 489 *~;
#X obj 146 524 wrap~;

# Similar structure for amplitude
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X connect 2 0 3 0;
#X connect 3 0 4 0;
#X connect 4 0 5 0;
#X connect 4 0 5 1;
#X connect 5 0 6 0;
#X connect 5 0 6 1;
#X connect 6 0 7 0;
```
