#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCMessage.h>
#include <math.h>
#include <esp_task_wdt.h>
#include <esp_sleep.h>
#include <esp_wifi.h>
#include "../include/config.h"

// Watchdog timeout in seconds
#define WDT_TIMEOUT 30

// Maximum OSC message size (bytes)
#define MAX_OSC_MESSAGE_SIZE 512

// Power management constants
#define SIGNAL_QUALITY_THRESHOLD_NOISE 50     // stddev < 50 = noise/idle
#define SIGNAL_QUALITY_THRESHOLD_TRIGGER 50   // stddev > 50 = trigger ACTIVE (lowered for better UX)
#define SIGNAL_QUALITY_THRESHOLD_SUSTAIN 100  // stddev > 100 = sustain ACTIVE (higher threshold to prevent premature sleep)
#define SIGNAL_STABILITY_THRESHOLD 40         // stddev of stddevs < 40 = stable signal (prevents false triggers)
#define SIGNAL_STABILITY_UNKNOWN 9999         // Sentinel value when insufficient data for stability calculation
#define STDDEV_HISTORY_SIZE 5                 // Track last 5 stddev measurements for stability
#define IDLE_CHECK_INTERVAL_MS 500            // Light sleep interval in IDLE state
#define IDLE_CHECK_SAMPLES 20                 // Samples to collect during IDLE check
#define ACTIVE_TRIGGER_COUNT 1                // Consecutive good checks to enter ACTIVE (500ms for faster response)
#define SUSTAIN_TIMEOUT_MS 300000             // 5 minutes of poor signal before returning to IDLE
#define POOR_SIGNAL_GRACE_PERIOD_MS 10000     // Allow 10s of poor signal before starting timeout
#define WIFI_RETRY_LIMIT 20                   // Max WiFi connection attempts in ACTIVE before returning to IDLE (20 * 3s = 1 min)

enum PowerState {
  POWER_STATE_IDLE,    // Light sleep, periodic signal checking (preserves state)
  POWER_STATE_ACTIVE   // Light sleep between samples, streaming
};

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
  PowerState powerState;
  uint16_t lastStddev;           // Most recent signal stddev
  int consecutiveGoodChecks;     // Count of consecutive good signal checks in IDLE
  unsigned long poorSignalStartTime; // Time when poor signal began (for grace period)
  uint16_t stddevHistory[STDDEV_HISTORY_SIZE];  // Rolling history of stddev values for stability check
  int stddevHistoryIndex;        // Index into stddev history
  int stddevHistoryCount;        // Count of valid entries in history (0-STDDEV_HISTORY_SIZE)
  int wifiRetryCount;            // Count of WiFi connection attempts in ACTIVE state
  uint32_t transitionsToIdle;    // Total transitions to IDLE state
  uint32_t transitionsToActive;  // Total transitions to ACTIVE state
} state = {
  .wifiConnected = false,
  .bufferIndex = 0,
  .bundleStartTime = 0,
  .bundlesSent = 0,
  .adcRingIndex = 0,
  .sampleCount = 0,
  .powerState = POWER_STATE_IDLE,
  .lastStddev = 0,
  .consecutiveGoodChecks = 0,
  .poorSignalStartTime = 0,
  .stddevHistory = {0},
  .stddevHistoryIndex = 0,
  .stddevHistoryCount = 0,
  .wifiRetryCount = 0,
  .transitionsToIdle = 0,
  .transitionsToActive = 0
};

// Networking
IPAddress serverIP;
WiFiUDP udpSend;   // For sending PPG data to SERVER_PORT
#ifdef ENABLE_OSC_ADMIN
WiFiUDP udpRecv;   // For receiving admin commands on ADMIN_PORT
#endif

// Timing
unsigned long lastSampleTime = 0;
unsigned long lastWiFiAdminCheckTime = 0;
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
uint16_t calculateStddev();
uint16_t calculateSignalStability();
void updateStddevHistory(uint16_t stddev);
void idleStateLoop();
void activeStateLoop();
void enterIdleState();
void enterActiveState();

