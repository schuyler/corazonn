# Heartbeat Firmware - Phase 2 Firmware Implementation TRD
## ESP32 Heartbeat Detection + Real OSC Data

**Version:** 1.0
**Date:** 2025-11-09
**Purpose:** Define ESP32 firmware requirements for ADC sampling, signal processing, beat detection, and real heartbeat OSC transmission
**Audience:** Coding agent implementing ESP32 firmware
**Hardware:** ESP32-WROOM-32 with PulseSensor optical pulse sensor
**Framework:** Arduino (via PlatformIO CLI for automated testing)
**Toolchain:** PlatformIO CLI (command-line compilation, upload, monitoring)

**⚠️ CRITICAL: PREREQUISITES**
```
Step 1: Complete phase1-firmware-trd.md FIRST
Step 2: Validate Phase 1 WiFi and OSC messaging working
Step 3: Connect PulseSensor hardware (GPIO 32)
Step 4: Then implement this firmware
Step 5: Test with real heartbeat detection
```

Phase 1 WiFi and OSC infrastructure MUST be working before starting Phase 2 implementation.

**Estimated Implementation Time:** 3-4 hours (code) + 2 hours (testing and tuning)

---

## 0. Prerequisites

### 0.1 Phase 1 Completion

**MUST have completed:**
- ✅ Phase 1 firmware uploaded and running
- ✅ WiFi connection stable
- ✅ OSC messages successfully transmitted to server
- ✅ Python OSC receiver validates message format
- ✅ 5-minute stability test passed

**Verify Phase 1 working:**
```bash
# Terminal 1: Start receiver
python3 osc_receiver.py --port 8000

# Terminal 2: Monitor ESP32 serial output
pio device monitor

# Should see test messages flowing at 1 Hz
```

### 0.2 Hardware Setup

**MUST complete before coding:**

**Step 1: Connect PulseSensor**
```
PulseSensor:
  Signal wire (purple/white) → ESP32 GPIO 32 (ADC1_CH4)
  VCC wire (red) → ESP32 3.3V
  GND wire (black) → ESP32 GND
```

**Step 2: Verify Sensor Connection**
```cpp
// Test code to verify sensor connected:
void setup() {
    Serial.begin(115200);
    pinMode(32, INPUT);
}
void loop() {
    int raw = analogRead(32);
    Serial.println(raw);
    delay(100);
}
// Expected: Values change 2000-3000 range when finger applied
//           Values ~0 or constant when no finger
```

**Step 3: Physical Setup**
- PulseSensor should be secured (tape or mounting bracket)
- Sensor LED should face outward (detects reflected light)
- Cable connections should be stable (no loose jumper wires)

---

## 1. Objective

Implement ESP32 firmware that reads analog sensor data, detects heartbeats using adaptive threshold algorithm, calculates inter-beat intervals, and transmits real heartbeat timing via OSC. Replaces Phase 1 test values with actual physiological data.

**Deliverables:**
- Single `main.cpp` source file (builds on Phase 1 structure)
- ADC sampling at 50 Hz per sensor
- Moving average filter for noise reduction
- Adaptive baseline tracking (handles varying signal amplitude)
- Beat detection with refractory period
- Real IBI calculation and OSC transmission
- Sensor disconnection detection
- Validated against real heartbeat data

**Success Criteria:**
- Firmware uploads to ESP32 without errors
- Detects heartbeats within 3 seconds of finger application
- BPM accuracy within ±5 BPM vs smartphone app
- Runs for 30+ minutes without crashes
- Handles sensor disconnect/reconnect gracefully
- OSC messages contain real IBI data (not test values)

---

## 2. Architecture Overview

### 2.1 Execution Model

**Single-threaded non-blocking architecture (same as Phase 1):**
- `setup()`: Initialize hardware, WiFi (reuse Phase 1), configure ADC, initialize sensor state
- `loop()`: Sample sensors at 50Hz, process signal, detect beats, send OSC, update LED
- No RTOS tasks, no interrupts (keep Phase 1 simplicity)

**Timing:**
- Phase 1: 1000ms test message interval → **Phase 2: 20ms ADC sample interval (50Hz)**
- Use `millis()` for non-blocking timing (same as Phase 1)
- Main loop cycles every ~20ms (vs Phase 1 10ms)

### 2.2 Data Flow

```
ADC Sample (50Hz) → Moving Average Filter → Baseline Tracking → 
Beat Detection (threshold + refractory) → IBI Calculation → OSC Transmission
```

### 2.3 State Machine (Phase 2 Extension)

```
STARTUP → WIFI_CONNECTING → WIFI_CONNECTED → SENSOR_INIT → RUNNING
                ↓                                              ↓
           ERROR_HALT                                  SENSOR_DISCONNECTED
                                                               ↓
                                                        (auto-reconnect)
```

**New States:**
- `SENSOR_INIT`: First ADC reading, initialize moving average buffer
- `SENSOR_DISCONNECTED`: Flat signal detected, stop sending OSC
- `RUNNING`: Normal operation with beat detection

