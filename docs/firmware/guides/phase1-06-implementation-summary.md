# Component 7.7 - Main Program Flow

**Milestone**: Complete ESP32 firmware with WiFi connection, OSC messaging, and LED status indication working together

**Reference**: `../reference/phase1-firmware-trd.md` Sections 7.1-7.2 (Main Program Flow)

**Status**: COMPLETE - All 71 tests passed (100%), Code review APPROVED (9.5/10)

**Implementation Date**: 2025-11-09

---

## Overview

Component 7.7 implements the main program flow for the Heartbeat Phase 1 firmware. This component brings together all previous components (WiFi connection, OSC messaging, LED control, WiFi monitoring) into a cohesive single-threaded non-blocking architecture.

The firmware:
- Initializes hardware (serial, GPIO, WiFi, UDP) in `setup()`
- Enters a main loop that sends test OSC messages at 1 Hz
- Monitors WiFi connection status and reconnects if needed
- Provides LED feedback indicating WiFi connection state
- Compiles to 738 KB (56.3% flash) with no errors or warnings

---

## Architecture Overview

### Execution Model

The firmware uses a single-threaded non-blocking architecture suitable for embedded systems:

```
STARTUP (setup)
    ↓
Initialize Serial (115200 baud)
    ↓
Configure GPIO (LED output)
    ↓
Connect to WiFi (30 second timeout)
    ↓
Initialize UDP socket (ephemeral port)
    ↓
RUNNING (loop - repeats every 10ms)
    ├─ Check WiFi status
    ├─ If interval elapsed:
    │  ├─ Generate test IBI value
    │  ├─ Send OSC message
    │  └─ Update timing/counter
    ├─ Update LED state
    └─ 10ms delay
```

### Non-Blocking Design

All timing uses `millis()` instead of blocking delays in the main loop:

```cpp
// Non-blocking approach (used)
if (currentTime - state.lastMessageTime >= TEST_MESSAGE_INTERVAL_MS) {
    sendHeartbeatOSC(test_ibi);
    state.lastMessageTime = currentTime;
}

// NOT blocking delay (avoided in loop)
// delay(1000);  // Would freeze all other operations for 1 second
```

This allows the loop to:
- Check WiFi status every 5 seconds
- Update LED at any time (no delay in updateLED)
- Send messages at 1 Hz (non-blocking check)
- Service the WiFi stack and other background tasks

---

## Function Responsibilities

### `bool connectWiFi()`

**Purpose**: Establish WiFi connection with timeout

**Behavior**:
1. Set WiFi to Station mode (client mode)
2. Begin connection with SSID and password
3. Poll WiFi status in a loop with LED blinking feedback
4. Timeout after 30 seconds if connection fails
5. Return true on success, false on timeout

**Requirements Implemented** (TRD R1-R4):
- R1: WiFi initialization (mode + begin)
- R2: Connection wait loop with timeout
- R3: Success behavior (set state, turn LED solid)
- R4: Failure behavior (print error, return false)

**Key Implementation Detail**: The LED blinks at 5 Hz during connection attempt using:
```cpp
digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
```

This creates a 100ms on/off pattern without blocking.

### `void sendHeartbeatOSC(int ibi_ms)`

**Purpose**: Construct and transmit OSC heartbeat message

**Behavior**:
1. Build OSC address string: `/heartbeat/[SENSOR_ID]`
2. Create OSCMessage object with address
3. Add int32 argument (IBI in milliseconds)
4. Send via UDP using critical sequence:
   - `udp.beginPacket()` - prepare UDP packet
   - `msg.send(udp)` - write OSC data
   - `udp.endPacket()` - transmit packet
   - `msg.empty()` - clear message buffer for reuse

**Requirements Implemented** (TRD R5-R8):
- R5: Address pattern construction
- R6: OSC message construction
- R7: UDP transmission with critical sequence
- R8: Fire-and-forget (no error checking, no return value)

**Critical Detail**: The sequence `beginPacket → send → endPacket → empty` is mandatory. Skipping `msg.empty()` causes subsequent messages to append rather than replace data.

### `void updateLED()`

**Purpose**: Update LED state based on WiFi connection status

**Behavior**:
- If WiFi disconnected: Blink at 5 Hz
- If WiFi connected: Solid ON

**Requirements Implemented** (TRD R9-R11):
- R9: LED blink pattern (5 Hz = 100ms on/off)
- R10: State determination based on `state.wifiConnected`
- R11: Non-blocking control (no delays)

**Implementation**: Uses same blink formula as connection phase:
```cpp
digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
```

