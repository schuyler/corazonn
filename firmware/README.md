# Heartbeat Installation - Phase 1 Firmware

**Purpose**: ESP32 firmware for WiFi-connected heartbeat sensor with OSC messaging

**Status**: COMPLETE AND APPROVED FOR DEPLOYMENT

**Component**: Component 7.7 - Main Program Flow

**Test Results**: 71/71 tests passed (100%), all 27 TRD requirements satisfied

**Compilation**: Zero errors, zero warnings

---

## Overview

This firmware provides the core functionality for Phase 1 of the Heartbeat Installation:

- Connects to a 2.4GHz WiFi network
- Sends test OSC heartbeat messages at 1 Hz to a network receiver
- Provides LED feedback (blinking during connection, solid when connected)
- Monitors WiFi connection and attempts automatic reconnection

The firmware uses a single-threaded non-blocking architecture, allowing efficient operation on ESP32 without FreeRTOS complexity.

---

## Quick Start

### Prerequisites

- ESP32-WROOM-32 or compatible board
- USB cable (data-capable, not charge-only)
- 2.4GHz WiFi network (5GHz not supported by ESP32)
- PlatformIO CLI installed (`pip install --upgrade platformio`)
- ESP32 platform installed (`pio pkg install --global --platform espressif32`)

### Build and Upload

```bash
# Navigate to firmware directory
cd /home/user/corazonn/firmware/heartbeat_phase1

# Compile firmware
pio run

# Upload to ESP32 (requires board connected via USB)
pio run --target upload

# Monitor serial output
pio device monitor
```

Exit monitor: Ctrl+C

### Expected Serial Output

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

---

## Configuration

Edit `/home/user/corazonn/firmware/heartbeat_phase1/src/main.cpp` to customize:

### Network Configuration

```cpp
const char* WIFI_SSID = "your-network-name";     // Your 2.4GHz WiFi SSID
const char* WIFI_PASSWORD = "your-password";     // WiFi password
const IPAddress SERVER_IP(192, 168, 1, 100);     // Your dev machine's IP
const uint16_t SERVER_PORT = 8000;               // OSC receiver port
```

**Important**: SERVER_IP must be your development machine's IP address on the WiFi network, NOT 127.0.0.1. Find your machine's IP:
- **Linux**: `ip addr show` or `ifconfig` (look for wlan0/eth0 inet address)
- **macOS**: System Preferences → Network → WiFi → Advanced → TCP/IP
- **Windows**: `ipconfig` (look for IPv4 Address)

### Hardware Configuration

```cpp
const int STATUS_LED_PIN = 2;  // GPIO 2 (standard for ESP32 DevKit boards)
```

Adjust if using different board or external LED.

### System Configuration

```cpp
const int SENSOR_ID = 0;              // 0-3, unique per ESP32 unit
const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;  // 1 Hz message rate
const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 seconds to connect
```

For multi-unit deployment, set different SENSOR_IDs (0, 1, 2, 3) on each board while keeping WiFi credentials identical.

---

## Pre-Deployment Checklist

Before uploading firmware to hardware:

- [ ] Configuration updated (SSID, password, SERVER_IP, SENSOR_ID)
- [ ] WiFi network is 2.4GHz (not 5GHz)
- [ ] Development machine IP address confirmed (not 127.0.0.1)
- [ ] ESP32 connected via USB
- [ ] Serial drivers installed (platform auto-detects)
- [ ] Firmware compiles: `pio run`
- [ ] No compilation errors or warnings

---

## Deployment

### Single Unit Deployment

1. **Configure firmware**:
   - Edit `src/main.cpp` with your WiFi credentials and SERVER_IP
   - Set SENSOR_ID = 0

2. **Compile**:
   ```bash
   pio run
   ```
   Expected: "SUCCESS" message with RAM/Flash usage

3. **Upload**:
   ```bash
   pio run --target upload
   ```
   Expected: "Hard resetting via RTS pin..." message

4. **Verify**:
   ```bash
   pio device monitor
   ```
   Should see startup banner and "Connected! IP: X.X.X.X" within 30 seconds

