# Component 7 - Part 5: Validated & Documented

**Milestone**: Phase 1 firmware fully validated, documented, and ready for production deployment

**Reference**: `docs/p1-fw-trd.md` Sections 10-11, 14 (Validation and Acceptance Criteria)

**Estimated Time**: 45-60 minutes

**Success Criteria**: All TRD acceptance criteria met, firmware documented, multi-unit testing complete (if hardware available)

---

## Prerequisites

Before starting Part 5:
- ✅ Part 1 complete: PlatformIO environment working
- ✅ Part 2 complete: Firmware skeleton compiles
- ✅ Part 3 complete: ESP32 connects to WiFi
- ✅ Part 4 complete: Messages sending to receiver at ~1 Hz

---

## Extended Stability Testing

- [ ] **Task 5.1**: Run 5-minute stability test (TRD Section 10.2 Step 4)
  - Ensure ESP32 running with WiFi connected
  - Ensure Python receiver running: `python3 testing/osc_receiver.py --port 8000`
  - Monitor both for 5 minutes minimum
  - **Watch for**:
    - No WiFi disconnections in ESP32 serial output
    - No message gaps > 2 seconds
    - Receiver invalid count stays at 0
    - Message counter incrementing continuously
    - No ESP32 resets (startup banner reappearing)
  - **Expected ESP32**: "Sent message #1" through "Sent message #300+" (at 1 Hz)
  - **Expected receiver**: 300+ total messages, 0 invalid, continuous statistics updates
  - **Status**: 5-minute stability test passed

- [ ] **Task 5.2**: Verify message rate accuracy
  - From receiver statistics after 5 minutes:
  - **Expected**: ~300 messages (5 min × 60 sec × 1 msg/sec = 300)
  - **Acceptable range**: 290-310 messages (±10ms timing variance acceptable)
  - **Status**: Message rate verified

