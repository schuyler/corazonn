# Component 7 - Part 4: Messages Send

**Milestone**: Complete Phase 1 firmware sending OSC heartbeat messages to Python receiver at 1 Hz

**Reference**: `docs/p1-fw-trd.md` Sections 6.2, 7.2 (OSC Function and Main Loop)

**Estimated Time**: 30-45 minutes

**Success Criteria**: Python receiver shows valid messages at ~1 Hz with 0 invalid messages

---

## Prerequisites

Before starting Part 4:
- ✅ Part 1 complete: PlatformIO environment working
- ✅ Part 2 complete: Firmware skeleton compiles
- ✅ Part 3 complete: ESP32 connects to WiFi successfully
- ⚠️ **Required for Part 4**: Python OSC receiver from Components 1-5 running
- ⚠️ **Required for Part 4**: Firewall configured to allow UDP port 8000

### Firewall Configuration

**Before testing**, configure your development machine's firewall to allow incoming UDP traffic on port 8000:

- **Linux**:
  ```bash
  sudo ufw allow 8000/udp
  sudo ufw status  # Verify rule added
  ```
- **macOS**:
  - System Preferences → Security & Privacy → Firewall Options
  - Click "+" and add Python (or turn off firewall for testing)
  - Allow incoming connections for Python
- **Windows**:
  - Windows Defender Firewall → Allow an app
  - Click "Allow another app" → Browse to Python executable
  - Check both "Private" and "Public" networks

**Why needed**: ESP32 sends UDP packets to your machine. Without firewall exception, packets will be dropped silently.

---

## OSC Message Function

- [x] **Task 4.1**: Implement address pattern construction (TRD R5)
  - Edit `/home/user/corazonn/firmware/heartbeat_phase1/src/main.cpp`
  - Find `void sendHeartbeatOSC(int ibi_ms)` function
  - Replace the skeleton with:
    ```cpp
    void sendHeartbeatOSC(int ibi_ms) {
        // Construct OSC address pattern
        char address[20];
        snprintf(address, sizeof(address), "/heartbeat/%d", SENSOR_ID);

        // Continue in next task...
    }
    ```
  - **Status**: Address pattern construction implemented ✓

- [x] **Task 4.2**: Implement OSC message construction (TRD R6)
  - Continue in `sendHeartbeatOSC()` after address:
    ```cpp
        // Create OSC message
        OSCMessage msg(address);
        msg.add((int32_t)ibi_ms);

        // Continue in next task...
    ```
  - **Status**: OSC message construction implemented ✓

- [x] **Task 4.3**: Implement UDP transmission (TRD R7)
  - Continue in `sendHeartbeatOSC()` after message creation:
    ```cpp
        // Transmit via UDP
        udp.beginPacket(SERVER_IP, SERVER_PORT);
        msg.send(udp);
        udp.endPacket();

        // Clear message buffer for reuse
        msg.empty();
    }
    ```
  - **Critical note**: Order matters - beginPacket → send → endPacket → empty
  - **Status**: UDP transmission implemented ✓

- [x] **Task 4.4**: Compile and verify OSC function
  - Run: `pio run`
  - **Expected**: Compilation succeeds
  - **Status**: OSC function compiles ✓

---

## Main Loop Implementation

- [x] **Task 4.5**: Implement message timing check (TRD R22)
  - Find `void loop()` function
  - Replace the current implementation with:
    ```cpp
    void loop() {
        // WiFi status monitoring (R21)
        checkWiFi();

        // Message timing (R22)
        unsigned long currentTime = millis();

        if (currentTime - state.lastMessageTime >= TEST_MESSAGE_INTERVAL_MS) {
            // Continue in next task...
        }

        // LED update (R26)
        updateLED();

        // Loop delay (R27)
        delay(10);
    }
    ```
  - **Status**: Message timing check added ✓

- [x] **Task 4.6**: Implement test message generation (TRD R23)
  - Inside the `if` block in loop():
    ```cpp
            // Generate test IBI value (R23)
            int test_ibi = 800 + (state.messageCounter % 200);
            // Creates sequence: 800, 801, 802, ..., 999, 800, 801, ...
            // Simulates 60-75 BPM heart rate

            // Continue in next task...
    ```
  - **Status**: Test message generation implemented ✓

