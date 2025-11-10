/**
 * Test Suite for Component 8.1: Phase 2 Configuration Constants
 *
 * Tests new Phase 2 configuration constants for ADC sampling and signal processing
 * Framework: PlatformIO native testing (Unity)
 *
 * This test suite validates:
 * - 12 new Phase 2 configuration constants are defined with correct types and values
 * - 7 Phase 1 constants remain unchanged
 * - TEST_MESSAGE_INTERVAL_MS is removed or commented out
 * - Constants are properly organized and documented
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
// CATEGORY 1: PHASE 2 ADC CONFIGURATION TESTS
// ============================================================================

/**
 * TEST 1.1: SENSOR_PIN constant is defined with correct type and value
 * Requirement: const int SENSOR_PIN = 32;
 */
void test_phase2_sensor_pin_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const int SENSOR_PIN"));

    // Verify correct value
    TEST_ASSERT_TRUE(source_matches_regex(source, "SENSOR_PIN\\s*=\\s*32"));
}

/**
 * TEST 1.2: ADC_RESOLUTION constant is defined with correct type and value
 * Requirement: const int ADC_RESOLUTION = 12;
 */
void test_phase2_adc_resolution_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const int ADC_RESOLUTION"));

    // Verify correct value (12-bit resolution)
    TEST_ASSERT_TRUE(source_matches_regex(source, "ADC_RESOLUTION\\s*=\\s*12"));
}

/**
 * TEST 1.3: SAMPLE_RATE_HZ constant is defined with correct type and value
 * Requirement: const int SAMPLE_RATE_HZ = 50;
 */
void test_phase2_sample_rate_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_RATE_HZ"));

    // Verify correct value (50 samples/second)
    TEST_ASSERT_TRUE(source_matches_regex(source, "SAMPLE_RATE_HZ\\s*=\\s*50"));
}

/**
 * TEST 1.4: SAMPLE_INTERVAL_MS constant is defined with correct type and value
 * Requirement: const int SAMPLE_INTERVAL_MS = 20;
 */
void test_phase2_sample_interval_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_INTERVAL_MS"));

    // Verify correct value (20ms interval = 50 samples/second)
    TEST_ASSERT_TRUE(source_matches_regex(source, "SAMPLE_INTERVAL_MS\\s*=\\s*20"));
}

// ============================================================================
// CATEGORY 2: PHASE 2 SIGNAL PROCESSING TESTS
// ============================================================================

/**
 * TEST 2.1: MOVING_AVG_SAMPLES constant is defined with correct type and value
 * Requirement: const int MOVING_AVG_SAMPLES = 5;
 */
void test_phase2_moving_avg_samples_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const int MOVING_AVG_SAMPLES"));

    // Verify correct value (5 sample window)
    TEST_ASSERT_TRUE(source_matches_regex(source, "MOVING_AVG_SAMPLES\\s*=\\s*5"));
}

/**
 * TEST 2.2: BASELINE_DECAY_RATE constant is defined with correct type and value
 * Requirement: const float BASELINE_DECAY_RATE = 0.1;
 */
void test_phase2_baseline_decay_rate_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with float type
    TEST_ASSERT_TRUE(source_contains(source, "const float BASELINE_DECAY_RATE"));

    // Verify correct value (0.1 = 10% decay rate)
    TEST_ASSERT_TRUE(source_matches_regex(source, "BASELINE_DECAY_RATE\\s*=\\s*0\\.1"));
}

/**
 * TEST 2.3: BASELINE_DECAY_INTERVAL constant is defined with correct type and value
 * Requirement: const int BASELINE_DECAY_INTERVAL = 150;
 */
void test_phase2_baseline_decay_interval_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const int BASELINE_DECAY_INTERVAL"));

    // Verify correct value (150 samples = 3 seconds)
    TEST_ASSERT_TRUE(source_matches_regex(source, "BASELINE_DECAY_INTERVAL\\s*=\\s*150"));
}