---

## 3. Required Libraries

### 3.1 Arduino Libraries (Phase 1 + New)

**Phase 1 Libraries (keep):**
- `WiFi.h` - ESP32 WiFi stack
- `WiFiUdp.h` - UDP socket implementation
- `OSC` by Adrian Freed (CNMat) - OSC message construction

**No new external libraries needed for Phase 2**

**Built-in ESP32 Functions (Phase 2):**
- `analogRead(pin)` - 12-bit ADC reading (0-4095)
- `analogSetAttenuation(ADC_11db)` - Set ADC input range to 0-3.3V

### 3.2 ADC Configuration

```cpp
// In setup(), before first analogRead():
analogSetAttenuation(ADC_11db);  // 0-3.3V input range
analogReadResolution(12);        // 12-bit resolution (0-4095)
```

**Requirements:**
- GPIO 32 is ADC1_CH4 (safe for WiFi, does not conflict)
- 12-bit resolution provides 0-4095 range
- PulseSensor outputs 0-3V, maps to ~0-3723 ADC units

---

## 4. Configuration Constants

### 4.1 Network Configuration (Phase 1 - Keep Unchanged)

```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS
const uint16_t SERVER_PORT = 8000;
```

**No changes from Phase 1** - WiFi and OSC parameters stay the same.

### 4.2 Hardware Configuration (Phase 2 Extension)

```cpp
// Phase 1 (keep):
const int STATUS_LED_PIN = 2;  // Built-in LED

// Phase 2 (add):
const int SENSOR_PIN = 32;     // GPIO 32 (ADC1_CH4)
const int ADC_RESOLUTION = 12; // 12-bit (0-4095)
```

**Requirements:**
- GPIO 32 is ADC1 channel (safe with WiFi)
- Input-only pin (no internal pullup/pulldown)
- 12-bit resolution standard on ESP32

### 4.3 Signal Processing Parameters (Phase 2 New)

```cpp
// Sampling configuration
const int SAMPLE_RATE_HZ = 50;              // 50 samples/second
const int SAMPLE_INTERVAL_MS = 20;          // 1000 / 50 = 20ms

// Moving average filter
const int MOVING_AVG_SAMPLES = 5;           // 100ms smoothing window (5 samples @ 50Hz)

// Baseline tracking (exponential decay)
const float BASELINE_DECAY_RATE = 0.1;      // 10% decay per interval
const int BASELINE_DECAY_INTERVAL = 150;    // Apply every 150 samples (3 seconds @ 50Hz)
```

**Rationale:**
- 50Hz sampling: Adequate for heartbeat (1-3 Hz fundamental frequency)
- 5-sample moving average: 100ms window smooths noise without excessive lag
- Baseline decay: 3-second interval balances stability vs adaptation

### 4.4 Beat Detection Parameters (Phase 2 New)

```cpp
// Threshold detection
const float THRESHOLD_FRACTION = 0.6;         // 60% of signal range above baseline
const int MIN_SIGNAL_RANGE = 50;              // Minimum ADC range for valid signal

// Refractory period
const unsigned long REFRACTORY_PERIOD_MS = 300;  // 300ms = max 200 BPM

// Disconnection detection
const int FLAT_SIGNAL_THRESHOLD = 5;          // ADC variance < 5 = flat
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;  // 1 second flat = disconnected
```

**Rationale:**
- 60% threshold: Empirically effective for PulseSensor (tunable 50-70%)
- Min range 50: Prevents false beats from noise on flat signals
- 300ms refractory: Prevents double-triggers, limits to physiological max (200 BPM)
- 1-second disconnect timeout: Fast response when sensor removed

### 4.5 System Configuration (Phase 1 Keep + Phase 2 Modify)

```cpp
const int SENSOR_ID = 0;  // CHANGE THIS: 0, 1, 2, or 3 (Phase 1)

// Phase 1 constant REMOVED:
// const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;  // NO LONGER USED

const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 seconds (Phase 1, keep)
```

**Phase 2 Changes:**
- Remove `TEST_MESSAGE_INTERVAL_MS` (no longer sending periodic test messages)
- OSC messages now triggered by beat detection events (asynchronous)

---

## 5. Data Structures

### 5.1 System State (Phase 1 - Modify)

**Phase 1 Structure:**
```cpp
struct SystemState {
    bool wifiConnected;
    unsigned long lastMessageTime;
    uint32_t messageCounter;
};
```

**Phase 2 Modified Structure:**
```cpp
struct SystemState {
    bool wifiConnected;           // Phase 1: Current WiFi connection status
    unsigned long lastWiFiCheckTime;  // Phase 2: For WiFi monitoring rate limit
    unsigned long loopCounter;    // Phase 2: For debug output throttling
    // Remove: lastMessageTime, messageCounter (no longer periodic messages)
    // Note: messageCounter was only used for Phase 1 periodic test messages,
    //       which are replaced by event-driven beat detection in Phase 2.
};
```

