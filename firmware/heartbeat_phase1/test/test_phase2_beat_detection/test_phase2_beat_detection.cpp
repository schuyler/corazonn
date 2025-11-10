/**
 * Test Suite for Components 8.6-8.9: Beat Detection and Main Program Flow
 *
 * Tests new Phase 2 beat detection functions and main program flow updates
 * Framework: PlatformIO native testing (Unity)
 *
 * This test suite validates:
 * Component 8.6: Disconnection detection function (checkDisconnection)
 * Component 8.7: Beat detection function (detectBeat)
 * Component 8.8: LED status function updates (updateLED modifications)
 * Component 8.9: Main program flow updates (setup and loop modifications)
 *
 * Testing Strategy: Static code analysis (text search and regex)
 * - No runtime testing (no hardware dependencies)
 * - Validates function signatures, presence, logic patterns
 * - Checks for correct implementation patterns and state management
 */

#include <unity.h>
#include <cstring>
#include <cstdio>
#include "test_helpers.h"

// ============================================================================
// TEST SETUP & TEARDOWN
// ============================================================================

void setUp(void) {
    // No embedded state to reset for static tests
}

void tearDown(void) {
    // Cleanup
}

// ============================================================================
// CATEGORY 1: CHECKDISCONNECTION FUNCTION (Component 8.6, TRD §6.4)
// ============================================================================

/**
 * TEST 1.1: checkDisconnection function declared
 * Requirement: void checkDisconnection(int rawValue) function exists
 */
void test_check_disconnection_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void checkDisconnection"));
}

/**
 * TEST 1.2: checkDisconnection has correct signature
 * Requirement: Takes int parameter (rawValue)
 */
void test_check_disconnection_signature(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for function signature with int parameter
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+checkDisconnection\\s*\\(\\s*int\\s+\\w+\\s*\\)"));
}

/**
 * TEST 1.3: checkDisconnection implements variance check (R12)
 * Requirement: Calculate variance = abs(rawValue - lastRawValue)
 */
void test_check_disconnection_variance_calculation(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for variance calculation using abs() and lastRawValue
    TEST_ASSERT_TRUE(source_contains(func_body, "abs"));
    TEST_ASSERT_TRUE(source_contains(func_body, "lastRawValue"));
}

/**
 * TEST 1.4: checkDisconnection checks flat signal threshold (R12)
 * Requirement: Compare variance < FLAT_SIGNAL_THRESHOLD
 */
void test_check_disconnection_flat_signal_threshold(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for comparison with FLAT_SIGNAL_THRESHOLD
    TEST_ASSERT_TRUE(source_contains(func_body, "FLAT_SIGNAL_THRESHOLD"));
}

/**
 * TEST 1.5: checkDisconnection increments flatSampleCount (R12)
 * Requirement: Increment flatSampleCount when variance is low
 */
void test_check_disconnection_flat_sample_count_increment(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for flatSampleCount increment
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "flatSampleCount\\s*(\\+\\+|\\+=)"));
}

/**
 * TEST 1.6: checkDisconnection resets flatSampleCount (R12)
 * Requirement: Reset flatSampleCount = 0 when variance is high
 */
void test_check_disconnection_flat_sample_count_reset(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for flatSampleCount = 0 assignment
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "flatSampleCount\\s*=\\s*0"));
}

/**
 * TEST 1.7: checkDisconnection implements disconnection threshold (R13)
 * Requirement: Check flatSampleCount >= 50 (1 second @ 50Hz)
 */
void test_check_disconnection_threshold_check(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for threshold comparison (50 samples or constant)
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "flatSampleCount\\s*>=\\s*(50|\\w+)"));
}

/**
 * TEST 1.8: checkDisconnection implements range check (R14)
 * Requirement: Calculate range = maxValue - minValue, check < MIN_SIGNAL_RANGE
 */
