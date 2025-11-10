# Phase 3 Component 9.1 - Test Suite Summary

## TDD Red Phase - Tests Written (NOT IMPLEMENTED YET)

**Status**: 43 failing tests ready to drive implementation

**Location**: `/home/user/corazonn/firmware/heartbeat_phase3/test/test_component_9_1.cpp`

**Framework**: Unity + PlatformIO native testing

**Test Pattern**: Static code analysis (parse `src/main.cpp` as text, verify patterns exist)

---

## Test Coverage by Component Task

### CATEGORY 1: PROJECT STRUCTURE & FILE TESTS (Task 1.1)
**2 tests** - Verifies project initialization
- `test_source_file_exists` - Confirms src/main.cpp exists and is >100 chars
- `test_file_header_comment_exists` - Verifies file header with Phase 3 identification

### CATEGORY 2: INCLUDES TESTS (Task 1.2)
**5 tests** - Verifies all required includes present
- `test_include_arduino_h` - #include <Arduino.h>
- `test_include_wifi_h` - #include <WiFi.h>
- `test_include_wifiudp_h` - #include <WiFiUdp.h>
- `test_include_oscmessage_h` - #include <OSCMessage.h>
- `test_includes_well_formed` - Verifies includes use correct < > syntax

### CATEGORY 3: NETWORK CONFIGURATION TESTS (Task 1.3)
**5 tests** - Verifies network constants defined
- `test_config_wifi_ssid_defined` - const char* WIFI_SSID = "heartbeat-install"
- `test_config_wifi_password_defined` - const char* WIFI_PASSWORD
- `test_config_server_ip_defined` - const IPAddress SERVER_IP with 4 octets
- `test_config_server_port_defined` - const uint16_t SERVER_PORT = 8000
- `test_config_wifi_timeout_defined` - const unsigned long WIFI_TIMEOUT_MS = 30000

### CATEGORY 4: HARDWARE CONFIGURATION TESTS (Task 1.4)
**7 tests** - Verifies hardware constants and static assertions
- `test_config_sensor_pins_defined` - const int SENSOR_PINS[4] = {32, 33, 34, 35}
- `test_config_num_sensors_defined` - const int NUM_SENSORS = 4
- `test_config_status_led_pin_defined` - const int STATUS_LED_PIN = 2
- `test_config_adc_resolution_defined` - const int ADC_RESOLUTION = 12
- `test_hardware_config_is_const` - Verifies all 4 hardware constants exist
- `test_static_assertion_array_size` - Verifies static_assert present
- `test_static_assertion_num_sensors` - Verifies static_assert(NUM_SENSORS == 4)

### CATEGORY 5: SIGNAL PROCESSING PARAMETERS TESTS (Task 1.5)
**7 tests** - Verifies signal processing constants
- `test_config_sample_rate_hz_defined` - const int SAMPLE_RATE_HZ = 50
- `test_config_sample_interval_ms_defined` - const int SAMPLE_INTERVAL_MS = 20
- `test_config_moving_avg_samples_defined` - const int MOVING_AVG_SAMPLES = 5
- `test_config_baseline_decay_rate_defined` - const float BASELINE_DECAY_RATE = 0.1
- `test_config_baseline_decay_interval_defined` - const int BASELINE_DECAY_INTERVAL = 150
- `test_signal_processing_is_const` - Verifies all signal processing constants
- `test_config_sample_interval_calculation` - Validates SAMPLE_INTERVAL_MS = 1000 / SAMPLE_RATE_HZ

### CATEGORY 6: BEAT DETECTION PARAMETERS TESTS (Task 1.6)
**6 tests** - Verifies beat detection constants
- `test_config_threshold_fraction_defined` - const float THRESHOLD_FRACTION = 0.6
- `test_config_min_signal_range_defined` - const int MIN_SIGNAL_RANGE = 50
- `test_config_refractory_period_ms_defined` - const unsigned long REFRACTORY_PERIOD_MS = 300
- `test_config_flat_signal_threshold_defined` - const int FLAT_SIGNAL_THRESHOLD = 5
- `test_config_disconnect_timeout_ms_defined` - const unsigned long DISCONNECT_TIMEOUT_MS = 1000
- `test_beat_detection_is_const` - Verifies all beat detection constants

### CATEGORY 7: DEBUG CONFIGURATION TESTS (Task 1.7)
**3 tests** - Verifies debug level macro
- `test_config_debug_level_defined` - #define DEBUG_LEVEL present
- `test_config_debug_level_valid` - DEBUG_LEVEL is 0, 1, or 2
- `test_config_debug_level_active` - DEBUG_LEVEL is active (not commented)

### CATEGORY 8: CONFIGURATION VALIDATION TESTS (Task 1.8)
**5 tests** - Validates all configurations work together
- `test_all_config_constants_defined` - All 21 constants present
- `test_config_array_size_consistency` - SENSOR_PINS[4] matches NUM_SENSORS=4
- `test_config_has_section_comments` - Configuration documented with comments
- `test_config_constants_used_descriptively` - At least 13 named constants
- `test_config_sensor_pins_valid_gpios` - Pins 32, 33, 34, 35 present

### CATEGORY 9: INTEGRATION TESTS
**3 tests** - Validates overall file structure
- `test_config_organization_order` - Includes before configuration
- `test_config_no_duplicates` - No duplicate constant definitions
- `test_configuration_file_structure` - File >500 chars with both comments and code

---

## What Tests Expect (TRD Task Requirements)

### Task 1.1: Create project directory
- ✓ Directory structure created
- ✓ platformio.ini copied from Phase 1
- ✓ src/, lib/, include/, test/ directories exist