**Initial Values:**
```cpp
SystemState state = {
    .wifiConnected = false,
    .lastWiFiCheckTime = 0,
    .loopCounter = 0
};
```

### 5.2 Sensor State (Phase 2 New)

**Purpose:** Track signal processing and beat detection for one sensor

```cpp
struct SensorState {
    // Moving average filter
    int rawSamples[MOVING_AVG_SAMPLES];  // Circular buffer (5 samples)
    int sampleIndex;                      // Current position in buffer
    int smoothedValue;                    // Output of moving average

    // Baseline tracking (exponential decay)
    int minValue;                         // Minimum, decays upward
    int maxValue;                         // Maximum, decays downward
    int samplesSinceDecay;                // Counter for 3-second decay interval

    // Beat detection state
    bool aboveThreshold;                  // Currently above threshold?
    unsigned long lastBeatTime;           // millis() of last beat
    unsigned long lastIBI;                // Inter-beat interval (ms)
    bool firstBeatDetected;               // Have we sent first beat?

    // Disconnection detection
    bool isConnected;                     // Valid signal present?
    int lastRawValue;                     // For flat signal detection
    int flatSampleCount;                  // Consecutive flat samples
};
```

**Initial Values:**
```cpp
SensorState sensor = {
    .rawSamples = {0},        // Will be initialized in setup()
    .sampleIndex = 0,
    .smoothedValue = 0,
    .minValue = 0,            // Will be set to first reading
    .maxValue = 4095,         // Will be set to first reading
    .samplesSinceDecay = 0,
    .aboveThreshold = false,
    .lastBeatTime = 0,
    .lastIBI = 0,
    .firstBeatDetected = false,
    .isConnected = false,     // Set true after first valid reading
    .lastRawValue = 0,
    .flatSampleCount = 0
};
```

### 5.3 Global Objects (Phase 1 Keep + Phase 2 Add)

```cpp
WiFiUDP udp;                  // Phase 1: UDP socket
SystemState state;            // Phase 2: Modified system state
SensorState sensor;           // Phase 2: Sensor state
static unsigned long ledPulseTime = 0;  // Time when LED pulse started
```

**Note:** Phase 2 implements single sensor (GPIO 32). Phase 3 will expand to 4 sensors.

---

## 6. Function Specifications

### 6.1 Sensor Initialization (Phase 2 New)

**Function:** `initializeSensor()`

**Signature:**
```cpp
void initializeSensor();
```

**Purpose:** Initialize ADC, pre-fill moving average buffer, set initial baseline

**Requirements:**

**R1: ADC Configuration**
- MUST call `analogSetAttenuation(ADC_11db)` for 0-3.3V range
- MUST call `analogReadResolution(12)` for 12-bit resolution
- MUST configure `SENSOR_PIN` (GPIO 32)
- Note: Some ESP32 cores may require `adcAttachPin(SENSOR_PIN)` to be called first for per-pin configuration

**R2: Initial Reading**
- MUST read first ADC sample: `int firstReading = analogRead(SENSOR_PIN)`
- MUST print first reading to serial for debugging

**R3: Moving Average Initialization**
- MUST pre-fill `rawSamples[]` array with first reading
- Prevents invalid data during buffer fill period
- Loop: `for (int i = 0; i < MOVING_AVG_SAMPLES; i++) sensor.rawSamples[i] = firstReading`

**R4: Baseline Initialization**
- MUST set `sensor.minValue = firstReading`
- MUST set `sensor.maxValue = firstReading`
- MUST set `sensor.smoothedValue = firstReading`

**R5: Connection State**
- MUST set `sensor.isConnected = true` (assume connected at start)
- MUST set `sensor.lastRawValue = firstReading`
- MUST set `sensor.lastBeatTime = millis()` (prevents false refractory rejection on first beat)

**Pseudocode:**
```
function initializeSensor():
    analogSetAttenuation(ADC_11db)
    analogReadResolution(12)
    # Note: Some ESP32 cores may require: adcAttachPin(SENSOR_PIN) first
    
    firstReading = analogRead(SENSOR_PIN)
    Serial.print("First ADC reading: ")
    Serial.println(firstReading)
    
    for i in 0 to MOVING_AVG_SAMPLES-1:
        sensor.rawSamples[i] = firstReading
    
    sensor.smoothedValue = firstReading
    sensor.minValue = firstReading
    sensor.maxValue = firstReading
    sensor.isConnected = true
    sensor.lastRawValue = firstReading
    sensor.lastBeatTime = millis()  # Prevents false refractory rejection on first beat
```

---

### 6.2 Moving Average Filter (Phase 2 New)

**Function:** `updateMovingAverage()`

**Signature:**
```cpp
void updateMovingAverage(int rawValue);
```

**Purpose:** Add new sample to circular buffer and calculate smoothed value

**Parameters:**
- `rawValue`: Current ADC reading (0-4095)

**Requirements:**

**R6: Circular Buffer Update**
- MUST replace oldest sample in buffer: `sensor.rawSamples[sensor.sampleIndex] = rawValue`
- MUST increment index: `sensor.sampleIndex = (sensor.sampleIndex + 1) % MOVING_AVG_SAMPLES`
- Modulo wraps index to 0 after reaching end

