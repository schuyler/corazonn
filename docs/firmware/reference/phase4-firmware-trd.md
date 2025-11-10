# Heartbeat Firmware - Phase 4 Firmware Implementation TRD
## OSC Integration & Production Validation

**Version:** 1.0
**Date:** 2025-11-09
**Purpose:** Integrate Phase 3 beat detection with Phase 1 OSC infrastructure for complete data pipeline
**Audience:** Coding agent implementing ESP32 firmware
**Hardware:** ESP32-WROOM-32 + 4 optical pulse sensors on GPIO 32-35
**Framework:** Arduino (via PlatformIO CLI)
**Toolchain:** PlatformIO CLI

**⚠️ CRITICAL: PREREQUISITES**
```
Step 1: Complete Phase 1 (WiFi + OSC with test values)
Step 2: Complete Phase 3 (Multi-sensor beat detection algorithm)
Step 3: Validate both independently working
Step 4: Implement Phase 4 (integrate real beats → OSC)
Step 5: End-to-end validation with audio server
```

Phase 1 OSC infrastructure AND Phase 3 beat detection MUST be validated before integration.

**Estimated Implementation Time:** 3-4 hours (integration) + 3-4 hours (validation)

---

## 0. Prerequisites

### 0.1 Phase 1 Completion

**MUST be validated before Phase 4:**
- ✅ WiFi connection stable (connects within 30 seconds)
- ✅ OSC message formatting correct (`/heartbeat/N <int32>`)
- ✅ Test messages (800-999ms) received by Python receiver
- ✅ LED feedback working (blink → solid)
- ✅ `sendHeartbeatOSC()` function proven reliable

**Verify Phase 1:**
```bash
cd /home/sderle/fw-phase-3/firmware/heartbeat_phase1
pio run --target upload && pio device monitor

# Should see:
# - WiFi connected
# - Messages sent at 1 Hz
# - Test IBI values 800-999ms
```

### 0.2 Phase 3 Completion

**MUST be implemented and validated:**
- ✅ 4 sensors sampling at 50Hz
- ✅ Moving average filter (5-sample window)
- ✅ Adaptive baseline tracking
- ✅ Threshold-based beat detection
- ✅ IBI calculation per sensor
- ✅ Disconnection detection
- ✅ Independent per-sensor state

**Note:** Phase 3 TRD exists (`docs/firmware/reference/phase3-firmware-trd.md`) but implementation directory does not exist yet. Agent must either:
1. Implement Phase 3 first (follow Phase 3 TRD), OR
2. Implement Phase 3 + Phase 4 together in a single unified firmware

**Recommended approach:** Implement Phase 3 fully, test independently, then proceed to Phase 4 integration.

### 0.3 Testing Infrastructure

**MUST be ready:**
- ✅ Python OSC receiver running on port 8000
- ✅ Development machine IP configured correctly
- ✅ 4 pulse sensors connected to GPIO 32-35
- ✅ Physical setup allows multiple people to test simultaneously

---

## 1. Objective

Integrate Phase 3's real beat detection with Phase 1's OSC messaging infrastructure to complete the full data pipeline from pulse sensor to audio server. Validate end-to-end functionality and production readiness.

**Deliverables:**
- Single `main.cpp` combining Phase 3 beat detection + Phase 1 OSC messaging
- Real sensor-derived IBI values transmitted via OSC (no more test values)
- Complete validation that beats flow correctly to server
- Production-ready configuration (DEBUG_LEVEL 0)
- Documentation of integration points and testing procedures

**Success Criteria:**
- Real beats from all 4 sensors transmitted via OSC
- OSC message format matches architecture spec
- BPM accuracy ±5 BPM vs smartphone reference
- Latency <25ms from beat detection to network transmission
- 30+ minute stability test passes
- Server-side validation confirms all messages valid
- Production mode (DEBUG_LEVEL 0) tested
- WiFi resilience validated under sensor load

---

## 2. Architecture Overview

### 2.1 Integration Points

**Phase 4 bridges these two working systems:**

```
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 3 (Implemented)                   │
│  Sensor → ADC → Moving Avg → Baseline → Beat Detection     │
│                                             ↓                │
│                                         IBI value           │
└─────────────────────────────────────────────────────────────┘
                                             ↓
                                    **INTEGRATION POINT**
                                             ↓
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 1 (Validated)                     │
│  sendHeartbeatOSC(sensorIndex, ibi_ms)                     │
│           ↓                                                  │
│  OSC Message → WiFiUDP → Network → Server                  │
└─────────────────────────────────────────────────────────────┘
```

