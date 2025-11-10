# Configuration & Data Structures

---

## 3. Required Libraries

### 3.1 Arduino Libraries

**Same as Phase 1:**
- `WiFi.h` — ESP32 WiFi (built-in)
- `WiFiUdp.h` — UDP sockets (built-in)
- `OSC` by Adrian Freed — OSC message formatting

**platformio.ini:**
```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
upload_speed = 921600
board_build.flash_mode = qio
board_build.flash_size = 4MB
lib_deps =
    https://github.com/CNMAT/OSC.git
```

No new libraries needed — building on Phase 1 infrastructure.

---

## 4. Configuration Constants

### 4.1 Network Configuration

**Unchanged from Phase 1:**
```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS
const uint16_t SERVER_PORT = 8000;
```

### 4.2 Hardware Configuration

```cpp
// Pulse sensors on ADC1 channels
const int SENSOR_PINS[4] = {32, 33, 34, 35};
const int NUM_SENSORS = 4;
const int STATUS_LED_PIN = 2;  // Built-in LED
const int ADC_RESOLUTION = 12;  // 12-bit: 0-4095
```

**Requirements:**
- MUST use GPIO 32-35 (ADC1 channels, avoid WiFi conflicts)
- MUST configure ADC to 12-bit resolution in setup()
- GPIO 34-35 input-only (no pinMode OUTPUT allowed)

### 4.3 Signal Processing Parameters

```cpp
// Sampling configuration
const int SAMPLE_RATE_HZ = 50;                  // Per sensor
const int SAMPLE_INTERVAL_MS = 20;              // 1000 / 50

// Moving average filter
const int MOVING_AVG_SAMPLES = 5;               // 100ms window

// Baseline tracking (exponential decay)
const float BASELINE_DECAY_RATE = 0.1;          // 10% decay toward center
const int BASELINE_DECAY_INTERVAL = 150;        // Apply every 150 samples (3 sec)
```

**Requirements:**
- `SAMPLE_INTERVAL_MS`: MUST match 1000 / SAMPLE_RATE_HZ
- `MOVING_AVG_SAMPLES`: MUST be small enough for real-time (5 samples = 100ms lag)
- `BASELINE_DECAY_INTERVAL`: MUST be sample count, not time (150 samples = 3 sec at 50Hz)

### 4.4 Beat Detection Parameters

```cpp
// Threshold calculation
const float THRESHOLD_FRACTION = 0.6;           // 60% of signal range
const int MIN_SIGNAL_RANGE = 50;                // ADC units, below = disconnected

// Beat detection
const unsigned long REFRACTORY_PERIOD_MS = 300; // Max 200 BPM
const int FLAT_SIGNAL_THRESHOLD = 5;            // ADC variance for "flat"
const unsigned long DISCONNECT_TIMEOUT_MS = 1000; // 50 samples flat = disconnected
```

**Requirements:**
- `THRESHOLD_FRACTION`: 0.5-0.7 typical, tunable per user
- `MIN_SIGNAL_RANGE`: Prevents false beats on noise
- `REFRACTORY_PERIOD_MS`: Enforces max BPM, prevents double-triggers
- `FLAT_SIGNAL_THRESHOLD`: Variance check for disconnection

**Rate Limiting:**
- Refractory period limits max message rate: 300ms = max 200 msg/min per sensor
- 4 sensors × 200 msg/min = 800 messages/min total system max

### 4.5 Debug Levels

```cpp
#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose

// Level 0: Production (WiFi status only)
// Level 1: Testing (beat timestamps + BPM)
// Level 2: Verbose (raw ADC values every 100ms, baseline tracking)
```

**Requirements:**
- Level 0: Minimal output for festival deployment
- Level 1: Beat detection events for validation
- Level 2: Full signal diagnostics for algorithm tuning

---

## 5. Data Structures

### 5.1 Sensor State

**Purpose:** Track per-sensor signal processing and beat detection state

