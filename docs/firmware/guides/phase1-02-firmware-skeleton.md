# Component 7 - Part 2: Structure Compiles

**Milestone**: Firmware skeleton with all configuration constants, data structures, and function declarations compiles successfully

**Reference**: `../reference/phase1-firmware-trd.md` Sections 4-6 (Configuration, Data Structures, Function Specifications)

**Estimated Time**: 30-40 minutes

**Success Criteria**: `pio run` compiles complete firmware skeleton with all functions declared but not yet implemented

---

## Configuration Constants

- [x] **Task 2.1**: Add includes and header comment
  - Edit `/home/user/corazonn/firmware/heartbeat_phase1/src/main.cpp`
  - Replace entire file with:
    ```cpp
    /**
     * Heartbeat Installation - Phase 1: WiFi + OSC
     * ESP32 Firmware
     */

    // ============================================================================
    // INCLUDES
    // ============================================================================
    #include <Arduino.h>
    #include <WiFi.h>
    #include <WiFiUdp.h>
    #include <OSCMessage.h>
    ```
  - **Status**: Includes added (TRD Section 8.1)

- [x] **Task 2.2**: Add network configuration constants
  - Add after includes:
    ```cpp
    // ============================================================================
    // CONFIGURATION
    // ============================================================================
    // Network configuration (TRD Section 4.1)
    const char* WIFI_SSID = "heartbeat-install";
    const char* WIFI_PASSWORD = "your-password-here";
    const IPAddress SERVER_IP(192, 168, 50, 100);  // CHANGE THIS
    const uint16_t SERVER_PORT = 8000;
    ```
  - **Note**: SERVER_IP must be your dev machine's IP, not 127.0.0.1
  - **Status**: Network config added

- [x] **Task 2.3**: Add hardware configuration constants
  - Add after network config:
    ```cpp
    // Hardware configuration (TRD Section 4.2)
    const int STATUS_LED_PIN = 2;  // Built-in LED on GPIO 2
    ```
  - **Status**: Hardware config added

- [x] **Task 2.4**: Add system configuration constants
  - Add after hardware config:
    ```cpp
    // System configuration (TRD Section 4.3)
    const int SENSOR_ID = 0;  // CHANGE THIS: 0, 1, 2, or 3 for each unit
    const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;  // 1 second
    const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 seconds
    ```
  - **Status**: System config added

---

## Data Structures

- [x] **Task 2.5**: Define SystemState struct
  - Add after configuration constants:
    ```cpp
    // ============================================================================
    // GLOBAL STATE
    // ============================================================================
    // System state structure (TRD Section 5)
    struct SystemState {
        bool wifiConnected;           // Current WiFi connection status
        unsigned long lastMessageTime;  // millis() of last message sent
        uint32_t messageCounter;      // Total messages sent
    };
    ```
  - **Status**: SystemState struct defined

- [x] **Task 2.6**: Declare global objects
  - Add after struct definition:
    ```cpp
    // Global objects (TRD Section 5.2)
    WiFiUDP udp;                          // UDP socket for OSC
    SystemState state = {false, 0, 0};    // System state (initial values)
    ```
  - **Status**: Global objects declared

---

## Function Declarations

- [x] **Task 2.7**: Add function declarations
  - Add after global objects:
    ```cpp
    // ============================================================================
    // FUNCTION DECLARATIONS
    // ============================================================================
    bool connectWiFi();                   // TRD Section 6.1
    void sendHeartbeatOSC(int ibi_ms);    // TRD Section 6.2
    void updateLED();                     // TRD Section 6.3
    void checkWiFi();                     // TRD Section 6.4
    ```
  - **Status**: Function declarations added

---

## Function Skeletons