**Key Integration Point:**
- Phase 3 `detectBeat()` already calls `sendHeartbeatOSC(sensorIndex, ibi)`
- Phase 1 `sendHeartbeatOSC()` already formats OSC correctly
- **Phase 4 validates this integration works in practice**

### 2.2 What Phase 4 Adds

**Technical changes (minimal):**
- Update `sendHeartbeatOSC()` signature to accept `sensorIndex` parameter
- Remove test message generation code from loop()
- Replace 1Hz timer with real-time beat detection triggers
- Validate LED feedback responds to real beats
- Add production configuration validation

**Primary focus:**
- **End-to-end testing** of complete data pipeline
- **Server-side validation** that messages are correct and timely
- **Production readiness** checks (stability, WiFi resilience, error handling)
- **Performance validation** (latency, throughput, reliability)

### 2.3 Execution Model

**Same as Phase 3, now with real OSC transmission:**
- `setup()`: Initialize hardware, WiFi, sensors, UDP
- `loop()` @ 50Hz:
  1. Sample all 4 sensors (ADC reads)
  2. Process each sensor (filter, baseline, threshold)
  3. Detect beats (rising edge + refractory check)
  4. **Immediately send OSC on beat detection** (Phase 1 infrastructure)
  5. Update LED (flash on any beat)
  6. Monitor WiFi status

**Timing:**
- Target: 20ms per sampling cycle (50Hz per sensor)
- Beat detection: <1ms computational overhead
- OSC transmission: 1-5ms typical UDP send
- **Total latency budget: <25ms from beat to network**

---

## 3. Implementation Approach

### 3.1 Code Structure

**Option A: Extend Phase 3 (Recommended if Phase 3 exists)**
- Copy `firmware/heartbeat_phase3/` → `firmware/heartbeat_phase4/`
- Modify `sendHeartbeatOSC()` signature (add sensorIndex parameter)
- Remove any test message generation code
- Update `loop()` to use real beat triggers
- Validate integration

**Option B: Unified Implementation (If Phase 3 not implemented yet)**
- Implement Phase 3 + Phase 4 together in `firmware/heartbeat_phase4/`
- Follow Phase 3 TRD for beat detection algorithm
- Follow Phase 1 TRD for OSC messaging
- Integrate at `detectBeat()` → `sendHeartbeatOSC()` interface

**File structure:**
```
firmware/heartbeat_phase4/
├── platformio.ini         # Same as Phase 1/3
├── src/
│   └── main.cpp          # Integrated firmware
├── include/
│   └── ssid.h            # WiFi credentials (untracked)
└── test/                 # Validation tests
```

### 3.2 Integration Checklist

**R1: Update sendHeartbeatOSC() Signature**

**Current (Phase 1):**
```cpp
void sendHeartbeatOSC(int ibi_ms);  // Uses global SENSOR_ID
```

**Required (Phase 4):**
```cpp
void sendHeartbeatOSC(int sensorIndex, int ibi_ms);  // Per-sensor addressing
```

**Implementation:**
```cpp
void sendHeartbeatOSC(int sensorIndex, int ibi_ms) {
    // Construct OSC address: /heartbeat/0, /heartbeat/1, etc.
    char oscAddress[20];
    snprintf(oscAddress, sizeof(oscAddress), "/heartbeat/%d", sensorIndex);
    
    // Create OSC message with int32 IBI
    OSCMessage msg(oscAddress);
    msg.add((int32_t)ibi_ms);
    
    // UDP transmission (Phase 1 proven sequence)
    udp.beginPacket(SERVER_IP, SERVER_PORT);
    msg.send(udp);
    udp.endPacket();
    msg.empty();
    
    #if DEBUG_LEVEL >= 2
        Serial.print("OSC sent: ");
        Serial.print(oscAddress);
        Serial.print(" ");
        Serial.println(ibi_ms);
    #endif
}
```

**R2: Remove Test Message Generation**

**Delete from Phase 1 loop():**
```cpp
// OLD PHASE 1 CODE - REMOVE:
if (currentTime - state.lastMessageTime >= TEST_MESSAGE_INTERVAL_MS) {
    int test_ibi = 800 + (state.messageCounter % 200);  // DELETE
    sendHeartbeatOSC(test_ibi);                         // DELETE
    state.lastMessageTime = currentTime;                 // DELETE
    state.messageCounter++;                              // DELETE
}
```

