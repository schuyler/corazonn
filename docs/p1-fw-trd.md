# Heartbeat Firmware - Phase 1 Firmware Implementation TRD
## ESP32 WiFi + OSC Messaging

**Version:** 2.0  
**Date:** 2025-11-08  
**Purpose:** Define ESP32 firmware requirements for WiFi connection and OSC messaging  
**Audience:** Coding agent implementing ESP32 firmware  
**Hardware:** ESP32-WROOM-32 or compatible (any ESP32 with WiFi)  
**Framework:** Arduino (for rapid prototyping within 1-week timeline)

**⚠️ CRITICAL: PREREQUISITES**
```
Step 1: Complete heartbeat-phase1-testing-infrastructure-trd.md FIRST
Step 2: Validate testing infrastructure works (Python OSC receiver running)
Step 3: Then implement this firmware
Step 4: Test firmware using infrastructure from Step 1
```

Testing infrastructure MUST be working before starting firmware implementation.

**Estimated Implementation Time:** 2-3 hours (code) + 1 hour (testing)

---

## 0. Prerequisites

### 0.1 Arduino IDE Setup

**MUST complete before writing any code:**

**Step 1: Install Arduino IDE**
- Download from: https://www.arduino.cc/en/software
- Version 2.0+ recommended
- Install for your operating system

**Step 2: Add ESP32 Board Support**
1. Open Arduino IDE
2. File → Preferences
3. Additional Board Manager URLs → Add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Click OK
5. Tools → Board → Boards Manager
6. Search "esp32"
7. Install "esp32 by Espressif Systems" (version 2.0.0 or newer)
8. Wait for installation to complete (may take 5-10 minutes)

**Step 3: Install OSC Library**
1. Tools → Manage Libraries
2. Search "OSC"
3. Install "OSC by Adrian Freed" (CNMat)
4. Version 1.3.7 or newer

**Step 4: Configure Board Settings**
1. Tools → Board → ESP32 Arduino → "ESP32 Dev Module"
2. Tools → Upload Speed → 921600 (or 115200 if upload fails)
   - 921600 is faster but some USB cables can't handle it
   - Use 115200 for reliability with cheap cables
3. Tools → Flash Frequency → 80MHz
   - Standard frequency, good balance of speed and stability
4. Tools → Flash Mode → QIO
   - Quad I/O mode, fastest flash access
5. Tools → Flash Size → 4MB (32Mb)
   - Standard ESP32-WROOM-32 size
   - 32Mb = 32 megabits = 4 megabytes
6. Tools → Partition Scheme → "Default 4MB with spiffs"
   - Provides ~1.2MB program space (adequate for Phase 1-4)
   - Includes SPIFFS filesystem for future data logging

**Step 5: Connect ESP32 Hardware**
1. Connect ESP32 to computer via USB cable
2. Tools → Port → Select correct port:
   - Windows: COMX (e.g., COM3, COM4)
   - macOS: /dev/cu.usbserial-XXXX
   - Linux: /dev/ttyUSB0 or /dev/ttyACM0
3. If port not visible: Install USB drivers (see below)

**USB Drivers (if needed):**
- **CP2102 chipset:** https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- **CH340 chipset:** http://www.wch-ic.com/downloads/CH341SER_ZIP.html
- Windows: Install driver, restart
- macOS/Linux: Usually automatic

### 0.2 Testing Infrastructure Setup

**MUST be completed from previous TRD:**
- ✅ Python OSC receiver implemented and tested
- ✅ Receiver runs on port 8000
- ✅ Can see messages when simulator runs

**Verify receiver is working:**
```bash
# Terminal 1: Start receiver
python3 osc_receiver.py --port 8000

# Terminal 2: Send test message with netcat (optional verification)
# If receiver shows received message, infrastructure is ready
```

---

## 1. Objective

Implement ESP32 firmware that connects to WiFi and sends test OSC messages. Validates communication pipeline before adding sensor hardware.

**Deliverables:**
- Single `.ino` Arduino sketch file
- Compiles for ESP32 target
- Connects to specified WiFi network
- Sends OSC heartbeat messages at 1 Hz
- LED indicates connection status
- Validated against testing infrastructure (see `heartbeat-phase1-testing-infrastructure-trd.md`)

