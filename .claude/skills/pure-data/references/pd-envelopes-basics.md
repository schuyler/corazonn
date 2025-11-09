# Pure Data Envelope Techniques Reference

Extracted from the D series examples in `pure-data/doc/3.audio.examples/`.

**Related envelope techniques:**
- [ADSR Envelopes](pd-envelopes-adsr.md) - Reusable envelope generators
- [dB Conversions and Quartic Envelopes](pd-envelopes-dbtable-conversions.md) - Logarithmic control and curved envelopes
- [Pitch and Portamento](pd-envelopes-pitch-modulation.md) - Pitch-based envelope techniques
- [Envelope Reference](pd-envelopes-reference.md) - General techniques and summary

---

## D01: Basic Envelope Generation with line~

**Source**: `D01.envelope.gen.pd`

### Use Case
Manual attack-decay-release envelope control for amplitude modulation. Demonstrates the fundamental pattern of scheduling ramps with `line~` and coordinating timing with `delay`.

### Core Pattern

```
[bng] attack/decay
|
[10 200(  <- attack: ramp to 10 over 200ms
|
[delay 200]  <- wait for attack to complete
|
[1 2500(  <- decay: ramp to 1 over 2500ms
|
[line~]  <- generate the envelope signal
```

### Complete Implementation

```
# Attack/decay trigger
[bng]
|
[t b b]
|        \
|         [delay 200]
|         |
[10 200(  [1 2500(
|         |
[line~]---/
```

### Release Pattern

```
[bng] release
|
[t b b]
|      \
|       [stop(  <- cancel scheduled decay
|       |
|     [delay]
|
[0 500(  <- release: ramp to 0 over 500ms
|
[line~]
```

### Key Concepts
- **Attack**: Immediate ramp to peak value
- **Decay**: Delayed secondary ramp to sustain level
- **Release**: Cancels pending messages and ramps to zero
- The `stop` message to `delay` prevents decay from triggering during release
- Timing coordination between `delay` and `line~` is critical

### Parameters
- Peak level (10 in example)
- Attack time (200ms)
- Decay time (2500ms)
- Sustain level (1)
- Release time (500ms)

### Raw Pd Implementation

```pd
#N canvas 488 38 648 696 12;
#X obj 163 345 delay 200;
#X obj 163 288 bng 19 250 50 0 empty empty empty;
#X msg 163 369 1 2500;
#X msg 98 345 10 200;
#X obj 164 411 line~;

# Attack trigger - send attack message immediately
#X connect 1 0 0 0;
#X connect 1 0 3 0;

# Delay triggers decay
#X connect 0 0 2 0;

# Decay and attack both sent to line~
#X connect 3 0 4 0;
#X connect 2 0 4 0;
```

---

## D01b: vline~ Alternative

**Source**: `D01.envelope.gen.pd` (right side)

### Use Case
Simplified envelope generation using `vline~`'s ability to schedule multiple segments in a single message.

### Core Pattern

```
[bng] attack/decay
|
[10 200, 1 2500 200(  <- peak_value attack_time, sustain decay_time delay
|
[vline~]
```

### Advantages over line~
- Single message defines both attack and decay
- No need for separate `delay` object
- More concise for multi-segment envelopes

### Message Format
```
target1 time1, target2 time2 delay2, target3 time3 delay3...
```

Each segment: `target duration [delay]`

### Raw Pd Implementation

```pd
#N canvas 0 0 500 400 12;
#X obj 100 100 bng 19 250 50 0 empty empty empty;
#X msg 100 130 10 200, 1 2500 200;
#X obj 100 160 vline~;
#X msg 100 190 0 500;

# Attack/decay in single message
#X connect 0 0 1 0;
#X connect 1 0 2 0;

# Release
#X connect 0 0 3 0;
#X connect 3 0 2 0;
```
