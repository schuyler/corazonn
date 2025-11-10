# Phase 3 Component 9.1 - Implementation Checklist

## Required: Create src/main.cpp with Configuration

This checklist shows EXACTLY what must be in `src/main.cpp` for all 43 tests to pass.

**File**: `/home/user/corazonn/firmware/heartbeat_phase3/src/main.cpp`

---

## SECTION 1: Header Comment (Task 1.2)
Required for tests:
- `test_file_header_comment_exists`

Must include:
```cpp
/**
 * Heartbeat Installation - Phase 3: Multi-Sensor Beat Detection
 * ESP32 Firmware - 4 Independent Pulse Sensors
 * Version: 3.0
 */
```

Alternatives accepted (at least one):
- "Phase 3" OR "phase 3" OR "Multi-Sensor"

---

## SECTION 2: Includes (Task 1.2)
Required for tests:
- `test_include_arduino_h`
- `test_include_wifi_h`
- `test_include_wifiudp_h`
- `test_include_oscmessage_h`
- `test_includes_well_formed`

Must include (in this order or any order):
```cpp
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <OSCMessage.h>
```

Do NOT use:
- `#include Arduino.h` (missing angle brackets)
- `#include WiFi.h` (missing angle brackets)

---

## SECTION 3: Network Configuration (Task 1.3)
Required for tests:
- `test_config_wifi_ssid_defined`
- `test_config_wifi_password_defined`
- `test_config_server_ip_defined`
- `test_config_server_port_defined`
- `test_config_wifi_timeout_defined`

Must define:
```cpp
// Network Configuration
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS to match your network
const uint16_t SERVER_PORT = 8000;
const unsigned long WIFI_TIMEOUT_MS = 30000;
```

Critical details:
- WIFI_SSID must contain: `heartbeat-install`
- SERVER_IP must have 4 numeric octets (can be any values)
- SERVER_PORT must contain: `8000`
- WIFI_TIMEOUT_MS must contain: `30000`

---

## SECTION 4: Hardware Configuration (Task 1.4)
Required for tests:
- `test_config_sensor_pins_defined`
- `test_config_num_sensors_defined`
- `test_config_status_led_pin_defined`
- `test_config_adc_resolution_defined`
- `test_hardware_config_is_const`
- `test_static_assertion_array_size`
- `test_static_assertion_num_sensors`

Must define:
```cpp
// Hardware Configuration
const int SENSOR_PINS[4] = {32, 33, 34, 35};  // ADC1 channels
const int NUM_SENSORS = 4;
const int STATUS_LED_PIN = 2;  // Built-in LED
const int ADC_RESOLUTION = 12;  // 12-bit: 0-4095

// Static assertions for configuration validation
static_assert(sizeof(SENSOR_PINS)/sizeof(SENSOR_PINS[0]) == 4, "SENSOR_PINS array must have 4 elements");
static_assert(NUM_SENSORS == 4, "NUM_SENSORS must equal 4");
```

Critical details:
- SENSOR_PINS MUST be array of [4]
- SENSOR_PINS MUST contain EXACTLY: 32, 33, 34, 35
- NUM_SENSORS MUST be: 4
- STATUS_LED_PIN MUST contain: 2
- ADC_RESOLUTION MUST contain: 12
- MUST have static_assert keyword present
- MUST have static_assert checking NUM_SENSORS == 4
- All must be `const` type

---

## SECTION 5: Signal Processing Parameters (Task 1.5)
Required for tests:
- `test_config_sample_rate_hz_defined`
- `test_config_sample_interval_ms_defined`
- `test_config_moving_avg_samples_defined`
- `test_config_baseline_decay_rate_defined`
- `test_config_baseline_decay_interval_defined`
- `test_signal_processing_is_const`
- `test_config_sample_interval_calculation`

Must define:
```cpp
// Signal Processing Parameters
const int SAMPLE_RATE_HZ = 50;                  // Per sensor
const int SAMPLE_INTERVAL_MS = 20;              // 1000 / 50
const int MOVING_AVG_SAMPLES = 5;               // 100ms window
const float BASELINE_DECAY_RATE = 0.1;          // 10% decay
const int BASELINE_DECAY_INTERVAL = 150;        // 3 sec @ 50Hz
```

Critical details:
- SAMPLE_RATE_HZ must be: 50
- SAMPLE_INTERVAL_MS must be: 20 (and 20 = 1000/50, so tests verify both)
- MOVING_AVG_SAMPLES must be: 5
- BASELINE_DECAY_RATE must be: 0.1 (floating point)
- BASELINE_DECAY_INTERVAL must be: 150
- All must be `const` (const int or const float)

---

## SECTION 6: Beat Detection Parameters (Task 1.6)
Required for tests:
- `test_config_threshold_fraction_defined`
- `test_config_min_signal_range_defined`
- `test_config_refractory_period_ms_defined`
- `test_config_flat_signal_threshold_defined`
- `test_config_disconnect_timeout_ms_defined`
- `test_beat_detection_is_const`

Must define:
```cpp
// Beat Detection Parameters
const float THRESHOLD_FRACTION = 0.6;           // 60% of range
const int MIN_SIGNAL_RANGE = 50;                // ADC units minimum
const unsigned long REFRACTORY_PERIOD_MS = 300; // Max 200 BPM
const int FLAT_SIGNAL_THRESHOLD = 5;            // Variance for "flat"
const unsigned long DISCONNECT_TIMEOUT_MS = 1000; // 1 sec flat
```

