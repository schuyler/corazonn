# API: OSC Message Transmission

OSC message construction and transmission over UDP.

---

## 6.5 OSC Message Transmission

**Function:** `sendHeartbeatOSC()`

**Signature:**
```cpp
void sendHeartbeatOSC(int sensorIndex, int ibi_ms);
```

**Purpose:** Construct and send OSC heartbeat message with inter-beat interval

**Parameters:**
- `sensorIndex`: Sensor ID 0-3
- `ibi_ms`: Inter-beat interval in milliseconds

**Message Format:**

| Field | Value | Example |
|---|---|---|
| OSC Address | `/heartbeat/N` (N=0-3) | `/heartbeat/0` |
| Data Type | int32 | `856` |
| Data Value | IBI in milliseconds | Inter-beat time |

**Requirements:**

**R20: Address Pattern**
```cpp
char oscAddress[20];
snprintf(oscAddress, sizeof(oscAddress), "/heartbeat/%d", sensorIndex);
```
- Format: `/heartbeat/N` where N = 0-3
- Buffer size 20 bytes sufficient
- Example: `/heartbeat/0`, `/heartbeat/2`, etc.

**R21: OSC Message Construction**
```cpp
OSCMessage msg(oscAddress);
msg.add((int32_t)ibi_ms);
```
- Create message with address pattern
- Add single int32 argument (IBI value)
- MUST cast to int32_t for correct OSC type
- Integer type ensures no precision loss

**R22: UDP Transmission**
```cpp
udp.beginPacket(SERVER_IP, SERVER_PORT);
msg.send(udp);
udp.endPacket();
msg.empty();
```
- MUST follow sequence: beginPacket → send → endPacket → empty
- `msg.empty()` clears message for reuse
- Fire-and-forget (no acknowledgment expected)
- Non-blocking operation

**R23: Debug Output**
```cpp
#if DEBUG_LEVEL >= 2
  Serial.print("Sent OSC: ");
  Serial.print(oscAddress);
  Serial.print(" ");
  Serial.println(ibi_ms);
#endif
```
- Level 2 debug: Confirm OSC transmission
- Production (Level 0): No output

**Same as Phase 1, but now with real sensor IBI values instead of test values**

---

## Message Flow

```
detectBeat() [sensor N]
  ↓
  Calculate IBI = now - lastBeatTime
  ↓
  sendHeartbeatOSC(N, ibi)
    ↓
    Create OSC message: /heartbeat/N <ibi_ms>
    ↓
    Send via UDP to SERVER_IP:SERVER_PORT
    ↓
    Clear message for reuse
```

---

## Example Messages

**Single Sensor:**
```
/heartbeat/0 856    (Sensor 0, 856ms between beats = ~70 BPM)
/heartbeat/0 869    (Sensor 0, 869ms = ~69 BPM)
/heartbeat/0 865    (Sensor 0, 865ms = ~69 BPM)
```

**Multiple Sensors Interleaved:**
```
/heartbeat/0 856
/heartbeat/2 742
/heartbeat/1 923
/heartbeat/0 861
/heartbeat/3 678
/heartbeat/2 739
```

---

## OSC Reception (Python Example)

Python receiver validates message format:
```python
def osc_handler(address, *args):
    if address.startswith('/heartbeat/'):
        sensor_id = int(address.split('/')[-1])
        ibi = args[0]
        bpm = 60000 / ibi
        print(f"[{address}] IBI: {ibi}ms, BPM: {bpm:.1f}")
```

**Expected Output:**
```
[/heartbeat/0] IBI: 856ms, BPM: 70.1
[/heartbeat/0] IBI: 869ms, BPM: 69.0
[/heartbeat/0] IBI: 865ms, BPM: 69.3
```

---

## Transmission Characteristics

**Rate Limiting:**
- Refractory period: 300ms minimum between beats per sensor
- Maximum rate: 200 messages/min per sensor
- 4 sensors: Max 800 messages/min total system

**Latency:**
- Target: <25ms from beat detection to network transmission
- Typical: 10-15ms (mostly from OSC library)

**Reliability:**
- UDP fire-and-forget (no retransmission)
- Network conditions may cause occasional loss
- Receiver should tolerate <1% packet loss

**Payload Size:**
- OSC packet: ~20 bytes
- Bandwidth: 800 msg/min × 20 bytes = ~267 bytes/sec
- Negligible WiFi impact (1Mbps = 125 KB/sec)

---

## Configuration for Different Servers

**Change in main.cpp:**
```cpp
const IPAddress SERVER_IP(192, 168, 1, 100);  // Your server IP
const uint16_t SERVER_PORT = 8000;             // Your OSC port
```

**Common Configurations:**
- Local network: `192.168.x.x`, Port 8000-9000
- Localhost: `127.0.0.1`, Port 8000 (USB/Serial only)
- Remote: Public IP, Port forwarding required

---

## Testing Reception

**Python receiver test:**
```bash
python3 osc_receiver.py --port 8000
```

**Expected output when sensor beats:**
```
[/heartbeat/0] IBI: 856ms, BPM: 70.1
[/heartbeat/0] IBI: 869ms, BPM: 69.0
```

**Troubleshooting:**
- No messages: Check SERVER_IP and SERVER_PORT match receiver
- Messages but wrong format: Check OSC library installation
- Intermittent loss: Check WiFi signal and interference

---

## Related Documentation

- [Configuration](configuration.md) — Network constants (SERVER_IP, SERVER_PORT)
- [API: Beat Detection](api-beat-detection.md) — Calls this function
- [Implementation](implementation.md) — WiFi setup for UDP
- [Operations](operations.md) — Testing and validation procedures

---

**Next Step:** Implement LED feedback with [API: Status](api-status.md)
