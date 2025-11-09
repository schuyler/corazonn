# Pure Data Sampling Utilities & Reference

Extracted from Pure Data audio examples (3.audio.examples series).

## General Sample Table Management

**Loading samples**:
```pd
[read ../path/to/file.wav table-name(
|
[soundfiler]
```

**Recording to table**:
```pd
[adc~]
|
[*~ envelope]  # fade in/out to avoid clicks
|
[tabwrite~ table-name]
```

**Table sizing**:
- Use `resize` message before recording
- Add 3 samples for `tabread4~` interpolation
- Example: 4 seconds at 48kHz = 192000 samples (192003 with padding)

---

## Key Objects Summary

- `tabread4~` - 4-point interpolation table reader (needs index)
- `phasor~` - Sawtooth oscillator (0-1 ramp), perfect for looping
- `line~` - Linear ramp generator, good for one-shots
- `vline~` - Multiple scheduled ramps in one object
- `soundfiler` - Load/save audio files to tables
- `tabwrite~` - Record audio signal to table
- `cos~` - Cosine oscillator (input in cycles)
- `wrap~` - Wrap signal to 0-1 range
- `samphold~` - Sample and hold (freeze value)
- `poly` - Polyphonic voice allocator
- `clone` - Create multiple instances of abstraction

---

## See Also

- **pd-sampling-basic-reading.md** - Scratch machine and basic looping
- **pd-sampling-smooth-looping.md** - Smooth loop playback with enveloping
- **pd-sampling-triggered-playback.md** - One-shot playback and parameterization
- **pd-sampling-polyphony.md** - Multiple simultaneous voices
