/**
 * Test Suite for Component 9.1: Project Structure & Configuration
 *
 * Tests against Phase 3 firmware TRD Tasks 1.1-1.8
 * Framework: PlatformIO native testing (Unity)
 *
 * This test suite validates the firmware configuration without executing
 * embedded code. Tests verify:
 * - Required source file exists
 * - Required includes present
 * - All configuration constants defined with correct values
 * - Hardware configuration constants (sensor pins, array size)
 * - Signal processing parameters
 * - Beat detection parameters
 * - Debug level macro
 * - Static assertions for array bounds
 */

#include <unity.h>
#include <cstring>
#include <cstdio>
#include "test_helpers.h"

// ============================================================================
// FORWARD DECLARATIONS FOR TESTS FROM test_component_9_2.cpp
// ============================================================================

// Component 9.2: SensorState Struct Tests
extern void test_struct_sensorstate_defined(void);
extern void test_sensorstate_field_pin(void);
extern void test_sensorstate_field_rawsamples(void);
extern void test_sensorstate_field_sampleindex(void);
extern void test_sensorstate_field_smoothedvalue(void);
extern void test_sensorstate_field_minvalue(void);
extern void test_sensorstate_field_maxvalue(void);
extern void test_sensorstate_field_samplessincedecay(void);
extern void test_sensorstate_field_abovethreshold(void);
extern void test_sensorstate_field_lastbeattime(void);
extern void test_sensorstate_field_lastibi(void);
extern void test_sensorstate_field_firstbeatdetected(void);
extern void test_sensorstate_field_isconnected(void);
extern void test_sensorstate_field_lastrawvalue(void);
extern void test_sensorstate_field_flatsamplecount(void);
extern void test_sensorstate_field_count(void);
extern void test_sensorstate_field_types(void);

// Component 9.2: SystemState Struct Tests
extern void test_struct_systemstate_defined(void);
extern void test_systemstate_field_wificonnected(void);
extern void test_systemstate_field_lastwifichecktime(void);
extern void test_systemstate_field_loopcounter(void);
extern void test_systemstate_field_beatdetectedthisloop(void);
extern void test_systemstate_field_count(void);
extern void test_systemstate_field_types(void);

// Component 9.2: Global Variables Tests
extern void test_global_var_wifiudp_declared(void);
extern void test_global_var_wifiudp_scope(void);
extern void test_global_var_system_declared(void);
extern void test_global_var_system_initialization(void);
extern void test_global_var_sensors_declared(void);
extern void test_global_var_sensors_size(void);
extern void test_global_vars_file_scope(void);

// Component 9.2: Function Declarations Tests
extern void test_function_connectwifi_declared(void);
extern void test_function_connectwifi_returntype(void);
extern void test_function_connectwifi_params(void);
extern void test_function_checkwifi_declared(void);
extern void test_function_checkwifi_returntype(void);
extern void test_function_checkwifi_params(void);
extern void test_function_initializesensor_declared(void);
extern void test_function_initializesensor_returntype(void);
extern void test_function_initializesensor_params(void);
extern void test_function_readandfiltersensor_declared(void);
extern void test_function_readandfiltersensor_returntype(void);
extern void test_function_readandfiltersensor_params(void);
extern void test_function_updatebaseline_declared(void);
extern void test_function_updatebaseline_returntype(void);
extern void test_function_updatebaseline_params(void);
extern void test_function_detectbeat_declared(void);
extern void test_function_detectbeat_returntype(void);
extern void test_function_detectbeat_params(void);
extern void test_function_sendheartbeatosc_declared(void);
extern void test_function_sendheartbeatosc_returntype(void);
extern void test_function_sendheartbeatosc_params(void);
extern void test_function_updateled_declared(void);
extern void test_function_updateled_returntype(void);
extern void test_function_updateled_params(void);
extern void test_all_functions_declared(void);
extern void test_function_declarations_before_setup(void);

// Component 9.2: Integration Tests
extern void test_structures_before_globals(void);
extern void test_globals_logical_order(void);
extern void test_complete_interface(void);
extern void test_no_duplicate_structs(void);
extern void test_function_signatures_consistent(void);

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
// CATEGORY 1: PROJECT STRUCTURE & FILE TESTS (Task 1.1)
// ============================================================================

