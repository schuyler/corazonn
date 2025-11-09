## Component 7: Phase 1 Firmware Implementation

Reference: `docs/p1-fw-trd.md`

### Prerequisites

- [ ] **Task 0.1**: Verify Arduino IDE installation
  - Download from https://www.arduino.cc/en/software (v2.0+)
  - Install for operating system
  - Launch IDE to confirm installation
  - **Status**: User-dependent (not automated)

- [ ] **Task 0.2**: Install ESP32 board support in Arduino IDE
  - Open Arduino IDE → File → Preferences
  - Add board manager URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
  - Tools → Board → Boards Manager
  - Search "esp32" → Install "esp32 by Espressif Systems" (v2.0.0+)
  - Wait for installation (5-10 minutes)
  - **Validation**: Tools → Board shows "ESP32 Dev Module" available
  - **Status**: User-dependent

- [ ] **Task 0.3**: Install OSC library
  - Arduino IDE → Tools → Manage Libraries
  - Search "OSC"
  - Install "OSC by Adrian Freed" (CNMat, v1.3.7+)
  - **Validation**: File → Examples shows "OSC" library
  - **Status**: User-dependent

- [ ] **Task 0.4**: Configure Arduino IDE board settings (TRD R28-R29)
  - Tools → Board → ESP32 Arduino → "ESP32 Dev Module"
  - Tools → Upload Speed → 921600 (or 115200 for reliability)
  - Tools → Flash Frequency → 80MHz
  - Tools → Flash Mode → QIO
  - Tools → Flash Size → 4MB (32Mb)
  - Tools → Partition Scheme → "Default 4MB with spiffs"
  - **Status**: User-dependent

- [ ] **Task 0.5**: Verify testing infrastructure ready
  - Confirm Components 1-5 complete (check `docs/tasks.md`)
  - Test receiver can run: `python3 testing/osc_receiver.py --port 8000`
  - Verify receiver prints "OSC Receiver listening on 0.0.0.0:8000"
  - Stop receiver (Ctrl+C)
  - **Status**: Prerequisites complete (Components 1-5 done)

### Component 7.1: Project Structure

- [ ] **Task 1.1**: Create firmware directory structure
  - Create: `/home/user/corazonn/firmware/` directory
  - Create: `/home/user/corazonn/firmware/heartbeat_phase1/` directory (Arduino sketch folder)
  - **Note**: Arduino requires .ino file to be in folder with same base name
  - **Pattern**: Follows project-structure.md firmware layout

- [ ] **Task 1.2**: Create firmware README
  - Create: `/home/user/corazonn/firmware/README.md`
  - Document: Purpose, Arduino IDE setup reference, upload instructions
  - Document: How to configure WiFi credentials and SERVER_IP
  - Document: How to set unique SENSOR_ID for each unit
  - **Reference**: Similar to testing/README.md structure

### Component 7.2: Firmware Skeleton

- [ ] **Task 2.1**: Create .ino file with includes and configuration (TRD Section 8.1)
  - File: `/home/user/corazonn/firmware/heartbeat_phase1/heartbeat_phase1.ino`
  - Add header comment with project name, phase, version
  - Add includes: `WiFi.h`, `WiFiUdp.h`, `OSCMessage.h`
  - Add network configuration constants (TRD Section 4.1):
    - `WIFI_SSID`, `WIFI_PASSWORD`
    - `SERVER_IP` (IPAddress type)
    - `SERVER_PORT` (8000)
  - Add hardware configuration (TRD Section 4.2):
    - `STATUS_LED_PIN` (GPIO 2)
  - Add system configuration (TRD Section 4.3):
    - `SENSOR_ID` (0-3)
    - `TEST_MESSAGE_INTERVAL_MS` (1000)
    - `WIFI_TIMEOUT_MS` (30000)
  - **Validation**: File compiles with no errors (even with empty setup/loop)

- [ ] **Task 2.2**: Define data structures (TRD Section 5)
  - Add `SystemState` struct with fields:
    - `bool wifiConnected`
    - `unsigned long lastMessageTime`
    - `uint32_t messageCounter`
  - Declare global objects:
    - `WiFiUDP udp;`
    - `SystemState state = {false, 0, 0};`
  - Add function declarations (forward declarations for Arduino)
  - **Validation**: File still compiles

### Component 7.3: WiFi Connection Function

- [ ] **Task 3.1**: Implement connectWiFi() skeleton (TRD Section 6.1)
  - Function signature: `bool connectWiFi();`
  - Return type: `bool` (true=success, false=timeout)
  - Add function to file after global variables
  - **Validation**: File compiles

