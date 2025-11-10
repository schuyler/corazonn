# Phase 4 Implementation: Testing & Validation

## 4. Validation & Testing Procedures

Validate Phase 4 integration through progressively comprehensive tests.

### 4.1 Unit Test: OSC Message Format

Validate OSC messages match architecture specification.

**Test Procedure:**
1. Set DEBUG_LEVEL = 2 in code
2. Place finger on Sensor 0 (GPIO 32)
3. Capture serial output showing OSC sends
4. Use Wireshark or Python receiver to inspect packet format

**Expected OSC Message Format:**

```
Address pattern: /heartbeat/0
Type tag string: ,i
Arguments: [int32] IBI in milliseconds

Example binary (hex):
  2f 68 65 61 72 74 62 65 61 74 2f 30 00 00  // "/heartbeat/0\0\0"
  2c 69 00 00                                  // ",i\0\0" (type tag)
  00 00 03 58                                  // int32: 856 (0x358)
```

**Validation Checklist:**
- ✅ Address pattern format: `/heartbeat/[0-3]` (exact match)
- ✅ Type tag: `,i` (int32 argument)
- ✅ Argument value: 300-3000ms typical range (50-200 BPM)
- ✅ Packet size: ~24 bytes (efficient)
- ✅ No malformed messages

**Tools:**
```bash
# Python receiver validation
python3 osc_receiver.py --port 8000 --validate

# Wireshark capture (if available)
sudo tcpdump -i any port 8000 -w phase4_capture.pcap
```

**Expected Serial Output:**
```
OSC sent: /heartbeat/0 856
OSC sent: /heartbeat/0 869
OSC sent: /heartbeat/0 865
```

### 4.2 Integration Test: Single Sensor Beat Flow

Validate complete pipeline for one sensor end-to-end.

**Test Procedure:**
1. Upload Phase 4 firmware with DEBUG_LEVEL = 1
2. Start Python OSC receiver on port 8000
3. Place finger on Sensor 0 (GPIO 32)
4. Run for 2 minutes
5. Observe beat detection and OSC transmission

**Expected ESP32 Serial Output:**
```
=== Heartbeat Installation - Phase 4 ===
OSC Integration & Production Validation
Initialized sensor 0 on GPIO 32
Initialized sensor 1 on GPIO 33
Initialized sensor 2 on GPIO 34
Initialized sensor 3 on GPIO 35
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.1.42
Setup complete. Starting beat detection with OSC transmission...

[0] First beat at 3421ms (no message sent)
[0] Beat at 4287ms, IBI=866ms
[0] Beat at 5156ms, IBI=869ms
[0] Beat at 6021ms, IBI=865ms
```

**Expected Python Receiver Output:**
```
OSC Receiver listening on 0.0.0.0:8000
[/heartbeat/0] IBI: 866ms, BPM: 69.3
[/heartbeat/0] IBI: 869ms, BPM: 69.1
[/heartbeat/0] IBI: 865ms, BPM: 69.4
```

**Validation Checklist:**
- ✅ First beat detected but no OSC sent (correct behavior)
- ✅ Subsequent beats send OSC immediately
- ✅ IBI values match between serial and receiver
- ✅ BPM calculated by receiver is reasonable (50-100 typical range)
- ✅ LED flashes on each beat
- ✅ No missed beats (continuous detection)

### 4.3 Integration Test: Multi-Sensor Independence

Validate all 4 sensors work independently and concurrently without crosstalk.

**Test Procedure:**
1. Set DEBUG_LEVEL = 1
2. 4 people, each places finger on different sensor simultaneously
3. Run for 5 minutes continuous
4. Monitor Python receiver output
5. Verify message stream shows proper interleaving

**Expected Python Receiver Output:**
```
[/heartbeat/0] IBI: 856ms, BPM: 70.1
[/heartbeat/2] IBI: 742ms, BPM: 80.9
[/heartbeat/1] IBI: 923ms, BPM: 65.0
[/heartbeat/0] IBI: 861ms, BPM: 69.7
[/heartbeat/3] IBI: 678ms, BPM: 88.5
[/heartbeat/2] IBI: 739ms, BPM: 81.2
[/heartbeat/1] IBI: 920ms, BPM: 65.2
[/heartbeat/0] IBI: 859ms, BPM: 69.9
```