**R7: Calculate Mean**
- MUST sum all samples in buffer
- MUST divide by `MOVING_AVG_SAMPLES` to get mean
- MUST store result in `sensor.smoothedValue`

**R8: No Filtering on First Fill**
- First 5 samples after initialization will gradually replace pre-filled values
- Moving average automatically adapts (no special case needed)

**Pseudocode:**
```
function updateMovingAverage(rawValue):
    sensor.rawSamples[sensor.sampleIndex] = rawValue
    sensor.sampleIndex = (sensor.sampleIndex + 1) % MOVING_AVG_SAMPLES
    
    sum = 0
    for i in 0 to MOVING_AVG_SAMPLES-1:
        sum += sensor.rawSamples[i]
    
    sensor.smoothedValue = sum / MOVING_AVG_SAMPLES
```

---

### 6.3 Baseline Tracking (Phase 2 New)

**Function:** `updateBaseline()`

**Signature:**
```cpp
void updateBaseline();
```

**Purpose:** Track running min/max with exponential decay toward current signal level

**Requirements:**

**R9: Instant Expansion**
- IF `sensor.smoothedValue < sensor.minValue`: Set `sensor.minValue = sensor.smoothedValue`
- IF `sensor.smoothedValue > sensor.maxValue`: Set `sensor.maxValue = sensor.smoothedValue`
- Baseline expands immediately when signal exceeds previous range

**R10: Periodic Decay**
- MUST increment `sensor.samplesSinceDecay++` each call
- IF `sensor.samplesSinceDecay >= BASELINE_DECAY_INTERVAL` (150 samples = 3 seconds):
  - Apply decay toward current signal level (smoothedValue):
    - `sensor.minValue += (sensor.smoothedValue - sensor.minValue) * BASELINE_DECAY_RATE`
    - `sensor.maxValue -= (sensor.maxValue - sensor.smoothedValue) * BASELINE_DECAY_RATE`
  - Reset counter: `sensor.samplesSinceDecay = 0`

**R11: Integer Arithmetic**
- Decay calculation uses float multiplication, then cast to int
- Example: `sensor.minValue += (int)((sensor.smoothedValue - sensor.minValue) * 0.1)`

**Pseudocode:**
```
function updateBaseline():
    # Instant expansion
    if sensor.smoothedValue < sensor.minValue:
        sensor.minValue = sensor.smoothedValue
    if sensor.smoothedValue > sensor.maxValue:
        sensor.maxValue = sensor.smoothedValue
    
    # Periodic decay toward current signal level
    sensor.samplesSinceDecay++
    if sensor.samplesSinceDecay >= BASELINE_DECAY_INTERVAL:
        sensor.minValue += (sensor.smoothedValue - sensor.minValue) * BASELINE_DECAY_RATE
        sensor.maxValue -= (sensor.maxValue - sensor.smoothedValue) * BASELINE_DECAY_RATE
        sensor.samplesSinceDecay = 0
```

---

### 6.4 Disconnection Detection (Phase 2 New)

**Function:** `checkDisconnection()`

**Signature:**
```cpp
void checkDisconnection(int rawValue);
```

**Purpose:** Detect flat signal indicating sensor disconnected

**Parameters:**
- `rawValue`: Current ADC reading (for variance check)

**Requirements:**

**R12: Flat Signal Detection**
- Calculate variance: `int variance = abs(rawValue - sensor.lastRawValue)`
- IF `variance < FLAT_SIGNAL_THRESHOLD` (5 ADC units):
  - Increment `sensor.flatSampleCount++`
- ELSE:
  - Reset `sensor.flatSampleCount = 0`

**R13: Disconnection Threshold**
- IF `sensor.flatSampleCount >= 50` (1 second @ 50Hz):
  - Set `sensor.isConnected = false`
  - MUST print "Sensor disconnected" to serial ONCE (not every sample)

**R14: Range Check**
- Calculate signal range: `int range = sensor.maxValue - sensor.minValue`
- IF `range < MIN_SIGNAL_RANGE` (50 ADC units):
  - Set `sensor.isConnected = false`

**R15: Reconnection Detection**
- IF `sensor.isConnected == false` AND signal shows variation:
  - IF `sensor.flatSampleCount == 0` AND `range >= MIN_SIGNAL_RANGE`:
    - Set `sensor.isConnected = true`
    - MUST print "Sensor reconnected" to serial
    - Reset baseline: `minValue = maxValue = smoothedValue`

**R16: Update Last Value**
- MUST update `sensor.lastRawValue = rawValue` at end (for next comparison)

