# Pure Data Audio Routing

Reference material for signal routing and feedback prevention in Pure Data.

See also: [Fundamentals](pd-audio-fundamentals.md), [Performance](pd-audio-performance.md), [Multichannel](pd-audio-multichannel.md)

## Audio Network Constraints

### No Cycles Allowed
- Audio network must be acyclic (no loops)
- Feedback loops cause error: "DSP loop detected"
- Use nonlocal signal connections for feedback (see below)

### Nonlocal Signal Connections

Three types of nonlocal connections for feedback or cross-window routing:

#### throw~ / catch~
- Summing bus implementation
- `throw~` adds into bus, `catch~` reads and zeros bus
- Many `throw~` to one `catch~` allowed
- One `throw~` can't talk to multiple `catch~`
- Can reset `throw~` destination

#### send~ / receive~
- `send~` saves signal
- `receive~` picks up signal (any number can receive)
- One `receive~` picks up one `send~` at a time
- Can switch between `send~` sources

#### delwrite~ / delread~ / delread4~
- Delay line implementation
- Minimum delay: one block (~1.45ms default)
- `delread4~` provides 4-point interpolation

### Reblocking Constraints
- Don't use `throw~/catch~` or `send~/receive~` between different block sizes
- Well-tested reblocking: `inlet~` and `outlet~`
- Signal sent backward in sort order: delayed by one block

## Multichannel Routing

Available since Pd 0.54-0. See [Multichannel Signals](pd-audio-multichannel.md) for full details.

### Nonlocal Multichannel
Can pass multichannel signals:
- `send~` / `receive~`
- `throw~` / `catch~`
- `inlet~` / `outlet~`
- `dac~` / `adc~`: Multiple I/O channels to/from one multichannel signal

### Channel Count Specification
Objects taking arguments for channel count:
- `receive~`
- `catch~`
- `adc~`