### Task 1.2: Create main.cpp with header and includes
Tests verify:
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
```

### Task 1.3: Add network configuration constants
Tests verify:
```cpp
// Network Configuration
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);
const uint16_t SERVER_PORT = 8000;
const unsigned long WIFI_TIMEOUT_MS = 30000;
```

### Task 1.4: Add hardware configuration constants + static_assert
Tests verify:
```cpp
// Hardware Configuration
const int SENSOR_PINS[4] = {32, 33, 34, 35};
const int NUM_SENSORS = 4;
const int STATUS_LED_PIN = 2;
const int ADC_RESOLUTION = 12;

static_assert(sizeof(SENSOR_PINS)/sizeof(SENSOR_PINS[0]) == NUM_SENSORS, ...);
static_assert(NUM_SENSORS == 4, ...);
```

### Task 1.5: Add signal processing parameters
Tests verify:
```cpp
// Signal Processing Parameters
const int SAMPLE_RATE_HZ = 50;
const int SAMPLE_INTERVAL_MS = 20;  // Must equal 1000/50
const int MOVING_AVG_SAMPLES = 5;
const float BASELINE_DECAY_RATE = 0.1;
const int BASELINE_DECAY_INTERVAL = 150;
```

### Task 1.6: Add beat detection parameters
Tests verify:
```cpp
// Beat Detection Parameters
const float THRESHOLD_FRACTION = 0.6;
const int MIN_SIGNAL_RANGE = 50;
const unsigned long REFRACTORY_PERIOD_MS = 300;
const int FLAT_SIGNAL_THRESHOLD = 5;
const unsigned long DISCONNECT_TIMEOUT_MS = 1000;
```

### Task 1.7: Add debug level configuration
Tests verify:
```cpp
// Debug Configuration
#define DEBUG_LEVEL 1  // 0=production, 1=testing, 2=verbose
```

### Task 1.8: Validate configuration compiles
Tests verify:
- All constants present with correct types
- SAMPLE_INTERVAL_MS = 1000 / SAMPLE_RATE_HZ (20 = 1000/50)
- SENSOR_PINS array size matches NUM_SENSORS
- Static assertions verify array bounds
- File is well-structured and documented

---

## Test Execution Guide

### When to Run Tests

Tests will FAIL until implementation is complete:

```bash
cd /home/user/corazonn/firmware/heartbeat_phase3
pio test -e test_component_9_1
```

Expected behavior:
- Red phase: All 43 tests FAIL (src/main.cpp doesn't exist)
- Green phase: After creating src/main.cpp with all constants, tests PASS
- Refactor phase: Improve code organization while keeping tests passing

### Running Tests Locally Without PlatformIO

If PlatformIO is not available, compile tests manually:

```bash
cd /home/user/corazonn/firmware/heartbeat_phase3/test
g++ -std=c++11 \
    -I. \
    -DUNITY_INCLUDE_PRINT_FORMATTED \
    test_component_9_1.cpp \
    -o test_runner
./test_runner
```

---

## Critical Implementation Notes

The following implementation details are CRITICAL for tests to pass:

1. **Array Declaration**
   - MUST be: `const int SENSOR_PINS[4] = {32, 33, 34, 35};`
   - Tests verify all 4 pin numbers (32, 33, 34, 35) are present
   - Tests verify array size is exactly [4]

2. **Static Assertions**
   - MUST include: `static_assert(NUM_SENSORS == 4, ...);`
   - MUST include: Array bounds check via static_assert
   - Tests check for presence of `static_assert` keyword

3. **Constant Values**
   - SAMPLE_INTERVAL_MS = 20 (must be 1000 / SAMPLE_RATE_HZ where SAMPLE_RATE_HZ = 50)
   - THRESHOLD_FRACTION = 0.6 (floating point, must match regex)
   - BASELINE_DECAY_RATE = 0.1 (floating point, must match regex)
   - All network/hardware/detection constants must use EXACT values specified

4. **Debug Level**
   - MUST be: `#define DEBUG_LEVEL` with value 0, 1, or 2
   - MUST NOT be commented out
   - Tests use `pattern_active()` to verify it's active (not on a // line)

5. **File Structure**
   - Must be >500 characters
   - Must include both C++ comments (//) and block comments (/** */)
   - Includes should come BEFORE configuration constants
   - Configuration should be organized by section

---

## Next Steps

1. **Read this summary** to understand what main.cpp needs
2. **Create src/main.cpp** with all 4+ sections of configuration
3. **Run tests**: `pio test -e test_component_9_1`
4. **All 43 tests should PASS**
5. **Then proceed to Tasks 2.x** (data structures) which have their own tests

---

## Test Categories Summary

| Category | Tests | Task | Status |
|----------|-------|------|--------|
| Project Structure | 2 | 1.1 | Red (failing) |
| Includes | 5 | 1.2 | Red (failing) |
| Network Config | 5 | 1.3 | Red (failing) |
| Hardware Config | 7 | 1.4 | Red (failing) |
| Signal Processing | 7 | 1.5 | Red (failing) |
| Beat Detection | 6 | 1.6 | Red (failing) |
| Debug Config | 3 | 1.7 | Red (failing) |
| Validation | 5 | 1.8 | Red (failing) |
| Integration | 3 | All | Red (failing) |
| **TOTAL** | **43** | **1.1-1.8** | **Red Phase Complete** |

---

## Files Created

- `/home/user/corazonn/firmware/heartbeat_phase3/` - Project directory
- `/home/user/corazonn/firmware/heartbeat_phase3/test/test_component_9_1.cpp` - Test suite (643 lines, 43 tests)
- `/home/user/corazonn/firmware/heartbeat_phase3/test/test_helpers.h` - Test utilities (copied from Phase 1)
- `/home/user/corazonn/firmware/heartbeat_phase3/platformio.ini` - Build config with test environment
