/**
 * Heartbeat Installation - Phase 1: WiFi + OSC
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
const IPAddress SERVER_IP(192, 168, 50, 100);  // CHANGE THIS
const uint16_t SERVER_PORT = 8000;

// Hardware configuration (TRD Section 4.2)
const int STATUS_LED_PIN = 2;  // Built-in LED on GPIO 2

// System configuration (TRD Section 4.3)
const int SENSOR_ID = 0;  // CHANGE THIS: 0, 1, 2, or 3 for each unit
const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;  // 1 second
const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 seconds

// ============================================================================
// GLOBAL STATE
// ============================================================================
// System state structure (TRD Section 5)
struct SystemState {
    bool wifiConnected;           // Current WiFi connection status
    unsigned long lastMessageTime;  // millis() of last message sent
    uint32_t messageCounter;      // Total messages sent
};

// Global objects (TRD Section 5.2)
WiFiUDP udp;                          // UDP socket for OSC
SystemState state = {false, 0, 0};    // System state (initial values)

// ============================================================================
// FUNCTION DECLARATIONS
// ============================================================================
bool connectWiFi();                   // TRD Section 6.1
void sendHeartbeatOSC(int ibi_ms);    // TRD Section 6.2
void updateLED();                     // TRD Section 6.3
void checkWiFi();                     // TRD Section 6.4

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
    Serial.println("\n=== Heartbeat Installation - Phase 1 ===");
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

    // R20: Completion Message
    Serial.println("Setup complete. Starting message loop...");
    state.lastMessageTime = millis();
}

/**
 * Arduino loop function - runs continuously
 * TRD Section 7.2
 */
void loop() {
    // R21: WiFi status monitoring
    checkWiFi();

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

    // R26: LED update
    updateLED();

    // R27: Loop delay
    delay(10);
}
