# Heartbeat Firmware - Phase 3 Firmware Implementation TRD
## Multi-Sensor with Beat Detection

**Version:** 1.0
**Date:** 2025-11-09
**Purpose:** Expand from single sensor to 4 sensors with real beat detection algorithm
**Audience:** Coding agent implementing ESP32 firmware
**Hardware:** ESP32-WROOM-32 + 4 optical pulse sensors on GPIO 32-35
**Framework:** Arduino (via PlatformIO CLI)
**Toolchain:** PlatformIO CLI

**⚠️ CRITICAL: PREREQUISITES**
```
Step 1: Complete Phase 1 (WiFi + OSC messaging with test values)
Step 2: Validate Phase 1 testing infrastructure works
Step 3: Implement this Phase 3 firmware (multi-sensor + beat detection)
Step 4: Test with multiple people/fingers simultaneously
```

Phase 1 WiFi and OSC infrastructure MUST be validated before expanding to sensors.

**Estimated Implementation Time:** 4-6 hours (code) + 2-3 hours (testing)

---

## 0. Prerequisites

### 0.1 Phase 1 Completion

**MUST be completed before Phase 3:**
- ✅ WiFi connection stable and tested
- ✅ OSC messaging validated with Python receiver
- ✅ LED feedback working
- ✅ PlatformIO toolchain configured
- ✅ Test messages sent at 1 Hz successfully

**Verify Phase 1 working:**
```bash
# Start receiver
python3 osc_receiver.py --port 8000

# Upload Phase 1 firmware
cd /home/sderle/fw-phase-3/firmware/heartbeat_phase1
pio run --target upload && pio device monitor

# Expected: Messages received, LED solid after WiFi connect
```

### 0.2 Hardware Setup

**Pulse Sensors:**
- Type: Optical pulse sensors (12-bit ADC, 0-4095 range)
- Quantity: 4 sensors
- Connections:
  - Sensor 0: GPIO 32 (ADC1_CH4)
  - Sensor 1: GPIO 33 (ADC1_CH5)
  - Sensor 2: GPIO 34 (ADC1_CH6, input-only)
  - Sensor 3: GPIO 35 (ADC1_CH7, input-only)
- Power: 3.3V from ESP32 VCC
- Ground: Common ground with ESP32

**Important GPIO Notes:**
- GPIO 34-35 are input-only (no pullup/pulldown available)
- All sensors use ADC1 to avoid WiFi conflicts (ADC2 shares pins with WiFi)
- 12-bit resolution: 0-4095 ADC values

**Physical Setup:**
- Mount sensors accessible for fingers/wrists
- Label each sensor with ID (0-3)
- Ensure stable physical mounting (vibration affects readings)
- Shield from ambient light if possible

### 0.3 Testing Requirements

**Single-Person Testing:**
- One finger on one sensor at a time
- Validates per-sensor independence
- Confirms no false positives on idle sensors

**Multi-Person Testing:**
- 2-4 people, each on different sensor
- Validates crosstalk prevention
- Confirms independent state tracking
- Tests concurrent beat detection

---

## 1. Objective

Expand Phase 1 firmware to support 4 pulse sensors with real beat detection algorithm. Maintain WiFi/OSC infrastructure while adding analog sampling, signal processing, and adaptive threshold beat detection.

**Deliverables:**
- Single `main.cpp` implementing multi-sensor firmware
- 4 independent sensor channels with per-sensor state
- 50Hz sampling rate per sensor
- Moving average filter (5-sample window)
- Adaptive baseline tracking (exponential decay)
- Threshold-based beat detection with refractory period
- Real IBI values (no more test messages)
- LED indicates beats from ANY sensor
- Debug levels for production/testing/verbose

**Success Criteria:**
- All 4 sensors detect beats independently
- No crosstalk between sensors
- BPM accuracy ±5 BPM vs smartphone app
- Single-person test: Only active sensor sends messages
- Multi-person test: All active sensors send messages
- Latency: Beat to OSC message <25ms
- 30+ minute stability test passes

---

## 2. Architecture Overview

### 2.1 Execution Model

**Polling architecture with precise timing:**
- `setup()`: Initialize hardware, WiFi, sensors, UDP
- `loop()`: 
  - Check if 20ms elapsed (50Hz per sensor)
  - Sample all 4 sensors
  - Process each sensor independently
  - Send OSC on beat detection
  - Update LED
  - Monitor WiFi status

**Timing:**
- Target: 20ms per sampling cycle (50Hz)
- Use `millis()` for non-blocking timing
- No interrupts or RTOS tasks (keep Phase 1 simplicity)

### 2.2 State Machine (Per Sensor)

```
INIT → FILLING_BUFFER → TRACKING → BEAT_DETECTED → TRACKING
                              ↓                         ↑
                         DISCONNECTED ←───────────────┘
```