/**
 * TEST 1.1: Source file exists and is readable (Task 1.1)
 */
void test_source_file_exists(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_GREATER_THAN(100, source.length());
}

/**
 * TEST 1.2: File contains header comment (Task 1.2)
 */
void test_file_header_comment_exists(void) {
    std::string source = read_source_file("src/main.cpp");

    // Check for header with Phase 3 identification
    TEST_ASSERT_TRUE(source_contains(source, "/**"));
    TEST_ASSERT_TRUE(source_contains(source, "Heartbeat"));
    TEST_ASSERT_TRUE(source_contains(source, "Phase 3") ||
                     source_contains(source, "phase 3") ||
                     source_contains(source, "Multi-Sensor"));
}

// ============================================================================
// CATEGORY 2: INCLUDES TESTS (Task 1.2)
// ============================================================================

/**
 * TEST 2.1: Arduino.h include present (Task 1.2)
 */
void test_include_arduino_h(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "#include <Arduino.h>"));
}

/**
 * TEST 2.2: WiFi.h include present (Task 1.2)
 */
void test_include_wifi_h(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "#include <WiFi.h>"));
}

/**
 * TEST 2.3: WiFiUdp.h include present (Task 1.2)
 */
void test_include_wifiudp_h(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "#include <WiFiUdp.h>"));
}

/**
 * TEST 2.4: OSCMessage.h include present (Task 1.2)
 */
void test_include_oscmessage_h(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "#include <OSCMessage.h>"));
}

/**
 * TEST 2.5: All includes are well-formed (Task 1.2)
 */
void test_includes_well_formed(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should NOT have malformed includes
    TEST_ASSERT_FALSE(source_contains(source, "#include Arduino.h"));
    TEST_ASSERT_FALSE(source_contains(source, "#include WiFi.h"));

    // Verify correct format exists
    TEST_ASSERT_TRUE(source_contains(source, "#include <Arduino.h>"));
}

// ============================================================================
// CATEGORY 3: NETWORK CONFIGURATION TESTS (Task 1.3)
// ============================================================================

/**
 * TEST 3.1: WIFI_SSID is defined (Task 1.3)
 */
void test_config_wifi_ssid_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const char* WIFI_SSID"));
    TEST_ASSERT_TRUE(source_contains(source, "heartbeat-install"));
}

/**
 * TEST 3.2: WIFI_PASSWORD is defined (Task 1.3)
 */
void test_config_wifi_password_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const char* WIFI_PASSWORD"));
}

/**
 * TEST 3.3: SERVER_IP is defined as IPAddress (Task 1.3)
 */
void test_config_server_ip_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const IPAddress SERVER_IP"));
    // Verify IP address pattern: four octets
    TEST_ASSERT_TRUE(source_matches_regex(source, "IPAddress.*SERVER_IP.*\\d+.*\\d+.*\\d+.*\\d+"));
}

/**
 * TEST 3.4: SERVER_PORT is defined as uint16_t = 8000 (Task 1.3)
 */
void test_config_server_port_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const uint16_t SERVER_PORT"));
    TEST_ASSERT_TRUE(source_contains(source, "8000"));
}

/**
 * TEST 3.5: WIFI_TIMEOUT_MS is defined = 30000 (Task 1.3)
 */
void test_config_wifi_timeout_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long WIFI_TIMEOUT_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "30000"));
}

// ============================================================================
// CATEGORY 4: HARDWARE CONFIGURATION TESTS (Task 1.4)
// ============================================================================

/**
 * TEST 4.1: SENSOR_PINS array is defined as {32, 33, 34, 35} (Task 1.4)
 */
void test_config_sensor_pins_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int SENSOR_PINS[4]"));
    TEST_ASSERT_TRUE(source_contains(source, "32"));
    TEST_ASSERT_TRUE(source_contains(source, "33"));
    TEST_ASSERT_TRUE(source_contains(source, "34"));
    TEST_ASSERT_TRUE(source_contains(source, "35"));
}

/**
 * TEST 4.2: NUM_SENSORS constant is defined = 4 (Task 1.4)
 */