The pattern repeats every 200ms with 5 Hz frequency.

### `void checkWiFi()`

**Purpose**: Monitor WiFi connection and attempt reconnection if dropped

**Behavior**:
1. Rate-limited to every 5 seconds (using static variable)
2. Check `WiFi.status()` against `WL_CONNECTED`
3. If disconnected: Print message and call `WiFi.reconnect()`
4. Update `state.wifiConnected` accordingly

**Requirements Implemented** (TRD R12-R14):
- R12: Status check
- R13: Reconnection logic (non-blocking)
- R14: Rate limiting (5-second intervals)

**Key Detail**: `WiFi.reconnect()` is non-blocking and returns immediately. The ESP32 WiFi stack handles reconnection in background, typically taking 5-30 seconds.

### `void setup()`

**Purpose**: Initialize all hardware and establish WiFi connection

**Sequence** (TRD R15-R20):
1. Initialize serial at 115200 baud
2. Print startup banner with sensor ID
3. Configure GPIO for LED output (initial state: LOW)
4. Attempt WiFi connection via `connectWiFi()`
5. If WiFi fails: Print diagnostic information and enter error loop (rapid LED blink forever)
6. Initialize UDP socket on ephemeral port (port 0)
7. Print "Setup complete" message
8. Initialize `state.lastMessageTime` for first message

**Error Handling**: If WiFi fails in setup:
```
ERROR: WiFi connection failed
WiFi status code: [code]
Possible causes:
  - Wrong SSID or password
  - Network is 5GHz (ESP32 requires 2.4GHz)
  - Out of range
  - Router offline
Entering error state (rapid blink)...
```

Then LED blinks rapidly forever until power cycle (no recovery in Phase 1).

### `void loop()`

**Purpose**: Main program loop - send messages at 1 Hz, monitor WiFi, update LED

**Sequence** (TRD R21-R27):
1. Call `checkWiFi()` - monitor connection status (rate-limited internally)
2. Get current time: `currentTime = millis()`
3. Check if message interval elapsed: `if (currentTime - state.lastMessageTime >= 1000)`
4. If interval elapsed:
   - Generate test IBI: `800 + (messageCounter % 200)` (creates sequence 800-999ms)
   - Send OSC message via `sendHeartbeatOSC(test_ibi)`
   - Update timing: `state.lastMessageTime = currentTime`
   - Increment counter: `state.messageCounter++`
   - Print to serial: "Sent message #N: /heartbeat/ID IBI"
5. Update LED: `updateLED()`
6. Delay 10ms to allow ESP32 background tasks
7. Loop repeats approximately every 10ms

**Timing Accuracy**: The 1 Hz message rate is maintained by checking elapsed time:
```cpp
// This works correctly even after millis() rolls over at 49.7 days
// due to unsigned integer arithmetic
if (currentTime - state.lastMessageTime >= TEST_MESSAGE_INTERVAL_MS) {
    // Send message
}
```

**Serial Output Format** (TRD R25):
```
Sent message #1: /heartbeat/0 800
Sent message #2: /heartbeat/0 801
Sent message #3: /heartbeat/0 802
...
Sent message #200: /heartbeat/0 999
Sent message #201: /heartbeat/0 800
```

The IBI values repeat every 200 messages (deterministic test pattern).

---

## State Management

### SystemState Structure

```cpp
struct SystemState {
    bool wifiConnected;           // Current WiFi connection status
    unsigned long lastMessageTime;  // millis() of last message sent
    uint32_t messageCounter;      // Total messages sent (rolls over at UINT32_MAX)
};
```

**State Transitions**:
- `wifiConnected`: Set true in `connectWiFi()` or `checkWiFi()`, set false on disconnection
- `lastMessageTime`: Updated each time message sent, used to trigger next message
- `messageCounter`: Incremented after each message, used to generate test IBI values

**Global Instance**:
```cpp
SystemState state = {false, 0, 0};  // Initial: disconnected, no timing, no messages
```

---

## Configuration Guide

### Network Configuration

Edit these constants in `src/main.cpp` before uploading to hardware:

```cpp
const char* WIFI_SSID = "your-network-name";  // Your 2.4GHz WiFi SSID
const char* WIFI_PASSWORD = "your-password";  // WiFi password
const IPAddress SERVER_IP(192, 168, 1, 100);  // Your dev machine's IP
const uint16_t SERVER_PORT = 8000;            // OSC receiver port
```

