# Pure Data Message Sequencing Reference

Scheduling messages with timing and queuing patterns.

**Related Topics:**
- Metro and conditional counting: See [pd-timing-metro-counters.md](pd-timing-metro-counters.md) and [pd-timing-conditional-counting.md](pd-timing-conditional-counting.md)
- Delays and pipe: See [pd-timing-delays-timers.md](pd-timing-delays-timers.md) and [pd-timing-pipe.md](pd-timing-pipe.md)
- Loops: See [pd-timing-loops.md](pd-timing-loops.md)
- Overview: See [pd-timing-reference.md](pd-timing-reference.md)

---

## Message Sequencing (`23.sequencing.pd`)

### Qlist (Simple Sequencer)
```
[msg: clear, add receive1 1, add 1000 receive1 0, ...]
|
[qlist]

[r receive1]  [r receive2]
|             |
[outputs...]
```

**Qlist Format:**
```
receive1 1        <- send "1" to receive1
1000 receive1 0   <- wait 1000ms, send "0" to receive1
receive2 2        <- send "2" to receive2
1000 receive2 0   <- wait 1000ms, send "0" to receive2
receive1 3        <- send "3" to receive1
```

**Features:**
- Messages starting with numbers = delay in ms
- Other messages sent via `[send]`/`[receive]`
- Can read/write files
- Tempo control
- Single-step mode

### Raw .pd Implementation - Qlist

Simple message sequencer:
```pd
#N canvas 334 58 895 518 12;
#X obj 186 167 r receive1;
#X obj 282 169 r receive2;
#X msg 46 111 clear \, add receive1 1 \, add 1000 receive1 0 \, add receive2 2 \, add 1000 receive2 0 \, add receive1 3 \, bang;
#X obj 46 152 qlist;
#X floatatom 186 193 0 0 0 0 - - - 0;
#X floatatom 282 194 0 0 0 0 - - - 0;
#X connect 0 0 4 0;
#X connect 1 0 5 0;
#X connect 2 0 3 0;
```

Sequence content:
```
receive1 1
1000 receive1 0
receive2 2
1000 receive2 0
receive1 3
```

Key pattern:
- `[qlist]` receives add messages to populate sequence
- Numbers at start of message = delay in milliseconds
- Receiver names route messages to receivers
- Bang from message triggers playback
- Lines starting with numbers = timed delays

### Text Sequence (Modern Alternative)
```
[text define -k seq]  <- click to edit
|
[msg: line 0, auto]
|
[text sequence seq -g]
```

**Features:**
- Same format as qlist
- More text operations available
- Better for larger sequences
- `-g` flag for GUI integration
- `line 0` rewinds, `auto` starts automatically

### Raw .pd Implementation - Text Sequence

Using text object for sequences:
```pd
#X obj 565 195 text define -k seq;
#A set receive1 1 \; 1000 receive1 0 \; receive2 2 \; 1000 receive2 0 \; receive1 3 \;;
#X msg 576 319 line 0 \, auto;
#X obj 576 373 text sequence seq -g;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
```

Key pattern:
- `[text define]` stores sequence data
- `[text sequence]` plays stored sequence
- `-g` flag enables GUI controls
- `line 0` rewinds to start
- `auto` enables automatic playback

### When to Use

**Qlist:**
- Simple message sequences (< 20 steps)
- Quick prototyping
- One-off patterns

**Text Sequence:**
- Complex sequences (> 20 steps)
- Sequences needing editing
- Multiple sequence storage
- Algorithmic generation of sequences

### Heartbeat Applications

**Lighting Cues:**
```
zone1 systole     <- turn on zone 1 (systole phase)
100 zone1 peak    <- 100ms later, peak brightness
200 zone1 off     <- 200ms later, fade off
300 zone2 on      <- 300ms later, next zone starts
```

**ECG Playback:**
```
p_wave 0.1        <- P-wave amplitude
80 p_wave 0       <- 80ms duration
50 qrs_start 1    <- 50ms later, QRS starts
100 r_peak 1.0    <- R-peak at 100ms
50 s_wave 0.3     <- S-wave
200 t_wave 0.15   <- T-wave
```

**Multi-Zone Patterns:**
- Sequence traveling wave patterns
- Coordinated systole/diastole across zones
- Breathing rhythm overlay
- State machine transitions
