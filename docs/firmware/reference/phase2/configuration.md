# Configuration & Data Structures

## 3. Required Libraries

### 3.1 Arduino Libraries (Phase 1 + New)

**Phase 1 Libraries (keep):**
- `WiFi.h` - ESP32 WiFi stack
- `WiFiUdp.h` - UDP socket implementation
- `OSC` by Adrian Freed (CNMat) - OSC message construction

**No new external libraries needed for Phase 2**

**Built-in ESP32 Functions (Phase 2):**
- `analogRead(pin)` - 12-bit ADC reading (0-4095)
- `analogSetAttenuation(ADC_11db)` - Set ADC input range to 0-3.3V

### 3.2 ADC Configuration

```cpp
// In setup(), before first analogRead():
analogSetAttenuation(ADC_11db);  // 0-3.3V input range
analogReadResolution(12);        // 12-bit resolution (0-4095)
```

**Requirements:**
- GPIO 32 is ADC1_CH4 (safe for WiFi, does not conflict)
- 12-bit resolution provides 0-4095 range
- PulseSensor outputs 0-3V, maps to ~0-3723 ADC units

---

## 4. Configuration Constants

### 4.1 Network Configuration (Phase 1 - Keep Unchanged)

```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS
const uint16_t SERVER_PORT = 8000;
```

**No changes from Phase 1** - WiFi and OSC parameters stay the same.

### 4.2 Hardware Configuration (Phase 2 Extension)

```cpp
// Phase 1 (keep):
const int STATUS_LED_PIN = 2;  // Built-in LED

// Phase 2 (add):
const int SENSOR_PIN = 32;     // GPIO 32 (ADC1_CH4)
const int ADC_RESOLUTION = 12; // 12-bit (0-4095)
```

**Requirements:**
- GPIO 32 is ADC1 channel (safe with WiFi)
- Input-only pin (no internal pullup/pulldown)
- 12-bit resolution standard on ESP32

### 4.3 Signal Processing Parameters (Phase 2 New)

```cpp
// Sampling configuration
const int SAMPLE_RATE_HZ = 50;              // 50 samples/second
const int SAMPLE_INTERVAL_MS = 20;          // 1000 / 50 = 20ms

// Moving average filter
const int MOVING_AVG_SAMPLES = 5;           // 100ms smoothing window (5 samples @ 50Hz)

// Baseline tracking (exponential decay)
const float BASELINE_DECAY_RATE = 0.1;      // 10% decay per interval
const int BASELINE_DECAY_INTERVAL = 150;    // Apply every 150 samples (3 seconds @ 50Hz)
```

**Rationale:**
- 50Hz sampling: Adequate for heartbeat (1-3 Hz fundamental frequency)
- 5-sample moving average: 100ms window smooths noise without excessive lag
- Baseline decay: 3-second interval balances stability vs adaptation

### 4.4 Beat Detection Parameters (Phase 2 New)

```cpp
// Threshold detection
const float THRESHOLD_FRACTION = 0.6;         // 60% of signal range above baseline
const int MIN_SIGNAL_RANGE = 50;              // Minimum ADC range for valid signal

// Refractory period
const unsigned long REFRACTORY_PERIOD_MS = 300;  // 300ms = max 200 BPM

// Disconnection detection
const int FLAT_SIGNAL_THRESHOLD = 5;          // ADC variance < 5 = flat
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;  // 1 second flat = disconnected
```

**Rationale:**
- 60% threshold: Empirically effective for PulseSensor (tunable 50-70%)
- Min range 50: Prevents false beats from noise on flat signals
- 300ms refractory: Prevents double-triggers, limits to physiological max (200 BPM)
- 1-second disconnect timeout: Fast response when sensor removed

### 4.5 System Configuration (Phase 1 Keep + Phase 2 Modify)

```cpp
const int SENSOR_ID = 0;  // CHANGE THIS: 0, 1, 2, or 3 (Phase 1)

// Phase 1 constant REMOVED:
// const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;  // NO LONGER USED

const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 seconds (Phase 1, keep)
```

**Phase 2 Changes:**
- Remove `TEST_MESSAGE_INTERVAL_MS` (no longer sending periodic test messages)
- OSC messages now triggered by beat detection events (asynchronous)

---

## 5. Data Structures

### 5.1 System State (Phase 1 - Modify)

**Phase 1 Structure:**
```cpp
struct SystemState {
    bool wifiConnected;
    unsigned long lastMessageTime;
    uint32_t messageCounter;
};
```

**Phase 2 Modified Structure:**
```cpp
struct SystemState {
    bool wifiConnected;           // Phase 1: Current WiFi connection status
    unsigned long lastWiFiCheckTime;  // Phase 2: For WiFi monitoring rate limit
    unsigned long loopCounter;    // Phase 2: For debug output throttling
    // Remove: lastMessageTime, messageCounter (no longer periodic messages)
    // Note: messageCounter was only used for Phase 1 periodic test messages,
    //       which are replaced by event-driven beat detection in Phase 2.
};
```

**Initial Values:**
```cpp
SystemState state = {
    .wifiConnected = false,
    .lastWiFiCheckTime = 0,
    .loopCounter = 0
};
```

### 5.2 Sensor State (Phase 2 New)

**Purpose:** Track signal processing and beat detection for one sensor

```cpp
struct SensorState {
    // Moving average filter
    int rawSamples[MOVING_AVG_SAMPLES];  // Circular buffer (5 samples)
    int sampleIndex;                      // Current position in buffer
    int smoothedValue;                    // Output of moving average

    // Baseline tracking (exponential decay)
    int minValue;                         // Minimum, decays upward
    int maxValue;                         // Maximum, decays downward
    int samplesSinceDecay;                // Counter for 3-second decay interval

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
```

**Initial Values:**
```cpp
SensorState sensor = {
    .rawSamples = {0},        // Will be initialized in setup()
    .sampleIndex = 0,
    .smoothedValue = 0,
    .minValue = 0,            // Will be set to first reading
    .maxValue = 4095,         // Will be set to first reading
    .samplesSinceDecay = 0,
    .aboveThreshold = false,
    .lastBeatTime = 0,
    .lastIBI = 0,
    .firstBeatDetected = false,
    .isConnected = false,     // Set true after first valid reading
    .lastRawValue = 0,
    .flatSampleCount = 0
};
```

### 5.3 Global Objects (Phase 1 Keep + Phase 2 Add)

```cpp
WiFiUDP udp;                  // Phase 1: UDP socket
SystemState state;            // Phase 2: Modified system state
SensorState sensor;           // Phase 2: Sensor state
static unsigned long ledPulseTime = 0;  // Time when LED pulse started
```

**Note:** Phase 2 implements single sensor (GPIO 32). Phase 3 will expand to 4 sensors.

---

## Related Documentation

- **[Overview](overview.md)** - Prerequisites and architecture
- **[API: Sensors](api-sensors.md)** - Sensor initialization and moving average
- **[Implementation](implementation.md)** - Code structure and main flow
