/**
 * Heartbeat Installation - Phase 3: Multi-Sensor Beat Detection
 * ESP32 Firmware - 4 Independent Pulse Sensors
 * Version: 3.0
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCMessage.h>

// Network Configuration
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);
const uint16_t SERVER_PORT = 8000;
const unsigned long WIFI_TIMEOUT_MS = 30000;

// Hardware Configuration
const int SENSOR_PINS[4] = {32, 33, 34, 35};
const int NUM_SENSORS = 4;
const int STATUS_LED_PIN = 2;
const int ADC_RESOLUTION = 12;

// Static assertions for configuration validation
static_assert(sizeof(SENSOR_PINS)/sizeof(SENSOR_PINS[0]) == NUM_SENSORS,
              "SENSOR_PINS array size must match NUM_SENSORS");
static_assert(NUM_SENSORS == 4,
              "Phase 3 requires exactly 4 sensors");

// Signal Processing Parameters
const int SAMPLE_RATE_HZ = 50;
const int SAMPLE_INTERVAL_MS = 20;
const int MOVING_AVG_SAMPLES = 5;
const float BASELINE_DECAY_RATE = 0.1;
const int BASELINE_DECAY_INTERVAL = 150;

// Beat Detection Parameters
const float THRESHOLD_FRACTION = 0.6;
const int MIN_SIGNAL_RANGE = 50;
const unsigned long REFRACTORY_PERIOD_MS = 300;
const int FLAT_SIGNAL_THRESHOLD = 5;
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;

// Debug Configuration
#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose

// ============================================================================
// DATA STRUCTURES (Component 9.2: Task 2.1 - SensorState)
// ============================================================================

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

// ============================================================================
// DATA STRUCTURES (Component 9.2: Task 2.2 - SystemState)
// ============================================================================

struct SystemState {
  bool wifiConnected;
  unsigned long lastWiFiCheckTime;
  unsigned long loopCounter;
  bool beatDetectedThisLoop;
};

// ============================================================================
// GLOBAL VARIABLES (Component 9.2: Task 2.3)
// ============================================================================

WiFiUDP udp;
SystemState system = {false, 0, 0, false};
SensorState sensors[4];

// ============================================================================
// FUNCTION DECLARATIONS (Component 9.2: Task 2.4)
// ============================================================================

// WiFi functions
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

// ============================================================================
// PLACEHOLDER SETUP AND LOOP (for testing)
// ============================================================================

// Placeholder functions to avoid linker errors during testing
void setup() {}
void loop() {}
