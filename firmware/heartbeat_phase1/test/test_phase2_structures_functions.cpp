/**
 * Test Suite for Components 8.2-8.5: Phase 2 Data Structures and Functions
 *
 * Tests new Phase 2 data structures and signal processing functions
 * Framework: PlatformIO native testing (Unity)
 *
 * This test suite validates:
 * Component 8.2: Data structure modifications (SystemState, SensorState, global variables)
 * Component 8.3: Sensor initialization function (initializeSensor)
 * Component 8.4: Moving average filter (updateMovingAverage)
 * Component 8.5: Baseline tracking (updateBaseline)
 *
 * Testing Strategy: Static code analysis (text search and regex)
 * - No runtime testing (no hardware dependencies)
 * - Validates structure definitions, field presence, function signatures
 * - Checks for correct types and initialization patterns
 */

#include <unity.h>
#include <cstring>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <regex>

// ============================================================================
// HELPER FUNCTIONS FOR SOURCE CODE ANALYSIS
// ============================================================================

std::string read_source_file(const char* filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        return "";
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

bool source_contains(const std::string& source, const std::string& pattern) {
    return source.find(pattern) != std::string::npos;
}

bool source_matches_regex(const std::string& source, const std::string& pattern_str) {
    try {
        std::regex pattern(pattern_str);
        return std::regex_search(source, pattern);
    } catch (...) {
        return false;
    }
}

int count_pattern_occurrences(const std::string& source, const std::string& pattern) {
    int count = 0;
    size_t pos = 0;
    while ((pos = source.find(pattern, pos)) != std::string::npos) {
        count++;
        pos += pattern.length();
    }
    return count;
}

// Helper: Check if pattern exists and is NOT commented
bool pattern_active(const std::string& source, const std::string& pattern) {
    size_t pos = source.find(pattern);
    if (pos == std::string::npos) {
        return false;
    }

    // Check if this occurrence is on a commented line
    size_t line_start = source.rfind('\n', pos);
    if (line_start == std::string::npos) {
        line_start = 0;
    } else {
        line_start++;
    }

    std::string line = source.substr(line_start, pos - line_start);
    // If line contains "//" before pattern, it's commented
    return line.find("//") == std::string::npos;
}

// Helper: Extract struct definition
std::string extract_struct_definition(const std::string& source, const std::string& struct_name) {
    std::regex pattern("struct\\s+" + struct_name + "\\s*\\{[^}]*\\}");
    std::smatch match;
    if (std::regex_search(source, match, pattern)) {
        return match.str();
    }
    return "";
}

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
// CATEGORY 1: SYSTEMSTATE STRUCTURE MODIFICATIONS (Component 8.2, TRD §5.1)
// ============================================================================

/**
 * TEST 1.1: SystemState structure exists
 * Requirement: Phase 1 SystemState structure preserved but modified
 */
void test_systemstate_structure_exists(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify struct exists
    TEST_ASSERT_TRUE(source_contains(source, "struct SystemState"));
}

/**
 * TEST 1.2: SystemState retains wifiConnected field (Phase 1)
 * Requirement: bool wifiConnected field must remain
 */
void test_systemstate_has_wifi_connected(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    TEST_ASSERT_TRUE(source_contains(struct_def, "bool wifiConnected"));
}

/**
 * TEST 1.3: SystemState removes lastMessageTime field (Phase 1 removal)
 * Requirement: lastMessageTime should be removed or commented out
 */
void test_systemstate_removes_last_message_time(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    // Field should be either absent or commented in struct definition
    TEST_ASSERT_FALSE(pattern_active(struct_def, "lastMessageTime"));
}

/**
 * TEST 1.4: SystemState removes messageCounter field (Phase 1 removal)
 * Requirement: messageCounter should be removed or commented out
 */
void test_systemstate_removes_message_counter(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    // Field should be either absent or commented in struct definition
    TEST_ASSERT_FALSE(pattern_active(struct_def, "messageCounter"));
}

/**
 * TEST 1.5: SystemState adds lastWiFiCheckTime field (Phase 2 new)
 * Requirement: unsigned long lastWiFiCheckTime field added
 */
void test_systemstate_adds_last_wifi_check_time(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    TEST_ASSERT_TRUE(source_contains(struct_def, "unsigned long lastWiFiCheckTime"));
}

/**
 * TEST 1.6: SystemState adds loopCounter field (Phase 2 new)
 * Requirement: unsigned long loopCounter field added for debug output throttling
 */
void test_systemstate_adds_loop_counter(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    TEST_ASSERT_TRUE(source_contains(struct_def, "unsigned long loopCounter"));
}

/**
 * TEST 1.7: SystemState initialization updated
 * Requirement: Initial values include wifiConnected, lastWiFiCheckTime, loopCounter
 */
void test_systemstate_initialization(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should have initialization with new fields
    // Look for state = { ... } pattern with at least false, 0, 0
    TEST_ASSERT_TRUE(source_matches_regex(source, "SystemState\\s+state\\s*=\\s*\\{"));
}

// ============================================================================
// CATEGORY 2: SENSORSTATE STRUCTURE (Component 8.2, TRD §5.2)
// ============================================================================

/**
 * TEST 2.1: SensorState structure exists
 * Requirement: New SensorState struct defined for signal processing
 */
void test_sensorstate_structure_exists(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "struct SensorState"));
}

