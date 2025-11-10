# Phase 2 Firmware Implementation - Task Breakdown

Reference: ../reference/phase2-firmware-trd.md

## Prerequisites

**Dependencies:**
- Component 7: Phase 1 Firmware Implementation (complete)
- PulseSensor hardware available
- Python OSC receiver tested

**Validation Tasks:**

- [ ] **Task 0.1**: Verify Phase 1 firmware complete and working (TRD §0.1)
  - Confirm Phase 1 firmware uploaded and running
  - Verify WiFi connection stable (check serial output)
  - Verify OSC messages successfully transmitted to server
  - Run Python OSC receiver: `python3 testing/osc_receiver.py --port 8000`
  - Verify receiver shows messages at ~1 Hz with 0 invalid messages
  - Run 5-minute stability test: No crashes, continuous operation
  - **Status**: Phase 1 validation complete

- [ ] **Task 0.2**: Connect PulseSensor hardware (TRD §0.2)
  - Connect PulseSensor signal wire (purple/white) to ESP32 GPIO 32 (ADC1_CH4)
  - Connect PulseSensor VCC wire (red) to ESP32 3.3V pin
  - Connect PulseSensor GND wire (black) to ESP32 GND pin
  - Verify PulseSensor LED is illuminated (indicates power)
  - Secure connections (no loose jumper wires)
  - **Status**: Hardware connected and powered

- [ ] **Task 0.3**: Verify sensor connection with test sketch (TRD §0.2)
  - Create temporary test file: `firmware/heartbeat_phase1/test_sensor.cpp`
  - Implement test code:
    ```cpp
    void setup() {
        Serial.begin(115200);
        pinMode(32, INPUT);
    }
    void loop() {
        int raw = analogRead(32);
        Serial.println(raw);
        delay(100);
    }
    ```
  - Temporarily rename `src/main.cpp` to `src/main.cpp.phase1`
  - Rename test file to `src/main.cpp`
  - Upload: `pio run --target upload && pio device monitor`
  - Apply finger to sensor, verify values change (2000-3000 range when finger applied)
  - Verify values ~0 or constant when no finger
  - Restore original: `mv src/main.cpp.phase1 src/main.cpp`
  - **Status**: Sensor hardware validated

- [ ] **Task 0.4**: Review Phase 2 TRD and understand architecture
  - Read TRD sections 1-2 (Objective, Architecture)
  - Review signal processing pipeline (ADC → Filter → Baseline → Beat Detection)
  - Understand state machine extensions (SENSOR_INIT, SENSOR_DISCONNECTED, RUNNING)
  - Review all function specifications (TRD §6)
  - **Status**: Architecture understood

## Component 8.1: Configuration Updates ✅ COMPLETE

- [x] **Task 1.1**: Update configuration constants (TRD §4.2, §4.3, §4.4)
  - Edit `firmware/heartbeat_phase1/src/main.cpp`
  - Add Phase 2 hardware configuration after existing Phase 1 constants:
    - `const int SENSOR_PIN = 32;` (GPIO 32, ADC1_CH4)
    - `const int ADC_RESOLUTION = 12;` (12-bit ADC)
  - **Status**: Hardware configuration added (lines 26-27)

- [x] **Task 1.2**: Add signal processing parameters (TRD §4.3)
  - Add sampling configuration constants:
    - `const int SAMPLE_RATE_HZ = 50;` (50 samples/second)
    - `const int SAMPLE_INTERVAL_MS = 20;` (20ms between samples)
  - Add moving average filter constants:
    - `const int MOVING_AVG_SAMPLES = 5;` (100ms smoothing window)
  - Add baseline tracking constants:
    - `const float BASELINE_DECAY_RATE = 0.1;` (10% decay)
    - `const int BASELINE_DECAY_INTERVAL = 150;` (3 seconds @ 50Hz)
  - **Status**: Signal processing parameters defined (lines 29-34)

- [x] **Task 1.3**: Add beat detection parameters (TRD §4.4)
  - Add threshold detection constants:
    - `const float THRESHOLD_FRACTION = 0.6;` (60% of signal range)
    - `const int MIN_SIGNAL_RANGE = 50;` (minimum ADC range for valid signal)
  - Add refractory period constant:
    - `const unsigned long REFRACTORY_PERIOD_MS = 300;` (max 200 BPM)
  - Add disconnection detection constants:
    - `const int FLAT_SIGNAL_THRESHOLD = 5;` (ADC variance threshold)
    - `const unsigned long DISCONNECT_TIMEOUT_MS = 1000;` (1 second flat signal)
  - **Status**: Beat detection parameters defined (lines 36-41)

