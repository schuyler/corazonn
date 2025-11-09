# Pure Data Message Construction

Reference for pack and unpack objects that combine and separate values into synchronized messages.

**See also**: [Message Variables and Dynamic Construction](pd-message-variables-and-dispatch.md)

## Message Construction and Unpacking

### pack - Combine Multiple Values into Lists

**Decision-Making Capability**: Aggregates multiple inputs into a single message for synchronized processing.

**Core Pattern**:
```pd
[pack float float float]
```

**How It Works**:
- Number of creation arguments sets number of inlets
- Stores values in inlets until leftmost inlet receives input
- Outputs complete list when triggered
- Hot inlet (left) triggers output, cold inlets (right) store values

**Use Cases**:
- Synchronizing multiple parameter changes
- Creating compound messages for complex objects
- Building lists with variable substitution ($1, $2, etc.)
- Coordinating timing of related values

**Example from 10.more.messages.pd**:
```pd
[floatatom]    [floatatom]    [floatatom]
     |              |              |
[pack float float float]
     |
[msg cis $1, boom $2, bah $3]
     |
[print]
```

**Raw .pd Implementation**:
```
#N canvas 0 0 400 350 12;
#X floatatom 50 50 5 0 0 0 - - - 0;
#X floatatom 120 50 5 0 0 0 - - - 0;
#X floatatom 190 50 5 0 0 0 - - - 0;
#X obj 100 90 pack float float float;
#X msg 100 130 cis $1, boom $2, bah $3;
#X obj 100 170 print;
#X connect 0 0 3 0;
#X connect 1 0 3 1;
#X connect 2 0 3 2;
#X connect 3 0 4 0;
#X connect 4 0 5 0;
```

### unpack - Split Lists into Individual Values

**Decision-Making Capability**: Distributes list elements across multiple processing paths.

**Core Pattern**:
```pd
[unpack float float]
```

**How It Works**:
- Outputs elements right-to-left (reverse order)
- Number of creation arguments determines number of outlets
- Can handle lists shorter than expected (unused outlets remain silent)

**Use Cases**:
- Separating coordinates (x, y pairs)
- Distributing parameters to different processors
- Breaking down compound messages for individual handling

**Example from 04.messages.pd**:
```pd
[msg 5 6]
     |
[unpack]
     |      |
[float] [float]
```

**Raw .pd Implementation**:
```
#N canvas 0 0 400 300 12;
#X msg 50 50 5 6;
#X obj 50 80 unpack;
#X floatatom 50 110 3 0 0 0 - - - 0;
#X floatatom 100 110 3 0 0 0 - - - 0;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
#X connect 1 1 3 0;
```