void test_check_disconnection_range_check(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for range calculation and MIN_SIGNAL_RANGE comparison
    TEST_ASSERT_TRUE(source_contains(func_body, "MIN_SIGNAL_RANGE"));
    TEST_ASSERT_TRUE(source_contains(func_body, "maxValue"));
    TEST_ASSERT_TRUE(source_contains(func_body, "minValue"));
}

/**
 * TEST 1.9: checkDisconnection sets isConnected false (R13, R14)
 * Requirement: Set sensor.isConnected = false when disconnected
 */
void test_check_disconnection_sets_isconnected_false(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for isConnected = false assignment
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "isConnected\\s*=\\s*false"));
}

/**
 * TEST 1.10: checkDisconnection implements reconnection detection (R15)
 * Requirement: Detect reconnection when signal shows variation
 */
void test_check_disconnection_reconnection_detection(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for isConnected = true assignment (reconnection)
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "isConnected\\s*=\\s*true"));
}

/**
 * TEST 1.11: checkDisconnection resets baseline on reconnection (R15)
 * Requirement: Reset minValue = maxValue = smoothedValue on reconnection
 */
void test_check_disconnection_reconnection_baseline_reset(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for baseline reset assignments
    // Should have assignments to minValue and maxValue with smoothedValue
    TEST_ASSERT_TRUE(source_contains(func_body, "smoothedValue"));
}

/**
 * TEST 1.12: checkDisconnection updates lastRawValue (R16)
 * Requirement: Update sensor.lastRawValue = rawValue at end
 */
void test_check_disconnection_updates_last_raw_value(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Look for lastRawValue assignment
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "lastRawValue\\s*="));
}

// ============================================================================
// CATEGORY 2: DETECTBEAT FUNCTION (Component 8.7, TRD §6.5)
// ============================================================================

/**
 * TEST 2.1: detectBeat function declared
 * Requirement: void detectBeat() function exists
 */
void test_detect_beat_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void detectBeat"));
}

/**
 * TEST 2.2: detectBeat has correct signature
 * Requirement: No parameters (void)
 */
void test_detect_beat_signature(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for function with no parameters
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+detectBeat\\s*\\(\\s*\\)"));
}

/**
 * TEST 2.3: detectBeat checks sensor connection (R17 prerequisite)
 * Requirement: Return early if sensor not connected
 */
void test_detect_beat_connection_check(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for isConnected check
    TEST_ASSERT_TRUE(source_contains(func_body, "isConnected"));
}

/**
 * TEST 2.4: detectBeat calculates threshold (R17)
 * Requirement: threshold = minValue + (maxValue - minValue) * THRESHOLD_FRACTION
 */
void test_detect_beat_threshold_calculation(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for threshold calculation with THRESHOLD_FRACTION
    TEST_ASSERT_TRUE(source_contains(func_body, "THRESHOLD_FRACTION"));
    TEST_ASSERT_TRUE(source_contains(func_body, "threshold"));
}

/**
 * TEST 2.5: detectBeat implements rising edge detection (R18)
 * Requirement: Check smoothedValue >= threshold AND !aboveThreshold
 */
void test_detect_beat_rising_edge_detection(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for rising edge condition
    TEST_ASSERT_TRUE(source_contains(func_body, "smoothedValue"));
    TEST_ASSERT_TRUE(source_contains(func_body, "threshold"));
    TEST_ASSERT_TRUE(source_contains(func_body, "aboveThreshold"));
}

/**
 * TEST 2.6: detectBeat implements refractory period check (R19)
 * Requirement: Check timeSinceLastBeat < REFRACTORY_PERIOD_MS BEFORE setting state
 */
void test_detect_beat_refractory_period_check(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for refractory period check with REFRACTORY_PERIOD_MS
    TEST_ASSERT_TRUE(source_contains(func_body, "REFRACTORY_PERIOD_MS"));
    TEST_ASSERT_TRUE(source_contains(func_body, "lastBeatTime"));
}

/**
 * TEST 2.7: detectBeat calculates time since last beat (R19)
 * Requirement: Calculate timeSinceLastBeat = millis() - lastBeatTime
 */
