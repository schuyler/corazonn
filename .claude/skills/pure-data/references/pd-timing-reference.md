# Pure Data Timing and Sequencing Quick Reference

Overview and reference tables for timing techniques.

**Detailed References:**
- Metro and counters: See [pd-timing-metro-counters.md](pd-timing-metro-counters.md)
- Conditional counting: See [pd-timing-conditional-counting.md](pd-timing-conditional-counting.md)
- Delays and timers: See [pd-timing-delays-timers.md](pd-timing-delays-timers.md)
- Pipe queuing: See [pd-timing-pipe.md](pd-timing-pipe.md)
- Message sequencing: See [pd-timing-sequencing.md](pd-timing-sequencing.md)
- Loops: See [pd-timing-loops.md](pd-timing-loops.md)

---

## Timing Precision Notes

All Pd time calculations are **idealized** - they don't account for:
- Computation time
- OS latency
- Audio buffer size effects

This allows deterministic timing algorithms, but actual output timing depends on:
- System load
- Audio driver settings
- Block size (64 samples default)

**For heartbeat project:**
- Metro good enough for lighting (humans perceive ~30ms threshold)
- Delay suitable for sub-beat accents
- Use audio-rate for sample-accurate timing
- Consider jitter accumulation over long sequences

---

## Quick Reference Table

| Technique | Object | Timing | Use Case |
|-----------|--------|--------|----------|
| Regular pulses | `[metro]` | Periodic | Heartbeat clock, step sequencer |
| Single event | `[delay]` | One-shot | Accents, debounce, post-beat flash |
| Time measurement | `[timer]` | On-demand | BPM detection, profiling |
| Counted loops | `[until N]` | Immediate | Burst generation, initialization |
| Conditional loops | `[until] + stop` | Immediate | Calculations, searches |
| Event sequences | `[qlist]` | Scheduled | Lighting cues, patterns |
| Complex sequences | `[text sequence]` | Scheduled | ECG playback, multi-zone |
| Delayed data | `[pipe]` | Queued | Multi-event timing, fades |

---

## Common Patterns for Heartbeat

### BPM to Metro
```
[floatatom]  <- BPM input
|
[/ 60]       <- beats per second
|
[* 1000]     <- milliseconds per beat
|
[metro]
```

Or combined:
```
[BPM]
|
[expr 60000/$f1]  <- ms per beat
|
[metro]
```

### Beat Counter with Reset
```
[metro]
|
[float]
|  \
|   [+ 1]
|   /
|  /
[float]
|
[mod 4]  <- reset every 4 beats
|
[beat number 0-3]
```

### Delayed Multi-Zone Trigger
```
[bang]  <- heartbeat event
|
[trigger bang bang bang]
|    |       |
|    [delay 50]
|    |       [delay 100]
|    |       |
[zone1] [zone2] [zone3]
```

### Timed Sequence Pattern
```
[qlist]
zone1 systole
100 zone1 peak
200 zone1 diastole
300 zone2 systole
400 zone2 peak
```