**R3: Validate Beat Detection Triggers OSC**

**Phase 3 detectBeat() already does this:**
```cpp
void detectBeat(int sensorIndex) {
    // ... threshold calculation, rising edge detection ...
    
    if (risingEdge && timeOK) {
        unsigned long ibi = now - sensors[sensorIndex].lastBeatTime;
        
        if (sensors[sensorIndex].firstBeatDetected) {
            // **THIS IS THE INTEGRATION POINT**
            sendHeartbeatOSC(sensorIndex, (int)ibi);  // ← Phase 1 function
            
            system.beatDetectedThisLoop = true;  // LED feedback
        }
        
        sensors[sensorIndex].lastBeatTime = now;
        sensors[sensorIndex].firstBeatDetected = true;
    }
}
```

**Verification:**
- MUST confirm `sendHeartbeatOSC()` called on every beat (after first)
- MUST pass correct sensorIndex (0-3)
- MUST pass real IBI value (time since last beat)

**R4: Validate LED Feedback for Real Beats**

**Phase 3 LED update should respond to real beats:**
```cpp
void updateLED() {
    static unsigned long ledPulseTime = 0;
    const int LED_PULSE_DURATION = 50;  // 50ms pulse
    
    if (!system.wifiConnected) {
        // Rapid blink during WiFi connection
        digitalWrite(STATUS_LED_PIN, (millis() / 50) % 2);
    } else if (system.beatDetectedThisLoop) {
        // Beat detected: pulse LED
        digitalWrite(STATUS_LED_PIN, HIGH);
        ledPulseTime = millis();
    } else if (millis() - ledPulseTime < LED_PULSE_DURATION) {
        // Hold pulse
        digitalWrite(STATUS_LED_PIN, HIGH);
    } else {
        // Idle: solid on
        digitalWrite(STATUS_LED_PIN, HIGH);
    }
    
    // Clear flag for next iteration
    system.beatDetectedThisLoop = false;
}
```

**Verification:**
- LED MUST flash on real beats (not on timer)
- LED MUST respond to ANY sensor's beat
- Flash duration: 50ms (visible but not distracting)

**R5: Configuration Constants Consolidation**

**Network (from Phase 1):**
```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS
const uint16_t SERVER_PORT = 8000;
```

**Hardware (from Phase 3):**
```cpp
const int SENSOR_PINS[4] = {32, 33, 34, 35};
const int NUM_SENSORS = 4;
const int STATUS_LED_PIN = 2;
const int ADC_RESOLUTION = 12;
```

**Signal Processing (from Phase 3):**
```cpp
const int SAMPLE_RATE_HZ = 50;
const int SAMPLE_INTERVAL_MS = 20;
const int MOVING_AVG_SAMPLES = 5;
const float BASELINE_DECAY_RATE = 0.1;
const int BASELINE_DECAY_INTERVAL = 150;
```

**Beat Detection (from Phase 3):**
```cpp
const float THRESHOLD_FRACTION = 0.6;
const int MIN_SIGNAL_RANGE = 50;
const unsigned long REFRACTORY_PERIOD_MS = 300;
const int FLAT_SIGNAL_THRESHOLD = 5;
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;
```

**Debug Level:**
```cpp
#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose
```

**R6: Remove Phase 1-Specific Code**

**DELETE from Phase 1:**
- `SENSOR_ID` constant (no longer needed, use array index)
- `TEST_MESSAGE_INTERVAL_MS` (no longer sending test messages)
- Test message generation logic in loop()
- `messageCounter` (unless needed for debug)

---

## 4. Validation & Testing

### 4.1 Unit Test: OSC Message Format

**Purpose:** Validate OSC messages match architecture specification

**Test Procedure:**
1. Set DEBUG_LEVEL = 2
2. Place finger on Sensor 0
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

**Validation:**
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

### 4.2 Integration Test: Single Sensor Beat Flow

**Purpose:** Validate complete pipeline for one sensor

**Test Procedure:**
1. Upload Phase 4 firmware with DEBUG_LEVEL = 1
2. Start Python OSC receiver
3. Place finger on Sensor 0 (GPIO 32)
4. Run for 2 minutes

**Expected Serial Output:**
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

**Validation:**
- ✅ First beat detected but no OSC sent (correct)
- ✅ Subsequent beats send OSC immediately
- ✅ IBI values match between serial and receiver
- ✅ BPM calculated by receiver is reasonable (50-100 typical)
- ✅ LED flashes on each beat
- ✅ No missed beats (continuous detection)