void test_detect_beat_time_since_last_beat(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for time since last beat calculation
    TEST_ASSERT_TRUE(source_contains(func_body, "millis()"));
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "millis\\s*\\(\\s*\\)\\s*-\\s*\\w*lastBeatTime"));
}

/**
 * TEST 2.8: detectBeat sets aboveThreshold AFTER refractory check (R19)
 * Requirement: Only set aboveThreshold = true if refractory period passed
 */
void test_detect_beat_above_threshold_after_refractory(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for aboveThreshold = true assignment
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "aboveThreshold\\s*=\\s*true"));
}

/**
 * TEST 2.9: detectBeat handles first beat detection (R20)
 * Requirement: Check firstBeatDetected flag, handle first beat specially
 */
void test_detect_beat_first_beat_detection(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for firstBeatDetected check
    TEST_ASSERT_TRUE(source_contains(func_body, "firstBeatDetected"));
}

/**
 * TEST 2.10: detectBeat sets firstBeatDetected true (R20)
 * Requirement: Set sensor.firstBeatDetected = true on first beat
 */
void test_detect_beat_sets_first_beat_detected(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for firstBeatDetected = true assignment
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "firstBeatDetected\\s*=\\s*true"));
}

/**
 * TEST 2.11: detectBeat calculates IBI for subsequent beats (R20)
 * Requirement: Calculate ibi = millis() - lastBeatTime for beats after first
 */
void test_detect_beat_ibi_calculation(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for IBI (inter-beat interval) calculation or variable
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "\\bibi\\b"));
}

/**
 * TEST 2.12: detectBeat stores IBI (R20)
 * Requirement: Store sensor.lastIBI = ibi
 */
void test_detect_beat_stores_ibi(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for lastIBI assignment
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "lastIBI\\s*="));
}

/**
 * TEST 2.13: detectBeat sends OSC message (R20)
 * Requirement: Call sendHeartbeatOSC(ibi) for valid beats
 */
void test_detect_beat_sends_osc(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for sendHeartbeatOSC call
    TEST_ASSERT_TRUE(source_contains(func_body, "sendHeartbeatOSC"));
}

/**
 * TEST 2.14: detectBeat triggers LED pulse (R20)
 * Requirement: Set ledPulseTime = millis() on valid beat
 */
void test_detect_beat_triggers_led_pulse(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for ledPulseTime assignment
    TEST_ASSERT_TRUE(source_contains(func_body, "ledPulseTime"));
}

/**
 * TEST 2.15: detectBeat implements falling edge detection (R21)
 * Requirement: Reset aboveThreshold = false when signal drops below threshold
 */
void test_detect_beat_falling_edge_detection(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for falling edge (aboveThreshold = false)
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "aboveThreshold\\s*=\\s*false"));
}

/**
 * TEST 2.16: detectBeat updates lastBeatTime (R20)
 * Requirement: Update sensor.lastBeatTime = millis() on valid beat
 */
void test_detect_beat_updates_last_beat_time(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Look for lastBeatTime = millis() assignment
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "lastBeatTime\\s*=\\s*millis"));
}

// ============================================================================
// CATEGORY 3: UPDATELED FUNCTION MODIFICATIONS (Component 8.8, TRD §6.7)
// ============================================================================

/**
 * TEST 3.1: updateLED function exists (Phase 1 preserved)
 * Requirement: void updateLED() function still exists
 */
void test_update_led_exists(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void updateLED"));
}

/**
 * TEST 3.2: updateLED has correct signature
 * Requirement: No parameters (void)
 */
void test_update_led_signature(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for function with no parameters
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+updateLED\\s*\\(\\s*\\)"));
}

/**
 * TEST 3.3: updateLED checks WiFi connection state (R22, R24)
 * Requirement: Check state.wifiConnected
 */
void test_update_led_wifi_check(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "updateLED");

    // Look for wifiConnected check
    TEST_ASSERT_TRUE(source_contains(func_body, "wifiConnected"));
}