- [ ] **Task 3.2**: Implement WiFi initialization (TRD R1)
  - Call `WiFi.mode(WIFI_STA)`
  - Call `WiFi.begin(WIFI_SSID, WIFI_PASSWORD)`
  - Print "Connecting to WiFi: [SSID]" to Serial
  - **Test**: Upload to ESP32, verify serial output shows connection attempt

- [ ] **Task 3.3**: Implement connection wait loop (TRD R2)
  - Poll `WiFi.status()` in loop
  - Check if `WL_CONNECTED` OR timeout exceeded
  - Use `millis()` for non-blocking timeout check (30 seconds)
  - Blink LED during connection: `digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2)`
  - **Test**: Verify LED blinks during connection attempt

- [ ] **Task 3.4**: Implement success behavior (TRD R3)
  - On `WL_CONNECTED`: Set `state.wifiConnected = true`
  - Turn LED solid ON
  - Print "Connected! IP: [IP_ADDRESS]" using `WiFi.localIP()`
  - Return `true`
  - **Test**: Verify successful connection with correct SSID/password

- [ ] **Task 3.5**: Implement failure behavior (TRD R4)
  - On timeout: Print "WiFi connection timeout"
  - Return `false` (LED left in last blink state)
  - **Test**: Test with wrong SSID, verify timeout message appears after 30 sec

### Component 7.4: OSC Message Function

- [ ] **Task 4.1**: Implement sendHeartbeatOSC() skeleton (TRD Section 6.2)
  - Function signature: `void sendHeartbeatOSC(int ibi_ms);`
  - Parameter: `ibi_ms` (300-3000ms range)
  - No return value (fire-and-forget UDP)
  - **Validation**: File compiles

- [ ] **Task 4.2**: Implement address pattern construction (TRD R5)
  - Create buffer: `char address[20];`
  - Use `snprintf(address, 20, "/heartbeat/%d", SENSOR_ID)`
  - **Validation**: Code compiles

- [ ] **Task 4.3**: Implement OSC message construction (TRD R6)
  - Create `OSCMessage msg(address);`
  - Add int32 argument: `msg.add((int32_t)ibi_ms);`
  - **Validation**: Code compiles with OSC library

- [ ] **Task 4.4**: Implement UDP transmission (TRD R7)
  - Call `udp.beginPacket(SERVER_IP, SERVER_PORT)`
  - Call `msg.send(udp)` to write OSC data
  - Call `udp.endPacket()` to transmit
  - Call `msg.empty()` AFTER endPacket to clear message buffer
  - **Critical**: Calling sequence matters (beginPacket → send → endPacket → empty)
  - **Test**: Cannot test until integrated with loop and receiver

### Component 7.5: LED Status Function

- [ ] **Task 5.1**: Implement updateLED() function (TRD Section 6.3, R9-R11)
  - Function signature: `void updateLED();`
  - If `!state.wifiConnected`: Blink at 5Hz using `(millis() / 100) % 2`
  - If `state.wifiConnected`: Solid HIGH
  - Use `digitalWrite(STATUS_LED_PIN, state)`
  - Non-blocking (no delays)
  - **Validation**: Code compiles

- [ ] **Task 5.2**: Test LED behavior
  - Upload firmware
  - Verify LED blinks during WiFi connection
  - Verify LED solid ON after connection
  - **Test**: Visual confirmation of LED states

### Component 7.6: WiFi Monitoring Function

- [ ] **Task 6.1**: Implement checkWiFi() function (TRD Section 6.4, R12-R14)
  - Function signature: `void checkWiFi();`
  - Use static variable for rate limiting: `static unsigned long lastCheckTime = 0;`
  - Check if `millis() - lastCheckTime < 5000`, return early if not time yet
  - Update `lastCheckTime = millis()`
  - Check `WiFi.status()`, update `state.wifiConnected`
  - If disconnected: Print "WiFi disconnected, reconnecting...", call `WiFi.reconnect()`
  - **Note**: `WiFi.reconnect()` is non-blocking
  - **Validation**: Code compiles

- [ ] **Task 6.2**: Test WiFi monitoring
  - Upload firmware, connect to WiFi
  - Disable WiFi router or move ESP32 out of range
  - Verify "WiFi disconnected" message appears
  - Re-enable WiFi
  - Verify reconnection occurs
  - **Test**: May be difficult without physical setup, can defer to integration testing

### Component 7.7: Main Program Flow

