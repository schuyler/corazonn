# Implementation: Main Program Flow & Compilation

---

## 7. Main Program Flow

### 7.1 setup() Function

**Requirements:**

**R26: Serial Initialization**
```cpp
Serial.begin(115200);
delay(100);
Serial.println("\n=== Heartbeat Installation - Phase 3 ===");
Serial.println("Multi-Sensor Beat Detection");
```

**R27: GPIO Configuration**
```cpp
pinMode(STATUS_LED_PIN, OUTPUT);
digitalWrite(STATUS_LED_PIN, LOW);

// Configure ADC resolution
analogReadResolution(ADC_RESOLUTION);  // 12-bit
analogSetAttenuation(ADC_11db);        // 0-3.3V range

// Note: No pinMode for sensor pins (ADC channels auto-configured)
// GPIO 34-35 are input-only, don't call pinMode OUTPUT
```

**Requirements:**
- Set ADC to 12-bit resolution (0-4095)
- Set attenuation for full 0-3.3V range
- DO NOT call pinMode on GPIO 32-35 (ADC auto-configures)

**R28: Sensor Initialization**
```cpp
for (int i = 0; i < NUM_SENSORS; i++) {
  sensors[i].pin = SENSOR_PINS[i];
  initializeSensor(i);

  #if DEBUG_LEVEL >= 1
    Serial.print("Initialized sensor ");
    Serial.print(i);
    Serial.print(" on GPIO ");
    Serial.println(sensors[i].pin);
  #endif
}
```

**R29: WiFi Connection**
```cpp
// Same as Phase 1
system.wifiConnected = connectWiFi();  // Uses Phase 1 implementation
if (!system.wifiConnected) {
  // Error state: rapid blink, halt
  Serial.println("ERROR: WiFi connection failed");
  while (true) {
    digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
    delay(100);
  }
}
```

**R30: UDP Initialization**
```cpp
udp.begin(0);  // Any available port
```

**R31: Completion Message**
```cpp
Serial.println("Setup complete. Starting multi-sensor detection...");
```

**Complete setup() Example:**
```cpp
void setup() {
  // R26: Serial
  Serial.begin(115200);
  delay(100);
  Serial.println("\n=== Heartbeat Installation - Phase 3 ===");
  Serial.println("Multi-Sensor Beat Detection");

  // R27: GPIO and ADC
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);
  analogReadResolution(ADC_RESOLUTION);
  analogSetAttenuation(ADC_11db);

  // R28: Initialize sensors
  for (int i = 0; i < NUM_SENSORS; i++) {
    sensors[i].pin = SENSOR_PINS[i];
    initializeSensor(i);
    #if DEBUG_LEVEL >= 1
      Serial.print("Initialized sensor ");
      Serial.print(i);
      Serial.print(" on GPIO ");
      Serial.println(sensors[i].pin);
    #endif
  }

  // R29: WiFi connection
  system.wifiConnected = connectWiFi();
  if (!system.wifiConnected) {
    Serial.println("ERROR: WiFi connection failed");
    while (true) {
      digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
      delay(100);
    }
  }

  // R30: UDP
  udp.begin(0);

  // R31: Ready
  Serial.println("Setup complete. Starting multi-sensor detection...");
}
```

---

### 7.2 loop() Function

**Structure:**