**Success Criteria:**
- Firmware uploads to ESP32 without errors
- Connects to WiFi within 30 seconds
- Python receiver (from testing infrastructure) receives messages
- Runs for 5+ minutes without crashes
- LED feedback working correctly

---

## 2. Architecture Overview

### 2.1 Execution Model

**Single-threaded non-blocking architecture:**
- `setup()`: Initialize hardware, connect WiFi, configure UDP
- `loop()`: Send test messages at 1 Hz, update LED, check WiFi status
- No RTOS tasks, no interrupts in Phase 1

**Timing:**
- Use `millis()` for non-blocking delays
- Main loop cycles every 10ms
- Message sending triggered when interval elapsed

### 2.2 State Machine

```
STARTUP → WIFI_CONNECTING → WIFI_CONNECTED → RUNNING
                ↓                                ↓
           ERROR_HALT                  (loop: send messages)
```

**States:**
- `STARTUP`: Hardware initialization
- `WIFI_CONNECTING`: Attempting WiFi connection (30 sec timeout)
- `WIFI_CONNECTED`: WiFi active, UDP ready
- `RUNNING`: Normal operation (sending messages)
- `ERROR_HALT`: Critical failure (infinite blink)

---

## 3. Required Libraries

### 3.1 Arduino Libraries

**Built-in (no installation):**
- `WiFi.h` - ESP32 WiFi stack
- `WiFiUdp.h` - UDP socket implementation

**External (install via Library Manager):**
- `OSC` by Adrian Freed (CNMat)
  - Version: 1.3.7 or newer
  - Provides: `OSCMessage.h`, `OSCBundle.h`
  - Installation: Arduino IDE → Tools → Manage Libraries → Search "OSC"

### 3.2 Library Usage

**WiFi.h:**
```cpp
WiFi.mode(WIFI_STA);          // Station mode (client)
WiFi.begin(ssid, password);   // Connect to AP
WiFi.status();                // Check connection status
WiFi.localIP();               // Get assigned IP
WiFi.reconnect();             // Attempt reconnection
```

**WiFiUdp.h:**
```cpp
WiFiUDP udp;
udp.begin(localPort);         // Bind to local port (use 0 for any)
udp.beginPacket(ip, port);    // Start packet
udp.write(buffer, length);    // Add data
udp.endPacket();              // Send packet
```

**OSCMessage.h:**
```cpp
OSCMessage msg("/address/pattern");
msg.add((int32_t)value);      // Add int32 argument
msg.send(udp);                // Send via UDP object
msg.empty();                  // Clear for reuse
```

---

## 4. Configuration Constants

### 4.1 Network Configuration

**MUST be user-configurable (edit before upload):**

```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS: Your dev machine's IP
const uint16_t SERVER_PORT = 8000;
```

**⚠️ CRITICAL - SERVER_IP Configuration:**
The ESP32 hardware CANNOT use `127.0.0.1` (that would be its own localhost).
You MUST use your development machine's IP address on the WiFi network.

**Finding your development machine's IP:**
- **Linux:** `ip addr show` or `ifconfig` (look for wlan0 or eth0 inet address)
- **macOS:** System Preferences → Network → WiFi → Advanced → TCP/IP (IPv4 Address)
- **Windows:** `ipconfig` (look for IPv4 Address under WiFi adapter)

Example: If your dev machine shows `192.168.1.100`, use:
```cpp
const IPAddress SERVER_IP(192, 168, 1, 100);
```

The ESP32 will connect to WiFi, get its own IP (e.g., `192.168.1.42`), and send messages to your dev machine at `192.168.1.100:8000` where the Python receiver is listening.

**Requirements:**
- `WIFI_SSID`: String, max 32 characters, **2.4GHz network only** (ESP32 does not support 5GHz)
- `WIFI_PASSWORD`: String, max 63 characters, WPA2
- `SERVER_IP`: IPv4 address of development machine running Python receiver
- `SERVER_PORT`: UDP port 8000 (matches testing infrastructure)