- [ ] **Task 7.1**: Implement setup() function (TRD Section 7.1, R15-R20)
  - Initialize serial: `Serial.begin(115200); delay(100);`
  - Print startup banner with sensor ID
  - Configure GPIO: `pinMode(STATUS_LED_PIN, OUTPUT); digitalWrite(STATUS_LED_PIN, LOW);`
  - Call `connectWiFi()` and store result in `state.wifiConnected`
  - If WiFi fails: Print detailed error info (TRD R18), enter infinite blink loop
  - If WiFi succeeds: Initialize UDP with `udp.begin(0)` (ephemeral port)
  - Print "Setup complete. Starting message loop..."
  - Initialize `state.lastMessageTime = millis();`
  - **Validation**: Upload and verify serial output shows complete boot sequence

- [ ] **Task 7.2**: Implement loop() function skeleton (TRD Section 7.2)
  - Add `checkWiFi();` call (TRD R21)
  - Add timing check: `unsigned long currentTime = millis();`
  - Add interval check: `if (currentTime - state.lastMessageTime >= TEST_MESSAGE_INTERVAL_MS)`
  - Add LED update: `updateLED();`
  - Add loop delay: `delay(10);` (TRD R27)
  - **Validation**: Code compiles

- [ ] **Task 7.3**: Implement message generation (TRD R23)
  - Inside interval check block:
  - Generate test IBI: `int test_ibi = 800 + (state.messageCounter % 200);`
  - **Note**: Creates deterministic sequence 800-999ms, repeats every 200 messages
  - Simulates 60-75 BPM heart rate
  - **Validation**: Code compiles

- [ ] **Task 7.4**: Implement message transmission in loop (TRD R24-R25)
  - Call `sendHeartbeatOSC(test_ibi);`
  - Update timing: `state.lastMessageTime = currentTime;`
  - Increment counter: `state.messageCounter++;`
  - Print to serial: "Sent message #N: /heartbeat/ID VALUE" (TRD R25)
  - **Test**: Upload, verify serial shows ~1 message/second

### Component 7.8: Single Unit Testing

- [ ] **Task 8.1**: Configure firmware for testing (TRD R30)
  - Edit `WIFI_SSID` to match development WiFi network (2.4GHz only)
  - Edit `WIFI_PASSWORD` with correct password
  - Find development machine IP: `ip addr show` (Linux) or `ifconfig` (Mac)
  - Edit `SERVER_IP` to development machine IP (NOT 127.0.0.1)
  - Set `SENSOR_ID = 0` for first unit
  - **Validation**: Configuration matches network environment

- [ ] **Task 8.2**: Upload and verify compilation (TRD Section 9)
  - Connect ESP32 to computer via USB
  - Verify Tools → Port shows correct port
  - Click Upload button in Arduino IDE
  - Wait for "Hard resetting via RTS pin..." message
  - **Expected**: Compilation succeeds, upload completes
  - **Troubleshooting**: If upload fails, try holding BOOT button or reduce upload speed

- [ ] **Task 8.3**: Verify serial output (TRD Section 10.2)
  - Open Serial Monitor (115200 baud)
  - Press ESP32 reset button if no output
  - **Expected output**:
    - Startup banner with sensor ID
    - "Connecting to WiFi: [SSID]"
    - "Connected! IP: [IP_ADDRESS]"
    - "Setup complete. Starting message loop..."
    - "Sent message #1: /heartbeat/0 800"
    - Messages continuing at ~1 Hz
  - **Validation**: Serial output matches expected format

- [ ] **Task 8.4**: Test with Python receiver (TRD Section 10.2)
  - Terminal 1: Start receiver `python3 testing/osc_receiver.py --port 8000`
  - Terminal 2: Monitor ESP32 serial output
  - **Expected receiver output**:
    - "[/heartbeat/0] IBI: 800ms, BPM: 75.0"
    - Messages at ~1 Hz matching ESP32 serial output
    - Statistics every 10 seconds
    - Invalid count = 0
  - **Validation**: Receiver shows valid messages from ESP32

- [ ] **Task 8.5**: Verify LED behavior (TRD Section 10.2 Step 3)
  - During "Connecting to WiFi": LED blinks rapidly (5 Hz)
  - After "Connected!": LED solid ON
  - **Validation**: Visual confirmation of LED states

- [ ] **Task 8.6**: Run 5-minute stability test (TRD Section 10.2 Step 4)
  - Keep receiver and ESP32 running for 5+ minutes
  - Monitor for: Crashes, WiFi disconnections, message gaps
  - Check receiver statistics: Invalid messages = 0
  - **Expected**: Continuous operation, message counter incrementing
  - **Validation**: No errors over 5 minutes

### Component 7.9: Multi-Unit Testing