- [x] **Task 1.4**: Remove Phase 1 test message constant (TRD §4.5)
  - Delete or comment out: `const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;`
  - Add comment: "// Phase 1 constant removed - Phase 2 uses event-driven OSC messages"
  - **Status**: Configuration cleaned up (line 45 commented, Phase 1 test code in loop() temporarily disabled lines 233-257)

- [x] **Task 1.5**: Validate configuration values match TRD specs
  - Verify SENSOR_PIN = 32 (TRD §4.2)
  - Verify SAMPLE_RATE_HZ = 50 (TRD §4.3)
  - Verify THRESHOLD_FRACTION = 0.6 (TRD §4.4)
  - Verify MIN_SIGNAL_RANGE = 50 (TRD §4.4)
  - Verify REFRACTORY_PERIOD_MS = 300 (TRD §4.4)
  - **Status**: Configuration validated - all 12 constants correct, 40 tests pass, 100% TRD compliance

## Component 8.2: Data Structure Modifications ✅ COMPLETE

- [x] **Task 2.1**: Modify SystemState structure (TRD §5.1)
  - Update `SystemState` struct definition:
    - Keep: `bool wifiConnected;`
    - Add: `unsigned long lastWiFiCheckTime;` (for WiFi monitoring rate limit)
    - Add: `unsigned long loopCounter;` (for debug output throttling)
    - Remove: `unsigned long lastMessageTime;` (no longer periodic messages)
    - Remove: `uint32_t messageCounter;` (no longer needed)
  - Update initialization: `SystemState state = {false, 0, 0};`
  - **Status**: SystemState updated for Phase 2

- [x] **Task 2.2**: Add SensorState structure (TRD §5.2)
  - Add new `SensorState` struct definition after `SystemState`:
    - Moving average fields: `int rawSamples[MOVING_AVG_SAMPLES]; int sampleIndex; int smoothedValue;`
    - Baseline tracking fields: `int minValue; int maxValue; int samplesSinceDecay;`
    - Beat detection fields: `bool aboveThreshold; unsigned long lastBeatTime; unsigned long lastIBI; bool firstBeatDetected;`
    - Disconnection detection fields: `bool isConnected; int lastRawValue; int flatSampleCount;`
  - **Status**: SensorState structure defined

- [x] **Task 2.3**: Initialize SensorState global variable (TRD §5.2)
  - Add global declaration: `SensorState sensor;`
  - Initialize with designated initializers:
    - `.rawSamples = {0}` (will be filled in setup)
    - `.sampleIndex = 0`, `.smoothedValue = 0`
    - `.minValue = 0`, `.maxValue = 4095`, `.samplesSinceDecay = 0`
    - `.aboveThreshold = false`, `.lastBeatTime = 0`, `.lastIBI = 0`, `.firstBeatDetected = false`
    - `.isConnected = false`, `.lastRawValue = 0`, `.flatSampleCount = 0`
  - **Status**: Sensor state initialized

- [x] **Task 2.4**: Add LED pulse global variable (TRD §5.3, §6.7)
  - Add global variable: `static unsigned long ledPulseTime = 0;`
  - Add comment: "// Time when LED beat pulse started (for 50ms pulse duration)"
  - **Status**: LED pulse tracking added

## Component 8.3: Sensor Initialization Function ✅ COMPLETE

- [x] **Task 3.1**: Create initializeSensor() function signature (TRD §6.1)
  - Add function declaration: `void initializeSensor();`
  - Add function implementation skeleton after global variables
  - **Status**: Function structure created

- [x] **Task 3.2**: Implement ADC configuration (TRD §6.1, R1)
  - Call `analogSetAttenuation(ADC_11db);` (0-3.3V input range)
  - Call `analogReadResolution(12);` (12-bit resolution, 0-4095)
  - Optional (ESP32 core-dependent): Call `adcAttachPin(SENSOR_PIN);`
  - Add serial output: "Initializing ADC..."
  - **Status**: ADC configured for 12-bit 0-3.3V range