// ============================================================================
// Setup
// ============================================================================

void setup() {
  // Serial for debugging
  Serial.begin(115200);
  delay(1000);  // Brief delay for USB CDC to stabilize

  // Capture boot time for uptime calculation
  bootTime = millis();

  Serial.println("\n\n=== Amor ESP32 Firmware - Starting ===");
  Serial.print("PPG ID: ");
  Serial.println(PPG_ID);
  Serial.print("PPG GPIO: ");
  Serial.println(PPG_GPIO);
  Serial.print("Server: ");
  Serial.print(SERVER_IP);
  Serial.print(":");
  Serial.println(SERVER_PORT);
  Serial.println("\n*** Power Management Enabled ***");
  Serial.println("Starting in IDLE state (signal monitoring)");

  // Initialize components
  setupLED();
  setupADC();

  // Skip WiFi setup - will connect when entering ACTIVE state
  // setupWiFi();

  #ifdef ENABLE_WATCHDOG
  // Initialize watchdog timer
  Serial.print("Initializing watchdog timer (");
  Serial.print(WDT_TIMEOUT);
  Serial.println("s timeout)");

  esp_err_t err = esp_task_wdt_init(WDT_TIMEOUT, true);
  if (err != ESP_OK) {
    Serial.print("ERROR: Watchdog init failed: ");
    Serial.println(err);
  }

  err = esp_task_wdt_add(NULL);
  if (err != ESP_OK) {
    Serial.print("ERROR: Watchdog add task failed: ");
    Serial.println(err);
  } else {
    // Reset watchdog immediately after successful initialization
    esp_task_wdt_reset();
    Serial.println("Watchdog initialized successfully");
  }
  #else
  Serial.println("Watchdog timer: DISABLED");
  #endif

  Serial.println("Setup complete");

  // Initialize stats timer
  lastStatsTime = millis();
}

// ============================================================================
// Setup Functions
// ============================================================================

void setupLED() {
  // LED disabled (not visible on ESP32-S3)
  #ifdef ENABLE_LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);  // Keep off to save power
  #endif
}

void setupADC() {
  // Configure ADC for PPG sensor
  analogSetAttenuation(ADC_11db);
  analogReadResolution(12);
  adcAttachPin(PPG_GPIO);

  Serial.println("ADC configured: 12-bit, 0-4095 range");
}

void scanWiFi() {
  Serial.println("Scanning for WiFi networks...");

  // Check WiFi MAC address to verify hardware is present
  String mac = WiFi.macAddress();
  Serial.print("WiFi MAC: ");
  Serial.println(mac);

  WiFi.persistent(false);  // Don't save WiFi config to flash
  WiFi.mode(WIFI_MODE_NULL);  // Reset WiFi
  delay(100);
  WiFi.mode(WIFI_STA);
  Serial.print("WiFi mode set, status: ");
  Serial.println(WiFi.status());

  WiFi.setTxPower(WIFI_POWER_8_5dBm);  // Reduce power for ESP32-S3-Zero
  Serial.println("TX power set to 8.5dBm");

  WiFi.disconnect();
  delay(500);  // Longer delay for radio to stabilize

  Serial.println("Starting scan...");
  int n = WiFi.scanNetworks();
  Serial.print("Scan complete. Found ");
  Serial.print(n);
  Serial.println(" networks:");
  for (int i = 0; i < n; i++) {
    Serial.print("  ");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(WiFi.SSID(i));
    Serial.print(" (");
    Serial.print(WiFi.RSSI(i));
    Serial.print(" dBm, ch ");
    Serial.print(WiFi.channel(i));
    Serial.println(")");
  }
  WiFi.scanDelete();
}

void setupWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 0, NULL, true);  // true = connect to hidden network
  WiFi.setTxPower(WIFI_POWER_7dBm);  // Reduce power for ESP32-S3-Zero (try lower if still failing)

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

    #ifdef ENABLE_OSC_ADMIN
    // Start UDP for receiving admin commands
    if (udpRecv.begin(ADMIN_PORT)) {
      Serial.print("UDP receive initialized on port ");
      Serial.println(ADMIN_PORT);
    }
    #endif
    // udpSend doesn't need begin() - it's used only for outgoing packets
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
  wl_status_t status = WiFi.status();
  state.wifiConnected = (status == WL_CONNECTED);

  if (!state.wifiConnected) {
    // Only interrupt and retry if connection is definitively failed (not in progress)
    if (status == WL_DISCONNECTED || status == WL_CONNECTION_LOST || status == WL_CONNECT_FAILED || status == WL_NO_SSID_AVAIL) {
      if (previousState) {
        Serial.println("WiFi disconnected, attempting to reconnect...");
      } else {
        Serial.print("WiFi connection failed (status=");
        Serial.print(status);
        Serial.print(", retry ");
        Serial.print(state.wifiRetryCount);
        Serial.print("/");
        Serial.print(WIFI_RETRY_LIMIT);
        Serial.println(")");
      }

      // Increment retry counter
      state.wifiRetryCount++;

      // Start new connection attempt
      WiFi.disconnect();
      delay(100);
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 0, NULL, true);  // true = connect to hidden network
      WiFi.setTxPower(WIFI_POWER_7dBm);  // Set TX power AFTER begin()
    } else if (status == WL_IDLE_STATUS) {
      // Connection in progress, but count it to prevent infinite waiting
      state.wifiRetryCount++;
      Serial.print("WiFi connection in progress (attempt ");
      Serial.print(state.wifiRetryCount);
      Serial.println(")...");
    }
  } else if (state.wifiConnected && !previousState) {
    Serial.println("WiFi reconnected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    state.wifiRetryCount = 0;  // Reset retry counter on successful connection

    #ifdef ENABLE_OSC_ADMIN
    // Re-initialize UDP receive socket after reconnection
    udpRecv.stop();  // Clean shutdown of previous socket
    if (udpRecv.begin(ADMIN_PORT)) {
      Serial.print("UDP receive re-initialized on port ");
      Serial.println(ADMIN_PORT);
    } else {
      Serial.println("ERROR: UDP receive re-initialization failed");
    }
    #endif
  }
}

// ============================================================================
// OSC Admin Commands
// ============================================================================

#ifdef ENABLE_OSC_ADMIN
void checkOSCMessages() {
  // Check for incoming OSC messages on ADMIN_PORT
  int packetSize = udpRecv.parsePacket();

  // Validate packet size
  if (packetSize > 0 && packetSize <= MAX_OSC_MESSAGE_SIZE) {
    OSCMessage msg;

    // Read the packet into the OSC message
    while (packetSize--) {
      msg.fill(udpRecv.read());
    }

    // Check if this is a restart command
    if (msg.fullMatch("/restart")) {
      handleRestartCommand();
    }

    // Clear message to avoid memory leak
    msg.empty();
  } else if (packetSize > MAX_OSC_MESSAGE_SIZE) {
    Serial.print("ERROR: OSC message too large (");
    Serial.print(packetSize);
    Serial.println(" bytes), ignoring");
    // Flush the oversized packet
    udpRecv.flush();
  }
}

void handleRestartCommand() {
  Serial.print("Restart request from ");
  Serial.print(udpRecv.remoteIP());
  Serial.print(":");
  Serial.println(udpRecv.remotePort());
  Serial.println("Rebooting ESP32...");
  Serial.flush();  // Ensure message is sent before restart

  delay(100);  // Brief delay to allow serial output
  ESP.restart();
}
#endif // ENABLE_OSC_ADMIN

// ============================================================================
// LED Feedback
// ============================================================================

void updateLED() {
  // LED disabled (not visible on ESP32-S3, wastes power)
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
  udpSend.beginPacket(serverIP, SERVER_PORT);
  msg.send(udpSend);
  udpSend.endPacket();

  // CRITICAL: Clear message to avoid memory leak
  msg.empty();

  // Increment bundle counter
  state.bundlesSent++;
}

