# Pure Data Programmatic Generation

See also:
- [File Format Reference](pd-file-format-reference.md)
- [Messaging Patterns](pd-file-format-messaging.md)
- [Organization Techniques](pd-file-format-organization.md)
- [Common Patterns](pd-file-format-patterns.md)
- [Validation Guide](pd-file-format-validation.md)

## Building a Patch Programmatically

1. **Start with header**:
   ```python
   lines = ["#N canvas 100 100 800 600 12;"]
   ```

2. **Add objects** (track indices):
   ```python
   obj_index = 0
   lines.append(f"#X obj 50 50 loadbang;")  # obj 0
   obj_index += 1
   lines.append(f"#X msg 50 100 440;")       # obj 1
   obj_index += 1
   ```

3. **Add connections**:
   ```python
   lines.append(f"#X connect 0 0 1 0;")  # loadbang -> msg
   ```

4. **Write file**:
   ```python
   with open('patch.pd', 'w') as f:
       f.write('\n'.join(lines) + '\n')
   ```

## Calculating Positions

**Grid layout**:
```python
x = 50 + (col * 100)
y = 50 + (row * 80)
```

**Chain layout** (vertical):
```python
x = 100  # Fixed
y = 50 + (index * 60)
```

## Object Index Tracking

Keep track of object indices as you add them:

```python
objects = []

def add_obj(x, y, name, args=""):
    idx = len(objects)
    objects.append(f"#X obj {x} {y} {name} {args};")
    return idx

osc_idx = add_obj(50, 100, "osc~", "440")
mul_idx = add_obj(50, 150, "*~", "0.1")
dac_idx = add_obj(50, 200, "dac~")

connections = [
    f"#X connect {osc_idx} 0 {mul_idx} 0;",
    f"#X connect {mul_idx} 0 {dac_idx} 0;",
    f"#X connect {mul_idx} 0 {dac_idx} 1;",
]
```

## File Template

Minimal working patch template:

```
#N canvas 100 100 600 400 12;
#X text 50 50 Your patch here;
```

With DSP control:

```
#N canvas 100 100 600 400 12;
#X obj 50 50 loadbang;
#X msg 50 100 \; pd dsp 1;
#X text 50 150 Auto-start DSP;
#X connect 0 0 1 0;
```