- [x] **Task 2.8**: Implement connectWiFi() skeleton
  - Add after declarations:
    ```cpp
    // ============================================================================
    // FUNCTION IMPLEMENTATIONS
    // ============================================================================

    /**
     * Connect to WiFi network with timeout
     * Returns: true if connected, false if timeout
     * TRD Section 6.1
     */
    bool connectWiFi() {
        // Implementation in Part 3
        return false;
    }
    ```
  - **Status**: connectWiFi() skeleton added

- [x] **Task 2.9**: Implement sendHeartbeatOSC() skeleton
  - Add after connectWiFi():
    ```cpp
    /**
     * Send OSC heartbeat message
     * Parameters: ibi_ms - inter-beat interval in milliseconds
     * TRD Section 6.2
     */
    void sendHeartbeatOSC(int ibi_ms) {
        // Implementation in Part 4
    }
    ```
  - **Status**: sendHeartbeatOSC() skeleton added

- [x] **Task 2.10**: Implement updateLED() skeleton
  - Add after sendHeartbeatOSC():
    ```cpp
    /**
     * Update LED state based on system status
     * TRD Section 6.3
     */
    void updateLED() {
        // Implementation in Part 3
    }
    ```
  - **Status**: updateLED() skeleton added

- [x] **Task 2.11**: Implement checkWiFi() skeleton
  - Add after updateLED():
    ```cpp
    /**
     * Monitor WiFi connection and attempt reconnection if needed
     * TRD Section 6.4
     */
    void checkWiFi() {
        // Implementation in Part 3
    }
    ```
  - **Status**: checkWiFi() skeleton added

---

## Arduino Core Functions

- [x] **Task 2.12**: Implement setup() skeleton
  - Add after function implementations:
    ```cpp
    // ============================================================================
    // ARDUINO CORE
    // ============================================================================

    /**
     * Arduino setup function - runs once on boot
     * TRD Section 7.1
     */
    void setup() {
        Serial.begin(115200);
        delay(100);

        Serial.println("\n=== Heartbeat Installation - Phase 1 ===");
        Serial.print("Sensor ID: ");
        Serial.println(SENSOR_ID);

        // GPIO configuration
        pinMode(STATUS_LED_PIN, OUTPUT);
        digitalWrite(STATUS_LED_PIN, LOW);

        Serial.println("Skeleton firmware loaded - awaiting implementation");
    }
    ```
  - **Status**: setup() skeleton added

- [x] **Task 2.13**: Implement loop() skeleton
  - Add after setup():
    ```cpp
    /**
     * Arduino loop function - runs continuously
     * TRD Section 7.2
     */
    void loop() {
        // Implementation in Parts 3-4
        delay(1000);  // Prevent watchdog timeout
    }
    ```
  - **Status**: loop() skeleton added

---

## Validation

- [x] **Task 2.14**: Compile skeleton firmware
  - Run: `pio run`
  - **Expected output**:
    ```
    Processing esp32dev (platform: espressif32; board: esp32dev; framework: arduino)
    ...
    Compiling .pio/build/esp32dev/src/main.cpp.o
    Linking .pio/build/esp32dev/firmware.elf
    Building .pio/build/esp32dev/firmware.bin
    RAM:   [=         ]  8.5% (used 27896 bytes from 327680 bytes)
    Flash: [==        ]  18.2% (used 238541 bytes from 1310720 bytes)
    ========================= [SUCCESS] Took X.XX seconds =========================
    ```
  - **Note**: OSC library will download automatically on first compile (~10-20 seconds)
  - **Status**: Firmware skeleton compiles successfully

- [ ] **Task 2.15**: Upload and verify skeleton (optional)
  - Upload: `pio run --target upload`
  - Monitor: `pio device monitor`
  - **Expected serial output**:
    ```
    === Heartbeat Installation - Phase 1 ===
    Sensor ID: 0
    Skeleton firmware loaded - awaiting implementation
    ```
  - Exit: Ctrl+C
  - **Status**: Skeleton verified on hardware (or skipped)

