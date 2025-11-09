# Envelope Techniques Reference

**Related envelope documentation:**
- [Envelope Basics](pd-envelopes-basics.md) - Foundation with line~ and vline~
- [ADSR Envelopes](pd-envelopes-adsr.md) - Reusable envelope generators
- [dB Conversions and Quartic Envelopes](pd-envelopes-dbtable-conversions.md) - Logarithmic control and curved envelopes
- [Pitch and Portamento](pd-envelopes-pitch-modulation.md) - Pitch-based envelope techniques

---

## General Envelope Techniques

### vline~ vs line~

**line~**:
- Simple ramp generator
- Single target per message
- Need external timing (`delay`) for multi-segment envelopes

**vline~**:
- Schedules multiple ramp segments
- Delays built into message format
- Better for complex envelopes
- Format: `target1 time1, target2 time2 delay2, ...`

### Envelope Retriggering

**Hard retrigger** (jumps to zero):
- Negative trigger to ADSR
- Send `0` to line~ before new ramp
- Clearer attack on each note

**Soft retrigger** (slur from current level):
- Positive trigger to ADSR
- New ramp starts from current value
- Natural for legato playing

### Performance Optimization

**Lookup tables vs real-time calculation**:
- `tabread4~` faster than `dbtorms~`, `mtof~`
- Use tables for high polyphony or embedded systems
- Tables require initialization and memory
- 4-point interpolation (`tabread4~`) smooths stepped data

**CPU costs** (rough order):
- `line~`, `vline~`: Minimal
- `+~`, `*~`: Very low
- `tabread4~`: Low
- `mtof~`, `dbtorms~`: Medium (transcendental functions)
- `expr~`: High (interpreted expressions)

### Common Patterns

**Amplitude control**:
```
[adsr] → [dbtorms~] → [*~ signal]
```

**Pitch control**:
```
[adsr] → [+~ base_pitch] → [mtof~] → [osc~]
```

**Filter cutoff**:
```
[adsr] → [*~ range] → [+~ base] → [vcf~]
```

**Vibrato depth**:
```
[adsr] → [*~ lfo~] → [+~ 1] → [*~ base_freq] → [osc~]
```

### Envelope Shapes Beyond ADSR

**Exponential decay** (natural instrument simulation):
```
[1(
|
[vline~]
|
[expr~ exp(-$v1 * 5)]  <- exponential decay
```

**Bezier curves** (complex shapes):
```
[vline~]  <- generate 0-1 ramp
|
[expr~ $v1 * $v1 * (3 - 2 * $v1)]  <- smoothstep
```

**Custom table lookup**:
```
[line~ 0 1000]  <- 0 to 1 ramp
|
[*~ table_size]
|
[tabread4~ custom-shape]  <- read custom envelope shape
```

---

## Summary Table

| Technique | Use Case | CPU Cost | Sonic Character |
|-----------|----------|----------|-----------------|
| `line~` + `delay` | Manual envelope control | Low | Direct, explicit timing |
| `vline~` | Multi-segment envelopes | Low | Compact, schedulable |
| ADSR abstraction | Reusable amp envelopes | Low | Classic synth response |
| dB conversion | Natural volume changes | Low (table) / Med (dbtorms~) | Perceptually uniform |
| Quartic curves | Pitch/amp sweeps | Medium (4 extra `*~`) | Smooth, natural motion |
| Pitch envelopes | Note transitions, effects | Medium | Expressive, dynamic |
| Portamento | Pitch sliding | Low | Smooth glides |

### Parameter Ranges Reference

**Amplitude** (dB):
- -∞ to 0 dB: Normal range
- 0 to +20 dB: Boost/headroom
- Table: 0-120 → 0-10 amplitude

**Time** (milliseconds):
- 0-50ms: Percussive, clicks
- 50-200ms: Fast attack/decay
- 200-1000ms: Moderate envelopes
- 1000+ms: Slow, pad-like

**Pitch** (MIDI):
- 0-127: Full MIDI range
- 21-108: Piano range (A0-C8)
- 60: Middle C (261.6 Hz)
- 69: A4 (440 Hz)
