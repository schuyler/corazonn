# Implementation Guide

## 7. Main Program Flow

### 7.1 setup() Function (Phase 2 Modified)

**Requirements:**

**R25: Serial Initialization (Phase 1 - Keep)**
```cpp
Serial.begin(115200);
delay(100);
```

**R26: Startup Banner (Phase 2 - Update)**
```cpp
Serial.println("\n=== Heartbeat Installation - Phase 2 ===");
Serial.println("Real Heartbeat Detection");
Serial.print("Sensor ID: ");
Serial.println(SENSOR_ID);
```

**R27: GPIO Configuration (Phase 1 - Keep + Phase 2 Add)**
```cpp
pinMode(STATUS_LED_PIN, OUTPUT);
digitalWrite(STATUS_LED_PIN, LOW);
pinMode(SENSOR_PIN, INPUT);  // Phase 2: ADC pin (actually optional, analogRead() auto-configures)
```

**R28: WiFi Connection (Phase 1 - Keep Exact)**
```cpp
state.wifiConnected = connectWiFi();
if (!state.wifiConnected) {
    // Same error handling as Phase 1
    Serial.println("ERROR: WiFi connection failed");
    // ... (Phase 1 diagnostic output)
    while (true) {
        digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
        delay(100);
    }
}
```

**R29: UDP Initialization (Phase 1 - Keep)**
```cpp
udp.begin(0);  // Ephemeral port
```

**R30: Sensor Initialization (Phase 2 - New)**
```cpp
initializeSensor();  // Configure ADC, pre-fill buffers
Serial.println("Sensor initialized. Ready for heartbeat detection.");
```

**R31: Completion Message (Phase 2 - Update)**
```cpp
Serial.println("Setup complete. Place finger on sensor to begin.");
```

---

### 7.2 loop() Function (Phase 2 Complete Rewrite)

**Requirements:**

**R32: Sampling Timing**
```cpp
static unsigned long lastSampleTime = 0;

unsigned long currentTime = millis();
if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = currentTime;
    // Proceed with sampling
}
```
- Non-blocking 20ms interval (50 Hz)
- Replaces Phase 1 1000ms test message interval

**R33: ADC Reading**
```cpp
int rawValue = analogRead(SENSOR_PIN);
```
- Read GPIO 32 ADC (12-bit, 0-4095 range)

**R34: Signal Processing Pipeline**
```cpp
updateMovingAverage(rawValue);  // Smooth signal
updateBaseline();               // Track min/max with decay
checkDisconnection(rawValue);   // Detect sensor removal
```
- Process signal in order: filter → baseline → disconnection check

**R35: Beat Detection**
```cpp
detectBeat();  // Threshold detection + OSC transmission
```
- Only runs if sensor connected (checked inside function)
- Sends OSC message on valid beat (not periodic)

**R36: WiFi Status Check (Phase 1 - Keep)**
```cpp
checkWiFi();  // Every 5 seconds, rate-limited internally
```

**R37: LED Update (Phase 2 - Modified)**
```cpp
updateLED();  // WiFi status + beat pulse
```

**R38: Loop Delay (Phase 2 - Modified)**
```cpp
delay(1);  // Minimal delay for WiFi background tasks
```
- Reduced from Phase 1's 10ms (loop now runs every 20ms via sample timing)

**R39: Debug Output (Phase 2 - Optional)**
```cpp
state.loopCounter++;
if (state.loopCounter % 50 == 0) {  // Every 1 second (50 samples @ 50Hz)
    Serial.print("ADC: ");
    Serial.print(sensor.smoothedValue);
    Serial.print(" Range: ");
    Serial.print(sensor.maxValue - sensor.minValue);
    Serial.print(" Threshold: ");
    Serial.println(sensor.minValue + (int)((sensor.maxValue - sensor.minValue) * THRESHOLD_FRACTION));
}
```
- Throttled debug output for tuning (can be disabled for production)

**Complete loop() Structure:**
```cpp
void loop() {
    static unsigned long lastSampleTime = 0;

    checkWiFi();  // WiFi monitoring (rate-limited)

    unsigned long currentTime = millis();
    if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
        lastSampleTime = currentTime;

        // Signal processing pipeline
        int rawValue = analogRead(SENSOR_PIN);
        updateMovingAverage(rawValue);
        updateBaseline();
        checkDisconnection(rawValue);
        detectBeat();

        // Debug output (optional)
        state.loopCounter++;
        // ... (throttled debug print)
    }

    updateLED();
    delay(1);
}
```

---

## 8. Complete Program Structure

### 8.1 File Organization (Phase 1 - Keep)

**PlatformIO Project Structure:**
```
firmware/heartbeat_phase1/  (reuse same directory)
├── platformio.ini          # No changes from Phase 1
├── src/
│   └── main.cpp           # Replace with Phase 2 implementation
├── lib/                   # Empty
├── include/               # Empty
└── test/                  # Future
```

**platformio.ini Configuration (Phase 1 - Keep Exact):**
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

**No changes to platformio.ini** - Phase 2 uses same build configuration.

### 8.2 Code Organization (Phase 2)

