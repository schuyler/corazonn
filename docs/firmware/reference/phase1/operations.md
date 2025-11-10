# Phase 1 Firmware - Operations & Testing

[**Back to Index**](index.md)

**Version:** 3.0 | **Date:** 2025-11-09

Validation, testing procedures, troubleshooting, and success criteria.

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

**Step 2: Monitor ESP32 Serial Output**
```bash
# Open serial monitor in new terminal
pio device monitor
```
- Baud rate: 115200 (configured in platformio.ini)
- Or connect via USB battery for standalone operation (no serial monitoring)

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
- Cause: ESP32 platform not installed
- Solution: PlatformIO automatically installs the ESP32 platform based on platformio.ini
- Verify platformio.ini contains: `platform = espressif32`
- Run: `pio pkg install` to ensure all packages are installed

**Error: "OSCMessage.h: No such file or directory"**
- Cause: OSC library not installed
- Solution: Verify platformio.ini contains: `lib_deps = https://github.com/CNMAT/OSC.git`
- Run: `pio pkg install` to install library dependencies
- Note: Use GitHub repository directly (version 3.5.8+), not PlatformIO registry (outdated at 1.0.0)

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
  5. Check USB drivers installed (see overview.md section 0.1)

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
  - Driver links in overview.md section 0.1
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

**Related sections:**
- See [overview.md](overview.md) for prerequisites and project goals
- See [api-network.md](api-network.md), [api-messaging.md](api-messaging.md) for API details
- See [implementation.md](implementation.md) for build and deployment steps