- [x] **Task 3.3**: Implement initial reading and buffer pre-fill (TRD §6.1, R2-R3)
  - Read first ADC sample: `int firstReading = analogRead(SENSOR_PIN);`
  - Print to serial: `Serial.print("First ADC reading: "); Serial.println(firstReading);`
  - Pre-fill moving average buffer in loop:
    ```cpp
    for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
        sensor.rawSamples[i] = firstReading;
    }
    ```
  - **Status**: Buffer pre-filled with first reading

- [x] **Task 3.4**: Implement baseline initialization (TRD §6.1, R4)
  - Set initial values:
    - `sensor.minValue = firstReading;`
    - `sensor.maxValue = firstReading;`
    - `sensor.smoothedValue = firstReading;`
  - **Status**: Baseline initialized

- [x] **Task 3.5**: Implement connection state initialization (TRD §6.1, R5)
  - Set connection state:
    - `sensor.isConnected = true;` (assume connected at start)
    - `sensor.lastRawValue = firstReading;`
    - `sensor.lastBeatTime = millis();` (prevents false refractory rejection)
  - Print to serial: "Sensor initialized. Ready for heartbeat detection."
  - **Status**: Sensor state initialized

## Component 8.4: Moving Average Filter Function ✅ COMPLETE

- [x] **Task 4.1**: Create updateMovingAverage() function (TRD §6.2)
  - Add function declaration: `void updateMovingAverage(int rawValue);`
  - Add function implementation skeleton
  - **Status**: Function structure created

- [x] **Task 4.2**: Implement circular buffer update (TRD §6.2, R6)
  - Replace oldest sample: `sensor.rawSamples[sensor.sampleIndex] = rawValue;`
  - Increment index with wraparound: `sensor.sampleIndex = (sensor.sampleIndex + 1) % MOVING_AVG_SAMPLES;`
  - **Status**: Circular buffer implemented

- [x] **Task 4.3**: Implement mean calculation (TRD §6.2, R7)
  - Calculate sum of all samples:
    ```cpp
    int sum = 0;
    for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
        sum += sensor.rawSamples[i];
    }
    ```
  - Calculate and store mean: `sensor.smoothedValue = sum / MOVING_AVG_SAMPLES;`
  - **Status**: Moving average calculation complete

## Component 8.5: Baseline Tracking Function ✅ COMPLETE

- [x] **Task 5.1**: Create updateBaseline() function (TRD §6.3)
  - Add function declaration: `void updateBaseline();`
  - Add function implementation skeleton
  - **Status**: Function structure created

- [x] **Task 5.2**: Implement instant expansion (TRD §6.3, R9)
  - Check for new minimum:
    ```cpp
    if (sensor.smoothedValue < sensor.minValue) {
        sensor.minValue = sensor.smoothedValue;
    }
    ```
  - Check for new maximum:
    ```cpp
    if (sensor.smoothedValue > sensor.maxValue) {
        sensor.maxValue = sensor.smoothedValue;
    }
    ```
  - **Status**: Instant baseline expansion implemented

- [x] **Task 5.3**: Implement periodic decay (TRD §6.3, R10-R11)
  - Increment decay counter: `sensor.samplesSinceDecay++;`
  - Check if decay interval reached:
    ```cpp
    if (sensor.samplesSinceDecay >= BASELINE_DECAY_INTERVAL) {
        // Apply decay toward current signal level
        sensor.minValue += (int)((sensor.smoothedValue - sensor.minValue) * BASELINE_DECAY_RATE);
        sensor.maxValue -= (int)((sensor.maxValue - sensor.smoothedValue) * BASELINE_DECAY_RATE);
        sensor.samplesSinceDecay = 0;
    }
    ```
  - **Status**: Exponential decay baseline tracking complete

## Component 8.6: Disconnection Detection Function

- [ ] **Task 6.1**: Create checkDisconnection() function (TRD §6.4)
  - Add function declaration: `void checkDisconnection(int rawValue);`
  - Add function implementation skeleton
  - **Status**: Function structure created

- [ ] **Task 6.2**: Implement flat signal detection (TRD §6.4, R12)
  - Calculate variance: `int variance = abs(rawValue - sensor.lastRawValue);`
  - Check variance threshold:
    ```cpp
    if (variance < FLAT_SIGNAL_THRESHOLD) {
        sensor.flatSampleCount++;
    } else {
        sensor.flatSampleCount = 0;
    }
    ```
  - **Status**: Flat signal variance check implemented