```cpp
struct SensorState {
  // Hardware
  int pin;                          // GPIO pin number

  // Moving average filter
  int rawSamples[MOVING_AVG_SAMPLES];  // Circular buffer
  int sampleIndex;                  // Current position in buffer
  int smoothedValue;                // Filter output

  // Baseline tracking (exponential decay)
  int minValue;                     // Decays upward toward center
  int maxValue;                     // Decays downward toward center
  int samplesSinceDecay;            // Counter for decay interval

  // Beat detection
  bool aboveThreshold;              // Currently above threshold?
  unsigned long lastBeatTime;       // millis() of last beat
  unsigned long lastIBI;            // Inter-beat interval (ms)
  bool firstBeatDetected;           // Have we sent first beat?

  // Disconnection detection
  bool isConnected;                 // Sensor shows valid signal?
  int lastRawValue;                 // For flat signal detection
  int flatSampleCount;              // Consecutive flat samples
};

SensorState sensors[4];
```

**Requirements:**

**R1: Initialization**
- MUST initialize all fields to zero/false in setup()
- MUST set `pin` to corresponding GPIO from SENSOR_PINS array
- MUST pre-fill `rawSamples` buffer with first ADC reading

**R2: Moving Average Buffer**
- Circular buffer: `sampleIndex` wraps at `MOVING_AVG_SAMPLES`
- On new sample: `rawSamples[sampleIndex] = newValue; sampleIndex = (sampleIndex + 1) % MOVING_AVG_SAMPLES;`
- Calculate mean: `sum(rawSamples) / MOVING_AVG_SAMPLES`

**R3: Baseline Tracking**
- Instant expansion: If `smoothedValue < minValue`, immediately update `minValue = smoothedValue`
- Instant expansion: If `smoothedValue > maxValue`, immediately update `maxValue = smoothedValue`
- Decay every 150 samples:
  - `minValue += (smoothedValue - minValue) * BASELINE_DECAY_RATE`
  - `maxValue -= (maxValue - smoothedValue) * BASELINE_DECAY_RATE`

**R4: Beat Detection State**
- `aboveThreshold`: Set true on rising edge, false on falling edge
- `lastBeatTime`: Updated with `millis()` when beat detected
- `firstBeatDetected`: False initially, set true after first beat (no IBI sent for first beat)

**R5: Disconnection State**
- `isConnected`: True by default, set false if flat signal or range too small
- `flatSampleCount`: Increment if variance < threshold, reset on change
- Mark disconnected if `flatSampleCount >= 50` (1 second at 50Hz)

### 5.2 System State

**Purpose:** Track global system state

```cpp
struct SystemState {
  bool wifiConnected;               // WiFi connection status
  unsigned long lastWiFiCheckTime;  // millis() of last WiFi check
  unsigned long loopCounter;        // For debug output throttling
  bool beatDetectedThisLoop;        // For LED pulse feedback
};

SystemState system = {false, 0, 0, false};
```

**Requirements:**
- `wifiConnected`: Updated by `checkWiFi()` every 5 seconds
- `loopCounter`: Incremented each loop, used for debug throttling
- `beatDetectedThisLoop`: Set true when ANY sensor detects beat, cleared after LED update

### 5.3 Global Objects

```cpp
WiFiUDP udp;          // UDP socket for OSC (from Phase 1)
SystemState system;   // System state
SensorState sensors[4];  // Array of 4 sensor states
```

---

## Related Documentation

- [Overview](overview.md) — System context and prerequisites
- [API: Sensors](api-sensors.md) — Sensor initialization and filtering functions
- [API: Signal Processing](api-signal-processing.md) — Baseline tracking function
- [API: Beat Detection](api-beat-detection.md) — Beat detection algorithm
- [Implementation](implementation.md) — How to use these structures in setup() and loop()

---

**Next Step:** Choose an API reference to implement:
- Sensors: [API: Sensors](api-sensors.md)
- Signal processing: [API: Signal Processing](api-signal-processing.md)
- Beat detection: [API: Beat Detection](api-beat-detection.md)