**States:**
- `INIT`: First sample, initialize buffers
- `FILLING_BUFFER`: First 5 samples (until moving average valid)
- `TRACKING`: Normal operation, waiting for beat
- `BEAT_DETECTED`: Beat detected, send OSC, enter refractory
- `DISCONNECTED`: Flat signal or insufficient range

### 2.3 Data Flow

```
Analog Sensor (GPIO 32-35)
    ↓
analogRead() - Raw ADC value (0-4095)
    ↓
Moving Average Filter - 5-sample circular buffer
    ↓
Smoothed Value - Filtered signal
    ↓
Baseline Tracking - Adaptive min/max with decay
    ↓
Threshold Calculation - 60% of signal range
    ↓
Beat Detection - Rising edge + refractory check
    ↓
IBI Calculation - Time since last beat
    ↓
OSC Message - /heartbeat/N <ibi_ms>
    ↓
WiFiUDP → Server
```

---

## 3. Required Libraries

### 3.1 Arduino Libraries

**Same as Phase 1:**
- `WiFi.h` - ESP32 WiFi (built-in)
- `WiFiUdp.h` - UDP sockets (built-in)
- `OSC` by Adrian Freed - OSC message formatting

**platformio.ini:**
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

No new libraries needed - building on Phase 1 infrastructure.

---

## 4. Configuration Constants

### 4.1 Network Configuration

**Unchanged from Phase 1:**
```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS
const uint16_t SERVER_PORT = 8000;
```

### 4.2 Hardware Configuration

```cpp
// Pulse sensors on ADC1 channels
const int SENSOR_PINS[4] = {32, 33, 34, 35};
const int NUM_SENSORS = 4;
const int STATUS_LED_PIN = 2;  // Built-in LED
const int ADC_RESOLUTION = 12;  // 12-bit: 0-4095
```

**Requirements:**
- MUST use GPIO 32-35 (ADC1 channels, avoid WiFi conflicts)
- MUST configure ADC to 12-bit resolution in setup()
- GPIO 34-35 input-only (no pinMode OUTPUT allowed)

### 4.3 Signal Processing Parameters

```cpp
// Sampling configuration
const int SAMPLE_RATE_HZ = 50;                  // Per sensor
const int SAMPLE_INTERVAL_MS = 20;              // 1000 / 50

// Moving average filter
const int MOVING_AVG_SAMPLES = 5;               // 100ms window

// Baseline tracking (exponential decay)
const float BASELINE_DECAY_RATE = 0.1;          // 10% decay toward center
const int BASELINE_DECAY_INTERVAL = 150;        // Apply every 150 samples (3 sec)
```

**Requirements:**
- `SAMPLE_INTERVAL_MS`: MUST match 1000 / SAMPLE_RATE_HZ
- `MOVING_AVG_SAMPLES`: MUST be small enough for real-time (5 samples = 100ms lag)
- `BASELINE_DECAY_INTERVAL`: MUST be sample count, not time (150 samples = 3 sec at 50Hz)

### 4.4 Beat Detection Parameters

```cpp
// Threshold calculation
const float THRESHOLD_FRACTION = 0.6;           // 60% of signal range
const int MIN_SIGNAL_RANGE = 50;                // ADC units, below = disconnected

// Beat detection
const unsigned long REFRACTORY_PERIOD_MS = 300; // Max 200 BPM
const int FLAT_SIGNAL_THRESHOLD = 5;            // ADC variance for "flat"
const unsigned long DISCONNECT_TIMEOUT_MS = 1000; // 50 samples flat = disconnected
```

**Requirements:**
- `THRESHOLD_FRACTION`: 0.5-0.7 typical, tunable per user
- `MIN_SIGNAL_RANGE`: Prevents false beats on noise
- `REFRACTORY_PERIOD_MS`: Enforces max BPM, prevents double-triggers
- `FLAT_SIGNAL_THRESHOLD`: Variance check for disconnection

**Rate Limiting:**
- Refractory period limits max message rate: 300ms = max 200 msg/min per sensor
- 4 sensors × 200 msg/min = 800 messages/min total system max

### 4.5 Debug Levels

```cpp
#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose

// Level 0: Production (WiFi status only)
// Level 1: Testing (beat timestamps + BPM)
// Level 2: Verbose (raw ADC values every 100ms, baseline tracking)
```

**Requirements:**
- Level 0: Minimal output for festival deployment
- Level 1: Beat detection events for validation
- Level 2: Full signal diagnostics for algorithm tuning

---

## 5. Data Structures

### 5.1 Sensor State

**Purpose:** Track per-sensor signal processing and beat detection state