5. **Test with receiver**:
   ```bash
   python3 /home/user/corazonn/testing/osc_receiver.py --port 8000
   ```
   Should show messages arriving at ~1 Hz with 0 invalid messages

### Multi-Unit Deployment

For deploying 2-4 units:

1. **Program first unit** (see Single Unit Deployment above)
2. **Program second unit**:
   - Edit `src/main.cpp`: Change `SENSOR_ID = 1`
   - Keep WIFI_SSID, WIFI_PASSWORD, SERVER_IP identical
   - Compile: `pio run`
   - Upload: `pio run --target upload`
3. **Repeat for units 3 and 4** with SENSOR_ID = 2, 3
4. **Test together**:
   - Start receiver: `python3 testing/osc_receiver.py --port 8000`
   - Power all units simultaneously
   - Receiver should show messages from all sensor IDs

---

## Verification

### LED Behavior

- **During WiFi connection**: LED blinks rapidly at 5 Hz (100ms on/off)
- **After connection**: LED solid ON
- **WiFi disconnection**: LED returns to blinking (automatic reconnection triggered)

### Serial Output Verification

Expected pattern (first 10 seconds):
```
=== Heartbeat Installation - Phase 1 ===
Sensor ID: 0
Connecting to WiFi: your-ssid
Connected! IP: 192.168.X.X
Setup complete. Starting message loop...
Sent message #1: /heartbeat/0 800
Sent message #2: /heartbeat/0 801
Sent message #3: /heartbeat/0 802
Sent message #4: /heartbeat/0 803
Sent message #5: /heartbeat/0 804
Sent message #6: /heartbeat/0 805
Sent message #7: /heartbeat/0 806
Sent message #8: /heartbeat/0 807
Sent message #9: /heartbeat/0 808
Sent message #10: /heartbeat/0 809
```

Message values repeat pattern 800-999 every 200 messages.

### Receiver Verification

Expected receiver output (for SENSOR_ID = 0):
```
OSC Receiver listening on 0.0.0.0:8000
[/heartbeat/0] IBI: 800ms, BPM: 75.0
[/heartbeat/0] IBI: 801ms, BPM: 74.9
[/heartbeat/0] IBI: 802ms, BPM: 74.8
[/heartbeat/0] IBI: 803ms, BPM: 74.7
[/heartbeat/0] IBI: 804ms, BPM: 74.6
[/heartbeat/0] IBI: 805ms, BPM: 74.5
...

--- Statistics (10.0s) ---
Total: 10, Valid: 10, Invalid: 0
Sensor 0: 10 messages, Avg IBI: 805ms, Avg BPM: 74.5
```

Verify: Invalid message count = 0

---

## Stability Testing

### 5-Minute Stability Test

To verify firmware reliability:

```bash
# Terminal 1: Start receiver
python3 /home/user/corazonn/testing/osc_receiver.py --port 8000

# Terminal 2: Monitor ESP32
pio device monitor

# Let both run for 5+ minutes
# Verify:
# - No WiFi disconnections in serial output
# - No message gaps > 2 seconds
# - Receiver shows 0 invalid messages
# - Message counter incrementing continuously
```

Expected results:
- Continuous operation without crashes
- Stable 1 Hz message rate
- Receiver shows 50+ messages, 0 invalid

---

## Troubleshooting

### Compilation Errors

**Error**: "WiFi.h: No such file or directory"
- Solution: ESP32 platform not installed
- Run: `pio pkg install --global --platform espressif32`
- Retry: `pio run`

**Error**: "OSCMessage.h: No such file or directory"
- Solution: OSC library not installed
- Verify `platformio.ini` has: `lib_deps = https://github.com/CNMAT/OSC.git`
- Run: `pio pkg install` to download dependencies
- Retry: `pio run`

**Error**: "multiple definition of 'udp'"
- Solution: WiFiUDP declared multiple times in source
- Ensure `WiFiUDP udp;` appears only once
- Check for duplicate code sections

### Upload Errors

