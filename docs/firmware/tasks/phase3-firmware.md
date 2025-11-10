# Phase 3 Firmware Implementation - Task Breakdown

Reference: ../reference/phase3/

## Prerequisites

**Dependencies:**
- Component 7: Phase 1 Firmware Implementation (complete)
- 4× PulseSensor hardware available (GPIO 32-35)
- Python OSC receiver tested

**Validation Tasks:**

- [ ] **Task 0.1**: Verify Phase 1 firmware complete and working (TRD overview.md §0.1)
  - Confirm Phase 1 firmware uploaded and running
  - Verify WiFi connection stable (check serial output)
  - Verify OSC messages successfully transmitted to server
  - Run Python OSC receiver: `python3 testing/osc_receiver.py --port 8000`
  - Verify receiver shows messages at ~1 Hz with 0 invalid messages
  - Run 5-minute stability test: No crashes, continuous operation
  - **Status**: Phase 1 validation complete

- [ ] **Task 0.2**: Connect PulseSensor hardware (TRD overview.md §0.2)
  - Connect 4× PulseSensors:
    - Sensor 0: Signal (purple) → GPIO 32, VCC (red) → 3.3V, GND (black) → GND
    - Sensor 1: Signal → GPIO 33, VCC → 3.3V, GND → GND
    - Sensor 2: Signal → GPIO 34, VCC → 3.3V, GND → GND (input-only pin)
    - Sensor 3: Signal → GPIO 35, VCC → 3.3V, GND → GND (input-only pin)
  - Verify all PulseSensor LEDs illuminated (indicates power)
  - Label each sensor with ID (0-3) using tape/sticker
  - Secure connections (no loose jumper wires)
  - **Status**: Hardware connected and powered (4 sensors)

- [ ] **Task 0.3**: Verify sensor connections with test sketch (TRD overview.md §0.2)
  - Create temporary test project in /tmp: `mkdir -p /tmp/sensor_test && cd /tmp/sensor_test`
  - Initialize test project: `pio project init --board esp32dev`
  - Create `src/main.cpp` with test code to read all 4 ADC pins:
    ```cpp
    #include <Arduino.h>
    void setup() {
        Serial.begin(115200);
        analogReadResolution(12);
    }
    void loop() {
        Serial.print("S0="); Serial.print(analogRead(32));
        Serial.print(" S1="); Serial.print(analogRead(33));
        Serial.print(" S2="); Serial.print(analogRead(34));
        Serial.print(" S3="); Serial.println(analogRead(35));
        delay(100);
    }
    ```
  - Upload: `pio run --target upload && pio device monitor`
  - Apply finger to each sensor sequentially, verify values change (2000-3000 range when finger applied)
  - Verify values ~0-500 or constant baseline when no finger
  - Clean up: `rm -rf /tmp/sensor_test`
  - **Status**: All 4 sensor hardware channels validated

- [ ] **Task 0.4**: Review Phase 3 architecture and documentation (TRD index.md, overview.md)
  - Read overview.md: Prerequisites, objectives, architecture
  - Review configuration.md: Data structures (SensorState array, SystemState)
  - Review implementation.md: Multi-sensor loop() structure
  - Understand multi-sensor key difference: Array indexing, independent state per sensor
  - **Status**: Architecture understood

## Component 9.1: Project Structure & Configuration

- [ ] **Task 1.1**: Create Phase 3 project directory (TRD implementation.md §8.1)
  - Create directory: `mkdir -p /home/user/corazonn/firmware/heartbeat_phase3`
  - Change directory: `cd /home/user/corazonn/firmware/heartbeat_phase3`
  - Initialize: `pio project init --board esp32dev`
  - Copy platformio.ini from Phase 1: `cp ../heartbeat_phase1/platformio.ini .`
  - Verify created: platformio.ini, src/, lib/, include/
  - **Status**: Project initialized with PlatformIO structure

- [ ] **Task 1.2**: Create main.cpp header and includes (TRD configuration.md §3, implementation.md §8.2)
  - File: `/home/user/corazonn/firmware/heartbeat_phase3/src/main.cpp`
  - Add header comment:
    ```cpp
    /**
     * Heartbeat Installation - Phase 3: Multi-Sensor Beat Detection
     * ESP32 Firmware - 4 Independent Pulse Sensors
     * Version: 3.0
     */
    ```
  - Add includes:
    ```cpp
    #include <Arduino.h>
    #include <WiFi.h>
    #include <WiFiUdp.h>
    #include <OSCMessage.h>
    ```
  - **Status**: File structure created

- [ ] **Task 1.3**: Add network configuration (TRD configuration.md §4.1)
  - Add network configuration constants (same as Phase 1):
    ```cpp
    // Network Configuration
    const char* WIFI_SSID = "heartbeat-install";
    const char* WIFI_PASSWORD = "your-password-here";
    const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS
    const uint16_t SERVER_PORT = 8000;
    const unsigned long WIFI_TIMEOUT_MS = 30000;
    ```
  - **Status**: Network constants defined

