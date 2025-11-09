# Pure Data File Format Reference

Pure Data patches (.pd files) are plain text files that can be created and edited programmatically.

See also:
- [Messaging Patterns](pd-file-format-messaging.md)
- [Organization Techniques](pd-file-format-organization.md)
- [Common Patterns](pd-file-format-patterns.md)
- [Programmatic Generation](pd-file-format-generation.md)
- [Validation Guide](pd-file-format-validation.md)

## File Structure

Every .pd file follows this structure:

```
#N canvas X Y WIDTH HEIGHT FONT;
#X obj X Y object-name [args...];
#X msg X Y message-text;
#X text X Y text-content;
#X floatatom X Y WIDTH MIN MAX LABEL_FLAG - - - FLAGS;
...more objects...
#X connect FROM_OBJ FROM_OUTLET TO_OBJ TO_OUTLET;
...more connections...
```

## Header Line

```
#N canvas X Y WIDTH HEIGHT FONT;
```

**Parameters**:
- `X Y` - Window position (pixels from top-left of screen)
- `WIDTH HEIGHT` - Window dimensions
- `FONT` - Font size (typically 10 or 12)

**Example**:
```
#N canvas 100 100 800 600 12;
```

## Object Types

### Object Box (`#X obj`)

```
#X obj X Y object-name [arg1 arg2 ...];
```

**Examples**:
```
#X obj 50 100 osc~ 440;                    # Oscillator at 440 Hz
#X obj 50 150 *~ 0.5;                      # Multiply by 0.5
#X obj 50 200 dac~;                        # Audio output
#X obj 100 50 loadbang;                    # Fires on patch load
#X obj 100 100 metro 1000;                 # Metro at 1000ms
#X obj 200 150 pack f f;                   # Pack two floats
```

**Coordinates**: X Y position in pixels from top-left of canvas.

### Message Box (`#X msg`)

```
#X msg X Y message-text;
```

**Examples**:
```
#X msg 100 50 bang;
#X msg 100 80 5;
#X msg 100 110 hello world;
#X msg 100 140 1 2 3;
#X msg 150 200 \; pd dsp 1;                # Semicolon sends to receiver
```

**Escaping**:
- Semicolon: `\;`
- Comma: `\,`
- Dollar sign: `\$`

### Text/Comment (`#X text`)

```
#X text X Y text-content;
```

**Examples**:
```
#X text 50 50 This is a comment;
#X text 50 80 Multiple words work fine;
#X text 50 110 Use \, f 20 to set width to 20 characters \, f 20;
```

**Width control**: Append `, f WIDTH` to wrap text at specified width.

### Number Box (`#X floatatom`)

```
#X floatatom X Y WIDTH MIN MAX LABEL_FLAG LABEL RECEIVE SEND FLAGS;
```

**Common pattern** (minimal):
```
#X floatatom 100 100 5 0 0 0 - - - 0;
```

**Parameters**:
- `WIDTH` - Display width in digits (e.g., 5)
- `MIN MAX` - Range limits (0 0 = unlimited)
- `LABEL_FLAG` - Position of label (0 = no label)
- `LABEL` - Label text (use `-` for none)
- `RECEIVE` - Receive name (use `-` for none)
- `SEND` - Send name (use `-` for none)
- `FLAGS` - Various flags (typically 0)

### Inlet/Outlet (`#X obj`)

```
#X obj X Y inlet;
#X obj X Y inlet~;
#X obj X Y outlet;
#X obj X Y outlet~;
```

Used in abstractions to connect to parent patch.

## Connections

```
#X connect FROM_OBJ FROM_OUTLET TO_OBJ TO_OUTLET;
```

**Object numbering**: Zero-indexed, in order of appearance after `#N canvas`.

**Outlet/inlet numbering**: Zero-indexed, left to right.

**Example**:
```
#N canvas 100 100 400 300 12;
#X obj 50 50 loadbang;          # Object 0
#X msg 50 100 440;               # Object 1
#X obj 50 150 osc~;              # Object 2
#X obj 50 200 dac~;              # Object 3
#X connect 0 0 1 0;              # loadbang -> msg
#X connect 1 0 2 0;              # msg -> osc~ inlet
#X connect 2 0 3 0;              # osc~ outlet -> dac~ left
#X connect 2 0 3 1;              # osc~ outlet -> dac~ right
```
