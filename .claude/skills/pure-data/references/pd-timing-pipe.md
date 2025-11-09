# Pure Data Pipe Reference

Delayed message queuing for any data type.

**Related Topics:**
- Delay and timer: See [pd-timing-delays-timers.md](pd-timing-delays-timers.md)
- Message sequencing: See [pd-timing-sequencing.md](pd-timing-sequencing.md)
- Overview: See [pd-timing-reference.md](pd-timing-reference.md)

---

## Pipe Object
```
[floatatom]
|
[pipe 2000]  <- delay any data type
|
[floatatom]
```

**Features:**
- Delays any message type (not just bang)
- Dynamically allocates memory for multiple events
- Can queue unlimited events
- Each event independent

### Raw .pd Implementation - Pipe

Delay any data type:
```pd
#X obj 68 395 pipe 2000;
#X floatatom 68 368 5 0 0 0 - - - 0;
#X floatatom 68 423 5 0 0 0 - - - 0;
#X connect 0 0 1 0;
```

Key pattern:
- Accepts any message type through left inlet
- Delays by specified milliseconds
- Preserves message format through delay
- Can queue unlimited messages

### When to Use

- Note sequences with timing
- Multi-event scheduling
- State changes with delays
- DMX fade timing

### Heartbeat Applications

- ECG waveform simulation (queue P, Q, R, S, T events)
- Breathing pattern overlay (queue inhale/exhale events)
- Multi-zone timing offsets
