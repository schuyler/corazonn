# Phase 1 Firmware - Implementation Guide

[**Back to Index**](index.md)

**Version:** 3.0 | **Date:** 2025-11-09

Main program flow, project structure, and build process.

---

## 7. Main Program Flow

### 7.1 setup() Function

**Requirements:**

**R15: Serial Initialization**
```cpp
Serial.begin(115200);
delay(100);  // Allow serial to initialize
```
- Baud rate: 115200
- Brief delay for stability

**R16: Startup Banner**
```cpp
Serial.println("\n=== Heartbeat Installation - Phase 1 ===");
Serial.print("Sensor ID: ");
Serial.println(SENSOR_ID);
```

**R17: GPIO Configuration**
```cpp
pinMode(STATUS_LED_PIN, OUTPUT);
digitalWrite(STATUS_LED_PIN, LOW);
```
- Configure LED pin as output
- Initial state: OFF

**R18: WiFi Connection**
```cpp
state.wifiConnected = connectWiFi();
if (!state.wifiConnected) {
    Serial.println("ERROR: WiFi connection failed");
    Serial.print("WiFi status code: ");
    Serial.println(WiFi.status());  // Print status for diagnosis
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
```
- Attempt connection
- If failure: Print diagnostic information before entering error loop
- WiFi.status() codes: 0=idle, 1=no SSID available, 3=connected, 4=failed, 6=disconnected
- Rapid blink indicates fatal error (cannot proceed without WiFi)

**R19: UDP Initialization**
```cpp
udp.begin(0);  // Bind to any available port
```
- Port 0 = let system assign ephemeral port (30000-60000 range typically)
- ESP32 acts as UDP client, doesn't need specific source port
- Server knows destination from received packet's source address

**R20: Completion Message**
```cpp
Serial.println("Setup complete. Starting message loop...");
state.lastMessageTime = millis();
```
- Confirm ready
- Initialize timing for first message

---

### 7.2 loop() Function

**Requirements:**

**R21: WiFi Status Check**
```cpp
checkWiFi();  // Periodic monitoring
```
- Call every iteration (rate-limited internally to 5-second intervals)
- Non-blocking (returns immediately if check not due)

**R22: Message Timing**
```cpp
unsigned long currentTime = millis();
if (currentTime - state.lastMessageTime >= TEST_MESSAGE_INTERVAL_MS) {
    // Send message
}
```
- Non-blocking delay using millis()
- Check if 1000ms interval elapsed
- Works correctly across millis() rollover (unsigned arithmetic)

**R23: Message Generation (Phase 1)**
```cpp
int test_ibi = 800 + (state.messageCounter % 200);
```
- Generate test values in range 800-999ms (simulates 60-75 BPM)
- Creates deterministic repeating sequence (not random)
- Sequence repeats every 200 messages for reproducibility in testing
- Pattern: 800, 801, 802, ..., 999, 800, 801, ...
- This is intentional - allows validation that counter is working correctly

**R24: Message Transmission**
```cpp
sendHeartbeatOSC(test_ibi);
state.lastMessageTime = currentTime;
state.messageCounter++;
```
- Send OSC message
- Update timing
- Increment counter

**R25: Serial Feedback**
```cpp
Serial.print("Sent message #");
Serial.print(state.messageCounter);
Serial.print(": /heartbeat/");
Serial.print(SENSOR_ID);
Serial.print(" ");
Serial.println(test_ibi);
```
- Confirm each transmission
- Show message address and IBI value
- Format matches testing infrastructure expectations

**Note on Serial Buffer:**
At 1 message/second, serial output is ~50 bytes/second. ESP32 serial buffer (default 256 bytes) will not overflow. If message rate increases in future phases, consider reducing serial verbosity.

**R26: LED Update**
```cpp
updateLED();
```
- Update LED state based on WiFi connection
- Non-blocking function call

**R27: Loop Delay**
```cpp
delay(10);
```
- 10ms delay for stability
- Reduces CPU usage
- Allows WiFi background tasks

---

## 8. Complete Program Structure

### 8.1 File Organization

**PlatformIO Project Structure:**

```
firmware/heartbeat_phase1/
├── platformio.ini          # Project configuration
├── src/
│   └── main.cpp           # Main firmware code
├── lib/                   # Custom libraries (empty for Phase 1)
├── include/               # Header files (empty for Phase 1)
└── test/                  # Unit tests (future phases)
```

**platformio.ini Configuration:**

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
upload_speed = 921600
board_build.flash_mode = qio
board_build.flash_size = 4MB
lib_deps =
    https://github.com/CNMAT/OSC.git