/**
 * TEST 2.2: SensorState has moving average buffer (rawSamples array)
 * Requirement: int rawSamples[MOVING_AVG_SAMPLES] circular buffer
 */
void test_sensorstate_has_raw_samples_array(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    // Check for rawSamples array with MOVING_AVG_SAMPLES size
    TEST_ASSERT_TRUE(source_matches_regex(struct_def, "int\\s+rawSamples\\s*\\["));
}

/**
 * TEST 2.3: SensorState has sampleIndex field
 * Requirement: int sampleIndex for circular buffer position
 */
void test_sensorstate_has_sample_index(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_TRUE(source_contains(struct_def, "int sampleIndex"));
}

/**
 * TEST 2.4: SensorState has smoothedValue field
 * Requirement: int smoothedValue for moving average output
 */
void test_sensorstate_has_smoothed_value(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_TRUE(source_contains(struct_def, "int smoothedValue"));
}

/**
 * TEST 2.5: SensorState has baseline tracking fields (minValue, maxValue)
 * Requirement: int minValue and int maxValue for baseline tracking
 */
void test_sensorstate_has_baseline_fields(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_TRUE(source_contains(struct_def, "int minValue"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "int maxValue"));
}

/**
 * TEST 2.6: SensorState has samplesSinceDecay field
 * Requirement: int samplesSinceDecay for periodic decay counter
 */
void test_sensorstate_has_samples_since_decay(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_TRUE(source_contains(struct_def, "int samplesSinceDecay"));
}

/**
 * TEST 2.7: SensorState has beat detection state fields
 * Requirement: aboveThreshold, lastBeatTime, lastIBI, firstBeatDetected
 */
void test_sensorstate_has_beat_detection_fields(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_TRUE(source_contains(struct_def, "bool aboveThreshold"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "unsigned long lastBeatTime"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "unsigned long lastIBI"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "bool firstBeatDetected"));
}

/**
 * TEST 2.8: SensorState has disconnection detection fields
 * Requirement: isConnected, lastRawValue, flatSampleCount
 */
void test_sensorstate_has_disconnection_fields(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_TRUE(source_contains(struct_def, "bool isConnected"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "int lastRawValue"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "int flatSampleCount"));
}

/**
 * TEST 2.9: SensorState has all required fields (integration check)
 * Requirement: All 14 fields present in structure
 */
void test_sensorstate_has_all_fields(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");

    // Count all required fields
    int field_count = 0;
    if (source_contains(struct_def, "rawSamples")) field_count++;
    if (source_contains(struct_def, "sampleIndex")) field_count++;
    if (source_contains(struct_def, "smoothedValue")) field_count++;
    if (source_contains(struct_def, "minValue")) field_count++;
    if (source_contains(struct_def, "maxValue")) field_count++;
    if (source_contains(struct_def, "samplesSinceDecay")) field_count++;
    if (source_contains(struct_def, "aboveThreshold")) field_count++;
    if (source_contains(struct_def, "lastBeatTime")) field_count++;
    if (source_contains(struct_def, "lastIBI")) field_count++;
    if (source_contains(struct_def, "firstBeatDetected")) field_count++;
    if (source_contains(struct_def, "isConnected")) field_count++;
    if (source_contains(struct_def, "lastRawValue")) field_count++;
    if (source_contains(struct_def, "flatSampleCount")) field_count++;

    // Should have 13 fields (rawSamples counts as 1)
    TEST_ASSERT_GREATER_OR_EQUAL(13, field_count);
}

