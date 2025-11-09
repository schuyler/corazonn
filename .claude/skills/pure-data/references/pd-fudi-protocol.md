# FUDI Protocol Reference

For practical networking examples and debugging, see [pd-networking-guide.md](pd-networking-guide.md).

## FUDI Protocol

**FUDI** = "Fast Unified Digital Interface" (or any acronym you can devise)

### Overview
- Networking protocol used internally by Pd
- Communication between GUI process and DSP process
- Used for saving patches to Pd files
- Packet-oriented protocol

### Format

#### Message Structure
- One or more **atoms** separated by **whitespace**
- Terminated by **semicolon** character
- Atom: sequence of one or more characters
- Whitespace in atoms can be escaped with backslash (ascii 92)

#### Whitespace
Can be any of:
- Space (ascii 32)
- Tab (ascii 9)
- Newline (ascii 10)

#### Termination
- **Semicolon** (ascii 59) is mandatory to terminate and send message
- **Newline** treated as whitespace (not needed for termination)

### Example Messages

```
test/blah 123.45314;
```

```
my-slider 12;
```

```
hello this is a message;
```

```
this message continues
in the following
line;
```

Multiple messages in one line:
```
you; can; send; multiple messages; in a line;
```

One atom with spaces:
```
this\ is\ one\ whole\ atom;
```

Atom with newline character:
```
this_atom_contains_a\
newline_character_in_it;
```

### Pd Objects for FUDI

#### netsend / netreceive
- Transport Pd messages over TCP or UDP socket
- Both support FUDI protocol

#### fudiformat / fudiparse
- Convert between Pd messages and FUDI packets
- `fudiformat`: Pd messages → FUDI packets
- `fudiparse`: FUDI packets → Pd messages

### Using FUDI from Other Tools

#### pdsend Command-Line Tool
Usage: `pdsend <portnumber> [host] [udp|tcp]`
- Default: localhost and tcp

Example:
```bash
echo "list foo bar;" | pdsend 8888
```

#### Tcl
Create socket and write data:
```tcl
set sock [socket localhost 8888]
puts $sock "test/blah 123.45314;"
```

Without newline (requires flush):
```tcl
set sock [socket localhost 8888]
puts -nonewline $sock "test/blah 123.45314;"
flush $sock
```

#### netcat (nc)
Command-line networking tool:
```bash
echo "blah;" | nc localhost 8888
```