- [ ] **Task 6.3**: Implement disconnection threshold (TRD §6.4, R13-R14)
  - Calculate signal range: `int range = sensor.maxValue - sensor.minValue;`
  - Check disconnection conditions:
    ```cpp
    bool wasConnected = sensor.isConnected;
    if (sensor.flatSampleCount >= 50 || range < MIN_SIGNAL_RANGE) {
        sensor.isConnected = false;
        if (wasConnected) {
            Serial.println("Sensor disconnected");
        }
    }
    ```
  - **Status**: Disconnection detection implemented

- [ ] **Task 6.4**: Implement reconnection detection (TRD §6.4, R15)
  - Check reconnection conditions:
    ```cpp
    if (!sensor.isConnected && sensor.flatSampleCount == 0 && range >= MIN_SIGNAL_RANGE) {
        sensor.isConnected = true;
        Serial.println("Sensor reconnected");
        sensor.minValue = sensor.smoothedValue;
        sensor.maxValue = sensor.smoothedValue;
    }
    ```
  - **Status**: Reconnection detection implemented

- [ ] **Task 6.5**: Update last raw value (TRD §6.4, R16)
  - Store current value for next iteration: `sensor.lastRawValue = rawValue;`
  - **Status**: Disconnection detection function complete

## Component 8.7: Beat Detection Function

- [ ] **Task 7.1**: Create detectBeat() function skeleton (TRD §6.5)
  - Add function declaration: `void detectBeat();`
  - Add function implementation skeleton
  - Add early return if disconnected:
    ```cpp
    if (!sensor.isConnected) {
        return;  // No detection when disconnected
    }
    ```
  - **Status**: Function structure created

- [ ] **Task 7.2**: Implement threshold calculation (TRD §6.5, R17)
  - Calculate adaptive threshold:
    ```cpp
    int threshold = sensor.minValue + (int)((sensor.maxValue - sensor.minValue) * THRESHOLD_FRACTION);
    ```
  - **Status**: Threshold calculation implemented

- [ ] **Task 7.3**: Implement rising edge detection (TRD §6.5, R18)
  - Check for rising edge:
    ```cpp
    if (sensor.smoothedValue >= threshold && !sensor.aboveThreshold) {
        // Potential beat detected
    }
    ```
  - **Status**: Rising edge detection logic added

- [ ] **Task 7.4**: Implement refractory period check (TRD §6.5, R19)
  - Inside rising edge block, check refractory period BEFORE setting state:
    ```cpp
    unsigned long timeSinceLastBeat = millis() - sensor.lastBeatTime;
    if (timeSinceLastBeat < REFRACTORY_PERIOD_MS) {
        return;  // Ignore this beat, do NOT update state
    }
    // Valid beat - now safe to update state
    sensor.aboveThreshold = true;
    ```
  - **Critical**: Must return BEFORE setting `aboveThreshold` if refractory period fails
  - **Status**: Refractory period implemented correctly

- [ ] **Task 7.5**: Implement first beat handling (TRD §6.5, R20)
  - After refractory check passes, handle first beat:
    ```cpp
    if (!sensor.firstBeatDetected) {
        sensor.firstBeatDetected = true;
        sensor.lastBeatTime = millis();
        Serial.println("First beat detected");
        return;  // Don't send OSC message (no reference IBI)
    }
    ```
  - **Status**: First beat detection implemented

- [ ] **Task 7.6**: Implement subsequent beat handling (TRD §6.5, R20)
  - After first beat check, handle subsequent beats:
    ```cpp
    // Second and subsequent beats
    unsigned long ibi = millis() - sensor.lastBeatTime;
    sensor.lastBeatTime = millis();
    sensor.lastIBI = ibi;
    sendHeartbeatOSC((int)ibi);
    ledPulseTime = millis();  // Trigger LED pulse
    Serial.print("Beat detected, IBI=");
    Serial.print(ibi);
    Serial.print("ms, BPM=");
    Serial.println(60000 / ibi);
    ```
  - **Status**: IBI calculation and OSC transmission implemented

- [ ] **Task 7.7**: Implement falling edge detection (TRD §6.5, R21)
  - Add falling edge check after rising edge block:
    ```cpp
    if (sensor.smoothedValue < threshold && sensor.aboveThreshold) {
        sensor.aboveThreshold = false;  // Ready for next beat
    }
    ```
  - **Status**: Beat detection function complete

