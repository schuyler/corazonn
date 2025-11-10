# Phase 3 Component 9.1 - Test Implementation Report

**Date**: 2025-11-10  
**Component**: 9.1 - Project Structure & Configuration  
**Tasks Covered**: 1.1-1.8  
**Framework**: Unity + PlatformIO native testing  

---

## EXECUTIVE SUMMARY

**TDD Red Phase Complete**: 43 failing tests written to drive implementation of Phase 3 firmware configuration.

Tests are ready and will guide the creation of `src/main.cpp` with all required configuration constants for multi-sensor beat detection system.

**Next Step**: Create `src/main.cpp` with configuration constants (see IMPLEMENTATION_CHECKLIST.md)

---

## IMPLEMENTATION STATUS

| Component | Status | Details |
|-----------|--------|---------|
| Test Suite | ✓ Complete | 43 tests, 9 categories, 643 lines |
| Test Helpers | ✓ Complete | Copied from Phase 1 |
| Project Structure | ✓ Complete | src/, lib/, include/, test/ directories |
| platformio.ini | ✓ Complete | Configured with test environment |
| src/main.cpp | ⏳ Pending | Ready to implement (see checklist) |

---

## TEST SUITE DETAILS

### File Location
- **Test Code**: `/home/user/corazonn/firmware/heartbeat_phase3/test/test_component_9_1.cpp`
- **Test Helpers**: `/home/user/corazonn/firmware/heartbeat_phase3/test/test_helpers.h`
- **Config**: `/home/user/corazonn/firmware/heartbeat_phase3/platformio.ini`

### Test Counts by Category

```
CATEGORY 1: Project Structure & File Tests (Task 1.1)          2 tests
CATEGORY 2: Includes Tests (Task 1.2)                          5 tests
CATEGORY 3: Network Configuration Tests (Task 1.3)             5 tests
CATEGORY 4: Hardware Configuration Tests (Task 1.4)            7 tests
CATEGORY 5: Signal Processing Parameters Tests (Task 1.5)      7 tests
CATEGORY 6: Beat Detection Parameters Tests (Task 1.6)         6 tests
CATEGORY 7: Debug Configuration Tests (Task 1.7)               3 tests
CATEGORY 8: Configuration Validation Tests (Task 1.8)          5 tests
CATEGORY 9: Integration Tests                                  3 tests
─────────────────────────────────────────────────────────────────────
TOTAL                                                          43 tests
```

### Test Pattern: Static Code Analysis

Each test:
1. Reads `src/main.cpp` as text
2. Uses pattern matching to verify:
   - Required #include statements present
   - Configuration constants defined with correct names
   - Constant values match specifications (e.g., SAMPLE_RATE_HZ = 50)
   - Static assertions present
   - DEBUG_LEVEL macro active (not commented)
3. Asserts patterns found (or fails test)

**No embedded code execution** - purely static analysis.

---

## WHAT TESTS VERIFY

### Task 1.1: Project Directory Creation
- src/main.cpp exists
- File is >100 characters

### Task 1.2: File Header & Includes
- File has header comment identifying Phase 3
- All 4 required includes present:
  - #include <Arduino.h>
  - #include <WiFi.h>
  - #include <WiFiUdp.h>
  - #include <OSCMessage.h>

### Task 1.3: Network Configuration
- WIFI_SSID = "heartbeat-install"
- WIFI_PASSWORD defined
- SERVER_IP defined as IPAddress with 4 octets
- SERVER_PORT = 8000
- WIFI_TIMEOUT_MS = 30000

### Task 1.4: Hardware Configuration
- SENSOR_PINS[4] = {32, 33, 34, 35}
- NUM_SENSORS = 4
- STATUS_LED_PIN = 2
- ADC_RESOLUTION = 12
- static_assert present for array bounds
- static_assert(NUM_SENSORS == 4)

### Task 1.5: Signal Processing Parameters
- SAMPLE_RATE_HZ = 50
- SAMPLE_INTERVAL_MS = 20 (= 1000 / 50)
- MOVING_AVG_SAMPLES = 5
- BASELINE_DECAY_RATE = 0.1
- BASELINE_DECAY_INTERVAL = 150

### Task 1.6: Beat Detection Parameters
- THRESHOLD_FRACTION = 0.6
- MIN_SIGNAL_RANGE = 50
- REFRACTORY_PERIOD_MS = 300
- FLAT_SIGNAL_THRESHOLD = 5
- DISCONNECT_TIMEOUT_MS = 1000

### Task 1.7: Debug Configuration
- #define DEBUG_LEVEL present
- DEBUG_LEVEL = 0, 1, or 2
- DEBUG_LEVEL not commented out

### Task 1.8: Configuration Validation
- All 21 configuration constants present
- No duplicate definitions
- File >500 characters
- Organized with comments

---

## CRITICAL IMPLEMENTATION NOTES

### 1. Constant Declarations
All configuration constants must use `const`:
```cpp
const int SAMPLE_RATE_HZ = 50;
const float THRESHOLD_FRACTION = 0.6;
const unsigned long WIFI_TIMEOUT_MS = 30000;
```

