# Phase 4 API Integration: Phase 1 + Phase 3 Requirements

Phase 4 integration requires six specific modifications to connect Phase 3's beat detection with Phase 1's OSC infrastructure.

## R1: Update sendHeartbeatOSC() Signature

The critical integration point: Phase 3 beat detection must pass sensor index to Phase 1 OSC transmission.

**Current Phase 1 Implementation:**
```cpp
void sendHeartbeatOSC(int ibi_ms);  // Uses global SENSOR_ID
```

**Required Phase 4 Implementation:**
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

**Verification Points:**
- Function accepts both sensorIndex (0-3) and ibi_ms parameters
- OSC address formatted as `/heartbeat/N` where N is sensorIndex
- Type tag `,i` for int32 argument
- Packet properly framed with beginPacket/endPacket
- Debug output includes OSC address and IBI value

## R2: Remove Test Message Generation

Phase 1 generated test messages at 1 Hz. Phase 4 uses real beat detection instead.

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

**Also Remove Constants:**
```cpp
#define TEST_MESSAGE_INTERVAL_MS 1000  // DELETE
#define SENSOR_ID 0                    // DELETE (use array index instead)
```

**Verification Points:**
- No timer-based message generation in loop()
- No TEST_MESSAGE_INTERVAL_MS constant
- No SENSOR_ID global constant
- All OSC messages triggered by beat detection, not timing

## R3: Validate Beat Detection Triggers OSC

Beat detection must immediately trigger OSC transmission. Phase 3 `detectBeat()` already has this structure.

**Integration Point in detectBeat():**
```cpp
void detectBeat(int sensorIndex) {
    // ... threshold calculation, rising edge detection ...

    if (risingEdge && timeOK) {
        unsigned long ibi = now - sensors[sensorIndex].lastBeatTime;

        if (sensors[sensorIndex].firstBeatDetected) {
            // **THIS IS THE CRITICAL INTEGRATION POINT**
            sendHeartbeatOSC(sensorIndex, (int)ibi);  // ← Phase 1 function

            system.beatDetectedThisLoop = true;  // LED feedback
        }

        sensors[sensorIndex].lastBeatTime = now;
        sensors[sensorIndex].firstBeatDetected = true;
    }
}
```

**Verification Checklist:**
- ✅ `sendHeartbeatOSC()` called on every beat after first
- ✅ Correct sensorIndex passed (0-3, matches GPIO)
- ✅ Real IBI value calculated (time since last beat)
- ✅ First beat: no OSC sent (correct - no reference point)
- ✅ Subsequent beats: IBI immediately transmitted
- ✅ LED flag set for visual feedback

## R4: Validate LED Feedback for Real Beats

LED must respond to real beat detection, not timer-based generation.

**Implementation:**
```cpp
void updateLED() {
    static unsigned long ledPulseTime = 0;
    const int LED_PULSE_DURATION = 50;  // 50ms visible pulse

    if (!system.wifiConnected) {
        // Rapid blink during WiFi connection
        digitalWrite(STATUS_LED_PIN, (millis() / 50) % 2);
    } else if (system.beatDetectedThisLoop) {
        // Beat detected: pulse LED
        digitalWrite(STATUS_LED_PIN, HIGH);
        ledPulseTime = millis();
    } else if (millis() - ledPulseTime < LED_PULSE_DURATION) {
        // Hold pulse for visibility
        digitalWrite(STATUS_LED_PIN, HIGH);
    } else {
        // Idle: solid on (WiFi connected, no beat)
        digitalWrite(STATUS_LED_PIN, HIGH);
    }

    // Clear flag for next iteration
    system.beatDetectedThisLoop = false;
}
```

**Verification Checklist:**
- ✅ LED flashes on real beats (50ms pulse)
- ✅ LED responds to ANY sensor's beat
- ✅ Flash duration visible but not distracting (50ms)
- ✅ LED indicates WiFi status (rapid blink during connection)
- ✅ No LED updates when no beats (depends on detectBeat trigger)