## Component 8.8: LED Status Function Update

- [ ] **Task 8.1**: Modify updateLED() function for beat pulse (TRD §6.7, R22-R24)
  - Update existing `updateLED()` function:
    ```cpp
    void updateLED() {
        if (!state.wifiConnected) {
            // Blink during connection (Phase 1 behavior)
            digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
        } else if (millis() - ledPulseTime < 50) {
            // Beat pulse active (50ms pulse)
            digitalWrite(STATUS_LED_PIN, HIGH);
        } else {
            // Solid on when connected (Phase 1 behavior)
            digitalWrite(STATUS_LED_PIN, HIGH);
        }
    }
    ```
  - **Status**: LED beat pulse implemented

## Component 8.9: Main Program Flow Updates

- [ ] **Task 9.1**: Update setup() function banner (TRD §7.1, R26)
  - Update startup banner in `setup()`:
    ```cpp
    Serial.println("\n=== Heartbeat Installation - Phase 2 ===");
    Serial.println("Real Heartbeat Detection");
    Serial.print("Sensor ID: ");
    Serial.println(SENSOR_ID);
    ```
  - **Status**: Banner updated for Phase 2

- [ ] **Task 9.2**: Add sensor GPIO configuration (TRD §7.1, R27)
  - After existing GPIO configuration, add:
    ```cpp
    pinMode(SENSOR_PIN, INPUT);  // ADC pin (actually optional, analogRead() auto-configures)
    ```
  - **Status**: Sensor pin configured

- [ ] **Task 9.3**: Add sensor initialization call (TRD §7.1, R30)
  - After UDP initialization, add:
    ```cpp
    initializeSensor();  // Configure ADC, pre-fill buffers
    Serial.println("Sensor initialized. Ready for heartbeat detection.");
    ```
  - **Status**: Sensor initialization integrated into setup

- [ ] **Task 9.4**: Update setup completion message (TRD §7.1, R31)
  - Replace existing completion message with:
    ```cpp
    Serial.println("Setup complete. Place finger on sensor to begin.");
    ```
  - **Status**: Setup function updated

- [ ] **Task 9.5**: Add sampling timing logic to loop() (TRD §7.2, R32)
  - Add static variable and timing check at start of loop():
    ```cpp
    static unsigned long lastSampleTime = 0;
    
    unsigned long currentTime = millis();
    if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
        lastSampleTime = currentTime;
        // Sampling code will go here
    }
    ```
  - **Status**: Sampling timing implemented

- [ ] **Task 9.6**: Integrate ADC reading into sample interval (TRD §7.2, R33)
  - Inside sampling interval block, add ADC read:
    ```cpp
    int rawValue = analogRead(SENSOR_PIN);
    ```
  - **Status**: ADC reading integrated

- [ ] **Task 9.7**: Add signal processing pipeline calls (TRD §7.2, R34)
  - After ADC read, add signal processing calls:
    ```cpp
    updateMovingAverage(rawValue);
    updateBaseline();
    checkDisconnection(rawValue);
    ```
  - **Status**: Signal processing pipeline integrated

- [ ] **Task 9.8**: Integrate beat detection call (TRD §7.2, R35)
  - After signal processing, add beat detection:
    ```cpp
    detectBeat();
    ```
  - **Status**: Beat detection integrated

- [ ] **Task 9.9**: Update loop delay for 50Hz operation (TRD §7.2, R38)
  - Change loop delay from Phase 1 value to minimal delay:
    ```cpp
    delay(1);  // Minimal delay for WiFi background tasks
    ```
  - **Status**: Loop delay updated

- [ ] **Task 9.10**: Add optional debug output (TRD §7.2, R39)
  - Inside sampling interval block, after signal processing, add optional debug:
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
  - Comment out for production, enable for tuning
  - **Status**: Debug output available for tuning

## Component 8.10: Compilation & Initial Testing

- [ ] **Task 10.1**: Compile Phase 2 firmware (TRD §9)
  - Run: `cd /home/sderle/corazonn/firmware/heartbeat_phase1 && pio run`
  - **Expected**: Compilation succeeds without errors
  - **Expected**: RAM usage ~16-18%, Flash usage ~38-40%
  - Resolve any compilation errors (check TRD §6 for function signatures)
  - **Status**: Firmware compiles successfully