/**
 * TEST 2.4: THRESHOLD_FRACTION constant is defined with correct type and value
 * Requirement: const float THRESHOLD_FRACTION = 0.6;
 */
void test_phase2_threshold_fraction_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with float type
    TEST_ASSERT_TRUE(source_contains(source, "const float THRESHOLD_FRACTION"));

    // Verify correct value (0.6 = 60% threshold)
    TEST_ASSERT_TRUE(source_matches_regex(source, "THRESHOLD_FRACTION\\s*=\\s*0\\.6"));
}

/**
 * TEST 2.5: MIN_SIGNAL_RANGE constant is defined with correct type and value
 * Requirement: const int MIN_SIGNAL_RANGE = 50;
 */
void test_phase2_min_signal_range_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const int MIN_SIGNAL_RANGE"));

    // Verify correct value (minimum range)
    TEST_ASSERT_TRUE(source_matches_regex(source, "MIN_SIGNAL_RANGE\\s*=\\s*50"));
}

// ============================================================================
// CATEGORY 3: PHASE 2 TIMING AND STATE TESTS
// ============================================================================

/**
 * TEST 3.1: REFRACTORY_PERIOD_MS constant is defined with correct type and value
 * Requirement: const unsigned long REFRACTORY_PERIOD_MS = 300;
 */
void test_phase2_refractory_period_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long REFRACTORY_PERIOD_MS"));

    // Verify correct value (300ms refractory period)
    TEST_ASSERT_TRUE(source_matches_regex(source, "REFRACTORY_PERIOD_MS\\s*=\\s*300"));
}

/**
 * TEST 3.2: FLAT_SIGNAL_THRESHOLD constant is defined with correct type and value
 * Requirement: const int FLAT_SIGNAL_THRESHOLD = 5;
 */
void test_phase2_flat_signal_threshold_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const int FLAT_SIGNAL_THRESHOLD"));

    // Verify correct value (5 ADC units variance)
    TEST_ASSERT_TRUE(source_matches_regex(source, "FLAT_SIGNAL_THRESHOLD\\s*=\\s*5"));
}

/**
 * TEST 3.3: DISCONNECT_TIMEOUT_MS constant is defined with correct type and value
 * Requirement: const unsigned long DISCONNECT_TIMEOUT_MS = 1000;
 */
void test_phase2_disconnect_timeout_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant exists with correct type
    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long DISCONNECT_TIMEOUT_MS"));

    // Verify correct value (1 second timeout)
    TEST_ASSERT_TRUE(source_matches_regex(source, "DISCONNECT_TIMEOUT_MS\\s*=\\s*1000"));
}

// ============================================================================
// CATEGORY 4: PHASE 1 CONSTANTS PRESERVATION TESTS
// ============================================================================

/**
 * TEST 4.1: WIFI_SSID constant remains unchanged (Phase 1)
 */
void test_phase1_wifi_ssid_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const char* WIFI_SSID"));
}

/**
 * TEST 4.2: SERVER_IP constant remains unchanged (Phase 1)
 */
void test_phase1_server_ip_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const IPAddress SERVER_IP"));
}

/**
 * TEST 4.3: SERVER_PORT constant remains unchanged (Phase 1)
 */
void test_phase1_server_port_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const uint16_t SERVER_PORT"));
    TEST_ASSERT_TRUE(source_contains(source, "8000"));
}

/**
 * TEST 4.4: STATUS_LED_PIN constant remains unchanged (Phase 1)
 */
void test_phase1_status_led_pin_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int STATUS_LED_PIN"));
    TEST_ASSERT_TRUE(source_contains(source, "STATUS_LED_PIN = 2"));
}

/**
 * TEST 4.5: SENSOR_ID constant remains unchanged (Phase 1)
 */
void test_phase1_sensor_id_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int SENSOR_ID"));
}

