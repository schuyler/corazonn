# Pure Data expr: Examples and Advanced Topics

Real-world patterns, performance considerations, and important notes

See also:
- [pd-expr-basics.md](pd-expr-basics.md) - Object reference and inlet/outlet configuration
- [pd-expr-operators-and-functions.md](pd-expr-operators-and-functions.md) - Operators and function reference
- [pd-expr-strings.md](pd-expr-strings.md) - String manipulation functions

## Usage Examples

### Simple Math
```
[expr $f1 + $f2]
[expr pow($f1, 2)]
[expr sqrt($f1 * $f1 + $f2 * $f2)]
```

### Multiple Outputs
```
[expr sin($f1); cos($f1)]
```
Creates 2 outlets: cosine (first), sine (second).

### Array Access
```
[expr tabname[int($f1)]]
[expr tabname[$i1] * 0.5]
```

### Signal Math
```
[expr~ $v1 * 0.5]
[expr~ ($v1 + $v2) / 2]
[expr~ if($v1 > 0, $v1, 0)]  (rectify)
```

### Filters with fexpr~
Simple lowpass:
```
[fexpr~ $x1 * 0.1 + $y1[-1] * 0.9]
```

Moving average (2-point):
```
[fexpr~ ($x1 + $x1[-1]) / 2]
```

Delay by 10 samples:
```
[fexpr~ $x1[-10]]
```

### Conversions
```
[expr mtof($f1)]  (MIDI to frequency)
[expr ftom($f1)]  (frequency to MIDI)
[expr dbtorms($f1)]  (dB to amplitude)
```

## Real-World Examples from Pure Data Documentation

### Envelope Calculations

Delay time conversion (sample delay to milliseconds):
```pd
#X obj 85 181 expr 1000*1024/$f1;
```
Converts sample count to milliseconds given sample rate.

Gaussian envelope (for waveshaping):
```pd
#X obj 68 251 expr exp(-$f1*$f1);
```
Generates bell curve for PAF (phase-aligned formant) synthesis.

Normalization for table lookup:
```pd
#X obj 50 245 expr exp(-($f1-1)/100);
#X obj 68 222 expr ($f1-100)/25;
```
Map control values to exponential functions and scaled ranges.

### Waveshaping Formulas

Chebyshev polynomials (harmonic waveshaping):
```pd
#X obj 46 174 expr 2*$f1*$f1-1;
#X obj 115 410 expr 4*$f1*$f1*$f1-3*$f1;
#X obj 407 334 expr 16*$f1*$f1*$f1*$f1*$f1-20*$f1*$f1*$f1+5*$f1;
#X obj 170 650 expr 8*$f1*$f1*$f1*$f1-8*$f1*$f1+1;
#X obj 465 582 expr 32*$f1*$f1*$f1*$f1*$f1*$f1-48*$f1*$f1*$f1*$f1+18*$f1*$f1-1;
```
Second through sixth order Chebyshev polynomials T2 through T6 for waveshaping.

Exponential transfer function:
```pd
#X obj 84 183 expr exp(-($f1-1)/100);
```
Exponential decay mapping for waveshaping synthesis.

### Frequency Modulation

Reciprocal for frequency division:
```pd
#X obj 211 366 expr 1/$f1;
#X obj 321 333 expr 1/$f1;
```
Convert frequency ratios to divisors for bandwidth/center-frequency control in PAF synthesis. Divides modulation depths by fundamental frequency.

## Important Notes

### Deprecated Syntax
Old: `func("$s#", ...)`
Current: `func($s#, ...)`

### Variable Access
Variables must be defined with `value` object before use in expr.

### Conditional Evaluation
In expr and fexpr~, `if()` only evaluates needed branch.
In expr~ with signal condition, both branches evaluated.

### Max Inlets/Outlets
Maximum 100 inlets and 100 outlets.

### Expression Evaluation Order
Multiple expressions separated by semicolons:
- Evaluated right to left
- Output order: first expression → first outlet, etc.

### Array Redrawing
Arrays automatically redraw after store operation (0.55+).

### Version History
- 0.58: String functions, better errors, fixed bugs
- 0.57: Fixed fact(), added acoustics functions
- 0.56: fexpr~ accepts float in first input, avg/Avg added
- 0.55: Array redraw, if() optimization, 100 inlets/outlets
- 0.5: Built-in native objects
- 0.4: Multiple expressions, variables, if(), new functions

## Performance Considerations

### expr vs expr~
- expr: Sporadic evaluation (on message)
- expr~: Every audio block (continuous)
- Use expr for control, expr~ for audio

### fexpr~ Cost
- Sample-by-sample more expensive than expr~ vector operations
- Necessary for algorithms requiring 1-sample feedback
- Useful for learning DSP concepts
- Consider native objects for standard operations

### Optimization Tips
- Minimize fexpr~ usage in polyphonic patches
- Use expr~ when possible (block-based faster)
- Pre-calculate constants outside expr
- Use lookup tables for expensive functions in tight loops