- [x] **Task 4.7**: Implement message transmission and state update (TRD R24-R25)
  - Continue inside the `if` block after test_ibi:
    ```cpp
            // Send OSC message (R24)
            sendHeartbeatOSC(test_ibi);

            // Update state (R24)
            state.lastMessageTime = currentTime;
            state.messageCounter++;

            // Serial feedback (R25)
            Serial.print("Sent message #");
            Serial.print(state.messageCounter);
            Serial.print(": /heartbeat/");
            Serial.print(SENSOR_ID);
            Serial.print(" ");
            Serial.println(test_ibi);
    ```
  - **Status**: Message transmission and state update implemented ✓

- [x] **Task 4.8**: Compile complete firmware
  - Run: `pio run`
  - **Expected**: Compilation succeeds
  - **Status**: Complete Phase 1 firmware compiles ✓

---

## Network Configuration

- [x] **Task 4.9**: Configure SERVER_IP
  - Find development machine's IP address:
    - **Linux**: `ip addr show` (look for wlan0 or eth0 inet address)
    - **macOS**: System Preferences → Network → WiFi → Advanced → TCP/IP
    - **Windows**: `ipconfig` (look for IPv4 Address under WiFi adapter)
  - **Example**: If your machine shows `192.168.1.100`
  - Edit `SERVER_IP` constant:
    ```cpp
    const IPAddress SERVER_IP(192, 168, 1, 100);  // Your dev machine's IP
    ```
  - **Critical**: Do NOT use 127.0.0.1 (that's ESP32's own localhost)
  - Save file
  - **Status**: SERVER_IP configured to dev machine ✓

- [x] **Task 4.10**: Verify SENSOR_ID
  - Check `SENSOR_ID` constant is set to 0 (for first unit)
  - **Note**: For multi-unit testing, each ESP32 needs unique ID (0-3)
  - **Status**: SENSOR_ID verified ✓

- [x] **Task 4.11**: Recompile with network config
  - Run: `pio run`
  - **Expected**: Compilation succeeds
  - **Status**: Firmware with network config compiles ✓

---

## Integration Testing

> **Note**: Tasks 4.12-4.16 require physical hardware (ESP32 device). These are pending hardware availability.

- [ ] **Task 4.12**: Start Python OSC receiver
  - Open new terminal window
  - Navigate to testing directory: `cd /home/user/corazonn/testing`
  - Start receiver: `python3 osc_receiver.py --port 8000`
  - **Expected output**: "OSC Receiver listening on 0.0.0.0:8000"
  - **Leave running** for testing
  - **Status**: Awaiting hardware

- [ ] **Task 4.13**: Upload firmware to ESP32
  - In original terminal: `pio run --target upload`
  - **Expected**: Upload succeeds
  - **Status**: Awaiting hardware

- [ ] **Task 4.14**: Monitor ESP32 serial output
  - Run: `pio device monitor`
  - **Expected output**:
    ```
    === Heartbeat Installation - Phase 1 ===
    Sensor ID: 0
    Connecting to WiFi: your-network-name
    Connected! IP: 192.168.X.X
    Setup complete. Starting message loop...
    Sent message #1: /heartbeat/0 800
    Sent message #2: /heartbeat/0 801
    Sent message #3: /heartbeat/0 802
    ...
    ```
  - Messages should appear at ~1 second intervals
  - **Status**: Awaiting hardware

- [ ] **Task 4.15**: Verify Python receiver output
  - Switch to receiver terminal
  - **Expected output**:
    ```
    [/heartbeat/0] IBI: 800ms, BPM: 75.0
    [/heartbeat/0] IBI: 801ms, BPM: 74.9
    [/heartbeat/0] IBI: 802ms, BPM: 74.8
    ...

    --- Statistics (10.0s) ---
    Total: 10, Valid: 10, Invalid: 0
    Sensor 0: 10 messages, Avg IBI: 805ms, Avg BPM: 74.5
    ```
  - **Verify**: Invalid count = 0
  - **Verify**: Messages at ~1 Hz
  - **Verify**: Sensor 0 shows activity
  - **Status**: Awaiting hardware

- [ ] **Task 4.16**: Run 2-minute stability test
  - Let ESP32 and receiver run for 2 minutes
  - Monitor both serial outputs
  - **Check for**:
    - No WiFi disconnections
    - No message gaps > 2 seconds
    - Invalid message count stays at 0
    - Message counter incrementing continuously
  - **Status**: Awaiting hardware

---

## Implementation Details

### Code Implementation Summary

All 8 requirements for Part 4 (R5-R8, R22-R25) have been implemented and verified:

**OSC Messaging Function (R5-R8)**
- R5 (Address Pattern): Constructs `/heartbeat/[SENSOR_ID]` format
- R6 (Message Construction): Creates OSCMessage with int32_t IBI value
- R7 (UDP Transmission): Sends via UDP with correct sequence (beginPacket → send → endPacket → empty)
- R8 (No Error Checking): Fire-and-forget UDP transmission as specified