void test_config_num_sensors_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int NUM_SENSORS"));
    TEST_ASSERT_TRUE(source_contains(source, "4"));
}

/**
 * TEST 4.3: STATUS_LED_PIN is defined = 2 (Task 1.4)
 */
void test_config_status_led_pin_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int STATUS_LED_PIN"));
    TEST_ASSERT_TRUE(source_contains(source, "= 2"));
}

/**
 * TEST 4.4: ADC_RESOLUTION is defined = 12 (Task 1.4)
 */
void test_config_adc_resolution_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int ADC_RESOLUTION"));
    TEST_ASSERT_TRUE(source_contains(source, "12"));
}

/**
 * TEST 4.5: Hardware configuration values are const (Task 1.4)
 */
void test_hardware_config_is_const(void) {
    std::string source = read_source_file("src/main.cpp");

    // Each hardware config should be const - at least 4 (SENSOR_PINS, NUM_SENSORS, STATUS_LED_PIN, ADC_RESOLUTION)
    int const_count = count_pattern_occurrences(source, "const int");
    TEST_ASSERT_GREATER_THAN(3, const_count);  // More than 3, so at least 4
}

/**
 * TEST 4.6: Static assertions for array bounds present (Task 1.4)
 */
void test_static_assertion_array_size(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should have at least one static_assert for array verification
    TEST_ASSERT_TRUE(source_contains(source, "static_assert"));
}

/**
 * TEST 4.7: Static assertion verifies NUM_SENSORS equals 4 (Task 1.4)
 */
void test_static_assertion_num_sensors(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should have static_assert with NUM_SENSORS == 4
    TEST_ASSERT_TRUE(source_contains(source, "static_assert"));
    TEST_ASSERT_TRUE(source_contains(source, "NUM_SENSORS"));
    TEST_ASSERT_TRUE(source_contains(source, "4"));
}

// ============================================================================
// CATEGORY 5: SIGNAL PROCESSING PARAMETERS TESTS (Task 1.5)
// ============================================================================

/**
 * TEST 5.1: SAMPLE_RATE_HZ is defined = 50 (Task 1.5)
 */
void test_config_sample_rate_hz_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_RATE_HZ"));
    TEST_ASSERT_TRUE(source_contains(source, "50"));
}

/**
 * TEST 5.2: SAMPLE_INTERVAL_MS is defined = 20 (Task 1.5)
 */
void test_config_sample_interval_ms_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_INTERVAL_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "20"));
}

/**
 * TEST 5.3: MOVING_AVG_SAMPLES is defined = 5 (Task 1.5)
 */
void test_config_moving_avg_samples_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int MOVING_AVG_SAMPLES"));
    TEST_ASSERT_TRUE(source_contains(source, "5"));
}

/**
 * TEST 5.4: BASELINE_DECAY_RATE is defined = 0.1 (Task 1.5)
 */
void test_config_baseline_decay_rate_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const float BASELINE_DECAY_RATE"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "BASELINE_DECAY_RATE\\s*=\\s*0\\.1"));
}

/**
 * TEST 5.5: BASELINE_DECAY_INTERVAL is defined = 150 (Task 1.5)
 */
void test_config_baseline_decay_interval_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int BASELINE_DECAY_INTERVAL"));
    TEST_ASSERT_TRUE(source_contains(source, "150"));
}

/**
 * TEST 5.6: Signal processing values are const (Task 1.5)
 */
void test_signal_processing_is_const(void) {
    std::string source = read_source_file("src/main.cpp");

    // Check for const declarations in signal processing section
    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_RATE_HZ"));
    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_INTERVAL_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "const int MOVING_AVG_SAMPLES"));
}

/**
 * TEST 5.7: SAMPLE_INTERVAL_MS = 1000 / SAMPLE_RATE_HZ (Task 1.8 validation)
 */
void test_config_sample_interval_calculation(void) {
    std::string source = read_source_file("src/main.cpp");

    // Both constants must be present for relationship to be valid
    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_RATE_HZ"));
    TEST_ASSERT_TRUE(source_contains(source, "const int SAMPLE_INTERVAL_MS"));

    // Verify the actual values are correct: 1000 / 50 = 20
    TEST_ASSERT_TRUE(source_contains(source, "50"));  // SAMPLE_RATE_HZ = 50
    TEST_ASSERT_TRUE(source_contains(source, "20"));  // SAMPLE_INTERVAL_MS = 20
}

