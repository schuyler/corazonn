#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCMessage.h>
#include "../include/config.h"

// ============================================================================
// Constants (from config.h via macros)
// ============================================================================

// See include/config.h for timing constants
// SAMPLE_RATE_HZ, SAMPLE_INTERVAL_MS, BUNDLE_SIZE, BUNDLE_INTERVAL_MS, WIFI_RECONNECT_INTERVAL_MS

// ============================================================================
// Global State
// ============================================================================

struct {
  bool wifiConnected;
  uint16_t sampleBuffer[BUNDLE_SIZE];
  int bufferIndex;
  unsigned long bundleStartTime;
} state = {
  .wifiConnected = false,
  .bufferIndex = 0,
  .bundleStartTime = 0
};

// Networking
IPAddress serverIP;
WiFiUDP udp;

// Timing
unsigned long lastSampleTime = 0;
unsigned long lastWiFiCheckTime = 0;
unsigned long lastLEDBlinkTime = 0;

// LED
bool ledState = false;

// ============================================================================
// Function Declarations
// ============================================================================

void setupADC();
void setupLED();
void setupWiFi();
void checkWiFi();
void updateLED();
void samplePPG();
void sendPPGBundle();

// ============================================================================
// Setup
// ============================================================================

void setup() {
  // Serial for debugging
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\nAmor ESP32 Firmware - Starting");
  Serial.print("PPG ID: ");
  Serial.println(PPG_ID);
  Serial.print("PPG GPIO: ");
  Serial.println(PPG_GPIO);
  Serial.print("Server: ");
  Serial.print(SERVER_IP);
  Serial.print(":");
  Serial.println(SERVER_PORT);

  // Initialize components
  setupLED();
  setupADC();
  setupWiFi();

  Serial.println("Setup complete");
}

// ============================================================================
// Setup Functions
// ============================================================================

void setupLED() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);  // Off initially
}

void setupADC() {
  // Configure ADC for PPG sensor
  analogSetAttenuation(ADC_11db);
  analogReadResolution(12);
  adcAttachPin(PPG_GPIO);

  Serial.println("ADC configured: 12-bit, 0-4095 range");
}

void setupWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // Parse server IP
  serverIP.fromString(SERVER_IP);

  // Wait for initial connection (max 10 seconds)
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    state.wifiConnected = true;
    Serial.println("\nWiFi connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());

    // Start UDP
    if (udp.begin(0)) {
      Serial.println("UDP initialized");
    }
  } else {
    Serial.println("\nWiFi connection failed, will retry");
    state.wifiConnected = false;
  }

  lastWiFiCheckTime = millis();
}

// ============================================================================
// WiFi Management
// ============================================================================

void checkWiFi() {
  unsigned long currentTime = millis();

  // Check WiFi status every 5 seconds
  if (currentTime - lastWiFiCheckTime >= WIFI_RECONNECT_INTERVAL_MS) {
    lastWiFiCheckTime = currentTime;

    bool previousState = state.wifiConnected;
    state.wifiConnected = (WiFi.status() == WL_CONNECTED);

    if (!state.wifiConnected && previousState) {
      Serial.println("WiFi disconnected, attempting to reconnect...");
      WiFi.reconnect();
    } else if (state.wifiConnected && !previousState) {
      Serial.println("WiFi reconnected!");
      Serial.print("IP: ");
      Serial.println(WiFi.localIP());

      // Re-initialize UDP socket after reconnection
      if (udp.begin(0)) {
        Serial.println("UDP re-initialized");
      }
    }
  }
}

// ============================================================================
// LED Feedback
// ============================================================================

void updateLED() {
  unsigned long currentTime = millis();

  if (state.wifiConnected) {
    // WiFi connected: solid LED (on)
    digitalWrite(LED_PIN, HIGH);
  } else {
    // WiFi disconnected or connecting: blink slowly (1 Hz)
    if (currentTime - lastLEDBlinkTime >= 500) {
      lastLEDBlinkTime = currentTime;
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState ? HIGH : LOW);
    }
  }
}

// ============================================================================
// PPG Sampling
// ============================================================================

void samplePPG() {
  unsigned long currentTime = millis();

  // Sample at 50Hz (20ms intervals)
  if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = currentTime;

    // Record bundle start time on first sample
    if (state.bufferIndex == 0) {
      state.bundleStartTime = currentTime;
    }

    // Read ADC value (0-4095)
    uint16_t sample = analogRead(PPG_GPIO);
    state.sampleBuffer[state.bufferIndex++] = sample;

    // Send bundle when full
    if (state.bufferIndex >= BUNDLE_SIZE) {
      sendPPGBundle();
      state.bufferIndex = 0;
    }
  }
}

// ============================================================================
// OSC Transmission
// ============================================================================

void sendPPGBundle() {
  // Only send if WiFi is connected
  if (!state.wifiConnected) {
    return;
  }

  // Construct OSC address: /ppg/{ppg_id}
  char address[20];
  snprintf(address, sizeof(address), "/ppg/%d", PPG_ID);

  // Create OSC message
  OSCMessage msg(address);

  // Add samples
  for (int i = 0; i < BUNDLE_SIZE; i++) {
    msg.add((int32_t)state.sampleBuffer[i]);
  }

  // Add timestamp (millis when first sample taken)
  msg.add((int32_t)state.bundleStartTime);

  // Send via UDP
  udp.beginPacket(serverIP, SERVER_PORT);
  msg.send(udp);
  udp.endPacket();

  // CRITICAL: Clear message to avoid memory leak
  msg.empty();
}

// ============================================================================
// Main Loop
// ============================================================================

void loop() {
  unsigned long currentTime = millis();

  // Sample PPG at 50Hz (non-blocking)
  samplePPG();

  // Check WiFi status every 5 seconds
  checkWiFi();

  // Update LED feedback
  updateLED();

  // Small delay to prevent watchdog issues
  delayMicroseconds(100);
}