/**
 * TEST 3.4: updateLED implements WiFi connecting blink (R22)
 * Requirement: Blink at 5 Hz (100ms on/off) when WiFi not connected
 */
void test_update_led_wifi_connecting_blink(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "updateLED");

    // Look for blink pattern using millis() / 100
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "millis\\s*\\(\\s*\\)\\s*/\\s*100"));
}

/**
 * TEST 3.5: updateLED implements beat pulse check (R23)
 * Requirement: Check if (millis() - ledPulseTime < 50)
 */
void test_update_led_beat_pulse_check(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "updateLED");

    // Look for ledPulseTime check with 50ms threshold
    TEST_ASSERT_TRUE(source_contains(func_body, "ledPulseTime"));
    TEST_ASSERT_TRUE(source_contains(func_body, "50"));
}

/**
 * TEST 3.6: updateLED implements state priority (R24)
 * Requirement: Priority order: WiFi blink > beat pulse > solid on
 */
void test_update_led_state_priority(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "updateLED");

    // Look for conditional structure (if-else or multiple digitalWrite calls)
    int if_count = count_pattern_occurrences(func_body, "if");
    TEST_ASSERT_GREATER_OR_EQUAL(1, if_count);
}

/**
 * TEST 3.7: updateLED writes to LED pin (R22-R24)
 * Requirement: Call digitalWrite(STATUS_LED_PIN, ...)
 */
void test_update_led_digital_write(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "updateLED");

    // Look for digitalWrite calls
    TEST_ASSERT_TRUE(source_contains(func_body, "digitalWrite"));
    TEST_ASSERT_TRUE(source_contains(func_body, "STATUS_LED_PIN"));
}

// ============================================================================
// CATEGORY 4: SETUP() MODIFICATIONS (Component 8.9, TRD §7.1)
// ============================================================================

/**
 * TEST 4.1: setup() function exists
 * Requirement: void setup() function preserved from Phase 1
 */
void test_setup_exists(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void setup()"));
}

/**
 * TEST 4.2: setup() calls initializeSensor (R30)
 * Requirement: Call initializeSensor() to configure ADC and buffers
 */
void test_setup_calls_initialize_sensor(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "setup");

    // Look for initializeSensor() call
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "initializeSensor\\s*\\(\\s*\\)"));
}

/**
 * TEST 4.3: setup() initializes Serial (Phase 1 preserved)
 * Requirement: Serial.begin(115200) still present
 */
void test_setup_serial_init(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "setup");

    // Look for Serial.begin
    TEST_ASSERT_TRUE(source_contains(func_body, "Serial.begin"));
    TEST_ASSERT_TRUE(source_contains(func_body, "115200"));
}

/**
 * TEST 4.4: setup() configures LED pin (Phase 1 preserved)
 * Requirement: pinMode(STATUS_LED_PIN, OUTPUT)
 */
void test_setup_led_pin_config(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "setup");

    // Look for LED pin configuration
    TEST_ASSERT_TRUE(source_contains(func_body, "pinMode"));
    TEST_ASSERT_TRUE(source_contains(func_body, "STATUS_LED_PIN"));
    TEST_ASSERT_TRUE(source_contains(func_body, "OUTPUT"));
}

/**
 * TEST 4.5: setup() connects WiFi (Phase 1 preserved)
 * Requirement: Call connectWiFi()
 */
void test_setup_wifi_connection(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "setup");

    // Look for connectWiFi call
    TEST_ASSERT_TRUE(source_contains(func_body, "connectWiFi"));
}

/**
 * TEST 4.6: setup() initializes UDP (Phase 1 preserved)
 * Requirement: udp.begin(0)
 */
void test_setup_udp_init(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "setup");

    // Look for udp.begin
    TEST_ASSERT_TRUE(source_contains(func_body, "udp.begin"));
}

// ============================================================================
// CATEGORY 5: LOOP() COMPLETE REWRITE (Component 8.9, TRD §7.2)
// ============================================================================