```cpp
struct SensorState {
  // Hardware
  int pin;                          // GPIO pin number
  
  // Moving average filter
  int rawSamples[MOVING_AVG_SAMPLES];  // Circular buffer
  int sampleIndex;                  // Current position in buffer
  int smoothedValue;                // Filter output
  
  // Baseline tracking (exponential decay)
  int minValue;                     // Decays upward toward center
  int maxValue;                     // Decays downward toward center
  int samplesSinceDecay;            // Counter for decay interval
  
  // Beat detection
  bool aboveThreshold;              // Currently above threshold?
  unsigned long lastBeatTime;       // millis() of last beat
  unsigned long lastIBI;            // Inter-beat interval (ms)
  bool firstBeatDetected;           // Have we sent first beat?
  
  // Disconnection detection
  bool isConnected;                 // Sensor shows valid signal?
  int lastRawValue;                 // For flat signal detection
  int flatSampleCount;              // Consecutive flat samples
};

SensorState sensors[4];
```

**Requirements:**

**R1: Initialization**
- MUST initialize all fields to zero/false in setup()
- MUST set `pin` to corresponding GPIO from SENSOR_PINS array
- MUST pre-fill `rawSamples` buffer with first ADC reading

**R2: Moving Average Buffer**
- Circular buffer: `sampleIndex` wraps at `MOVING_AVG_SAMPLES`
- On new sample: `rawSamples[sampleIndex] = newValue; sampleIndex = (sampleIndex + 1) % MOVING_AVG_SAMPLES;`
- Calculate mean: `sum(rawSamples) / MOVING_AVG_SAMPLES`

**R3: Baseline Tracking**
- Instant expansion: If `smoothedValue < minValue`, immediately update `minValue = smoothedValue`
- Instant expansion: If `smoothedValue > maxValue`, immediately update `maxValue = smoothedValue`
- Decay every 150 samples:
  - `minValue += (smoothedValue - minValue) * BASELINE_DECAY_RATE`
  - `maxValue -= (maxValue - smoothedValue) * BASELINE_DECAY_RATE`

**R4: Beat Detection State**
- `aboveThreshold`: Set true on rising edge, false on falling edge
- `lastBeatTime`: Updated with `millis()` when beat detected
- `firstBeatDetected`: False initially, set true after first beat (no IBI sent for first beat)

**R5: Disconnection State**
- `isConnected`: True by default, set false if flat signal or range too small
- `flatSampleCount`: Increment if variance < threshold, reset on change
- Mark disconnected if `flatSampleCount >= 50` (1 second at 50Hz)

### 5.2 System State

**Purpose:** Track global system state

```cpp
struct SystemState {
  bool wifiConnected;               // WiFi connection status
  unsigned long lastWiFiCheckTime;  // millis() of last WiFi check
  unsigned long loopCounter;        // For debug output throttling
  bool beatDetectedThisLoop;        // For LED pulse feedback
};

SystemState system = {false, 0, 0, false};
```

**Requirements:**
- `wifiConnected`: Updated by `checkWiFi()` every 5 seconds
- `loopCounter`: Incremented each loop, used for debug throttling
- `beatDetectedThisLoop`: Set true when ANY sensor detects beat, cleared after LED update

### 5.3 Global Objects

```cpp
WiFiUDP udp;          // UDP socket for OSC (from Phase 1)
SystemState system;   // System state
SensorState sensors[4];  // Array of 4 sensor states
```

---

## 6. Function Specifications

### 6.1 Sensor Initialization

**Function:** `initializeSensor()`

**Signature:**
```cpp
void initializeSensor(int sensorIndex);
```

**Purpose:** Initialize sensor state on startup

**Parameters:**
- `sensorIndex`: Index 0-3 into sensors array

**Requirements:**

**R6: Initial Reading**
```cpp
int firstReading = analogRead(sensors[sensorIndex].pin);
```
- MUST read ADC immediately after GPIO configuration
- Provides valid starting value for buffers

**R7: Buffer Pre-fill**
```cpp
for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
  sensors[sensorIndex].rawSamples[i] = firstReading;
}
```
- MUST fill entire moving average buffer with first reading
- Prevents invalid calculations during buffer fill
- Allows immediate filtering

**R8: State Initialization**
```cpp
sensors[sensorIndex].sampleIndex = 0;
sensors[sensorIndex].smoothedValue = firstReading;
sensors[sensorIndex].minValue = firstReading;
sensors[sensorIndex].maxValue = firstReading;
sensors[sensorIndex].aboveThreshold = false;
sensors[sensorIndex].lastBeatTime = 0;
sensors[sensorIndex].lastIBI = 0;
sensors[sensorIndex].firstBeatDetected = false;
sensors[sensorIndex].isConnected = true;  // Assume connected initially
sensors[sensorIndex].lastRawValue = firstReading;
sensors[sensorIndex].flatSampleCount = 0;
sensors[sensorIndex].samplesSinceDecay = 0;
```