- [ ] **Task 1.4**: Add hardware configuration (TRD configuration.md §4.2)
  - Add hardware constants:
    ```cpp
    // Hardware Configuration
    const int SENSOR_PINS[4] = {32, 33, 34, 35};  // ADC1 channels
    const int NUM_SENSORS = 4;
    const int STATUS_LED_PIN = 2;  // Built-in LED
    const int ADC_RESOLUTION = 12;  // 12-bit: 0-4095
    ```
  - **Status**: Hardware configuration defined (4 sensors)

- [ ] **Task 1.5**: Add signal processing parameters (TRD configuration.md §4.3)
  - Add sampling and filtering constants:
    ```cpp
    // Signal Processing Parameters
    const int SAMPLE_RATE_HZ = 50;                  // Per sensor
    const int SAMPLE_INTERVAL_MS = 20;              // 1000 / 50
    const int MOVING_AVG_SAMPLES = 5;               // 100ms window
    const float BASELINE_DECAY_RATE = 0.1;          // 10% decay
    const int BASELINE_DECAY_INTERVAL = 150;        // 3 sec @ 50Hz
    ```
  - **Status**: Signal processing parameters defined

- [ ] **Task 1.6**: Add beat detection parameters (TRD configuration.md §4.4)
  - Add beat detection constants:
    ```cpp
    // Beat Detection Parameters
    const float THRESHOLD_FRACTION = 0.6;           // 60% of range
    const int MIN_SIGNAL_RANGE = 50;                // ADC units minimum
    const unsigned long REFRACTORY_PERIOD_MS = 300; // Max 200 BPM
    const int FLAT_SIGNAL_THRESHOLD = 5;            // Variance for "flat"
    const unsigned long DISCONNECT_TIMEOUT_MS = 1000; // 1 sec flat
    ```
  - **Status**: Beat detection parameters defined

- [ ] **Task 1.7**: Add debug level configuration (TRD configuration.md §4.5)
  - Add debug level macro:
    ```cpp
    // Debug Configuration
    #define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose
    // Level 0: WiFi status only
    // Level 1: Beat timestamps + BPM
    // Level 2: Raw ADC values every 100ms, baseline tracking
    ```
  - **Status**: Debug level configured

- [ ] **Task 1.8**: Validate all configuration constants (TRD configuration.md §4)
  - Verify SENSOR_PINS = {32, 33, 34, 35} (ADC1 channels)
  - Verify NUM_SENSORS = 4
  - Verify SAMPLE_INTERVAL_MS = 1000 / SAMPLE_RATE_HZ
  - Verify all constants match TRD specifications
  - Compile: `pio run` (should succeed with empty setup/loop)
  - **Status**: Configuration validated, compiles

## Component 9.2: Data Structures

- [ ] **Task 2.1**: Define SensorState structure (TRD configuration.md §5.1, R1-R5)
  - Add SensorState struct definition:
    ```cpp
    struct SensorState {
      // Hardware
      int pin;

      // Moving average filter
      int rawSamples[MOVING_AVG_SAMPLES];
      int sampleIndex;
      int smoothedValue;

      // Baseline tracking
      int minValue;
      int maxValue;
      int samplesSinceDecay;

      // Beat detection
      bool aboveThreshold;
      unsigned long lastBeatTime;
      unsigned long lastIBI;
      bool firstBeatDetected;

      // Disconnection detection
      bool isConnected;
      int lastRawValue;
      int flatSampleCount;
    };
    ```
  - **Status**: SensorState structure defined

- [ ] **Task 2.2**: Define SystemState structure (TRD configuration.md §5.2)
  - Add SystemState struct definition:
    ```cpp
    struct SystemState {
      bool wifiConnected;
      unsigned long lastWiFiCheckTime;
      unsigned long loopCounter;
      bool beatDetectedThisLoop;
    };
    ```
  - **Status**: SystemState structure defined

- [ ] **Task 2.3**: Declare global variables (TRD configuration.md §5.3)
  - Add global variable declarations:
    ```cpp
    // Global State
    WiFiUDP udp;
    SystemState system = {false, 0, 0, false};
    SensorState sensors[4];  // Array of 4 sensor states
    ```
  - **Status**: Global variables declared

- [ ] **Task 2.4**: Add function declarations (TRD implementation.md §8.2)
  - Add forward declarations:
    ```cpp
    // WiFi (from Phase 1)
    bool connectWiFi();
    void checkWiFi();

    // Sensor processing
    void initializeSensor(int sensorIndex);
    void readAndFilterSensor(int sensorIndex);
    void updateBaseline(int sensorIndex);
    void detectBeat(int sensorIndex);

    // OSC transmission
    void sendHeartbeatOSC(int sensorIndex, int ibi_ms);

    // Status indication
    void updateLED();
    ```
  - Compile: `pio run` (should succeed with empty functions)
  - **Status**: Function declarations added, compiles

## Component 9.3: Sensor Initialization Function

- [ ] **Task 3.1**: Implement initializeSensor() signature (TRD api-sensors.md §6.1)
  - Add function skeleton:
    ```cpp
    void initializeSensor(int sensorIndex) {
      // Implementation will go here
    }
    ```
  - **Status**: Function signature created