/**
 * TEST 5.1: loop() function exists
 * Requirement: void loop() function preserved
 */
void test_loop_exists(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void loop()"));
}

/**
 * TEST 5.2: loop() implements sampling timing (R32)
 * Requirement: Check timing with lastSampleTime and SAMPLE_INTERVAL_MS
 */
void test_loop_sampling_timing(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for lastSampleTime variable and SAMPLE_INTERVAL_MS check
    TEST_ASSERT_TRUE(source_contains(func_body, "lastSampleTime"));
    TEST_ASSERT_TRUE(source_contains(func_body, "SAMPLE_INTERVAL_MS"));
}

/**
 * TEST 5.3: loop() uses static variable for timing (R32)
 * Requirement: static unsigned long lastSampleTime
 */
void test_loop_static_sample_time(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for static lastSampleTime declaration
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "static\\s+unsigned\\s+long\\s+lastSampleTime"));
}

/**
 * TEST 5.4: loop() reads ADC (R33)
 * Requirement: int rawValue = analogRead(SENSOR_PIN)
 */
void test_loop_adc_reading(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for analogRead call
    TEST_ASSERT_TRUE(source_contains(func_body, "analogRead"));
    TEST_ASSERT_TRUE(source_contains(func_body, "SENSOR_PIN"));
}

/**
 * TEST 5.5: loop() calls updateMovingAverage (R34)
 * Requirement: Call updateMovingAverage(rawValue) in signal processing pipeline
 */
void test_loop_calls_update_moving_average(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for updateMovingAverage call
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "updateMovingAverage\\s*\\("));
}

/**
 * TEST 5.6: loop() calls updateBaseline (R34)
 * Requirement: Call updateBaseline() in signal processing pipeline
 */
void test_loop_calls_update_baseline(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for updateBaseline call
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "updateBaseline\\s*\\("));
}

/**
 * TEST 5.7: loop() calls checkDisconnection (R34)
 * Requirement: Call checkDisconnection(rawValue) in signal processing pipeline
 */
void test_loop_calls_check_disconnection(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for checkDisconnection call
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "checkDisconnection\\s*\\("));
}

/**
 * TEST 5.8: loop() calls detectBeat (R35)
 * Requirement: Call detectBeat() for heartbeat detection
 */
void test_loop_calls_detect_beat(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for detectBeat call
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "detectBeat\\s*\\("));
}

/**
 * TEST 5.9: loop() calls checkWiFi (R36)
 * Requirement: Call checkWiFi() for WiFi status monitoring
 */
void test_loop_calls_check_wifi(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for checkWiFi call
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "checkWiFi\\s*\\("));
}

/**
 * TEST 5.10: loop() calls updateLED (R37)
 * Requirement: Call updateLED() for LED status indication
 */
void test_loop_calls_update_led(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for updateLED call
    TEST_ASSERT_TRUE(source_matches_regex(func_body, "updateLED\\s*\\("));
}

/**
 * TEST 5.11: loop() has minimal delay (R38)
 * Requirement: delay(1) for WiFi background tasks
 */
void test_loop_minimal_delay(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for delay call
    TEST_ASSERT_TRUE(source_contains(func_body, "delay"));
}

/**
 * TEST 5.12: loop() uses loopCounter for debug throttling (R39)
 * Requirement: Increment state.loopCounter for throttled debug output
 */
void test_loop_loop_counter(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Look for loopCounter (may be optional debug code)
    // This is optional per TRD, so we just check if it exists
    bool has_loop_counter = source_contains(func_body, "loopCounter");
    // No assertion - this is optional debug feature
    (void)has_loop_counter; // Suppress unused warning
}

/**
 * TEST 5.13: loop() Phase 1 test code removed
 * Requirement: TEST_MESSAGE_INTERVAL_MS logic removed
 */
void test_loop_phase1_test_code_removed(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Verify TEST_MESSAGE_INTERVAL_MS is NOT actively used in loop
    TEST_ASSERT_FALSE(pattern_active(func_body, "TEST_MESSAGE_INTERVAL_MS"));
}

