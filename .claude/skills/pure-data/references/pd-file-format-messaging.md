# Pure Data Messaging Patterns

See also:
- [File Format Reference](pd-file-format-reference.md)
- [Organization Techniques](pd-file-format-organization.md)
- [Common Patterns](pd-file-format-patterns.md)
- [Programmatic Generation](pd-file-format-generation.md)
- [Validation Guide](pd-file-format-validation.md)

## Send/Receive Pattern

### Send (`#X obj`)

```
#X obj X Y s name;        # Control-rate send
#X obj X Y s~ name;       # Audio-rate send
```

### Receive (`#X obj`)

```
#X obj X Y r name;        # Control-rate receive
#X obj X Y r~ name;       # Audio-rate receive
```

**Example**:
```
#X obj 50 100 r ibi-0;
#X obj 50 150 expr 60000/$f1;
#X obj 50 200 s bpm-0;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
```

## Local Send/Receive (`$0`)

Use `$0` prefix for instance-unique send/receive names.

**File: counter.pd**
```
#N canvas 100 100 300 250 12;
#X obj 50 50 inlet;
#X obj 50 100 f 0;                # Float storage
#X obj 80 100 + 1;                # Increment
#X obj 50 150 s $0-count;         # Local send
#X obj 50 200 r $0-count;         # Local receive
#X obj 50 250 outlet;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X connect 1 0 3 0;
#X connect 2 0 1 1;
#X connect 4 0 5 0;
```

Each instance gets unique `$0` value (e.g., `1001-count`, `1002-count`).

## Message Box Variables

Use `$1`, `$2` in message boxes to reference incoming values.

```
#X msg 100 100 frequency $1;      # Incoming 440 -> "frequency 440"
#X msg 100 130 $2 $1;              # Swap order: "5 6" -> "6 5"
#X msg 100 160 add $1 $2 $3;       # "1 2 3" -> "add 1 2 3"
```
