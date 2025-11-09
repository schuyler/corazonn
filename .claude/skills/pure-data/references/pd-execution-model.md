# Pure Data Execution Model

Reference material extracted from Pure Data Manual Chapter 2: Theory of Operation

**Related documentation:**
- [Fundamentals](pd-fundamentals.md)
- [Workflow and Editing](pd-workflow-and-editing.md)
- [Advanced Structures](pd-advanced-structures.md)
- [Timing and Format](pd-timing-and-format.md)

## Object Types

### Control Objects
- Process messages sporadically in response to events
- Examples: `notein`, `stripnote`, `mtof`
- Carry out computations when triggered

### Tilde Objects (Signal Objects)
- Names end with tilde character (~)
- Compute audio samples continuously when DSP is on
- Examples: `osc~`, `*~`, `dac~`
- Run in blocks (64 samples by default at 48000 Hz = ~1.33ms)

## Connections

Two types of connections:
- **Control connections**: Thin lines, carry sporadic messages
- **Signal connections**: Thick lines, carry continuous audio streams

Rules:
- Signal connections can't connect to control inlets
- Control connections to signal inlets auto-convert numbers to signals
- Audio signals run continuously; control computations are interspersed

#### Raw .pd file format:
```
#X connect 1 0 6 0;
#X connect 3 0 4 0;
#X connect 4 0 17 0;
#X connect 6 0 15 0;
#X connect 6 1 0 0;
```
Format: `#X connect <outlet-object> <outlet-index> <inlet-object> <inlet-index>;`

## Messages

Messages contain:
- **Selector**: Symbol defining message type
- **Arguments**: Atoms (numbers or symbols) following selector

### Special Selectors
- `float`: Single number
- `symbol`: Single symbol
- `list`: Multiple atoms (numbers and/or symbols)
- `bang`: Event trigger with no arguments
- `pointer`: Used for data structures (not visible at patch level)

### Atoms
- **Numbers**: Always float type (no integer type in Pd)
- 32-bit floats (single precision) or 64-bit (Pd64)
- Displayed with 6 significant digits precision
- Exponential notation for very large/small values
- **Symbols**: Any non-number text, case-sensitive

### Numerical Precision
- Display: 6 significant digits via '%g' sprintf pattern
- Single precision: integers ±16777216 (±2^24)
- Double precision: integers ±9007199254740992 (±2^53)
- Exponential notation used for exponents ≥6 or ≤-5

## Message Passing

### Depth-First Execution
- Each message triggers a tree of subsequent messages
- Tree executed depth-first
- Order depends on connection creation order (not visible)
- Infinite loops cause stack overflow (legal if `delay` breaks loop)

### Hot and Cold Inlets
- **Hot inlet**: Leftmost inlet, triggers output when receiving messages
- **Cold inlets**: Other inlets, store values without triggering output
- Values in cold inlets are "sticky" (persist until changed)
- Exception: `timer` object treats leftmost inlet as cold

### Outlet Order Convention
- Multiple outlets send messages right to left
- Ensures rightmost inlet receives value before leftmost (hot) inlet
- Use `trigger` (abbreviated `t`) to enforce specific order

### Message Box Variables
- `$1`, `$2`, etc. refer to arguments of incoming message
- Undefined for bang messages or when clicking message box
- Dollar signs can specify variable selectors or destinations

#### Raw .pd file format:
```
#X msg 75 312 \; pickles 99 \; crackers 56;
```
Semicolons within message boxes route to receive objects (syntax: `; <receive-name> <message>`)
