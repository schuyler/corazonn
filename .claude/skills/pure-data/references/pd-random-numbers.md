# Pure Data Random Number Generation

Reference for random object, continuous random values, and seeding for repeatable sequences.

**See also**: [Conditional Routing](pd-conditional-routing.md) | [Routing Patterns](pd-routing-patterns.md)

## Random Number Generation

### random - Pseudo-Random Integer Generation

**Decision-Making Capability**: Introduces non-deterministic behavior for variation and unpredictability.

**Core Pattern**:
```pd
[random 5]
```

**How It Works**:
- Outputs integer from 0 to (N-1)
- [random 5] outputs 0, 1, 2, 3, or 4
- Each bang triggers new value
- Sequence is deterministic unless seeded

**Use Cases**:
- Algorithmic composition (random note selection)
- Generative patterns
- Parameter variation
- Probabilistic decision making

**Example from 19.random.pd**:
```pd
[bang]
  |
[random 5]
  |
[floatatom]  # 0 to 4
```

**Raw .pd Implementation**:
```
#N canvas 0 0 400 300 12;
#X obj 50 50 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X obj 50 90 random 5;
#X floatatom 50 130 0 0 0 0 - - - 0;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
```

### Continuous Random Values (0.0 to 0.999)

**Pattern**:
```pd
[random 1000]
     |
[/ 1000]
     |
[floatatom]
```

**Raw .pd Implementation**:
```
#N canvas 0 0 400 300 12;
#X obj 50 50 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X obj 50 90 random 1000;
#X obj 50 130 / 1000;
#X floatatom 50 170 0 0 0 0 - - - 0;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X connect 2 0 3 0;
```

**How It Works**:
- Generate large integer range
- Divide to normalize to [0, 1) range
- Higher random range = finer resolution

**Use Cases**:
- Random amplitudes (0.0 to 1.0)
- Probabilistic gates (compare to threshold)
- Smooth parameter variation

### Seeding for Repeatable Sequences

**Decision-Making Capability**: Controls whether randomness is repeatable or varies each run.

**Pattern**:
```pd
[loadbang]    [bang]
     |          |
  [timer]-------+
     |
[msg seed $1]
     |
  [random 5]
```

**Raw .pd Implementation**:
```
#N canvas 0 0 400 350 12;
#X obj 50 50 loadbang;
#X obj 50 90 timer;
#X obj 120 90 bng 19 250 50 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000;
#X msg 50 130 seed $1;
#X obj 50 170 random 5;
#X floatatom 50 210 0 0 0 0 - - - 0;
#X connect 0 0 1 0;
#X connect 1 0 3 0;
#X connect 2 0 1 1;
#X connect 3 0 4 0;
#X connect 4 0 5 0;
```

**How It Works**:
- [loadbang] triggers at patch load
- [timer] measures time until user interaction
- Time value used as seed
- Same seed = same sequence

**Use Cases**:
- **Unseeded (time-based)**: Live performances, interactive installations
- **Fixed seed**: Testing, reproducible compositions, debugging

**Unseeded Behavior** (from 19.random.pd):
> If you give two randoms the same seed they give the same sequence. If you never seed them, you'll get different sequences out of each one.
