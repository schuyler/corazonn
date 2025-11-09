# Pure Data expr: String Manipulation Functions

Reference for string operations in expr (control rate) objects

See also:
- [pd-expr-basics.md](pd-expr-basics.md) - Object reference and inlet/outlet configuration
- [pd-expr-operators-and-functions.md](pd-expr-operators-and-functions.md) - Operators and other function categories
- [pd-expr-examples-and-advanced.md](pd-expr-examples-and-advanced.md) - Examples and performance notes

## String Manipulation Functions

These only work with `expr` (not expr~ or fexpr~) and return symbols.

| Function | Args | Returns | Description |
|----------|------|---------|-------------|
| symbol(), sym() | 1-3 | symbol | Format symbol from int/float/symbol. Like sprintf: 0 args=empty, 1 arg=%s/%d/%f, 2 args=%Xs/%.Xd/%.Xf, 3 args=%Y.Xs/%Y.Xd/%Y.Xf |
| var() | 1 | float | Treat symbol as variable name, return value |
| strlen() | 1 | int | Length of symbol |
| tolower() | 1 | symbol | Convert all to lowercase |
| tonlower() | 2 | symbol | Convert nth character to lowercase |
| toupper() | 1 | symbol | Convert all to uppercase |
| tonupper() | 2 | symbol | Convert nth character to uppercase |
| strcat() | var | symbol | Concatenate strings |
| strncat() | 3 | symbol | Concatenate first n chars of second string |
| strcmp() | 2 | int | Compare strings (>, ==, <) |
| strncmp() | 3 | int | Compare n characters |
| strcasecmp() | 2 | int | Compare ignoring case |
| strncasecmp() | 3 | int | Compare n chars ignoring case |
| strpbrk() | 2 | symbol | Locate first occurrence of any char from second string |
| strspn() | 2 | int | Index of first char NOT in charset |
| strcspn() | 2 | int | Index of first char also in charset |

## Usage Examples

String operations are control-rate only:
```
[expr strcat("hello", " ", "world")]
[expr strlen($s1)]
[expr toupper($s1)]
```

String formatting:
```
[expr symbol($f1)]
[expr symbol($f1, 2)]
[expr symbol($f1, 3, 2)]
```

String comparison and manipulation:
```
[expr strcmp($s1, "target")]
[expr strcasecmp($s1, "TARGET")]
[expr tolower($s1)]
```
