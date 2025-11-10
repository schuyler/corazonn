# Messaging API

## OSC Message Transmission (Phase 1)

The OSC transmission function from Phase 1 is reused in Phase 2 with the same implementation. The key difference is that Phase 2 sends real IBI values instead of test values.

### sendHeartbeatOSC()

**Signature:**
```cpp
void sendHeartbeatOSC(int ibi_ms);
```

**Purpose:** Construct and transmit OSC message with heartbeat interval-between-beats (IBI) data

**Source:** `phase1-firmware-trd.md` Section 6.2

**Parameters:**
- `ibi_ms`: Inter-beat interval in milliseconds (real heartbeat data in Phase 2)

**Return:** None

**Key behavior:**
- Constructs OSC message with address pattern `/heartbeat/{SENSOR_ID}`
- Includes IBI value in message
- Transmits via UDP to `SERVER_IP:SERVER_PORT`
- Uses WiFiUDP socket `udp` created in setup()

**Implementation Details:**

```cpp
void sendHeartbeatOSC(int ibi_ms) {
    if (!state.wifiConnected) return;

    OSCMessage msg("/heartbeat/");
    msg.add(SENSOR_ID);
    msg.add(ibi_ms);

    udp.beginPacket(SERVER_IP, SERVER_PORT);
    msg.send(udp);
    udp.endPacket();
}
```

**Requirements:**
- MUST check `state.wifiConnected` before transmission
- MUST use `OSCMessage` from CNMAT OSC library
- MUST include `SENSOR_ID` in address pattern or message body
- MUST include IBI value in milliseconds
- MUST use UDP socket for transmission

### Message Format (Phase 2)

**OSC Address:** `/heartbeat/0` (for SENSOR_ID=0)

**Message Contents:**
- IBI value in milliseconds (unsigned long cast to int)
- Example: 847 (representing 847ms between beats = ~70 BPM)

**Expected Python Receiver Output:**
```
[/heartbeat/0] IBI: 847ms, BPM: 70.8
```

### Phase 2 Changes

**Phase 1 (test values):**
```cpp
sendHeartbeatOSC(1000);  // Always 1000ms (fixed test value)
```

**Phase 2 (real data):**
```cpp
unsigned long ibi = millis() - sensor.lastBeatTime;
sendHeartbeatOSC((int)ibi);  // Real inter-beat interval
```

### Usage in Beat Detection

**Called from `detectBeat()` on valid beat:**
```cpp
// Calculate IBI from actual heartbeat timing
unsigned long ibi = millis() - sensor.lastBeatTime;
sensor.lastBeatTime = millis();
sensor.lastIBI = ibi;

// Transmit real IBI to receiver
sendHeartbeatOSC((int)ibi);
```

### Notes

- **No implementation changes from Phase 1** - Function signature and behavior identical
- **Data difference** - Phase 2 sends real IBI values from heartbeat detection algorithm
- Message validation and receiver format remain unchanged
- All 4 ESP32 units can transmit simultaneously (differentiated by SENSOR_ID)

---

## Related Documentation

- **[Network API](api-network.md)** - WiFi connection foundation
- **[Beat Detection API](api-beat-detection.md)** - Where OSC transmission is triggered
- **[Configuration](configuration.md)** - Network configuration for UDP transmission
- **[Implementation](implementation.md)** - Integration in main program flow

---

## Message Delivery

OSC messages are sent asynchronously when beats are detected:
- No guaranteed ordering (UDP is connectionless)
- No acknowledgment (fire-and-forget)
- Receiver should validate message format
- Typical throughput: 60-120 messages per minute (BPM dependent)