### 4.2 Hardware Configuration

```cpp
const int STATUS_LED_PIN = 2;  // Built-in LED (GPIO 2 on most ESP32 boards)
```

**Requirements:**
- LED pin MUST be output-capable GPIO
- GPIO 2 is standard built-in LED on ESP32 DevKit boards
- May need adjustment for other board variants

### 4.3 System Configuration

```cpp
const int SENSOR_ID = 0;  // Unique sensor ID: 0, 1, 2, or 3
const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;  // 1 second
const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 seconds
```

**Requirements:**
- `SENSOR_ID`: Integer 0-3, unique per ESP32 unit
- `TEST_MESSAGE_INTERVAL_MS`: Milliseconds between messages (Phase 1: 1000)
- `WIFI_TIMEOUT_MS`: Max time to wait for WiFi connection

---

## 5. Data Structures

### 5.1 System State

**Purpose:** Track WiFi connection and message timing

```cpp
struct SystemState {
    bool wifiConnected;           // Current WiFi connection status
    unsigned long lastMessageTime;  // millis() of last message sent
    uint32_t messageCounter;      // Total messages sent
};
```

**Requirements:**
- `wifiConnected`: Set true when WiFi.status() == WL_CONNECTED
- `lastMessageTime`: Updated each time message sent
- `messageCounter`: Incremented each time message sent, rolls over at UINT32_MAX

**Initial Values:**
```cpp
SystemState state = {
    .wifiConnected = false,
    .lastMessageTime = 0,
    .messageCounter = 0
};
```

### 5.2 Global Objects

```cpp
WiFiUDP udp;          // UDP socket for OSC transmission
SystemState state;    // System state (defined above)
```

---

## 6. Function Specifications

### 6.1 WiFi Connection

**Function:** `connectWiFi()`

**Signature:**
```cpp
bool connectWiFi();
```

**Purpose:** Establish WiFi connection with timeout

**Requirements:**

**R1: WiFi Initialization**
- MUST call `WiFi.mode(WIFI_STA)` before `WiFi.begin()`
- MUST call `WiFi.begin(WIFI_SSID, WIFI_PASSWORD)`
- MUST print "Connecting to WiFi: [SSID]" to serial

**R2: Connection Wait Loop**
- MUST poll `WiFi.status()` until `WL_CONNECTED` OR timeout
- MUST timeout after `WIFI_TIMEOUT_MS` milliseconds
- MUST use non-blocking delay (check millis() each iteration)
- MUST blink LED during connection attempt (100ms on/off)

**R3: Success Behavior**
- MUST set `state.wifiConnected = true`
- MUST turn LED solid ON
- MUST print "Connected! IP: [IP_ADDRESS]" to serial
- MUST return `true`

**R4: Failure Behavior**
- MUST print "WiFi connection timeout" to serial
- MUST leave LED in last blink state
- MUST return `false`

**Example Serial Output (Success):**
```
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.50.42
```

**Example Serial Output (Failure):**
```
Connecting to WiFi: heartbeat-install
WiFi connection timeout
```

---

### 6.2 OSC Message Construction

**Function:** `sendHeartbeatOSC()`

**Signature:**
```cpp
void sendHeartbeatOSC(int ibi_ms);
```

**Purpose:** Construct and send OSC heartbeat message

**Parameters:**
- `ibi_ms`: Inter-beat interval in milliseconds (300-3000 valid range)

**Requirements:**

**R5: Address Pattern Construction**
- MUST construct address string: `/heartbeat/[SENSOR_ID]`
- Format using `snprintf()` with buffer size 20 bytes minimum
- Example: SENSOR_ID=0 → "/heartbeat/0"

**R6: OSC Message Construction**
- MUST create OSCMessage object with address pattern
- MUST add single int32 argument: `ibi_ms`
- MUST use `msg.add((int32_t)ibi_ms)` for correct type

**R7: UDP Transmission**
- MUST call `udp.beginPacket(SERVER_IP, SERVER_PORT)`
- MUST call `msg.send(udp)` to write OSC data to packet
- MUST call `udp.endPacket()` to transmit packet
- MUST call `msg.empty()` AFTER `udp.endPacket()` to clear message buffer
- Calling sequence is critical: beginPacket → send → endPacket → empty
- msg.empty() prepares message object for reuse in next transmission

