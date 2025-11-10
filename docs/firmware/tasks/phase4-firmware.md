## Component 8: Phase 4 Firmware Implementation
## OSC Integration & Production Validation

Reference: `../reference/phase4-firmware-trd.md`

**Implementation Approach:** Unified Phase 3 + Phase 4 (TRD Option B)

This component implements Phase 3 beat detection algorithm AND integrates with Phase 1 OSC messaging infrastructure in a single unified firmware implementation.

### Prerequisites

- [ ] **Task 0.1**: Verify Phase 1 firmware exists
  - Check Phase 1 directory exists: `ls /home/sderle/fw-phase-3/firmware/heartbeat_phase1`
  - **Expected**: Directory contains platformio.ini and src/main.cpp
  - **Status**: Phase 1 firmware code available

- [ ] **Task 0.2**: Validate Phase 1 firmware working (Phase 4 TRD Section 0.1)
  - Upload Phase 1 firmware: `cd /home/sderle/fw-phase-3/firmware/heartbeat_phase1 && pio run --target upload`
  - Monitor serial: `pio device monitor`
  - Start Python receiver: `python3 testing/osc_receiver.py --port 8000`
  - Verify: WiFi connects, test messages sent at 1 Hz, receiver shows valid messages
  - Verify: LED solid after WiFi connection
  - **Status**: Phase 1 validated (WiFi + OSC infrastructure working)

- [ ] **Task 0.3**: Verify testing infrastructure ready
  - Confirm Python OSC receiver runs: `python3 testing/osc_receiver.py --port 8000`
  - Verify receiver prints "OSC Receiver listening on 0.0.0.0:8000"
  - Find development machine IP: `ip addr show` or `ifconfig`
  - Note IP for configuration (NOT 127.0.0.1, must be network IP)
  - Stop receiver (Ctrl+C)
  - **Status**: Testing infrastructure ready

- [ ] **Task 0.4**: Verify hardware setup (4 pulse sensors)
  - Connect Sensor 0 to GPIO 32 (ADC1_CH4)
  - Connect Sensor 1 to GPIO 33 (ADC1_CH5)
  - Connect Sensor 2 to GPIO 34 (ADC1_CH6, input-only)
  - Connect Sensor 3 to GPIO 35 (ADC1_CH7, input-only)
  - All sensors powered from ESP32 3.3V, common ground
  - Label sensors physically with IDs 0-3
  - **Status**: Hardware connected and labeled

- [ ] **Task 0.5**: Verify GPIO configuration understanding
  - Confirm GPIO 32-35 all use ADC1 (avoids WiFi conflicts with ADC2)
  - Confirm GPIO 34-35 are input-only (no pullup/pulldown, no OUTPUT mode)
  - Confirm 12-bit ADC resolution: 0-4095 range
  - Verify Phase 3 TRD Section 4.2 hardware requirements
  - **Status**: Hardware requirements understood

### Component 8.1: Project Structure (Phase 4 TRD Section 3.1)

- [ ] **Task 1.1**: Initialize PlatformIO project (Phase 4 TRD Section 3.1)
  - Create directory: `mkdir -p /home/sderle/fw-phase-3/firmware/heartbeat_phase4`
  - Change directory: `cd /home/sderle/fw-phase-3/firmware/heartbeat_phase4`
  - Initialize: `pio project init --board esp32dev`
  - Verify created: platformio.ini, src/, lib/, include/
  - **Status**: Project initialized with PlatformIO structure

- [ ] **Task 1.2**: Configure platformio.ini (Phase 3 TRD Section 3.1)
  - Edit `/home/sderle/fw-phase-3/firmware/heartbeat_phase4/platformio.ini`
  - Set platform = espressif32
  - Set board = esp32dev
  - Set framework = arduino
  - Set monitor_speed = 115200
  - Set upload_speed = 921600
  - Set board_build.flash_mode = qio
  - Set board_build.flash_size = 4MB
  - Add lib_deps = https://github.com/CNMAT/OSC.git
  - **Status**: Configuration matches Phase 1/3 requirements

- [ ] **Task 1.3**: Create firmware README
  - Create: `/home/sderle/fw-phase-3/firmware/heartbeat_phase4/README.md`
  - Document: Purpose (Phase 4 - OSC Integration & Production)
  - Document: PlatformIO setup and compilation commands
  - Document: How to configure WiFi credentials and SERVER_IP
  - Document: Debug levels 0/1/2 meanings
  - Include: `pio run`, `pio run --target upload`, `pio device monitor` commands
  - **Status**: README complete with Phase 4 context

### Component 8.2: Firmware Skeleton (Phase 4 TRD Section 3.2)

- [ ] **Task 2.1**: Create src/main.cpp with includes (Phase 4 TRD Section 3.2, Phase 3 TRD R26)
  - File: `/home/sderle/fw-phase-3/firmware/heartbeat_phase4/src/main.cpp`
  - Add header comment: "Heartbeat Installation - Phase 4", "OSC Integration & Production Validation"
  - Add includes: `#include <Arduino.h>`, `#include <WiFi.h>`, `#include <WiFiUdp.h>`, `#include <OSCMessage.h>`
  - Add empty `setup()` and `loop()` functions
  - **Status**: Code compiles: `pio run`

- [ ] **Task 2.2**: Add network configuration constants (Phase 4 TRD Section 3.2, R5)
  - From Phase 1: Network configuration section
  - Add `const char* WIFI_SSID = "heartbeat-install";`
  - Add `const char* WIFI_PASSWORD = "your-password-here";`
  - Add `const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS`
  - Add `const uint16_t SERVER_PORT = 8000;`
  - Add comment: "MUST configure SSID, PASSWORD, and SERVER_IP before upload"
  - **Status**: Code compiles: `pio run`