- [ ] **Task 5.3**: Verify LED stability
  - During 5-minute test, verify LED:
    - Stays solid ON entire time (doesn't blink after connection)
    - No flickering or dimming
    - Indicates stable WiFi connection
  - **Status**: LED behavior stable

- [ ] **Task 5.3a**: Memory leak testing (TRD Section 11.4)
  - **Purpose**: Verify RAM usage remains stable over time (no memory leaks)
  - Add temporary debug output to `loop()` function:
    ```cpp
    void loop() {
        static unsigned long lastMemCheck = 0;

        // Print free heap every 60 seconds
        if (millis() - lastMemCheck >= 60000) {
            lastMemCheck = millis();
            Serial.print("Free heap: ");
            Serial.print(ESP.getFreeHeap());
            Serial.println(" bytes");
        }

        // ... rest of loop() code
    }
    ```
  - Compile and upload: `pio run --target upload`
  - Monitor serial output: `pio device monitor`
  - **Expected behavior**:
    - Free heap should be ~280,000-295,000 bytes (typical for ESP32)
    - Value should remain stable (±1000 bytes acceptable)
    - Should NOT decrease continuously over 10+ minutes
  - **Example good output**:
    ```
    Free heap: 287432 bytes  [minute 1]
    Free heap: 287424 bytes  [minute 2]
    Free heap: 287436 bytes  [minute 3]
    Free heap: 287428 bytes  [minute 4]
    ```
  - **Example bad output (memory leak)**:
    ```
    Free heap: 287432 bytes  [minute 1]
    Free heap: 285120 bytes  [minute 2]
    Free heap: 282808 bytes  [minute 3]
    Free heap: 280496 bytes  [minute 4]  <- Decreasing = leak!
    ```
  - Let run for 10+ minutes, verify heap remains stable
  - After testing, remove debug code from `loop()`
  - **Status**: Memory leak test passed (stable heap)

---

## Multi-Unit Testing (Optional)

**Note**: Skip this section if you have only 1 ESP32. Multi-unit testing can be done later when additional hardware is available.

- [ ] **Task 5.4**: Program second ESP32 with SENSOR_ID=1 (TRD R31)
  - Connect second ESP32 via USB
  - Edit `src/main.cpp`: Change `SENSOR_ID` from 0 to 1
  - Keep WIFI_SSID, WIFI_PASSWORD, SERVER_IP identical to first unit
  - Compile: `pio run`
  - Upload: `pio run --target upload`
  - **Status**: Second ESP32 programmed with SENSOR_ID=1

- [ ] **Task 5.5**: Label units physically
  - Use sticker, marker, or label maker
  - Mark first ESP32: "Sensor 0"
  - Mark second ESP32: "Sensor 1"
  - **Status**: Units labeled

- [ ] **Task 5.6**: Run multi-unit integration test (TRD R32-R33)
  - Start single receiver: `python3 testing/osc_receiver.py --port 8000`
  - Power both ESP32 units (via USB or battery)
  - Let run for 5+ minutes
  - **Expected receiver output**:
    ```
    [/heartbeat/0] IBI: 800ms, BPM: 75.0
    [/heartbeat/1] IBI: 800ms, BPM: 75.0
    [/heartbeat/0] IBI: 801ms, BPM: 74.9
    [/heartbeat/1] IBI: 801ms, BPM: 74.9
    ...

    --- Statistics (10.0s) ---
    Total: 20, Valid: 20, Invalid: 0
    Sensor 0: 10 messages, Avg IBI: 805ms, Avg BPM: 74.5
    Sensor 1: 10 messages, Avg IBI: 805ms, Avg BPM: 74.5
    ```
  - **Verify**: Both sensor 0 and sensor 1 show activity
  - **Verify**: Invalid count = 0
  - **Verify**: No message interference
  - **Status**: Multi-unit test passed (or skipped if only 1 unit)

- [ ] **Task 5.7**: Test with 4 units (if available)
  - Repeat Task 5.4 for SENSOR_ID=2 and SENSOR_ID=3
  - Run all 4 units simultaneously
  - **Expected**: Receiver shows all 4 sensors active, 0 invalid
  - **Status**: 4-unit test passed (or skipped)

---

## Acceptance Criteria Validation

- [ ] **Task 5.8**: Verify TRD Section 11 acceptance criteria
  - Review TRD Section 11 (Acceptance Criteria)
  - Check each criterion:

**Compilation (Section 11.1):**
- [ ] ✅ Firmware compiles without errors
- [ ] ✅ Firmware compiles without warnings (or only benign warnings)
- [ ] ✅ Binary size < 500KB (check `pio run` output)

**Runtime Behavior (Section 11.2):**
- [ ] ✅ Connects to WiFi within 30 seconds
- [ ] ✅ Prints IP address to serial
- [ ] ✅ Sends OSC messages at ~1 Hz (±10%)
- [ ] ✅ Messages received by Python receiver
- [ ] ✅ 0 invalid messages in receiver
- [ ] ✅ Runs for 5+ minutes without crashes or resets
- [ ] ✅ LED indicates connection status correctly

**Message Format (Section 11.3):**
- [ ] ✅ Address pattern: `/heartbeat/[0-3]`
- [ ] ✅ Argument type: int32
- [ ] ✅ Argument value: 800-999ms range
- [ ] ✅ Message size: 24 bytes (verify in receiver)

**Reliability (Section 11.4):**
- [ ] ✅ Handles WiFi connection failure (error state, not crash)
- [ ] ✅ No memory leaks over 5+ minutes (stable RAM usage)
- [ ] ✅ Consistent performance (no degradation)
- [ ] ✅ Stable message rate (not speeding up or slowing down)

- **Status**: All TRD acceptance criteria met

---

## Documentation

- [ ] **Task 5.9**: Create firmware README
  - Create file: `/home/user/corazonn/firmware/README.md`
  - Content:
    ```markdown
    # Heartbeat Installation - Phase 1 Firmware

    ESP32 firmware for heartbeat sensor installation. Sends OSC messages over WiFi.

    ## Requirements

    - ESP32-WROOM-32 or compatible
    - 2.4GHz WiFi network (ESP32 does not support 5GHz)
    - Development machine running Python OSC receiver
    - PlatformIO CLI installed

    ## Configuration

    Before uploading firmware, edit `src/main.cpp` and configure:

    1. **WiFi Credentials** (lines ~30-32):
       ```cpp
       const char* WIFI_SSID = "your-network-name";
       const char* WIFI_PASSWORD = "your-password";
       ```

    2. **Server IP** (line ~33):
       - Find your development machine's IP address:
         - Linux: `ip addr show` (look for wlan0 or eth0)
         - macOS: System Preferences → Network → WiFi → Advanced → TCP/IP
         - Windows: `ipconfig` (look for IPv4 Address)
       - Update SERVER_IP:
         ```cpp
         const IPAddress SERVER_IP(192, 168, 1, 100);  // YOUR IP HERE
         ```
       - **Do NOT use 127.0.0.1** (that's ESP32's own localhost)

    3. **Sensor ID** (line ~39):
       ```cpp
       const int SENSOR_ID = 0;  // 0, 1, 2, or 3 for each unit
       ```
       - Use unique ID for each ESP32 (0-3)

    ## Compilation & Upload

    ```bash
    # Navigate to project directory
    cd /home/user/corazonn/firmware/heartbeat_phase1

    # Compile
    pio run

    # Upload to ESP32 (connected via USB)
    pio run --target upload

    # Monitor serial output
    pio device monitor
    ```

    ## Expected Behavior

    1. LED blinks rapidly during WiFi connection (~5 seconds)
    2. LED solid ON after WiFi connected
    3. Serial output shows:
       ```
       === Heartbeat Installation - Phase 1 ===
       Sensor ID: 0
       Connecting to WiFi: your-network
       Connected! IP: 192.168.X.X
       Setup complete. Starting message loop...
       Sent message #1: /heartbeat/0 800
       ```
    4. Messages sent at 1 Hz to configured server

    ## Troubleshooting

    See comprehensive troubleshooting in `/home/user/corazonn/docs/p1-fw-trd.md` Section 13.

    **Common issues:**
    - **Won't connect to WiFi**: Check SSID/password, ensure 2.4GHz network
    - **Receiver shows no messages**: Check SERVER_IP matches dev machine, check firewall
    - **Upload fails**: Hold BOOT button during upload, check USB cable

    ## Testing

    1. Start Python receiver:
       ```bash
       python3 /home/user/corazonn/testing/osc_receiver.py --port 8000
       ```

    2. Upload firmware and monitor

    3. Verify receiver shows valid messages (0 invalid)

    ## Multi-Unit Deployment

    For multiple ESP32 units:
    1. Program each with unique SENSOR_ID (0, 1, 2, or 3)
    2. Keep WiFi credentials and SERVER_IP identical
    3. Label units physically (sticker/marker)
    4. All units send to same receiver

    ## Technical Reference

    Full implementation details: `/home/user/corazonn/docs/p1-fw-trd.md`

    ## Status

    **Phase 1**: WiFi + OSC messaging ✅ Complete
    **Phase 2**: Sensor integration (TBD)
    ```
  - Save file
  - **Status**: firmware/README.md created

- [ ] **Task 5.10**: Create deployment checklist
  - Add section to firmware/README.md:
    ```markdown
    ## Pre-Deployment Checklist

    Before deploying each ESP32 unit:

    - [ ] PlatformIO CLI installed and working
    - [ ] ESP32 platform installed (`pio pkg list --global --only-platforms`)
    - [ ] Testing infrastructure ready (Python receiver tested)
    - [ ] WiFi credentials configured in src/main.cpp
    - [ ] SERVER_IP set to development machine IP (not 127.0.0.1)
    - [ ] SENSOR_ID set uniquely for each unit (0-3)
    - [ ] Firmware compiles without errors (`pio run`)
    - [ ] Firmware uploads successfully (`pio run --target upload`)
    - [ ] ESP32 connects to WiFi (serial shows "Connected! IP: X.X.X.X")
    - [ ] LED blinks then solid (visual confirmation)
    - [ ] Receiver shows valid messages (0 invalid)
    - [ ] 5-minute stability test passed
    - [ ] Unit physically labeled with SENSOR_ID
    - [ ] Deployment date and version documented

    ## Version History

    - **v1.0 Phase 1** (YYYY-MM-DD): Initial WiFi + OSC implementation
    ```
  - **Status**: Deployment checklist added

- [ ] **Task 5.11**: Update tasks.md completion status
  - Edit `/home/user/corazonn/docs/tasks.md`
  - Add Component 7 completion entry after Component 6:
    ```markdown
    ## Component 7: Phase 1 Firmware Implementation

    - [x] **Part 1**: Environment ready (PlatformIO setup)
    - [x] **Part 2**: Structure compiles (firmware skeleton)
    - [x] **Part 3**: WiFi connects (ESP32 connects to network)
    - [x] **Part 4**: Messages send (OSC to receiver)
    - [x] **Part 5**: Validated & documented (acceptance criteria met)

    **Status**: Completed on YYYY-MM-DD
    **Toolchain**: PlatformIO CLI (v3.0 TRD)
    **Outcome**: Phase 1 firmware fully functional, all acceptance criteria met
    ```
  - **Status**: tasks.md updated

---

## Final Milestone Checkpoint

**Phase 1 Firmware Complete Checklist**:

**Compilation & Structure:**
- [ ] Firmware compiles without errors (`pio run`)
- [ ] All includes present (Arduino.h, WiFi.h, WiFiUdp.h, OSCMessage.h)
- [ ] Configuration constants defined (network, hardware, system)
- [ ] Data structures complete (SystemState, global objects)
- [ ] All functions implemented (connectWiFi, sendHeartbeatOSC, updateLED, checkWiFi, setup, loop)

**WiFi Functionality:**
- [ ] Connects to 2.4GHz WiFi network
- [ ] Connection timeout handled (30 seconds)
- [ ] Connection status monitored every 5 seconds
- [ ] Reconnection automatic if WiFi drops
- [ ] LED indicates connection status (blink → solid)

**OSC Messaging:**
- [ ] OSC messages constructed correctly
- [ ] Address pattern: /heartbeat/[SENSOR_ID]
- [ ] Argument type: int32
- [ ] UDP transmission working
- [ ] Message rate ~1 Hz

**Testing & Validation:**
- [ ] 5-minute stability test passed
- [ ] 0 invalid messages in receiver
- [ ] No WiFi disconnections
- [ ] No ESP32 resets
- [ ] LED behavior stable
- [ ] Multi-unit testing passed (if applicable)

**Documentation:**
- [ ] firmware/README.md created
- [ ] Configuration instructions clear
- [ ] Deployment checklist included
- [ ] Troubleshooting cross-referenced
- [ ] tasks.md updated

**TRD Compliance:**
- [ ] All requirements R1-R33 implemented
- [ ] All acceptance criteria met (Section 11)
- [ ] All success metrics achieved (Section 14)

**What You've Built**:
- Complete Phase 1 ESP32 firmware
- WiFi connection with automatic reconnection
- OSC heartbeat message transmission
- LED status indication
- Comprehensive documentation
- Multi-unit deployment capability
- Production-ready Phase 1 implementation

**Ready for**: Phase 2 firmware (sensor integration) when hardware arrives

**Total Time Across All Parts**: ______ hours

**Overall Issues Encountered**: _______________________

---

## Deployment Notes

**For Production Deployment:**

1. **Hardware Preparation**:
   - 1-4 ESP32-WROOM-32 boards
   - USB cables for initial programming
   - Battery packs for standalone operation (optional)
   - Labels/stickers for unit identification

2. **Network Setup**:
   - 2.4GHz WiFi network dedicated to installation (recommended)
   - Server machine running Python OSC receiver
   - Server machine IP address static or reserved (DHCP reservation)

3. **Programming Workflow**:
   - Program unit 0, label, test
   - Program unit 1, label, test
   - Program unit 2, label, test
   - Program unit 3, label, test
   - Multi-unit test all simultaneously

4. **Verification**:
   - Each unit connects independently
   - Receiver shows all sensor IDs
   - Invalid message count = 0
   - Stable operation for 30+ minutes

5. **Known Limitations (Phase 1)**:
   - No actual sensor input (test values only)
   - No beat detection algorithm
   - No watchdog timer
   - No OTA updates
   - No power management
   - See TRD Section 12 for complete list

---

## Success Metrics Achieved

Per TRD Section 14:

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

**Congratulations! Phase 1 firmware implementation complete.**

---

**Next Steps**: Await Phase 2 TRD for sensor integration (optical pulse sensors, beat detection, IBI calculation)
