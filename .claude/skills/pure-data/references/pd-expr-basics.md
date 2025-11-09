# Pure Data expr Family: Basics

Reference for expr, expr~, and fexpr~ objects - C-like expression evaluation in Pure Data

See also:
- [pd-expr-operators-and-functions.md](pd-expr-operators-and-functions.md) - Operators and function reference
- [pd-expr-strings.md](pd-expr-strings.md) - String manipulation functions
- [pd-expr-examples-and-advanced.md](pd-expr-examples-and-advanced.md) - Examples and performance notes

## Overview

The expr family provides C-like expression evaluation objects:
- **expr**: Control rate (messages)
- **expr~**: Signal rate (vector operations on audio blocks)
- **fexpr~**: Sample-by-sample with access to previous input/output samples

Originally from IRCAM's jMax, now built-in native objects in Pd.
Released under BSD License.

## expr (Control Rate)

### Basic Usage
Evaluates C-like expressions at control rate.

### Inlets
Defined by variables in expression:
- `$i#`: Integer input (inlet #, 1-100)
- `$f#`: Float input (inlet #, 1-100)
- `$s#`: Symbol input (inlet #, 1-100)

Example: `$i1`, `$f2`, `$s3` creates 3 inlets (integer, float, symbol)

### Outlets
Multiple expressions separated by semicolons create multiple outlets (up to 100).
Expressions evaluated **right to left** (bottom to top).

Example:
```
[expr $f1 + 10; $f1 * 2]
```
Creates 2 outlets: first outputs `$f1 * 2`, second outputs `$f1 + 10`.

### Type Conversion
- Float to integer: Automatic if inlet defined as `$i#`
- Explicit conversion: Use `int()`, `float()` functions

### Arrays and Variables
- **Arrays**: Accessed like C arrays: `tabname[5]`
- **Variables**: From `value` object: `valx + 10`
- **Dynamic arrays**: `$s2[5]` uses symbol from inlet 2 as array name

### String Output
expr can output symbols using string functions (see String Functions below).

## expr~ (Signal Rate)

### Basic Usage
Efficient signal and control stream processing via vector operations on audio blocks.
Operations happen on entire audio block (64 samples by default).

### Inlets
Same as expr, plus:
- `$v#`: Signal vector input (inlet #, 1-100)

At least first inlet should be signal (`$v1`).

Example:
```
[expr~ $v1 * $f2 + $v3]
```
Creates 3 inlets: signal, float, signal.

### Outlets
Multiple expressions create multiple signal outlets.
All outputs are signals.

### MSP Limitation
In Max/MSP (not Pd): Signal inlets must come first.
- Pd: Can mix `$v`, `$i`, `$f`, `$s` in any order
- MSP: All `$v` must precede other types

## fexpr~ (Sample-by-Sample with History)

### Basic Usage
Sample-by-sample evaluation with access to previous samples.
For FIR and IIR filters, custom DSP algorithms.

### Inlets
First inlet must be signal:
- `$x#[n]`: Signal input # at sample offset n
  - `$x1[0]` or `$x1`: Current sample
  - `$x1[-1]`: Previous sample
  - `$x1[-n]`: n samples ago (up to block size, 64 default)
- `$i#`, `$f#`, `$s#`: Control inlets (same as expr)

Note: `$v#` syntax NOT allowed in fexpr~.

### Outlets
- `$y#[n]`: Output # at sample offset n
  - `$y1[-1]`: Previous output sample from first expression
  - `$y1[-n]`: n samples ago (up to block size)
  - Index from -1 to -blocksize

Multiple expressions create multiple signal outlets.
Each outlet accessible via `$y#`.

### Linear Interpolation
Fractional offsets use linear interpolation: `$x1[-1.5]`.

### Example: Simple FIR Filter
Average current and previous sample:
```
[fexpr~ ($x1[0] + $x1[-1]) / 2]
```
Or simplified (brackets optional for current sample):
```
[fexpr~ ($x1 + $x1[-1]) / 2]
```

### Example: IIR Filter
Using previous output:
```
[fexpr~ $x1 + 0.9 * $y1[-1]]
```

### Methods
- `clear`: Clear all past input and output buffers
- `clear x#`: Clear past values of input #
- `clear y#`: Clear past values of output #
- `set x# val1 val2 ...`: Set past input values (x#[-1], x#[-2], ...)
- `set y# val1 val2 ...`: Set past output values (y#[-1], y#[-2], ...)
- `set val1 val2 ...`: Set first past value of each output
