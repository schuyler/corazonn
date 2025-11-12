#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCMessage.h>
#include <math.h>
#include <esp_task_wdt.h>
#include "../include/config.h"

// Watchdog timeout in seconds
#define WDT_TIMEOUT 30

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
  uint32_t bundlesSent;
  uint16_t adcRingBuffer[50];
  int adcRingIndex;
  int sampleCount;  // Track actual samples in ring buffer (max 50)
} state = {
  .wifiConnected = false,
  .bufferIndex = 0,
  .bundleStartTime = 0,
  .bundlesSent = 0,
  .adcRingIndex = 0,
  .sampleCount = 0
};

// Networking
IPAddress serverIP;
WiFiUDP udp;

// Timing
unsigned long lastSampleTime = 0;
unsigned long lastWiFiAdminCheckTime = 0;
unsigned long lastWatchdogResetTime = 0;
unsigned long lastLEDBlinkTime = 0;
unsigned long lastStatsTime = 0;
unsigned long bootTime = 0;

// LED
bool ledState = false;

// ============================================================================
// Function Declarations
// ============================================================================

void setupADC();
void setupLED();
void setupWiFi();
void checkWiFi();
void checkOSCMessages();
void handleRestartCommand();
void updateLED();
void samplePPG();
void sendPPGBundle();
void printStats();

// ============================================================================
// Setup
// ============================================================================

void setup() {
  // Serial for debugging
  Serial.begin(115200);
  delay(1000);

  // Capture boot time for uptime calculation
  bootTime = millis();

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

  // Initialize watchdog timer
  Serial.print("Initializing watchdog timer (");
  Serial.print(WDT_TIMEOUT);
  Serial.println("s timeout)");
  esp_task_wdt_init(WDT_TIMEOUT, true);  // Enable panic on timeout
  esp_task_wdt_add(NULL);  // Add current task to watchdog

  Serial.println("Setup complete");

  // Initialize stats timer
  lastStatsTime = millis();
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

    // Start UDP for sending PPG data and receiving admin commands
    if (udp.begin(ADMIN_PORT)) {
      Serial.print("UDP initialized on port ");
      Serial.println(ADMIN_PORT);
    }
  } else {
    Serial.println("\nWiFi connection failed, will retry");
    state.wifiConnected = false;
  }

  lastWiFiAdminCheckTime = millis();
}

// ============================================================================
// WiFi Management
// ============================================================================