// ============================================================================
// Signal Quality
// ============================================================================

uint16_t calculateStddev() {
  if (state.sampleCount < 10) {
    return 0;
  }

  // Calculate mean
  uint32_t sum = 0;
  for (int i = 0; i < state.sampleCount; i++) {
    sum += state.adcRingBuffer[i];
  }
  uint16_t mean = sum / state.sampleCount;

  // Calculate standard deviation
  uint32_t sumSqDiff = 0;
  for (int i = 0; i < state.sampleCount; i++) {
    int32_t diff = (int32_t)state.adcRingBuffer[i] - (int32_t)mean;
    sumSqDiff += diff * diff;
  }

  return (uint16_t)sqrt((double)sumSqDiff / state.sampleCount);
}

void updateStddevHistory(uint16_t stddev) {
  // Add to rolling history
  state.stddevHistory[state.stddevHistoryIndex] = stddev;
  state.stddevHistoryIndex = (state.stddevHistoryIndex + 1) % STDDEV_HISTORY_SIZE;
  if (state.stddevHistoryCount < STDDEV_HISTORY_SIZE) {
    state.stddevHistoryCount++;
  }
}

uint16_t calculateSignalStability() {
  // Need at least 3 measurements for meaningful stability calculation
  if (state.stddevHistoryCount < 3) {
    return SIGNAL_STABILITY_UNKNOWN;  // Return high value = unstable when insufficient data
  }

  // Calculate mean of stddev values
  uint32_t sum = 0;
  for (int i = 0; i < state.stddevHistoryCount; i++) {
    sum += state.stddevHistory[i];
  }
  uint16_t mean = sum / state.stddevHistoryCount;

  // Calculate standard deviation of stddev values
  uint32_t sumSqDiff = 0;
  for (int i = 0; i < state.stddevHistoryCount; i++) {
    int32_t diff = (int32_t)state.stddevHistory[i] - (int32_t)mean;
    sumSqDiff += diff * diff;
  }

  return (uint16_t)sqrt((double)sumSqDiff / state.stddevHistoryCount);
}

// ============================================================================
// Power State Management
// ============================================================================

void enterIdleState() {
  Serial.println("Entering IDLE state (light sleep monitoring)");
  state.powerState = POWER_STATE_IDLE;
  state.consecutiveGoodChecks = 0;
  state.transitionsToIdle++;

  // Reset signal quality tracking to avoid contamination from ACTIVE state
  state.stddevHistoryCount = 0;
  state.stddevHistoryIndex = 0;
  for (int i = 0; i < STDDEV_HISTORY_SIZE; i++) {
    state.stddevHistory[i] = 0;
  }

  // Reset ADC ring buffer to avoid contamination
  state.sampleCount = 0;
  state.adcRingIndex = 0;

  // Reset WiFi retry counter
  state.wifiRetryCount = 0;

  // Disconnect WiFi to save power
  if (state.wifiConnected) {
    WiFi.disconnect(true);  // true = turn off WiFi radio
    WiFi.mode(WIFI_OFF);
    state.wifiConnected = false;
  }
}

void enterActiveState() {
  Serial.println("Entering ACTIVE state (streaming mode)");
  state.powerState = POWER_STATE_ACTIVE;
  state.transitionsToActive++;
  state.wifiRetryCount = 0;

  // Reconnect WiFi
  setupWiFi();

  // Validate connection and enable power save mode
  if (!state.wifiConnected) {
    Serial.println("WARNING: Failed to connect WiFi in ACTIVE state");
    state.wifiRetryCount++;
    // Continue in ACTIVE - checkWiFi() will retry connection every 3 seconds
  } else {
    // Enable WiFi power save mode for light sleep
    esp_err_t err = esp_wifi_set_ps(WIFI_PS_MIN_MODEM);
    if (err != ESP_OK) {
      Serial.print("WARNING: WiFi power save failed: ");
      Serial.println(err);
    }
  }
}