```

**src/main.cpp Structure:**

```cpp
/**
 * Heartbeat Installation - Phase 1: WiFi + OSC
 * ESP32 Firmware
 */

// ============================================================================
// INCLUDES
// ============================================================================
#include <Arduino.h>    // Required for PlatformIO (auto-included in Arduino IDE)
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCMessage.h>

// ============================================================================
// CONFIGURATION
// ============================================================================
// Network configuration
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 50, 100);
const uint16_t SERVER_PORT = 8000;

// Hardware configuration
const int STATUS_LED_PIN = 2;

// System configuration
const int SENSOR_ID = 0;  // CHANGE THIS: 0, 1, 2, or 3
const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;
const unsigned long WIFI_TIMEOUT_MS = 30000;

// ============================================================================
// GLOBAL STATE
// ============================================================================
struct SystemState {
    bool wifiConnected;
    unsigned long lastMessageTime;
    uint32_t messageCounter;
};

WiFiUDP udp;
SystemState state = {false, 0, 0};

// ============================================================================
// FUNCTION DECLARATIONS
// ============================================================================
bool connectWiFi();
void sendHeartbeatOSC(int ibi_ms);
void updateLED();
void checkWiFi();

// ============================================================================
// FUNCTION IMPLEMENTATIONS
// ============================================================================
// [Implement functions per specifications above]

// ============================================================================
// ARDUINO CORE
// ============================================================================
void setup() {
    // [Implement per R15-R20]
}

void loop() {
    // [Implement per R21-R27]
}
```

---

## 9. Compilation & Upload

### 9.1 PlatformIO Configuration

**Required Settings (in platformio.ini):**

**R28: Board Selection**
```ini
[env:esp32dev]
board = esp32dev
```
- Board: esp32dev (ESP32 Dev Module)
- Can specify variant if needed (e.g., esp32-wroom-32)

**R29: Upload Settings**
```ini
upload_speed = 921600           # Fast upload (or 115200 for reliability)
board_build.flash_mode = qio    # Quad I/O mode
board_build.flash_size = 4MB    # Flash size
monitor_speed = 115200          # Serial monitor baud rate
```

**R30: Pre-Upload Configuration**
- MUST edit WiFi credentials in `src/main.cpp` (SSID, PASSWORD)
- MUST edit SERVER_IP to match receiver
- MUST set unique SENSOR_ID (0-3)

### 9.2 PlatformIO Commands

**Compilation Only:**
```bash
cd /home/user/corazonn/firmware/heartbeat_phase1
pio run
```

**Upload to ESP32:**
```bash
# Compile and upload
pio run --target upload

# If upload fails, try reducing upload speed by editing platformio.ini:
# upload_speed = 115200
```

**Serial Monitor:**
```bash
# Open serial monitor (115200 baud, configured in platformio.ini)
pio device monitor

# Exit: Ctrl+C
```

**Combined Build-Upload-Monitor:**
```bash
# Upload firmware and immediately open serial monitor
pio run --target upload && pio device monitor
```

**Expected Compilation Output:**
```
Processing esp32dev (platform: espressif32; board: esp32dev; framework: arduino)
...
Building .pio/build/esp32dev/firmware.bin
RAM:   [=         ]  14.2% (used 46552 bytes from 327680 bytes)
Flash: [====      ]  35.8% (used 469645 bytes from 1310720 bytes)
========================= [SUCCESS] Took X.XX seconds =========================
```

**Expected Upload Output:**
```
Configuring upload protocol...
Looking for upload port...
Auto-detected: /dev/ttyUSB0
Uploading .pio/build/esp32dev/firmware.bin
...
Writing at 0x00010000... (100%)
Wrote 469645 bytes (XXXXX compressed) at 0x00010000 in X.X seconds (effective XXX.X kbit/s)...
Hash of data verified.

Leaving...
Hard resetting via RTS pin...
```

### 9.3 Troubleshooting PlatformIO Upload

**Upload fails: "serial.serialutil.SerialException: [Errno 2] could not open port"**
- Cause: Port permissions or wrong port
- Solution:
  ```bash
  # List available ports
  pio device list

  # Linux: Add user to dialout group
  sudo usermod -a -G dialout $USER
  # (logout and login required)

  # Specify port manually in platformio.ini:
  # upload_port = /dev/ttyUSB0
  ```

**Upload fails: "A fatal error occurred: Failed to connect"**
- Hold BOOT button on ESP32 during upload
- Try lower upload speed (115200 instead of 921600)
- Check USB cable (must be data cable, not charge-only)

---

**Related sections:**
- See [api-network.md](api-network.md), [api-messaging.md](api-messaging.md), [api-status.md](api-status.md) for function specifications
- See [operations.md](operations.md) for testing and validation