- [ ] **Task 3.2**: Implement initial ADC reading (TRD api-sensors.md §6.1, R6)
  - Read first ADC value:
    ```cpp
    int firstReading = analogRead(sensors[sensorIndex].pin);
    #if DEBUG_LEVEL >= 1
      Serial.print("Sensor ");
      Serial.print(sensorIndex);
      Serial.print(" initial ADC: ");
      Serial.println(firstReading);
    #endif
    ```
  - **Status**: Initial reading implemented

- [ ] **Task 3.3**: Implement buffer pre-fill (TRD api-sensors.md §6.1, R7)
  - Pre-fill moving average buffer:
    ```cpp
    for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
      sensors[sensorIndex].rawSamples[i] = firstReading;
    }
    ```
  - **Status**: Buffer pre-filled

- [ ] **Task 3.4**: Implement state initialization (TRD api-sensors.md §6.1, R8)
  - Initialize all sensor state fields:
    ```cpp
    sensors[sensorIndex].sampleIndex = 0;
    sensors[sensorIndex].smoothedValue = firstReading;
    sensors[sensorIndex].minValue = firstReading;
    sensors[sensorIndex].maxValue = firstReading;
    sensors[sensorIndex].samplesSinceDecay = 0;

    sensors[sensorIndex].aboveThreshold = false;
    sensors[sensorIndex].lastBeatTime = 0;
    sensors[sensorIndex].lastIBI = 0;
    sensors[sensorIndex].firstBeatDetected = false;

    sensors[sensorIndex].isConnected = true;
    sensors[sensorIndex].lastRawValue = firstReading;
    sensors[sensorIndex].flatSampleCount = 0;
    ```
  - Compile: `pio run`
  - **Status**: Sensor initialization complete

## Component 9.4: Sampling & Filtering Function

- [ ] **Task 4.1**: Implement readAndFilterSensor() signature (TRD api-sensors.md §6.2)
  - Add function skeleton:
    ```cpp
    void readAndFilterSensor(int sensorIndex) {
      // Implementation will go here
    }
    ```
  - **Status**: Function signature created

- [ ] **Task 4.2**: Implement ADC read (TRD api-sensors.md §6.2, R9)
  - Read current ADC value:
    ```cpp
    int rawValue = analogRead(sensors[sensorIndex].pin);
    ```
  - **Status**: ADC reading implemented

- [ ] **Task 4.3**: Implement moving average update (TRD api-sensors.md §6.2, R10)
  - Update circular buffer and calculate mean:
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
  - **Status**: Moving average filter implemented

- [ ] **Task 4.4**: Implement flat signal detection (TRD api-sensors.md §6.2, R11)
  - Check variance and update disconnection state:
    ```cpp
    if (abs(rawValue - sensors[sensorIndex].lastRawValue) < FLAT_SIGNAL_THRESHOLD) {
      sensors[sensorIndex].flatSampleCount++;
    } else {
      sensors[sensorIndex].flatSampleCount = 0;
    }

    if (sensors[sensorIndex].flatSampleCount >= 50) {  // 50 samples = 1 sec
      if (sensors[sensorIndex].isConnected) {
        #if DEBUG_LEVEL >= 1
          Serial.print("[");
          Serial.print(sensorIndex);
          Serial.println("] Sensor disconnected");
        #endif
      }
      sensors[sensorIndex].isConnected = false;
    }

    sensors[sensorIndex].lastRawValue = rawValue;
    ```
  - Compile: `pio run`
  - **Status**: Sampling and filtering complete

## Component 9.5: Baseline Tracking Function

- [ ] **Task 5.1**: Implement updateBaseline() signature (TRD api-signal-processing.md §6.3)
  - Add function skeleton:
    ```cpp
    void updateBaseline(int sensorIndex) {
      // Implementation will go here
    }
    ```
  - **Status**: Function signature created

- [ ] **Task 5.2**: Implement instant expansion (TRD api-signal-processing.md §6.3, R12)
  - Expand min/max immediately if signal exceeds bounds:
    ```cpp
    int smoothed = sensors[sensorIndex].smoothedValue;

    if (smoothed < sensors[sensorIndex].minValue) {
      sensors[sensorIndex].minValue = smoothed;
    }
    if (smoothed > sensors[sensorIndex].maxValue) {
      sensors[sensorIndex].maxValue = smoothed;
    }
    ```
  - **Status**: Instant expansion implemented

- [ ] **Task 5.3**: Implement exponential decay (TRD api-signal-processing.md §6.3, R13)
  - Apply decay every 150 samples:
    ```cpp
    sensors[sensorIndex].samplesSinceDecay++;

    if (sensors[sensorIndex].samplesSinceDecay >= BASELINE_DECAY_INTERVAL) {
      sensors[sensorIndex].minValue +=
        (smoothed - sensors[sensorIndex].minValue) * BASELINE_DECAY_RATE;
      sensors[sensorIndex].maxValue -=
        (sensors[sensorIndex].maxValue - smoothed) * BASELINE_DECAY_RATE;
      sensors[sensorIndex].samplesSinceDecay = 0;
    }
    ```
  - **Status**: Exponential decay implemented