**Pseudocode:**
```
function checkDisconnection(rawValue):
    variance = abs(rawValue - sensor.lastRawValue)
    
    if variance < FLAT_SIGNAL_THRESHOLD:
        sensor.flatSampleCount++
    else:
        sensor.flatSampleCount = 0
    
    range = sensor.maxValue - sensor.minValue
    
    # Check for disconnection
    wasConnected = sensor.isConnected
    if sensor.flatSampleCount >= 50 OR range < MIN_SIGNAL_RANGE:
        sensor.isConnected = false
        if wasConnected:
            Serial.println("Sensor disconnected")
    
    # Check for reconnection
    if NOT sensor.isConnected AND sensor.flatSampleCount == 0 AND range >= MIN_SIGNAL_RANGE:
        sensor.isConnected = true
        Serial.println("Sensor reconnected")
        sensor.minValue = sensor.smoothedValue
        sensor.maxValue = sensor.smoothedValue
    
    sensor.lastRawValue = rawValue
```

---

### 6.5 Beat Detection (Phase 2 New)

**Function:** `detectBeat()`

**Signature:**
```cpp
void detectBeat();
```

**Purpose:** Detect heartbeat using adaptive threshold with refractory period

**Requirements:**

**R17: Threshold Calculation**
- Calculate threshold: `int threshold = sensor.minValue + (int)((sensor.maxValue - sensor.minValue) * THRESHOLD_FRACTION)`
- Threshold is 60% of signal range above baseline (configurable via THRESHOLD_FRACTION)

**R18: Rising Edge Detection**
- IF `sensor.smoothedValue >= threshold` AND `sensor.aboveThreshold == false`:
  - Potential beat detected (rising edge)
  - Check refractory period BEFORE updating state

**R19: Refractory Period Check (MUST pass BEFORE setting aboveThreshold)**
- IF potential beat detected:
  - Calculate time since last beat: `unsigned long timeSinceLastBeat = millis() - sensor.lastBeatTime`
  - IF `timeSinceLastBeat < REFRACTORY_PERIOD_MS` (300ms):
    - Ignore beat (too soon, likely noise or double-trigger)
    - Return WITHOUT setting `sensor.aboveThreshold` or sending OSC

**R20: Valid Beat Handling**
- IF potential beat AND refractory period passed:
  - IF `sensor.firstBeatDetected == false`:
    - Set `sensor.firstBeatDetected = true`
    - Record timestamp: `sensor.lastBeatTime = millis()`
    - Print "First beat detected" to serial
    - Do NOT send OSC message (no reference IBI)
    - Return
  - ELSE (second and subsequent beats):
    - Calculate IBI: `unsigned long ibi = millis() - sensor.lastBeatTime`
    - Update timestamp: `sensor.lastBeatTime = millis()`
    - Store IBI: `sensor.lastIBI = ibi`
    - Send OSC message: `sendHeartbeatOSC((int)ibi)`
    - Print beat info to serial

**R21: Falling Edge Detection**
- IF `sensor.smoothedValue < threshold` AND `sensor.aboveThreshold == true`:
  - Set `sensor.aboveThreshold = false` (ready for next beat)

**Pseudocode:**
```
function detectBeat():
    if NOT sensor.isConnected:
        return  # No detection when disconnected
    
    threshold = sensor.minValue + (sensor.maxValue - sensor.minValue) * THRESHOLD_FRACTION
    
    # Rising edge
    if sensor.smoothedValue >= threshold AND NOT sensor.aboveThreshold:
        # Potential beat detected
        timeSinceLastBeat = millis() - sensor.lastBeatTime
        
        # R19: Refractory Period Check (BEFORE setting state)
        if timeSinceLastBeat < REFRACTORY_PERIOD_MS:
            return  # Ignore this beat, do NOT update state
        
        # Valid beat - now safe to update state
        sensor.aboveThreshold = true  # Set AFTER refractory check
        
        if NOT sensor.firstBeatDetected:
            sensor.firstBeatDetected = true
            sensor.lastBeatTime = millis()
            Serial.println("First beat detected")
        else:
            ibi = millis() - sensor.lastBeatTime
            sensor.lastBeatTime = millis()
            sensor.lastIBI = ibi
            sendHeartbeatOSC(ibi)
            ledPulseTime = millis()  # Trigger LED pulse
            Serial.print("Beat detected, IBI=")
            Serial.print(ibi)
            Serial.print("ms, BPM=")
            Serial.println(60000 / ibi)
    
    # Falling edge
    if sensor.smoothedValue < threshold AND sensor.aboveThreshold:
        sensor.aboveThreshold = false
```

---

### 6.6 WiFi Functions (Phase 1 - Keep Unchanged)

**Functions from Phase 1 - No Modifications:**
- `connectWiFi()` - TRD Section 6.1 (Phase 1)
- `sendHeartbeatOSC(int ibi_ms)` - TRD Section 6.2 (Phase 1)
- `checkWiFi()` - TRD Section 6.4 (Phase 1)

**Keep exact implementation from Phase 1.** These functions already handle:
- WiFi connection with timeout
- OSC message construction and UDP transmission
- WiFi status monitoring and reconnection

**No changes needed** - Phase 2 just calls `sendHeartbeatOSC()` with real IBI instead of test values.

---

### 6.7 LED Status Indication (Phase 2 Modified)

**Function:** `updateLED()`

