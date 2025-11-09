# Pure Data Fundamentals

Reference material extracted from Pure Data Manual Chapter 2: Theory of Operation

**Related documentation:**
- [Execution Model and Message Passing](pd-execution-model.md)
- [Workflow and Editing](pd-workflow-and-editing.md)
- [Advanced Structures](pd-advanced-structures.md)
- [Timing and Format](pd-timing-and-format.md)

## Overview

Pure Data (Pd) is a real-time graphical programming environment designed for audio processing. It resembles the MAX system but is simpler and more portable. Pd can be used as an embeddable audio synthesis library (via libpd) and allows users to define and access data structures in innovative ways.

## Canvases and Patches

A Pd document is called a **canvas** or **patch**. The main Pd window shows console output and has:
- Menu bar (File, Edit, Put, Find, Media, Window, Tools, Help)
- DSP toggle (turns audio processing on/off globally)
- Console area for printout from objects and Pd messages

DSP (Digital Signal Processing) is off by default. When turned on, Pd computes audio samples in realtime for all open patches at 48000 Hz sample rate by default.

## Box Types

Pd patches contain four types of boxes:

### Object Boxes
- Rectangular shape
- Load an instance of a class
- Text consists of atoms (separated by spaces)
- First atom (symbol) determines object type
- Subsequent atoms are creation arguments
- Example: `+ 13` creates an addition object initialized to add 13

#### Raw .pd file format:
```
#X obj 87 86 + 9;
#X obj 311 115 print;
#X obj 125 89 float;
```

### Message Boxes
- Flag-shaped outline
- Text defines message(s) to send when activated
- Can be activated by clicking or receiving input
- Messages sent to outlet or to specified destinations
- Example: `1.5` sends a float message

#### Raw .pd file format:
```
#X msg 87 55 5;
#X msg 217 55 5 6;
#X msg 125 64 bang;
#X msg 184 370 1.2 3.4;
```

### GUI Boxes
- Three basic types: number, symbol, list
- Visually dynamic, content changes during runtime
- Can be used as controls (click/drag) or displays
- Additional GUI types: bang, toggle, sliders, radio buttons (IEMguis)

#### Raw .pd file format:
```
#X floatatom 256 115 3 0 0 0 - - - 0;
#X obj 125 236 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X obj 53 486 tgl 19 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000 0 1;
```

### Comments
- Text annotations
- Don't affect patch execution
- Can't be connected to other boxes

## Inlets and Outlets

- **Inlets**: Inputs at top of boxes
- **Outlets**: Outputs at bottom of boxes
- Boxes may have zero or more inlets/outlets
- Connection type (control or signal) determined by outlet type
