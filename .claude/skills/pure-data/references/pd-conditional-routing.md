# Pure Data Conditional Routing Objects

Reference for select, route, spigot, and moses objects that control message flow based on conditions.

**See also**: [Message Construction](pd-message-construction.md) | [Random Numbers](pd-random-numbers.md) | [Routing Patterns](pd-routing-patterns.md)

## Conditional Routing Objects

### select - Pattern Matching with Bang Output

**Decision-Making Capability**: Tests input against expected values and triggers specific actions on match.

**Core Pattern**:
```pd
[select 1 2]
```

**How It Works**:
- Compares incoming number to creation arguments
- Outputs bang from matching outlet
- Rightmost outlet catches non-matches
- Can test against multiple values simultaneously

**Use Cases**:
- State machine transitions
- MIDI note filtering
- Menu/button selection handling
- Event detection (specific values trigger actions)

**Example from 18.conditional.pd**:
```pd
[floatatom]
     |
[select 1 2]
     |      |      |
[print-1] [print-2] [print-3]
```
Input 1 → left outlet (bang)
Input 2 → middle outlet (bang)
Other → right outlet (bang)

**Raw .pd Implementation**:
```
#N canvas 0 0 400 350 12;
#X floatatom 50 50 0 0 0 0 - - - 0;
#X obj 50 90 select 1 2;
#X obj 50 130 print select-1;
#X obj 120 130 print select-2;
#X obj 190 130 print select-3;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X connect 1 1 3 0;
#X connect 1 2 4 0;
```

### route - Pattern Matching with Data Forwarding

**Decision-Making Capability**: Examines first element of list and conditionally passes remaining data to appropriate outlet.

**Core Pattern**:
```pd
[route 1 2]
```

**How It Works**:
- Tests first element of incoming list
- Strips matched element and outputs remainder
- Preserves data (unlike select which outputs bangs)
- Multiple outlets for different routing paths

**Use Cases**:
- OSC message demultiplexing
- MIDI channel separation
- Command parsing (strip prefix, route payload)
- List processing pipelines

**Example from 18.conditional.pd**:
```pd
[floatatom]    [floatatom]
     |              |
     |         [t b f]
     |          |   |
[pack float float]
          |
     [route 1 2]
     |      |      |
[float] [float] [unpack]
```
If first element matches 1 or 2, second element goes to that outlet.
Non-matching lists go to rightmost outlet intact.

**Raw .pd Implementation**:
```
#N canvas 0 0 400 350 12;
#X floatatom 50 50 0 0 0 0 - - - 0;
#X floatatom 120 50 0 0 0 0 - - - 0;
#X obj 100 90 t b f;
#X obj 80 130 pack float float;
#X obj 100 180 route 1 2;
#X floatatom 100 220 0 0 0 0 - - - 0;
#X floatatom 150 220 0 0 0 0 - - - 0;
#X obj 200 220 unpack;
#X connect 0 0 2 0;
#X connect 1 0 3 1;
#X connect 2 0 3 0;
#X connect 2 1 3 1;
#X connect 3 0 4 0;
#X connect 4 0 5 0;
#X connect 4 1 6 0;
#X connect 4 2 7 0;
```

**Key Difference from select**:
- select: outputs bang, discards data
- route: outputs data (minus selector), preserves information

### spigot - Gate/Conditional Pass-Through

**Decision-Making Capability**: Controls message flow with on/off switch, enabling conditional execution paths.

**Core Pattern**:
```pd
[spigot]
```

**How It Works**:
- Left inlet: data input
- Right inlet: gate control (nonzero = open, zero = closed)
- When open, messages pass through unchanged
- When closed, messages are blocked

**Use Cases**:
- Enabling/disabling audio processing chains
- Gating sensor input based on state
- Mute/unmute functionality
- Conditional parameter updates (only when active)

**Example from 18.conditional.pd**:
```pd
[floatatom]    [toggle]
     |              |
  [spigot]-----------+
     |
[floatatom]
```
Toggle on: data flows through
Toggle off: data blocked

**Raw .pd Implementation**:
```
#N canvas 0 0 400 300 12;
#X floatatom 50 50 0 0 0 0 - - - 0;
#X obj 80 50 tgl 19 0 empty empty empty 17 7 0 10 #dfdfdf #000000 #000000 0 1;
#X obj 50 100 spigot;
#X floatatom 50 150 0 0 0 0 - - - 0;
#X connect 0 0 2 0;
#X connect 1 0 2 1;
#X connect 2 0 3 0;
```

**Note**: Inputs are reversed compared to Max's gate object (data left, control right).

### moses - Numeric Threshold Routing

**Decision-Making Capability**: Routes numbers based on threshold comparison, enabling range-based decisions.

**Core Pattern**:
```pd
[moses 5]
```

**How It Works**:
- Compares input to creation argument (threshold)
- Left outlet: values less than threshold
- Right outlet: values greater than or equal to threshold
- Threshold can be set dynamically via right inlet

**Use Cases**:
- Range splitting (low/high values)
- Velocity-sensitive MIDI processing
- Sensor calibration and scaling
- Boundary detection in continuous data

**Example from 18.conditional.pd**:
```pd
[floatatom]
     |
[moses 5]
     |      |
[float] [float]
```
Input < 5 → left outlet
Input ≥ 5 → right outlet

**Raw .pd Implementation**:
```
#N canvas 0 0 400 300 12;
#X floatatom 50 50 0 0 0 0 - - - 0;
#X obj 50 100 moses 5;
#X floatatom 50 150 0 0 0 0 - - - 0;
#X floatatom 120 150 0 0 0 0 - - - 0;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X connect 1 1 3 0;
```

**Dynamic Threshold**:
```pd
[floatatom]    [floatatom]
     |              |
  [moses]-----------+
     |      |
```
Right inlet updates threshold value.

**Raw .pd Implementation (Dynamic)**:
```
#N canvas 0 0 400 300 12;
#X floatatom 50 50 0 0 0 0 - - - 0;
#X floatatom 120 50 0 0 0 0 - - - 0;
#X obj 50 100 moses;
#X floatatom 50 150 0 0 0 0 - - - 0;
#X floatatom 120 150 0 0 0 0 - - - 0;
#X connect 0 0 2 0;
#X connect 1 0 2 1;
#X connect 2 0 3 0;
#X connect 2 1 4 0;
```