/**
 * TEST 5.14: loop() Phase 1 messageCounter removed
 * Requirement: messageCounter logic removed from loop
 */
void test_loop_message_counter_removed(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Verify messageCounter is NOT actively used in loop
    TEST_ASSERT_FALSE(pattern_active(func_body, "messageCounter"));
}

/**
 * TEST 5.15: loop() implements proper signal processing order (R34)
 * Requirement: Pipeline order: updateMovingAverage -> updateBaseline -> checkDisconnection
 */
void test_loop_signal_processing_order(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Find positions of function calls
    size_t pos_moving_avg = func_body.find("updateMovingAverage");
    size_t pos_baseline = func_body.find("updateBaseline");
    size_t pos_disconnect = func_body.find("checkDisconnection");

    // Verify all functions are called
    TEST_ASSERT_TRUE(pos_moving_avg != std::string::npos);
    TEST_ASSERT_TRUE(pos_baseline != std::string::npos);
    TEST_ASSERT_TRUE(pos_disconnect != std::string::npos);

    // Verify proper order (moving average -> baseline -> disconnection)
    TEST_ASSERT_TRUE(pos_moving_avg < pos_baseline);
    TEST_ASSERT_TRUE(pos_baseline < pos_disconnect);
}

// ============================================================================
// CATEGORY 6: INTEGRATION TESTS
// ============================================================================

/**
 * TEST 6.1: All new Phase 2 beat detection functions declared
 * Requirement: checkDisconnection and detectBeat functions exist
 */
void test_all_beat_detection_functions_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    int function_count = 0;
    if (source_contains(source, "void checkDisconnection")) function_count++;
    if (source_contains(source, "void detectBeat")) function_count++;

    // Should have both new functions
    TEST_ASSERT_EQUAL(2, function_count);
}

/**
 * TEST 6.2: All Phase 2 signal processing functions exist
 * Requirement: All 5 Phase 2 functions implemented (8.3-8.7)
 */
void test_all_phase2_signal_functions_exist(void) {
    std::string source = read_source_file("src/main.cpp");

    int function_count = 0;
    if (source_contains(source, "void initializeSensor")) function_count++;
    if (source_contains(source, "void updateMovingAverage")) function_count++;
    if (source_contains(source, "void updateBaseline")) function_count++;
    if (source_contains(source, "void checkDisconnection")) function_count++;
    if (source_contains(source, "void detectBeat")) function_count++;

    // Should have all 5 signal processing functions
    TEST_ASSERT_EQUAL(5, function_count);
}

/**
 * TEST 6.3: Beat detection integrates with signal processing
 * Requirement: detectBeat uses smoothedValue, minValue, maxValue from signal processing
 */
void test_beat_detection_signal_integration(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Verify detectBeat uses signal processing outputs
    TEST_ASSERT_TRUE(source_contains(func_body, "smoothedValue"));
    TEST_ASSERT_TRUE(source_contains(func_body, "minValue"));
    TEST_ASSERT_TRUE(source_contains(func_body, "maxValue"));
}

/**
 * TEST 6.4: Beat detection integrates with OSC transmission
 * Requirement: detectBeat calls sendHeartbeatOSC from Phase 1
 */
void test_beat_detection_osc_integration(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Verify detectBeat calls OSC transmission
    TEST_ASSERT_TRUE(source_contains(func_body, "sendHeartbeatOSC"));
}

/**
 * TEST 6.5: Beat detection integrates with LED indication
 * Requirement: detectBeat sets ledPulseTime for LED pulse
 */
void test_beat_detection_led_integration(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "detectBeat");

    // Verify detectBeat triggers LED pulse
    TEST_ASSERT_TRUE(source_contains(func_body, "ledPulseTime"));
}

/**
 * TEST 6.6: Disconnection detection integrates with signal processing
 * Requirement: checkDisconnection uses maxValue, minValue from baseline tracking
 */
