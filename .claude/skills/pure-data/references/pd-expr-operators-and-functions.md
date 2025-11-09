# Pure Data expr: Operators and Functions

Reference for operators and computational functions in expr family objects

See also:
- [pd-expr-basics.md](pd-expr-basics.md) - Object reference and inlet/outlet configuration
- [pd-expr-strings.md](pd-expr-strings.md) - String manipulation functions
- [pd-expr-examples-and-advanced.md](pd-expr-examples-and-advanced.md) - Examples and performance notes

## Operators

Listed from highest to lowest precedence:

| Operator | Description |
|----------|-------------|
| ~ | One's complement |
| * | Multiply |
| / | Divide |
| % | Modulo |
| + | Add |
| - | Subtract |
| << | Shift left |
| >> | Shift right |
| < | Less than (boolean) |
| <= | Less than or equal (boolean) |
| > | Greater than (boolean) |
| >= | Greater than or equal (boolean) |
| == | Equal (boolean) |
| != | Not equal (boolean) |
| & | Bitwise AND |
| ^ | Exclusive OR |
| \| | Bitwise OR |
| && | Logical AND (boolean) |
| \|\| | Logical OR (boolean) |
| ! | Logical NOT (boolean) |

## Functions

### General Functions

| Function | Args | Description |
|----------|------|-------------|
| if() | 3 | Conditional: if(condition, IfTrue, IfFalse). In expr~, if condition is signal, evaluated per-sample |
| int() | 1 | Convert to integer |
| rint() | 1 | Round to nearby integer |
| floor() | 1 | Largest integer ≤ argument |
| ceil() | 1 | Smallest integer ≥ argument |
| float() | 1 | Convert to float |
| min() | 2 | Minimum |
| max() | 2 | Maximum |
| abs() | 1 | Absolute value |
| isinf() | 1 | Is infinite |
| finite() | 1 | Is finite |
| isnan() | 1 | Is not a number |
| copysign() | 2 | Copy sign of number |
| imodf() | 1 | Get signed integer from float |
| modf() | 1 | Get signed fractional from float |
| drem() | 2 | Floating-point remainder |
| fmod() | 2 | Floating-point remainder |

### Power Functions

| Function | Args | Description |
|----------|------|-------------|
| pow() | 2 | Raise to power: pow(x,y) = x^y |
| sqrt() | 1 | Square root |
| exp() | 1 | e raised to power of argument |
| ln(), log() | 1 | Natural logarithm |
| log10() | 1 | Log base 10 |
| fact() | 1 | Factorial |
| erf() | 1 | Error function |
| erfc() | 1 | Complementary error function |
| cbrt() | 1 | Cube root |
| expm1() | 1 | Exponential minus 1 |
| log1p() | 1 | Logarithm of 1 plus |
| ldexp() | 2 | Multiply float by integral power of 2 |

### Trigonometric Functions

All expect radian values.

| Function | Args | Description |
|----------|------|-------------|
| sin() | 1 | Sine |
| cos() | 1 | Cosine |
| tan() | 1 | Tangent |
| asin() | 1 | Arc sine |
| acos() | 1 | Arc cosine |
| atan() | 1 | Arc tangent |
| atan2() | 2 | Arc tangent of 2 variables |
| sinh() | 1 | Hyperbolic sine |
| cosh() | 1 | Hyperbolic cosine |
| tanh() | 1 | Hyperbolic tangent |
| asinh() | 1 | Inverse hyperbolic sine |
| acosh() | 1 | Inverse hyperbolic cosine |
| atanh() | 1 | Inverse hyperbolic tangent |
| hypot() | 2 | Euclidean distance (0 to location) |

### Table Functions

| Function | Args | Description |
|----------|------|-------------|
| size() | 1 | Size of table |
| sum() | 1 | Sum of all elements |
| Sum() | 3 | Sum of elements in specified boundary |
| avg() | 1 | Average of all elements |
| Avg() | 3 | Average of elements in specified boundary |

### Acoustics Functions

| Function | Args | Description |
|----------|------|-------------|
| mtof() | 1 | MIDI pitch to frequency (Hz) |
| ftom() | 1 | Frequency (Hz) to MIDI pitch |
| dbtorms() | 1 | dB to RMS |
| rmstodb() | 1 | RMS to dB |
| powtodb() | 1 | Power to dB |
| dbtopow() | 1 | dB to power |