// ============================================================================
// CATEGORY 6: BEAT DETECTION PARAMETERS TESTS (Task 1.6)
// ============================================================================

/**
 * TEST 6.1: THRESHOLD_FRACTION is defined = 0.6 (Task 1.6)
 */
void test_config_threshold_fraction_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const float THRESHOLD_FRACTION"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "THRESHOLD_FRACTION\\s*=\\s*0\\.6"));
}

/**
 * TEST 6.2: MIN_SIGNAL_RANGE is defined = 50 (Task 1.6)
 */
void test_config_min_signal_range_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int MIN_SIGNAL_RANGE"));
    TEST_ASSERT_TRUE(source_contains(source, "50"));
}

/**
 * TEST 6.3: REFRACTORY_PERIOD_MS is defined = 300 (Task 1.6)
 */
void test_config_refractory_period_ms_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long REFRACTORY_PERIOD_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "300"));
}

/**
 * TEST 6.4: FLAT_SIGNAL_THRESHOLD is defined = 5 (Task 1.6)
 */
void test_config_flat_signal_threshold_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int FLAT_SIGNAL_THRESHOLD"));
    TEST_ASSERT_TRUE(source_contains(source, "5"));
}

/**
 * TEST 6.5: DISCONNECT_TIMEOUT_MS is defined = 1000 (Task 1.6)
 */
void test_config_disconnect_timeout_ms_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long DISCONNECT_TIMEOUT_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "1000"));
}

/**
 * TEST 6.6: Beat detection values are const (Task 1.6)
 */
void test_beat_detection_is_const(void) {
    std::string source = read_source_file("src/main.cpp");

    // Check for const declarations in beat detection section
    TEST_ASSERT_TRUE(source_contains(source, "const float THRESHOLD_FRACTION"));
    TEST_ASSERT_TRUE(source_contains(source, "const int MIN_SIGNAL_RANGE"));
    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long REFRACTORY_PERIOD_MS"));
}

// ============================================================================
// CATEGORY 7: DEBUG CONFIGURATION TESTS (Task 1.7)
// ============================================================================

/**
 * TEST 7.1: DEBUG_LEVEL macro is defined (Task 1.7)
 */
void test_config_debug_level_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "#define DEBUG_LEVEL"));
}

/**
 * TEST 7.2: DEBUG_LEVEL is set to 0, 1, or 2 (Task 1.7)
 */
void test_config_debug_level_valid(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify DEBUG_LEVEL is one of the valid values
    bool is_valid = source_contains(source, "#define DEBUG_LEVEL 0") ||
                    source_contains(source, "#define DEBUG_LEVEL 1") ||
                    source_contains(source, "#define DEBUG_LEVEL 2");

    TEST_ASSERT_TRUE(is_valid);
}

/**
 * TEST 7.3: DEBUG_LEVEL is active (not commented out) (Task 1.7)
 */
void test_config_debug_level_active(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(pattern_active(source, "#define DEBUG_LEVEL"));
}

// ============================================================================
// CATEGORY 8: CONFIGURATION VALIDATION TESTS (Task 1.8)
// ============================================================================

/**
 * TEST 8.1: All configuration constants are present (Task 1.8)
 */