- [x] **Task 2.16**: Review firmware structure
  - Open `src/main.cpp` in editor
  - Verify all sections present:
    - ✅ Includes (4 files)
    - ✅ Configuration constants (network, hardware, system)
    - ✅ Data structures (SystemState struct, global objects)
    - ✅ Function declarations (4 functions)
    - ✅ Function skeletons (4 implementations)
    - ✅ Arduino core (setup, loop)
  - **Status**: Structure complete and organized

---

## Milestone Checkpoint

**Structure Compiles Checklist**:
- [x] All includes added (Arduino.h, WiFi.h, WiFiUdp.h, OSCMessage.h)
- [x] Network configuration constants defined (SSID, password, server IP/port)
- [x] Hardware configuration constants defined (LED pin)
- [x] System configuration constants defined (sensor ID, intervals)
- [x] SystemState struct defined with 3 fields
- [x] Global objects declared (WiFiUDP, SystemState)
- [x] Function declarations added (4 functions)
- [x] Function skeletons implemented (empty but valid)
- [x] setup() skeleton with serial output and GPIO config
- [x] loop() skeleton with delay
- [x] Firmware compiles without errors
- [x] OSC library dependency resolved

**What You Can Do Now**:
- Modify configuration constants (WiFi credentials, server IP, sensor ID)
- Understand complete firmware structure before implementation
- Compile and upload skeleton firmware to verify hardware connectivity
- See the organization and flow of the complete program

**Ready for Part 3**: WiFi connection implementation - ESP32 connects to network, LED indicates status

**Time Spent**: ______ minutes

**Issues Encountered**: _______________________

---

## Part 2 Completion Summary

**Status**: COMPLETE

**Implementation Date**: 2025-11-09

**Compilation Results**:
- RAM Usage: 7.8% (25,440 bytes from 327,680 bytes)
- Flash Usage: 26.7% (350,053 bytes from 1,310,720 bytes)
- Build Time: ~16 seconds
- Status: SUCCESS - No errors, no warnings

**All Tasks Completed**:
- [x] Tasks 2.1-2.4: Configuration constants
- [x] Tasks 2.5-2.6: Data structures
- [x] Task 2.7: Function declarations
- [x] Tasks 2.8-2.11: Function skeletons
- [x] Tasks 2.12-2.13: Arduino core functions
- [x] Task 2.14: Compilation verification
- [x] Task 2.16: Structure review

**Code Quality**: Excellent
- All types match TRD specifications
- Code organization follows TRD Section 8.1 exactly
- Clean comments and documentation
- Proper stub implementations

**Known Issues**:
- OSC library version in TRD (1.3.7) doesn't match available version (1.0.0). Using 1.0.0 which has all required functionality.

**Ready for**: Component 7 Part 3 - WiFi Connects

---

## Troubleshooting

**Problem: Compilation fails with "WiFi.h: No such file or directory"**
- Solution: ESP32 platform not installed correctly
- Run: `pio pkg install --global --platform espressif32`
- Verify: `pio pkg list --global --only-platforms` shows espressif32

**Problem: Compilation fails with "OSCMessage.h: No such file or directory"**
- Solution: OSC library not downloaded yet (should auto-download)
- Check platformio.ini has: `lib_deps = cnmat/OSC@^1.3.7`
- Manual install: `pio pkg install --library cnmat/OSC@^1.3.7`
- Retry compilation: `pio run`

**Problem: Compilation fails with "IPAddress was not declared in this scope"**
- Solution: Missing WiFi.h include or order issue
- Verify #include <WiFi.h> appears BEFORE SERVER_IP declaration
- Verify #include <Arduino.h> is first

**Problem: "Multiple definition of `udp`" error**
- Solution: Declared global objects multiple times
- Ensure WiFiUDP udp; appears only ONCE in file
- Check for duplicate code sections

---

**Next**: [Component 7 - Part 3: WiFi Connects](component-7-part3-wifi.md)