// ============================================================================
// CATEGORY 3: GLOBAL VARIABLES (Component 8.2, TRD §5.3)
// ============================================================================

/**
 * TEST 3.1: Global SensorState variable declared
 * Requirement: SensorState sensor; declared at global scope
 */
void test_global_sensor_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for "SensorState sensor" declaration (not in function)
    TEST_ASSERT_TRUE(source_matches_regex(source, "SensorState\\s+sensor\\s*[=;]"));
}

/**
 * TEST 3.2: Global ledPulseTime variable declared
 * Requirement: static unsigned long ledPulseTime = 0;
 */
void test_global_led_pulse_time_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for ledPulseTime declaration
    TEST_ASSERT_TRUE(source_contains(source, "ledPulseTime"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "unsigned\\s+long\\s+ledPulseTime"));
}

/**
 * TEST 3.3: Global SystemState variable updated (Phase 1 kept)
 * Requirement: SystemState state; still exists with new initialization
 */
void test_global_system_state_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_matches_regex(source, "SystemState\\s+state\\s*[=;]"));
}

/**
 * TEST 3.4: Global WiFiUDP variable preserved (Phase 1)
 * Requirement: WiFiUDP udp; still exists
 */
void test_global_udp_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "WiFiUDP udp"));
}

// ============================================================================
// CATEGORY 4: INITIALIZESENSOR FUNCTION (Component 8.3, TRD §6.1)
// ============================================================================

/**
 * TEST 4.1: initializeSensor function declared
 * Requirement: void initializeSensor() function exists
 */
void test_initialize_sensor_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void initializeSensor"));
}

/**
 * TEST 4.2: initializeSensor has function body
 * Requirement: Function implementation exists (not just declaration)
 */
void test_initialize_sensor_implemented(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for function definition with body
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+initializeSensor\\s*\\(\\s*\\)\\s*\\{"));
}

/**
 * TEST 4.3: initializeSensor configures ADC attenuation (R1)
 * Requirement: Calls analogSetAttenuation(ADC_11db)
 */
void test_initialize_sensor_adc_attenuation(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for analogSetAttenuation call
    TEST_ASSERT_TRUE(source_contains(source, "analogSetAttenuation"));
    TEST_ASSERT_TRUE(source_contains(source, "ADC_11db"));
}

/**
 * TEST 4.4: initializeSensor configures ADC resolution (R1)
 * Requirement: Calls analogReadResolution(12)
 */
void test_initialize_sensor_adc_resolution(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for analogReadResolution call
    TEST_ASSERT_TRUE(source_contains(source, "analogReadResolution"));
}

/**
 * TEST 4.5: initializeSensor reads first ADC sample (R2)
 * Requirement: Reads analogRead(SENSOR_PIN) for initialization
 */
void test_initialize_sensor_first_reading(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for analogRead(SENSOR_PIN) in initializeSensor context
    TEST_ASSERT_TRUE(source_contains(source, "analogRead"));
    TEST_ASSERT_TRUE(source_contains(source, "SENSOR_PIN"));
}

/**
 * TEST 4.6: initializeSensor pre-fills rawSamples buffer (R3)
 * Requirement: Loop to fill rawSamples[] with initial reading
 */
void test_initialize_sensor_prefills_buffer(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for loop pattern filling rawSamples
    // Should have for loop with MOVING_AVG_SAMPLES and rawSamples assignment
    TEST_ASSERT_TRUE(source_contains(source, "rawSamples"));
    TEST_ASSERT_TRUE(source_contains(source, "MOVING_AVG_SAMPLES"));
}

/**
 * TEST 4.7: initializeSensor initializes baseline values (R4)
 * Requirement: Sets minValue, maxValue, smoothedValue to first reading
 */
void test_initialize_sensor_baseline_init(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for assignments to baseline fields
    TEST_ASSERT_TRUE(source_matches_regex(source, "minValue\\s*="));
    TEST_ASSERT_TRUE(source_matches_regex(source, "maxValue\\s*="));
    TEST_ASSERT_TRUE(source_matches_regex(source, "smoothedValue\\s*="));
}

/**
 * TEST 4.8: initializeSensor sets connection state (R5)
 * Requirement: Sets isConnected = true, lastRawValue, lastBeatTime
 */
void test_initialize_sensor_connection_state(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for isConnected assignment
    TEST_ASSERT_TRUE(source_matches_regex(source, "isConnected\\s*="));
}

// ============================================================================
// CATEGORY 5: UPDATEMOVINGAVERAGE FUNCTION (Component 8.4, TRD §6.2)
// ============================================================================

/**
 * TEST 5.1: updateMovingAverage function declared
 * Requirement: void updateMovingAverage(int rawValue) function exists
 */
void test_update_moving_average_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void updateMovingAverage"));
}