- [ ] **Task 5.4**: Implement range check for disconnection/reconnection (TRD api-signal-processing.md §6.3, R14)
  - Mark disconnected if range too small, reconnected if range increases:
    ```cpp
    int range = sensors[sensorIndex].maxValue - sensors[sensorIndex].minValue;
    if (range < MIN_SIGNAL_RANGE) {
      if (sensors[sensorIndex].isConnected) {
        #if DEBUG_LEVEL >= 1
          Serial.print("[");
          Serial.print(sensorIndex);
          Serial.println("] Signal range too small, disconnected");
        #endif
      }
      sensors[sensorIndex].isConnected = false;
    } else {
      // Reconnection: range increased above threshold
      if (!sensors[sensorIndex].isConnected) {
        #if DEBUG_LEVEL >= 1
          Serial.print("[");
          Serial.print(sensorIndex);
          Serial.println("] Sensor reconnected");
        #endif
        sensors[sensorIndex].isConnected = true;
        sensors[sensorIndex].firstBeatDetected = false;  // Reset for new connection
      }
    }
    ```
  - Compile: `pio run`
  - **Status**: Baseline tracking complete

## Component 9.6: Beat Detection Function

- [ ] **Task 6.1**: Implement detectBeat() signature and disconnection check (TRD api-beat-detection.md §6.4, R15)
  - Add function with early return:
    ```cpp
    void detectBeat(int sensorIndex) {
      if (!sensors[sensorIndex].isConnected) {
        return;  // Skip if disconnected
      }
      // Implementation will go here
    }
    ```
  - **Status**: Function signature created

- [ ] **Task 6.2**: Implement threshold calculation (TRD api-beat-detection.md §6.4, R16)
  - Calculate adaptive threshold:
    ```cpp
    int threshold = sensors[sensorIndex].minValue +
      (sensors[sensorIndex].maxValue - sensors[sensorIndex].minValue) * THRESHOLD_FRACTION;
    ```
  - **Status**: Threshold calculation implemented

- [ ] **Task 6.3**: Implement rising edge detection (TRD api-beat-detection.md §6.4, R17)
  - Detect signal crossing threshold:
    ```cpp
    bool currentlyAbove = (sensors[sensorIndex].smoothedValue >= threshold);

    if (currentlyAbove && !sensors[sensorIndex].aboveThreshold) {
      // Rising edge detected - check refractory period
      unsigned long now = millis();
      unsigned long timeSinceLastBeat = now - sensors[sensorIndex].lastBeatTime;

      if (timeSinceLastBeat < REFRACTORY_PERIOD_MS) {
        sensors[sensorIndex].aboveThreshold = currentlyAbove;
        return;  // Too soon, ignore
      }

      // Beat detected logic will go here
    }

    sensors[sensorIndex].aboveThreshold = currentlyAbove;
    ```
  - **Status**: Rising edge and refractory check implemented

- [ ] **Task 6.4**: Implement IBI calculation and first beat handling (TRD api-beat-detection.md §6.4, R19)
  - Calculate IBI and handle first/subsequent beats:
    ```cpp
    // Inside rising edge block after refractory check:
    unsigned long now = millis();
    unsigned long ibi = now - sensors[sensorIndex].lastBeatTime;

    if (sensors[sensorIndex].firstBeatDetected) {
      // Subsequent beat: send OSC
      sendHeartbeatOSC(sensorIndex, (int)ibi);
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
      // First beat: just record time
      sensors[sensorIndex].firstBeatDetected = true;

      #if DEBUG_LEVEL >= 1
        Serial.print("[");
        Serial.print(sensorIndex);
        Serial.print("] First beat at ");
        Serial.print(now);
        Serial.println("ms (no message sent)");
      #endif
    }

    sensors[sensorIndex].lastBeatTime = now;
    sensors[sensorIndex].lastIBI = ibi;
    ```
  - Compile: `pio run`
  - **Status**: Beat detection complete

## Component 9.7: OSC Messaging Function

- [ ] **Task 7.1**: Implement sendHeartbeatOSC() signature (TRD api-messaging.md §6.5)
  - Add function skeleton:
    ```cpp
    void sendHeartbeatOSC(int sensorIndex, int ibi_ms) {
      // Implementation will go here
    }
    ```
  - **Status**: Function signature created

- [ ] **Task 7.2**: Implement OSC address pattern construction (TRD api-messaging.md §6.5, R20)
  - Format address with sensor index:
    ```cpp
    char oscAddress[20];
    snprintf(oscAddress, sizeof(oscAddress), "/heartbeat/%d", sensorIndex);
    ```
  - **Status**: Address pattern implemented

- [ ] **Task 7.3**: Implement OSC message construction and transmission (TRD api-messaging.md §6.5, R21-R22)
  - Build and send OSC message:
    ```cpp
    OSCMessage msg(oscAddress);
    msg.add((int32_t)ibi_ms);

    udp.beginPacket(SERVER_IP, SERVER_PORT);
    msg.send(udp);
    udp.endPacket();
    msg.empty();

    #if DEBUG_LEVEL >= 2
      Serial.print("Sent OSC: ");
      Serial.print(oscAddress);
      Serial.print(" ");
      Serial.println(ibi_ms);
    #endif
    ```
  - Compile: `pio run`
  - **Status**: OSC messaging complete

## Component 9.8: LED Status & WiFi Functions