**Validation Checklist:**
- ✅ All 4 sensors send messages (indices 0, 1, 2, 3)
- ✅ Messages interleaved showing independent timing
- ✅ Each sensor's BPM stable (±5 BPM variation acceptable)
- ✅ No crosstalk (sensor 0 doesn't trigger sensor 1 messages)
- ✅ LED responds to beats from ANY sensor
- ✅ No packet loss (receiver sees all expected messages)

### 4.4 Latency Test: Beat to Network Timing

Measure time from beat detection to OSC transmission across network.

**Option A: Serial Timestamp Comparison**
```cpp
// In detectBeat(), add timing code:
#if DEBUG_LEVEL >= 2
    unsigned long beatTime = millis();
    sendHeartbeatOSC(sensorIndex, (int)ibi);
    unsigned long oscSentTime = millis();
    Serial.print("[");
    Serial.print(sensorIndex);
    Serial.print("] Latency: ");
    Serial.print(oscSentTime - beatTime);
    Serial.println("ms");
#endif
```

**Option B: Python Receiver Timestamp Validation**
```python
# In osc_receiver.py:
import time
def handle_heartbeat(address, *args):
    recv_time = time.time() * 1000  # Convert to milliseconds
    ibi = args[0] if args else 0
    # Can compare with ESP32 embedded timestamp if available
    print(f"Received {address}: {ibi}ms at {recv_time}")
```

**Validation Criteria:**
- ✅ 95th percentile latency <25ms
- ✅ Typical latency <10ms
- ✅ No outliers >50ms (would indicate WiFi congestion)

**Acceptable Latency Breakdown:**
- Beat detection: <1ms
- OSC message construction: <1ms
- UDP transmission: 1-5ms typical, up to 20ms worst case
- Network propagation: 1-5ms on local WiFi
- **Total: should stay under 25ms for 95% of beats**

### 4.5 Stress Test: Extended Duration Stability

Validate production readiness - no crashes, memory leaks, or WiFi issues during extended operation.

**Test Procedure:**
1. Set DEBUG_LEVEL = 0 (production mode)
2. 2-4 people on sensors simultaneously
3. Run for 60+ minutes continuous
4. Monitor Python receiver statistics
5. Check for any anomalies in message stream

**Validation Metrics:**

**Firmware Stability:**
- ✅ No ESP32 resets (check serial for startup banner)
- ✅ No WiFi disconnections (or successful auto-reconnects only)
- ✅ Consistent beat detection throughout (no degradation)
- ✅ LED continues responding to beats (not frozen)

**Network Stability:**
- ✅ Zero packet loss (receiver sees all expected messages)
- ✅ Message rate stable (no slowdowns or speedups)
- ✅ Latency consistent (no increasing trend over time)

**Server-Side Validation:**
```
Total messages received: 4,287
Invalid messages: 0
Average BPM per sensor:
  [0]: 68.4 BPM (63 messages)
  [1]: 74.2 BPM (74 messages)
  [2]: 71.8 BPM (68 messages)
  [3]: 82.5 BPM (82 messages)
Packet loss: 0.0%
Average latency: 12ms
Max latency: 23ms
```

**Failure Criteria (test failed if any occur):**
- Any ESP32 resets observed
- WiFi disconnection without automatic reconnection
- Packet loss >1%
- Invalid OSC messages detected
- Latency >50ms sustained

### 4.6 WiFi Resilience Test

Validate automatic reconnection under WiFi disruption.

**Test Procedure:**
1. Firmware running normally with beats being detected
2. Disable WiFi access point for 30 seconds
3. Re-enable access point
4. Monitor ESP32 reconnection behavior
5. Verify OSC transmission resumes

**Expected Behavior:**
```
[0] Beat at 45123ms, IBI=867ms
[1] Beat at 45298ms, IBI=742ms
WiFi disconnected, reconnecting...
[0] Beat at 46021ms, IBI=898ms  (beat detected but OSC not sent)
[1] Beat at 46089ms, IBI=791ms  (beat detected but OSC not sent)
WiFi reconnected! IP: 192.168.1.42
[0] Beat at 46932ms, IBI=911ms  (OSC sent successfully)
[1] Beat at 46887ms, IBI=798ms  (OSC sent successfully)
```

**Validation Checklist:**
- ✅ WiFi disconnection detected within 5 seconds
- ✅ Reconnection attempted automatically
- ✅ Sampling continues during disconnection (no beats missed)
- ✅ OSC transmission resumes immediately after reconnection
- ✅ LED shows connection status (blinks during reconnect)
- ✅ No ESP32 reset required for reconnection

### 4.7 BPM Accuracy Validation

Validate against smartphone heart rate app as reference.

**Test Procedure:**
1. Install smartphone heart rate app (e.g., "Instant Heart Rate" on iOS/Android)
2. Test subject simultaneously:
   - Left index finger on smartphone camera
   - Right index finger on ESP32 Sensor 0
3. Measure for 60 seconds
4. Compare BPM values from both sources

**Expected Results:**
```
Smartphone app: 72 BPM (stable reading after 30 seconds warmup)
ESP32 Sensor 0: 70 BPM (average over full 60 seconds)
Difference: 2 BPM (within ±5 BPM tolerance)
```

**Validation Criteria:**
- ✅ BPM difference ≤5 BPM from smartphone reference
- ✅ ESP32 readings stable (not jumping wildly)
- ✅ No missed beats causing artificially low BPM
- ✅ No false beats causing artificially high BPM

**Note:** Absolute accuracy is not critical for art installation. Relative beat-to-beat consistency is more important than absolute BPM match. ±5 BPM tolerance is acceptable.

---

## Test Execution Checklist

Complete these tests in order before declaring Phase 4 complete:

- [ ] 4.1 Unit Test: OSC Message Format ✅
- [ ] 4.2 Integration Test: Single Sensor ✅
- [ ] 4.3 Integration Test: Multi-Sensor ✅
- [ ] 4.4 Latency Test ✅
- [ ] 4.5 Stress Test (60 minutes) ✅
- [ ] 4.6 WiFi Resilience Test ✅
- [ ] 4.7 BPM Accuracy Test ✅

---

## Next Steps

After all validation tests pass, proceed to [Operations](./operations.md) for:
- Production configuration
- Acceptance criteria
- Troubleshooting procedures
- Deployment checklist
