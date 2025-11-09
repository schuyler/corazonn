# Pure Data Timing and Format

Reference material extracted from Pure Data Manual Chapter 2: Theory of Operation

**Related documentation:**
- [Fundamentals](pd-fundamentals.md)
- [Execution Model and Message Passing](pd-execution-model.md)
- [Workflow and Editing](pd-workflow-and-editing.md)
- [Advanced Structures](pd-advanced-structures.md)

## Scheduling

### Time Representation
- 64-bit floating-point numbers
- Sample accuracy, essentially never overflows
- Time in milliseconds to user

### Audio and Message Interleaving
- Audio processed every block (64 samples = ~1.33ms at 48kHz)
- Message cascades run between audio ticks
- Messages never passed during DSP tick (atomic)
- Parameter changes take effect simultaneously

### Determinism
- All scheduled messages happen as scheduled regardless of real-time performance
- External events get consistent time tags
- Time never decreases
- Timer objects measure logical time (deterministic)
- `realtime` object measures physical time (non-deterministic)
- Same-time messages execute in scheduling order

### Computation Load
- Pd maintains lead on computations (user-specified buffer)
- Configure via `-audiobuf` and `-blocksize` flags
- Audio gaps if Pd gets late
- Disk streaming works correctly (batch mode possible)
- GUI runs as separate process (close unused windows)

## Semantics

### Object Creation
- Object box text specifies creation message to Pd
- First word (selector) determines object class
- Message arguments become creation arguments
- Changing text destroys old object, creates new one
- Example: `makenote 64 250` - selector "makenote", arguments "64" and "250"

### Data Persistence
- Design principle: patches are printable (appearance determines functionality)
- Object state changes not reflected in appearance are NOT saved
- Deleting/recreating object reinitializes state
- Some objects have file read/write for state (`text`, etc.)
- Use `loadbang` to initialize parameters on patch load
- Use `savestate` for abstraction state persistence

### Escaping Characters
- Backslash (\\) escapes special characters
- Special characters: space, comma (,), semicolon (;), dollar ($), backslash (\\)
- Example: `Hi\, how are you?` treats comma as literal text

## Raw .pd File Format

Pd patches are stored as plain text files. The raw format uses Tcl-like syntax with space-separated atoms.

### Patch Structure
```
#N canvas 511 38 529 651 12;
#X floatatom 100 94 4 0 0 0 - - - 0;
#X obj 87 86 + 9;
#X msg 87 55 5;
#X text 33 21 Example patch;
#X connect 2 0 1 0;
#X connect 0 0 1 1;
```

### Line Types

**Canvas declaration** (`#N canvas`):
```
#N canvas <x> <y> <width> <height> <font-size>;
```
- x, y: window position
- width, height: window dimensions
- font-size: default text size (12)

**Object** (`#X obj`):
```
#X obj <x> <y> <class> [args];
```

**Message** (`#X msg`):
```
#X msg <x> <y> <message-text>;
```

**Number/GUI** (`#X floatatom`, `#X symbolatom`):
```
#X floatatom <x> <y> <width> <min> <max> <log-flag> <send> <recv> <label> <init>;
```

**Connection** (`#X connect`):
```
#X connect <source-obj-index> <outlet> <dest-obj-index> <inlet>;
```
Objects are indexed in order of creation, starting from 0.

**Comments** (`#X text`):
```
#X text <x> <y> <width> <label>;
```

**Subpatch** (`#N canvas` within `#X obj`):
```
#N canvas <x> <y> <width> <height> <font-size>;
[subpatch contents]
#X restore <x> <y> <label>;
```

**Array** (`#X array`):
```
#N canvas 0 0 450 300 (subpatch) 0;
#X array <name> <size> float <flag>;
#X coords <x-min> <y-max> <x-max> <y-min> <width> <height> <x-flag> <y-flag> <graph-flag>;
#X restore <x> <y> graph;
```

### Examples

**Simple counter with float storage**:
```
#N canvas 531 38 423 657 12;
#X floatatom 107 605 4 0 0 0 - - - 0;
#X obj 107 580 + 1;
#X obj 125 89 float;
#X msg 125 64 bang;
#X connect 3 0 2 0;
#X connect 2 0 1 0;
#X connect 1 0 0 0;
```

**Send/receive example**:
```
#N canvas 499 62 580 460 12;
#X obj 85 144 send crackers;
#X obj 85 171 receive crackers;
#X floatatom 85 117 0 0 0 0 - - - 0;
#X floatatom 85 198 0 0 0 0 - - - 0;
#X connect 2 0 0 0;
#X connect 1 0 3 0;
```

**Message box with semicolon routing**:
```
#X msg 75 312 \; pickles 99 \; crackers 56;
```
This sends value 99 to "pickles" receiver and 56 to "crackers" receiver.
