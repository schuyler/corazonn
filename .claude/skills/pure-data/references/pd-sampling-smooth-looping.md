# Pure Data Smooth Loop Techniques

Extracted from Pure Data audio examples (3.audio.examples series).

## B09: Enveloped Looping (Smooth Loops)

**Pattern**: Cosine envelope to eliminate loop clicks

**Use when**: You need smooth looping without audible discontinuities

**Key technique**: Apply cosine envelope (-π/2 to π/2) to amplitude

```pd
[phasor~]
|
[copies for both reading and envelope]
|                           |
[*~ chunk-size]            [-~ 0.5]  # -0.5 to +0.5
|                           |
[+~ 1]                      [*~ 0.5]  # -0.25 to +0.25 (cycles)
|                           |
[tabread4~]                [cos~]
|                           |
[*~]<-----------------------+  # multiply sample by envelope
```

**Notes**:
- Cosine from -90° to +90° (0 to max to 0)
- `cos~` input is in cycles (2π radians = 1)
- Range -0.25 to +0.25 gives the positive part of cosine wave
- Envelope automatically synced to phasor frequency

**Raw .pd implementation:**
```
#X floatatom 142 70 6 0 0 0 - \$0-freq - 0;
#X obj 142 97 phasor~;
#X obj 142 179 -~ 0.5;
#X obj 142 204 *~ 0.5;
#X obj 142 239 cos~;
#X obj 142 272 *~;
#X obj 207 178 *~;
#X obj 207 203 +~ 1;
#X obj 207 229 tabread4~ table18;
#X obj 142 363 output~;
```

---

## B10: Sliding Loop Window

**Pattern**: Variable read point with enveloping

**Use when**: You want to loop different windows of a sample dynamically

**Key technique**: Add adjustable offset to chunk reading

```pd
[freq] [chunk-size(ms)] [read-point(ms)]
   |         |                |
   |         [* 48]           [* 48]
   |         |                |
[phasor~]    |                |
   |         |                |
   [*~]<----+                 |
   |                          |
   [+~]<---------------------+  # add read point offset
   |
   [+~ 1]
   |
[tabread4~]
```

**Notes**:
- Read point can be negative or extend beyond chunk size
- Useful for exploring different parts of a sample
- Combine with cosine envelope (B09) to avoid clicks
- Allows doppler shift effects when changing read point

---

## B13: Overlapping Read Elements

**Pattern**: Two phase-shifted readers summed together

**Use when**: You need smooth transitions without any artifacts

**Key technique**: 180° out-of-phase phasors, each with envelope, summed

```pd
# Voice 1:
[phasor~]
|
[copies for reading and envelope]

# Voice 2:
[phasor~]
|
[+~ 0.5]  # shift 180 degrees
|
[wrap~]   # keep in 0-1 range
|
[copies for reading and envelope]

# Each voice:
phase -> [*~ chunk] -> [+~ read-pt] -> [+~ 1] -> [tabread4~] -> [*~ envelope] -> [+~] (sum)
```

**Notes**:
- When one voice fades out, the other fades in
- Eliminates all discontinuities
- Costs 2x CPU (two readers running)
- Essential for high-quality granular/looping playback

---

## See Also

- **pd-sampling-basic-reading.md** - Variable position reading and fixed-frequency looping
- **pd-sampling-utilities.md** - Key objects and sample table management
