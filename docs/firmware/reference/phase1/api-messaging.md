# Phase 1 Firmware - Messaging API

[**Back to Index**](index.md)

**Version:** 3.0 | **Date:** 2025-11-09

Function for constructing and transmitting OSC heartbeat messages.

---

## 6.2 OSC Message Construction

**Function:** `sendHeartbeatOSC()`

**Signature:**
```cpp
void sendHeartbeatOSC(int ibi_ms);
```

**Purpose:** Construct and send OSC heartbeat message

**Parameters:**
- `ibi_ms`: Inter-beat interval in milliseconds (300-3000 valid range)

**Requirements:**

**R5: Address Pattern Construction**
- MUST construct address string: `/heartbeat/[SENSOR_ID]`
- Format using `snprintf()` with buffer size 20 bytes minimum
- Example: SENSOR_ID=0 → "/heartbeat/0"

**R6: OSC Message Construction**
- MUST create OSCMessage object with address pattern
- MUST add single int32 argument: `ibi_ms`
- MUST use `msg.add((int32_t)ibi_ms)` for correct type

**R7: UDP Transmission**
- MUST call `udp.beginPacket(SERVER_IP, SERVER_PORT)`
- MUST call `msg.send(udp)` to write OSC data to packet
- MUST call `udp.endPacket()` to transmit packet
- MUST call `msg.empty()` AFTER `udp.endPacket()` to clear message buffer
- Calling sequence is critical: beginPacket → send → endPacket → empty
- msg.empty() prepares message object for reuse in next transmission

**R8: No Error Checking**
- Fire-and-forget transmission (UDP nature)
- No return value needed
- No acknowledgment expected
- Packet may be lost - this is acceptable UDP behavior

**Pseudocode:**
```
function sendHeartbeatOSC(ibi_ms):
    address = format("/heartbeat/%d", SENSOR_ID)
    msg = new OSCMessage(address)
    msg.add_int32(ibi_ms)

    udp.beginPacket(SERVER_IP, SERVER_PORT)
    msg.send(udp)
    udp.endPacket()

    msg.empty()
```

**Implementation Notes:**

**Address Pattern Format:**

The address pattern follows OSC convention: `/heartbeat/0`, `/heartbeat/1`, etc. Use `snprintf()` for safe string formatting. Allocate a char buffer of at least 20 bytes:

```cpp
char address[20];
snprintf(address, sizeof(address), "/heartbeat/%d", SENSOR_ID);
OSCMessage msg(address);
```

**Message Argument:**

The single int32 argument represents the inter-beat interval in milliseconds. The OSC library requires explicit type casting with `(int32_t)` to ensure the correct data type is transmitted.

**UDP Packet Sequence:**

The sequence `beginPacket → send → endPacket → empty` is essential:
1. `beginPacket()` initializes a new UDP packet to the target IP and port
2. `msg.send()` serializes the OSC message into the packet buffer
3. `endPacket()` transmits the packet over the network
4. `msg.empty()` resets the message object's internal buffer, preparing it for reuse

Failing to call `msg.empty()` after `endPacket()` can cause buffer state issues in subsequent transmissions.

**Fire-and-Forget Design:**

This function does not check for transmission success or network errors. UDP is a best-effort protocol—packets may be lost, duplicated, or reordered. The testing infrastructure validates message reception separately.

---

**Example Message Sequence:**

Calling `sendHeartbeatOSC(800)` with SENSOR_ID=0 transmits:
- Address: `/heartbeat/0`
- Argument type: int32
- Argument value: 800
- Total message size: 24 bytes (typical OSC overhead)

---

**Related sections:**
- See [configuration.md](configuration.md) for SENSOR_ID and SERVER_IP settings
- See [implementation.md](implementation.md) for how to call this in the loop() function
- See [operations.md](operations.md) for message validation in testing