- [ ] **Task 10.2**: Upload Phase 2 firmware (TRD §9)
  - Ensure PulseSensor connected to GPIO 32
  - Run: `pio run --target upload`
  - **Expected**: Upload completes, "Hard resetting via RTS pin..."
  - **Status**: Phase 2 firmware uploaded

- [ ] **Task 10.3**: Verify startup sequence (TRD §10.2)
  - Open serial monitor: `pio device monitor`
  - **Expected serial output**:
    ```
    === Heartbeat Installation - Phase 2 ===
    Real Heartbeat Detection
    Sensor ID: 0
    Connecting to WiFi: heartbeat-install
    Connected! IP: 192.168.X.X
    First ADC reading: XXXX
    Sensor initialized. Ready for heartbeat detection.
    Setup complete. Place finger on sensor to begin.
    ```
  - Verify all initialization messages appear
  - **Status**: Startup sequence validated

## Component 8.11: Heartbeat Detection Validation

- [ ] **Task 11.1**: Start Python OSC receiver (TRD §10.2)
  - Terminal 1: `python3 testing/osc_receiver.py --port 8000`
  - Verify receiver starts and listens on port 8000
  - **Status**: Receiver running

- [ ] **Task 11.2**: Test first beat detection (TRD §10.2)
  - Place fingertip on PulseSensor (cover LED completely)
  - Apply gentle, steady pressure
  - Hold still for 10 seconds
  - **Expected serial output**:
    ```
    First beat detected
    Beat detected, IBI=XXXms, BPM=XX
    Beat detected, IBI=XXXms, BPM=XX
    ...
    ```
  - Verify "First beat detected" appears within 3 seconds
  - Verify subsequent beats appear regularly
  - **Status**: Beat detection working

- [ ] **Task 11.3**: Verify OSC message transmission (TRD §10.2)
  - Check receiver terminal (Terminal 1)
  - **Expected receiver output**:
    ```
    [/heartbeat/0] IBI: XXXms, BPM: XX.X
    [/heartbeat/0] IBI: XXXms, BPM: XX.X
    ...
    ```
  - Verify messages appear after first beat
  - Verify IBI values are realistic (300-2000ms typical)
  - Verify BPM values are realistic (30-200 BPM typical)
  - **Status**: Real heartbeat data transmitted via OSC

- [ ] **Task 11.4**: Verify LED beat pulse (TRD §10.2)
  - Observe built-in LED during heartbeat detection
  - Before finger applied: Solid ON (WiFi connected)
  - After beats start: Brief flicker on each beat (50ms pulse)
  - **Status**: LED visual feedback working

## Component 8.12: Disconnection Handling Validation

- [ ] **Task 12.1**: Test sensor disconnection (TRD §10.2)
  - Remove finger from sensor (while monitoring serial output)
  - **Expected**: "Sensor disconnected" message appears within 1 second
  - **Expected**: Receiver stops showing new messages
  - **Expected**: LED stays solid ON (WiFi still connected)
  - **Status**: Disconnection detection working

- [ ] **Task 12.2**: Test sensor reconnection (TRD §10.2)
  - Reapply finger to sensor
  - **Expected serial output within 3 seconds**:
    ```
    Sensor reconnected
    First beat detected
    Beat detected, IBI=XXXms, BPM=XX
    ```
  - **Expected**: Receiver shows messages resume
  - **Status**: Reconnection handling working

## Component 8.13: BPM Accuracy Validation

- [ ] **Task 13.1**: Compare BPM with smartphone app (TRD §10.2)
  - Install smartphone heart rate app (e.g., "Instant Heart Rate")
  - Simultaneously measure:
    - Place finger on PulseSensor connected to ESP32
    - Place another finger on smartphone camera
  - Run both measurements for 30 seconds
  - Compare BPM values from serial output vs smartphone app
  - **Acceptance criteria**: ±5 BPM difference
  - **Status**: BPM accuracy within ±5 BPM

- [ ] **Task 13.2**: Tune threshold if needed (TRD §11.1)
  - If BPM accuracy outside ±5 BPM range:
    - **Missed beats** (gaps > 2 seconds): Decrease `THRESHOLD_FRACTION` to 0.55 or 0.5
    - **False beats** (BPM > 120 at rest): Increase `THRESHOLD_FRACTION` to 0.65 or 0.7
    - **Incorrect BPM**: Improve sensor contact, hold still, try different finger
  - Recompile and retest after each adjustment
  - Document final threshold value
  - **Status**: Threshold tuned for accurate beat detection