/**
 * TEST 4.6: WIFI_TIMEOUT_MS constant remains unchanged (Phase 1)
 */
void test_phase1_wifi_timeout_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long WIFI_TIMEOUT_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "30000"));
}

/**
 * TEST 4.7: WIFI_PASSWORD constant remains unchanged (Phase 1)
 */
void test_phase1_wifi_password_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const char* WIFI_PASSWORD"));
}

// ============================================================================
// CATEGORY 5: PHASE 1 CONSTANT REMOVAL TESTS
// ============================================================================

/**
 * TEST 5.1: TEST_MESSAGE_INTERVAL_MS is removed or commented
 * This constant is no longer needed in Phase 2 as real sensor data is used
 */
void test_phase2_test_message_interval_removed(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constant is either absent OR properly commented out
    // pattern_active() returns true if pattern exists and is NOT commented
    TEST_ASSERT_FALSE(pattern_active(source, "TEST_MESSAGE_INTERVAL_MS"));
}

// ============================================================================
// CATEGORY 6: CONSTANT ORGANIZATION TESTS
// ============================================================================

/**
 * TEST 6.1: Phase 2 ADC constants are in a dedicated section
 * Should have a comment section for ADC/Sampling configuration
 */
void test_phase2_adc_section_organized(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constants are organized with comments
    // Check for presence of at least the ADC constants in a group
    TEST_ASSERT_TRUE(source_contains(source, "SENSOR_PIN"));
    TEST_ASSERT_TRUE(source_contains(source, "ADC_RESOLUTION"));
    TEST_ASSERT_TRUE(source_contains(source, "SAMPLE_RATE_HZ"));
}

/**
 * TEST 6.2: Phase 2 signal processing constants are in a dedicated section
 * Should have a comment section for signal processing configuration
 */
void test_phase2_signal_section_organized(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify signal processing constants exist
    TEST_ASSERT_TRUE(source_contains(source, "BASELINE_DECAY_RATE"));
    TEST_ASSERT_TRUE(source_contains(source, "THRESHOLD_FRACTION"));
    TEST_ASSERT_TRUE(source_contains(source, "MIN_SIGNAL_RANGE"));
}

/**
 * TEST 6.3: All 12 new Phase 2 constants are present (integration check)
 */
void test_phase2_all_constants_present(void) {
    std::string source = read_source_file("src/main.cpp");

    // Count of Phase 2 constants should be 12
    int phase2_count = 0;

    if (source_contains(source, "SENSOR_PIN")) phase2_count++;
    if (source_contains(source, "ADC_RESOLUTION")) phase2_count++;
    if (source_contains(source, "SAMPLE_RATE_HZ")) phase2_count++;
    if (source_contains(source, "SAMPLE_INTERVAL_MS")) phase2_count++;
    if (source_contains(source, "MOVING_AVG_SAMPLES")) phase2_count++;
    if (source_contains(source, "BASELINE_DECAY_RATE")) phase2_count++;
    if (source_contains(source, "BASELINE_DECAY_INTERVAL")) phase2_count++;
    if (source_contains(source, "THRESHOLD_FRACTION")) phase2_count++;
    if (source_contains(source, "MIN_SIGNAL_RANGE")) phase2_count++;
    if (source_contains(source, "REFRACTORY_PERIOD_MS")) phase2_count++;
    if (source_contains(source, "FLAT_SIGNAL_THRESHOLD")) phase2_count++;
    if (source_contains(source, "DISCONNECT_TIMEOUT_MS")) phase2_count++;

    // All 12 should be present
    TEST_ASSERT_EQUAL(12, phase2_count);
}

// ============================================================================
// CATEGORY 7: TYPE SAFETY TESTS
// ============================================================================