Tests verify:
- Exact constant names (case-sensitive)
- Exact values (must match specifications)
- Types (const int, const float, etc.)

### 2. Array Declaration
Must be exactly:
```cpp
const int SENSOR_PINS[4] = {32, 33, 34, 35};
```

Tests verify:
- Array syntax [4]
- All 4 pin numbers present: 32, 33, 34, 35
- const int type

### 3. Static Assertions
Must be present:
```cpp
static_assert(sizeof(SENSOR_PINS)/sizeof(SENSOR_PINS[0]) == 4, "...");
static_assert(NUM_SENSORS == 4, "...");
```

Tests verify:
- Keyword `static_assert` present
- References to `NUM_SENSORS` and 4

### 4. Debug Macro
Must be:
```cpp
#define DEBUG_LEVEL 1  // or 0 or 2
```

Tests verify:
- `#define DEBUG_LEVEL` present
- Value is 0, 1, or 2
- Not commented out (checked with pattern_active())

### 5. Floating-Point Constants
Must use exact decimal representation:
```cpp
const float BASELINE_DECAY_RATE = 0.1;
const float THRESHOLD_FRACTION = 0.6;
```

Tests verify:
- Using regex matching for float values
- Exact representation (0.1, not 0.10 or .1)

---

## TEST EXECUTION

### Run Tests
```bash
cd /home/user/corazonn/firmware/heartbeat_phase3
pio test -e test_component_9_1
```

### Expected Results: RED PHASE (now)
- All 43 tests FAIL
- Reason: src/main.cpp doesn't exist

### Expected Results: GREEN PHASE (after implementation)
- All 43 tests PASS
- No failures or errors

---

## IMPLEMENTATION GUIDE

### Step 1: Create src/main.cpp
Use IMPLEMENTATION_CHECKLIST.md for exact requirements.

Minimum content:
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

// Placeholder to avoid linker errors
void setup() {}
void loop() {}
```

### Step 2: Verify Tests Pass
```bash
pio test -e test_component_9_1
# Expected: All 43 tests PASS
```

### Step 3: Continue to Component 9.2
After tests pass, proceed to data structures (Component 9.2).

---

## FILES CREATED

| File | Size | Purpose |
|------|------|---------|
| test_component_9_1.cpp | 643 lines | Main test suite (43 tests) |
| test_helpers.h | 132 lines | Test utility functions |
| platformio.ini | Updated | Added test environment config |
| TEST_SUMMARY.md | Complete | Detailed test documentation |
| IMPLEMENTATION_CHECKLIST.md | Complete | Exact implementation requirements |
| TEST_REPORT.md | This file | Executive summary |

---

## QUESTIONS & ANSWERS

**Q: Should I add setup() and loop() functions?**  
A: Optional. Tests ignore function bodies. You can add empty placeholders or wait for Task 9.x.

**Q: Can I add comments in the constants section?**  
A: YES. Comments are encouraged. Tests look for comments to verify organization.

**Q: What if a test fails after I implement?**  
A: Read the test name to identify what's missing. Check IMPLEMENTATION_CHECKLIST.md for exact syntax.

**Q: Can I modify the test file?**  
A: Not recommended. Tests are frozen for this TDD phase. Fix the implementation instead.

**Q: Do I need WiFi functions in this component?**  
A: No. Task 1.3 only requires constants. WiFi implementation (Task 8.2) comes later.

**Q: What about sensor structures and functions?**  
A: Those are Component 9.2+. This component is configuration only.

---

## VERIFICATION CHECKLIST

After implementing src/main.cpp:

- [ ] All 43 tests pass
- [ ] No compilation errors
- [ ] All constants have correct types (const int, const float, etc.)
- [ ] All values exactly match specifications
- [ ] Static assertions are present
- [ ] DEBUG_LEVEL is not commented out
- [ ] File contains section comments
- [ ] File is >500 characters
- [ ] Includes come before configuration

---

## NEXT STEPS

1. **Review** IMPLEMENTATION_CHECKLIST.md for exact requirements
2. **Create** `/home/user/corazonn/firmware/heartbeat_phase3/src/main.cpp`
3. **Run tests**: `pio test -e test_component_9_1`
4. **Verify** all 43 tests PASS
5. **Continue** to Component 9.2 (data structures)

---

## TEST FRAMEWORK

- **Framework**: Unity (PlatformIO native)
- **Platform**: native (runs on build machine, not ESP32)
- **Pattern**: Static analysis (parse and search text)
- **Dependencies**: test_helpers.h utility functions

---

## SUMMARY

**TDD Red Phase**: COMPLETE ✓
- 43 tests written
- All tests ready to fail
- Implementation checklist provided
- Clear specifications documented

**Next Phase**: GREEN (implement main.cpp)
- All 21 constants required
- Static assertions required
- Configuration sections documented
- Estimated implementation time: 10-15 minutes

**Status**: READY FOR IMPLEMENTATION