### 4.3 Integration Test: Multi-Sensor Independence

**Purpose:** Validate all 4 sensors work independently and concurrently

**Test Procedure:**
1. DEBUG_LEVEL = 1
2. 4 people, each place finger on different sensor
3. Run for 5 minutes
4. Monitor Python receiver

**Expected Receiver Output:**
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

**Validation:**
- ✅ All 4 sensors send messages
- ✅ Messages interleaved (independent timing per sensor)
- ✅ Each sensor's BPM stable (±5 BPM variation)
- ✅ No crosstalk (sensor 0 doesn't trigger sensor 1 messages)
- ✅ LED responds to beats from ANY sensor
- ✅ No packet loss (receiver sees all messages)

### 4.4 Latency Test: Beat to Network Timing

**Purpose:** Measure latency from beat detection to OSC transmission

**Test Method:**

**Option A: Serial Timestamp Comparison**
```cpp
// In detectBeat(), add timestamps:
#if DEBUG_LEVEL >= 2
    unsigned long beatTime = millis();
    sendHeartbeatOSC(sensorIndex, (int)ibi);
    unsigned long oscSentTime = millis();
    Serial.print("Latency: ");
    Serial.print(oscSentTime - beatTime);
    Serial.println("ms");
#endif
```

**Option B: Python Receiver Timestamp Validation**
```python
# In osc_receiver.py, add:
import time
def handle_heartbeat(address, *args):
    recv_time = time.time() * 1000  # ms
    # Compare with ESP32 timestamp if available
```

**Validation:**
- ✅ 95th percentile latency <25ms
- ✅ Typical latency <10ms
- ✅ No outliers >50ms (would indicate WiFi issues)

**Acceptable latency breakdown:**
- Beat detection: <1ms
- OSC message construction: <1ms
- UDP transmission: 1-5ms typical, up to 20ms worst case
- Network propagation: 1-5ms on local WiFi

### 4.5 Stress Test: Extended Duration Stability

**Purpose:** Validate production readiness (no crashes, memory leaks, WiFi issues)

**Test Procedure:**
1. Set DEBUG_LEVEL = 0 (production mode, minimal serial output)
2. 2-4 people on sensors
3. Run for 60+ minutes continuous
4. Monitor Python receiver statistics

**Validation Metrics:**

**Firmware Stability:**
- ✅ No ESP32 resets (check serial for startup banner)
- ✅ No WiFi disconnections (or successful auto-reconnects)
- ✅ Consistent beat detection throughout (no degradation)
- ✅ LED continues to respond (not frozen)

**Network Stability:**
- ✅ Zero packet loss (receiver sees all expected messages)
- ✅ Message rate stable (no slowdowns or speedups)
- ✅ Latency consistent (no increasing trend)

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

**Failure Criteria (test failed if):**
- Any ESP32 resets
- WiFi disconnection without auto-reconnect
- Packet loss >1%
- Invalid OSC messages >0
- Latency >50ms sustained

### 4.6 WiFi Resilience Test

**Purpose:** Validate automatic reconnection under stress

**Test Procedure:**
1. Firmware running with beats being detected
2. Disable WiFi access point for 30 seconds
3. Re-enable access point
4. Monitor reconnection

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

**Validation:**
- ✅ WiFi disconnection detected within 5 seconds
- ✅ Reconnection attempted automatically
- ✅ Sampling continues during disconnection (no beats missed)
- ✅ OSC transmission resumes immediately after reconnection
- ✅ LED shows connection status (blink during reconnect)
- ✅ No ESP32 reset required

### 4.7 BPM Accuracy Validation

**Purpose:** Validate against smartphone heart rate app reference

**Test Procedure:**
1. Install smartphone heart rate app (e.g., "Instant Heart Rate" on iOS/Android)
2. Test subject simultaneously:
   - Left index finger on smartphone camera
   - Right index finger on ESP32 Sensor 0
3. Measure for 60 seconds
4. Compare BPM values

**Expected Results:**
```
Smartphone app: 72 BPM (stable reading after 30 seconds)
ESP32 Sensor 0: 70 BPM (average over 60 seconds)
Difference: 2 BPM (within ±5 BPM tolerance)
```

**Validation:**
- ✅ BPM difference ≤5 BPM
- ✅ ESP32 readings stable (not jumping wildly)
- ✅ No missed beats causing artificially low BPM
- ✅ No false beats causing artificially high BPM

**Note:** Absolute accuracy is not critical for art installation (relative changes more important). ±5 BPM tolerance is acceptable for this application.

---

## 5. Production Configuration

### 5.1 Production Settings

**For festival deployment, MUST configure:**

```cpp
// Network - CHANGE THESE
const char* WIFI_SSID = "festival-network";      // Festival WiFi
const char* WIFI_PASSWORD = "secure-password";   // From organizers
const IPAddress SERVER_IP(192, 168, 1, 100);    // Audio server IP
const uint16_t SERVER_PORT = 8000;               // OSC port

// Debug level - PRODUCTION MODE
#define DEBUG_LEVEL 0  // Minimal serial output

// Signal processing - TUNED VALUES (if needed after testing)
const float THRESHOLD_FRACTION = 0.6;   // May need adjustment per installation
const int MIN_SIGNAL_RANGE = 50;        // Noise floor depends on environment
```

### 5.2 Production Validation Checklist

**Before festival deployment:**

**Hardware:**
- ✅ All 4 sensors mounted securely
- ✅ ESP32 powered reliably (USB or external 5V)
- ✅ Pulse sensors labeled 0-3 clearly
- ✅ WiFi antenna not obstructed
- ✅ Status LED visible to technicians

**Configuration:**
- ✅ WiFi credentials correct (tested on-site)
- ✅ Server IP correct (ping from ESP32 network)
- ✅ DEBUG_LEVEL = 0 (production mode)
- ✅ Threshold tuned for installation environment
- ✅ Sensors respond to all test subjects

**Testing:**
- ✅ 4-person test successful (all sensors working)
- ✅ 30+ minute stability test passed
- ✅ WiFi resilience validated
- ✅ BPM accuracy acceptable (±5 BPM)
- ✅ Server receives and processes all messages
- ✅ Audio synthesis responds correctly to beats

**Documentation:**
- ✅ Sensor-to-person mapping documented
- ✅ WiFi network details recorded
- ✅ Server IP and port documented
- ✅ Troubleshooting guide available on-site
- ✅ Emergency reset procedure documented

### 5.3 Production Serial Output

**DEBUG_LEVEL = 0 (Production Mode):**
```
=== Heartbeat Installation - Phase 4 ===
OSC Integration & Production Validation
Connecting to WiFi: festival-network
Connected! IP: 192.168.1.42
Setup complete. Starting beat detection...
```
(No further output unless errors occur)

**Benefits:**
- Minimal serial buffer usage
- No performance overhead from logging
- Clean monitor output for technicians
- Errors still visible if they occur

**DEBUG_LEVEL = 1 (Testing Mode) for troubleshooting:**
```
[0] Beat at 12847ms, IBI=867ms
[2] Beat at 13021ms, IBI=742ms
[1] Beat at 13198ms, IBI=923ms
WiFi disconnected, reconnecting...
```

**Switch to Level 1 if issues occur during festival, back to Level 0 when stable.**

---

## 6. Acceptance Criteria

### 6.1 Phase 4 Complete

**All criteria MUST be met:**

**Integration:**
- ✅ Phase 3 beat detection + Phase 1 OSC messaging integrated
- ✅ Real sensor IBIs transmitted (no test values)
- ✅ `sendHeartbeatOSC()` called on every beat detection
- ✅ LED responds to real beats (not timer-based)

**Functionality:**
- ✅ All 4 sensors detect beats independently
- ✅ OSC messages format correct: `/heartbeat/[0-3] <int32>`
- ✅ BPM accuracy ±5 BPM vs smartphone reference
- ✅ First beat detection: no OSC sent (correct behavior)
- ✅ Subsequent beats: IBI calculated and sent correctly
- ✅ Disconnection detection working (<1 sec response)
- ✅ Reconnection automatic (<3 sec resume)

**Performance:**
- ✅ Latency <25ms (95th percentile, beat to network)
- ✅ 30+ minute stability test passes
- ✅ No crashes, resets, or memory issues
- ✅ WiFi auto-reconnect validated
- ✅ Consistent performance (no degradation)

**Validation:**
- ✅ Single-sensor test successful
- ✅ Multi-sensor test successful (2-4 people)
- ✅ Python receiver validates all messages
- ✅ Zero invalid OSC messages
- ✅ Zero packet loss (<1% acceptable)
- ✅ Server-side processing working

**Production:**
- ✅ DEBUG_LEVEL 0 tested (production mode)
- ✅ Configuration documented
- ✅ On-site WiFi validated
- ✅ 4-person end-to-end test passed
- ✅ Emergency procedures documented

### 6.2 Ready for Festival Deployment

**System is production-ready when:**

- ✅ Complete data pipeline validated (sensor → ESP32 → network → server → audio)
- ✅ Multi-person testing successful (4 simultaneous users)
- ✅ Extended duration test passed (60+ minutes)
- ✅ On-site WiFi tested and stable
- ✅ Audio synthesis responds correctly to heartbeat messages
- ✅ Technicians trained on system monitoring
- ✅ Troubleshooting procedures documented and tested
- ✅ Backup ESP32 units programmed and ready
- ✅ Power supply reliable and tested
- ✅ Physical installation secure and accessible

---

## 7. Known Limitations

### 7.1 Intentional Simplifications (Acceptable for Art Installation)

**Not implemented in Phase 4:**
- No waveform transmission (only IBI intervals)
- No HRV (heart rate variability) analysis
- No beat prediction or anticipation
- No multi-server broadcasting
- No onboard BPM calculation (server does this)
- No quality metrics per beat (SNR, confidence)
- No NTP time synchronization
- No SD card logging
- No web-based configuration interface
- No OTA (over-the-air) firmware updates

**These features could be added in future versions if needed, but are not required for festival installation.**

### 7.2 Environmental Limitations

**System performance affected by:**
- **Ambient light:** Optical sensors sensitive to bright light (shield sensors if possible)
- **Cold hands:** Reduced peripheral blood flow affects signal quality (warm up before using)
- **Movement:** Large motions create artifacts (ask participants to stay relatively still)
- **WiFi congestion:** Festival WiFi with many users may cause intermittent dropouts (use dedicated network if possible)
- **Distance:** ESP32 WiFi range ~30m from access point (position router centrally)

**Mitigation strategies documented in troubleshooting guide.**

### 7.3 Algorithm Limitations

**Beat detection algorithm:**
- **Fixed threshold fraction:** May not be optimal for all users (tunable constant)
- **Moving average lag:** 50ms delay in signal (acceptable for this application)
- **Baseline adaptation:** 3-second time constant (may miss very rapid amplitude changes)
- **Refractory period:** Enforces max 200 BPM (protects against false triggers)

**These are acceptable tradeoffs for real-time beat detection in art installation context.**

### 7.4 Protocol Limitations

**UDP OSC transmission:**
- **No acknowledgment:** ESP32 doesn't know if server received message
- **No packet ordering:** Messages may arrive out of order (rare on local WiFi)
- **No automatic discovery:** Server IP must be configured manually
- **Fire-and-forget:** Lost packets not retransmitted (acceptable for beat events)

**These UDP characteristics are acceptable because:**
- Occasional dropped beat event is not critical (next beat arrives soon)
- Local WiFi has very low packet loss (<0.1% typical)
- Server handles out-of-order messages correctly (timestamps available)
- Simplicity and low latency more important than guaranteed delivery

---

## 8. Troubleshooting

### 8.1 Integration Issues

**Symptom: Beats detected but no OSC messages**

**Debug steps:**
1. Set DEBUG_LEVEL = 2
2. Check serial output for "OSC sent:" messages
3. Verify `sendHeartbeatOSC()` is being called

**Possible causes:**
- `sendHeartbeatOSC()` not called in `detectBeat()`
- Function signature mismatch (forgot sensorIndex parameter)
- WiFi disconnected (check `wifiConnected` state)

**Solution:**
```cpp
// In detectBeat(), verify this code exists:
if (sensors[sensorIndex].firstBeatDetected) {
    sendHeartbeatOSC(sensorIndex, (int)ibi);  // ← Must be here
    system.beatDetectedThisLoop = true;
}
```

### 8.2 OSC Format Issues

**Symptom: Python receiver shows "Invalid OSC message"**

**Debug steps:**
1. Use Wireshark to capture raw UDP packets
2. Check OSC message binary format
3. Verify type tag is `,i` (int32)

**Possible causes:**
- Wrong argument type (e.g., float instead of int32)
- Missing null termination in address string
- Incorrect `msg.send()` sequence

**Solution:**
```cpp
// Verify exact sequence:
OSCMessage msg(oscAddress);
msg.add((int32_t)ibi_ms);  // ← Must cast to int32_t
udp.beginPacket(SERVER_IP, SERVER_PORT);
msg.send(udp);
udp.endPacket();
msg.empty();  // ← Don't forget this
```

### 8.3 High Latency

**Symptom: Latency >50ms consistently**

**Debug steps:**
1. Measure latency with DEBUG_LEVEL = 2 timestamps
2. Check WiFi signal strength (`WiFi.RSSI()`)
3. Monitor network with ping tests

**Possible causes:**
- WiFi congestion or interference
- Router overloaded
- Network path through multiple hops
- ESP32 too far from router

**Solutions:**
- Move ESP32 closer to router
- Use 2.4GHz channel with less interference
- Dedicate router to heartbeat system
- Increase WiFi transmit power if needed

### 8.4 Packet Loss

**Symptom: Python receiver missing messages (>1% loss)**

**Debug steps:**
1. Count beats in serial output (DEBUG_LEVEL = 1)
2. Count messages in Python receiver
3. Compare counts after 5 minutes

**Possible causes:**
- WiFi signal weak
- Network congestion
- Receiver buffer overflow
- Firewall dropping packets

**Solutions:**
- Improve WiFi signal strength
- Reduce competing WiFi traffic
- Check firewall rules on server
- Use dedicated network if possible

### 8.5 BPM Inaccuracy

**Symptom: BPM differs by >5 BPM from smartphone reference**

**Debug steps:**
1. Set DEBUG_LEVEL = 2
2. Check raw ADC values (should oscillate)
3. Check baseline min/max (should track signal)
4. Check threshold crossing events

**Possible causes:**
- THRESHOLD_FRACTION too high or too low
- Sensor contact poor
- Ambient light interference
- Movement artifacts

**Solutions:**
- Adjust THRESHOLD_FRACTION (try 0.5-0.7)
- Improve finger contact (press firmer)
- Shield sensors from ambient light
- Ask participant to stay still

---

## 9. Next Steps After Phase 4

### 9.1 Server-Side Integration

**After Phase 4 firmware validated, integrate with audio server:**

1. **Pure Data OSC Receiver:**
   - Implement OSC listener on port 8000
   - Parse `/heartbeat/[0-3]` messages
   - Extract IBI int32 values
   - Map to audio synthesis parameters

2. **Audio Synthesis:**
   - Convert IBI to BPM: `60000 / ibi_ms`
   - Map BPM to audio parameters (pitch, rhythm, amplitude)
   - Synchronize audio with beat events
   - Handle 4 independent audio channels (one per sensor)

3. **Lighting Control (Optional):**
   - Send beat events to lighting system
   - Synchronize lights with heartbeats
   - Map sensor positions to light fixtures

### 9.2 Installation Testing

**On-site validation before festival opening:**

1. **Network Setup:**
   - Configure festival WiFi credentials
   - Test ESP32 connects reliably
   - Measure WiFi signal strength at installation location
   - Verify server reachable from ESP32 network

2. **Multi-Person Test:**
   - 4 volunteers test all sensors simultaneously
   - Run for 15+ minutes
   - Validate audio synthesis responds correctly
   - Check for any crosstalk or interference

3. **Environmental Adaptation:**
   - Test in actual lighting conditions
   - Adjust THRESHOLD_FRACTION if needed
   - Test with various skin tones and hand temperatures
   - Document any tuning changes

4. **Technician Training:**
   - Show how to monitor system status (LED, serial)
   - Demonstrate reset procedure
   - Explain common issues and solutions
   - Provide troubleshooting checklist

### 9.3 Monitoring and Maintenance

**During festival operation:**

1. **Continuous Monitoring:**
   - Server logs all OSC messages with timestamps
   - Track packet loss and latency metrics
   - Alert on sustained WiFi disconnections
   - Monitor sensor health (beats per minute)

2. **Daily Checks:**
   - Verify all 4 sensors responding
   - Check WiFi connection stable
   - Test audio synthesis working
   - Inspect physical hardware (connections, mounting)

3. **Backup Procedures:**
   - Keep backup ESP32 programmed and ready
   - Document quick replacement procedure
   - Maintain spare pulse sensors
   - Keep WiFi credentials accessible

---

## 10. Document References

### 10.1 Related Documents

**Architecture:**
- `docs/firmware/reference/architecture.md` - Overall system design, OSC protocol spec

**Previous Phases:**
- `docs/firmware/reference/phase1-firmware-trd.md` - WiFi + OSC infrastructure
- `docs/firmware/reference/phase3-firmware-trd.md` - Multi-sensor beat detection

**Testing:**
- `firmware/heartbeat_phase1/TEST_SUITE_GUIDE.md` - Phase 1 validation procedures
- `docs/firmware/guides/phase1-05-validation.md` - Python OSC receiver setup

**Implementation:**
- `firmware/heartbeat_phase1/src/main.cpp` - Phase 1 reference code
- `firmware/heartbeat_phase4/src/main.cpp` - Phase 4 integrated code (to be created)

### 10.2 Key Architecture References

**OSC Protocol (architecture.md lines 190-208):**
- Address pattern: `/heartbeat/N` where N = 0-3
- Argument: single int32 (IBI in milliseconds)
- Transport: UDP, fire-and-forget
- No BPM calculation on ESP32 (server does this)

**Network Configuration (architecture.md lines 30-37):**
- Fixed destination IP and port (configured at compile time)
- UDP socket, no discovery
- Packet size ~24 bytes (no fragmentation)

**Beat Detection (architecture.md lines 154-187):**
- Adaptive threshold: 60% of signal range
- Refractory period: 300ms (max 200 BPM)
- First beat: no OSC sent (no reference point)
- Subsequent beats: IBI = time since last beat

---

## 11. Success Metrics Summary

### 11.1 Technical Metrics

**Required for Phase 4 completion:**

| Metric | Target | Test Method | Status |
|--------|--------|-------------|--------|
| OSC format correctness | 100% valid | Python receiver validation | ☐ |
| BPM accuracy | ±5 BPM | vs smartphone reference | ☐ |
| Latency (95th %ile) | <25ms | Timestamp comparison | ☐ |
| Packet loss | <1% | Receiver statistics | ☐ |
| Stability (30min) | 0 crashes | Extended duration test | ☐ |
| WiFi resilience | Auto-reconnect <30s | Disconnect/reconnect test | ☐ |
| Multi-sensor independence | No crosstalk | 4-person test | ☐ |
| Production mode | Clean operation | DEBUG_LEVEL 0 test | ☐ |

### 11.2 Qualitative Assessment

**System is ready when:**
- Technician can set up and validate system in <15 minutes
- Non-technical users can apply finger and see immediate response
- Audio synthesis is clearly driven by heartbeat rhythms
- System runs unattended for hours without intervention
- Occasional packet loss or disconnection doesn't disrupt experience
- Visual feedback (LED) provides clear status indication
- Troubleshooting procedures are effective and documented

---

## 12. Conclusion

Phase 4 completes the firmware data pipeline by integrating:
- **Phase 1's** proven WiFi and OSC messaging infrastructure
- **Phase 3's** multi-sensor beat detection algorithm
- **End-to-end validation** from pulse sensor to audio server

The result is a production-ready system that:
- Detects real heartbeats from 4 independent sensors
- Transmits IBI values via OSC with <25ms latency
- Operates reliably for hours without intervention
- Handles WiFi disruptions gracefully
- Provides clear visual feedback
- Integrates seamlessly with audio synthesis server

**Implementation focus:** Integration and validation, not new feature development. Most code already exists in Phase 1 and Phase 3; Phase 4 ensures they work together correctly in production.

---

*End of Technical Requirements Document*

**Document Version:** 1.0  
**Last Updated:** 2025-11-09  
**Status:** Ready for implementation  
**Dependencies:**  
  - Phase 1 (WiFi + OSC infrastructure) - IMPLEMENTED  
  - Phase 3 (Multi-sensor beat detection) - SPECIFIED IN TRD, NOT YET IMPLEMENTED  
**Estimated Time:** 3-4 hours integration + 3-4 hours validation  
**Next Step:** Implement Phase 3 if not done, then integrate with Phase 4 requirements  

---

**IMPLEMENTATION NOTE:**

Since `firmware/heartbeat_phase3/` does not exist yet, the coding agent has two options:

**Option A (Recommended):** Sequential implementation
1. Implement Phase 3 first (follow `phase3-firmware-trd.md`)
2. Validate Phase 3 independently
3. Then implement Phase 4 integration (this TRD)

**Option B:** Unified implementation
1. Create `firmware/heartbeat_phase4/` directly
2. Implement Phase 3 + Phase 4 together
3. Follow both TRDs in parallel
4. Validate complete system

Either approach is acceptable. Option A is safer (validate incrementally), Option B is faster (single implementation pass).

**END OF DOCUMENT**