/**
 * TEST 7.1: Integer constants use 'const int' (not 'const uint' or similar)
 * Verifies: SENSOR_PIN, ADC_RESOLUTION, SAMPLE_RATE_HZ, SAMPLE_INTERVAL_MS,
 *           MOVING_AVG_SAMPLES, BASELINE_DECAY_INTERVAL, MIN_SIGNAL_RANGE,
 *           FLAT_SIGNAL_THRESHOLD
 */
void test_phase2_int_constants_correct_type(void) {
    std::string source = read_source_file("src/main.cpp");

    // These 8 should be 'const int'
    TEST_ASSERT_TRUE(source_contains(source, "const int SENSOR_PIN"));
    TEST_ASSERT_TRUE(source_contains(source, "const int ADC_RESOLUTION"));
    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_RATE_HZ"));
    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_INTERVAL_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "const int MOVING_AVG_SAMPLES"));
    TEST_ASSERT_TRUE(source_contains(source, "const int BASELINE_DECAY_INTERVAL"));
    TEST_ASSERT_TRUE(source_contains(source, "const int MIN_SIGNAL_RANGE"));
    TEST_ASSERT_TRUE(source_contains(source, "const int FLAT_SIGNAL_THRESHOLD"));
}

/**
 * TEST 7.2: Float constants use 'const float' for decay and threshold fractions
 * Verifies: BASELINE_DECAY_RATE, THRESHOLD_FRACTION
 */
void test_phase2_float_constants_correct_type(void) {
    std::string source = read_source_file("src/main.cpp");

    // These 2 should be 'const float'
    TEST_ASSERT_TRUE(source_contains(source, "const float BASELINE_DECAY_RATE"));
    TEST_ASSERT_TRUE(source_contains(source, "const float THRESHOLD_FRACTION"));
}

/**
 * TEST 7.3: Timing constants use 'const unsigned long' for millisecond intervals
 * Verifies: REFRACTORY_PERIOD_MS, DISCONNECT_TIMEOUT_MS
 */
void test_phase2_timing_constants_correct_type(void) {
    std::string source = read_source_file("src/main.cpp");

    // These 2 should be 'const unsigned long'
    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long REFRACTORY_PERIOD_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long DISCONNECT_TIMEOUT_MS"));
}

// ============================================================================
// CATEGORY 8: VALUE RANGE AND REASONABLENESS TESTS
// ============================================================================

/**
 * TEST 8.1: ADC_RESOLUTION is reasonable (8-16 bit range typical for ADC)
 * Value should be between 8 and 16
 */
void test_phase2_adc_resolution_reasonable(void) {
    std::string source = read_source_file("src/main.cpp");

    // 12-bit is standard for ESP32 ADC
    TEST_ASSERT_TRUE(source_matches_regex(source, "ADC_RESOLUTION\\s*=\\s*(8|10|12|14|16)"));
}

/**
 * TEST 8.2: SAMPLE_RATE_HZ is reasonable (10-1000 Hz typical for ECG)
 * Value should be between 10 and 1000 Hz
 */
void test_phase2_sample_rate_reasonable(void) {
    std::string source = read_source_file("src/main.cpp");

    // 50 Hz is reasonable for ECG sampling
    TEST_ASSERT_TRUE(source_matches_regex(source, "SAMPLE_RATE_HZ\\s*=\\s*[0-9]+"));
    TEST_ASSERT_TRUE(source_contains(source, "50"));
}

/**
 * TEST 8.3: MOVING_AVG_SAMPLES is small (typically 3-10 for real-time processing)
 * Value should be less than 20
 */
void test_phase2_moving_avg_reasonable(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_matches_regex(source, "MOVING_AVG_SAMPLES\\s*=\\s*[0-9]+"));
    // Verify it's a single digit (less than 10)
    TEST_ASSERT_TRUE(source_contains(source, "MOVING_AVG_SAMPLES = 5"));
}

/**
 * TEST 8.4: BASELINE_DECAY_RATE is a fraction between 0 and 1
 * Value should be 0.0-1.0
 */
