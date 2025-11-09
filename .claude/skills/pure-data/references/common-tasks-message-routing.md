# Message Handling

Quick reference for routing and filtering messages in Pure Data.

## Trigger Multiple Actions in Order

```
[r input]
|
[t f f f]  # or [trigger float float float]
```

**Execution order**: Right to left (rightmost outlet triggers first).

**Example**: Send to 3 destinations, ensuring right one processes before left:
```
[t f f f]
|   |   |
|   |   [third]
|   |
|   [second]
|
[first]
```

## Split Message by Threshold

```
[r value]
|
[moses 300]  # Split at 300
|         |
|         [< 300]
|
[>= 300]
```

**Chain for range checking**:
```
[moses 300]  # Lower bound
|
[moses 3001] # Upper bound
|         |
|         [> 3000]
|
[300-3000]  # Valid range
```

## Route by Symbol

```
[r message]
|
[route symbol1 symbol2 symbol3]
|       |       |
```

**Example**: OSC routing by address.

## Select Specific Value

```
[r value]
|
[sel 1]  # Only outputs bang if value is 1
|
[do-something]
```

**Multiple values**: `[sel 0 1 2]` has 4 outlets (0, 1, 2, else).

---

**Related documentation**:
- See common-tasks-testing-validation.md for debugging message flow with [print]
- See common-tasks-osc-networking.md for OSC-specific routing with [routeOSC]