- [ ] **Task 8.1**: Implement updateLED() function (TRD api-status.md §6.6, R24-R25)
  - Add LED control logic:
    ```cpp
    void updateLED() {
      static unsigned long ledPulseTime = 0;
      const int LED_PULSE_DURATION = 50;

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
        // Solid on when connected
        digitalWrite(STATUS_LED_PIN, HIGH);
      }

      system.beatDetectedThisLoop = false;
    }
    ```
  - **Status**: LED status function implemented

- [ ] **Task 8.2**: Copy WiFi functions from Phase 1 (TRD api-network.md §6.7)
  - Source file: `/home/user/corazonn/firmware/heartbeat_phase1/src/main.cpp`
  - Copy `connectWiFi()` function (no modifications needed)
  - Copy `checkWiFi()` function (no modifications needed)
  - Verify both functions compile: `pio run`
  - Verify signatures match Phase 3 function declarations (Task 2.4)
  - **Status**: WiFi functions reused from Phase 1 (tested in Component 7)

## Component 9.9: Main Program Flow

- [ ] **Task 9.1**: Implement setup() - Serial and banner (TRD implementation.md §7.1, R26)
  - Add serial initialization and startup banner:
    ```cpp
    void setup() {
      Serial.begin(115200);
      delay(100);
      Serial.println("\n=== Heartbeat Installation - Phase 3 ===");
      Serial.println("Multi-Sensor Beat Detection");
    }
    ```
  - **Status**: Serial and banner implemented

- [ ] **Task 9.2**: Implement setup() - GPIO and ADC configuration (TRD implementation.md §7.1, R27)
  - Configure LED and ADC settings:
    ```cpp
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);

    analogReadResolution(ADC_RESOLUTION);
    analogSetAttenuation(ADC_11db);
    ```
  - **Status**: GPIO and ADC configured

- [ ] **Task 9.3**: Implement setup() - Sensor initialization loop (TRD implementation.md §7.1, R28)
  - Initialize all 4 sensors:
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
  - **Status**: Sensor initialization integrated

- [ ] **Task 9.4**: Implement setup() - WiFi and UDP initialization (TRD implementation.md §7.1, R29-R30)
  - Connect WiFi and start UDP:
    ```cpp
    system.wifiConnected = connectWiFi();
    if (!system.wifiConnected) {
      Serial.println("ERROR: WiFi connection failed");
      while (true) {
        digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
        delay(100);
      }
    }

    udp.begin(0);  // Any available port

    Serial.println("Setup complete. Starting multi-sensor detection...");
    ```
  - Compile: `pio run`
  - **Status**: setup() function complete

- [ ] **Task 9.5**: Implement loop() - Timing and sensor processing (TRD implementation.md §7.2, R32-R33)
  - Add loop structure with 50Hz timing:
    ```cpp
    void loop() {
      static unsigned long lastSampleTime = 0;
      unsigned long currentTime = millis();

      if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
        lastSampleTime = currentTime;
        system.beatDetectedThisLoop = false;

        for (int i = 0; i < NUM_SENSORS; i++) {
          readAndFilterSensor(i);
          updateBaseline(i);
          detectBeat(i);
        }

        updateLED();

        #if DEBUG_LEVEL >= 2
          if (system.loopCounter % 5 == 0) {
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

      checkWiFi();
      delay(1);
    }
    ```
  - Compile: `pio run`
  - **Status**: loop() function complete

## Component 9.10: Compilation & Initial Testing

- [ ] **Task 10.1**: Compile Phase 3 firmware (TRD implementation.md §9.1)
  - Run: `cd /home/user/corazonn/firmware/heartbeat_phase3 && pio run`
  - **Expected**: Compilation succeeds without errors
  - **Expected**: Binary size < 500KB, RAM usage < 10KB
  - Resolve any compilation errors
  - **Status**: Firmware compiles successfully

- [ ] **Task 10.2**: Configure WiFi credentials and server IP (TRD implementation.md §9.2)
  - Edit main.cpp:
    - Set WIFI_SSID to match development WiFi network (2.4GHz)
    - Set WIFI_PASSWORD with correct password
    - Find development machine IP: `ip addr show` or `ifconfig`
    - Set SERVER_IP to development machine IP (NOT 127.0.0.1)
  - **Status**: Network configuration matches environment

- [ ] **Task 10.3**: Upload Phase 3 firmware (TRD implementation.md §9.4)
  - Ensure all 4 PulseSensors connected to GPIO 32-35
  - Run: `pio run --target upload`
  - **Expected**: Upload completes, "Hard resetting via RTS pin..."
  - **Status**: Phase 3 firmware uploaded

- [ ] **Task 10.4**: Verify startup sequence (TRD operations.md §10.1)
  - Open serial monitor: `pio device monitor`
  - **Expected serial output**:
    ```
    === Heartbeat Installation - Phase 3 ===
    Multi-Sensor Beat Detection
    Initialized sensor 0 on GPIO 32
    Initialized sensor 1 on GPIO 33
    Initialized sensor 2 on GPIO 34
    Initialized sensor 3 on GPIO 35
    Connecting to WiFi: heartbeat-install
    Connected! IP: 192.168.X.X
    Setup complete. Starting multi-sensor detection...
    ```
  - Verify all initialization messages appear
  - **Status**: Startup sequence validated