void test_disconnection_signal_integration(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "checkDisconnection");

    // Verify checkDisconnection uses baseline values
    TEST_ASSERT_TRUE(source_contains(func_body, "maxValue"));
    TEST_ASSERT_TRUE(source_contains(func_body, "minValue"));
}

/**
 * TEST 6.7: Main loop integrates all components
 * Requirement: loop() calls all signal processing and detection functions
 */
void test_loop_integrates_all_components(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string func_body = extract_function_body(source, "loop");

    // Verify loop calls all major functions
    int function_calls = 0;
    if (source_contains(func_body, "updateMovingAverage")) function_calls++;
    if (source_contains(func_body, "updateBaseline")) function_calls++;
    if (source_contains(func_body, "checkDisconnection")) function_calls++;
    if (source_contains(func_body, "detectBeat")) function_calls++;
    if (source_contains(func_body, "checkWiFi")) function_calls++;
    if (source_contains(func_body, "updateLED")) function_calls++;

    // Should call all 6 integration functions
    TEST_ASSERT_GREATER_OR_EQUAL(6, function_calls);
}

/**
 * TEST 6.8: Phase 1 functions preserved
 * Requirement: connectWiFi, sendHeartbeatOSC, checkWiFi still exist
 */
void test_phase1_functions_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "bool connectWiFi"));
    TEST_ASSERT_TRUE(source_contains(source, "void sendHeartbeatOSC"));
    TEST_ASSERT_TRUE(source_contains(source, "void checkWiFi"));
}

/**
 * TEST 6.9: Phase 2 uses Phase 1 WiFi infrastructure
 * Requirement: WiFiUDP, OSC includes, and functions preserved
 */
void test_phase2_uses_phase1_wifi(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify Phase 1 WiFi infrastructure preserved
    TEST_ASSERT_TRUE(source_contains(source, "#include <WiFi.h>"));
    TEST_ASSERT_TRUE(source_contains(source, "#include <OSCMessage.h>"));
    TEST_ASSERT_TRUE(source_contains(source, "WiFiUDP udp"));
}

/**
 * TEST 6.10: Complete Phase 2 implementation
 * Requirement: All components 8.1-8.9 integrated
 */
void test_complete_phase2_implementation(void) {
    std::string source = read_source_file("src/main.cpp");

    // Count all Phase 2 components
    int components = 0;

    // 8.1: Configuration constants (at least some key ones)
    if (source_contains(source, "SAMPLE_RATE_HZ")) components++;

    // 8.2: Data structures
    if (source_contains(source, "struct SensorState")) components++;

    // 8.3-8.7: Functions
    if (source_contains(source, "void initializeSensor")) components++;
    if (source_contains(source, "void updateMovingAverage")) components++;
    if (source_contains(source, "void updateBaseline")) components++;
    if (source_contains(source, "void checkDisconnection")) components++;
    if (source_contains(source, "void detectBeat")) components++;

    // 8.8: updateLED exists (modification)
    if (source_contains(source, "void updateLED")) components++;

    // 8.9: setup and loop exist
    if (source_contains(source, "void setup()")) components++;
    if (source_contains(source, "void loop()")) components++;

    // Should have all 10 components
    TEST_ASSERT_GREATER_OR_EQUAL(10, components);
}

// ============================================================================
// TEST RUNNER MAIN
// ============================================================================

