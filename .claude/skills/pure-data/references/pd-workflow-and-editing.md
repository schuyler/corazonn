# Pure Data Workflow and Editing

Reference material extracted from Pure Data Manual Chapter 2: Theory of Operation

**Related documentation:**
- [Fundamentals](pd-fundamentals.md)
- [Execution Model and Message Passing](pd-execution-model.md)
- [Advanced Structures](pd-advanced-structures.md)
- [Timing and Format](pd-timing-and-format.md)

## Edit vs Run Mode

### Run Mode
- Default mode
- Arrow cursor
- Click/interact with GUIs and message boxes
- Shortcuts: Ctrl+/ (DSP on), Ctrl+. (DSP off)

### Edit Mode
- Activated via Edit menu or Ctrl+E
- Hand cursor
- Move boxes by clicking/dragging
- Edit text, create/delete boxes, make/cut connections
- Resize boxes at right edge (double arrow cursor)
- Temporary run mode: hold Ctrl

### Editing Operations
- Select: Click boxes, Shift+Click for multiple, drag rectangle
- Move: Arrow keys (1px), Shift+Arrow (10px)
- Tidy Up: Shift+Ctrl+R to align selected boxes
- Delete: Backspace or Delete key
- Copy/Paste: Ctrl+C, Ctrl+V (connections duplicated too)
- Duplicate: Ctrl+D
- Undo/Redo: Available in both modes