**Signature:**
```cpp
void updateLED();
```

**Purpose:** Update LED state based on WiFi and beat detection status

**Requirements:**

**R22: LED States (Phase 2 Enhanced)**
- **WiFi Connecting:** Blink at 5 Hz (100ms on/off) - Phase 1 behavior
- **WiFi Connected, No Beat:** Solid ON - Phase 1 behavior
- **Beat Detected:** 50ms pulse (briefly brighter, then return to solid) - Phase 2 new

**R23: Beat Pulse Implementation**
- When beat detected (call from `detectBeat()`): Set global `ledPulseTime = millis()`
- In `updateLED()`:
  - IF `millis() - ledPulseTime < 50`: Keep LED HIGH (pulse duration)
  - ELSE: Return to solid HIGH (normal connected state)

**R24: State Determination**
- Priority order:
  1. If WiFi not connected: Blink at 5 Hz
  2. If beat pulse active (<50ms since pulse): HIGH
  3. Else: Solid HIGH (connected, waiting for beats)

**Modified Pseudocode:**
```
# ledPulseTime is a global variable (declared in Section 5.3)

function updateLED():
    if NOT state.wifiConnected:
        # Blink during connection
        digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2)
    else if (millis() - ledPulseTime < 50):
        # Beat pulse active
        digitalWrite(STATUS_LED_PIN, HIGH)
    else:
        # Solid on when connected
        digitalWrite(STATUS_LED_PIN, HIGH)

function onBeatDetected():
    ledPulseTime = millis()  # Trigger pulse
```

**Note:** Beat pulse is subtle (both states are HIGH), but can be enhanced with external LED on different pin if needed.

---

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

**Expected Compilation Output (Phase 2):**
```
Processing esp32dev (platform: espressif32; board: esp32dev; framework: arduino)
...
RAM:   [==        ]  16.8% (used 55104 bytes from 327680 bytes)
Flash: [====      ]  38.2% (used 501024 bytes from 1310720 bytes)
========================= [SUCCESS] Took X.XX seconds =========================
```
- Slightly larger than Phase 1 due to signal processing code

---

## 10. Validation & Testing

### 10.1 Prerequisites (Phase 2 Specific)

**MUST have:**
- ✅ Phase 1 firmware tested and working
- ✅ PulseSensor physically connected to GPIO 32
- ✅ Python OSC receiver running
- ✅ Smartphone heart rate app for BPM validation

### 10.2 Validation Procedure

**Step 1: Start Receiver**
```bash
python3 osc_receiver.py --port 8000
```

**Step 2: Upload Phase 2 Firmware**
```bash
pio run --target upload && pio device monitor
```

**Step 3: Verify Startup**
Expected serial output:
```
=== Heartbeat Installation - Phase 2 ===
Real Heartbeat Detection
Sensor ID: 0
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.50.42
First ADC reading: 2456
Sensor initialized. Ready for heartbeat detection.
Setup complete. Place finger on sensor to begin.
```

**Step 4: Apply Finger to Sensor**
- Place fingertip on PulseSensor (cover LED completely)
- Apply gentle, steady pressure
- Hold still for 10 seconds

**Expected Serial Output:**
```
First beat detected
Beat detected, IBI=847ms, BPM=70
Beat detected, IBI=856ms, BPM=70
Beat detected, IBI=843ms, BPM=71
...
```

**Expected Receiver Output:**
```
[/heartbeat/0] IBI: 847ms, BPM: 70.8
[/heartbeat/0] IBI: 856ms, BPM: 70.1
[/heartbeat/0] IBI: 843ms, BPM: 71.2
...
```

**Step 5: Validate LED Behavior**
- Before finger applied: Solid ON (WiFi connected)
- After beats start: Brief flicker on each beat (50ms pulse)

**Step 6: Test Disconnection**
- Remove finger from sensor
- Expected serial output within 1 second:
  ```
  Sensor disconnected
  ```
- Expected receiver: No more messages
- LED stays solid ON (WiFi still connected)

**Step 7: Test Reconnection**
- Reapply finger to sensor
- Expected serial output within 3 seconds:
  ```
  Sensor reconnected
  First beat detected
  Beat detected, IBI=XXXms, BPM=XX
  ```
- Expected receiver: Messages resume

**Step 8: BPM Accuracy Check**
- Use smartphone heart rate app simultaneously
- Compare app BPM to serial output BPM
- Acceptable: ±5 BPM difference
- If outside range: Tune `THRESHOLD_FRACTION` (see Section 11)

**Step 9: Extended Run (30 Minutes)**
- Keep finger on sensor
- Monitor serial output and receiver
- Check for:
  - ✅ No crashes or resets
  - ✅ Consistent BPM (±10 BPM variation normal)
  - ✅ No WiFi disconnections
  - ✅ No memory issues

---

### 10.3 Multi-Unit Testing (Phase 2)

**Requirements:**
- Program 2-4 ESP32s with Phase 2 firmware
- Each unit has unique SENSOR_ID (0, 1, 2, 3)
- All units connected to same WiFi network

