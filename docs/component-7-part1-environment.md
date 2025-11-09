# Component 7 - Part 1: Environment Ready

**Milestone**: PlatformIO environment set up and can compile empty ESP32 firmware

**Reference**: `docs/p1-fw-trd.md` Section 0 (Prerequisites)

**Estimated Time**: 15-20 minutes

**Success Criteria**: `pio run` compiles empty project successfully

---

## Prerequisites

- [ ] **Task 0.1**: Install PlatformIO CLI
  - Install via pip: `pip install --upgrade platformio`
  - Or via package manager: `brew install platformio` (macOS) or `sudo apt-get install platformio` (Linux)
  - Verify: `pio --version` shows version number
  - **Expected output**: `PlatformIO Core, version X.X.X`
  - **Status**: PlatformIO CLI installed

- [ ] **Task 0.2**: Install ESP32 platform
  - Run: `pio pkg install --global --platform espressif32`
  - Wait for download and installation (may take 2-5 minutes)
  - Verify: `pio pkg list --global --only-platforms`
  - **Expected output**: Shows `espressif32 @ X.X.X`
  - **Status**: ESP32 platform installed

- [ ] **Task 0.3**: Verify USB drivers and port access (Optional - needed for upload in Task 1.6)
  - **Note**: Part 1 only requires compilation (Task 1.5), not hardware. Can defer this until Part 3.
  - If ESP32-WROOM-32 hardware available:
    - Install USB drivers first:
      - **CP2102 driver**: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
      - **CH340 driver**: https://learn.sparkfun.com/tutorials/how-to-install-ch340-drivers/all
    - Connect ESP32 via USB cable to computer (use data-capable cable, not charge-only)
    - Run: `pio device list`
    - **Expected output**: Shows `/dev/ttyUSB0` (Linux), `/dev/cu.usbserial-XXXX` (macOS), or `COMX` (Windows)
    - **Linux users**: If no port visible, add to dialout group:
      ```bash
      sudo usermod -a -G dialout $USER
      # Then logout and login
      ```
    - **Status**: ESP32 detected on USB port
  - If no hardware available yet:
    - Skip to Task 0.4, complete Part 1 with compilation only
    - Hardware validation deferred to Part 3 (WiFi connectivity)

- [ ] **Task 0.4**: Verify testing infrastructure ready
  - Confirm Components 1-5 complete: Check `docs/tasks.md`
  - Test receiver: `python3 testing/osc_receiver.py --port 8000`
  - **Expected output**: "OSC Receiver listening on 0.0.0.0:8000"
  - Stop receiver: Ctrl+C
  - **Status**: Testing infrastructure confirmed working

---

## Project Initialization

- [ ] **Task 1.1**: Create firmware directory structure
  - Create directory: `mkdir -p /home/user/corazonn/firmware/heartbeat_phase1`
  - Change to directory: `cd /home/user/corazonn/firmware/heartbeat_phase1`
  - **Status**: Directory created

- [ ] **Task 1.2**: Initialize PlatformIO project
  - Run: `pio project init --board esp32dev`
  - Wait for initialization (downloads framework if needed, ~30 seconds)
  - Verify created files:
    ```bash
    ls -la
    # Should show: platformio.ini, src/, lib/, include/, .pio/
    ```
  - **Status**: PlatformIO project initialized

- [ ] **Task 1.3**: Configure platformio.ini
  - Edit `/home/user/corazonn/firmware/heartbeat_phase1/platformio.ini`
  - Replace contents with:
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
        cnmat/OSC@^1.3.7
    ```
  - Save file
  - **Status**: Configuration matches TRD requirements (R28-R29)

- [ ] **Task 1.4**: Create minimal main.cpp
  - Create file: `/home/user/corazonn/firmware/heartbeat_phase1/src/main.cpp`
  - Add minimal Arduino code:
    ```cpp
    #include <Arduino.h>

    void setup() {
      Serial.begin(115200);
      Serial.println("PlatformIO test successful");
    }

    void loop() {
      delay(1000);
    }
    ```
  - Save file
  - **Status**: Minimal firmware file created

---

## Validation

- [ ] **Task 1.5**: Compile empty firmware
  - Run: `pio run`
  - **Expected output**:
    ```
    Processing esp32dev (platform: espressif32; board: esp32dev; framework: arduino)
    ...
    Building .pio/build/esp32dev/firmware.bin
    RAM:   [          ]   3.2% (used 10456 bytes from 327680 bytes)
    Flash: [=         ]   5.1% (used 66789 bytes from 1310720 bytes)
    ========================= [SUCCESS] Took X.XX seconds =========================
    ```
  - **Status**: Compilation successful

- [ ] **Task 1.6**: Test upload to ESP32 (optional at this stage)
  - Ensure ESP32 connected via USB
  - Run: `pio run --target upload`
  - **Expected**: Upload completes, shows "Hard resetting via RTS pin..."
  - Open serial monitor: `pio device monitor`
  - **Expected serial output**: "PlatformIO test successful" repeating
  - Exit monitor: Ctrl+C
  - **Note**: Can skip this test and do it in Part 3 if hardware not available yet
  - **Status**: Upload verified (or skipped if no hardware)

---

## Milestone Checkpoint

**Environment Ready Checklist**:
- ✅ PlatformIO CLI installed and working
- ✅ ESP32 platform installed
- ✅ USB drivers working (ESP32 detected) - *Optional, can defer to Part 3*
- ✅ Testing infrastructure confirmed (Components 1-5)
- ✅ Project initialized with proper structure
- ✅ platformio.ini configured correctly
- ✅ Minimal firmware compiles successfully (required)
- ✅ OSC library dependency declared (will download on first use)

**Ready for Part 2**: Firmware skeleton with configuration constants and data structures

**Time Spent**: ______ minutes

**Issues Encountered**: _______________________

---

## Troubleshooting

**Problem: `pio: command not found`**
- Solution: PlatformIO not in PATH
  - If installed via pip, add to PATH: `export PATH=$PATH:~/.local/bin`
  - If installed via installer script: `export PATH=$PATH:~/.platformio/penv/bin`
  - Add to `~/.bashrc` or `~/.zshrc` to make permanent

**Problem: `pio device list` shows no devices**
- Solution: USB driver or permissions issue
  - Linux: Run `sudo usermod -a -G dialout $USER`, logout, login
  - macOS: Install CP2102 or CH340 driver from TRD Section 0.1
  - Windows: Install driver from Device Manager
  - Verify cable is data-capable (not charge-only)

**Problem: Compilation fails with "platform espressif32 not found"**
- Solution: Run `pio pkg install --global --platform espressif32` again
- Check internet connection (downloads ~200MB)

**Problem: OSC library download fails during compilation**
- Solution: Library will download on first compilation that needs it
- If fails: Check internet connection
- Manual install: `pio pkg install --library cnmat/OSC@^1.3.7`

---

**Next**: [Component 7 - Part 2: Structure Compiles](component-7-part2-skeleton.md)
