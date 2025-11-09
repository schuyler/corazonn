# Pure Data Routing Patterns and Principles

Reference for compound routing patterns, decision-making capabilities summary, and key design principles.

**See also**: [Message Construction](pd-message-construction.md) | [Message Variables and Dynamic Construction](pd-message-variables-and-dispatch.md) | [Conditional Routing](pd-conditional-routing.md) | [Random Numbers](pd-random-numbers.md)

## Compound Routing Patterns

### State Machine with select

```pd
[floatatom]
     |
[select 0 1 2]
     |      |      |
[msg state-idle] [msg state-active] [msg state-error]
```

### Multi-Path Data Router

```pd
[pack float float]
     |
[route 1 2 3]
     |      |      |      |
[process-a] [process-b] [process-c] [default]
```

### Gated Random Source

```pd
[metro 100]    [toggle]
     |              |
  [spigot]-----------+
     |
  [random 12]
     |
  [+ 60]  # MIDI notes 60-71
```

### Threshold-Based Range Mapper

```pd
[floatatom]
     |
[moses 50]
     |              |
[* 0.5]        [* 2]  # scale low/high differently
     |              |
```

### Probabilistic Gate

```pd
[bang]
  |
[random 100]
  |
[/ 100]
  |
[moses 0.3]  # 30% probability
  |      |
[bang] [bang]
(yes)  (no)
```

## Summary of Decision-Making Capabilities

| Object | Input | Output | Decision Type |
|--------|-------|--------|---------------|
| select | value | bang | Exact match |
| route | list | data subset | First element match |
| spigot | value + gate | value or nothing | Binary gate |
| moses | number | left or right | Threshold comparison |
| random | bang | random int | Non-deterministic |
| pack | multiple values | list | Synchronization |
| unpack | list | multiple values | Distribution |

## Key Principles

1. **Right-to-Left Evaluation**: Unpack and multi-outlet objects output right-to-left to maintain correct ordering for downstream processing.

2. **Hot vs. Cold Inlets**: Leftmost inlet triggers computation, others store values. Critical for pack and conditional objects.

3. **Data vs. Trigger**: select outputs bangs (triggers), route outputs data. Choose based on whether downstream needs the value or just notification.

4. **Determinism**: Pure Data is deterministic unless you introduce randomness via [random] or external input. Use seeding to control repeatability.

5. **Message Dispatch**: Semicolons and commas enable complex routing without explicit patch cords, essential for dynamic parameter control.
