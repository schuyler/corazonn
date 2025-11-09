# ADSR Envelopes

**Related envelope techniques:**
- [Envelope Basics](pd-envelopes-basics.md) - Foundation with line~ and vline~
- [dB Conversions and Quartic Envelopes](pd-envelopes-dbtable-conversions.md) - Logarithmic control and curved envelopes
- [Pitch and Portamento](pd-envelopes-pitch-modulation.md) - Pitch-based envelope techniques
- [Envelope Reference](pd-envelopes-reference.md) - General techniques and summary

---

## D02: ADSR Abstraction

**Source**: `D02.adsr.pd` and `adsr.pd`

### Use Case
Reusable ADSR envelope generator with configurable parameters. Standard approach for amplitude control in synthesizers.

### Usage

```
[tgl]  <- 1 = attack, 0 = release
|
[adsr 1 100 200 50 250]
      |  |   |   |   |
      |  |   |   |   +-- Release time (ms)
      |  |   |   +------ Sustain level (%)
      |  |   +---------- Decay time (ms)
      |  +-------------- Attack time (ms)
      +----------------- Peak level
|
[*~]  <- multiply with audio signal
```

### Abstraction Internals (adsr.pd)

```
# Main trigger inlet
[inlet]
|
[sel 0]  <- detect release (0) vs attack (non-zero)
|     \
|      [moses]  <- test for negative trigger
|      |     \
|      |      [t b b]  <- negative trigger: zero output then attack
|      |      |     \
|      |      |      [0(
|      |      |      |
|      |      [b]----+
|      |             |
[stop] [del $2]------+  <- cancel decay, or schedule decay after attack
|      |
|      [f $4]  <- recall sustain level
|      |
|      [* 0.01]  <- convert percent to multiplier
|      |
|      [* $1]  <- multiply by peak level
|      |
|      [pack f $3]  <- pack with decay time
|      |
|      [s $0-line]
|
[pack 0 $5]  <- release: pack 0 with release time
|
[s $0-line]

# Line generation
[r $0-line]
|
[line~]
|
[outlet~]
```

### Key Features
- **Positive trigger**: Attack from current level (slur effect)
- **Negative trigger**: Jump to zero, then attack (hard retrigger)
- **Zero trigger**: Release to zero
- `$0-line` uses local send/receive for internal messaging
- Sustain level stored as percent (0-100)

### Retrigger Behavior
When retriggering before release completes, the envelope attacks from the current level rather than zero. This creates a natural "slur" effect. For isolated attacks, use negative triggers.

### Raw Pd Implementation (adsr.pd)

Abstraction file structure:

```pd
#N canvas 351 82 872 651 12;
#X obj 129 120 inlet;
#X obj 438 160 inlet;
#X obj 495 160 inlet;
#X obj 545 160 inlet;
#X obj 600 160 inlet;
#X text 125 95 trigger;
#X text 491 138 attack;
#X text 546 138 decay;
#X text 593 138 sustain;
#X text 653 138 release;

# Inlet 0: trigger (0 = release, + = attack, - = zero then attack)
# Inlet 1: peak level ($1)
# Inlet 2: attack time ($2)
# Inlet 3: decay time ($3)
# Inlet 4: sustain percent ($4)
# Inlet 5: release time ($5)

#X obj 129 148 sel 0;
#X obj 231 101 moses;
#X obj 218 131 t b b;
#X msg 152 299 0;

# Release detection
#X connect 0 0 10 0;
#X connect 10 0 12 0;

# Negative trigger test (moses tests if < 0)
#X connect 0 0 11 0;
#X connect 11 0 13 0;
#X connect 11 1 12 0;

#X obj 190 273 f $1;
#X obj 422 285 del $2;
#X obj 446 313 f $4;
#X obj 446 338 * 0.01;
#X obj 485 364 * $1;
#X obj 485 388 pack f $3;
#X obj 595 429 r $0-line;
#X obj 595 476 line~;
#X obj 596 356 s $0-line;
#X obj 596 315 pack 0 $5;
#X obj 595 536 outlet~;

# Attack path: peak level → attack time → line~
# Decay path: sustain → decay time → line~
# Release path: always 0 → release time → line~
```

**Usage in parent patch**:

```pd
#X obj 64 261 tgl 21 0 empty empty empty 0 -10 0 12;
#X obj 64 228 adsr 1 100 200 50 250;
#X obj 46 393 *~;

# Toggle controls gate (1=attack, 0=release)
#X connect 0 0 1 0;

# Envelope output modulates audio signal
#X connect 1 0 2 1;
```