- [ ] **Task 2.3**: Add hardware configuration constants (Phase 3 TRD Section 4.2)
  - Add `const int SENSOR_PINS[4] = {32, 33, 34, 35};`
  - Add `const int NUM_SENSORS = 4;`
  - Add `const int STATUS_LED_PIN = 2;`
  - Add `const int ADC_RESOLUTION = 12;  // 12-bit: 0-4095`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 2.4**: Add signal processing constants (Phase 3 TRD Section 4.3)
  - Add `const int SAMPLE_RATE_HZ = 50;  // Per sensor`
  - Add `const int SAMPLE_INTERVAL_MS = 20;  // 1000 / 50`
  - Add `const int MOVING_AVG_SAMPLES = 5;  // 100ms window`
  - Add `const float BASELINE_DECAY_RATE = 0.1;  // 10% decay toward center`
  - Add `const int BASELINE_DECAY_INTERVAL = 150;  // Every 3 sec (150 samples at 50Hz)`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 2.5**: Add beat detection constants (Phase 3 TRD Section 4.4)
  - Add `const float THRESHOLD_FRACTION = 0.6;  // 60% of signal range`
  - Add `const int MIN_SIGNAL_RANGE = 50;  // ADC units, below = disconnected`
  - Add `const unsigned long REFRACTORY_PERIOD_MS = 300;  // Max 200 BPM`
  - Add `const int FLAT_SIGNAL_THRESHOLD = 5;  // ADC variance for "flat"`
  - Add `const unsigned long DISCONNECT_TIMEOUT_MS = 1000;  // 50 samples flat`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 2.6**: Add debug level configuration (Phase 3 TRD Section 4.5)
  - Add `#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose`
  - Add comments explaining each level:
    - Level 0: Production (WiFi status only)
    - Level 1: Testing (beat timestamps + IBI values)
    - Level 2: Verbose (raw ADC values every 100ms, baseline tracking)
  - **Status**: Code compiles: `pio run`

- [ ] **Task 2.7**: Define SensorState struct (Phase 3 TRD Section 5.1, R1-R5)
  - Create `struct SensorState { ... };` with fields:
    - `int pin;` - GPIO pin number
    - `int rawSamples[MOVING_AVG_SAMPLES];` - Circular buffer
    - `int sampleIndex;` - Current position in buffer
    - `int smoothedValue;` - Filter output
    - `int minValue;` - Baseline minimum (decays upward)
    - `int maxValue;` - Baseline maximum (decays downward)
    - `int samplesSinceDecay;` - Counter for decay interval
    - `bool aboveThreshold;` - Currently above threshold?
    - `unsigned long lastBeatTime;` - millis() of last beat
    - `unsigned long lastIBI;` - Inter-beat interval (ms)
    - `bool firstBeatDetected;` - Have we sent first beat?
    - `bool isConnected;` - Sensor shows valid signal?
    - `int lastRawValue;` - For flat signal detection
    - `int flatSampleCount;` - Consecutive flat samples
  - **Status**: Code compiles: `pio run`

- [ ] **Task 2.8**: Define SystemState struct (Phase 3 TRD Section 5.2)
  - Create `struct SystemState { ... };` with fields:
    - `bool wifiConnected;` - WiFi connection status
    - `unsigned long lastWiFiCheckTime;` - millis() of last WiFi check
    - `unsigned long loopCounter;` - For debug output throttling
    - `bool beatDetectedThisLoop;` - For LED pulse feedback
  - **Status**: Code compiles: `pio run`

- [ ] **Task 2.9**: Declare global objects and state (Phase 3 TRD Section 5.3)
  - Declare `WiFiUDP udp;`
  - Declare `SystemState system = {false, 0, 0, false};`
  - Declare `SensorState sensors[4];`
  - Add function forward declarations (will implement later)
  - **Status**: Code compiles: `pio run`

### Component 8.3: Sensor Initialization (Phase 3 TRD Section 6.1)

- [ ] **Task 3.1**: Implement initializeSensor() skeleton (Phase 3 TRD Section 6.1)
  - Function signature: `void initializeSensor(int sensorIndex);`
  - Parameter: `sensorIndex` - Index 0-3 into sensors array
  - Empty function body for now
  - **Status**: Code compiles: `pio run`

- [ ] **Task 3.2**: Implement initial ADC reading (Phase 3 TRD R6)
  - Read first value: `int firstReading = analogRead(sensors[sensorIndex].pin);`
  - Store for buffer pre-fill
  - **Status**: Code compiles: `pio run`

- [ ] **Task 3.3**: Implement buffer pre-fill (Phase 3 TRD R7)
  - Loop: `for (int i = 0; i < MOVING_AVG_SAMPLES; i++)`
  - Fill buffer: `sensors[sensorIndex].rawSamples[i] = firstReading;`
  - Purpose: Prevents invalid calculations during buffer fill, allows immediate filtering
  - **Status**: Code compiles: `pio run`

- [ ] **Task 3.4**: Implement state initialization (Phase 3 TRD R8)
  - Initialize all SensorState fields:
    - `sampleIndex = 0`
    - `smoothedValue = firstReading`
    - `minValue = firstReading`
    - `maxValue = firstReading`
    - `aboveThreshold = false`
    - `lastBeatTime = 0`
    - `lastIBI = 0`
    - `firstBeatDetected = false`
    - `isConnected = true` (assume connected initially)
    - `lastRawValue = firstReading`
    - `flatSampleCount = 0`
    - `samplesSinceDecay = 0`
  - **Status**: Code compiles: `pio run`

### Component 8.4: Signal Processing (Phase 3 TRD Section 6.2, 6.3)

- [ ] **Task 4.1**: Implement readAndFilterSensor() skeleton (Phase 3 TRD Section 6.2)
  - Function signature: `void readAndFilterSensor(int sensorIndex);`
  - Parameter: `sensorIndex` - Index 0-3 into sensors array
  - Empty function body for now
  - **Status**: Code compiles: `pio run`

- [ ] **Task 4.2**: Implement ADC read (Phase 3 TRD R9)
  - Read ADC: `int rawValue = analogRead(sensors[sensorIndex].pin);`
  - 12-bit resolution: 0-4095 range
  - **Status**: Code compiles: `pio run`