## Component 8.14: Extended Stability Testing

- [ ] **Task 14.1**: Run 30-minute stability test (TRD §10.2)
  - Start receiver: `python3 testing/osc_receiver.py --port 8000`
  - Upload firmware: `pio run --target upload && pio device monitor`
  - Place finger on sensor
  - Monitor continuously for 30+ minutes
  - **Check for**:
    - No crashes or ESP32 resets
    - Consistent BPM (±10 BPM variation normal)
    - No WiFi disconnections
    - No "Sensor disconnected" false alarms
    - Receiver shows continuous message stream
  - **Status**: 30-minute test passed

- [ ] **Task 14.2**: Verify memory stability (TRD §14.4)
  - During stability test, add free heap monitoring
  - Add to debug output: `Serial.println(ESP.getFreeHeap());`
  - Verify heap size stable (no continuous decrease)
  - Remove debug code after verification
  - **Status**: No memory leaks detected

## Component 8.15: Multi-Unit Testing

- [ ] **Task 15.1**: Program additional ESP32 units (TRD §10.3)
  - For each additional ESP32:
    - Edit `src/main.cpp`: Set unique `SENSOR_ID` (1, 2, or 3)
    - Keep all other configuration identical (WIFI_SSID, PASSWORD, SERVER_IP)
    - Compile: `pio run`
    - Upload: `pio run --target upload`
  - Physically label units with sensor ID (sticker or marker)
  - **Status**: Multiple units programmed with unique IDs

- [ ] **Task 15.2**: Run multi-unit integration test (TRD §10.3, §12.5)
  - Start single receiver: `python3 testing/osc_receiver.py --port 8000`
  - Power 4 ESP32 units simultaneously (minimum 4 units required for full acceptance per TRD §12.5)
  - Apply different fingers to each sensor
  - Run for 5+ minutes
  - **Expected receiver output**:
    - Messages from all sensor IDs (e.g., /heartbeat/0, /heartbeat/1, /heartbeat/2, /heartbeat/3)
    - Each sensor has independent BPM
    - No message interference
    - Invalid message count = 0
  - Remove one finger, verify only that sensor stops sending
  - **Status**: Multi-unit operation validated

## Component 8.16: Acceptance Criteria Validation

- [ ] **Task 16.1**: Verify compilation criteria (TRD §12.1)
  - ✅ Compiles without errors
  - ✅ Compiles without warnings (or only benign warnings)
  - ✅ Binary size < 550KB
  - **Status**: Compilation criteria met

- [ ] **Task 16.2**: Verify runtime behavior criteria (TRD §12.2)
  - ✅ Connects to WiFi within 30 seconds
  - ✅ Initializes sensor successfully
  - ✅ Detects heartbeats within 3 seconds of finger application
  - ✅ BPM accuracy within ±5 BPM vs smartphone app
  - ✅ OSC messages contain real IBI values (not test values)
  - ✅ Python receiver validates all messages (0 invalid)
  - ✅ Runs for 30+ minutes without crashes
  - ✅ LED indicates WiFi connection and beat pulses
  - **Status**: Runtime behavior criteria met

- [ ] **Task 16.3**: Verify signal processing criteria (TRD §12.3)
  - ✅ Moving average smooths noisy signals
  - ✅ Baseline adapts to different signal amplitudes
  - ✅ No false beats from noise
  - ✅ No missed beats from weak signals (with proper tuning)
  - ✅ Refractory period prevents double-triggers
  - **Status**: Signal processing criteria met

- [ ] **Task 16.4**: Verify disconnection handling criteria (TRD §12.4)
  - ✅ Detects sensor removal within 1 second
  - ✅ Stops sending OSC messages when disconnected
  - ✅ Auto-reconnects within 3 seconds of reapplication
  - ✅ Resumes beat detection after reconnection
  - ✅ No crashes when sensor removed/reapplied
  - **Status**: Disconnection handling criteria met

- [ ] **Task 16.5**: Verify multi-unit operation criteria (TRD §12.5)
  - ✅ 4 units operate simultaneously without interference
  - ✅ Each unit sends independent heartbeat data
  - ✅ Receiver distinguishes all sensor IDs correctly
  - ✅ No network congestion (240-480 msg/min total across 4 sensors)
  - **Status**: Multi-unit operation criteria met

