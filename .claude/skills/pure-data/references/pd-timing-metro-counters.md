# Pure Data Metro and Counters Reference

Basic timing control with metro and float-based counting.

**Related Topics:**
- Conditional counting: See [pd-timing-conditional-counting.md](pd-timing-conditional-counting.md)
- Sequencing: See [pd-timing-sequencing.md](pd-timing-sequencing.md)
- Overview: See [pd-timing-reference.md](pd-timing-reference.md)

---

## Counters with Metro (`05.counter.pd`)

### Core Pattern
```
[tgl]
|
[metro 500]  <- outputs bang every 500ms
|
[float]      <- storage for current count
|  \
|   [+ 1]    <- increment
|   /
|  /
[float]      <- feedback loop
|
[output]
```

### Raw .pd Implementation

Simple counter with metro and float storage:
```pd
#N canvas 531 38 423 657 12;
#X floatatom 107 605 4 0 0 0 - - - 0;
#X obj 107 580 + 1;
#X obj 177 351 + 1;
#X msg 125 64 bang;
#X obj 182 88 + 1;
#X obj 53 544 metro 500;
#X obj 125 89 float;
#X obj 125 262 float;
#X obj 53 580 float;
#X obj 53 486 tgl 19 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000 0 1;
#X connect 1 0 0 0;
#X connect 1 0 8 1;
#X connect 3 0 6 0;
#X connect 5 0 8 0;
#X connect 6 0 4 0;
#X connect 7 0 0 0;
#X connect 8 0 1 0;
#X connect 9 0 5 0;
```

Key connections:
- Toggle controls metro on/off
- Metro outputs bang at regular intervals
- Float stores and increments the count
- + 1 increments on each bang
- Feedback loop: output goes back to float's cold inlet

### Key Concepts

**Float as Storage**
- `[float]` or `[f]` stores a single floating-point number
- Hot inlet (left): bang triggers output
- Cold inlet (right): stores value without outputting

**Metro Object**
- `[metro <ms>]` outputs bang at regular intervals
- Controlled by toggle (1 = on, 0 = off)
- Time specified in milliseconds (500 = twice per second)

### When to Use
- Regular heartbeat generation (BPM sync)
- Step sequencers for lighting patterns
- Animation frame triggers
- Periodic sensor polling

### Heartbeat Applications
- Master clock for coordinated lighting
- Heart rate to metro conversion: `[metro <60000/BPM>]`
- Breathing rhythm patterns (slower metro)
- Synchronized multi-zone effects
