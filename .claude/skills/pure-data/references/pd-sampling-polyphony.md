# Pure Data Polyphonic Sampling

Extracted from Pure Data audio examples (3.audio.examples series).

## D11: Polyphonic Sampler

**Pattern**: Voice allocation with `poly`, instantiation with `clone`

**Use when**: You need multiple simultaneous notes

**Key technique**: Fake MIDI notes for voice allocation, distribute to clones

```pd
[trigger note]
|
[f] -> [+ 1] -> [mod 1e+06]  # generate unique "pitch" tag
|
[makenote 64 duration]  # generate note-off
|
[poly 8 1]  # allocate to 8 voices, steal oldest
|
[stripnote]  # remove note-offs
|
[pack voice pitch amp duration sample start rise decay]
|
[clone -s 1 sampvoice 8]  # 8 instances of abstraction
```

**Notes**:
- `poly` needs unique pitch values to track notes
- `makenote` generates delayed note-off messages
- Voice number routes to correct clone instance
- Each clone receives full parameter list
- Abstraction must not use send/receive (would cross voices)

---

## See Also

- **pd-sampling-triggered-playback.md** - Single voice playback and parameterization
- **pd-sampling-utilities.md** - Key objects reference