## R5: Consolidate Configuration Constants

Phase 4 pulls configuration from both Phase 1 and Phase 3.

**Network Constants (Phase 1):**
```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE FOR DEPLOYMENT
const uint16_t SERVER_PORT = 8000;
const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 second connection timeout
```

**Hardware Constants (Phase 3):**
```cpp
const int SENSOR_PINS[4] = {32, 33, 34, 35};
const int NUM_SENSORS = 4;
const int STATUS_LED_PIN = 2;
const int ADC_RESOLUTION = 12;
const int ADC_MAX = 4095;  // 12-bit resolution
```

**Signal Processing Constants (Phase 3):**
```cpp
const int SAMPLE_RATE_HZ = 50;
const int SAMPLE_INTERVAL_MS = 20;
const int MOVING_AVG_SAMPLES = 5;
const float BASELINE_DECAY_RATE = 0.1;
const int BASELINE_DECAY_INTERVAL = 150;
```

**Beat Detection Constants (Phase 3):**
```cpp
const float THRESHOLD_FRACTION = 0.6;      // 60% of signal range
const int MIN_SIGNAL_RANGE = 50;           // Minimum to consider valid signal
const unsigned long REFRACTORY_PERIOD_MS = 300;  // Max 200 BPM
const int FLAT_SIGNAL_THRESHOLD = 5;       // Disconnection detection
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;  // 1 second timeout
```

**Debug Configuration:**
```cpp
#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose
```

**Verification Points:**
- All Phase 1 network constants present
- All Phase 3 hardware constants present
- DEBUG_LEVEL properly set (1 for testing, 0 for production)
- No conflicting constant definitions
- All magic numbers extracted as named constants

## R6: Remove Phase 1-Specific Code

Phase 1 code no longer needed in Phase 4 once integration complete.

**Delete Constants:**
```cpp
#define TEST_MESSAGE_INTERVAL_MS 1000  // DELETE
#define SENSOR_ID 0                    // DELETE
```

**Delete from loop() or setup():**
- Test message generation logic (R2)
- `messageCounter` state variable (unless needed for debug)
- Timer-based OSC transmission code
- Any Phase 1-specific serial debug messages

**Keep from Phase 1:**
- WiFi connection initialization
- WiFi status monitoring
- `sendHeartbeatOSC()` function (now modified signature)
- OSC library includes and UDP socket setup
- Network configuration constants

**Verification Points:**
- ✅ No test message generation code remains
- ✅ No TEST_MESSAGE_INTERVAL constant
- ✅ No SENSOR_ID (use array indices instead)
- ✅ All OSC messages driven by beat detection
- ✅ WiFi infrastructure code intact

---

## Integration Verification Checklist

Before declaring Phase 4 integration complete:

**Code Review:**
- [ ] R1: `sendHeartbeatOSC(int sensorIndex, int ibi_ms)` signature updated
- [ ] R2: Test message generation code removed
- [ ] R3: `detectBeat()` calls `sendHeartbeatOSC()` with correct parameters
- [ ] R4: LED responds to real beats via `system.beatDetectedThisLoop` flag
- [ ] R5: All Phase 1 and Phase 3 constants present and consolidated
- [ ] R6: Phase 1 test code removed, integration code remains

**Functional Testing:**
- [ ] Compilation succeeds with no errors
- [ ] Board uploads successfully
- [ ] Serial monitor shows clean startup
- [ ] WiFi connects within 30 seconds
- [ ] First beat detection doesn't send OSC (correct behavior)
- [ ] Subsequent beats send OSC messages
- [ ] LED flashes on beat detection
- [ ] Python receiver sees all messages
- [ ] OSC message format correct (`/heartbeat/[0-3] <int32>`)

---

## Next Steps

See [Implementation](./implementation.md) for detailed testing and validation procedures that verify these integration requirements work correctly.