**Call Location:** In `setup()` after GPIO configuration, before main loop

---

### 6.2 Signal Sampling and Filtering

**Function:** `readAndFilterSensor()`

**Signature:**
```cpp
void readAndFilterSensor(int sensorIndex);
```

**Purpose:** Read ADC, update moving average, store smoothed value

**Parameters:**
- `sensorIndex`: Index 0-3 into sensors array

**Requirements:**

**R9: ADC Read**
```cpp
int rawValue = analogRead(sensors[sensorIndex].pin);
```
- Read current ADC value from sensor pin
- 12-bit resolution: 0-4095

**R10: Moving Average Update**
```cpp
// Store in circular buffer
sensors[sensorIndex].rawSamples[sensors[sensorIndex].sampleIndex] = rawValue;
sensors[sensorIndex].sampleIndex = (sensors[sensorIndex].sampleIndex + 1) % MOVING_AVG_SAMPLES;

// Calculate average
int sum = 0;
for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
  sum += sensors[sensorIndex].rawSamples[i];
}
sensors[sensorIndex].smoothedValue = sum / MOVING_AVG_SAMPLES;
```
- MUST maintain circular buffer correctly
- MUST calculate mean of all samples
- Smoothed value used for all downstream processing

**R11: Disconnection Check**
```cpp
// Check for flat signal
if (abs(rawValue - sensors[sensorIndex].lastRawValue) < FLAT_SIGNAL_THRESHOLD) {
  sensors[sensorIndex].flatSampleCount++;
} else {
  sensors[sensorIndex].flatSampleCount = 0;
}

// Mark disconnected after 1 second flat
if (sensors[sensorIndex].flatSampleCount >= 50) {  // 50 samples at 50Hz = 1 sec
  sensors[sensorIndex].isConnected = false;
}

sensors[sensorIndex].lastRawValue = rawValue;
```
- Detect lack of signal variation
- Reset counter on any significant change
- Require sustained flatness (1 second) before marking disconnected

---

### 6.3 Baseline Tracking

**Function:** `updateBaseline()`

**Signature:**
```cpp
void updateBaseline(int sensorIndex);
```

**Purpose:** Adaptive min/max tracking with exponential decay

**Parameters:**
- `sensorIndex`: Index 0-3 into sensors array

**Requirements:**

**R12: Instant Expansion**
```cpp
int smoothed = sensors[sensorIndex].smoothedValue;

// Expand range immediately if signal exceeds current bounds
if (smoothed < sensors[sensorIndex].minValue) {
  sensors[sensorIndex].minValue = smoothed;
}
if (smoothed > sensors[sensorIndex].maxValue) {
  sensors[sensorIndex].maxValue = smoothed;
}
```
- MUST respond instantly to signal increases
- Ensures threshold doesn't clip valid beats

**R13: Exponential Decay**
```cpp
sensors[sensorIndex].samplesSinceDecay++;

if (sensors[sensorIndex].samplesSinceDecay >= BASELINE_DECAY_INTERVAL) {
  // Decay min upward toward center
  sensors[sensorIndex].minValue += 
    (smoothed - sensors[sensorIndex].minValue) * BASELINE_DECAY_RATE;
  
  // Decay max downward toward center
  sensors[sensorIndex].maxValue -= 
    (sensors[sensorIndex].maxValue - smoothed) * BASELINE_DECAY_RATE;
  
  sensors[sensorIndex].samplesSinceDecay = 0;
}
```
- MUST apply decay every 150 samples (3 seconds at 50Hz)
- Decay rate: 10% toward current signal per interval
- Prevents baseline from drifting too far from signal

**R14: Range Check**
```cpp
int range = sensors[sensorIndex].maxValue - sensors[sensorIndex].minValue;
if (range < MIN_SIGNAL_RANGE) {
  sensors[sensorIndex].isConnected = false;
}
```
- Mark disconnected if range too small (likely noise, not pulse)
- Prevents false beats on flat signals

---

### 6.4 Beat Detection

**Function:** `detectBeat()`

**Signature:**
```cpp
void detectBeat(int sensorIndex);
```

**Purpose:** Rising edge threshold crossing with refractory period

**Parameters:**
- `sensorIndex`: Index 0-3 into sensors array

**Requirements:**

**R15: Skip If Disconnected**
```cpp
if (!sensors[sensorIndex].isConnected) {
  return;  // Don't attempt detection on disconnected sensor
}
```

**R16: Threshold Calculation**
```cpp
int threshold = sensors[sensorIndex].minValue + 
  (sensors[sensorIndex].maxValue - sensors[sensorIndex].minValue) * THRESHOLD_FRACTION;
```
- Calculate as fraction of signal range above baseline
- Default: 60% of range

