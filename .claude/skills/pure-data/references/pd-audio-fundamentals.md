# Pure Data Audio Fundamentals

Reference material for audio signal processing fundamentals in Pure Data.

See also: [Audio Routing](pd-audio-routing.md), [Performance](pd-audio-performance.md), [Objects](pd-audio-objects.md), [Multichannel](pd-audio-multichannel.md)

## Sample Rate and Format

### Internal Representation
- Audio signals: 32-bit floating-point numbers internally
- Full dynamic range available
- Input/output range: -1 to 1 (values clipped at boundaries)
- Default sample rate: 48000 Hz (configurable)

### Audio I/O
- Hardware typically: 16-bit or 24-bit
- File formats supported: wave, aiff, caf, next
- File bit depths: 16-bit, 24-bit fixed point, or 32-bit float
- File I/O objects: `soundfiler`, `readsf~`, `writesf~`

## Tilde Objects

### Naming Convention
- Names end with tilde (~) character
- Tilde resembles sinusoid (symbolizes audio function)
- Examples: `osc~`, `*~`, `dac~`, `adc~`, `lop~`

### Block Processing
- Default: 64 samples per block at 48000 Hz
- Block time: ~1.33 milliseconds (1-1/3 ms)
- Audio network sorted into linear order when DSP on
- Runs continuously when DSP enabled
- Sort triggered when: DSP turned on, audio network changed

### Signal Connections
- Visually thicker than control connections
- Can't connect to control inlets
- Audio outlets only connect to signal inlets
- Leftmost inlet may accept both audio and messages

### Inlet Behavior
- Leftmost inlet: May accept audio and/or messages
- Other inlets: Either audio or control (not both)
- Secondary audio inlets: Auto-promote floats to signals at control rate
- Some objects run different algorithms based on input type
  - Example: `lop~` uses efficient routine when no signal at right inlet

### Configurable Inlets
These objects can take control or signal in 2nd inlet via creation argument:
- `+~`, `-~`, `*~`, `/~`
- `max~`, `min~`
- `log~`, `pow~`

## Signal/Control Conversion

### Control to Signal
- `sig~`: Convert float to signal (also sets default with creation argument)
- `line~`: Smooth ramp from control to signal
- `vline~`: Variable-time ramp with sample accuracy
- Most objects auto-promote floats to signals at secondary inlets

### Signal to Control
- Must specify sampling moments
- `snapshot~`: Sample signal at control rate
- `tabwrite~` + `tabread`: Sample to array then read as control
- `env~`: Envelope follower (outputs control floats)
- Analysis objects output control data