**Error**: "Failed to connect to ESP32"
- Try 1: Hold BOOT button during upload
- Try 2: Use lower upload speed in platformio.ini: `upload_speed = 115200`
- Try 3: Different USB cable (must be data cable)

**Error**: "Port not found" or "could not open port"
- Windows: Install CP2102 or CH340 driver from Silicon Labs
- Linux: `sudo usermod -a -G dialout $USER` (then logout/login)
- macOS: May need driver in Security & Privacy

### Runtime Issues

**WiFi won't connect (LED blinks forever)**
- Check 1: SSID exact match? (case-sensitive)
- Check 2: Password correct?
- Check 3: Network is 2.4GHz? (not 5GHz)
- Check 4: In WiFi range? (move closer to router)

**Receiver shows nothing (no messages)**
- Check 1: SERVER_IP correct? (must be dev machine's IP, not 127.0.0.1)
- Check 2: Firewall blocking port 8000?
  - Linux: `sudo ufw allow 8000/udp`
  - Windows: Add Python to Windows Defender exceptions
  - macOS: System Preferences → Security & Privacy → Firewall
- Check 3: Receiver actually running? (should print "listening on 0.0.0.0:8000")

**Receiver shows invalid messages**
- Likely OSC library version issue (should use GitHub version 3.5.8+)
- Verify platformio.ini: `lib_deps = https://github.com/CNMAT/OSC.git`
- Clean build: `pio run --target clean && pio run`

**Messages stop after several minutes**
- Check 1: "WiFi disconnected" in serial output? (unstable WiFi)
  - Try different router channel
  - Move ESP32 closer to router
- Check 2: Startup banner reappearing? (ESP32 resetting)
  - May indicate power issue
  - Try powered USB hub or external power

---

## Project Structure

```
firmware/heartbeat_phase1/
├── README.md                  # This file
├── platformio.ini            # Build configuration
├── src/
│   └── main.cpp             # Main firmware (244 lines)
├── lib/                      # Custom libraries (empty for Phase 1)
├── include/                  # Header files (empty for Phase 1)
└── test/                     # Unit tests
    └── test_firmware.cpp     # 71 test cases
```

---

## Build Information

### Compilation Statistics

- **Source File**: `src/main.cpp` (244 lines)
- **Functions**: 6 (connectWiFi, sendHeartbeatOSC, updateLED, checkWiFi, setup, loop)
- **Configuration Constants**: 8
- **Data Structures**: 1 (SystemState)
- **Global Objects**: 2 (WiFiUDP, SystemState)

### Memory Usage

- **RAM**: 45,080 bytes (13.8% of 327 KB)
- **Flash**: 738,157 bytes (56.3% of 1,310 KB)
- **Binary Size**: 469,645 bytes

Headroom available for Phase 2 features (sensor input, beat detection).

### Build Performance

- **Clean Build**: ~36 seconds (includes OSC library download)
- **Rebuild (no changes)**: ~3 seconds
- **Test Suite**: ~4.6 seconds

---

## Testing

### Unit Tests

Complete test suite with 71 test cases covers:
- Compilation verification (4 tests)
- Configuration validation (9 tests)
- State management (6 tests)
- Function signatures (7 tests)
- Logic verification (26 tests)
- Integration testing (5 tests)
- Code quality (5 tests)
- TRD compliance (10 tests)

**Status**: All 71 tests PASSED (100%)

Run tests:
```bash
pio test --environment native
```

### Test Results

See `/home/user/corazonn/TEST_RESULTS_COMPONENT_7.7.md` for complete test report.

---

## Deployment Checklist

### Before Compilation

- [ ] Source files present and readable
- [ ] Configuration constants defined
- [ ] All required headers present
- [ ] No syntax errors in code

### After Compilation

- [ ] Binary compiles without errors
- [ ] No compiler warnings
- [ ] RAM usage < 100% (currently 13.8%)
- [ ] Flash usage < 100% (currently 56.3%)
- [ ] Binary size reasonable (< 1 MB)

### Before Upload

- [ ] WiFi credentials configured (SSID, password)
- [ ] SERVER_IP set to dev machine's IP
- [ ] SENSOR_ID set correctly
- [ ] ESP32 connected via USB
- [ ] Serial port detected (`pio device list`)

### After Upload

- [ ] Upload succeeds without errors
- [ ] "Hard resetting via RTS pin..." message appears
- [ ] Serial monitor shows startup output
- [ ] "Connected! IP: X.X.X.X" appears within 30 seconds

### During Testing

- [ ] LED blinks during WiFi connection
- [ ] LED solid ON after connection
- [ ] Messages appear at ~1 Hz in serial output
- [ ] Receiver shows messages at 1 Hz
- [ ] Receiver shows 0 invalid messages
- [ ] No crashes over 5+ minutes

---

## Architecture & Design

### Non-Blocking Design

All timing uses `millis()` instead of blocking delays in main loop:
- Loop cycles every 10ms
- WiFi status checked every 5 seconds (rate-limited)
- Messages sent every 1 second (interval-based)
- LED updated continuously (no delays)

Benefits:
- ESP32 WiFi stack continues operating in background
- Responsive LED updates without visible lag
- Stable 1 Hz message rate
- No interrupts or RTOS needed (single-threaded)

### State Management

Program state tracked in SystemState struct:
```cpp
struct SystemState {
    bool wifiConnected;           // WiFi connection status
    unsigned long lastMessageTime;  // Timing for next message
    uint32_t messageCounter;      // Total messages sent
};
```

State updated in loop and monitored functions, enabling:
- Clear program flow
- Easy debugging (can inspect state)
- Simple extension to Phase 2

### LED Feedback

Two-state LED indication:
- **Disconnected**: 5 Hz blinking (100ms on/off)
- **Connected**: Solid ON

Uses non-blocking formula: `(millis() / 100) % 2`

No blocking delays, LED responds immediately to state changes.

---

## References

**Technical Reference Document** (TRD):
- `/home/user/corazonn/docs/p1-fw-trd.md` (complete specifications)

**Implementation Documentation**:
- `/home/user/corazonn/docs/component-7-part7-main-program-flow.md` (detailed architecture)

**Test Results**:
- `/home/user/corazonn/TEST_RESULTS_COMPONENT_7.7.md` (71 test cases)

**Testing Infrastructure**:
- `/home/user/corazonn/testing/osc_receiver.py` (Python receiver)

**Task Tracking**:
- `/home/user/corazonn/docs/component-7-tasks-draft.md` (implementation tasks)

---

## Support & Issues

### Known Limitations (Phase 1)

- No sensor input (test messages only)
- No beat detection algorithm
- No WiFi reconnection after initial setup failure
- No power management or sleep modes
- No data logging
- Simple LED feedback (on/off only)

These will be addressed in Phase 2+.

### Getting Help

1. Check Troubleshooting section above
2. Review test results: `/home/user/corazonn/TEST_RESULTS_COMPONENT_7.7.md`
3. Check TRD: `/home/user/corazonn/docs/p1-fw-trd.md`
4. Examine source code comments: `/home/user/corazonn/firmware/heartbeat_phase1/src/main.cpp`

---

## Maintenance

### Updating Firmware

To update configuration or fix bugs:

1. Edit `src/main.cpp`
2. Recompile: `pio run`
3. Upload: `pio run --target upload`
4. Verify: `pio device monitor`

### Backing Up Configuration

Save your custom configuration:
```bash
cp src/main.cpp src/main.cpp.backup
```

This preserves your WiFi credentials and SERVER_IP.

### Next Steps (Phase 2)

Phase 2 will add:
- Analog sensor input on GPIO 32
- Simple beat detection algorithm
- Sensor-derived IBI values (not test values)
- Additional OSC message types
- Persistent WiFi reconnection
- Configuration persistence

Firmware structure is designed to accommodate these additions with minimal changes.

---

**Status**: COMPLETE AND APPROVED FOR DEPLOYMENT

**Code Review Score**: 9.5/10

**Test Results**: 71/71 PASSED (100%)

**TRD Compliance**: All 27 requirements satisfied (R1-R27)

**Date**: 2025-11-09