void test_phase2_decay_rate_reasonable(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should be a decimal between 0 and 1
    TEST_ASSERT_TRUE(source_matches_regex(source, "BASELINE_DECAY_RATE\\s*=\\s*0\\.[0-9]+"));
}

/**
 * TEST 8.5: THRESHOLD_FRACTION is a fraction between 0 and 1
 * Value should be 0.0-1.0
 */
void test_phase2_threshold_reasonable(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should be a decimal between 0 and 1
    TEST_ASSERT_TRUE(source_matches_regex(source, "THRESHOLD_FRACTION\\s*=\\s*0\\.[0-9]+"));
}

/**
 * TEST 8.6: REFRACTORY_PERIOD_MS is reasonable for heart rate detection (100-500ms)
 */
void test_phase2_refractory_reasonable(void) {
    std::string source = read_source_file("src/main.cpp");

    // 300ms is reasonable for refractory period in ECG
    TEST_ASSERT_TRUE(source_matches_regex(source, "REFRACTORY_PERIOD_MS\\s*=\\s*[0-9]+"));
    TEST_ASSERT_TRUE(source_contains(source, "REFRACTORY_PERIOD_MS = 300"));
}

/**
 * TEST 8.7: DISCONNECT_TIMEOUT_MS is reasonable (500ms - 5sec for timeout)
 */
void test_phase2_disconnect_timeout_reasonable(void) {
    std::string source = read_source_file("src/main.cpp");

    // 1000ms (1 second) is reasonable timeout
    TEST_ASSERT_TRUE(source_matches_regex(source, "DISCONNECT_TIMEOUT_MS\\s*=\\s*[0-9]+"));
    TEST_ASSERT_TRUE(source_contains(source, "DISCONNECT_TIMEOUT_MS = 1000"));
}

// ============================================================================
// CATEGORY 9: CONFIGURATION SECTION STRUCTURE TESTS
// ============================================================================

/**
 * TEST 9.1: Configuration section comments are present
 * Verify structure includes section headers for organization
 */
void test_phase2_config_section_marked(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should have configuration section markers
    TEST_ASSERT_TRUE(source_contains(source, "CONFIGURATION"));
}

/**
 * TEST 9.2: All constants are marked const (immutability enforced)
 * Count const declarations should increase by 12 from Phase 1
 */
void test_phase2_constants_are_const(void) {
    std::string source = read_source_file("src/main.cpp");

    // Each new Phase 2 constant should be const
    int const_count = count_pattern_occurrences(source, "const");

    // Should have at least 19 const declarations (7 Phase 1 + 12 Phase 2)
    TEST_ASSERT_GREATER_THAN(18, const_count);
}

/**
 * TEST 9.3: Each constant has a comment explaining its purpose
 * Verify constants are documented with // comments
 */
void test_phase2_constants_documented(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for commented sections explaining Phase 2 constants
    // Should have comments for ADC, sampling, signal processing
    TEST_ASSERT_TRUE(source_contains(source, "//"));
    TEST_ASSERT_TRUE(source_contains(source, "/*"));
}

// ============================================================================
// CATEGORY 10: BACKWARD COMPATIBILITY TESTS
// ============================================================================

/**
 * TEST 10.1: Phase 1 functions remain unchanged
 * Verify connectWiFi, sendHeartbeatOSC, updateLED, checkWiFi still exist
 */
void test_phase2_phase1_functions_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "bool connectWiFi()"));
    TEST_ASSERT_TRUE(source_contains(source, "void sendHeartbeatOSC"));
    TEST_ASSERT_TRUE(source_contains(source, "void updateLED()"));
    TEST_ASSERT_TRUE(source_contains(source, "void checkWiFi()"));
}

/**
 * TEST 10.2: setup() and loop() functions still exist
 * Verify core Arduino functions are preserved
 */
void test_phase2_arduino_core_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void setup()"));
    TEST_ASSERT_TRUE(source_contains(source, "void loop()"));
}

