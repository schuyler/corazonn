# Pure Data Multichannel Signals

Reference material for multichannel signal processing (Pd 0.54+).

See also: [Fundamentals](pd-audio-fundamentals.md), [Routing](pd-audio-routing.md), [Objects](pd-audio-objects.md)

## Multichannel Signals

Available since Pd 0.54-0

### Signal Properties
- **Length**: Block size (64 default)
- **Channel count**: 1 by default, can be multichannel

### Multichannel Operations

#### Combining and Splitting
- `snake~`: Combine single channels into multichannel OR split multichannel into singles

#### Nonlocal Multichannel
Can pass multichannel signals:
- `send~` / `receive~`
- `throw~` / `catch~`
- `inlet~` / `outlet~`
- `dac~` / `adc~`: Multiple I/O channels to/from one multichannel signal

#### Channel Count Specification
Objects taking arguments for channel count:
- `receive~`
- `catch~`
- `adc~`

### Multichannel-Aware Objects

#### Stateless Objects
- No memory from one DSP tick to next
- All adapted for multichannel
- Arithmetic/math: `+~`, `-~`, `*~`, `/~`, `wrap~`, `sqrt~`, etc.
- Determine channel count from inputs
- Binary operations can combine single and multichannel

#### Additional Multichannel Support
- `delread~`, `delwrite~`, `delread4~`
- `tabread~`, `tabwrite~`, `tabread4~`
- `tabplay~`, `tabsend~`, `tabreceive~`
- `readsf~`, `writesf~`
- `sig~`, `snapshot~`, `print~`

#### Not Adapted for Multichannel
- Filters and oscillators (many design possibilities)
- Use `clone` object instead for multichannel processing
- `clone` distributes multichannel signals among cloned patches