## Component 9.11: Single-Sensor Smoke Test

- [ ] **Task 11.1**: Set DEBUG_LEVEL to 2 for verbose testing (TRD operations.md §10.1)
  - Edit main.cpp: Set `#define DEBUG_LEVEL 2`
  - Recompile and upload: `pio run --target upload && pio device monitor`
  - **Status**: Verbose debug enabled

- [ ] **Task 11.2**: Start Python OSC receiver (TRD operations.md §10.1)
  - Terminal 1: `python3 testing/osc_receiver.py --port 8000`
  - Verify receiver starts and listens on port 8000
  - **Status**: Receiver running

- [ ] **Task 11.3**: Test Sensor 0 beat detection (TRD operations.md §10.1)
  - Place one finger on Sensor 0 (GPIO 32)
  - Apply gentle, steady pressure
  - Hold still for 10 seconds
  - **Expected serial output**:
    ```
    [0]=2456 [1]=2391 [2]=0 [3]=2678
    [0]=2467 [1]=2401 [2]=0 [3]=2689
    [0] First beat at 3421ms (no message sent)
    [0]=2489 [1]=2423 [2]=0 [3]=2701
    [0] Beat at 4287ms, IBI=866ms
    Sent OSC: /heartbeat/0 866
    ```
  - **Expected receiver output**:
    ```
    [/heartbeat/0] IBI: 866ms, BPM: 69.2
    [/heartbeat/0] IBI: 869ms, BPM: 69.0
    ```
  - Verify first beat detected within 3 seconds
  - Verify subsequent beats appear regularly
  - Verify IBI values realistic (600-1200ms = 50-100 BPM)
  - **Status**: Sensor 0 beat detection working

- [ ] **Task 11.4**: Verify other sensors show no false positives (TRD operations.md §10.2)
  - Keep finger on Sensor 0 only
  - Observe serial output for Sensors 1, 2, 3
  - **Expected**: No beat messages from sensors 1-3
  - **Expected**: Sensor 1-3 values show steady baseline (no pulsing)
  - **Status**: No crosstalk confirmed

- [ ] **Task 11.5**: Verify LED beat pulse (TRD operations.md §10.1)
  - Observe built-in LED during Sensor 0 beats
  - **Expected**: Brief flicker on each beat (50ms pulse)
  - **Status**: LED visual feedback working

## Component 9.12: Single-Person Multi-Sensor Test

- [ ] **Task 12.1**: Set DEBUG_LEVEL to 1 for testing (TRD operations.md §10.2)
  - Edit main.cpp: Set `#define DEBUG_LEVEL 1`
  - Recompile and upload: `pio run --target upload && pio device monitor`
  - **Status**: Testing debug level enabled

- [ ] **Task 12.2**: Test each sensor independently (TRD operations.md §10.2)
  - Place finger on Sensor 0 for 10 seconds, observe beats
  - Move to Sensor 1 for 10 seconds, observe beats
  - Move to Sensor 2 for 10 seconds, observe beats
  - Move to Sensor 3 for 10 seconds, observe beats
  - **Expected**: Only active sensor sends messages
  - **Expected**: Inactive sensors silent (no false positives)
  - **Expected**: BPM consistent across all sensors (±5 BPM)
  - **Status**: Each sensor detects beats independently

- [ ] **Task 12.3**: Verify disconnection detection (TRD operations.md §10.4)
  - Place finger on Sensor 0, wait for beats
  - Remove finger, wait 2 seconds
  - **Expected serial output**:
    ```
    [0] Beat at 12847ms, IBI=856ms
    [0] Beat at 13703ms, IBI=856ms
    [0] Sensor disconnected
    ```
  - Receiver shows no new messages
  - LED stays solid ON (WiFi still connected)
  - **Status**: Disconnection detection working

- [ ] **Task 12.4**: Verify reconnection handling (TRD operations.md §10.4)
  - Reapply finger to Sensor 0
  - **Expected serial output within 3 seconds**:
    ```
    [0] Sensor reconnected
    [0] First beat at 16421ms (no message sent)
    [0] Beat at 17289ms, IBI=868ms
    ```
  - Receiver shows messages resume
  - **Status**: Reconnection handling working

## Component 9.13: Multi-Person Concurrent Test

- [ ] **Task 13.1**: Prepare multi-person test setup (TRD operations.md §10.3)
  - Verify DEBUG_LEVEL = 1 (testing mode)
  - Verify Python receiver running on port 8000
  - Arrange 2-4 people for concurrent testing
  - Assign each person to specific sensor (0-3)
  - **Status**: Multi-person test setup ready

- [ ] **Task 13.2**: Run multi-person concurrent test (TRD operations.md §10.3)
  - 2-4 people each place finger on different sensor simultaneously
  - Run for 5 minutes continuously
  - **Expected serial output** (interleaved):
    ```
    [0] Beat at 3421ms, IBI=866ms
    [2] Beat at 3678ms, IBI=742ms
    [1] Beat at 3891ms, IBI=923ms
    [0] Beat at 4287ms, IBI=866ms
    [3] Beat at 4432ms, IBI=678ms
    [2] Beat at 4501ms, IBI=823ms
    ```
  - **Expected receiver output** (interleaved):
    ```
    [/heartbeat/0] IBI: 866ms, BPM: 69.4
    [/heartbeat/2] IBI: 742ms, BPM: 80.9
    [/heartbeat/1] IBI: 923ms, BPM: 65.0
    [/heartbeat/0] IBI: 866ms, BPM: 69.4
    [/heartbeat/3] IBI: 678ms, BPM: 88.5
    ```
  - **Status**: Multi-person concurrent operation validated

