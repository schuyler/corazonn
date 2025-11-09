# Pure Data Delays and Timers Reference

Time-based operations for scheduling and measuring.

**Related Topics:**
- Pipe delays: See [pd-timing-pipe.md](pd-timing-pipe.md)
- Conditional counting: See [pd-timing-conditional-counting.md](pd-timing-conditional-counting.md)
- Overview: See [pd-timing-reference.md](pd-timing-reference.md)

---

## Delay Object
```
[bng]
|
[delay 2000]  <- schedule bang 2000ms later
|             <- right inlet: set time without scheduling
[output]

[stop]  <- cancel scheduled event
```

**Features:**
- Schedules single event for future time
- Non-integer times allowed (123.45ms)
- Re-banging reschedules (cancels previous)
- Stop message cancels scheduled output

### Raw .pd Implementation - Delay

Single delayed event:
```pd
#N canvas 470 64 566 499 12;
#X obj 57 145 print;
#X msg 71 84 stop;
#X obj 57 115 delay 2000;
#X floatatom 356 259 7 0 0 0 - - - 0;
#X obj 388 209 delay 123.45;
#X obj 57 55 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X obj 356 182 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X connect 1 0 2 0;
#X connect 2 0 0 0;
#X connect 4 0 3 0;
#X connect 5 0 2 0;
#X connect 6 0 4 0;
```

Key pattern:
- Bang triggers delay scheduling
- Delay outputs bang after specified milliseconds
- Stop message cancels scheduled output
- Right inlet sets time without scheduling

## Timer Object
```
[bng]  [bng]
|       |
|       [delay 123.45]
|       |
[timer]
|
[floatatom]  <- elapsed time in ms
```

**Features:**
- Measures time between left and right inlet bangs
- Useful for performance measurement
- Tempo detection from tap input

### Raw .pd Implementation - Timer

Measure time between two bangs:
```pd
#X obj 356 234 timer;
#X floatatom 356 259 7 0 0 0 - - - 0;
#X obj 388 209 delay 123.45;
#X obj 356 182 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X connect 3 0 0 0;
#X connect 3 0 2 0;
#X connect 0 0 1 0;
#X connect 2 0 0 1;
```

Key pattern:
- Left inlet receives first bang (start)
- Right inlet receives second bang (stop)
- Outputs elapsed time in milliseconds

### When to Use

**Delay:**
- One-shot events (flash after 100ms)
- Debouncing inputs
- Accent patterns (delay certain beats)

**Timer:**
- BPM detection from taps
- Performance profiling
- Rhythm analysis

### Heartbeat Applications

**Delay:**
- Post-beat flashes (100-200ms after R-wave)
- Refractory period simulation
- Delayed response to intensity peaks

**Timer:**
- R-R interval measurement (heart rate variability)
- Beat-to-beat timing for adaptive patterns