**Test Procedure:**
1. Start single Python receiver
2. Power all ESP32s simultaneously
3. Apply different fingers to each sensor
4. Verify receiver shows messages from all sensor IDs
5. Verify each sensor has independent BPM
6. Remove one finger, verify only that sensor stops sending

**Expected Result:**
- 4 independent heartbeat streams
- No interference between sensors
- Different BPM values per person

---

## 11. Tuning & Optimization

### 11.1 Threshold Tuning

**Symptom: Missed Beats (gaps > 2 seconds)**
- Cause: Threshold too high for weak signals
- Solution: Reduce `THRESHOLD_FRACTION` from 0.6 to 0.5
- Test incrementally: 0.6 → 0.55 → 0.5

**Symptom: False Beats (BPM > 120 at rest)**
- Cause: Threshold too low, noise triggers beats
- Solution: Increase `THRESHOLD_FRACTION` from 0.6 to 0.7
- Test incrementally: 0.6 → 0.65 → 0.7

**Symptom: BPM Incorrect (±10+ BPM vs phone app)**
- Cause: Poor sensor contact or movement
- Solution: Improve physical sensor placement, hold still

### 11.2 Debug Output Levels

**Level 0: Production (Default)**
```cpp
// In detectBeat(), keep only beat messages
Serial.print("Beat detected, IBI=");
Serial.println(ibi);
```

**Level 1: Detailed Debug (Enable for Tuning)**
```cpp
// In loop(), every 1 second:
if (state.loopCounter % 50 == 0) {
    Serial.print("Smoothed: ");
    Serial.print(sensor.smoothedValue);
    Serial.print(" Min: ");
    Serial.print(sensor.minValue);
    Serial.print(" Max: ");
    Serial.print(sensor.maxValue);
    Serial.print(" Threshold: ");
    Serial.println(sensor.minValue + (int)((sensor.maxValue - sensor.minValue) * THRESHOLD_FRACTION));
}
```

**Level 2: Raw Data (Enable for Hardware Debug)**
```cpp
// In loop(), every sample:
Serial.print("Raw: ");
Serial.print(rawValue);
Serial.print(" Smoothed: ");
Serial.println(sensor.smoothedValue);
```

**Warning:** Level 2 generates 50 lines/second and can overflow the serial buffer if run continuously. Recommend using only for short diagnostic tests (< 10 seconds).

### 11.3 Parameter Recommendations

**Conservative (fewer false beats, may miss weak beats):**
```cpp
const float THRESHOLD_FRACTION = 0.7;
const int MIN_SIGNAL_RANGE = 80;
const unsigned long REFRACTORY_PERIOD_MS = 350;
```

**Sensitive (catches weak beats, may have false triggers):**
```cpp
const float THRESHOLD_FRACTION = 0.5;
const int MIN_SIGNAL_RANGE = 30;
const unsigned long REFRACTORY_PERIOD_MS = 250;
```

**Default (balanced, works for most users):**
```cpp
const float THRESHOLD_FRACTION = 0.6;
const int MIN_SIGNAL_RANGE = 50;
const unsigned long REFRACTORY_PERIOD_MS = 300;
```

---

## 12. Acceptance Criteria

### 12.1 Compilation

**MUST:**
- ✅ Compile without errors
- ✅ Compile without warnings (or only benign warnings)
- ✅ Binary size < 550KB (reasonable headroom)

### 12.2 Runtime Behavior

**MUST:**
- ✅ Connect to WiFi within 30 seconds
- ✅ Initialize sensor successfully
- ✅ Detect heartbeats within 3 seconds of finger application
- ✅ BPM accuracy within ±5 BPM vs smartphone app
- ✅ OSC messages contain real IBI values (not test values)
- ✅ Python receiver validates all messages (0 invalid)
- ✅ Run for 30+ minutes without crashes
- ✅ LED indicates WiFi connection and beat pulses

### 12.3 Signal Processing

**MUST:**
- ✅ Moving average smooths noisy signals
- ✅ Baseline adapts to different signal amplitudes
- ✅ No false beats from noise
- ✅ No missed beats from weak signals (with proper tuning)
- ✅ Refractory period prevents double-triggers

### 12.4 Disconnection Handling

**MUST:**
- ✅ Detect sensor removal within 1 second
- ✅ Stop sending OSC messages when disconnected
- ✅ Auto-reconnect within 3 seconds of reapplication
- ✅ Resume beat detection after reconnection
- ✅ No crashes when sensor removed/reapplied

### 12.5 Multi-Unit Operation

**MUST:**
- ✅ 4 units operate simultaneously without interference
- ✅ Each unit sends independent heartbeat data
- ✅ Receiver distinguishes all sensor IDs correctly
- ✅ No network congestion (4 sensors × 60-120 BPM = 240-480 msg/min total)

---

## 13. Known Limitations (Phase 2)

**Carried Over from Phase 1:**
- No watchdog timer (will add in Phase 3)
- No sophisticated LED feedback (just on/pulse)
- No power management
- No OTA updates
- No configuration web interface

