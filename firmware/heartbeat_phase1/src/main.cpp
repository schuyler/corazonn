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
#include "ssid.h"

// ============================================================================
// CONFIGURATION
// ============================================================================
// Network configuration (TRD Section 4.1)
// const char* WIFI_SSID = "heartbeat-install";
///const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 0, 79);  // CHANGE THIS
const uint16_t SERVER_PORT = 8000;

// Hardware configuration (TRD Section 4.2)
const int STATUS_LED_PIN = 2;  // Built-in LED on GPIO 2
const int SENSOR_PIN = 32;                 // Phase 2: GPIO 32 (ADC1_CH4)
const int ADC_RESOLUTION = 12;             // Phase 2: 12-bit (0-4095)

// Signal processing parameters (Phase 2 New, TRD §4.3)
const int SAMPLE_RATE_HZ = 50;             // 50 samples/second
const int SAMPLE_INTERVAL_MS = 20;         // 1000 / 50 = 20ms
const int MOVING_AVG_SAMPLES = 5;          // 100ms smoothing window (5 samples @ 50Hz)
const float BASELINE_DECAY_RATE = 0.1;     // 10% decay per interval
const int BASELINE_DECAY_INTERVAL = 150;   // Apply every 150 samples (3 seconds @ 50Hz)

// Beat detection parameters (Phase 2 New, TRD §4.4)
const float THRESHOLD_FRACTION = 0.6;              // 60% of signal range above baseline
const int MIN_SIGNAL_RANGE = 50;                   // Minimum ADC range for valid signal
const unsigned long REFRACTORY_PERIOD_MS = 300;    // 300ms = max 200 BPM
const int FLAT_SIGNAL_THRESHOLD = 5;               // ADC variance < 5 = flat
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;  // 1 second flat = disconnected

// System configuration (TRD Section 4.5)
const int SENSOR_ID = 0;  // CHANGE THIS: 0, 1, 2, or 3 for each unit
// const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;  // Phase 1 constant removed - Phase 2 uses event-driven OSC messages
const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 seconds

// ============================================================================
// GLOBAL STATE
// ============================================================================
// System state structure (TRD Section 5)
struct SystemState {
    bool wifiConnected;                // Current WiFi connection status (Phase 1 - keep)
    unsigned long lastWiFiCheckTime;   // Phase 2: For WiFi monitoring rate limit
    unsigned long loopCounter;         // Phase 2: For debug output throttling
    // REMOVE: unsigned long lastMessageTime;
    // REMOVE: uint32_t messageCounter;
};

// Sensor state structure (Phase 2 New, TRD Section 5.2)
struct SensorState {
    // Moving average filter
    int rawSamples[MOVING_AVG_SAMPLES];  // Circular buffer (5 samples)
    int sampleIndex;                      // Current position in buffer
    int smoothedValue;                    // Output of moving average

    // Baseline tracking
    int minValue;                         // Minimum, decays upward
    int maxValue;                         // Maximum, decays downward
    int samplesSinceDecay;                // Counter for decay interval

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

// Global objects (TRD Section 5.2)
WiFiUDP udp;                          // UDP socket for OSC (Phase 1 - keep)
SystemState state = {false, 0, 0};    // Phase 2: Updated initialization
SensorState sensor = {                 // Phase 2: New sensor state
    .rawSamples = {0},
    .sampleIndex = 0,
    .smoothedValue = 0,
    .minValue = 0,
    .maxValue = 4095,
    .samplesSinceDecay = 0,
    .aboveThreshold = false,
    .lastBeatTime = 0,
    .lastIBI = 0,
    .firstBeatDetected = false,
    .isConnected = false,
    .lastRawValue = 0,
    .flatSampleCount = 0
};
static unsigned long ledPulseTime = 0;  // Time when LED pulse started (for 50ms pulse)

// ============================================================================
// FUNCTION DECLARATIONS
// ============================================================================
// Phase 1 functions
bool connectWiFi();                   // TRD Section 6.1
void sendHeartbeatOSC(int ibi_ms);    // TRD Section 6.2
void updateLED();                     // TRD Section 6.3
void checkWiFi();                     // TRD Section 6.4

// Phase 2 functions (new)
void initializeSensor();              // Component 8.3: Sensor initialization
void updateMovingAverage(int rawValue);  // Component 8.4: Moving average filter
void updateBaseline();                // Component 8.5: Baseline tracking

// ============================================================================
// FUNCTION IMPLEMENTATIONS
// ============================================================================

/**
 * Connect to WiFi network with timeout
 * Returns: true if connected, false if timeout
 * TRD Section 6.1
 */
bool connectWiFi() {
    // R1: WiFi Initialization
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);