void checkWiFi() {
  bool previousState = state.wifiConnected;
  state.wifiConnected = (WiFi.status() == WL_CONNECTED);

  if (!state.wifiConnected) {
    if (previousState) {
      Serial.println("WiFi disconnected, attempting to reconnect...");
    }
    WiFi.reconnect();  // Always try, not just on transitions
  } else if (state.wifiConnected && !previousState) {
    Serial.println("WiFi reconnected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());

    // Re-initialize UDP socket after reconnection
    if (udp.begin(ADMIN_PORT)) {
      Serial.print("UDP re-initialized on port ");
      Serial.println(ADMIN_PORT);
    }
  }
}

// ============================================================================
// OSC Admin Commands
// ============================================================================

void checkOSCMessages() {
  // Check for incoming OSC messages on ADMIN_PORT
  int packetSize = udp.parsePacket();

  if (packetSize > 0) {
    OSCMessage msg;

    // Read the packet into the OSC message
    while (packetSize--) {
      msg.fill(udp.read());
    }

    // Check if this is a restart command
    if (msg.fullMatch("/restart")) {
      handleRestartCommand();
    }

    // Clear message to avoid memory leak
    msg.empty();
  }
}

void handleRestartCommand() {
  Serial.println("Restart request received via OSC");
  Serial.println("Rebooting ESP32...");
  Serial.flush();  // Ensure message is sent before restart

  delay(100);  // Brief delay to allow serial output
  ESP.restart();
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

    // Add sample to rolling statistics buffer
    state.adcRingBuffer[state.adcRingIndex] = sample;
    state.adcRingIndex = (state.adcRingIndex + 1) % 50;
    if (state.sampleCount < 50) {
      state.sampleCount++;
    }

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

  // Increment bundle counter
  state.bundlesSent++;
}

// ============================================================================
// Statistics
// ============================================================================

void printStats() {
  unsigned long currentTime = millis();
  unsigned long uptimeMs = (currentTime - bootTime);
  float uptimeSec = uptimeMs / 1000.0f;

  // Build single-line stats string
  char statsLine[256];
  char* pos = statsLine;
  int remaining = sizeof(statsLine);

  // Uptime [HH.Hs]
  int written = snprintf(pos, remaining, "[%.1fs] PPG_ID=%d", uptimeSec, PPG_ID);
  pos += written;
  remaining -= written;

  // WiFi status
  if (state.wifiConnected) {
    int rssi = WiFi.RSSI();
    written = snprintf(pos, remaining, " | WiFi: OK (%s, %ddBm)",
                       WiFi.localIP().toString().c_str(), rssi);
  } else {
    written = snprintf(pos, remaining, " | WiFi: DOWN");
  }
  pos += written;
  remaining -= written;

  // Bundles and samples
  uint32_t totalSamplesSent = state.bundlesSent * BUNDLE_SIZE;
  written = snprintf(pos, remaining, " | Sent: %lu bundles (%lu samples)",
                     state.bundlesSent, totalSamplesSent);
  pos += written;
  remaining -= written;

  // ADC Statistics (only if we have at least 10 samples)
  if (state.sampleCount >= 10) {
    uint32_t sum = 0;
    uint16_t minVal = 4095;
    uint16_t maxVal = 0;

    for (int i = 0; i < state.sampleCount; i++) {
      uint16_t val = state.adcRingBuffer[i];
      sum += val;
      if (val < minVal) minVal = val;
      if (val > maxVal) maxVal = val;
    }

    // Calculate mean
    uint16_t mean = sum / state.sampleCount;

    // Calculate standard deviation
    uint32_t sumSqDiff = 0;
    for (int i = 0; i < state.sampleCount; i++) {
      int32_t diff = (int32_t)state.adcRingBuffer[i] - (int32_t)mean;
      sumSqDiff += diff * diff;
    }
    uint16_t stddev = (uint16_t)sqrt((double)sumSqDiff / state.sampleCount);

    written = snprintf(pos, remaining, " | ADC: %u±%u (%u-%u)",
                       mean, stddev, minVal, maxVal);
    pos += written;
    remaining -= written;
  }

  // Message rate (bundles per second)
  float rate = (uptimeSec > 0) ? ((float)state.bundlesSent / uptimeSec) : 0.0f;
  written = snprintf(pos, remaining, " | Rate: %.1f msg/s", rate);
  pos += written;
  remaining -= written;

  // Print single line
  Serial.println(statsLine);
}

// ============================================================================
// Main Loop
// ============================================================================

void loop() {
  unsigned long currentTime = millis();

  // Sample PPG at 50Hz (non-blocking)
  samplePPG();

  // Check WiFi and admin commands every 3 seconds
  if (currentTime - lastWiFiAdminCheckTime >= WIFI_ADMIN_CHECK_INTERVAL_MS) {
    lastWiFiAdminCheckTime = currentTime;
    checkWiFi();
    checkOSCMessages();
  }

  // Reset watchdog timer every 5 seconds
  if (currentTime - lastWatchdogResetTime >= WATCHDOG_RESET_INTERVAL_MS) {
    lastWatchdogResetTime = currentTime;
    esp_task_wdt_reset();
  }

  // Print statistics every 5 seconds
  if (currentTime - lastStatsTime >= 5000) {
    lastStatsTime = currentTime;
    printStats();
  }

  // Update LED feedback
  updateLED();

  // Small delay for loop stability
  delayMicroseconds(100);
}