**Phase 2 Specific:**
- Single sensor only (GPIO 32) - Phase 3 will add 4 sensors
- Fixed threshold fraction (not auto-adaptive per user)
- No waveform transmission (only IBI)
- No HRV analysis
- Optical sensor sensitive to ambient light, movement, cold hands

**These will be addressed in later phases.**

---

## 14. Troubleshooting

### 14.1 Sensor Issues

**No ADC readings (values stuck at 0 or 4095)**
- Check wiring: Signal to GPIO 32, VCC to 3.3V, GND to GND
- Verify PulseSensor LED is on (indicates power)
- Test with multimeter: Signal pin should vary 1-3V when finger applied

**ADC readings constant (no variation)**
- Sensor not detecting pulse
- Try different finger (index or middle finger best)
- Apply more/less pressure
- Cover sensor LED completely (block ambient light)
- Check sensor LED facing outward (detects reflected light)

**Erratic readings (wild fluctuations)**
- Loose jumper wire connection
- Re-seat all 3 connections
- Check for broken wire
- Move cables away from power wires (reduce EMI)

### 14.2 Beat Detection Issues

**No beats detected (ADC working, no "Beat detected" messages)**
- Enable debug output (Level 1) to see threshold values
- Check signal range: Should be > 50 ADC units when finger applied
- If range < 50: Adjust finger pressure, try different finger
- If range > 50 but no beats: Lower `THRESHOLD_FRACTION` to 0.5

**False beats (BPM > 150 at rest)**
- Threshold too low
- Increase `THRESHOLD_FRACTION` to 0.7
- Check for movement (hold finger very still)
- Increase `MIN_SIGNAL_RANGE` to 80

**Missed beats (gaps > 2 seconds)**
- Threshold too high for weak signals
- Decrease `THRESHOLD_FRACTION` to 0.5
- Improve sensor contact (more pressure)
- Check sensor not covered by external light (cover with hand)

**BPM incorrect (±10+ BPM difference)**
- Poor sensor contact
- Movement during measurement
- Compare to multiple phone apps (some apps inaccurate)
- Try different finger
- Ensure sensor LED fully covered

### 14.3 Disconnection Issues

**"Sensor disconnected" immediately after startup**
- No finger on sensor (expected behavior)
- Sensor not actually connected (check wiring)

**"Sensor disconnected" while finger applied**
- Sensor signal too weak (range < 50)
- Increase finger pressure
- Try different finger
- Check sensor power (LED should be bright)

**"Sensor reconnected" flapping (rapid connect/disconnect)**
- Borderline signal quality
- Increase `MIN_SIGNAL_RANGE` to 80 (more stable threshold)
- Improve sensor contact

### 14.4 Performance Issues

**Loop running slow (sample rate < 50 Hz)**
- Too much serial output (disable Level 2 debug)
- WiFi congestion (check router)
- Reduce serial baud rate (unlikely with 115200)

**Memory issues (crashes after long runtime)**
- Check for memory leaks with serial output
- Monitor free heap: `Serial.println(ESP.getFreeHeap())`
- Should be stable (no fixed-size data structures should leak)

---

## 15. Success Metrics

### 15.1 Phase 2 Firmware Complete

**All criteria MUST be met:**

1. ✅ Firmware compiles without errors
2. ✅ Uploads to ESP32 successfully
3. ✅ WiFi connection stable (Phase 1 functionality maintained)
4. ✅ ADC sampling at 50 Hz
5. ✅ Moving average filter working
6. ✅ Baseline tracking adapts to signal
7. ✅ Beats detected within 3 seconds of finger application
8. ✅ BPM accuracy ±5 BPM vs smartphone app
9. ✅ OSC messages contain real IBI values
10. ✅ Python receiver validates all messages
11. ✅ Sensor disconnection detected within 1 second
12. ✅ Auto-reconnection working
13. ✅ 30-minute stability test passes
14. ✅ Multi-unit test passes (2+ ESP32s simultaneously)
15. ✅ Code organized and commented

### 15.2 Ready for Phase 3

Phase 2 complete, proceed to Phase 3 when:

- ✅ Single sensor heartbeat detection reliable
- ✅ Signal processing algorithm tuned
- ✅ Disconnection handling robust
- ✅ BPM accuracy validated
- ✅ OSC messaging proven with real data
- ✅ Code structure ready to add 3 more sensors

**Phase 3 Preview:** Will add 3 more sensors (GPIO 33, 34, 35), independent state tracking per sensor, concurrent beat detection on all 4 channels, and multi-sensor OSC transmission.

---

*End of Technical Reference Document*

**Document Version:** 1.0  
**Last Updated:** 2025-11-09  
**Status:** Ready for implementation by coding agent  
**Dependencies:** Phase 1 firmware (WiFi + OSC), PulseSensor hardware  
**Previous:** `phase1-firmware-trd.md` (WiFi + OSC messaging)  
**Next:** `phase3-firmware-trd.md` (4-sensor expansion)