**Critical**:
- SSID must be 2.4GHz network (ESP32 does not support 5GHz)
- SERVER_IP must be your development machine's IP on the WiFi network, NOT 127.0.0.1
- Find your machine's IP:
  - Linux: `ip addr show` (look for wlan0 or eth0 inet address)
  - macOS: System Preferences → Network → WiFi → Advanced
  - Windows: `ipconfig` (IPv4 Address under WiFi adapter)

### Hardware Configuration

```cpp
const int STATUS_LED_PIN = 2;  // GPIO 2 (standard built-in LED on ESP32 DevKit)
```

Adjust if using different board or external LED.

### System Configuration

```cpp
const int SENSOR_ID = 0;              // 0-3, unique per ESP32 unit
const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;  // 1 second between messages
const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 seconds to connect
```

**For multi-unit deployment**:
- Unit 1: SENSOR_ID = 0
- Unit 2: SENSOR_ID = 1
- Unit 3: SENSOR_ID = 2
- Unit 4: SENSOR_ID = 3

Keep WiFi credentials identical across all units.

---

## Implementation Details

### Compilation Results

- **Source File**: `/home/user/corazonn/firmware/heartbeat_phase1/src/main.cpp`
- **Lines of Code**: 244
- **Functions**: 6 (connectWiFi, sendHeartbeatOSC, updateLED, checkWiFi, setup, loop)
- **Configuration Constants**: 8
- **Data Structures**: 1 (SystemState)
- **Global Objects**: 2 (WiFiUDP udp, SystemState state)

### Memory Usage

- **RAM**: 45,080 bytes (13.8% of 327 KB available)
- **Flash**: 738,157 bytes (56.3% of 1,310 KB available)
- **Binary Size**: 469,645 bytes

Headroom available for Phase 2 features (sensor input, beat detection).

### Build Performance

- **Clean Build**: 36.25 seconds (includes library download)
- **Rebuild (no changes)**: 3.23 seconds
- **First Compile (after PlatformIO setup)**: ~40 seconds total

### Code Organization

```
main.cpp Structure:
├── File Header (purpose, version)
├── INCLUDES (4 headers)
├── CONFIGURATION (8 constants)
├── GLOBAL STATE (SystemState struct, global objects)
├── FUNCTION DECLARATIONS (4 functions forward-declared)
├── FUNCTION IMPLEMENTATIONS
│   ├── connectWiFi()
│   ├── sendHeartbeatOSC()
│   ├── updateLED()
│   └── checkWiFi()
└── ARDUINO CORE
    ├── setup()
    └── loop()
```

Each section has clear header comments with section separators.

### Dependencies

**Libraries**:
- `Arduino.h` - Arduino framework (auto-included by PlatformIO)
- `WiFi.h` - ESP32 WiFi stack (built-in)
- `WiFiUdp.h` - UDP networking (built-in)
- `OSCMessage.h` - OSC protocol (from CNMAT/OSC v3.5.8 GitHub)

**External Dependencies**:
- PlatformIO CLI (for building and uploading)
- ESP32 platform (espressif32)
- 2.4GHz WiFi network
- Development machine running Python OSC receiver (for testing)

---

## Testing & Verification

### Test Results Summary

**Status**: ✅ ALL TESTS PASSED

- **Compilation Tests**: SUCCESS (no errors, no warnings)
- **Unit Tests**: 71/71 PASSED (100%)
- **Code Quality**: Excellent
- **TRD Requirements**: All 27 (R1-R27) verified

### Compilation Verification

```
Platform: espressif32
Board: esp32dev
Framework: arduino

Memory Usage:
  RAM:   13.8% (45,080 bytes / 327,680 bytes)
  Flash: 56.3% (738,157 bytes / 1,310,720 bytes)

Status: SUCCESS ✅
```

### Unit Tests Breakdown

| Category | Tests | Status |
|----------|-------|--------|
| Compilation | 4 | ✅ 4/4 |
| Configuration | 9 | ✅ 9/9 |
| Global State | 6 | ✅ 6/6 |
| Function Signatures | 7 | ✅ 7/7 |
| Logic Verification | 26 | ✅ 26/26 |
| Integration | 5 | ✅ 5/5 |
| Code Quality | 5 | ✅ 5/5 |
| TRD Compliance | 10 | ✅ 10/10 |
| **TOTAL** | **71** | **✅ 71/71** |

### Code Review Approval

**Status**: APPROVED FOR DEPLOYMENT

**Quality Score**: 9.5/10

**Verified By**:
- Zeppo: All 27 requirements verified as satisfied
- Chico: Implementation quality approved
- Groucho: Architectural soundness validated

---

## Hardware Deployment

### Pre-Deployment Checklist

Before uploading to ESP32:

