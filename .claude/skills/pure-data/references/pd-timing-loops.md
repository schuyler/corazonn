# Pure Data Loops Reference

Immediate iteration techniques with `until` object and conditional stopping.

**Related Topics:**
- Metro counters: See [pd-timing-metro-counters.md](pd-timing-metro-counters.md) for timing-based looping (safer alternative)
- Conditional counting: See [pd-timing-conditional-counting.md](pd-timing-conditional-counting.md)
- Sequencing: See [pd-timing-sequencing.md](pd-timing-sequencing.md)
- Overview: See [pd-timing-reference.md](pd-timing-reference.md)

---

## Counting Loop
```
[msg: 5]  <- number of iterations
|
[until]   <- loops N times
|
[print repetition]
```

**Behavior:**
- Sends N bangs immediately (no delay)
- All iterations in single message context
- Completes before next message processed

### Raw .pd Implementation - Counting Loop

Loop N times immediately:
```pd
#N canvas 561 38 513 680 12;
#X obj 180 286 until;
#X floatatom 180 254 5 0 0 1 - - - 0;
#X obj 180 330 print repetition;
#X msg 180 219 5;
#X connect 0 0 2 0;
#X connect 1 0 0 0;
#X connect 3 0 1 0;
```

Key pattern:
- Message sets loop count (5)
- `[until]` outputs N bangs in sequence
- All bangs occur within single message execution
- No timing delay between iterations

## Conditional Loop
```
[bng]          [0]  <- reset
|              |
[until]        |
|              |
[float]--------+
|  \
|   [+ 1]
|   /
|  /
[float]
|
[moses 10]  <- test if < 10
|       \
print   [bang]  <- stop when >= 10
        |
        [until] (right inlet)
```

**Behavior:**
- Runs until stopped via right inlet bang
- WARNING: Will freeze Pd if not stopped
- Use comparison to automatically stop

### Raw .pd Implementation - Conditional Loop

Loop until condition met:
```pd
#X obj 162 499 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X obj 162 528 until;
#X obj 162 554 float;
#X obj 219 553 + 1;
#X obj 162 588 moses 10;
#X obj 277 540 bang;
#X obj 162 621 print number;
#X msg 240 511 0;
#X connect 6 0 7 0;
#X connect 4 0 5 0;
#X connect 4 1 6 1;
#X connect 5 0 7 0;
#X connect 3 0 2 1;
#X connect 2 0 3 0;
#X connect 2 0 4 0;
#X connect 7 0 2 1;
#X connect 8 0 7 1;
```

Key pattern:
- `[until]` starts on bang to left inlet
- Counter increments in feedback loop
- `[moses]` splits on condition (< 10 goes left, >= 10 right)
- Right outlet of moses stops until via right inlet
- Reset message sets counter to 0

### When to Use

**Counting Loop:**
- Burst generation (N rapid events)
- Array population
- Fixed repetitions without timing

**Conditional Loop:**
- Iterative calculations
- Search algorithms
- Pattern generation until condition

### When NOT to Use
- Anything with timing (use metro + counter)
- Audio-rate operations (use audio objects)
- Long computations (risk freezing)

### Heartbeat Applications

**Counting Loop:**
- Generate burst of N DMX commands
- Populate lookup table
- Initialize multi-zone states
- Quick parameter sweeps

**Conditional Loop:**
- Calculate BPM from R-R intervals (iterate until stable)
- Find optimal brightness mapping
- Generate fade tables
- State machine traversal

**Alternative (Safer):**
Most heartbeat uses should prefer `[metro]` + `[select]` for safety:
```
[metro 10]  <- fast metro instead of until
|
[counter with stop condition]
```
