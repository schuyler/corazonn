# Pure Data Networking Guide

Practical examples, setup patterns, and debugging for FUDI and OSC communication.

For protocol specifications, see [pd-fudi-protocol.md](pd-fudi-protocol.md) and [pd-osc-protocol.md](pd-osc-protocol.md).

For object reference, see [pd-network-objects-reference.md](pd-network-objects-reference.md).

## Practical Considerations

### Choosing TCP vs UDP

#### TCP (Transmission Control Protocol)
- Reliable delivery
- Guaranteed order
- Connection-oriented
- Higher latency
- Better for: Control messages, state synchronization

#### UDP (User Datagram Protocol)
- Unreliable delivery (packets may be lost)
- No guaranteed order
- Connectionless
- Lower latency
- Better for: Real-time audio, continuous control streams, OSC

### Port Numbers
- Avoid ports < 1024 (system/privileged)
- Common OSC port: 8000-8100 range
- Common Pd FUDI: 3000-4000 range
- Check firewall settings

### Message Size
- UDP packets: Typically limited to 1472 bytes (safe size)
- TCP: No practical limit (stream-based)
- OSC bundles can exceed UDP limits

### Localhost vs Network
- Localhost (127.0.0.1): Same machine only
- Network IP: Accessible from other machines
- 0.0.0.0: Listen on all interfaces

### Error Handling
- Network errors appear in Pd console
- `netsend`: Check connection status outlet
- `netreceive`: Monitor for unexpected disconnections
- UDP: No delivery confirmation (send and forget)

### Performance
- Don't send audio samples over control networks
- Use for control data, parameters, events
- For audio: Use audio interfaces, not network (unless specialized)
- Batch updates when possible to reduce packet overhead

## Example Setups

### Simple FUDI Communication (TCP)

**Sender patch (.pd format):**
```pd
#N canvas 440 155 400 300 12;
#X msg 440 155 connect localhost 3000;
#X msg 494 271 1 2 3 4;
#X obj 440 325 netsend;
#X obj 440 355 tgl 19 0 empty empty empty 0 -10 0 12 #dfdfdf #000000 #000000 0 1;
#X floatatom 440 392 2 0 0 0 - - - 0;
#X msg 456 189 disconnect;
#X connect 0 0 2 0;
#X connect 1 0 2 0;
#X connect 2 0 3 0;
#X connect 2 1 4 0;
#X connect 5 0 2 0;
```

**Receiver patch (.pd format):**
```pd
#N canvas 649 308 400 300 12;
#X obj 649 308 netreceive -f 3000;
#X obj 649 363 print TCP-FUDI;
#X obj 829 310 print Address/Port;
#X msg 649 183 listen 3000;
#X connect 3 0 0 0;
#X connect 0 0 1 0;
#X connect 0 1 2 0;
```

Notes:
- `connect localhost 3000` - establishes TCP connection to receiver on port 3000
- Outlet 1: receives incoming messages
- Outlet 2 (with `-f` flag): address and port info

### UDP FUDI Communication

**Sender (UDP):**
```pd
#X msg 670 432 connect localhost 3001;
#X msg 705 515 send bar $1;
#X obj 670 546 netsend -u;
#X floatatom 705 491 4 0 0 0 - - - 0;
#X connect 0 0 2 0;
#X connect 1 0 2 0;
```

**Receiver (UDP):**
```pd
#X obj 491 538 netreceive -u 3001;
#X obj 491 566 print UDP-FUDI;
#X connect 0 0 1 0;
```

Notes:
- UDP is connectionless (`-u` flag)
- No send-back in UDP mode from receiver
- Lower latency, unreliable delivery

### OSC Communication (UDP Binary Mode)

**Sender (OSC over UDP):**
```pd
#X msg 442 150 disconnect;
#X msg 79 143 disconnect;
#X obj 417 277 netsend -u -b;
#X obj 63 273 netsend -b;
#X msg 417 108 connect localhost 3004;
#X msg 63 101 connect localhost 3003;
#X msg 75 378 1 2 3 4;
#X connect 0 0 3 0;
#X connect 1 0 2 0;
#X connect 6 0 2 0;
```

**Receiver (OSC):**
```pd
#X obj 406 389 netreceive -u -b -f 3004;
#X obj 75 414 netreceive -b 3003;
#X obj 505 316 print backwards;
#X connect 1 0 2 0;
```

Notes:
- Binary mode (`-b` flag) used for OSC packets
- Can work with `oscformat` and `oscparse` objects
- UDP for OSC is typical pattern

### IPv6 and Multicast (UDP)

**Sending to IPv6 address:**
```pd
#X msg 255 298 connect 239.200.200.200 3005;
#X msg 275 330 connect ff00::114 3005;
#X obj 195 446 netsend -u;
```

**Receiving on multicast:**
```pd
#X obj 593 381 netreceive -u -f 3005;
#X msg 646 277 listen 3005 239.200.200.200;
#X msg 666 308 listen 3005 ff00::114;
```

Notes:
- IPv4 multicast: `239.200.200.200`
- IPv6 multicast: `ff00::114`
- Specify interface/address in second argument

### Bidirectional UDP Communication

**Sender with response listening:**
```pd
#X msg 27 62 connect localhost 3006 3007;
#X obj 27 198 netsend -u -b;
#X msg 65 152 1 2 3;
#X listbox 115 235 10 0 0 0 - - - 0;
#X connect 0 0 1 0;
#X connect 2 0 1 0;
#X connect 1 1 3 0;
```

**Receiver sending back:**
```pd
#X obj 294 247 netsend -u -b;
#X msg 294 122 connect localhost 3007;
#X msg 325 208 1 2 3;
#X connect 1 0 0 0;
#X connect 2 0 0 0;
```

Notes:
- `connect localhost 3006 3007` - second port for receiving responses
- Requires separate `netsend` object on receiver side to send back
- Listbox outlet receives responses

### Remote Pd Control
Send message to remote Pd instance:
```pd
[; pd dsp 1(  (local)

vs

[connect remote-ip 9001(
|
[netsend]
|
[; pd dsp 1(  (remote, via network)
```

## Security Considerations
- Network ports are exposed to local network
- No authentication in basic Pd networking
- No encryption in FUDI or native OSC
- Use firewall to restrict access
- Consider VPN for internet communication
- Localhost communication is safe (127.0.0.1)

## Debugging

### Testing Connections
- Use `netcat` or `telnet` to test ports
- Check Pd console for error messages
- Verify firewall isn't blocking
- Use `print` objects to see data flow

### Common Issues
- Port already in use
- Firewall blocking
- Wrong IP address
- Protocol mismatch (TCP vs UDP)
- Message formatting errors
- Semicolon missing in FUDI messages

### Troubleshooting Tools
- `pdsend`: Test sending to Pd
- `nc` (netcat): Generic network testing
- `tcpdump`/`wireshark`: Packet inspection
- Pd console: Error messages and status