- [ ] **Task 9.1**: Program additional ESP32 units (TRD R31)
  - Clone firmware or use same .ino file
  - For each additional ESP32:
    - Change `SENSOR_ID` to 1, 2, or 3 (unique per unit)
    - Keep `WIFI_SSID`, `WIFI_PASSWORD`, `SERVER_IP` identical
  - Upload to each ESP32
  - Physically label units (sticker or marker) with sensor ID
  - **Validation**: Each unit programmed with unique SENSOR_ID

- [ ] **Task 9.2**: Run multi-unit integration test (TRD Section 10.3, R32-R33)
  - Start single receiver: `python3 testing/osc_receiver.py --port 8000`
  - Power 2-4 ESP32 units simultaneously
  - Let run for 5+ minutes
  - **Expected**:
    - Receiver shows messages from all sensor IDs
    - Each sensor operates independently
    - No message interference
    - Invalid message count = 0
  - **Validation**: Receiver statistics show activity for all connected sensors

- [ ] **Task 9.3**: Verify acceptance criteria (TRD Section 11)
  - Check compilation: No errors or warnings
  - Check WiFi: Connects within 30 seconds
  - Check message rate: ~1 Hz ± 10% per sensor
  - Check message format: Address `/heartbeat/[0-3]`, int32 argument, 800-999ms range
  - Check reliability: 5+ minutes without crashes
  - Check LED: Correct states during connection and operation
  - **Validation**: All acceptance criteria met

### Component 7.10: Documentation & Completion

- [ ] **Task 10.1**: Document firmware configuration in README
  - Add section to `firmware/README.md`:
    - How to find development machine IP address
    - How to configure WIFI_SSID, WIFI_PASSWORD, SERVER_IP
    - How to set unique SENSOR_ID for each unit
    - Upload procedure and troubleshooting
  - Reference TRD Section 13 (Troubleshooting)
  - **Validation**: README has clear setup instructions

- [ ] **Task 10.2**: Create configuration checklist
  - Document in README or separate `CONFIGURATION.md`:
    - Pre-upload checklist (WiFi credentials, IP address, sensor ID)
    - Verification steps (serial output, receiver test)
    - Multi-unit deployment procedure
  - **Validation**: Checklist complete and clear

- [ ] **Task 10.3**: Final validation against TRD
  - Review TRD Section 14 (Success Metrics)
  - Verify all 10 criteria met:
    1. ✅ Firmware compiles without errors
    2. ✅ Uploads to ESP32 successfully
    3. ✅ Connects to WiFi (verified by serial output)
    4. ✅ Sends OSC messages at 1 Hz
    5. ✅ Python receiver validates all messages (0 invalid)
    6. ✅ LED feedback working (blink → solid)
    7. ✅ 5-minute stability test passes
    8. ✅ Multi-unit test passes (2+ ESP32s simultaneously)
    9. ✅ Serial output clean and informative
    10. ✅ Code organized and commented
  - **Validation**: All success metrics achieved

- [ ] **Task 10.4**: Update tasks.md completion status
  - Mark Component 7 as complete
  - Note any deviations from TRD or issues encountered
  - Document firmware version and date
  - **Status**: Phase 1 firmware implementation complete

---

## Task Execution Notes

**Order**: Tasks should be completed in sequence. Each task builds on previous work.

**Testing Strategy**:
- Tasks 2.x-7.x: Incremental development with compilation checks
- Task 8.x: Single-unit validation against testing infrastructure
- Task 9.x: Multi-unit validation
- Task 10.x: Documentation and final acceptance

**Hardware Required**:
- 1-4 ESP32-WROOM-32 boards (or compatible)
- USB cables for programming
- Development machine with WiFi and Arduino IDE
- 2.4GHz WiFi network (ESP32 does not support 5GHz)

**Dependencies**:
- Components 1-5 complete (testing infrastructure ready)
- Arduino IDE installed and configured
- ESP32 board support installed
- OSC library installed

**Time Estimate**:
- Prerequisites (Tasks 0.x): 30-45 min (first time setup)
- Project structure (Tasks 1.x): 10 min
- Firmware skeleton (Tasks 2.x): 15-20 min
- WiFi function (Tasks 3.x): 30-40 min
- OSC function (Tasks 4.x): 20-30 min
- LED function (Tasks 5.x): 15-20 min
- WiFi monitoring (Tasks 6.x): 20-30 min
- Main program (Tasks 7.x): 30-40 min
- Single unit testing (Tasks 8.x): 30-45 min
- Multi-unit testing (Tasks 9.x): 30-45 min (if hardware available)
- Documentation (Tasks 10.x): 20-30 min
- **Total: 4-5 hours** (matches TRD estimate: 2-3 hours code + 1 hour testing + setup)

**Acceptance**: Component 7 complete when all tasks checked off and firmware successfully tested against Python receiver (Components 2-5) with 0 invalid messages over 5+ minutes.