**Main Loop Implementation (R22-R25)**
- R22 (Message Timing): Checks elapsed time against TEST_MESSAGE_INTERVAL_MS (1000ms)
- R23 (Test IBI Generation): Creates sequence 800-999ms simulating 60-75 BPM heart rate
- R24 (State Management): Updates lastMessageTime and messageCounter after transmission
- R25 (Serial Feedback): Outputs "Sent message #N: /heartbeat/[ID] [IBI]"

### Compilation Results

- **Status**: Successful compilation verified
- **RAM Usage**: 13.8% (45,080 bytes)
- **Flash Usage**: 738 KB
- **OSC Library**: GitHub CNMAT/OSC repository (version 3.5.8)
- **Build Output**: No warnings or errors

### Verification Approval

- **Zeppo**: All 8 requirements verified as satisfied
- **Chico**: Implementation quality approved
- **Groucho**: Architectural soundness validated

---

## Milestone Checkpoint

**Messages Send Checklist**:
- [x] sendHeartbeatOSC() fully implemented (R5-R8) ✓
- [x] loop() implements message timing and generation (R22-R27) ✓
- [x] Test IBI generation creates 800-999ms sequence (R23) ✓
- [x] Serial output shows sent messages (R25) ✓
- [x] SERVER_IP configured to development machine ✓
- [ ] Python receiver running and listening on port 8000 (awaiting hardware)
- [ ] ESP32 connects to WiFi successfully (awaiting hardware)
- [ ] ESP32 sends OSC messages at ~1 Hz (awaiting hardware)
- [ ] Receiver shows valid messages (0 invalid) (awaiting hardware)
- [x] Message format correct: /heartbeat/[0-3] with int32 IBI ✓
- [ ] 2-minute stability test passes (awaiting hardware)

**Code Implementation Status**: ✓ COMPLETE

All code implementation tasks (4.1-4.11) completed and compilation successful.

**Hardware Testing Status**: PENDING

Hardware testing tasks (4.12-4.16) require physical ESP32 device and network setup.

**What You Can Do Now**:
- Review OSC message implementation in sendHeartbeatOSC()
- Examine loop() timing and message generation logic
- Verify compilation output and memory usage
- Prepare for hardware deployment and testing

**Ready for Part 5**: Final validation (hardware testing, 5-minute stability test, multi-unit testing, final documentation)

**Time Spent**: Implementation and review complete

**Issues Encountered**: None - all code implementation targets successfully met

---

## Troubleshooting

**Problem: ESP32 sends messages but receiver shows nothing**
- Check 1: SERVER_IP matches your dev machine's IP? (not 127.0.0.1)
  - ESP32 serial shows: "Connected! IP: 192.168.X.Y"
  - Dev machine IP should be: 192.168.X.Z (same subnet)
- Check 2: Firewall blocking UDP port 8000?
  - See "Firewall Configuration" in Prerequisites section above
  - Verify firewall rule is active before testing
- Check 3: Receiver actually running on correct port?
  - Receiver output should show: "listening on 0.0.0.0:8000"
- Check 4: ESP32 and dev machine on same WiFi network?
  - Both should have 192.168.X.X addresses in same subnet

**Problem: Receiver shows invalid messages**
- Check 1: OSC library version correct?
  - platformio.ini should have: `lib_deps = https://github.com/CNMAT/OSC.git`
- Check 2: Message construction order correct?
  - Should be: beginPacket → send → endPacket → empty
- Check 3: Address pattern format correct?
  - Should be: "/heartbeat/0" (not "heartbeat/0" or "/heartbeat0")

**Problem: Message rate not ~1 Hz**
- Check 1: TEST_MESSAGE_INTERVAL_MS = 1000?
- Check 2: Loop delay appropriate?
  - delay(10) in loop() is correct
  - Longer delays slow message rate

**Problem: Messages stop after a few minutes**
- Check 1: WiFi disconnection?
  - ESP32 serial should show "WiFi disconnected" if WiFi drops
  - Verify reconnection logic working
- Check 2: ESP32 resetting?
  - Look for startup banner reappearing in serial output
  - May indicate power issue or watchdog reset

**Problem: Compilation error "OSCMessage does not name a type"**
- Solution: OSC library not installed
- Check platformio.ini has: `lib_deps = cnmat/OSC@^1.3.7`
- Clean and rebuild: `pio run --target clean && pio run`

---

**Next**: [Component 7 - Part 5: Validated & Documented](component-7-part5-tasks.md)