**R8: No Error Checking**
- Fire-and-forget transmission (UDP nature)
- No return value needed
- No acknowledgment expected
- Packet may be lost - this is acceptable UDP behavior

**Pseudocode:**
```
function sendHeartbeatOSC(ibi_ms):
    address = format("/heartbeat/%d", SENSOR_ID)
    msg = new OSCMessage(address)
    msg.add_int32(ibi_ms)
    
    udp.beginPacket(SERVER_IP, SERVER_PORT)
    msg.send(udp)
    udp.endPacket()
    
    msg.empty()
```

---

### 6.3 LED Status Indication

**Function:** `updateLED()`

**Signature:**
```cpp
void updateLED();
```

**Purpose:** Update LED state based on system status

**Requirements:**

**R9: LED States**
- **WiFi Connecting:** Blink at 5 Hz (100ms on, 100ms off)
- **WiFi Connected:** Solid ON
- **No state for message pulse in Phase 1** (simplified)

**R10: State Determination**
- MUST check `state.wifiConnected`
- If false: Blink at 5 Hz using `(millis() / 100) % 2`
- If true: Solid HIGH

**R11: LED Control**
- MUST use `digitalWrite(STATUS_LED_PIN, HIGH/LOW)`
- Non-blocking (no delays)

**Pseudocode:**
```
function updateLED():
    if not state.wifiConnected:
        # Blink during connection
        led_state = (millis() / 100) % 2
        digitalWrite(STATUS_LED_PIN, led_state)
    else:
        # Solid on when connected
        digitalWrite(STATUS_LED_PIN, HIGH)
```

---

### 6.4 WiFi Status Monitoring

**Function:** `checkWiFi()`

**Signature:**
```cpp
void checkWiFi();
```

**Purpose:** Monitor WiFi connection, attempt reconnection if dropped

**Requirements:**

**R12: Status Check**
- MUST check `WiFi.status()` for current connection state
- If `WL_CONNECTED`: Set `state.wifiConnected = true`
- If not `WL_CONNECTED`: Set `state.wifiConnected = false`

**R13: Reconnection Logic**
- If disconnected: MUST call `WiFi.reconnect()`
- MUST print "WiFi disconnected, reconnecting..." to serial
- WiFi.reconnect() is **non-blocking** - returns immediately, reconnection happens in background
- May take 5-30 seconds to reconnect
- ESP32 WiFi stack handles reconnection attempts automatically
- No timeout needed - will keep trying indefinitely

**R14: Call Frequency**
- SHOULD be called every 5 seconds (not every loop iteration)
- Use static variable with `millis()` timer to rate-limit checks
- Static variable MUST be initialized to 0 (causes immediate first check)

**Pseudocode:**
```
static last_check_time = 0  # Initialize to 0

function checkWiFi():
    if millis() - last_check_time < 5000:
        return  # Check at most every 5 seconds
    
    last_check_time = millis()
    
    if WiFi.status() != WL_CONNECTED:
        state.wifiConnected = false
        print("WiFi disconnected, reconnecting...")
        WiFi.reconnect()
    else:
        state.wifiConnected = true
```

**Note on millis() Rollover:**
The expression `millis() - last_check_time` works correctly even after millis() rolls over at 49.7 days due to unsigned arithmetic properties. Do not "fix" this with additional rollover handling.

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

**Single .ino file structure:**