    unsigned long startTime = millis();

    // R2: Connection Wait Loop
    while (WiFi.status() != WL_CONNECTED) {
        if (millis() - startTime >= WIFI_TIMEOUT_MS) {
            // R4: Failure Behavior
            Serial.println("WiFi connection timeout");
            return false;
        }

        // Blink LED during connection (5 Hz = 100ms on/off)
        digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
        delay(100);
    }

    // R3: Success Behavior
    state.wifiConnected = true;
    digitalWrite(STATUS_LED_PIN, HIGH);  // Solid ON

    Serial.print("Connected! IP: ");
    Serial.println(WiFi.localIP());

    return true;
}

/**
 * Initialize sensor and ADC configuration
 * Component 8.3, TRD Section 6.1 (Phase 2)
 */
void initializeSensor() {
    // R1: ADC Configuration
    adcAttachPin(SENSOR_PIN);        // For per-pin configuration on some cores
    analogSetAttenuation(ADC_11db);
    analogReadResolution(12);

    // R2: Initial Reading
    int firstReading = analogRead(SENSOR_PIN);
    Serial.print("First ADC reading: ");
    Serial.println(firstReading);

    // R3: Pre-fill Moving Average Buffer
    for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
        sensor.rawSamples[i] = firstReading;
    }

    // R4: Baseline Initialization
    sensor.smoothedValue = firstReading;
    sensor.minValue = firstReading;
    sensor.maxValue = firstReading;

    // R5: Connection State
    sensor.isConnected = true;
    sensor.lastRawValue = firstReading;
    sensor.lastBeatTime = millis();  // Prevents false refractory rejection on first beat
}

/**
 * Send OSC heartbeat message
 * Parameters: ibi_ms - inter-beat interval in milliseconds
 * TRD Section 6.2
 */
void sendHeartbeatOSC(int ibi_ms) {
    // R5: Construct OSC address pattern
    char address[20];
    snprintf(address, sizeof(address), "/heartbeat/%d", SENSOR_ID);

    // R6: Create OSC message
    OSCMessage msg(address);
    msg.add((int32_t)ibi_ms);

    // R7: UDP transmission (critical order: beginPacket → send → endPacket → empty)
    udp.beginPacket(SERVER_IP, SERVER_PORT);
    msg.send(udp);
    udp.endPacket();
    msg.empty();
}

/**
 * Update moving average filter with new raw value
 * Component 8.4, TRD Section 6.2 (Phase 2)
 * Parameters: rawValue - new ADC reading
 */
void updateMovingAverage(int rawValue) {
    // R6: Circular Buffer Update
    sensor.rawSamples[sensor.sampleIndex] = rawValue;
    sensor.sampleIndex = (sensor.sampleIndex + 1) % MOVING_AVG_SAMPLES;

    // R7: Calculate Mean
    int sum = 0;
    for (int i = 0; i < MOVING_AVG_SAMPLES; i++) {
        sum += sensor.rawSamples[i];
    }
    sensor.smoothedValue = sum / MOVING_AVG_SAMPLES;
}

/**
 * Update LED state based on system status
 * TRD Section 6.3
 */
void updateLED() {
    // R10: State Determination
    if (!state.wifiConnected) {
        // R9: Blink at 5Hz while not connected
        // R11: Non-blocking LED control
        digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
    } else {
        // R9: Solid ON when connected
        digitalWrite(STATUS_LED_PIN, HIGH);
    }
}

/**
 * Update baseline tracking (min/max with decay)
 * Component 8.5, TRD Section 6.3 (Phase 2)
 */
