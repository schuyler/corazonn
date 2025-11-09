# Pure Data Advanced Structures

Reference material extracted from Pure Data Manual Chapter 2: Theory of Operation

**Related documentation:**
- [Fundamentals](pd-fundamentals.md)
- [Execution Model and Message Passing](pd-execution-model.md)
- [Workflow and Editing](pd-workflow-and-editing.md)
- [Timing and Format](pd-timing-and-format.md)

## Subpatches

Two mechanisms for subpatches:

### One-Off Subpatches
- Created as `pd` or `pd my-name` object box
- Contents saved as part of parent patch
- Each copy can be changed individually
- Analogy: bracketed blocks of code

### Abstractions
- Separate .pd file invoked by filename (without .pd extension)
- Changes affect all instances
- Can take creation arguments: `my-abstraction 5` sets `$1` to 5
- Dollar signs in object boxes expanded at creation time
- Dollar signs in message boxes expanded at message time
- Use `clone` to create/manage multiple copies
- Analogy: subroutines or functions

#### Raw .pd file format:
```
#X obj 85 171 receive crackers;
#X obj 245 176 receive pickles;
#X obj 85 144 send crackers;
#X obj 247 138 send pickles;
```

### Inlet/Outlet Objects
- `inlet` / `outlet`: Control messages
- `inlet~` / `outlet~`: Audio signals
- `inlet~` has right outlet for control messages mixed into signal inlet
- Appear on parent box in left-to-right order

### Graph-on-Parent
- Checkbox in subpatch/abstraction properties
- Makes controls visible on parent patch
- Only controls appear (not regular objects)
- Right-click and select "Open" to edit (clicking interacts with controls)

## Arrays

Linear arrays of numbers for wavetables, samples, lookup tables, control data.

#### Raw .pd file format:
```
#N canvas 0 0 450 300 (subpatch) 0;
#X array array99 5 float 2;
#X coords 0 1 5 -1 403 199 1 0 0;
#X restore 31 340 graph;
```

### Properties
- Predefined name and size (number of points)
- Stored as 32-bit floating-point (4 bytes each)
- Indexed from 0 to N-1
- Memory allocation should happen before audio starts (to avoid buffer under/overruns)

### Storage Requirements
- 1 second at 48kHz: 192 kilobytes
- 1 minute at 48kHz: 11.5 megabytes
- Multi-channel: separate array per channel

### Usage
- Control operations: `tabread`, `tabwrite`
- Signal operations: `tabread~`, `tabread4~` (4-point interpolation), `tabwrite~`
- Other operations: `soundfiler`, `tabplay~`, `tabsend~`, `tabreceive~`

#### Raw .pd file format:
```
#X obj 132 619 tabread;
#X obj 131 593 tabwrite;
#X obj 228 593 tabread~;
#X obj 293 593 tabread4~;
#X obj 366 593 tabwrite~;
```

### Appearance
- Usually in graph-on-parent subpatches (visible as rectangle)
- Can be in regular subpatches (text box)
- Created via Put menu → array
