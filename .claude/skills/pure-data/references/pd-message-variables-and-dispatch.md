# Pure Data Message Variables and Dynamic Construction

Reference for message box variables ($N), argument reordering, and message dispatch separators.

**See also**: [Message Construction](pd-message-construction.md)

## Message Variables and Dynamic Construction

### $1, $2, $N - Message Box Variables

**Decision-Making Capability**: Creates templates that adapt to incoming data, enabling context-dependent message generation.

**Core Pattern**:
```pd
[msg $2 $1 5]
```

**How It Works**:
- $1 refers to first element of incoming list
- $2 refers to second element, etc.
- Variables can be reordered, repeated, or mixed with constants
- Input number atoms are treated as single-element lists

**Use Cases**:
- Argument reordering (swap, reverse)
- Inserting constants alongside variable data
- Creating multiple related messages from single input
- Building OSC-style messages with variable parameters

**Example from 10.more.messages.pd**:
```pd
[msg 45 67]
     |
[msg $2 $1 5]
     |
[print]  # outputs: 67 45 5
```

**Raw .pd Implementation**:
```
#N canvas 0 0 400 300 12;
#X msg 50 50 45 67;
#X msg 50 90 $2 $1 5;
#X obj 50 130 print;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
```

### Semicolon and Comma Separators

**Decision-Making Capability**: Single trigger can dispatch multiple messages to different destinations.

**Semicolon (;)** - Separate destinations:
```pd
[msg 3 ; number9 5 ; 9bis 45]
```
Sends three messages to three different receivers.

**Comma (,)** - Same destination:
```pd
[msg 3, 4, 5]
```
Sends three sequential messages to the same outlet.

**Combined with Variables**:
```pd
[msg ; number9 $1 ; 9bis $2]
```
Routes variable data to multiple named receivers.

**Use Cases**:
- Updating multiple GUI elements from one action
- Broadcasting state changes to multiple subsystems
- Creating event chains without explicit connections
- Remote parameter updates via send/receive pairs