- [ ] **Task 13.3**: Verify concurrent operation criteria (TRD operations.md §10.3)
  - ✅ All active sensors send messages
  - ✅ Messages interleaved (independent timing)
  - ✅ BPM values reasonable for all people (30-200 BPM)
  - ✅ No missed beats (no gaps > 2 seconds per sensor)
  - ✅ LED blinks on beats from ANY sensor
  - ✅ No crashes or errors over 5 minutes
  - **Status**: Concurrent operation criteria met

## Component 9.14: Extended Duration & BPM Accuracy

- [ ] **Task 14.1**: Run 30-minute stability test (TRD operations.md §10.5)
  - Set DEBUG_LEVEL = 0 (production mode, minimal output)
  - Recompile and upload: `pio run --target upload`
  - Start receiver: `python3 testing/osc_receiver.py --port 8000`
  - 2-4 people on sensors continuously for 30+ minutes
  - **Check for**:
    - No crashes or ESP32 resets
    - Consistent BPM (±10 BPM variation normal)
    - No WiFi disconnections (or auto-reconnects if drops)
    - No false disconnection alarms
    - Receiver shows continuous message stream
  - **Status**: 30-minute stability test passed

- [ ] **Task 14.2**: BPM accuracy validation against smartphone (TRD operations.md §10.6)
  - Install heart rate app on smartphone (e.g., "Instant Heart Rate")
  - Simultaneously measure:
    - Smartphone camera finger sensor
    - ESP32 Sensor 0 (different finger on same person)
  - Run for 1 minute, compare average BPM
  - **Acceptance criteria**: ±5 BPM difference
  - If outside range:
    - Missed beats (gaps > 2s): Decrease THRESHOLD_FRACTION to 0.5
    - False beats (BPM > 120 at rest): Increase THRESHOLD_FRACTION to 0.7
    - Retest after adjustment
  - **Status**: BPM accuracy within ±5 BPM

## Component 9.15: Acceptance Criteria Validation

- [ ] **Task 15.1**: Verify compilation and upload criteria (TRD operations.md §11.1)
  - ✅ Compiles without errors
  - ✅ Uploads successfully
  - ✅ Binary size < 500KB
  - ✅ RAM usage < 10KB
  - **Status**: Compilation criteria met

- [ ] **Task 15.2**: Verify single-sensor operation criteria (TRD operations.md §11.2)
  - ✅ Detects beats within 3 seconds of finger application
  - ✅ BPM accuracy ±5 BPM vs smartphone
  - ✅ First beat: no message sent (correct behavior)
  - ✅ Subsequent beats: IBI messages sent
  - ✅ Disconnection detected within 1 second
  - ✅ Reconnection detected within 3 seconds
  - **Status**: Single-sensor criteria met

- [ ] **Task 15.3**: Verify multi-sensor operation criteria (TRD operations.md §11.3)
  - ✅ All 4 sensors operate simultaneously
  - ✅ No crosstalk (inactive sensors silent)
  - ✅ Independent beat detection per sensor
  - ✅ LED responds to beats from ANY sensor
  - ✅ 2-4 person test successful
  - **Status**: Multi-sensor criteria met

- [ ] **Task 15.4**: Verify reliability criteria (TRD operations.md §11.4)
  - ✅ 30+ minute stability test passes
  - ✅ No crashes or watchdog resets
  - ✅ WiFi resilience (auto-reconnect if drops)
  - ✅ Consistent performance (no degradation)
  - **Status**: Reliability criteria met

- [ ] **Task 15.5**: Verify protocol validation criteria (TRD operations.md §11.5)
  - ✅ OSC messages format correct: `/heartbeat/[0-3] <int32>`
  - ✅ All messages received by Python receiver
  - ✅ 0 invalid messages over 30-minute test
  - ✅ Latency <25ms (beat to network transmission)
  - **Status**: Protocol criteria met

- [ ] **Task 15.6**: Final success metrics validation (TRD operations.md §14.1)
  - Verify all 12 Phase 3 completion criteria met:
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
  - **Status**: All success metrics met

## Component 9.16: Documentation & Completion

- [ ] **Task 16.1**: Update firmware README for Phase 3 (TRD operations.md §14.2)
  - Update `/home/user/corazonn/firmware/README.md`:
    - Add Phase 3 section with overview
    - Document 4-sensor hardware setup (GPIO 32-35 wiring)
    - Document multi-sensor architecture (independent state per sensor)
    - Document DEBUG_LEVEL meanings (0/1/2)
    - Document tuning parameters (THRESHOLD_FRACTION, MIN_SIGNAL_RANGE)
    - Document troubleshooting multi-sensor issues (crosstalk, false positives)
  - **Status**: README updated for Phase 3