int main(int argc, char* argv[]) {
    UNITY_BEGIN();

    // Category 1: checkDisconnection Function (Component 8.6, TRD §6.4)
    RUN_TEST(test_check_disconnection_declared);
    RUN_TEST(test_check_disconnection_signature);
    RUN_TEST(test_check_disconnection_variance_calculation);
    RUN_TEST(test_check_disconnection_flat_signal_threshold);
    RUN_TEST(test_check_disconnection_flat_sample_count_increment);
    RUN_TEST(test_check_disconnection_flat_sample_count_reset);
    RUN_TEST(test_check_disconnection_threshold_check);
    RUN_TEST(test_check_disconnection_range_check);
    RUN_TEST(test_check_disconnection_sets_isconnected_false);
    RUN_TEST(test_check_disconnection_reconnection_detection);
    RUN_TEST(test_check_disconnection_reconnection_baseline_reset);
    RUN_TEST(test_check_disconnection_updates_last_raw_value);

    // Category 2: detectBeat Function (Component 8.7, TRD §6.5)
    RUN_TEST(test_detect_beat_declared);
    RUN_TEST(test_detect_beat_signature);
    RUN_TEST(test_detect_beat_connection_check);
    RUN_TEST(test_detect_beat_threshold_calculation);
    RUN_TEST(test_detect_beat_rising_edge_detection);
    RUN_TEST(test_detect_beat_refractory_period_check);
    RUN_TEST(test_detect_beat_time_since_last_beat);
    RUN_TEST(test_detect_beat_above_threshold_after_refractory);
    RUN_TEST(test_detect_beat_first_beat_detection);
    RUN_TEST(test_detect_beat_sets_first_beat_detected);
    RUN_TEST(test_detect_beat_ibi_calculation);
    RUN_TEST(test_detect_beat_stores_ibi);
    RUN_TEST(test_detect_beat_sends_osc);
    RUN_TEST(test_detect_beat_triggers_led_pulse);
    RUN_TEST(test_detect_beat_falling_edge_detection);
    RUN_TEST(test_detect_beat_updates_last_beat_time);

    // Category 3: updateLED Function Modifications (Component 8.8, TRD §6.7)
    RUN_TEST(test_update_led_exists);
    RUN_TEST(test_update_led_signature);
    RUN_TEST(test_update_led_wifi_check);
    RUN_TEST(test_update_led_wifi_connecting_blink);
    RUN_TEST(test_update_led_beat_pulse_check);
    RUN_TEST(test_update_led_state_priority);
    RUN_TEST(test_update_led_digital_write);

    // Category 4: setup() Modifications (Component 8.9, TRD §7.1)
    RUN_TEST(test_setup_exists);
    RUN_TEST(test_setup_calls_initialize_sensor);
    RUN_TEST(test_setup_serial_init);
    RUN_TEST(test_setup_led_pin_config);
    RUN_TEST(test_setup_wifi_connection);
    RUN_TEST(test_setup_udp_init);

    // Category 5: loop() Complete Rewrite (Component 8.9, TRD §7.2)
    RUN_TEST(test_loop_exists);
    RUN_TEST(test_loop_sampling_timing);
    RUN_TEST(test_loop_static_sample_time);
    RUN_TEST(test_loop_adc_reading);
    RUN_TEST(test_loop_calls_update_moving_average);
    RUN_TEST(test_loop_calls_update_baseline);
    RUN_TEST(test_loop_calls_check_disconnection);
    RUN_TEST(test_loop_calls_detect_beat);
    RUN_TEST(test_loop_calls_check_wifi);
    RUN_TEST(test_loop_calls_update_led);
    RUN_TEST(test_loop_minimal_delay);
    RUN_TEST(test_loop_loop_counter);
    RUN_TEST(test_loop_phase1_test_code_removed);
    RUN_TEST(test_loop_message_counter_removed);
    RUN_TEST(test_loop_signal_processing_order);

    // Category 6: Integration Tests
    RUN_TEST(test_all_beat_detection_functions_declared);
    RUN_TEST(test_all_phase2_signal_functions_exist);
    RUN_TEST(test_beat_detection_signal_integration);
    RUN_TEST(test_beat_detection_osc_integration);
    RUN_TEST(test_beat_detection_led_integration);
    RUN_TEST(test_disconnection_signal_integration);
    RUN_TEST(test_loop_integrates_all_components);
    RUN_TEST(test_phase1_functions_preserved);
    RUN_TEST(test_phase2_uses_phase1_wifi);
    RUN_TEST(test_complete_phase2_implementation);

    return UNITY_END();
}