- [ ] **Task 4.3**: Store raw value in circular buffer (Phase 3 TRD R10)
  - Store in buffer: `sensors[sensorIndex].rawSamples[sensors[sensorIndex].sampleIndex] = rawValue;`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 4.4**: Update circular buffer index (Phase 3 TRD R10)
  - Advance index: `sensors[sensorIndex].sampleIndex = (sensors[sensorIndex].sampleIndex + 1) % MOVING_AVG_SAMPLES;`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 4.5**: Calculate moving average (Phase 3 TRD R10)
  - Calculate sum: `int sum = 0; for (int i = 0; i < MOVING_AVG_SAMPLES; i++) sum += sensors[sensorIndex].rawSamples[i];`
  - Store smoothed value: `sensors[sensorIndex].smoothedValue = sum / MOVING_AVG_SAMPLES;`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 4.6**: Implement disconnection check (Phase 3 TRD R11)
  - Check flat signal: `if (abs(rawValue - sensors[sensorIndex].lastRawValue) < FLAT_SIGNAL_THRESHOLD)`
  - Increment counter: `sensors[sensorIndex].flatSampleCount++;`
  - Reset on change: `else flatSampleCount = 0;`
  - Mark disconnected after 50 samples (1 second): `if (flatSampleCount >= 50) isConnected = false;`
  - Update last value: `sensors[sensorIndex].lastRawValue = rawValue;`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 4.7**: Implement updateBaseline() skeleton (Phase 3 TRD Section 6.3)
  - Function signature: `void updateBaseline(int sensorIndex);`
  - Parameter: `sensorIndex` - Index 0-3 into sensors array
  - Empty function body for now
  - **Status**: Code compiles: `pio run`

- [ ] **Task 4.8**: Implement instant expansion (Phase 3 TRD R12)
  - Get smoothed value: `int smoothed = sensors[sensorIndex].smoothedValue;`
  - Expand min: `if (smoothed < sensors[sensorIndex].minValue) minValue = smoothed;`
  - Expand max: `if (smoothed > sensors[sensorIndex].maxValue) maxValue = smoothed;`
  - Purpose: Respond instantly to signal increases, prevents threshold clipping
  - **Status**: Code compiles: `pio run`

- [ ] **Task 4.9**: Implement exponential decay (Phase 3 TRD R13)
  - Increment counter: `sensors[sensorIndex].samplesSinceDecay++;`
  - Check interval: `if (samplesSinceDecay >= BASELINE_DECAY_INTERVAL)`
  - Decay min upward: `minValue += (smoothed - minValue) * BASELINE_DECAY_RATE;`
  - Decay max downward: `maxValue -= (maxValue - smoothed) * BASELINE_DECAY_RATE;`
  - Reset counter: `samplesSinceDecay = 0;`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 4.10**: Implement range check for disconnection (Phase 3 TRD R14)
  - Calculate range: `int range = sensors[sensorIndex].maxValue - sensors[sensorIndex].minValue;`
  - Check minimum: `if (range < MIN_SIGNAL_RANGE) sensors[sensorIndex].isConnected = false;`
  - Purpose: Prevents false beats on flat signals (noise, not pulse)
  - **Status**: Code compiles: `pio run`

### Component 8.5: Beat Detection (Phase 3 TRD Section 6.4)

- [ ] **Task 5.1**: Implement detectBeat() skeleton (Phase 3 TRD Section 6.4)
  - Function signature: `void detectBeat(int sensorIndex);`
  - Parameter: `sensorIndex` - Index 0-3 into sensors array
  - Empty function body for now
  - **Status**: Code compiles: `pio run`

- [ ] **Task 5.2**: Implement disconnection skip (Phase 3 TRD R15)
  - Check: `if (!sensors[sensorIndex].isConnected) return;`
  - Purpose: Don't attempt detection on disconnected sensor
  - **Status**: Code compiles: `pio run`

- [ ] **Task 5.3**: Implement threshold calculation (Phase 3 TRD R16)
  - Calculate: `int threshold = sensors[sensorIndex].minValue + (maxValue - minValue) * THRESHOLD_FRACTION;`
  - Default: 60% of signal range above baseline minimum
  - **Status**: Code compiles: `pio run`

- [ ] **Task 5.4**: Implement rising edge detection (Phase 3 TRD R17)
  - Check current state: `bool currentlyAbove = (sensors[sensorIndex].smoothedValue >= threshold);`
  - Detect transition: `if (currentlyAbove && !sensors[sensorIndex].aboveThreshold)`
  - Update state: `sensors[sensorIndex].aboveThreshold = currentlyAbove;`
  - Purpose: Trigger only on transition from below to above (prevents double-triggering)
  - **Status**: Code compiles: `pio run`

- [ ] **Task 5.5**: Implement refractory period check (Phase 3 TRD R18)
  - Get current time: `unsigned long now = millis();`
  - Calculate time since last: `unsigned long timeSinceLastBeat = now - sensors[sensorIndex].lastBeatTime;`
  - Check minimum: `if (timeSinceLastBeat < REFRACTORY_PERIOD_MS) return;`
  - Purpose: Enforces minimum time between beats (300ms = max 200 BPM), rate-limits OSC
  - **Status**: Code compiles: `pio run`

- [ ] **Task 5.6**: Implement IBI calculation (Phase 3 TRD R19, Phase 4 TRD R3)
  - Calculate IBI: `unsigned long ibi = now - sensors[sensorIndex].lastBeatTime;`
  - Check first beat: `if (sensors[sensorIndex].firstBeatDetected)`
  - If first beat detected: Call `sendHeartbeatOSC(sensorIndex, (int)ibi);`
  - Set LED flag: `system.beatDetectedThisLoop = true;`
  - Add debug output (Level 1): Print sensor index, timestamp, IBI value
  - **Status**: Code compiles: `pio run`

- [ ] **Task 5.7**: Implement first beat handling (Phase 3 TRD R19)
  - If not first beat: Set `sensors[sensorIndex].firstBeatDetected = true;`
  - Add debug output (Level 1): "First beat at <timestamp>ms (no message sent)"
  - Purpose: First beat establishes reference, no IBI to calculate yet
  - **Status**: Code compiles: `pio run`

- [ ] **Task 5.8**: Update beat tracking state (Phase 3 TRD R19)
  - Update time: `sensors[sensorIndex].lastBeatTime = now;`
  - Update IBI: `sensors[sensorIndex].lastIBI = ibi;`
  - **Status**: Code compiles: `pio run`