**R17: Rising Edge Detection**
```cpp
bool currentlyAbove = (sensors[sensorIndex].smoothedValue >= threshold);

if (currentlyAbove && !sensors[sensorIndex].aboveThreshold) {
  // Rising edge detected
  // ... check refractory, calculate IBI ...
}

// Update state for next iteration
sensors[sensorIndex].aboveThreshold = currentlyAbove;
```
- Trigger only on transition from below to above
- Prevents double-triggering on single beat
- Falling edge (above→below) just updates state, no action

**R18: Refractory Period Check**
```cpp
unsigned long now = millis();
unsigned long timeSinceLastBeat = now - sensors[sensorIndex].lastBeatTime;

if (timeSinceLastBeat < REFRACTORY_PERIOD_MS) {
  return;  // Too soon after last beat, ignore
}
```
- Enforces minimum time between beats (300ms = max 200 BPM)
- Prevents noise from triggering false beats
- Also rate-limits OSC messages

**R19: IBI Calculation and OSC Transmission**
```cpp
// Calculate inter-beat interval
unsigned long ibi = now - sensors[sensorIndex].lastBeatTime;

if (sensors[sensorIndex].firstBeatDetected) {
  // Send OSC message with real IBI
  sendHeartbeatOSC(sensorIndex, (int)ibi);
  
  // Set flag for LED feedback
  system.beatDetectedThisLoop = true;
  
  #if DEBUG_LEVEL >= 1
    Serial.print("[");
    Serial.print(sensorIndex);
    Serial.print("] Beat at ");
    Serial.print(now);
    Serial.print("ms, IBI=");
    Serial.print(ibi);
    Serial.println("ms");
  #endif
} else {
  // First beat: just record time, don't send (no reference point)
  sensors[sensorIndex].firstBeatDetected = true;
  
  #if DEBUG_LEVEL >= 1
    Serial.print("[");
    Serial.print(sensorIndex);
    Serial.print("] First beat at ");
    Serial.print(now);
    Serial.println("ms (no message sent)");
  #endif
}

// Update beat tracking
sensors[sensorIndex].lastBeatTime = now;
sensors[sensorIndex].lastIBI = ibi;
```

**Requirements:**
- First beat after startup or reconnection: Record time only, no OSC sent
- Subsequent beats: Calculate IBI, send OSC message
- IBI is time since last beat on THIS sensor (independent per sensor)
- Set `beatDetectedThisLoop` for LED feedback

**Reconnection Behavior:**
After disconnection, `firstBeatDetected` remains true, so next beat will send OSC with potentially large IBI (accurate time since last beat before disconnect). This is intentional - provides true inter-beat interval.

---

### 6.5 OSC Message Transmission

**Function:** `sendHeartbeatOSC()`

**Signature:**
```cpp
void sendHeartbeatOSC(int sensorIndex, int ibi_ms);
```

**Purpose:** Construct and send OSC heartbeat message

**Parameters:**
- `sensorIndex`: Sensor ID 0-3
- `ibi_ms`: Inter-beat interval in milliseconds

**Requirements:**

**R20: Address Pattern**
```cpp
char oscAddress[20];
snprintf(oscAddress, sizeof(oscAddress), "/heartbeat/%d", sensorIndex);
```
- Format: `/heartbeat/N` where N = 0-3
- Buffer size 20 bytes sufficient

**R21: OSC Message Construction**
```cpp
OSCMessage msg(oscAddress);
msg.add((int32_t)ibi_ms);
```
- Create message with address pattern
- Add single int32 argument (IBI value)
- MUST cast to int32_t for correct OSC type

**R22: UDP Transmission**
```cpp
udp.beginPacket(SERVER_IP, SERVER_PORT);
msg.send(udp);
udp.endPacket();
msg.empty();
```
- MUST follow sequence: beginPacket → send → endPacket → empty
- `msg.empty()` clears message for reuse
- Fire-and-forget (no acknowledgment expected)

**R23: Debug Output**
```cpp
#if DEBUG_LEVEL >= 2
  Serial.print("Sent OSC: ");
  Serial.print(oscAddress);
  Serial.print(" ");
  Serial.println(ibi_ms);
#endif
```
- Level 2 debug: Confirm OSC transmission
- Production (Level 0): No output

**Same as Phase 1, but now with real sensor IBI values instead of test values**

---

### 6.6 LED Status Indication

**Function:** `updateLED()`

**Signature:**
```cpp
void updateLED();
```

**Purpose:** Visual feedback for system state and beat detection

**Requirements:**

**R24: LED States**
- **WiFi connecting:** Rapid blink 10Hz (50ms on/off)
- **WiFi connected, no beats:** Solid ON
- **Beat detected:** 50ms pulse (briefly brighter or just visible pulse)

