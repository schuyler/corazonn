# Pure Data Organization Techniques

See also:
- [File Format Reference](pd-file-format-reference.md)
- [Messaging Patterns](pd-file-format-messaging.md)
- [Common Patterns](pd-file-format-patterns.md)
- [Programmatic Generation](pd-file-format-generation.md)
- [Validation Guide](pd-file-format-validation.md)

## Subpatch Definition

```
#N canvas X Y WIDTH HEIGHT subpatch-name FLAGS;
... objects inside subpatch ...
#X restore PARENT_X PARENT_Y pd subpatch-name;
```

**Example**:
```
#N canvas 100 100 400 300 12;
#X obj 100 100 pd my-subpatch;     # Object 0 in main patch

#N canvas 200 200 300 200 my-subpatch 0;
#X obj 50 50 inlet;                # Inside subpatch
#X obj 50 100 * 2;
#X obj 50 150 outlet;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X restore 100 100 pd my-subpatch;  # Closes subpatch definition

#X msg 100 50 5;                   # Object 1 in main patch
#X floatatom 100 150 5 0 0 0 - - - 0;  # Object 2 in main patch
#X connect 1 0 0 0;                # msg -> subpatch inlet
#X connect 0 0 2 0;                # subpatch outlet -> number
```

## Abstractions

Abstractions are separate .pd files referenced by name.

**File: doubler.pd**
```
#N canvas 100 100 300 200 12;
#X obj 50 50 inlet;
#X obj 50 100 * 2;
#X obj 50 150 outlet;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
```

**Using in parent:**
```
#N canvas 100 100 400 300 12;
#X obj 100 100 doubler;            # Loads doubler.pd
#X msg 100 50 5;
#X floatatom 100 150 5 0 0 0 - - - 0;
#X connect 1 0 0 0;
#X connect 0 0 2 0;
```

## Creation Arguments

Use `$1`, `$2`, `$3`, etc. in abstractions to reference creation arguments.

**File: multiply.pd**
```
#N canvas 100 100 300 200 12;
#X obj 50 50 inlet;
#X obj 50 100 * $1;              # $1 replaced with first argument
#X obj 50 150 outlet;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
```

**Using with arguments:**
```
#X obj 100 100 multiply 3;        # Multiplies by 3
#X obj 100 150 multiply 0.5;      # Multiplies by 0.5
```