void idleStateLoop() {
  #ifdef ENABLE_WATCHDOG
  esp_task_wdt_reset();  // Reset watchdog on each wake cycle
  #endif

  // Collect burst of samples to check signal quality
  Serial.println("IDLE: Checking signal quality...");

  for (int i = 0; i < IDLE_CHECK_SAMPLES; i++) {
    uint16_t sample = analogRead(PPG_GPIO);
    state.adcRingBuffer[state.adcRingIndex] = sample;
    state.adcRingIndex = (state.adcRingIndex + 1) % 50;
    if (state.sampleCount < 50) {
      state.sampleCount++;
    }
    delay(2);  // Small delay between samples (~500Hz burst)
  }

  // Calculate signal quality
  state.lastStddev = calculateStddev();
  updateStddevHistory(state.lastStddev);
  uint16_t stability = calculateSignalStability();

  Serial.print("IDLE: stddev=");
  Serial.print(state.lastStddev);
  Serial.print(" stability=");
  Serial.println(stability);

  // Check if signal is good (magnitude + stability to prevent false triggers)
  bool signalGood = (state.lastStddev > SIGNAL_QUALITY_THRESHOLD_TRIGGER) &&
                    (stability < SIGNAL_STABILITY_THRESHOLD);

  if (signalGood) {
    state.consecutiveGoodChecks++;
    Serial.print("IDLE: Good stable signal detected (");
    Serial.print(state.consecutiveGoodChecks);
    Serial.print("/");
    Serial.print(ACTIVE_TRIGGER_COUNT);
    Serial.println(")");

    if (state.consecutiveGoodChecks >= ACTIVE_TRIGGER_COUNT) {
      // Trigger: Enter ACTIVE state
      enterActiveState();
      return;
    }
  } else {
    state.consecutiveGoodChecks = 0;
  }

  // Enter light sleep for IDLE_CHECK_INTERVAL_MS
  Serial.print("IDLE: Light sleep for ");
  Serial.print(IDLE_CHECK_INTERVAL_MS);
  Serial.println("ms");
  Serial.flush();  // Ensure serial output is sent before sleep

  unsigned long sleepStart = millis();
  esp_sleep_enable_timer_wakeup(IDLE_CHECK_INTERVAL_MS * 1000);  // microseconds
  esp_err_t err = esp_light_sleep_start();  // Light sleep preserves state and allows faster wake
  unsigned long sleepDuration = millis() - sleepStart;

  // Validate sleep actually worked
  if (err != ESP_OK) {
    Serial.print("ERROR: Light sleep failed: ");
    Serial.println(err);
    delay(IDLE_CHECK_INTERVAL_MS);  // Fallback to regular delay
  } else if (sleepDuration < (IDLE_CHECK_INTERVAL_MS - 10)) {
    Serial.print("WARNING: Sleep short, only ");
    Serial.print(sleepDuration);
    Serial.println("ms (light sleep may not be working)");
    delay(IDLE_CHECK_INTERVAL_MS - sleepDuration);  // Make up the difference
  }
}