```cpp
void loop() {
  static unsigned long lastSampleTime = 0;

  // 1. Check if time to sample (20ms interval = 50Hz)
  unsigned long currentTime = millis();
  if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = currentTime;

    // Clear beat detection flag
    system.beatDetectedThisLoop = false;

    // 2. Process all 4 sensors
    for (int i = 0; i < NUM_SENSORS; i++) {
      readAndFilterSensor(i);     // Sample + moving average
      updateBaseline(i);          // Adaptive threshold tracking
      detectBeat(i);              // Beat detection + OSC transmission
    }

    // 3. Update LED (responds to ANY sensor beat)
    updateLED();

    // 4. Debug output (throttled)
    #if DEBUG_LEVEL >= 2
      if (system.loopCounter % 5 == 0) {  // Every 100ms (5 samples)
        Serial.print("[0]=");
        Serial.print(sensors[0].smoothedValue);
        Serial.print(" [1]=");
        Serial.print(sensors[1].smoothedValue);
        Serial.print(" [2]=");
        Serial.print(sensors[2].smoothedValue);
        Serial.print(" [3]=");
        Serial.println(sensors[3].smoothedValue);
      }
    #endif

    system.loopCounter++;
  }

  // 5. Check WiFi status (every 5 seconds, rate-limited internally)
  checkWiFi();

  // 6. Small delay for stability
  delay(1);  // Minimal delay, allows WiFi background tasks
}
```

**Requirements:**

**R32: Timing Precision**
- MUST check elapsed time, not use blocking delays
- Target 20ms ± 2ms per cycle
- `millis()` provides 1ms resolution for beat timestamps

**R33: Sensor Independence**
- MUST process each sensor independently
- Each sensor has own state, threshold, beat detection
- No crosstalk between sensors

**R34: LED Feedback**
- LED responds to beats from ANY sensor
- If multiple sensors beat simultaneously, LED shows one pulse (no flicker)

**R35: Debug Output Throttling**
- Level 2: Raw values every 100ms (not every 20ms)
- Use `loopCounter % 5` to throttle
- Prevents serial buffer overflow

**R36: Non-Blocking**
- Loop cycles continuously
- WiFi tasks run in background
- No long blocking operations

**Execution Timeline (Typical):**
```
Time  | Event
------|-----------------------------------------------
0ms   | Start of cycle (lastSampleTime updated)
1-3ms | Sample 4 sensors (4ms total)
4-6ms | Update baselines (2ms total)
7-12ms| Beat detection + OSC (3ms per sensor, 12ms total)
13ms  | Update LED (1ms)
14ms  | Serial output if DEBUG_LEVEL >= 2 (optional)
14-15ms| WiFi check (rate-limited to every 5 seconds)
16-19ms| delay(1) for WiFi background tasks
20ms  | Next cycle begins
```

---

## 8. Complete Program Structure

### 8.1 File Organization

**Same as Phase 1 structure:**
```
firmware/heartbeat_phase3/
├── platformio.ini
├── src/
│   └── main.cpp           # All Phase 3 code
├── lib/
├── include/
└── test/
```

### 8.2 main.cpp Structure

```cpp
/**
 * Heartbeat Installation - Phase 3: Multi-Sensor Beat Detection
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
// Network (same as Phase 1)
// Hardware (4 sensors)
// Signal processing parameters
// Beat detection parameters
// Debug level

// ============================================================================
// DATA STRUCTURES
// ============================================================================
struct SensorState { /* ... */ };
struct SystemState { /* ... */ };

// ============================================================================
// GLOBAL STATE
// ============================================================================
WiFiUDP udp;
SystemState system = {false, 0, 0, false};
SensorState sensors[4];

// ============================================================================
// FUNCTION DECLARATIONS
// ============================================================================
// WiFi (from Phase 1)
bool connectWiFi();
void checkWiFi();

// Sensor processing (new in Phase 3)
void initializeSensor(int sensorIndex);
void readAndFilterSensor(int sensorIndex);
void updateBaseline(int sensorIndex);
void detectBeat(int sensorIndex);

// OSC transmission (updated signature)
void sendHeartbeatOSC(int sensorIndex, int ibi_ms);

// Status indication (updated for beats)
void updateLED();

// ============================================================================
// FUNCTION IMPLEMENTATIONS
// ============================================================================
// [Implement all functions per specifications]

// ============================================================================
// ARDUINO CORE
// ============================================================================
void setup() {
  // R26-R31: Initialize serial, GPIO, sensors, WiFi, UDP
}

void loop() {
  // R32-R36: Sample sensors, process, detect beats, transmit OSC
}
```

