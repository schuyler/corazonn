# Phase 4 Configuration: Code Structure & Implementation

## 3. Implementation Approach

### 3.1 Code Structure

Organize Phase 4 firmware with clear separation of concerns.

**Option A: Extend Phase 3 (Recommended if Phase 3 exists)**
- Copy `firmware/heartbeat_phase3/` → `firmware/heartbeat_phase4/`
- Modify `sendHeartbeatOSC()` signature (add sensorIndex parameter)
- Remove any test message generation code
- Update `loop()` to use real beat triggers
- Validate integration

**Option B: Unified Implementation (If Phase 3 not implemented yet)**
- Implement Phase 3 + Phase 4 together in `firmware/heartbeat_phase4/`
- Follow Phase 3 TRD for beat detection algorithm
- Follow Phase 1 TRD for OSC messaging
- Integrate at `detectBeat()` → `sendHeartbeatOSC()` interface

**File Structure:**

```
firmware/heartbeat_phase4/
├── platformio.ini         # Build configuration (same as Phase 1/3)
├── src/
│   └── main.cpp          # Integrated firmware (Phase 3 + Phase 1)
├── include/
│   └── ssid.h            # WiFi credentials (untracked by git)
└── test/                 # Validation test documentation
```

### 3.2 Configuration Constants Consolidation

Phase 4 requires configuration from both Phase 1 (network) and Phase 3 (hardware/signal processing).

**Network Configuration (from Phase 1):**
```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS
const uint16_t SERVER_PORT = 8000;
```

**Hardware Configuration (from Phase 3):**
```cpp
const int SENSOR_PINS[4] = {32, 33, 34, 35};
const int NUM_SENSORS = 4;
const int STATUS_LED_PIN = 2;
const int ADC_RESOLUTION = 12;
```

**Signal Processing Configuration (from Phase 3):**
```cpp
const int SAMPLE_RATE_HZ = 50;
const int SAMPLE_INTERVAL_MS = 20;
const int MOVING_AVG_SAMPLES = 5;
const float BASELINE_DECAY_RATE = 0.1;
const int BASELINE_DECAY_INTERVAL = 150;
```

**Beat Detection Configuration (from Phase 3):**
```cpp
const float THRESHOLD_FRACTION = 0.6;
const int MIN_SIGNAL_RANGE = 50;
const unsigned long REFRACTORY_PERIOD_MS = 300;
const int FLAT_SIGNAL_THRESHOLD = 5;
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;
```

**Debug Configuration:**
```cpp
#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose
```

### 3.3 Data Structures

Phase 4 uses data structures from Phase 3 to track per-sensor state.

**Sensor State Structure:**

```cpp
struct SensorState {
    int rawValue;                      // Current ADC reading
    int filteredValue;                 // After moving average
    int baseline;                      // Adaptive baseline
    int baselineMin, baselineMax;      // Range for threshold calculation

    unsigned long lastBeatTime;        // Timestamp of last detected beat
    bool firstBeatDetected;            // Flag: first beat yet?

    unsigned long lastBaselineUpdate;  // For baseline adaptation timing
    unsigned long lastADCReadTime;     // For sampling rate control
    unsigned long lastDisconnectCheck; // For detecting disconnected sensors

    // Moving average circular buffer
    int filterBuffer[5];
    int filterIndex;
};
```

**System State Structure:**

```cpp
struct SystemState {
    bool wifiConnected;                // Current WiFi connection status
    unsigned long lastWiFiCheck;       // Last time we checked connection
    bool beatDetectedThisLoop;         // Flag for LED feedback
    unsigned long bootTime;            // System boot timestamp
};
```

### 3.4 Code Organization

**main.cpp sections (recommended order):**

```cpp
// 1. Includes and configuration constants
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCMessage.h>
// ... network and hardware config ...

// 2. Global state structures
SensorState sensors[4];
SystemState system;
WiFiUDP udp;

// 3. Hardware initialization functions
void initializeSensors()
void initializeWiFi()
void initializeLED()

// 4. Core beat detection functions
void sampleSensors()
void filterSignal(int sensorIndex)
void updateBaseline(int sensorIndex)
void detectBeat(int sensorIndex)

// 5. OSC transmission (Phase 1 integration)
void sendHeartbeatOSC(int sensorIndex, int ibi_ms)

// 6. System functions
void updateLED()
void checkWiFiStatus()
void loop()
void setup()
```

### 3.5 Dependency Summary

**From Phase 1 (Required):**
- WiFi connection code
- OSC message library (library for OSCMessage)
- UDP transmission implementation
- `sendHeartbeatOSC()` function signature and logic

**From Phase 3 (Required):**
- ADC sampling routine (50Hz)
- Moving average filter implementation
- Baseline tracking algorithm
- Beat detection threshold logic
- Refractory period enforcement
- Per-sensor state management
- LED feedback logic

**Phase 4 Additions (New):**
- Integration of Phase 1 and Phase 3
- Modified `sendHeartbeatOSC(int sensorIndex, int ibi_ms)` signature
- Removal of test message generation
- Production validation procedures

### 3.6 Libraries Required

Add to `platformio.ini`:

```ini
lib_deps =
    arduino-libraries/WiFi
    arduino-libraries/WiFiUdp
    1883@1.0.0  ; OSCMessage by CNMAT
```

**Library Versions:**
- WiFi: Built-in to ESP32 Arduino framework
- WiFiUdp: Built-in to ESP32 Arduino framework
- OSCMessage: Version 1.0.0 or later (CNMAT library)

### 3.7 Build Configuration

**platformio.ini settings for ESP32:**

```ini
[env:esp32dev]
platform = espressif32@6.0.0
board = esp32dev
framework = arduino
upload_speed = 921600
monitor_speed = 115200
build_flags = -DDEBUG_LEVEL=1
```

**Build and deploy:**

```bash
cd firmware/heartbeat_phase4
pio run --target upload
pio device monitor --baud 115200
```

---

## Next Steps

See [API Integration](./api-integration.md) for the six specific integration requirements (R1-R6) that transform Phase 1 and Phase 3 into Phase 4.
