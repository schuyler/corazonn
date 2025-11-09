# Pure Data Validation Guide

See also:
- [File Format Reference](pd-file-format-reference.md)
- [Messaging Patterns](pd-file-format-messaging.md)
- [Organization Techniques](pd-file-format-organization.md)
- [Common Patterns](pd-file-format-patterns.md)
- [Programmatic Generation](pd-file-format-generation.md)

## Validation Rules

Check .pd file validity:

1. No syntax errors when opening in Pd
2. All connections reference valid object indices
3. All object indices < total number of objects
4. Coordinates are positive integers
5. File ends with newline

## Common Errors

- Missing semicolon at end of lines
- Invalid object indices in `#X connect`
- Unescaped special characters (`;`, `,`, `$`)
- Missing `#N canvas` header
- Mismatched subpatch `#N canvas` and `#X restore`

## References

- Pure Data file format is not formally documented
- Best reference: Read existing .pd files
- Files are backwards compatible across Pd versions
- Extended Pd flavors may add custom syntax (stick to vanilla)