Critical details:
- THRESHOLD_FRACTION must be: 0.6 (floating point)
- MIN_SIGNAL_RANGE must be: 50
- REFRACTORY_PERIOD_MS must be: 300
- FLAT_SIGNAL_THRESHOLD must be: 5
- DISCONNECT_TIMEOUT_MS must be: 1000
- All must be `const` (const float or const unsigned long/int)

---

## SECTION 7: Debug Configuration (Task 1.7)
Required for tests:
- `test_config_debug_level_defined`
- `test_config_debug_level_valid`
- `test_config_debug_level_active`

Must define:
```cpp
// Debug Configuration
#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose
```

Critical details:
- Must be: `#define DEBUG_LEVEL` (macro, not const)
- Value must be: 0, 1, or 2
- Must NOT be commented out (tests check with `pattern_active()`)
- Can optionally include comment about debug levels

---

## SUMMARY: Constants Count

The implementation must define at least **21 distinct constants**:

**Network Configuration (5)**:
1. WIFI_SSID
2. WIFI_PASSWORD
3. SERVER_IP
4. SERVER_PORT
5. WIFI_TIMEOUT_MS

**Hardware Configuration (4)**:
6. SENSOR_PINS
7. NUM_SENSORS
8. STATUS_LED_PIN
9. ADC_RESOLUTION

**Signal Processing (5)**:
10. SAMPLE_RATE_HZ
11. SAMPLE_INTERVAL_MS
12. MOVING_AVG_SAMPLES
13. BASELINE_DECAY_RATE
14. BASELINE_DECAY_INTERVAL

**Beat Detection (5)**:
15. THRESHOLD_FRACTION
16. MIN_SIGNAL_RANGE
17. REFRACTORY_PERIOD_MS
18. FLAT_SIGNAL_THRESHOLD
19. DISCONNECT_TIMEOUT_MS

**Debug (1)**:
20. DEBUG_LEVEL (macro)

**Static Assertions (2+)**:
21. Array bounds check
22. NUM_SENSORS == 4

---

## TESTING STRATEGY

After creating `src/main.cpp`:

1. **Run tests**:
   ```bash
   cd /home/user/corazonn/firmware/heartbeat_phase3
   pio test -e test_component_9_1
   ```

2. **Expected results**:
   - All 43 tests PASS ✓
   - No failures or errors

3. **If tests fail**:
   - Read test name to identify missing constant
   - Verify exact spelling, type, and value
   - Check that constants appear in correct section
   - Ensure no typos in values (e.g., 0.1 not 0.10)

---

## MINIMUM WORKING EXAMPLE

Here is a minimal main.cpp that will pass all 43 tests:

```cpp
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

static_assert(sizeof(SENSOR_PINS)/sizeof(SENSOR_PINS[0]) == 4, "Array size");
static_assert(NUM_SENSORS == 4, "Sensor count");

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
#define DEBUG_LEVEL 1

// Placeholder functions to avoid linker errors during testing
void setup() {}
void loop() {}
```

This minimal file will:
- ✓ Pass all 43 tests
- ✓ Compile without errors
- ✓ Verify all configuration constants are correct

---

## Important Notes for Implementation

1. **Do NOT add** anything beyond Task 1.8 yet
   - No data structures (those are Task 2.x)
   - No function implementations (those are Tasks 3.x+)
   - No setup()/loop() logic (those are Tasks 9.x)

2. **Test focus**:
   - Tests only check for constant declarations
   - Tests do NOT execute code
   - Tests use static code analysis (text pattern matching)

3. **Verification**:
   - After creating main.cpp, run: `pio test -e test_component_9_1`
   - All 43 tests should PASS
   - No modifications needed if all tests pass

4. **Next phase**:
   - After Component 9.1 tests pass
   - Move to Component 9.2 tests (data structures)
   - Each component has its own test suite

---

## File Checklist

- [x] `/home/user/corazonn/firmware/heartbeat_phase3/` - Directory created
- [x] `/home/user/corazonn/firmware/heartbeat_phase3/src/` - Created
- [x] `/home/user/corazonn/firmware/heartbeat_phase3/test/` - Created
- [x] `/home/user/corazonn/firmware/heartbeat_phase3/test/test_component_9_1.cpp` - Created (643 lines, 43 tests)
- [x] `/home/user/corazonn/firmware/heartbeat_phase3/test/test_helpers.h` - Copied from Phase 1
- [x] `/home/user/corazonn/firmware/heartbeat_phase3/platformio.ini` - Copied from Phase 1
- [ ] `/home/user/corazonn/firmware/heartbeat_phase3/src/main.cpp` - **TO BE CREATED** (your task)

---

## Questions Before Implementation?

Before writing src/main.cpp, confirm:

1. Should WIFI_PASSWORD be "your-password-here" or actual password?
   - **Answer**: Use "your-password-here" - tests only check the constant exists

2. Should SERVER_IP be 192.168.1.100?
   - **Answer**: Tests don't check specific octets, any IP format works. Example is fine.

3. Can I add comments in the constants section?
   - **Answer**: YES! Comments are encouraged. Tests look for comments.

4. Can I add setup()/loop() placeholder functions?
   - **Answer**: YES! Tests ignore function bodies. You can add empty functions if needed.

5. Can constants be on multiple lines?
   - **Answer**: YES! Tests use substring matching, not line-based.

6. Do I need to implement WiFi functions yet?
   - **Answer**: NO! Only configuration constants for now. Task 8.2 (later) copies WiFi functions from Phase 1.

---