```cpp
/**
 * Heartbeat Installation - Phase 1: WiFi + OSC
 * ESP32 Firmware
 */

// ============================================================================
// INCLUDES
// ============================================================================
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

### 9.1 Arduino IDE Configuration

**Required Settings:**

**R28: Board Selection**
- Tools → Board → ESP32 Arduino → "ESP32 Dev Module"
- Or specific board variant if known (e.g., "ESP32-WROOM-DA Module")

**R29: Upload Settings**
- Port: Select correct COM port (Windows) or /dev/ttyUSB0 (Linux)
- Upload Speed: 921600 (fast) or 115200 (reliable)
- Flash Frequency: 80MHz
- Flash Mode: QIO
- Flash Size: 4MB (32Mb)
- Partition Scheme: Default 4MB with spiffs

**R30: Pre-Upload Configuration**
- MUST edit WiFi credentials (SSID, PASSWORD)
- MUST edit SERVER_IP to match receiver
- MUST set unique SENSOR_ID (0-3)

### 9.2 Upload Procedure

**Steps:**
1. Connect ESP32 to computer via USB cable
2. Open `.ino` file in Arduino IDE
3. Verify board and port settings (Tools menu)
4. Edit configuration constants (WIFI_SSID, SENSOR_ID, etc.)
5. Click "Upload" button (or Sketch → Upload)
6. Wait for "Hard resetting via RTS pin..." message
7. Open Serial Monitor (Tools → Serial Monitor)
8. Set baud rate to 115200
9. Press ESP32 reset button if no output appears

**Expected Upload Output:**
```
Sketch uses XXXXX bytes (XX%) of program storage space.
Global variables use XXXX bytes (XX%) of dynamic memory.
...
Connecting........_____.....
Writing at 0x00010000... (100%)
Wrote XXXXX bytes in X.XX seconds (effective XXX.X kbit/s)
Hash of data verified.
Leaving...
Hard resetting via RTS pin...
```

---

## 10. Validation Against Testing Infrastructure

### 10.1 Prerequisites

**MUST have completed:**
- Testing infrastructure built (from `heartbeat-phase1-testing-infrastructure-trd.md`)
- Python OSC receiver running
- ESP32 firmware uploaded and running

### 10.2 Validation Procedure

**Step 1: Start Receiver**
```bash
python3 osc_receiver.py --port 8000
```
Expected: "OSC Receiver listening on 0.0.0.0:8000"

**Step 2: Power ESP32**
- Connect via USB or battery
- Open Serial Monitor (115200 baud)

**Expected Serial Output:**
```
=== Heartbeat Installation - Phase 1 ===
Sensor ID: 0
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.50.42
Setup complete. Starting message loop...
Sent message #1: /heartbeat/0 800
Sent message #2: /heartbeat/0 850
Sent message #3: /heartbeat/0 900
...
```

**Expected Receiver Output:**
```
[/heartbeat/0] IBI: 800ms, BPM: 75.0
[/heartbeat/0] IBI: 850ms, BPM: 70.6
[/heartbeat/0] IBI: 900ms, BPM: 66.7
...
```

**Step 3: Validate LED**
- During "Connecting": LED blinks rapidly (5 Hz)
- After "Connected": LED solid ON

**Step 4: Run for 5 Minutes**
- Verify continuous message flow
- No WiFi disconnections
- Message counter increments consistently
- Receiver shows 0 invalid messages

### 10.3 Multi-Unit Testing

**Requirements for multi-unit test:**

**R31: Unit Identification**
- MUST program each ESP32 with unique SENSOR_ID (0, 1, 2, 3)
- MUST physically label units (sticker, marker, etc.)

**R32: Independent Operation**
- Each unit MUST connect to WiFi independently
- Each unit MUST send messages independently
- No synchronization required between units

**R33: Receiver Validation**
- Receiver MUST show messages from all sensor IDs
- Receiver MUST track statistics per sensor
- No interference between units

**Test Procedure:**
1. Program 2-4 ESP32s with different SENSOR_IDs
2. Start single receiver
3. Power all ESP32s simultaneously
4. Run for 5 minutes
5. Verify receiver shows messages from all units

---

## 11. Acceptance Criteria

### 11.1 Compilation

**MUST:**
- ✅ Compile without errors
- ✅ Compile without warnings (or only benign warnings)
- ✅ Binary size < 500KB (plenty of headroom on ESP32)

### 11.2 Runtime Behavior

**MUST:**
- ✅ Connect to WiFi within 30 seconds
- ✅ Print IP address to serial
- ✅ Send OSC messages at ~1 Hz (±10%)
- ✅ Messages received by Python receiver
- ✅ 0 invalid messages in receiver
- ✅ Run for 5+ minutes without crashes or resets
- ✅ LED indicates connection status correctly

### 11.3 Message Format

**MUST:**
- ✅ Address pattern: `/heartbeat/[0-3]`
- ✅ Argument type: int32
- ✅ Argument value: 800-1000ms range
- ✅ Message size: 24 bytes
- ✅ Passes all protocol tests from testing infrastructure

### 11.4 Reliability

**MUST:**
- ✅ Handle WiFi connection failure (error state, not crash)
- ✅ No memory leaks over 5+ minutes
- ✅ Consistent performance (no degradation)
- ✅ Stable message rate (not speeding up or slowing down)

---

## 12. Known Limitations (Phase 1)

**Intentional Simplifications:**
- No sensor input (using test values)
- No beat detection algorithm
- No watchdog timer
- No WiFi reconnection after error state
- No sophisticated LED feedback (just on/off)
- No power management
- No OTA updates
- No configuration web interface

**These will be addressed in later phases.**

---

## 13. Troubleshooting

### 13.1 Compilation Errors

**Error: "WiFi.h: No such file or directory"**
- Cause: ESP32 board package not installed
- Solution: File → Preferences → Additional Board Manager URLs → Add ESP32 URL:
  ```
  https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
  ```
- Then: Tools → Board → Boards Manager → Search "esp32" → Install "esp32 by Espressif Systems"

**Error: "OSCMessage.h: No such file or directory"**
- Cause: OSC library not installed
- Solution: Tools → Manage Libraries → Search "OSC" → Install "OSC by Adrian Freed"
- Version: Must be 1.3.7 or newer

**Error: "invalid conversion from 'const char*' to 'char*'"**
- Cause: String constant handling
- Solution: Use `const char*` for SSID/password, not `char*`
- Example: `const char* WIFI_SSID = "...";` (correct)

**Error: "'IPAddress' does not name a type"**
- Cause: Missing WiFi.h include
- Solution: Add `#include <WiFi.h>` at top of file