/**
 * TEST 5.2: updateMovingAverage has correct signature
 * Requirement: Takes int parameter (rawValue)
 */
void test_update_moving_average_signature(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for function signature with int parameter
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+updateMovingAverage\\s*\\(\\s*int\\s+\\w+\\s*\\)"));
}

/**
 * TEST 5.3: updateMovingAverage updates circular buffer (R6)
 * Requirement: Assigns to rawSamples[sampleIndex] and increments index
 */
void test_update_moving_average_buffer_update(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for rawSamples array assignment
    TEST_ASSERT_TRUE(source_matches_regex(source, "rawSamples\\s*\\["));
    // Look for sampleIndex manipulation
    TEST_ASSERT_TRUE(source_matches_regex(source, "sampleIndex"));
}

/**
 * TEST 5.4: updateMovingAverage uses modulo for circular buffer (R6)
 * Requirement: Index wraps using % MOVING_AVG_SAMPLES
 */
void test_update_moving_average_modulo_wrap(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for modulo operation with MOVING_AVG_SAMPLES
    TEST_ASSERT_TRUE(source_matches_regex(source, "%\\s*MOVING_AVG_SAMPLES"));
}

/**
 * TEST 5.5: updateMovingAverage calculates mean (R7)
 * Requirement: Sums samples and divides by MOVING_AVG_SAMPLES
 */
void test_update_moving_average_calculates_mean(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for loop summing samples and division
    // Should have sum variable and division by MOVING_AVG_SAMPLES
    TEST_ASSERT_TRUE(source_contains(source, "sum"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "/\\s*MOVING_AVG_SAMPLES"));
}

/**
 * TEST 5.6: updateMovingAverage stores result in smoothedValue (R7)
 * Requirement: Result assigned to sensor.smoothedValue
 */
void test_update_moving_average_stores_result(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for assignment to smoothedValue
    TEST_ASSERT_TRUE(source_matches_regex(source, "smoothedValue\\s*="));
}

// ============================================================================
// CATEGORY 6: UPDATEBASELINE FUNCTION (Component 8.5, TRD §6.3)
// ============================================================================

/**
 * TEST 6.1: updateBaseline function declared
 * Requirement: void updateBaseline() function exists
 */
void test_update_baseline_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void updateBaseline"));
}

/**
 * TEST 6.2: updateBaseline has correct signature
 * Requirement: No parameters (void)
 */
void test_update_baseline_signature(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for function with no parameters
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+updateBaseline\\s*\\(\\s*\\)"));
}

/**
 * TEST 6.3: updateBaseline implements instant expansion for min (R9)
 * Requirement: If smoothedValue < minValue, set minValue = smoothedValue
 */
void test_update_baseline_instant_expansion_min(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for comparison and assignment pattern for minValue
    TEST_ASSERT_TRUE(source_matches_regex(source, "smoothedValue\\s*<\\s*minValue"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "minValue\\s*=\\s*.*smoothedValue"));
}

/**
 * TEST 6.4: updateBaseline implements instant expansion for max (R9)
 * Requirement: If smoothedValue > maxValue, set maxValue = smoothedValue
 */
void test_update_baseline_instant_expansion_max(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for comparison and assignment pattern for maxValue
    TEST_ASSERT_TRUE(source_matches_regex(source, "smoothedValue\\s*>\\s*maxValue"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "maxValue\\s*=\\s*.*smoothedValue"));
}

/**
 * TEST 6.5: updateBaseline increments decay counter (R10)
 * Requirement: Increments samplesSinceDecay each call
 */
void test_update_baseline_increments_decay_counter(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for samplesSinceDecay increment (++ or +=)
    TEST_ASSERT_TRUE(source_matches_regex(source, "samplesSinceDecay\\s*(\\+\\+|\\+=)"));
}

/**
 * TEST 6.6: updateBaseline checks decay interval (R10)
 * Requirement: Compares samplesSinceDecay >= BASELINE_DECAY_INTERVAL
 */
void test_update_baseline_checks_decay_interval(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for comparison with BASELINE_DECAY_INTERVAL
    TEST_ASSERT_TRUE(source_contains(source, "BASELINE_DECAY_INTERVAL"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "samplesSinceDecay\\s*>="));
}