### Component 8.6: OSC Integration (Phase 4 TRD Section 3.2)

- [ ] **Task 6.1**: Implement sendHeartbeatOSC() with updated signature (Phase 4 TRD Section 3.2, R1)
  - Function signature: `void sendHeartbeatOSC(int sensorIndex, int ibi_ms);`
  - Parameters: `sensorIndex` (0-3), `ibi_ms` (300-3000ms typical)
  - Empty function body for now
  - **Note**: Updated from Phase 1 signature (added sensorIndex parameter)
  - **Status**: Code compiles: `pio run`

- [ ] **Task 6.2**: Implement OSC address construction (Phase 3 TRD R20, Phase 4 TRD R1)
  - Create buffer: `char oscAddress[20];`
  - Format address: `snprintf(oscAddress, sizeof(oscAddress), "/heartbeat/%d", sensorIndex);`
  - Result: `/heartbeat/0`, `/heartbeat/1`, `/heartbeat/2`, `/heartbeat/3`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 6.3**: Implement OSC message construction (Phase 3 TRD R21)
  - Create message: `OSCMessage msg(oscAddress);`
  - Add argument: `msg.add((int32_t)ibi_ms);`
  - **Critical**: MUST cast to int32_t for correct OSC type tag
  - **Status**: Code compiles: `pio run`

- [ ] **Task 6.4**: Implement UDP transmission (Phase 3 TRD R22, Phase 1 validated)
  - Call: `udp.beginPacket(SERVER_IP, SERVER_PORT);`
  - Send: `msg.send(udp);`
  - Complete: `udp.endPacket();`
  - Clear: `msg.empty();`
  - **Critical**: MUST follow this exact sequence (beginPacket → send → endPacket → empty)
  - **Status**: Code compiles: `pio run`

- [ ] **Task 6.5**: Add debug output for OSC sends (Phase 3 TRD R23)
  - Add conditional: `#if DEBUG_LEVEL >= 2`
  - Print: "Sent OSC: " + oscAddress + " " + ibi_ms
  - Purpose: Level 2 debug confirms OSC transmission, production (Level 0) no output
  - **Status**: Code compiles: `pio run`