**Code Organization Best Practices:**
- Keep constants at top (easy to modify)
- Declare data structures before use
- Declare all functions before setup()
- Implement functions in logical order
- setup() and loop() at bottom

---

## 9. Compilation & Upload

### 9.1 PlatformIO Commands

**Same as Phase 1:**

```bash
cd /home/sderle/fw-phase-3/firmware/heartbeat_phase3

# Compile
pio run

# Upload
pio run --target upload

# Monitor serial output
pio device monitor

# Combined: Compile, upload, and monitor
pio run --target upload && pio device monitor
```

**Common Options:**
```bash
# Verbose output (debugging)
pio run -v

# Specific environment
pio run -e esp32dev

# Clean rebuild
pio run --target clean && pio run
```

### 9.2 Pre-Upload Configuration

**MUST configure before upload:**
1. WiFi credentials (WIFI_SSID, WIFI_PASSWORD)
2. Server IP address (SERVER_IP)
3. Debug level (DEBUG_LEVEL 0/1/2)

**Example configuration in main.cpp:**
```cpp
// Network Configuration (CHANGE THESE)
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE TO YOUR SERVER IP
const uint16_t SERVER_PORT = 8000;

// Debug level
#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose
```

**Sensor IDs:**
- Phase 3 uses all 4 sensors simultaneously
- No need to change SENSOR_ID (removed from Phase 3)
- Each sensor identified by array index 0-3

### 9.3 Compilation Validation

**Expected Success:**
```
Building [==================================================] 100%
Linking .pio/build/esp32dev/firmware.elf
Building .pio/build/esp32dev/firmware.bin
Binary sketch size: XXX bytes (YY% of YYY KB flash)
RAM:   [==        ]  15.0% (used XXXXX bytes from XXXXX bytes)
Upload size: XXX bytes
```

**Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| `fatal error: OSCMessage.h: No such file` | OSC library not installed | Run `pio lib install` |
| `undefined reference to 'connectWiFi'` | Phase 1 WiFi function missing | Copy from Phase 1 main.cpp |
| `error: 'sensors' was not declared` | Missing global array | Check configuration constants |
| `error: expected ';' before '}'` | Syntax error | Check struct definitions and brackets |

### 9.4 Upload & Monitor

**Upload Procedure:**
1. Connect ESP32 via USB
2. Verify COM port: `pio device list`
3. Run: `pio run --target upload`
4. Wait for "Hard resetting via RTS pin..." message
5. Monitor output: `pio device monitor`

**Successful Upload:**
```
Connecting....._____....
Chip is ESP32-WROOM-32E (revision 1)
Features: WiFi, BT, Dual Core, 240MHz, VRef calibration in efuse
Uploading stub...
Running stub...
Stub running...
Changing baud rate to 921600
Changed.
Uploading 234752 bytes from firmware.bin to flash at 0x00001000
(Some progress dots)
Wrote 234752 bytes (157376 compressed) at 0x00001000 in 2.8 seconds
Hard resetting via RTS pin...
```

**Serial Monitor Output (startup):**
```
=== Heartbeat Installation - Phase 3 ===
Multi-Sensor Beat Detection
Initialized sensor 0 on GPIO 32
Initialized sensor 1 on GPIO 33
Initialized sensor 2 on GPIO 34
Initialized sensor 3 on GPIO 35
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.1.42
Setup complete. Starting multi-sensor detection...
```

---

## Related Documentation

- [Configuration](configuration.md) — Constants and data structures
- [API: Sensors](api-sensors.md) — initializeSensor(), readAndFilterSensor()
- [API: Signal Processing](api-signal-processing.md) — updateBaseline()
- [API: Beat Detection](api-beat-detection.md) — detectBeat()
- [API: Messaging](api-messaging.md) — sendHeartbeatOSC()
- [API: Status](api-status.md) — updateLED()
- [API: Network](api-network.md) — checkWiFi()

---

**Next Step:** Validate with [Operations: Testing](operations.md)