**src/main.cpp Structure:**
```cpp
/**
 * Heartbeat Installation - Phase 2: Real Heartbeat Detection
 * ESP32 Firmware
 */

// ============================================================================
// INCLUDES
// ============================================================================
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCMessage.h>

// ============================================================================
// CONFIGURATION
// ============================================================================
// Network configuration (Phase 1 - keep)
// Hardware configuration (Phase 1 + Phase 2)
// Signal processing parameters (Phase 2 new)
// Beat detection parameters (Phase 2 new)

// ============================================================================
// GLOBAL STATE
// ============================================================================
struct SystemState { /* Phase 2 modified */ };
struct SensorState { /* Phase 2 new */ };
WiFiUDP udp;
SystemState state = { /* ... */ };
SensorState sensor = { /* ... */ };

// ============================================================================
// FUNCTION DECLARATIONS
// ============================================================================
// Phase 1 functions (keep):
bool connectWiFi();
void sendHeartbeatOSC(int ibi_ms);
void checkWiFi();

// Phase 2 functions (new):
void initializeSensor();
void updateMovingAverage(int rawValue);
void updateBaseline();
void checkDisconnection(int rawValue);
void detectBeat();

// Phase 1+2 function (modified):
void updateLED();

// ============================================================================
// FUNCTION IMPLEMENTATIONS
// ============================================================================
// [Phase 1 functions: keep exact implementation]
// [Phase 2 functions: implement per specifications above]

// ============================================================================
// ARDUINO CORE
// ============================================================================
void setup() {
    // [Phase 2 setup: WiFi (Phase 1) + Sensor init (Phase 2)]
}

void loop() {
    // [Phase 2 loop: ADC sampling + signal processing + beat detection]
}
```

---

## 9. Compilation & Upload

### 9.1 Pre-Upload Configuration (Phase 2 Changes)

**MUST edit in `src/main.cpp`:**
```cpp
// Network (same as Phase 1):
const char* WIFI_SSID = "heartbeat-install";      // Your WiFi SSID
const char* WIFI_PASSWORD = "your-password-here";  // Your WiFi password
const IPAddress SERVER_IP(192, 168, 1, 100);      // Your dev machine IP

// Sensor ID (same as Phase 1):
const int SENSOR_ID = 0;  // Change to 1, 2, 3 for additional units
```

**Tuning parameters (optional, start with defaults):**
```cpp
const float THRESHOLD_FRACTION = 0.6;      // Adjust if needed (0.5-0.7)
const int MIN_SIGNAL_RANGE = 50;           // Adjust if needed (30-100)
```

### 9.2 PlatformIO Commands (Phase 1 - Keep)

**Same commands as Phase 1:**
```bash
cd /home/sderle/corazonn/firmware/heartbeat_phase1

# Compile
pio run

# Upload
pio run --target upload

# Monitor
pio device monitor

# Combined
pio run --target upload && pio device monitor
```

### 9.3 Expected Compilation Output (Phase 2)

```
Processing esp32dev (platform: espressif32; board: esp32dev; framework: arduino)
...
RAM:   [==        ]  16.8% (used 55104 bytes from 327680 bytes)
Flash: [====      ]  38.2% (used 501024 bytes from 1310720 bytes)
========================= [SUCCESS] Took X.XX seconds =========================
```
- Slightly larger than Phase 1 due to signal processing code

### 9.4 Compilation Troubleshooting

**Error: undefined reference to `sendHeartbeatOSC(int)`**
- Missing Phase 1 WiFi function implementations
- Ensure `connectWiFi()`, `sendHeartbeatOSC()`, `checkWiFi()` from Phase 1 are present

**Error: cannot convert `int` to `bool`**
- Check `initializeSensor()` return type (should be void)
- Check state initialization values

**Warning: unused variable**
- Normal for optional debug code
- Can be disabled with `#ifdef DEBUG_MODE`

**Error: WiFiUdp.h: No such file or directory**
- ESP32 board support not installed
- Run: `pio platform install espressif32`

---

## Related Documentation

- **[Overview](overview.md)** - Architecture and objectives
- **[Configuration](configuration.md)** - Constants and data structures
- **[API Functions](api-sensors.md)** - Function implementations
- **[Operations](operations.md)** - Testing and validation

---

## Development Workflow

```
1. Install PlatformIO CLI
2. Clone/setup firmware directory
3. Copy Phase 1 main.cpp as starting point
4. Add Phase 2 constants and structures (Sections 4-5)
5. Implement Phase 2 functions (Sections 6.1-6.5, 6.7)
6. Update setup() and loop() (Section 7)
7. Compile and test
8. Debug with serial output
9. Tune parameters based on test results
10. Run validation suite (Section 10)
```

---

## Performance Characteristics

**Memory Usage:**
- RAM: ~55KB / 328KB (17%)
- Flash: ~500KB / 1.3MB (38%)
- Headroom: Good for additions in Phase 3 (4 sensors)

**CPU Usage:**
- Loop frequency: ~50 Hz (sampling rate)
- Non-blocking: No delays blocking main loop
- WiFi: Concurrent background task (no impact on sampling)

**Timing Accuracy:**
- ADC sample interval: 20ms ± 1-2ms jitter
- Sufficient for heartbeat detection (fundamental frequency 1-3 Hz)
- Jitter acceptable for IBI calculation (tolerance ±5% typical)