void updateBaseline() {
    // Use references for cleaner code
    int& smoothedValue = sensor.smoothedValue;
    int& minValue = sensor.minValue;
    int& maxValue = sensor.maxValue;
    int& samplesSinceDecay = sensor.samplesSinceDecay;

    // R9: Instant Expansion
    if (smoothedValue < minValue) {
        minValue = smoothedValue;
    }
    if (smoothedValue > maxValue) {
        maxValue = smoothedValue;
    }

    // R10: Periodic Decay
    samplesSinceDecay++;
    if (samplesSinceDecay >= BASELINE_DECAY_INTERVAL) {
        minValue += (int)((smoothedValue - minValue) * BASELINE_DECAY_RATE);
        maxValue -= (int)((maxValue - smoothedValue) * BASELINE_DECAY_RATE);
        samplesSinceDecay = 0;
    }
}

/**
 * Monitor WiFi connection and attempt reconnection if needed
 * TRD Section 6.4
 */
void checkWiFi() {
    // R14: Rate limit to every 5 seconds (initialized to 0 for immediate first check)
    static unsigned long lastCheckTime = 0;

    if (millis() - lastCheckTime < 5000) {
        return;  // Check at most every 5 seconds
    }

    lastCheckTime = millis();

    // R12: Status Check
    if (WiFi.status() != WL_CONNECTED) {
        // R13: Reconnection Logic
        state.wifiConnected = false;
        Serial.println("WiFi disconnected, reconnecting...");
        WiFi.reconnect();  // Non-blocking
    } else {
        state.wifiConnected = true;
    }
}

// ============================================================================
// ARDUINO CORE
// ============================================================================

/**
 * Arduino setup function - runs once on boot
 * TRD Section 7.1
 */
void setup() {
    // R15: Serial Initialization
    Serial.begin(115200);
    delay(100);

    // R16: Startup Banner
    Serial.println("\n=== Heartbeat Installation - Phase 2 ===");
    Serial.println("Real Heartbeat Detection");
    Serial.print("Sensor ID: ");
    Serial.println(SENSOR_ID);

    // R17: GPIO Configuration
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);

    // R18: WiFi Connection
    state.wifiConnected = connectWiFi();

    if (!state.wifiConnected) {
        Serial.println("ERROR: WiFi connection failed");
        Serial.print("WiFi status code: ");
        Serial.println(WiFi.status());
        Serial.println("Possible causes:");
        Serial.println("  - Wrong SSID or password");
        Serial.println("  - Network is 5GHz (ESP32 requires 2.4GHz)");
        Serial.println("  - Out of range");
        Serial.println("  - Router offline");
        Serial.println("Entering error state (rapid blink)...");

        // Enter error state: blink rapidly forever
        while (true) {
            digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
            delay(100);
        }
    }

    // R19: UDP Initialization
    udp.begin(0);  // Ephemeral port

    // Phase 2: Sensor Initialization
    initializeSensor();

    // R20: Completion Message
    Serial.println("Setup complete. Place finger on sensor to begin.");
}

/**
 * Arduino loop function - runs continuously
 * TRD Section 7.2
 */
void loop() {
    // R21: WiFi status monitoring
    checkWiFi();

    // Phase 1 test message code temporarily disabled - will be replaced with Phase 2 sampling in Component 8.9
    /*
    // R22: Message timing check
    unsigned long currentTime = millis();

    if (currentTime - state.lastMessageTime >= TEST_MESSAGE_INTERVAL_MS) {
        // R23: Generate test IBI value (800-999ms sequence)
        int test_ibi = 800 + (state.messageCounter % 200);

        // R24: Send OSC message
        sendHeartbeatOSC(test_ibi);

        // R24: Update state
        state.lastMessageTime = currentTime;
        state.messageCounter++;

        // R25: Serial feedback
        Serial.print("Sent message #");
        Serial.print(state.messageCounter);
        Serial.print(": /heartbeat/");
        Serial.print(SENSOR_ID);
        Serial.print(" ");
        Serial.println(test_ibi);
    }
    */

    // R26: LED update
    updateLED();

    // R27: Loop delay
    delay(10);
}