- [ ] **Task 16.2**: Create Phase 3 deployment checklist
  - Add to README: "Phase 3 Pre-Deployment Checklist"
    - Hardware: 4× PulseSensors connected to GPIO 32-35, 3.3V, GND
    - Configuration: WIFI_SSID, WIFI_PASSWORD, SERVER_IP, DEBUG_LEVEL
    - Testing: Single-sensor smoke test, multi-person test, 30-minute stability
    - Validation: BPM accuracy vs smartphone, 0 invalid messages
    - Production: DEBUG_LEVEL 0 tested, LED feedback clear
  - **Status**: Deployment checklist documented

- [ ] **Task 16.3**: Document multi-sensor troubleshooting (TRD operations.md §13)
  - Create troubleshooting section in README:
    - No beats detected: Check finger contact, adjust THRESHOLD_FRACTION
    - False beats: Increase REFRACTORY_PERIOD_MS, reduce vibration
    - Crosstalk: Verify independent SensorState per sensor, check array indexing
    - Disconnection issues: Verify MIN_SIGNAL_RANGE, check ambient light
    - WiFi issues: Same as Phase 1 (SSID/password, 2.4GHz, SERVER_IP)
  - **Status**: Troubleshooting guide complete

- [ ] **Task 16.4**: Mark Phase 3 complete
  - Update `docs/tasks.md`: Mark Component 9 (Phase 3 Firmware) as complete
  - Commit all changes: `git add -A && git commit -m "Complete Phase 3 firmware implementation"`
  - Document completion date
  - **Status**: Phase 3 firmware implementation complete

---

## Task Execution Notes

**Order**: Tasks MUST be completed in sequence. Each task builds on previous work.

**Testing Strategy**:
- Tasks 0.x: Prerequisites validation (Phase 1 working, hardware connected)
- Tasks 1.x-2.x: Configuration and data structure setup (compile checks)
- Tasks 3.x-8.x: Function implementations (incremental with compile checks)
- Tasks 9.x: Main program flow (setup/loop implementation)
- Tasks 10.x: Compilation and initial upload
- Tasks 11.x: Single-sensor smoke test (validate one channel)
- Tasks 12.x: Single-person multi-sensor test (validate independence)
- Tasks 13.x: Multi-person concurrent test (validate scalability)
- Tasks 14.x: Extended duration and BPM accuracy validation
- Tasks 15.x: Acceptance criteria verification (all 12 criteria)
- Tasks 16.x: Documentation and completion

**Hardware Required**:
- 1× ESP32-WROOM-32 board
- 4× PulseSensor optical pulse sensors (new for Phase 3)
- USB cable for programming (data capable)
- Development machine with WiFi and PlatformIO CLI
- 2.4GHz WiFi network (same as Phase 1)
- 2-4 people for multi-person testing

**Dependencies**:
- Component 7 complete (Phase 1 firmware working)
- 4× PulseSensor hardware available
- Python OSC receiver tested (from Phase 1)

**Time Estimate**:
- Prerequisites (Tasks 0.x): 20-30 min (hardware connection, validation)
- Configuration (Tasks 1.x-2.x): 20-30 min (constants, data structures)
- Sensor functions (Tasks 3.x-5.x): 45-60 min (init, sampling, baseline)
- Beat detection (Tasks 6.x-7.x): 45-60 min (beat detection, OSC)
- LED & WiFi (Task 8.x): 15-20 min (status functions)
- Main program (Tasks 9.x): 30-40 min (setup/loop)
- Compilation & upload (Tasks 10.x): 15-20 min
- Single-sensor test (Tasks 11.x): 30-40 min
- Multi-sensor tests (Tasks 12.x-13.x): 60-90 min (includes multi-person coordination)
- Extended testing (Tasks 14.x): 45 min (30-min stability + BPM validation)
- Acceptance & docs (Tasks 15.x-16.x): 30-40 min
- **Total: 6-8 hours** (includes multi-person testing coordination)

**Acceptance**: Component 9 complete when:
- All tasks checked off
- All 4 sensors detect beats independently with ±5 BPM accuracy
- Multi-person test validates concurrent operation (2-4 people)
- OSC receiver validates all messages (0 invalid) over 30+ minutes
- All 12 TRD success metrics met

**Critical Implementation Notes**:
1. **Array Indexing** (All tasks): MUST pass sensorIndex to all functions, verify bounds 0-3
2. **Independent State** (Task 2.3): Each sensor has isolated SensorState, no global state sharing
3. **LED Feedback** (Task 8.1): LED responds to beats from ANY sensor via system.beatDetectedThisLoop
4. **Refractory Period** (Task 6.3): MUST check BEFORE updating aboveThreshold state
5. **First Beat** (Task 6.4): No OSC message sent on first beat (no reference IBI yet)
6. **Multi-Person Testing** (Task 13.x): Requires 2-4 people, coordinate scheduling

**Known Limitations** (documented in TRD operations.md §12):
- No waveform transmission (only IBI)
- Fixed threshold (not adaptive per user)
- 12-bit ADC (adequate but not clinical-grade)
- GPIO 34-35 input-only (no pullup/pulldown)
- Sensitive to ambient light and movement
