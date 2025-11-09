# Network Objects Quick Reference

For protocol specifications, see [pd-fudi-protocol.md](pd-fudi-protocol.md) and [pd-osc-protocol.md](pd-osc-protocol.md).

For practical examples and debugging, see [pd-networking-guide.md](pd-networking-guide.md).

## Network Objects

### netsend
Send messages over network
- Arguments: Protocol type (tcp/udp)
- Messages:
  - `connect <host> <port>`: Establish connection
  - `disconnect`: Close connection
  - `send <data>`: Send data (implicit)
- Outlets: Connection status

### netreceive
Receive messages from network
- Arguments: Port number, protocol type (tcp/udp)
- Automatically listens on specified port
- Outlets: Received data, connection info

### oscformat
Format OSC packets
- Input: Pd list (address pattern and arguments)
- Output: Binary OSC packet
- Example input: `/test/freq 440`

### oscparse
Parse OSC packets
- Input: Binary OSC packet
- Output: Pd list (address pattern and arguments)
- Handles OSC type tags automatically