- [ ] Configure WIFI_SSID for your 2.4GHz network
- [ ] Configure WIFI_PASSWORD with correct credentials
- [ ] Configure SERVER_IP to your development machine's IP
- [ ] Verify SENSOR_ID (0-3, unique per unit)
- [ ] ESP32 connected via USB to computer
- [ ] Serial drivers installed (USB to UART chip)
- [ ] PlatformIO CLI installed and verified

### Compilation Command

```bash
cd /home/user/corazonn/firmware/heartbeat_phase1
pio run
```

Expected output:
```
Processing esp32dev...
Building .pio/build/esp32dev/firmware.bin
RAM: [=         ] 13.8% (used 45,080 bytes from 327,680 bytes)
Flash: [====     ] 56.3% (used 738,157 bytes from 1,310,720 bytes)
========================= [SUCCESS] ========================
```

### Upload Command

```bash
pio run --target upload
```

Expected output:
```
Configuring upload protocol...
Auto-detected: /dev/ttyUSB0
Uploading .pio/build/esp32dev/firmware.bin
...
Hard resetting via RTS pin...
```

### Serial Monitoring

```bash
pio device monitor
```

Expected output (first 10 seconds):
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

Exit monitor: Ctrl+C

### Validation Against Testing Infrastructure

**Hardware Test Procedure**:

1. **Start Python Receiver** (in separate terminal):
   ```bash
   python3 /home/user/corazonn/testing/osc_receiver.py --port 8000
   ```
   Expected: "OSC Receiver listening on 0.0.0.0:8000"

2. **Monitor ESP32 Serial Output**:
   ```bash
   pio device monitor
   ```
   Verify messages appear at ~1 Hz

3. **Monitor Receiver Output**:
   Expected:
   ```
   [/heartbeat/0] IBI: 800ms, BPM: 75.0
   [/heartbeat/0] IBI: 801ms, BPM: 74.9
   [/heartbeat/0] IBI: 802ms, BPM: 74.8
   ...
   --- Statistics (10.0s) ---
   Total: 10, Valid: 10, Invalid: 0
   ```
   Verify: Invalid count = 0

4. **Verify LED Behavior**:
   - During "Connecting to WiFi": LED blinks rapidly (5 Hz)
   - After "Connected!": LED solid ON

5. **Run Stability Test**:
   - Let receiver and ESP32 run for 5+ minutes
   - Verify continuous message flow (no gaps > 2 seconds)
   - Verify no WiFi reconnections or crashes
   - Verify receiver maintains 0 invalid messages

---

## Troubleshooting

### Compilation Errors

**Error: "WiFi.h: No such file or directory"**
- Cause: ESP32 platform not installed
- Solution: `pio pkg install --global --platform espressif32`

**Error: "OSCMessage.h: No such file or directory"**
- Cause: OSC library not installed
- Solution: Verify `platformio.ini` has `lib_deps = https://github.com/CNMAT/OSC.git`
- Run: `pio pkg install` to download dependencies

**Error: "multiple definition of 'udp'"**
- Cause: Global WiFiUDP declared twice
- Solution: Ensure `WiFiUDP udp;` appears only once

### Upload Issues

**Error: "Failed to connect to ESP32"**
- Try: Hold BOOT button during upload
- Try: Use lower upload speed (edit platformio.ini: `upload_speed = 115200`)
- Try: Different USB cable (must be data cable, not charge-only)

**Error: "Port not found"**
- Windows: Install CP2102 or CH340 driver from silicon labs website
- Linux: `sudo usermod -a -G dialout $USER` (then logout/login)
- macOS: May need driver approval in Security & Privacy

### Runtime Issues

