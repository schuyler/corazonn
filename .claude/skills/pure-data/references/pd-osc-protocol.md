# OSC Protocol Reference

For practical networking examples and debugging, see [pd-networking-guide.md](pd-networking-guide.md).

## OSC Protocol

**OSC** = Open Sound Control

### Overview
- Industry-standard protocol for multimedia communication
- Alternative to FUDI for network communication
- More structured than FUDI
- Binary format (vs FUDI text)
- Supports timestamping
- Address pattern matching

### OSC in Pure Data

#### Native OSC Objects

**oscformat**
- Convert Pd lists to OSC packets
- Input: Pd list messages
- Output: Binary OSC packet

**oscparse**
- Parse OSC packets into Pd messages
- Input: Binary OSC packet
- Output: Pd list messages

#### Usage Pattern
Typical setup for OSC communication:
1. Prepare message as Pd list with OSC address pattern
2. `oscformat`: Convert to OSC packet
3. `netsend`: Send over network (UDP typical for OSC)
4. Receive via `netreceive`
5. `oscparse`: Parse back to Pd message

Example patches in "OSC Communication" section below show binary mode transmission suitable for OSC.

### OSC Address Patterns
- Hierarchical naming: `/synth/osc1/frequency`
- Pattern matching with wildcards
- More structured than FUDI's flat namespace

### OSC vs FUDI

#### FUDI Advantages
- Text-based (human readable)
- Simple format
- Native to Pd
- Easy to debug
- No conversion needed for Pd-to-Pd communication

#### OSC Advantages
- Industry standard (interoperability)
- Binary format (more efficient)
- Timestamping support
- Type tagging (explicit data types)
- Address pattern matching
- Better for complex multimedia setups

### External OSC Libraries

While Pd has native `oscformat` and `oscparse`, additional functionality available via externals:
- More complete OSC implementations
- OSC bundle support
- Advanced pattern matching
- Route by address

Check Pd documentation and deken for OSC externals.