**R25: Implementation**
```cpp
static unsigned long ledPulseTime = 0;
const int LED_PULSE_DURATION = 50;  // 50ms for visibility

if (!system.wifiConnected) {
  // Rapid blink while connecting
  digitalWrite(STATUS_LED_PIN, (millis() / 50) % 2);
} else if (system.beatDetectedThisLoop) {
  // Beat detected: turn on and record time
  digitalWrite(STATUS_LED_PIN, HIGH);
  ledPulseTime = millis();
} else if (millis() - ledPulseTime < LED_PULSE_DURATION) {
  // Keep on during pulse duration
  digitalWrite(STATUS_LED_PIN, HIGH);
} else {
  // Solid on when connected and idle
  digitalWrite(STATUS_LED_PIN, HIGH);
}

// Clear flag for next iteration
system.beatDetectedThisLoop = false;
```

**Requirements:**
- LED blinks on beat from ANY sensor (not just sensor 0)
- Pulse duration 50ms (clearly visible)
- Non-blocking (no delays)
- Static variable `ledPulseTime` tracks pulse timing

**Change from Phase 1:** Now responds to real beat detection instead of message sends

---

### 6.7 WiFi Status Monitoring

**Function:** `checkWiFi()`

**Same as Phase 1 - no changes needed**

**Requirements:**
- Check WiFi.status() every 5 seconds
- If disconnected: Call WiFi.reconnect(), set system.wifiConnected = false
- If connected: Set system.wifiConnected = true
- Non-blocking operation

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

# Monitor
pio device monitor

# Combined
pio run --target upload && pio device monitor
```

### 9.2 Pre-Upload Configuration

**MUST configure before upload:**
1. WiFi credentials (WIFI_SSID, WIFI_PASSWORD)
2. Server IP address (SERVER_IP)
3. Debug level (DEBUG_LEVEL 0/1/2)

**Sensor IDs:**
- Phase 3 uses all 4 sensors simultaneously
- No need to change SENSOR_ID (removed from Phase 3)
- Each sensor identified by array index 0-3

---

## 10. Validation & Testing

### 10.1 Single-Sensor Smoke Test

**Purpose:** Validate one sensor independently

**Procedure:**
1. Upload firmware with DEBUG_LEVEL = 2
2. Place one finger on Sensor 0 (GPIO 32)
3. Monitor serial output

**Expected Output:**
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

[0]=2456 [1]=2391 [2]=0 [3]=2678
[0]=2467 [1]=2401 [2]=0 [3]=2689
[0] First beat at 3421ms (no message sent)
[0]=2489 [1]=2423 [2]=0 [3]=2701
[0] Beat at 4287ms, IBI=866ms
[0]=2512 [1]=2445 [2]=0 [3]=2715
[0] Beat at 5156ms, IBI=869ms
```

**Validation:**
- ✅ Sensor 0 shows pulsing values (2400-2800 typical range)
- ✅ Sensors 1-3 show steady baseline (no finger)
- ✅ First beat detected, no message sent
- ✅ Subsequent beats send OSC with IBI
- ✅ IBI values reasonable (600-1200ms = 50-100 BPM)

### 10.2 Single-Person Multi-Sensor Test

**Purpose:** Validate sensor independence (one finger at a time)

**Procedure:**
1. DEBUG_LEVEL = 1 (testing)
2. Place finger on Sensor 0 for 10 seconds
3. Move to Sensor 1 for 10 seconds
4. Move to Sensor 2 for 10 seconds
5. Move to Sensor 3 for 10 seconds

**Expected Behavior:**
- Only active sensor sends messages
- Inactive sensors show no beats (no false positives)
- LED blinks on beats from any sensor
- Python receiver shows messages from one sensor at a time

**Validation:**
- ✅ No crosstalk (inactive sensors silent)
- ✅ Each sensor detects beats correctly
- ✅ BPM consistent across all sensors (±5 BPM)

### 10.3 Multi-Person Test

**Purpose:** Validate concurrent operation with 2-4 people

**Procedure:**
1. DEBUG_LEVEL = 1
2. 2-4 people each place finger on different sensor
3. Run for 5 minutes
4. Monitor Python receiver

**Expected Output (Receiver):**
```
[/heartbeat/0] IBI: 856ms, BPM: 70.1
[/heartbeat/2] IBI: 742ms, BPM: 80.9
[/heartbeat/1] IBI: 923ms, BPM: 65.0
[/heartbeat/0] IBI: 861ms, BPM: 69.7
[/heartbeat/3] IBI: 678ms, BPM: 88.5
[/heartbeat/2] IBI: 739ms, BPM: 81.2
```

**Validation:**
- ✅ All active sensors send messages
- ✅ Messages interleaved (independent timing)
- ✅ BPM values reasonable for all people
- ✅ No missed beats (no gaps > 2 seconds)
- ✅ LED blinks on beats from any sensor

