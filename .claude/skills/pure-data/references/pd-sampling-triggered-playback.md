# Pure Data Triggered Playback Techniques

Extracted from Pure Data audio examples (3.audio.examples series).

## C05: One-Shot Sampler with line~

**Pattern**: Use `line~` instead of `phasor~` for triggered playback

**Use when**: Playing samples once on trigger (drums, one-shots)

**Key technique**: Fade out current sound, then trigger new `line~` ramp

```pd
[bang]  # trigger
|
[mute output, wait 5ms, then start]
|
# Cutoff envelope:
[line~] <- [r cutoff]  # 0-1 for amplitude
|
# Phase generator:
[line~] <- [r phase]  # message: "1, 4.8e+08 1e+07"
|                      # (start, end samples, duration ms)
[+~ 1]
|
[tabread4~]
|
[*~] <- cutoff
```

**Notes**:
- Message format: `start_sample, end_sample duration_ms`
- Duration calc: `samples / sample_rate * 1000`
- 5ms fade prevents clicks when retriggering
- Can vary speed by changing end_sample value

**Raw .pd implementation:**
```
#X obj 86 75 r phase;
#X obj 86 105 line~;
#X obj 86 135 tabread4~ tab28;
#X obj 126 165 r cutoff;
#X obj 126 192 line~;
#X obj 86 192 *~;
#X obj 86 244 output~;
#X obj 225 99 bng 19 250 50 0 empty empty empty 0 -6 0 8;
#X obj 325 154 delay 5;
#X msg 225 190 \; cutoff 0 5;
#X msg 325 189 \; phase 1 \, 4.8e+08 1e+07 \; cutoff 1;
```

---

## D10: Parameterized Sampler

**Pattern**: Store all playback parameters, calculate transposition

**Use when**: You need full control over sample playback (pitch, envelope, position)

**Key technique**: Parameter packing with transposition calculation

```pd
# Parameters:
[pitch(MIDI)] [amp(dB)] [duration(ms)] [sample#] [start(ms)] [rise(ms)] [decay(ms)]
|
[unpack f f f f f f f]
|
# Transposition:
[pitch] -> [expr pow(2, $f1/1200)] -> [* duration_samples] -> end_phase
|
# Envelope:
[amp] -> [dbtorms] -> [sqrt] -> [sqrt] -> [line~] -> [*~ (4x)] -> amplitude envelope
|
# Trigger after 5ms mute:
[delay 5] -> pack all params -> send to voice
```

**Notes**:
- MIDI pitch: `pow(2, cents/1200)` for frequency ratio
- Envelope uses 4th root/power for natural curve
- Sample number switches between loaded tables
- Rise/decay times in message: `0, amplitude rise_ms, 0 decay_ms`

---

## See Also

- **pd-sampling-polyphony.md** - Multiple simultaneous notes
- **pd-sampling-utilities.md** - Key objects and table management