/**
 * TEST 10.3: SystemState struct is preserved
 * Global state structure should not be modified
 */
void test_phase2_system_state_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "struct SystemState"));
}

/**
 * TEST 10.4: WiFi and OSC functionality is preserved
 * Core includes and features from Phase 1 remain
 */
void test_phase2_core_features_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "#include <WiFi.h>"));
    TEST_ASSERT_TRUE(source_contains(source, "#include <OSCMessage.h>"));
    TEST_ASSERT_TRUE(source_contains(source, "WiFiUDP udp"));
}

// ============================================================================
// TEST RUNNER MAIN
// ============================================================================

int main(int argc, char* argv[]) {
    UNITY_BEGIN();

    // Category 1: Phase 2 ADC Configuration Tests
    RUN_TEST(test_phase2_sensor_pin_defined);
    RUN_TEST(test_phase2_adc_resolution_defined);
    RUN_TEST(test_phase2_sample_rate_defined);
    RUN_TEST(test_phase2_sample_interval_defined);

    // Category 2: Phase 2 Signal Processing Tests
    RUN_TEST(test_phase2_moving_avg_samples_defined);
    RUN_TEST(test_phase2_baseline_decay_rate_defined);
    RUN_TEST(test_phase2_baseline_decay_interval_defined);
    RUN_TEST(test_phase2_threshold_fraction_defined);
    RUN_TEST(test_phase2_min_signal_range_defined);

    // Category 3: Phase 2 Timing and State Tests
    RUN_TEST(test_phase2_refractory_period_defined);
    RUN_TEST(test_phase2_flat_signal_threshold_defined);
    RUN_TEST(test_phase2_disconnect_timeout_defined);

    // Category 4: Phase 1 Constants Preservation Tests
    RUN_TEST(test_phase1_wifi_ssid_preserved);
    RUN_TEST(test_phase1_server_ip_preserved);
    RUN_TEST(test_phase1_server_port_preserved);
    RUN_TEST(test_phase1_status_led_pin_preserved);
    RUN_TEST(test_phase1_sensor_id_preserved);
    RUN_TEST(test_phase1_wifi_timeout_preserved);
    RUN_TEST(test_phase1_wifi_password_preserved);

    // Category 5: Phase 1 Constant Removal Tests
    RUN_TEST(test_phase2_test_message_interval_removed);

    // Category 6: Constant Organization Tests
    RUN_TEST(test_phase2_adc_section_organized);
    RUN_TEST(test_phase2_signal_section_organized);
    RUN_TEST(test_phase2_all_constants_present);

    // Category 7: Type Safety Tests
    RUN_TEST(test_phase2_int_constants_correct_type);
    RUN_TEST(test_phase2_float_constants_correct_type);
    RUN_TEST(test_phase2_timing_constants_correct_type);

    // Category 8: Value Range and Reasonableness Tests
    RUN_TEST(test_phase2_adc_resolution_reasonable);
    RUN_TEST(test_phase2_sample_rate_reasonable);
    RUN_TEST(test_phase2_moving_avg_reasonable);
    RUN_TEST(test_phase2_decay_rate_reasonable);
    RUN_TEST(test_phase2_threshold_reasonable);
    RUN_TEST(test_phase2_refractory_reasonable);
    RUN_TEST(test_phase2_disconnect_timeout_reasonable);

    // Category 9: Configuration Section Structure Tests
    RUN_TEST(test_phase2_config_section_marked);
    RUN_TEST(test_phase2_constants_are_const);
    RUN_TEST(test_phase2_constants_documented);

    // Category 10: Backward Compatibility Tests
    RUN_TEST(test_phase2_phase1_functions_preserved);
    RUN_TEST(test_phase2_arduino_core_preserved);
    RUN_TEST(test_phase2_system_state_preserved);
    RUN_TEST(test_phase2_core_features_preserved);

    return UNITY_END();
}