### 10.4 Disconnection/Reconnection Test

**Purpose:** Validate disconnection detection

**Procedure:**
1. Finger on Sensor 0, wait for beats
2. Remove finger, wait 2 seconds
3. Reapply finger

**Expected Behavior:**
```
[0] Beat at 12847ms, IBI=856ms
[0] Beat at 13703ms, IBI=856ms
[0] Sensor disconnected
(no messages for 2 seconds)
[0] Sensor reconnected
[0] Beat at 16421ms, IBI=2718ms  // Large IBI = time since last beat
[0] Beat at 17289ms, IBI=868ms
```

**Validation:**
- ✅ Messages stop within 1 second of finger removal
- ✅ Messages resume within 3 seconds of finger reapplication
- ✅ First IBI after reconnect is large (accurate)
- ✅ Subsequent IBIs normal

### 10.5 Extended Duration Test

**Purpose:** Validate stability and memory safety

**Procedure:**
1. 2-4 people on sensors
2. Run for 30+ minutes
3. Monitor serial and receiver

**Validation:**
- ✅ No crashes or resets
- ✅ No WiFi disconnections (or auto-reconnects if drops)
- ✅ Consistent beat detection throughout
- ✅ No memory issues (fixed allocation, no leaks)
- ✅ LED continues to respond

### 10.6 BPM Accuracy Test

**Purpose:** Validate against smartphone reference

**Procedure:**
1. Install heart rate app on smartphone (e.g., "Instant Heart Rate")
2. Simultaneously measure:
   - Smartphone finger sensor
   - ESP32 sensor (same finger on different hand)
3. Compare BPM over 1 minute

**Validation:**
- ✅ BPM within ±5 BPM of smartphone
- ✅ Steady state BPM stable (not jumping wildly)

---

## 11. Acceptance Criteria

### 11.1 Compilation & Upload

**MUST:**
- ✅ Compile without errors
- ✅ Upload successfully
- ✅ Binary size < 500KB
- ✅ RAM usage < 10KB

### 11.2 Single-Sensor Operation

**MUST:**
- ✅ Detect beats within 3 seconds of finger application
- ✅ BPM accuracy ±5 BPM vs smartphone
- ✅ First beat: no message sent (correct behavior)
- ✅ Subsequent beats: IBI messages sent
- ✅ Disconnection detected within 1 second
- ✅ Reconnection detected within 3 seconds

### 11.3 Multi-Sensor Operation

**MUST:**
- ✅ All 4 sensors operate simultaneously
- ✅ No crosstalk (inactive sensors silent)
- ✅ Independent beat detection per sensor
- ✅ LED responds to beats from ANY sensor
- ✅ 2-4 person test successful

### 11.4 Reliability

**MUST:**
- ✅ 30+ minute stability test passes
- ✅ No crashes or watchdog resets
- ✅ WiFi resilience (auto-reconnect if drops)
- ✅ Consistent performance (no degradation)

### 11.5 Protocol Validation

**MUST:**
- ✅ OSC messages format correct: `/heartbeat/[0-3] <int32>`
- ✅ All messages received by Python receiver
- ✅ 0 invalid messages
- ✅ Latency <25ms (beat to network)

---

## 12. Known Limitations (Phase 3)

**Intentional Simplifications:**
- No waveform transmission (only IBI)
- No HRV analysis
- Fixed threshold fraction (not adaptive per user)
- No calibration UI
- No SD card logging
- No NTP time sync
- Single server destination
- No beat prediction

**Algorithm Limitations:**
- Moving average lag: 50ms
- Baseline adaptation: 3 second time constant
- Threshold may not be optimal for all users (tunable via constant)
- Sensitive to ambient light and movement

**Hardware Limitations:**
- 12-bit ADC (adequate but not clinical)
- GPIO 34-35 input-only (no pullup/pulldown)
- WiFi range ~30m from AP

**These are acceptable for festival installation. Future phases could address if needed.**

---

## 13. Troubleshooting

### 13.1 No Beats Detected

**Symptom:** Sensor connected, but no beats detected

**Debug Steps:**
1. Set DEBUG_LEVEL = 2
2. Check raw ADC values:
   - Should oscillate (e.g., 2400-2800)
   - If flat (constant value): Sensor disconnected or poor contact
3. Check baseline min/max:
   - Range should be > 50 ADC units
   - If < 50: Signal too weak
4. Check smoothed value crosses threshold

**Solutions:**
- Improve finger contact (press firmer)
- Shield from ambient light
- Adjust THRESHOLD_FRACTION (try 0.5 or 0.7)
- Increase MIN_SIGNAL_RANGE if noisy environment

### 13.2 False Beats / Double Triggers

**Symptom:** Too many beats, unrealistic BPM (>150)