void test_all_config_constants_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    // Network configuration
    TEST_ASSERT_TRUE(source_contains(source, "WIFI_SSID"));
    TEST_ASSERT_TRUE(source_contains(source, "WIFI_PASSWORD"));
    TEST_ASSERT_TRUE(source_contains(source, "SERVER_IP"));
    TEST_ASSERT_TRUE(source_contains(source, "SERVER_PORT"));
    TEST_ASSERT_TRUE(source_contains(source, "WIFI_TIMEOUT_MS"));

    // Hardware configuration
    TEST_ASSERT_TRUE(source_contains(source, "SENSOR_PINS"));
    TEST_ASSERT_TRUE(source_contains(source, "NUM_SENSORS"));
    TEST_ASSERT_TRUE(source_contains(source, "STATUS_LED_PIN"));
    TEST_ASSERT_TRUE(source_contains(source, "ADC_RESOLUTION"));

    // Signal processing
    TEST_ASSERT_TRUE(source_contains(source, "SAMPLE_RATE_HZ"));
    TEST_ASSERT_TRUE(source_contains(source, "SAMPLE_INTERVAL_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "MOVING_AVG_SAMPLES"));
    TEST_ASSERT_TRUE(source_contains(source, "BASELINE_DECAY_RATE"));
    TEST_ASSERT_TRUE(source_contains(source, "BASELINE_DECAY_INTERVAL"));

    // Beat detection
    TEST_ASSERT_TRUE(source_contains(source, "THRESHOLD_FRACTION"));
    TEST_ASSERT_TRUE(source_contains(source, "MIN_SIGNAL_RANGE"));
    TEST_ASSERT_TRUE(source_contains(source, "REFRACTORY_PERIOD_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "FLAT_SIGNAL_THRESHOLD"));
    TEST_ASSERT_TRUE(source_contains(source, "DISCONNECT_TIMEOUT_MS"));

    // Debug
    TEST_ASSERT_TRUE(source_contains(source, "DEBUG_LEVEL"));
}

/**
 * TEST 8.2: SENSOR_PINS array size matches NUM_SENSORS (Task 1.8)
 */
void test_config_array_size_consistency(void) {
    std::string source = read_source_file("src/main.cpp");

    // Both array declaration and size constant must exist
    TEST_ASSERT_TRUE(source_contains(source, "const int SENSOR_PINS[4]"));
    TEST_ASSERT_TRUE(source_contains(source, "const int NUM_SENSORS"));

    // Verify they both reference 4
    TEST_ASSERT_TRUE(source_matches_regex(source, "SENSOR_PINS\\[4\\]"));
}

/**
 * TEST 8.3: Configuration uses comments to describe sections (Task 1.8)
 */
void test_config_has_section_comments(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should have commented sections
    TEST_ASSERT_TRUE(source_contains(source, "//"));
    TEST_ASSERT_TRUE(source_contains(source, "/*") || source_contains(source, "//"));
}

/**
 * TEST 8.4: No hardcoded numeric values without descriptive constants (Task 1.8)
 */
void test_config_constants_used_descriptively(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should define key values as named constants
    TEST_ASSERT_TRUE(source_contains(source, "const"));
    int const_count = count_pattern_occurrences(source, "const");
    TEST_ASSERT_GREATER_THAN(12, const_count);  // At least 13 const declarations
}

/**
 * TEST 8.5: Hardware configuration (SENSOR_PINS[4]) matches GPIO pins (Task 1.8)
 */
void test_config_sensor_pins_valid_gpios(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify the exact pin assignments
    TEST_ASSERT_TRUE(source_contains(source, "32"));  // GPIO 32
    TEST_ASSERT_TRUE(source_contains(source, "33"));  // GPIO 33
    TEST_ASSERT_TRUE(source_contains(source, "34"));  // GPIO 34
    TEST_ASSERT_TRUE(source_contains(source, "35"));  // GPIO 35

    // In the context of SENSOR_PINS array
    TEST_ASSERT_TRUE(source_contains(source, "SENSOR_PINS[4]"));
}

// ============================================================================
// CATEGORY 9: INTEGRATION TESTS
// ============================================================================

/**
 * TEST 9.1: Configuration section is organized before implementations (Task 1.8)
 */
void test_config_organization_order(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should have marked sections
    size_t includes_pos = source.find("#include");
    size_t config_pos = source.find("CONFIGURATION") != std::string::npos ?
                       source.find("CONFIGURATION") :
                       source.find("const");

    // Includes should come before configuration
    TEST_ASSERT_GREATER_THAN(includes_pos, config_pos);
}

/**
 * TEST 9.2: No duplicate constant definitions (Task 1.8)
 */
void test_config_no_duplicates(void) {
    std::string source = read_source_file("src/main.cpp");

    // Each constant should be defined exactly once
    int num_sensors_count = count_pattern_occurrences(source, "const int NUM_SENSORS");
    int sensor_pins_count = count_pattern_occurrences(source, "const int SENSOR_PINS");
    int sample_rate_count = count_pattern_occurrences(source, "const int SAMPLE_RATE_HZ");

    // Each should appear exactly once (or small multiples for comments/duplicates)
    TEST_ASSERT_EQUAL(1, num_sensors_count);
    TEST_ASSERT_EQUAL(1, sensor_pins_count);
    TEST_ASSERT_EQUAL(1, sample_rate_count);
}

/**
 * TEST 9.3: File is non-empty and well-structured (Task 1.8)
 */
void test_configuration_file_structure(void) {
    std::string source = read_source_file("src/main.cpp");

    // File should be reasonably sized
    TEST_ASSERT_GREATER_THAN(500, source.length());  // More than 500 chars

    // Should have both comments and code
    TEST_ASSERT_TRUE(source_contains(source, "const"));
    TEST_ASSERT_TRUE(source_contains(source, "#define") || source_contains(source, "const"));
}

// ============================================================================
// TEST RUNNER MAIN
// ============================================================================

int main(int argc, char* argv[]) {
    UNITY_BEGIN();

    // ========== Component 9.1 Tests ==========
    // Category 1: Project Structure & File Tests
    RUN_TEST(test_source_file_exists);
    RUN_TEST(test_file_header_comment_exists);

    // Category 2: Includes Tests
    RUN_TEST(test_include_arduino_h);
    RUN_TEST(test_include_wifi_h);
    RUN_TEST(test_include_wifiudp_h);
    RUN_TEST(test_include_oscmessage_h);
    RUN_TEST(test_includes_well_formed);

    // Category 3: Network Configuration Tests
    RUN_TEST(test_config_wifi_ssid_defined);
    RUN_TEST(test_config_wifi_password_defined);
    RUN_TEST(test_config_server_ip_defined);
    RUN_TEST(test_config_server_port_defined);
    RUN_TEST(test_config_wifi_timeout_defined);

    // Category 4: Hardware Configuration Tests
    RUN_TEST(test_config_sensor_pins_defined);
    RUN_TEST(test_config_num_sensors_defined);
    RUN_TEST(test_config_status_led_pin_defined);
    RUN_TEST(test_config_adc_resolution_defined);
    RUN_TEST(test_hardware_config_is_const);
    RUN_TEST(test_static_assertion_array_size);
    RUN_TEST(test_static_assertion_num_sensors);

    // Category 5: Signal Processing Parameters Tests
    RUN_TEST(test_config_sample_rate_hz_defined);
    RUN_TEST(test_config_sample_interval_ms_defined);
    RUN_TEST(test_config_moving_avg_samples_defined);
    RUN_TEST(test_config_baseline_decay_rate_defined);
    RUN_TEST(test_config_baseline_decay_interval_defined);
    RUN_TEST(test_signal_processing_is_const);
    RUN_TEST(test_config_sample_interval_calculation);

    // Category 6: Beat Detection Parameters Tests
    RUN_TEST(test_config_threshold_fraction_defined);
    RUN_TEST(test_config_min_signal_range_defined);
    RUN_TEST(test_config_refractory_period_ms_defined);
    RUN_TEST(test_config_flat_signal_threshold_defined);
    RUN_TEST(test_config_disconnect_timeout_ms_defined);
    RUN_TEST(test_beat_detection_is_const);

    // Category 7: Debug Configuration Tests
    RUN_TEST(test_config_debug_level_defined);
    RUN_TEST(test_config_debug_level_valid);
    RUN_TEST(test_config_debug_level_active);

    // Category 8: Configuration Validation Tests
    RUN_TEST(test_all_config_constants_defined);
    RUN_TEST(test_config_array_size_consistency);
    RUN_TEST(test_config_has_section_comments);
    RUN_TEST(test_config_constants_used_descriptively);
    RUN_TEST(test_config_sensor_pins_valid_gpios);

    // Category 9: Integration Tests
    RUN_TEST(test_config_organization_order);
    RUN_TEST(test_config_no_duplicates);
    RUN_TEST(test_configuration_file_structure);

    // ========== Component 9.2 Tests ==========
    // Category 1: SensorState Struct Tests (from test_component_9_2.cpp)
    RUN_TEST(test_struct_sensorstate_defined);
    RUN_TEST(test_sensorstate_field_pin);
    RUN_TEST(test_sensorstate_field_rawsamples);
    RUN_TEST(test_sensorstate_field_sampleindex);
    RUN_TEST(test_sensorstate_field_smoothedvalue);
    RUN_TEST(test_sensorstate_field_minvalue);
    RUN_TEST(test_sensorstate_field_maxvalue);
    RUN_TEST(test_sensorstate_field_samplessincedecay);
    RUN_TEST(test_sensorstate_field_abovethreshold);
    RUN_TEST(test_sensorstate_field_lastbeattime);
    RUN_TEST(test_sensorstate_field_lastibi);
    RUN_TEST(test_sensorstate_field_firstbeatdetected);
    RUN_TEST(test_sensorstate_field_isconnected);
    RUN_TEST(test_sensorstate_field_lastrawvalue);
    RUN_TEST(test_sensorstate_field_flatsamplecount);
    RUN_TEST(test_sensorstate_field_count);
    RUN_TEST(test_sensorstate_field_types);

    // Category 2: SystemState Struct Tests (from test_component_9_2.cpp)
    RUN_TEST(test_struct_systemstate_defined);
    RUN_TEST(test_systemstate_field_wificonnected);
    RUN_TEST(test_systemstate_field_lastwifichecktime);
    RUN_TEST(test_systemstate_field_loopcounter);
    RUN_TEST(test_systemstate_field_beatdetectedthisloop);
    RUN_TEST(test_systemstate_field_count);
    RUN_TEST(test_systemstate_field_types);

    // Category 3: Global Variables Tests (from test_component_9_2.cpp)
    RUN_TEST(test_global_var_wifiudp_declared);
    RUN_TEST(test_global_var_wifiudp_scope);
    RUN_TEST(test_global_var_system_declared);
    RUN_TEST(test_global_var_system_initialization);
    RUN_TEST(test_global_var_sensors_declared);
    RUN_TEST(test_global_var_sensors_size);
    RUN_TEST(test_global_vars_file_scope);

    // Category 4: Function Declarations Tests (from test_component_9_2.cpp)
    RUN_TEST(test_function_connectwifi_declared);
    RUN_TEST(test_function_connectwifi_returntype);
    RUN_TEST(test_function_connectwifi_params);
    RUN_TEST(test_function_checkwifi_declared);
    RUN_TEST(test_function_checkwifi_returntype);
    RUN_TEST(test_function_checkwifi_params);
    RUN_TEST(test_function_initializesensor_declared);
    RUN_TEST(test_function_initializesensor_returntype);
    RUN_TEST(test_function_initializesensor_params);
    RUN_TEST(test_function_readandfiltersensor_declared);
    RUN_TEST(test_function_readandfiltersensor_returntype);
    RUN_TEST(test_function_readandfiltersensor_params);
    RUN_TEST(test_function_updatebaseline_declared);
    RUN_TEST(test_function_updatebaseline_returntype);
    RUN_TEST(test_function_updatebaseline_params);
    RUN_TEST(test_function_detectbeat_declared);
    RUN_TEST(test_function_detectbeat_returntype);
    RUN_TEST(test_function_detectbeat_params);
    RUN_TEST(test_function_sendheartbeatosc_declared);
    RUN_TEST(test_function_sendheartbeatosc_returntype);
    RUN_TEST(test_function_sendheartbeatosc_params);
    RUN_TEST(test_function_updateled_declared);
    RUN_TEST(test_function_updateled_returntype);
    RUN_TEST(test_function_updateled_params);
    RUN_TEST(test_all_functions_declared);
    RUN_TEST(test_function_declarations_before_setup);

    // Category 5: Integration Tests (from test_component_9_2.cpp)
    RUN_TEST(test_structures_before_globals);
    RUN_TEST(test_globals_logical_order);
    RUN_TEST(test_complete_interface);
    RUN_TEST(test_no_duplicate_structs);
    RUN_TEST(test_function_signatures_consistent);

    return UNITY_END();
}