- [ ] **Task 6.6**: Verify integration point (Phase 4 TRD R2, R3)
  - Confirm: `sendHeartbeatOSC()` called from `detectBeat()` (Task 5.6)
  - Confirm: Test message generation code NOT present (Phase 1's test loop removed)
  - Confirm: Only real beat detections trigger OSC messages
  - **Status**: Integration verified, code compiles: `pio run`

- [ ] **Task 6.7**: Remove Phase 1 test code (Phase 4 TRD R6)
  - Verify `SENSOR_ID` constant removed (no longer needed with array indexing)
  - Verify `TEST_MESSAGE_INTERVAL_MS` constant removed
  - Verify test message generation loop removed from loop()
  - Verify `messageCounter` only used for debug (if at all)
  - **Status**: Phase 1 test code cleaned up

### Component 8.7: LED Feedback (Phase 3 TRD Section 6.6)

- [ ] **Task 7.1**: Implement updateLED() skeleton (Phase 3 TRD Section 6.6)
  - Function signature: `void updateLED();`
  - Empty function body for now
  - **Status**: Code compiles: `pio run`

- [ ] **Task 7.2**: Implement LED states (Phase 3 TRD R24-R25, Phase 4 TRD R4)
  - Add static variable: `static unsigned long ledPulseTime = 0;`
  - Add constant: `const int LED_PULSE_DURATION = 50;  // 50ms pulse`
  - If WiFi connecting: Rapid blink 10Hz: `digitalWrite(STATUS_LED_PIN, (millis() / 50) % 2);`
  - If beat detected: Turn on and record time: `digitalWrite(STATUS_LED_PIN, HIGH); ledPulseTime = millis();`
  - If during pulse: Keep on: `if (millis() - ledPulseTime < LED_PULSE_DURATION) digitalWrite(STATUS_LED_PIN, HIGH);`
  - Else: Solid on when connected: `digitalWrite(STATUS_LED_PIN, HIGH);`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 7.3**: Clear beat detection flag (Phase 3 TRD R25)
  - After LED update: `system.beatDetectedThisLoop = false;`
  - Purpose: Reset flag for next loop iteration
  - **Note**: LED responds to beats from ANY sensor (not just sensor 0)
  - **Status**: Code compiles: `pio run`

### Component 8.8: WiFi Functions (Adapted from Phase 1)

**Note:** These functions are adapted from Phase 1 validated implementation. Copy from `/home/sderle/fw-phase-3/firmware/heartbeat_phase1/src/main.cpp` as starting point.

- [ ] **Task 8.1**: Copy and adapt connectWiFi() from Phase 1 (Phase 1 TRD Section 6.1, R1-R4)
  - Copy function from Phase 1: `firmware/heartbeat_phase1/src/main.cpp`
  - Update to use Phase 4 SystemState struct
  - Function signature: `bool connectWiFi();`
  - Initialize: `WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);`
  - Print: "Connecting to WiFi: [SSID]"
  - Poll WiFi.status() in loop with 30 second timeout
  - Blink LED during connection: `digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);`
  - On success: Set `system.wifiConnected = true`, LED solid, print IP, return true
  - On timeout: Print error, return false
  - **Status**: Code compiles: `pio run`

- [ ] **Task 8.2**: Copy and adapt checkWiFi() from Phase 1 (Phase 1 TRD Section 6.4, R12-R14)
  - Copy function from Phase 1: `firmware/heartbeat_phase1/src/main.cpp`
  - Update to use Phase 4 SystemState struct
  - Function signature: `void checkWiFi();`
  - Use static variable for rate limiting: `static unsigned long lastCheckTime = 0;`
  - Check every 5 seconds: `if (millis() - lastCheckTime < 5000) return;`
  - Update: `lastCheckTime = millis();`
  - Check status: `WiFi.status()`, update `system.wifiConnected`
  - If disconnected: Print "WiFi disconnected, reconnecting...", call `WiFi.reconnect()`
  - **Note**: `WiFi.reconnect()` is non-blocking
  - **Status**: Code compiles: `pio run`

### Component 8.9: Main Program Flow (Phase 3 TRD Section 7)

- [ ] **Task 9.1**: Implement setup() serial initialization (Phase 3 TRD R26)
  - Initialize serial: `Serial.begin(115200); delay(100);`
  - Print startup banner:
    - "=== Heartbeat Installation - Phase 4 ==="
    - "OSC Integration & Production Validation"
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.2**: Implement setup() GPIO configuration (Phase 3 TRD R27)
  - Configure LED: `pinMode(STATUS_LED_PIN, OUTPUT); digitalWrite(STATUS_LED_PIN, LOW);`
  - Configure ADC resolution: `analogReadResolution(ADC_RESOLUTION);  // 12-bit`
  - Set attenuation: `analogSetAttenuation(ADC_11db);  // 0-3.3V range`
  - **Note**: DO NOT call pinMode on GPIO 32-35 (ADC auto-configures)
  - **Note**: GPIO 34-35 are input-only, never call pinMode OUTPUT on them
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.3**: Implement setup() sensor initialization (Phase 3 TRD R28)
  - Loop through sensors: `for (int i = 0; i < NUM_SENSORS; i++)`
  - Set pin: `sensors[i].pin = SENSOR_PINS[i];`
  - Initialize: `initializeSensor(i);`
  - Add debug output (Level 1): "Initialized sensor N on GPIO M"
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.4**: Implement setup() WiFi connection (Phase 3 TRD R29)
  - Call: `system.wifiConnected = connectWiFi();`
  - Check result: `if (!system.wifiConnected)`
  - On failure: Print "ERROR: WiFi connection failed"
  - Enter error loop: `while (true) { digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2); delay(100); }`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.5**: Implement setup() UDP initialization (Phase 3 TRD R30)
  - Initialize UDP: `udp.begin(0);  // Ephemeral port`
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.6**: Implement setup() completion message (Phase 3 TRD R31)
  - Print: "Setup complete. Starting beat detection with OSC transmission..."
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.7**: Implement loop() timing check (Phase 3 TRD Section 7.2, R32)
  - Add static variable: `static unsigned long lastSampleTime = 0;`
  - Get current time: `unsigned long currentTime = millis();`
  - Check interval: `if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS)`
  - Update time: `lastSampleTime = currentTime;`
  - Purpose: 20ms intervals = 50Hz sampling per sensor, non-blocking
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.8**: Implement loop() sensor processing (Phase 3 TRD R32-R34)
  - Clear flag: `system.beatDetectedThisLoop = false;`
  - Loop through sensors: `for (int i = 0; i < NUM_SENSORS; i++)`
  - Process each sensor:
    - `readAndFilterSensor(i);`  // Sample + moving average
    - `updateBaseline(i);`        // Adaptive threshold tracking
    - `detectBeat(i);`            // Beat detection + OSC transmission
  - Purpose: Each sensor processed independently, no crosstalk
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.9**: Implement loop() LED update (Phase 3 TRD R34)
  - Call: `updateLED();`
  - Purpose: LED responds to beats from ANY sensor
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.10**: Implement loop() debug output (Phase 3 TRD R35)
  - Add conditional: `#if DEBUG_LEVEL >= 2`
  - Throttle output: `if (system.loopCounter % 5 == 0)`  // Every 100ms (5 samples)
  - Print smoothed values for all 4 sensors: "[0]=value [1]=value [2]=value [3]=value"
  - Increment counter: `system.loopCounter++;`
  - Purpose: Prevents serial buffer overflow, shows signal activity
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.11**: Implement loop() WiFi monitoring (Phase 3 TRD R36)
  - Call: `checkWiFi();`
  - Note: Rate-limited internally (every 5 seconds)
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.12**: Implement loop() stability delay (Phase 3 TRD R36)
  - Add: `delay(1);`
  - Purpose: Minimal delay, allows WiFi background tasks, non-blocking
  - **Status**: Code compiles: `pio run`

- [ ] **Task 9.13**: Verify complete firmware compiles and uploads (Phase 4 TRD Section 3.4)
  - Compile full implementation: `pio run`
  - **Expected**: No compilation errors, all components integrated
  - Upload to ESP32: `pio run --target upload`
  - **Expected**: Upload succeeds, device boots without immediate crash
  - Monitor serial for 10 seconds: `pio device monitor`
  - **Expected**: Startup banner visible, no immediate runtime errors
  - **Status**: Firmware boots successfully on hardware

### Component 8.10: Single-Sensor Testing (Phase 4 TRD Section 4.2)

- [ ] **Task 10.1**: Configure firmware for testing (Phase 4 TRD Section 4.2)
  - Edit `src/main.cpp`
  - Set `WIFI_SSID` to match development WiFi network (2.4GHz only)
  - Set `WIFI_PASSWORD` with correct password
  - Find development machine IP: `ip addr show` (Linux) or `ifconfig` (Mac)
  - Set `SERVER_IP` to development machine IP (NOT 127.0.0.1)
  - Set `DEBUG_LEVEL = 1` (testing mode)
  - **Status**: Configuration matches network environment

- [ ] **Task 10.2**: Compile and upload firmware (Phase 4 TRD Section 4.2)
  - Compile: `pio run`
  - **Expected**: Compilation succeeds, shows RAM/Flash usage
  - Connect ESP32 via USB
  - Verify port: `pio device list`
  - Upload: `pio run --target upload`
  - **Expected**: Upload completes, "Hard resetting via RTS pin..."
  - **Status**: Firmware uploaded successfully

- [ ] **Task 10.3**: Verify serial output with no fingers (Phase 4 TRD Section 4.2)
  - Open serial monitor: `pio device monitor`
  - **Expected output**:
    - Startup banner: "=== Heartbeat Installation - Phase 4 ==="
    - Sensor initialization messages (4 sensors on GPIO 32-35)
    - "Connecting to WiFi: [SSID]"
    - "Connected! IP: [IP_ADDRESS]"
    - "Setup complete. Starting beat detection with OSC transmission..."
    - NO beat messages (no fingers on sensors)
  - **Status**: Serial output matches expected format, no false beats

- [ ] **Task 10.4**: Validate OSC message format (Phase 4 TRD Section 4.1)
  - Place finger on Sensor 0, capture 10+ beats
  - Check Python receiver output for format validation
  - **Expected receiver output**:
    - All messages have address `/heartbeat/0`
    - All messages have int32 type tag
    - IBI values in 300-3000ms range
    - Zero invalid messages
  - Optional: Use Wireshark to inspect raw UDP packets
  - **Status**: OSC format validated per architecture spec

- [ ] **Task 10.5**: Test single sensor beat detection (Phase 4 TRD Section 4.2)
  - Start Python receiver: `python3 testing/osc_receiver.py --port 8000` (in separate terminal)
  - Place one finger firmly on Sensor 0 (GPIO 32)
  - Monitor serial output for 30 seconds
  - **Expected serial output**:
    - "[0] First beat at <timestamp>ms (no message sent)"
    - "[0] Beat at <timestamp>ms, IBI=<value>ms"
    - IBI values 600-1200ms typical (50-100 BPM)
    - NO messages from sensors 1-3 (no crosstalk)
  - **Expected receiver output**:
    - "[/heartbeat/0] IBI: <value>ms, BPM: <calculated>"
    - Messages at heartbeat rate (~60-80 per minute)
  - **Status**: Single sensor detects beats, OSC messages received

- [ ] **Task 10.6**: Verify LED behavior (Phase 4 TRD R4)
  - During "Connecting to WiFi": LED blinks rapidly (10Hz)
  - After "Connected!": LED solid ON
  - During beats: LED flashes briefly (50ms pulse, visible)
  - **Status**: Visual confirmation of LED states responding to real beats

- [ ] **Task 10.7**: Test sensor independence (Phase 3 TRD Section 10.2)
  - Remove finger from Sensor 0
  - Wait 2 seconds (verify messages stop)
  - Place finger on Sensor 1 (GPIO 33)
  - Monitor for 15 seconds
  - Move to Sensor 2 (GPIO 34), monitor 15 seconds
  - Move to Sensor 3 (GPIO 35), monitor 15 seconds
  - **Expected**: Only active sensor sends messages, no crosstalk
  - **Status**: Each sensor operates independently

- [ ] **Task 10.8**: Test disconnection detection (Phase 3 TRD Section 10.4)
  - Place finger on Sensor 0
  - Wait for steady beats (3-4 beats)
  - Remove finger suddenly
  - Monitor serial and receiver
  - **Expected**: Messages stop within 1 second of removal
  - Reapply finger
  - **Expected**: First beat after reconnection: no message (establishes reference)
  - **Expected**: Subsequent beats resume normally
  - **Status**: Disconnection and reconnection working correctly

- [ ] **Task 10.9**: Validate BPM accuracy (Phase 4 TRD Section 4.7)
  - Install smartphone heart rate app (e.g., "Instant Heart Rate")
  - Simultaneously measure:
    - Left index finger on smartphone camera
    - Right index finger on ESP32 Sensor 0
  - Measure for 60 seconds
  - Record: Smartphone BPM, ESP32 average BPM (from receiver)
  - Calculate difference
  - **Expected**: Difference ≤5 BPM
  - **Status**: BPM accuracy validated (±5 BPM acceptable)

### Component 8.11: Multi-Sensor Testing (Phase 4 TRD Section 4.3)

- [ ] **Task 11.1**: Test two-person simultaneous operation (Phase 4 TRD Section 4.3)
  - 2 people: Each place finger on different sensor (e.g., Sensor 0 and Sensor 2)
  - Run for 5 minutes
  - Monitor Python receiver output
  - **Expected**:
    - Messages from both sensors interleaved
    - Independent timing (different BPM rates)
    - No crosstalk or interference
    - LED blinks on beats from EITHER sensor
  - **Status**: Two-sensor concurrent operation validated

- [ ] **Task 11.2**: Test four-person simultaneous operation (Phase 4 TRD Section 4.3)
  - 4 people: Each place finger on different sensor (0-3)
  - Run for 5 minutes
  - Monitor receiver statistics
  - **Expected receiver output**:
    - Messages from all 4 sensors: `/heartbeat/0`, `/heartbeat/1`, `/heartbeat/2`, `/heartbeat/3`
    - Interleaved timing (independent beat rates)
    - Each person's BPM stable (±5 BPM variation)
    - Invalid message count = 0
  - **Status**: Four-sensor concurrent operation validated

- [ ] **Task 11.3**: Verify multi-sensor acceptance criteria (Phase 3 TRD Section 11.3)
  - Check: All 4 sensors operate simultaneously
  - Check: No crosstalk (inactive sensors silent)
  - Check: Independent beat detection per sensor
  - Check: LED responds to beats from ANY sensor
  - Check: 2-4 person test successful
  - **Status**: All multi-sensor criteria met

### Component 8.12: Performance & Stability Testing (Phase 4 TRD Section 4.4-4.6)

- [ ] **Task 12.1**: Measure latency (Phase 4 TRD Section 4.4)
  - Set `DEBUG_LEVEL = 2`
  - Add timestamp logging in `detectBeat()`:
    - Record time before `sendHeartbeatOSC()` call
    - Record time after `sendHeartbeatOSC()` returns
    - Print latency in milliseconds
  - Place finger on sensor, capture 20+ beats
  - Calculate: Min, max, average, 95th percentile latency
  - **Expected**: 95th percentile <25ms, typical <10ms
  - Remove timestamp logging after test (keep DEBUG_LEVEL 2 option)
  - **Status**: Latency validated (<25ms target met)

- [ ] **Task 12.2**: Extended stability test (Phase 4 TRD Section 4.5)
  - Set `DEBUG_LEVEL = 1` (testing mode)
  - 2-4 people on sensors
  - Run for 60+ minutes continuous
  - Monitor: Serial output, Python receiver statistics
  - **Expected**:
    - No ESP32 resets (check serial for startup banner)
    - No WiFi disconnections (or successful auto-reconnects)
    - Consistent beat detection throughout (no degradation)
    - LED continues to respond (not frozen)
    - Receiver: 0 invalid messages, consistent message rate
  - Record: Total messages received, packet loss %, average latency
  - **Status**: 60-minute stability test passed, no crashes or degradation

- [ ] **Task 12.3**: WiFi resilience test (Phase 4 TRD Section 4.6)
  - Firmware running with beats being detected
  - Disable WiFi access point for 30 seconds
  - Monitor serial output
  - Re-enable access point
  - **Expected behavior**:
    - WiFi disconnection detected within 5 seconds
    - Serial: "WiFi disconnected, reconnecting..."
    - Beat detection continues (no beats missed)
    - Reconnection automatic within 30 seconds
    - OSC transmission resumes immediately after reconnection
    - LED shows connection status (blink during reconnect, solid after)
  - **Status**: WiFi resilience validated, automatic reconnection working

### Component 8.13: Production Configuration (Phase 4 TRD Section 5)

- [ ] **Task 13.1**: Test production mode (DEBUG_LEVEL 0) (Phase 4 TRD Section 5.1)
  - Edit `src/main.cpp`: Set `DEBUG_LEVEL = 0`
  - Compile and upload: `pio run --target upload`
  - Monitor serial: `pio device monitor`
  - **Expected serial output**:
    - Startup banner
    - WiFi connection messages
    - "Setup complete. Starting beat detection..."
    - NO beat detection messages (minimal output)
    - Errors still visible if they occur
  - Place finger on sensor, verify Python receiver still shows messages
  - **Status**: Production mode tested, minimal serial overhead

- [ ] **Task 13.2**: Create production configuration checklist (Phase 4 TRD Section 5.2)
  - Create file: `PRODUCTION_CHECKLIST.md` in firmware directory
  - Document pre-deployment checklist:
    - Hardware: All 4 sensors mounted, ESP32 powered, sensors labeled
    - Configuration: WiFi credentials, SERVER_IP, DEBUG_LEVEL=0
    - Testing: 4-person test, 30+ minute stability, WiFi resilience
    - Documentation: Sensor mapping, troubleshooting guide, reset procedure
  - **Status**: Production checklist documented

- [ ] **Task 13.3**: Document production serial output expectations (Phase 4 TRD Section 5.3)
  - Add to README: Production mode (DEBUG_LEVEL 0) serial output
  - Document: Minimal output for performance, errors still visible
  - Document: When to switch to Level 1 for troubleshooting
  - Document: When to switch to Level 2 for algorithm tuning
  - **Status**: Production serial output documented

- [ ] **Task 13.4**: Validate production acceptance criteria (Phase 4 TRD Section 6.1)
  - Verify all Phase 4 acceptance criteria:
    - ✅ Phase 3 beat detection + Phase 1 OSC messaging integrated
    - ✅ Real sensor IBIs transmitted (no test values)
    - ✅ sendHeartbeatOSC() called on every beat detection
    - ✅ LED responds to real beats (not timer-based)
    - ✅ All 4 sensors detect beats independently
    - ✅ OSC message format correct: `/heartbeat/[0-3] <int32>`
    - ✅ BPM accuracy ±5 BPM vs smartphone reference
    - ✅ First beat detection: no OSC sent (correct behavior)
    - ✅ Disconnection detection working (<1 sec response)
    - ✅ Latency <25ms (95th percentile)
    - ✅ 60+ minute stability test passes
    - ✅ WiFi auto-reconnect validated
    - ✅ DEBUG_LEVEL 0 tested (production mode)
  - **Status**: All Phase 4 acceptance criteria verified

### Component 8.14: Documentation & Completion (Phase 4 TRD Section 8, 9)

- [ ] **Task 14.1**: Update firmware README with Phase 4 details
  - Update `firmware/heartbeat_phase4/README.md`:
    - Phase 4 purpose: OSC Integration & Production Validation
    - How to configure WiFi credentials and SERVER_IP
    - Debug levels and when to use each (0/1/2)
    - Beat detection parameters and tuning guidance
    - 4-sensor hardware setup (GPIO 32-35)
    - Testing procedure: single-sensor, multi-sensor, stability
    - Production deployment checklist reference
  - **Status**: README complete with Phase 4 implementation guide

- [ ] **Task 14.2**: Document troubleshooting procedures (Phase 4 TRD Section 8)
  - Create: `TROUBLESHOOTING.md` in firmware directory
  - Document common issues:
    - Beats detected but no OSC messages → check WiFi, verify sendHeartbeatOSC() called
    - No beats detected → check sensor contact, ambient light, threshold tuning
    - False beats / double triggers → adjust refractory period, threshold
    - Crosstalk between sensors → verify per-sensor state management
    - High latency → check WiFi signal, network congestion
    - BPM inaccuracy → adjust THRESHOLD_FRACTION, improve sensor contact
  - Include: Debug steps, solutions, parameter tuning guidance
  - **Status**: Troubleshooting guide complete

- [ ] **Task 14.3**: Document beat detection parameters (Phase 3 TRD Section 4.3-4.4)
  - Add to README: Signal processing parameters section
  - Document tunable parameters:
    - THRESHOLD_FRACTION: 0.5-0.7 typical (0.6 default)
    - MIN_SIGNAL_RANGE: 50 default (ADC units)
    - REFRACTORY_PERIOD_MS: 300ms default (max 200 BPM)
    - BASELINE_DECAY_RATE: 0.1 default (10% decay)
  - Explain when and how to adjust each parameter
  - **Status**: Parameter tuning documented

- [ ] **Task 14.4**: Create installation validation checklist (Phase 4 TRD Section 9.2)
  - Create: `INSTALLATION_VALIDATION.md` in firmware directory
  - Document on-site validation steps:
    - Network setup: Configure WiFi, test ESP32 connects, verify server reachable
    - Multi-person test: 4 volunteers, 15+ minutes, validate audio synthesis
    - Environmental adaptation: Test lighting conditions, adjust thresholds, test various users
    - Technician training: Monitor system status, reset procedure, troubleshooting
  - Include: Daily checks, backup procedures, monitoring guidelines
  - **Status**: Installation validation checklist complete

- [ ] **Task 14.5**: Final validation against TRD (Phase 4 TRD Section 11)
  - Review Phase 4 TRD Section 6 (Acceptance Criteria)
  - Verify all technical metrics met:
    - ✅ OSC format correctness: 100% valid
    - ✅ BPM accuracy: ±5 BPM vs smartphone
    - ✅ Latency (95th %ile): <25ms
    - ✅ Packet loss: <1%
    - ✅ Stability (60min): 0 crashes
    - ✅ WiFi resilience: Auto-reconnect <30s
    - ✅ Multi-sensor independence: No crosstalk
    - ✅ Production mode: Clean operation
  - Review qualitative assessment (TRD Section 11.2):
    - ✅ Technician can set up in <15 minutes
    - ✅ Users get immediate response
    - ✅ System runs unattended for hours
    - ✅ Visual feedback clear (LED)
  - **Status**: All Phase 4 requirements verified and documented

- [ ] **Task 14.6**: Update project tasks completion status
  - Mark Component 8 as complete in project documentation
  - Record: Phase 4 firmware implementation complete
  - Record: Firmware version, completion date
  - Note: Ready for festival deployment pending on-site validation
  - **Status**: Phase 4 firmware implementation complete

---

## Task Execution Notes

**Order**: Tasks should be completed in sequence within each component. Components 8.1-8.9 are code implementation, 8.10-8.13 are validation, 8.14 is documentation.

**Testing Strategy**:
- Tasks 2.x-9.x: Incremental development with compilation checks (`pio run` after each task)
- Task 10.x: Single-unit validation (one sensor at a time, then independence)
- Task 11.x: Multi-unit validation (2-4 people simultaneously)
- Task 12.x: Performance and stability validation (latency, extended duration, WiFi resilience)
- Task 13.x: Production configuration validation
- Task 14.x: Documentation and final acceptance

**Implementation Approach**:
- **Unified Phase 3 + Phase 4**: Following TRD Option B (recommended approach)
- Implements Phase 3 beat detection algorithm AND Phase 4 OSC integration together
- Single firmware combining: 4-sensor sampling, signal processing, beat detection, OSC transmission
- Builds on Phase 1 validated WiFi and OSC infrastructure

**Hardware Required**:
- 1 ESP32-WROOM-32 board (or compatible)
- 4 optical pulse sensors (12-bit ADC, 0-4095 range)
- Sensor connections: GPIO 32, 33, 34, 35 (ADC1 channels)
- USB cable for programming (data capable, not charge-only)
- Development machine with WiFi and PlatformIO CLI
- 2.4GHz WiFi network (ESP32 does not support 5GHz)

**Multi-Person Testing Required**:
- Single-person tests: Tasks 10.5-10.9 (verify each sensor independently)
- Two-person test: Task 11.1 (verify concurrent operation)
- Four-person test: Task 11.2 (verify full system capacity)
- Extended test: Task 12.2 (60+ minutes with 2-4 people)

**Dependencies**:
- Phase 1 complete and validated (WiFi + OSC infrastructure)
- Python OSC receiver working (testing infrastructure)
- PlatformIO CLI installed and configured
- ESP32 platform installed
- USB drivers working

**Time Estimate**:
- Prerequisites (Tasks 0.x): 20-30 min (verification and hardware setup)
- Project structure (Tasks 1.x): 10-15 min
- Firmware skeleton (Tasks 2.x): 30-40 min (configuration constants, data structures)
- Sensor initialization (Tasks 3.x): 20-30 min
- Signal processing (Tasks 4.x): 45-60 min (filtering, baseline tracking)
- Beat detection (Tasks 5.x): 45-60 min (threshold, rising edge, refractory, IBI)
- OSC integration (Tasks 6.x): 30-40 min (updated signature, integration)
- LED feedback (Tasks 7.x): 15-20 min
- WiFi functions (Tasks 8.x): 20-30 min (adapt from Phase 1)
- Main program flow (Tasks 9.x): 45-60 min (setup, loop structure)
- Single-sensor testing (Tasks 10.x): 60-90 min (compile, upload, validate each sensor)
- Multi-sensor testing (Tasks 11.x): 45-60 min (requires 2-4 people)
- Performance testing (Tasks 12.x): 90-120 min (latency, 60-min stability, WiFi resilience)
- Production config (Tasks 13.x): 30-40 min (DEBUG_LEVEL 0 testing, checklists)
- Documentation (Tasks 14.x): 45-60 min (README, troubleshooting, validation)
- **Total: 8-11 hours** (6-8 hours code + 2-3 hours testing)

**Acceptance**: Component 8 complete when all tasks checked off and firmware successfully tested:
- ✅ Single-sensor operation validated (BPM accuracy ±5 BPM)
- ✅ Multi-sensor operation validated (4 people simultaneously, no crosstalk)
- ✅ Performance validated (latency <25ms, 60+ min stability, WiFi resilience)
- ✅ Production mode tested (DEBUG_LEVEL 0)
- ✅ All Python receiver messages valid (0 invalid messages)
- ✅ All acceptance criteria met (Phase 4 TRD Section 6)

**Key Success Metrics**:
- OSC format correctness: 100% valid messages
- BPM accuracy: ±5 BPM vs smartphone reference
- Latency: <25ms (95th percentile)
- Stability: 60+ minutes with 0 crashes
- Multi-sensor: All 4 sensors independent, no crosstalk
- Production: Clean operation with minimal serial output

**Next Steps After Phase 4**:
- Server-side Pure Data OSC receiver implementation
- Audio synthesis integration (map IBI/BPM to audio parameters)
- Festival installation and on-site validation
- Lighting control integration (optional)
- Technician training and documentation

**Phase 4 Deliverables**:
- ✅ Single `main.cpp` with unified Phase 3 + Phase 4 implementation
- ✅ Real beat detection from 4 sensors at 50Hz
- ✅ OSC messages: `/heartbeat/[0-3] <int32_ibi_ms>`
- ✅ LED feedback on real beats (any sensor)
- ✅ Production-ready configuration (DEBUG_LEVEL 0 tested)
- ✅ Comprehensive documentation (README, troubleshooting, installation validation)
- ✅ End-to-end validation complete (sensor → ESP32 → network → server)

---

**END OF PHASE 4 TASK BREAKDOWN**
