# Pure Data Basic Sampling: Variable Position Reading & Looping

Extracted from Pure Data audio examples (3.audio.examples series).

## B07: Scratch Machine (Variable Position Reading)

**Pattern**: Direct index control with `tabread4~`

**Use when**: You need manual control over playback position (scratching, scrubbing)

**Key technique**: Convert a control value (0-100) to sample index, smooth with `line~`, read with `tabread4~`

```pd
# Control flow:
[hsl] (0-100)
|
[* 480]  # convert to samples (480 samples per 0.01 sec at 48kHz)
|
[pack f 100]  # pack index and line duration (ms)
|
[line~]  # smooth transition
|
[+~ 1]  # add 1 to avoid table start
|
[tabread4~ sample-table]
```

**Notes**:
- `tabread4~` uses 4-point cubic interpolation
- Add 1 to avoid beginning of table (interpolation requirement)
- Table needs 3 extra samples for interpolation (48003 for 1 second at 48kHz)

**Raw .pd implementation:**
```
#X floatatom 72 205 7 0 100 0 - - - 0;
#X obj 72 263 * 480;
#X obj 72 291 pack f 100;
#X obj 72 392 line~;
#X obj 72 419 +~ 1;
#X obj 72 450 tabread4~ sample-table;
#X obj 72 508 output~;
```

---

## B08: Looping Sampler (Fixed Frequency)

**Pattern**: `phasor~` to generate repeating index, scale to chunk size

**Use when**: Looping a segment at a specific frequency (rhythmic repetition, granular texture)

**Key technique**: Use `phasor~` frequency to control loop rate, multiply output by chunk size

```pd
# Control:
[freq(Hz)] [chunk-size(ms)]
    |           |
    |           [* 48]  # convert ms to samples
    |           |
[phasor~]       |
    |           |
    [*~ ]<------+  # scale phase 0-1 to 0-chunk_size
    |
    [+~ 1]  # offset from table start
    |
[tabread4~ table]
```

**Notes**:
- Frequency < 20 Hz: hear repetition/transposition
- Frequency > 50 Hz: hear pitched tone
- Chunk size controls timbre when frequency is high
- Often produces clicks at loop points (see B09 for solution)

**Raw .pd implementation:**
```
#X floatatom 105 180 5 0 0 0 - \$0-freq - 0;
#X floatatom 130 243 8 0 1000 0 - \$0-size - 0;
#X obj 130 269 * 48;
#X obj 105 206 phasor~;
#X obj 105 299 *~ 0;
#X obj 105 343 +~ 1;
#X obj 105 392 tabread4~ table17;
#X obj 105 524 output~;
```

---

## See Also

- **pd-sampling-smooth-looping.md** - Smooth loop playback with enveloping
- **pd-sampling-utilities.md** - Table management and key objects