/**
 * TEST 6.7: updateBaseline applies periodic decay (R10)
 * Requirement: Applies BASELINE_DECAY_RATE to min/max values
 */
void test_update_baseline_applies_decay(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for BASELINE_DECAY_RATE usage
    TEST_ASSERT_TRUE(source_contains(source, "BASELINE_DECAY_RATE"));
}

/**
 * TEST 6.8: updateBaseline resets decay counter (R10)
 * Requirement: Resets samplesSinceDecay = 0 after decay
 */
void test_update_baseline_resets_counter(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for samplesSinceDecay = 0 assignment
    TEST_ASSERT_TRUE(source_matches_regex(source, "samplesSinceDecay\\s*=\\s*0"));
}

/**
 * TEST 6.9: updateBaseline uses float multiplication for decay (R11)
 * Requirement: Integer arithmetic with float multiplication pattern
 */
void test_update_baseline_float_arithmetic(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for multiplication with BASELINE_DECAY_RATE (float constant)
    // Should have pattern like: value * BASELINE_DECAY_RATE
    TEST_ASSERT_TRUE(source_matches_regex(source, "\\*\\s*BASELINE_DECAY_RATE"));
}

// ============================================================================
// CATEGORY 7: INTEGRATION TESTS
// ============================================================================

/**
 * TEST 7.1: All new Phase 2 functions declared
 * Requirement: All 5 new functions present in code
 */
void test_all_phase2_functions_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    int function_count = 0;
    if (source_contains(source, "void initializeSensor")) function_count++;
    if (source_contains(source, "void updateMovingAverage")) function_count++;
    if (source_contains(source, "void updateBaseline")) function_count++;
    if (source_contains(source, "void checkDisconnection")) function_count++;
    if (source_contains(source, "void detectBeat")) function_count++;

    // Should have at least 3 functions implemented (8.3-8.5)
    // checkDisconnection and detectBeat are in later components
    TEST_ASSERT_GREATER_OR_EQUAL(3, function_count);
}

/**
 * TEST 7.2: Data structures and functions compatible
 * Requirement: Functions use fields from SensorState structure
 */
void test_structures_functions_compatible(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify functions reference sensor. fields
    TEST_ASSERT_TRUE(source_contains(source, "sensor."));
}

/**
 * TEST 7.3: initializeSensor called from setup()
 * Requirement: Sensor initialization happens during setup
 */
void test_initialize_sensor_called_from_setup(void) {
    std::string source = read_source_file("src/main.cpp");

    // Look for initializeSensor() call (likely in setup)
    TEST_ASSERT_TRUE(source_matches_regex(source, "initializeSensor\\s*\\(\\s*\\)\\s*;"));
}

/**
 * TEST 7.4: Moving average and baseline functions work together
 * Requirement: Both functions use smoothedValue, minValue, maxValue
 */
void test_moving_average_baseline_integration(void) {
    std::string source = read_source_file("src/main.cpp");

    // Both functions should reference these fields
    int smoothed_refs = count_pattern_occurrences(source, "smoothedValue");
    int min_refs = count_pattern_occurrences(source, "minValue");
    int max_refs = count_pattern_occurrences(source, "maxValue");

    TEST_ASSERT_GREATER_THAN(2, smoothed_refs);
    TEST_ASSERT_GREATER_THAN(2, min_refs);
    TEST_ASSERT_GREATER_THAN(2, max_refs);
}

/**
 * TEST 7.5: All Phase 2 constants used by functions
 * Requirement: Functions reference Phase 2 configuration constants
 */
void test_phase2_constants_used(void) {
    std::string source = read_source_file("src/main.cpp");

    // Functions should use these constants
    TEST_ASSERT_TRUE(source_contains(source, "MOVING_AVG_SAMPLES"));
    TEST_ASSERT_TRUE(source_contains(source, "BASELINE_DECAY_RATE"));
    TEST_ASSERT_TRUE(source_contains(source, "BASELINE_DECAY_INTERVAL"));
    TEST_ASSERT_TRUE(source_contains(source, "SENSOR_PIN"));
}

/**
 * TEST 7.6: Code organization maintained
 * Requirement: Clear sections with comments (Phase 1 pattern preserved)
 */
void test_code_organization_maintained(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should have section headers
    TEST_ASSERT_TRUE(source_contains(source, "CONFIGURATION"));
    TEST_ASSERT_TRUE(source_contains(source, "GLOBAL STATE"));
    TEST_ASSERT_TRUE(source_contains(source, "FUNCTION"));
}