void activeStateLoop() {
  unsigned long currentTime = millis();

  // Sample PPG at 50Hz (non-blocking)
  samplePPG();

  // Check WiFi and admin commands every 3 seconds
  if (currentTime - lastWiFiAdminCheckTime >= WIFI_ADMIN_CHECK_INTERVAL_MS) {
    lastWiFiAdminCheckTime = currentTime;
    checkWiFi();

    // Check if WiFi retry limit exceeded
    if (state.wifiRetryCount >= WIFI_RETRY_LIMIT) {
      Serial.print("ACTIVE: WiFi retry limit exceeded (");
      Serial.print(state.wifiRetryCount);
      Serial.println(" attempts), returning to IDLE");
      enterIdleState();
      return;
    }

    #ifdef ENABLE_OSC_ADMIN
    checkOSCMessages();
    #endif
    #ifdef ENABLE_WATCHDOG
    esp_task_wdt_reset();  // Reset watchdog to prove firmware health
    #endif

    // Check signal quality for sustain timer (use higher SUSTAIN threshold)
    state.lastStddev = calculateStddev();
    if (state.lastStddev > SIGNAL_QUALITY_THRESHOLD_SUSTAIN) {
      // Good signal, reset grace period
      state.poorSignalStartTime = 0;
    } else {
      // Poor signal detected
      if (state.poorSignalStartTime == 0) {
        // First detection of poor signal, start grace period
        state.poorSignalStartTime = currentTime;
        Serial.println("ACTIVE: Poor signal detected, starting grace period");
      }

      // Check if total poor signal duration (from first detection) exceeds grace + timeout
      unsigned long timeSincePoorSignal = currentTime - state.poorSignalStartTime;
      unsigned long totalTimeout = POOR_SIGNAL_GRACE_PERIOD_MS + SUSTAIN_TIMEOUT_MS;
      if (timeSincePoorSignal >= totalTimeout) {
        Serial.print("ACTIVE: Poor signal for ");
        Serial.print(timeSincePoorSignal / 1000);
        Serial.println("s, returning to IDLE");
        enterIdleState();
        return;
      }
    }
  }

  // Print statistics every 5 seconds
  if (currentTime - lastStatsTime >= 5000) {
    lastStatsTime = currentTime;
    printStats();
  }

  // Update LED feedback
  updateLED();

  // Light sleep until next sample time (power saving)
  unsigned long nextSampleTime = lastSampleTime + SAMPLE_INTERVAL_MS;
  if (currentTime < nextSampleTime) {
    unsigned long sleepTimeMs = nextSampleTime - currentTime;
    if (sleepTimeMs > 1) {
      // Use light sleep for any meaningful wait > 1ms
      unsigned long sleepStart = millis();
      esp_sleep_enable_timer_wakeup(sleepTimeMs * 1000);  // microseconds
      esp_err_t err = esp_light_sleep_start();
      unsigned long actualSleep = millis() - sleepStart;

      if (err != ESP_OK) {
        Serial.print("WARNING: ACTIVE light sleep failed: ");
        Serial.println(err);
        delay(sleepTimeMs);  // Fallback to regular delay
      } else if (actualSleep < sleepTimeMs - 2) {  // 2ms tolerance
        Serial.print("WARNING: ACTIVE sleep short, only ");
        Serial.print(actualSleep);
        Serial.print("ms of ");
        Serial.print(sleepTimeMs);
        Serial.println("ms");
        delay(sleepTimeMs - actualSleep);  // Make up the difference
      }
    }
    // For very short waits (<= 1ms), just continue - the loop overhead handles it
  }
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

  // Uptime [HH.Hs] and power state
  const char* stateStr = (state.powerState == POWER_STATE_IDLE) ? "IDLE" : "ACTIVE";
  int written = snprintf(pos, remaining, "[%.1fs] PPG_ID=%d [%s]", uptimeSec, PPG_ID, stateStr);
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

    written = snprintf(pos, remaining, " | ADC: %u±%u (%u-%u) | SigQual: %u",
                       mean, stddev, minVal, maxVal, state.lastStddev);
    pos += written;
    remaining -= written;
  } else {
    // Show signal quality even without full stats
    written = snprintf(pos, remaining, " | SigQual: %u", state.lastStddev);
    pos += written;
    remaining -= written;
  }

  // Message rate (bundles per second)
  float rate = (uptimeSec > 0) ? ((float)state.bundlesSent / uptimeSec) : 0.0f;
  written = snprintf(pos, remaining, " | Rate: %.1f msg/s", rate);
  pos += written;
  remaining -= written;

  // State transitions
  written = snprintf(pos, remaining, " | Transitions: I=%lu A=%lu",
                     state.transitionsToIdle, state.transitionsToActive);
  pos += written;
  remaining -= written;

  // Print single line
  Serial.println(statsLine);
}

// ============================================================================
// Main Loop
// ============================================================================

void loop() {
  // Dispatch to appropriate power state handler
  if (state.powerState == POWER_STATE_IDLE) {
    idleStateLoop();
  } else {
    activeStateLoop();
  }
}