### 13.2 Upload Errors

**Error: "Failed to connect to ESP32"**
- Solutions (try in order):
  1. Press and hold BOOT button on ESP32 during upload
  2. Press BOOT button, click Upload, release BOOT when "Connecting..." appears
  3. Try different USB cable (data cable, not charge-only)
  4. Reduce upload speed: Tools → Upload Speed → 115200
  5. Check USB drivers installed (see Section 0.1)

**Error: "A fatal error occurred: Timed out waiting for packet header"**
- Solutions:
  1. Press ESP32 reset button (EN or RST)
  2. Disconnect and reconnect USB cable
  3. Try different USB port on computer
  4. Check ESP32 has power (LED should be on)

**Error: "Serial port not found" or "Port not available"**
- **Windows:**
  - Check Device Manager → Ports (COM & LPT)
  - Install CP2102 or CH340 driver if "Unknown Device"
  - Driver links in Section 0.1
- **macOS:**
  - Port should be /dev/cu.usbserial-XXXX
  - If not visible: Install driver for your USB chip (CP2102 or CH340)
  - May need to approve driver in System Preferences → Security & Privacy
- **Linux:**
  - Port is /dev/ttyUSB0 or /dev/ttyACM0
  - Add user to dialout group: `sudo usermod -a -G dialout $USER`
  - Logout and login for group change to take effect
  - Check permissions: `ls -l /dev/ttyUSB0`

### 13.3 Runtime Issues

**ESP32 connects but no messages received at Python receiver**
- Check 1: SERVER_IP correct?
  - MUST be development machine's IP, not 127.0.0.1
  - Verify with `ipconfig` (Windows), `ifconfig` (Linux/Mac)
- Check 2: ESP32 and dev machine on same WiFi network?
  - Check ESP32 prints "Connected! IP: 192.168.X.X"
  - Dev machine should be 192.168.X.Y (same subnet)
- Check 3: Firewall blocking UDP port 8000?
  - **Windows:** Windows Defender Firewall → Allow app → Python
  - **macOS:** System Preferences → Security → Firewall Options → Allow Python
  - **Linux:** `sudo ufw allow 8000/udp`
