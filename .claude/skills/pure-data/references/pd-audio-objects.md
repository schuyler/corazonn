# Pure Data Audio Objects

Reference catalog of common audio objects in Pure Data.

See also: [Fundamentals](pd-audio-fundamentals.md), [Routing](pd-audio-routing.md), [Examples](pd-audio-examples.md)

## Common Audio Objects

### Oscillators and Generators
- `osc~`: Sinusoid oscillator
- `phasor~`: Ramp/sawtooth (0 to 1)
- `noise~`: White noise

### Filters
- `lop~`: Low-pass filter
- `hip~`: High-pass filter
- `bp~`: Band-pass filter
- `vcf~`: Voltage-controlled filter
- `bob~`: Band-pass/band-reject

### Math and Utilities
- `+~`, `-~`, `*~`, `/~`: Arithmetic
- `max~`, `min~`: Comparison
- `clip~`: Limit range
- `wrap~`: Wrap values
- `sqrt~`, `rsqrt~`, `log~`, `exp~`, `pow~`: Math functions
- `abs~`: Absolute value

### Analysis
- `env~`: Envelope follower
- `fft~`: Fast Fourier Transform
- `ifft~`: Inverse FFT
- `rfft~`, `rifft~`: Real FFT variants
- `framp~`: FFT frequency domain ramp
- `sigmund~`: Pitch tracker (external)

### Delay and Reverb
- `delwrite~`, `delread~`, `delread4~`: Delay lines
- `vd~`: Variable delay
- `rev1~`, `rev2~`, `rev3~`: Simple reverbs (externals)

### Table Lookup
- `tabread4~`: 4-point interpolating table read
- `tabosc4~`: 4-point interpolating table oscillator
- `tabwrite~`: Write signal to table
- `tabplay~`: Play table as sample
- `tabsend~`, `tabreceive~`: Nonlocal table access

### I/O
- `adc~`: Audio input
- `dac~`: Audio output
- `readsf~`: Read soundfile
- `writesf~`: Write soundfile
- `soundfiler`: Load/save arrays to files (control object)

### Conversion
- `sig~`: Float to signal
- `snapshot~`: Signal to float
- `line~`, `vline~`: Smoothed control to signal

### Subpatching
- `inlet~`, `outlet~`: Audio inlets/outlets for subpatches
- `block~`, `switch~`: Block size and switching control
- `throw~`, `catch~`: Nonlocal summing bus
- `send~`, `receive~`: Nonlocal signal routing
