# Pure Data Common Patterns

See also:
- [File Format Reference](pd-file-format-reference.md)
- [Messaging Patterns](pd-file-format-messaging.md)
- [Organization Techniques](pd-file-format-organization.md)
- [Programmatic Generation](pd-file-format-generation.md)
- [Validation Guide](pd-file-format-validation.md)

## Simple Oscillator Patch

```
#N canvas 100 100 400 300 12;
#X obj 50 100 osc~ 440;
#X obj 50 150 *~ 0.1;
#X obj 50 200 dac~;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X connect 1 0 2 1;
```

## Loadbang Pattern

```
#X obj 50 50 loadbang;
#X msg 50 100 1;
#X obj 50 150 s some-init-value;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
```

## OSC Receiver Pattern

```
#X obj 50 50 udpreceive 8000;
#X obj 50 100 unpackOSC;
#X obj 50 150 routeOSC /heartbeat/0;
#X obj 50 200 s ibi-0;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X connect 2 0 3 0;
```

## Table Creation

```
#X obj 50 50 table sample-0;
```

Or with array properties:
```
#N canvas 0 0 450 300 (subpatch) 0;
#X array sample-0 96000 float 2;
#X coords 0 1 96000 -1 200 140 1;
#X restore 100 100 graph;
```