## Component 8.17: Documentation & Completion

- [ ] **Task 17.1**: Document tuning parameters
  - Create `firmware/heartbeat_phase1/TUNING.md`:
    - Document final `THRESHOLD_FRACTION` value used
    - Document final `MIN_SIGNAL_RANGE` value used
    - Document BPM accuracy results vs smartphone app
    - Document any sensor-specific quirks discovered
  - **Status**: Tuning parameters documented

- [ ] **Task 17.2**: Update firmware README for Phase 2
  - Update `firmware/README.md`:
    - Add Phase 2 section with overview
    - Document PulseSensor hardware setup (GPIO 32 wiring)
    - Document how to test sensor connection before firmware upload
    - Document tuning parameters and when to adjust
    - Document troubleshooting (TRD §14)
  - **Status**: README updated for Phase 2

- [ ] **Task 17.3**: Create pre-deployment checklist
  - Add to README: "Phase 2 Pre-Deployment Checklist"
    - Hardware: PulseSensor connected to GPIO 32, 3.3V, GND
    - Configuration: WIFI_SSID, WIFI_PASSWORD, SERVER_IP, SENSOR_ID
    - Testing: Smartphone app BPM comparison, 30-minute stability test
    - Multi-unit: Unique SENSOR_ID per unit, all units tested simultaneously
  - **Status**: Checklist documented

- [ ] **Task 17.4**: Final validation against TRD success metrics (TRD §15)
  - Verify all 15 Phase 2 completion criteria met:
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
  - **Status**: All success metrics met

- [ ] **Task 17.5**: Mark Phase 2 complete
  - Update `docs/tasks.md`: Mark Component 8 (Phase 2 Firmware) as complete
  - Commit all changes: `git add -A && git commit -m "Complete Phase 2 firmware implementation"`
  - Document completion date
  - **Status**: Phase 2 firmware implementation complete

---

## Task Execution Notes

**Order**: Tasks must be completed in sequence. Each task builds on previous work.

**Testing Strategy**:
- Tasks 0.x: Prerequisites and hardware validation
- Tasks 1.x-2.x: Configuration and data structure updates (compile checks)
- Tasks 3.x-8.x: Function implementations (incremental with compile checks)
- Tasks 9.x: Main program flow updates (compile and upload)
- Tasks 10.x: Compilation and initial testing
- Tasks 11.x-12.x: Heartbeat detection and disconnection validation
- Tasks 13.x: BPM accuracy validation and tuning
- Tasks 14.x: Extended stability testing
- Tasks 15.x: Multi-unit validation
- Tasks 16.x: Acceptance criteria verification
- Tasks 17.x: Documentation and completion

**Hardware Required**:
- 1-4 ESP32-WROOM-32 boards (Phase 1 hardware reused)
- 1-4 PulseSensor optical pulse sensors (new for Phase 2)
- USB cables for programming
- 2.4GHz WiFi network (same as Phase 1)
- Development machine with Python OSC receiver
- Smartphone with heart rate monitoring app (for BPM validation)

**Dependencies**:
- Component 7 complete (Phase 1 firmware working)
- PulseSensor hardware available
- Python OSC receiver tested (Components 2-5)

**Acceptance**: Component 8 complete when:
- All tasks checked off
- Firmware detects real heartbeats with ±5 BPM accuracy
- OSC receiver validates all messages (0 invalid) over 30+ minutes
- Multi-unit operation validated (4 ESP32s, independent heartbeat streams)
- All TRD §15 success metrics met

**Critical Implementation Notes**:
1. **Refractory period check** (Task 7.4): MUST return BEFORE setting `aboveThreshold` if check fails
2. **First beat handling** (Task 7.5): MUST return without sending OSC (no reference IBI yet)
3. **Baseline decay** (Task 5.3): Uses integer arithmetic with float multiplication
4. **Disconnection detection** (Task 6.3): Only print message once when state changes
5. **ADC configuration** (Task 3.2): Some ESP32 cores may require `adcAttachPin()` call

**Known Limitations** (will be addressed in Phase 3):
- Single sensor only (GPIO 32)
- Fixed threshold (not auto-adaptive per user)
- No waveform transmission (only IBI)
- No HRV analysis
- Optical sensor sensitive to ambient light, movement, cold hands