**Debug Steps:**
1. Check if refractory period enforced (should see "ignored" if DEBUG_LEVEL 2)
2. Observe signal: High noise or vibration?

**Solutions:**
- Increase REFRACTORY_PERIOD_MS to 400ms
- Increase THRESHOLD_FRACTION to 0.7 (higher threshold)
- Stabilize physical mounting (reduce vibration)

### 13.3 Missed Beats

**Symptom:** Gaps > 2 seconds between beats

**Debug Steps:**
1. Check signal amplitude (min/max range)
2. Check if threshold too high

**Solutions:**
- Decrease THRESHOLD_FRACTION to 0.5
- Improve sensor contact
- Warm up hands (cold reduces signal)

### 13.4 Crosstalk Between Sensors

**Symptom:** Inactive sensors show beats

**Debug Steps:**
1. Verify each sensor has independent SensorState struct
2. Check sensorIndex passed correctly to all functions
3. Confirm no global variables shared between sensors

**Cause:** Likely bug in per-sensor state management

### 13.5 WiFi Issues

**Same as Phase 1 troubleshooting:**
- Connection timeout: Check SSID/password, 2.4GHz network
- Messages not received: Check SERVER_IP, firewall
- Disconnections: Check WiFi range, interference

---

## 14. Success Metrics

### 14.1 Phase 3 Complete

**All criteria MUST be met:**

1. ✅ Firmware compiles and uploads without errors
2. ✅ All 4 sensors initialized correctly
3. ✅ Single-sensor test: Beats detected, BPM accurate
4. ✅ Single-person multi-sensor test: No crosstalk
5. ✅ Multi-person test: All sensors operate independently
6. ✅ BPM accuracy ±5 BPM vs smartphone
7. ✅ Disconnection detection working (1 sec timeout)
8. ✅ Reconnection automatic (3 sec response)
9. ✅ LED feedback for beats from any sensor
10. ✅ 30-minute stability test passes
11. ✅ Python receiver validates all messages
12. ✅ Debug levels 0/1/2 all functional

### 14.2 Ready for Festival Deployment

Phase 3 complete, system ready for installation when:

- ✅ Multi-sensor operation validated
- ✅ Beat detection reliable
- ✅ No crosstalk confirmed
- ✅ Extended duration testing passed
- ✅ WiFi resilience tested
- ✅ LED feedback clear
- ✅ Code clean and commented
- ✅ DEBUG_LEVEL 0 tested (production mode)

**Next Steps:**
- Integrate with audio synthesis (server-side)
- Test full system with Pure Data patches
- Festival installation and validation

---

*End of Technical Requirements Document*

**Document Version:** 1.0  
**Last Updated:** 2025-11-09  
**Status:** Ready for implementation  
**Dependencies:** Phase 1 (WiFi + OSC infrastructure)  
**Estimated Time:** 4-6 hours implementation + 2-3 hours testing  

---

## Appendix: Sample Serial Output

### Level 0 (Production)
```
=== Heartbeat Installation - Phase 3 ===
Multi-Sensor Beat Detection
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.1.42
Setup complete. Starting multi-sensor detection...
```
(No further output during operation)

### Level 1 (Testing)
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

[0] First beat at 3421ms (no message sent)
[1] First beat at 3856ms (no message sent)
[0] Beat at 4287ms, IBI=866ms
[2] First beat at 4501ms (no message sent)
[0] Beat at 5156ms, IBI=869ms
[1] Beat at 5234ms, IBI=1378ms
[2] Beat at 5389ms, IBI=888ms
[3] First beat at 5672ms (no message sent)
[0] Beat at 6021ms, IBI=865ms
[1] Beat at 6103ms, IBI=869ms
[2] Beat at 6278ms, IBI=889ms
[3] Beat at 6547ms, IBI=875ms
```

### Level 2 (Verbose Debug)
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

[0]=2456 [1]=2391 [2]=0 [3]=2678
[0]=2467 [1]=2401 [2]=0 [3]=2689
[0]=2489 [1]=2423 [2]=0 [3]=2701
[0]=2512 [1]=2445 [2]=0 [3]=2715
[0] min=2200 max=2800 thresh=2560
[0]=2534 [1]=2467 [2]=0 [3]=2728
[0] BEAT at 3421ms, IBI=0ms (first, not sent)
[0]=2556 [1]=2489 [2]=0 [3]=2741
[0]=2578 [1]=2511 [2]=0 [3]=2754
[1] min=2100 max=2700 thresh=2460
[1] BEAT at 3856ms, IBI=0ms (first, not sent)
[0]=2545 [1]=2489 [2]=0 [3]=2767
[0]=2523 [1]=2467 [2]=0 [3]=2780
[0] BEAT at 4287ms, IBI=866ms
Sent OSC: /heartbeat/0 866
```

---

**END OF DOCUMENT**
