# Phase 1 Firmware - Overview

[**Back to Index**](index.md)

**Version:** 3.0 | **Date:** 2025-11-09
**Purpose:** Define ESP32 firmware requirements for WiFi connection and OSC messaging
**Audience:** Coding agent implementing ESP32 firmware
**Hardware:** ESP32-WROOM-32 or compatible
**Framework:** Arduino (via PlatformIO CLI)
**Toolchain:** PlatformIO CLI (command-line compilation, upload, monitoring)

---

## 0. Prerequisites

### 0.1 PlatformIO CLI Setup

**MUST complete before writing any code:**

**Step 1: Install PlatformIO CLI**

**Option A: Via pip (Recommended)**
```bash
pip install --upgrade platformio
pio --version  # Verify installation
```

**Option B: Via installer script**
```bash
curl -fsSL https://raw.githubusercontent.com/platformio/platformio-core-installer/master/get-platformio.py -o get-platformio.py
python3 get-platformio.py

# Add to PATH (~/.bashrc or ~/.zshrc)
export PATH=$PATH:~/.platformio/penv/bin
```

**Option C: Via package manager**
```bash
# macOS
brew install platformio

# Linux (Debian/Ubuntu)
sudo apt-get install platformio
```

**Step 2: Install ESP32 Platform**
```bash
pio pkg install --global --platform espressif32
pio pkg list --global --only-platforms
# Should show: espressif32 @ X.X.X
```

**Step 3: Connect ESP32 Hardware**

1. Connect ESP32 to computer via USB cable
2. Verify port detection:
   ```bash
   pio device list
   ```
   - Windows: COMX (e.g., COM3, COM4)
   - macOS: /dev/cu.usbserial-XXXX
   - Linux: /dev/ttyUSB0 or /dev/ttyACM0

**USB Drivers (if needed):**
- CP2102: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- CH340: http://www.wch-ic.com/downloads/CH341SER_ZIP.html
- Linux: Add user to dialout group: `sudo usermod -a -G dialout $USER`

**Step 4: Verify PlatformIO Setup**
```bash
mkdir -p /tmp/pio-test && cd /tmp/pio-test
pio project init --board esp32dev
pio run  # Should compile
cd .. && rm -rf /tmp/pio-test
```

### 0.2 Testing Infrastructure Setup

**MUST be completed from separate TRD:**
- ✅ Python OSC receiver implemented and tested
- ✅ Receiver runs on port 8000
- ✅ Can see messages when simulator runs

**Verify receiver is working:**
```bash
# Terminal 1: Start receiver
python3 osc_receiver.py --port 8000

# Should print: "OSC Receiver listening on 0.0.0.0:8000"
```

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

## 1. Objective

Implement ESP32 firmware that connects to WiFi and sends test OSC messages. Validates communication pipeline before adding sensor hardware.

**Deliverables:**
- Single `main.cpp` source file (PlatformIO structure)
- Compiles for ESP32 target
- Connects to specified WiFi network
- Sends OSC heartbeat messages at 1 Hz
- LED indicates connection status
- Validated against testing infrastructure

**Success Criteria:**
- Firmware uploads to ESP32 without errors
- Connects to WiFi within 30 seconds
- Python receiver receives messages
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

**Continue learning:**
- See [configuration.md](configuration.md) for library and constant setup
- See [api-network.md](api-network.md) for WiFi functions
- See [implementation.md](implementation.md) for code structure