**ESP32 connects but receiver shows nothing**
- Check 1: SERVER_IP correct? (not 127.0.0.1, must be dev machine's IP)
- Check 2: Firewall blocking port 8000?
  - Linux: `sudo ufw allow 8000/udp`
  - Windows: Add Python to Windows Defender Firewall exceptions
- Check 3: Receiver running? Should print "listening on 0.0.0.0:8000"

**LED doesn't blink during connection**
- Check: STATUS_LED_PIN correct for your board? (GPIO 2 is standard)
- Check: LED physically connected? (test with external LED on different pin)

**"WiFi connection timeout" message**
- Check 1: SSID correct? (case-sensitive, exact match)
- Check 2: Password correct? (test on phone/laptop first)
- Check 3: Network is 2.4GHz? (ESP32 doesn't support 5GHz)
- Check 4: In range? (move ESP32 closer to router)

**Messages stop after several minutes**
- Check 1: "WiFi disconnected" messages in serial output? (WiFi unstable)
  - Try different router channel (less congestion)
  - Move ESP32 closer to router
- Check 2: Startup banner reappearing? (ESP32 resetting)
  - May indicate power issue
  - Try powered USB hub or external 5V supply

---

## Design Decisions

### Non-Blocking Architecture

**Decision**: Use `millis()` for all timing instead of blocking delays in loop()

**Rationale**:
- Allows WiFi stack to continue operating in background
- Enables quick LED updates without visible delay
- Maintains consistent message rate (1 Hz)
- Typical embedded systems pattern

**Alternative Considered**: Task-based system (FreeRTOS)
- Not needed for Phase 1 (single responsibility)
- Adds complexity and memory overhead
- Non-blocking approach is simpler and adequate

### Single Global State Struct

**Decision**: Use `SystemState` struct with 3 fields instead of separate global variables

**Rationale**:
- Groups related state together (cohesion)
- Easier to understand program state at a glance
- Simpler to extend with new state in future phases
- Easy to serialize for logging or remote sync

### Fire-and-Forget UDP

**Decision**: No acknowledgment or retry logic for OSC messages

**Rationale**:
- UDP is connectionless (no acknowledgment mechanism)
- Phase 1 is test messages (not critical data)
- Simplifies code and reduces latency
- Acceptable for heartbeat monitoring (some message loss tolerable)

**Future Alternative**: TCP or MQTT for critical data (Phase 2+)

### 5 Hz LED Blink Pattern

**Decision**: Blink at 5 Hz (100ms on/off) during WiFi connection

**Rationale**:
- Provides clear visual feedback (not too fast to see)
- Uses simple formula: `(millis() / 100) % 2`
- Matches common embedded system conventions
- No blocking delays (non-blocking implementation)

### Test IBI Generation

**Decision**: Generate deterministic sequence 800-999ms instead of random values

**Rationale**:
- Reproducible for testing (same sequence every time)
- Easier to validate message flow (can predict values)
- Repeats every 200 messages (coincides with BPM range 60-75)
- Simulates realistic heart rate (60-75 BPM = 800-1000ms IBI)

---

## Future Enhancements

### Phase 2: Sensor Input

Add analog sensor reading on GPIO 32:
- Read sensor at 50 Hz
- Implement simple threshold-based beat detection
- Replace test IBI with sensor-derived values
- Add confidence metric to OSC message

### Phase 3: Advanced Features

- Persistent WiFi reconnection (not just during setup)
- Adjustable message rate (not fixed at 1 Hz)
- Configuration web interface
- Over-the-air (OTA) updates
- Data logging to SD card

### Phase 4: Hardware Integration

- Multiple sensor inputs
- OLED display for status
- Battery power management
- Enclosure and mounting

---

## Files & References

**Implementation File**:
- `/home/user/corazonn/firmware/heartbeat_phase1/src/main.cpp` (244 lines)

**Configuration File**:
- `/home/user/corazonn/firmware/heartbeat_phase1/platformio.ini`

**Test Results**:
- `/home/user/corazonn/TEST_RESULTS_COMPONENT_7.7.md` (complete test report)

**Technical Reference Document**:
- `/home/user/corazonn/../reference/phase1-firmware-trd.md` (sections 4-7)

**Related Component Documentation**:
- `/home/user/corazonn/docs/firmware/guides/phase1-03-wifi-connection.md`
- `/home/user/corazonn/docs/firmware/guides/phase1-04-osc-messaging.md`

**Testing Infrastructure**:
- `/home/user/corazonn/testing/osc_receiver.py`
- `/home/user/corazonn/firmware/heartbeat_phase1/TEST_SUITE_GUIDE.md`

---

## Summary

Component 7.7 implements a complete, tested, and approved ESP32 firmware that:
- Connects reliably to WiFi networks (with 30-second timeout and automatic reconnection)
- Sends OSC heartbeat messages at 1 Hz to a Python receiver
- Provides clear LED feedback (blinking during connection, solid when connected)
- Uses non-blocking architecture for responsive operation
- Passes all 71 unit tests (100% pass rate)
- Compiles with zero errors and zero warnings
- Uses 56.3% of available flash (738 KB of 1.3 MB)
- Uses 13.8% of available RAM (45 KB of 320 KB)

The firmware is ready for Phase 1 hardware deployment and testing.

---

**Document Version**: 1.0
**Status**: COMPLETE
**Generated**: 2025-11-09
**Review Status**: APPROVED FOR DEPLOYMENT (9.5/10 quality score)
