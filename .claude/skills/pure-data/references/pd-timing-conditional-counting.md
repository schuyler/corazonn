# Pure Data Conditional Counting Reference

Counting techniques with conditions, stopping, and state-based behavior.

**Related Topics:**
- Metro basics: See [pd-timing-metro-counters.md](pd-timing-metro-counters.md)
- Message sequencing: See [pd-timing-sequencing.md](pd-timing-sequencing.md)
- Overview: See [pd-timing-reference.md](pd-timing-reference.md)

---

## Pattern 1: Auto-Stop Counter (1-10)
```
[bng]
|
[trigger bang bang]
|         \
|          [0]  <- initialize to 0 first
|          /
[metro 500]
|
[float]
|  \
|   [+ 1]
|   /
|  /
[float]
|
[select 10]  <- matches value 10
|
[stop]
|
[metro]
```

### Raw .pd Implementation - Auto-Stop Counter

Stop when reaching 10:
```pd
#N canvas 512 43 668 510 12;
#X floatatom 214 200 4 0 0 0 - - - 0;
#X obj 214 174 + 1;
#X obj 214 121 metro 500;
#X msg 123 124 stop;
#X obj 214 148 float;
#X obj 214 92 trigger bang bang;
#X msg 330 119 0;
#X obj 123 98 select 10;
#X obj 130 353 >= 0;
#X obj 130 379 select 0 1;
#X floatatom 130 327 4 0 0 0 - - - 0;
#X floatatom 214 200 4 0 0 0 - - - 0;
#X obj 214 66 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X connect 0 0 4 0;
#X connect 1 0 7 0;
#X connect 4 0 1 0;
#X connect 5 0 2 0;
#X connect 5 1 6 0;
#X connect 6 0 4 1;
#X connect 7 0 3 0;
#X connect 12 0 5 0;
```

Key pattern:
- `[trigger bang bang]` ensures initialization runs first
- `[select 10]` matches the target value and triggers stop
- Metro stops when it receives stop message
- Integer conversion through float feedback

## Pattern 2: Conditional Counting
```
[floatatom]  <- input value
|
[>= 0]       <- test condition (outputs 1 or 0)
|
[select 0 1] <- route based on condition
|       \
[-1]    [float]  <- clear or continue
        |  \
        |   [+ 1]
        |   /
        |  /
        [float]
```

### Raw .pd Implementation - Conditional Count

Count only when input is non-negative:
```pd
#X obj 130 353 >= 0;
#X obj 130 379 select 0 1;
#X obj 163 434 float;
#X obj 217 435 + 1;
#X msg 130 405 -1;
#X floatatom 130 327 4 0 0 0 - - - 0;
#X floatatom 217 461 4 0 0 0 - - - 0;
#X obj 173 407 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X connect 8 0 9 0;
#X connect 9 0 10 0;
#X connect 9 1 11 0;
#X connect 11 0 12 0;
#X connect 12 0 11 1;
#X connect 12 0 13 0;
#X connect 10 0 11 0;
```

Key pattern:
- `[>= 0]` tests if input is non-negative
- `[select 0 1]` routes based on test result
- Negative values (outlet 0) reset counter to -1
- Non-negative values (outlet 1) increment counter

### Key Concepts

**Select Object**
- `[select <value>]` or `[sel <value>]` outputs bang on match
- Multiple values: `[select 0 1 2]` has outlets for each
- Outlet order: matched values left to right, then unmatched (rightmost)

**Trigger Object**
- `[trigger bang bang]` or `[t b b]` converts input to multiple outputs
- Outputs fire right-to-left (initialization before action)
- Types: `b` (bang), `f` (float), `s` (symbol), `a` (anything)

### When to Use
- Bounded sequences (count to N then stop)
- State-based behavior (only count when condition met)
- Limit cycle detection
- Pattern variations based on input

### Heartbeat Applications
- Count beats per measure/phrase
- Skip beats based on heart rate zones
- Arrhythmia detection (unexpected values)
- Intensity ramping (count up to peak, then reset)