- Check 4: Python receiver actually running?
  - Should print "OSC Receiver listening on 0.0.0.0:8000"

**LED blinks continuously, no "Connected" message**
- Check 1: WiFi credentials correct?
  - SSID exact match (case-sensitive)
  - Password correct
- Check 2: Network is 2.4GHz?
  - ESP32 cannot connect to 5GHz networks
  - Check router settings or use 2.4GHz-only network
- Check 3: Network in range?
  - Move ESP32 closer to router
  - Check WiFi signal strength
- Check 4: DHCP available?
  - Router may have reached maximum client limit
  - Check router admin page
- Debug: Add after `WiFi.begin()`:
  ```cpp
  while (WiFi.status() != WL_CONNECTED) {
      Serial.print("Status: ");
      Serial.println(WiFi.status());
      delay(500);
  }
  ```
  - Status codes: 0=idle, 1=no SSID, 3=connected, 4=failed, 6=disconnected

**Messages stop after several minutes**
- Check 1: WiFi connection stable?
  - Watch serial monitor for "WiFi disconnected" messages
  - Try different router channel (less congestion)
  - Move ESP32 closer to router
- Check 2: ESP32 resetting?
  - Look for startup banner in serial monitor
  - If restarting: Power supply issue or watchdog reset (not implemented in Phase 1)
- Check 3: Python receiver still running?
  - Check receiver terminal for errors

**Serial monitor shows garbage characters**
- Cause: Wrong baud rate
- Solution: Serial Monitor → Bottom right → Set to 115200

**Serial monitor shows nothing**
- Solution 1: Press ESP32 reset button (EN or RST)
- Solution 2: Disconnect/reconnect USB cable
- Solution 3: Check Serial Monitor is open (Tools → Serial Monitor)

### 13.4 Network Debugging

**Verify ESP32 is sending packets (Linux/Mac):**
```bash
# On development machine, find your WiFi IP
ifconfig  # Look for en0 or wlan0

# Capture packets
sudo tcpdump -i any port 8000 -A

# Should see ESP32 source IP and OSC message content
```

**Verify ESP32 has network connectivity:**
Add to firmware for testing:
```cpp
// After WiFi connects, try to ping gateway
IPAddress gateway = WiFi.gatewayIP();
Serial.print("Gateway: ");
Serial.println(gateway);

// Check if can resolve DNS (tests network stack)
IPAddress testIP;
if (WiFi.hostByName("google.com", testIP)) {
    Serial.print("DNS works, resolved to: ");
    Serial.println(testIP);
}
```

### 13.5 Known ESP32-Specific Issues

**Brown-out detector triggered**
- Symptom: ESP32 resets during WiFi connection
- Cause: USB power insufficient for WiFi radio
- Solution: Use powered USB hub or external 5V power supply

**Flash read error**
- Symptom: Upload succeeds but ESP32 won't boot
- Solution: Hold BOOT button, press reset, release BOOT, try upload again

**Conflicting SSID characters**
- Symptom: Connection fails with correct credentials
- Cause: Some special characters in SSID cause issues
- Solution: Use alphanumeric SSID if possible, or escape special characters

---

## 14. Success Metrics

### 14.1 Phase 1 Firmware Complete

**All criteria MUST be met:**

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

### 14.2 Ready for Phase 2

Phase 1 complete, proceed to Phase 2 when:

- ✅ WiFi connection reliable
- ✅ OSC messaging proven correct
- ✅ LED feedback validated
- ✅ Testing infrastructure integration working
- ✅ Multi-unit operation confirmed
- ✅ Code structure ready to add sensor input

**Phase 2 Preview:** Will add analog sensor reading (GPIO 32), simple threshold-based beat detection, and replace test IBI values with real sensor-derived IBIs.

---

*End of Technical Reference Document*

**Document Version:** 1.0  
**Last Updated:** 2025-11-08  
**Status:** Ready for implementation by coding agent  
**Dependencies:** Testing infrastructure from `heartbeat-phase1-testing-infrastructure-trd.md`  
**Next:** `heartbeat-phase2-firmware-trd.md` (sensor integration)
