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

// ============================================================================
// CONFIGURATION
// ============================================================================
// Network configuration (TRD Section 4.1)
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
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
    // Implementation in Part 3
    return false;
}

/**
 * Send OSC heartbeat message
 * Parameters: ibi_ms - inter-beat interval in milliseconds
 * TRD Section 6.2
 */
void sendHeartbeatOSC(int ibi_ms) {
    // Implementation in Part 4
}

/**
 * Update LED state based on system status
 * TRD Section 6.3
 */
void updateLED() {
    // Implementation in Part 3
}

/**
 * Monitor WiFi connection and attempt reconnection if needed
 * TRD Section 6.4
 */
void checkWiFi() {
    // Implementation in Part 3
}

// ============================================================================
// ARDUINO CORE
// ============================================================================

/**
 * Arduino setup function - runs once on boot
 * TRD Section 7.1
 */
void setup() {
    Serial.begin(115200);
    delay(100);

    Serial.println("\n=== Heartbeat Installation - Phase 1 ===");
    Serial.print("Sensor ID: ");
    Serial.println(SENSOR_ID);

    // GPIO configuration
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);

    Serial.println("Skeleton firmware loaded - awaiting implementation");
}

/**
 * Arduino loop function - runs continuously
 * TRD Section 7.2
 */
void loop() {
    // Implementation in Parts 3-4
    delay(1000);  // Prevent watchdog timeout
}
