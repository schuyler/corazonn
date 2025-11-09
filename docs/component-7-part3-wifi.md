# Component 7 - Part 3: WiFi Connects

**Milestone**: ESP32 successfully connects to WiFi network with LED status indication

**Reference**: `docs/p1-fw-trd.md` Sections 6.1, 6.3, 6.4, 7.1 (WiFi Functions and Setup)

**Estimated Time**: 45-60 minutes

**Success Criteria**: ESP32 connects to WiFi, LED blinks during connection then stays solid, serial output shows "Connected! IP: X.X.X.X"

---

## Prerequisites

Before starting Part 3:
- ✅ Part 1 complete: PlatformIO environment working
- ✅ Part 2 complete: Firmware skeleton compiles
- ⚠️ **Required for Part 3**: Physical ESP32 hardware connected via USB
- ⚠️ **Required for Part 3**: 2.4GHz WiFi network accessible (ESP32 doesn't support 5GHz)

---

## WiFi Connection Function

- [ ] **Task 3.1**: Implement WiFi initialization (TRD R1)
  - Edit `/home/user/corazonn/firmware/heartbeat_phase1/src/main.cpp`
  - Find `bool connectWiFi()` function
  - Replace the skeleton with:
    ```cpp
    bool connectWiFi() {
        WiFi.mode(WIFI_STA);
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

        Serial.print("Connecting to WiFi: ");
        Serial.println(WIFI_SSID);

        unsigned long startTime = millis();

        // Continue in next task...
        return false;  // Temporary
    }
    ```
  - **Status**: WiFi initialization implemented

- [ ] **Task 3.2**: Implement connection wait loop (TRD R2)
  - Continue in `connectWiFi()` function after startTime:
    ```cpp
        // Connection wait loop with timeout
        while (WiFi.status() != WL_CONNECTED) {
            if (millis() - startTime >= WIFI_TIMEOUT_MS) {
                Serial.println("WiFi connection timeout");
                return false;
            }

            // Blink LED during connection (5 Hz)
            digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
            delay(100);
        }

        // Continue in next task...
    ```
  - **Status**: Connection wait loop implemented

- [ ] **Task 3.3**: Implement success behavior (TRD R3)
  - Continue in `connectWiFi()` after the while loop:
    ```cpp
        // Connection successful
        state.wifiConnected = true;
        digitalWrite(STATUS_LED_PIN, HIGH);  // Solid ON

        Serial.print("Connected! IP: ");
        Serial.println(WiFi.localIP());

        return true;
    }
    ```
  - **Status**: Success behavior implemented

- [ ] **Task 3.3a**: Validate complete connectWiFi() assembly
  - **Critical**: Verify the complete function was assembled correctly across Tasks 3.1-3.3
  - Review entire `connectWiFi()` function in main.cpp
  - **Expected structure**:
    1. WiFi.mode() and WiFi.begin() calls (from Task 3.1)
    2. Complete while loop with timeout and LED blink (from Task 3.2)
    3. Success behavior with return true (from Task 3.3)
    4. No "Continue in next task..." comments remaining
    5. No "return false; // Temporary" in the middle of the function
  - **Common error**: Forgetting to remove temporary return statement from Task 3.1
  - **If assembly incorrect**: Go back and verify each section was added properly
  - **Status**: Complete connectWiFi() function validated

- [ ] **Task 3.4**: Compile and verify WiFi function
  - Run: `pio run`
  - **Expected**: Compilation succeeds
  - **Status**: WiFi function compiles

---

## LED Status Function

- [ ] **Task 3.5**: Implement updateLED() function (TRD R9-R11)
  - Find `void updateLED()` function
  - Replace the skeleton with:
    ```cpp
    void updateLED() {
        if (!state.wifiConnected) {
            // Blink at 5Hz while not connected
            digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
        } else {
            // Solid ON when connected
            digitalWrite(STATUS_LED_PIN, HIGH);
        }
    }
    ```
  - **Status**: updateLED() implemented

- [ ] **Task 3.6**: Compile and verify LED function
  - Run: `pio run`
  - **Expected**: Compilation succeeds
  - **Status**: LED function compiles

---

## WiFi Monitoring Function

- [ ] **Task 3.7**: Implement checkWiFi() function (TRD R12-R14)
  - Find `void checkWiFi()` function
  - Replace the skeleton with:
    ```cpp
    void checkWiFi() {
        static unsigned long lastCheckTime = 0;

        // Rate limit to every 5 seconds
        if (millis() - lastCheckTime < 5000) {
            return;
        }

        lastCheckTime = millis();

        // Check WiFi status
        if (WiFi.status() != WL_CONNECTED) {
            state.wifiConnected = false;
            Serial.println("WiFi disconnected, reconnecting...");
            WiFi.reconnect();  // Non-blocking
        } else {
            state.wifiConnected = true;
        }
    }
    ```
  - **Status**: checkWiFi() implemented

- [ ] **Task 3.8**: Compile and verify WiFi monitoring
  - Run: `pio run`
  - **Expected**: Compilation succeeds
  - **Status**: WiFi monitoring compiles

---

## Update Setup Function

- [ ] **Task 3.9**: Integrate WiFi connection into setup() (TRD R15-R20)
  - Find `void setup()` function
  - Replace the skeleton with:
    ```cpp
    void setup() {
        // Serial initialization (R15)
        Serial.begin(115200);
        delay(100);

        // Startup banner (R16)
        Serial.println("\n=== Heartbeat Installation - Phase 1 ===");
        Serial.print("Sensor ID: ");
        Serial.println(SENSOR_ID);

        // GPIO configuration (R17)
        pinMode(STATUS_LED_PIN, OUTPUT);
        digitalWrite(STATUS_LED_PIN, LOW);

        // WiFi connection (R18)
        state.wifiConnected = connectWiFi();

        if (!state.wifiConnected) {
            Serial.println("ERROR: WiFi connection failed");
            Serial.print("WiFi status code: ");
            Serial.println(WiFi.status());
            Serial.println("Possible causes:");
            Serial.println("  - Wrong SSID or password");
            Serial.println("  - Network is 5GHz (ESP32 requires 2.4GHz)");
            Serial.println("  - Out of range");
            Serial.println("  - Router offline");
            Serial.println("Entering error state (rapid blink)...");

            // Enter error state: blink rapidly forever
            while (true) {
                digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
                delay(100);
            }
        }

        // UDP initialization (R19)
        udp.begin(0);  // Ephemeral port

        // Completion message (R20)
        Serial.println("Setup complete. Starting message loop...");
        state.lastMessageTime = millis();
    }
    ```
  - **Status**: setup() integrated with WiFi

- [ ] **Task 3.10**: Update loop() to call WiFi monitoring
  - Find `void loop()` function
  - Replace the skeleton with:
    ```cpp
    void loop() {
        // WiFi status monitoring (R21)
        checkWiFi();

        // LED update (R26)
        updateLED();

        // Loop delay (R27)
        delay(10);
    }
    ```
  - **Status**: loop() calls WiFi functions

- [ ] **Task 3.11**: Compile complete WiFi firmware
  - Run: `pio run`
  - **Expected**: Compilation succeeds
  - **Status**: Complete WiFi firmware compiles

---

## Hardware Testing

- [ ] **Task 3.12**: Configure WiFi credentials
  - Edit `WIFI_SSID` constant to match your 2.4GHz WiFi network name
  - Edit `WIFI_PASSWORD` constant with correct password
  - **Verify**: SSID is case-sensitive and exact match
  - **Verify**: Password is correct (test on phone/laptop first if unsure)
  - Save file
  - **Status**: WiFi credentials configured

- [ ] **Task 3.13**: Upload firmware to ESP32
  - Ensure ESP32 connected via USB
  - Run: `pio run --target upload`
  - **Expected**: Upload completes, "Hard resetting via RTS pin..."
  - **If fails**: Try holding BOOT button during upload
  - **Status**: Firmware uploaded

- [ ] **Task 3.14**: Monitor serial output during connection
  - Run: `pio device monitor`
  - **Expected output**:
    ```
    === Heartbeat Installation - Phase 1 ===
    Sensor ID: 0
    Connecting to WiFi: your-network-name
    Connected! IP: 192.168.X.X
    Setup complete. Starting message loop...
    ```
  - **Note**: Watch LED - should blink during "Connecting" then solid ON after "Connected!"
  - **Status**: WiFi connection successful

- [ ] **Task 3.15**: Verify LED behavior
  - During boot to "Connected!": LED blinks rapidly (~5 Hz)
  - After "Connected!": LED solid ON continuously
  - **Status**: LED behavior correct

- [ ] **Task 3.16**: Test WiFi persistence
  - Let ESP32 run for 2-3 minutes
  - Verify no "WiFi disconnected" messages in serial output
  - Verify LED stays solid ON (doesn't blink again)
  - **Status**: WiFi connection stable

- [ ] **Task 3.17**: Test WiFi reconnection (optional)
  - While ESP32 running, disable WiFi router or move ESP32 out of range
  - **Expected serial**: "WiFi disconnected, reconnecting..."
  - **Expected LED**: Starts blinking again
  - Re-enable WiFi router or move ESP32 back in range
  - **Expected**: Reconnects within 30 seconds, LED solid ON again
  - Exit monitor: Ctrl+C
  - **Status**: Reconnection tested (or skipped)

---

## Milestone Checkpoint

**WiFi Connects Checklist**:
- [ ] connectWiFi() fully implemented (R1-R4)
- [ ] updateLED() fully implemented (R9-R11)
- [ ] checkWiFi() fully implemented (R12-R14)
- [ ] setup() integrated with WiFi connection (R15-R20)
- [ ] loop() calls WiFi monitoring and LED update (R21, R26, R27)
- [ ] WiFi credentials configured correctly
- [ ] Firmware uploads to ESP32 successfully
- [ ] ESP32 connects to WiFi network
- [ ] Serial output shows "Connected! IP: X.X.X.X"
- [ ] LED blinks during connection, solid ON after connected
- [ ] WiFi connection remains stable for 2+ minutes
- [ ] Reconnection works after temporary disconnection

**What You Can Do Now**:
- Connect ESP32 to any 2.4GHz WiFi network
- Monitor connection status via LED (blinking = connecting, solid = connected)
- Detect and handle WiFi disconnections automatically
- Use UDP sockets (initialized and ready for OSC)

**Ready for Part 4**: OSC message transmission - complete firmware sending heartbeat messages to Python receiver

**Time Spent**: ______ minutes

**Issues Encountered**: _______________________

---

## Troubleshooting

**Problem: "Connecting to WiFi..." but never connects**
- Check 1: SSID correct? (case-sensitive, exact match)
- Check 2: Password correct? (test on another device first)
- Check 3: Network is 2.4GHz? (ESP32 cannot connect to 5GHz networks)
- Check 4: ESP32 within range? (move closer to router)
- Check 5: Router DHCP enabled? (ESP32 needs automatic IP assignment)
- Debug: Add after WiFi.begin():
  ```cpp
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < WIFI_TIMEOUT_MS) {
      Serial.print("Status: ");
      Serial.println(WiFi.status());  // 0=idle, 1=no SSID, 3=connected, 4=failed, 6=disconnected
      delay(500);
  }
  ```

**Problem: Connects but immediately enters error state blink**
- Solution: setup() may have logic error
- Verify `state.wifiConnected = connectWiFi();` line present
- Verify `if (!state.wifiConnected)` check comes AFTER connectWiFi() call

**Problem: LED doesn't blink during connection**
- Check: STATUS_LED_PIN correct for your board? (GPIO 2 is common, but varies)
- Try: Change to GPIO 2, 13, or board-specific LED pin
- Verify: pinMode(STATUS_LED_PIN, OUTPUT) in setup()

**Problem: Compilation error "WiFi.h: No such file or directory"**
- Solution: ESP32 platform not installed
- Run: `pio pkg install --global --platform espressif32`
- Retry: `pio run`

**Problem: "WiFi disconnected, reconnecting..." appearing constantly**
- Cause: Weak WiFi signal or interference
- Solution 1: Move ESP32 closer to router
- Solution 2: Try different WiFi channel on router (less congested)
- Solution 3: Check for 2.4GHz vs 5GHz confusion (ESP32 needs 2.4GHz)

---

**Next**: [Component 7 - Part 4: Messages Send](component-7-part4-messages.md)