/**
 * TEST 7.7: Phase 1 functions preserved
 * Requirement: connectWiFi, sendHeartbeatOSC, checkWiFi, updateLED still exist
 */
void test_phase1_functions_preserved(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "bool connectWiFi"));
    TEST_ASSERT_TRUE(source_contains(source, "void sendHeartbeatOSC"));
    TEST_ASSERT_TRUE(source_contains(source, "void checkWiFi"));
    TEST_ASSERT_TRUE(source_contains(source, "void updateLED"));
}

// ============================================================================
// TEST RUNNER MAIN
// ============================================================================

int main(int argc, char* argv[]) {
    UNITY_BEGIN();

    // Category 1: SystemState Structure Modifications (Component 8.2, TRD §5.1)
    RUN_TEST(test_systemstate_structure_exists);
    RUN_TEST(test_systemstate_has_wifi_connected);
    RUN_TEST(test_systemstate_removes_last_message_time);
    RUN_TEST(test_systemstate_removes_message_counter);
    RUN_TEST(test_systemstate_adds_last_wifi_check_time);
    RUN_TEST(test_systemstate_adds_loop_counter);
    RUN_TEST(test_systemstate_initialization);

    // Category 2: SensorState Structure (Component 8.2, TRD §5.2)
    RUN_TEST(test_sensorstate_structure_exists);
    RUN_TEST(test_sensorstate_has_raw_samples_array);
    RUN_TEST(test_sensorstate_has_sample_index);
    RUN_TEST(test_sensorstate_has_smoothed_value);
    RUN_TEST(test_sensorstate_has_baseline_fields);
    RUN_TEST(test_sensorstate_has_samples_since_decay);
    RUN_TEST(test_sensorstate_has_beat_detection_fields);
    RUN_TEST(test_sensorstate_has_disconnection_fields);
    RUN_TEST(test_sensorstate_has_all_fields);

    // Category 3: Global Variables (Component 8.2, TRD §5.3)
    RUN_TEST(test_global_sensor_declared);
    RUN_TEST(test_global_led_pulse_time_declared);
    RUN_TEST(test_global_system_state_declared);
    RUN_TEST(test_global_udp_preserved);

    // Category 4: initializeSensor Function (Component 8.3, TRD §6.1)
    RUN_TEST(test_initialize_sensor_declared);
    RUN_TEST(test_initialize_sensor_implemented);
    RUN_TEST(test_initialize_sensor_adc_attenuation);
    RUN_TEST(test_initialize_sensor_adc_resolution);
    RUN_TEST(test_initialize_sensor_first_reading);
    RUN_TEST(test_initialize_sensor_prefills_buffer);
    RUN_TEST(test_initialize_sensor_baseline_init);
    RUN_TEST(test_initialize_sensor_connection_state);

    // Category 5: updateMovingAverage Function (Component 8.4, TRD §6.2)
    RUN_TEST(test_update_moving_average_declared);
    RUN_TEST(test_update_moving_average_signature);
    RUN_TEST(test_update_moving_average_buffer_update);
    RUN_TEST(test_update_moving_average_modulo_wrap);
    RUN_TEST(test_update_moving_average_calculates_mean);
    RUN_TEST(test_update_moving_average_stores_result);

    // Category 6: updateBaseline Function (Component 8.5, TRD §6.3)
    RUN_TEST(test_update_baseline_declared);
    RUN_TEST(test_update_baseline_signature);
    RUN_TEST(test_update_baseline_instant_expansion_min);
    RUN_TEST(test_update_baseline_instant_expansion_max);
    RUN_TEST(test_update_baseline_increments_decay_counter);
    RUN_TEST(test_update_baseline_checks_decay_interval);
    RUN_TEST(test_update_baseline_applies_decay);
    RUN_TEST(test_update_baseline_resets_counter);
    RUN_TEST(test_update_baseline_float_arithmetic);

    // Category 7: Integration Tests
    RUN_TEST(test_all_phase2_functions_declared);
    RUN_TEST(test_structures_functions_compatible);
    RUN_TEST(test_initialize_sensor_called_from_setup);
    RUN_TEST(test_moving_average_baseline_integration);
    RUN_TEST(test_phase2_constants_used);
    RUN_TEST(test_code_organization_maintained);
    RUN_TEST(test_phase1_functions_preserved);

    return UNITY_END();
}
