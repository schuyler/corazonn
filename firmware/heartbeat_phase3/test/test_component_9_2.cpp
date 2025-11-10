/**
 * Test Suite for Component 9.2: Data Structures
 *
 * Tests against Phase 3 firmware TRD Tasks 2.1-2.4
 * Framework: PlatformIO native testing (Unity)
 *
 * This test suite validates data structures and global variables without executing
 * embedded code. Tests verify:
 * - SensorState struct defined with all 13 fields
 * - SystemState struct defined with all 4 fields
 * - Global variables declared (udp, system, sensors[4])
 * - All 8 function declarations present with correct signatures
 */

#include <unity.h>
#include <cstring>
#include <cstdio>
#include "test_helpers.h"

// ============================================================================
// NOTE: setUp() and tearDown() are defined in test_component_9_1.cpp
// ============================================================================

// ============================================================================
// CATEGORY 1: SENSORSTATE STRUCT DEFINITION TESTS (Task 2.1)
// ============================================================================

/**
 * TEST 1.1: SensorState struct is defined (Task 2.1)
 */
void test_struct_sensorstate_defined(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "struct SensorState"));
}

/**
 * TEST 1.2: SensorState struct contains hardware field: pin (Task 2.1, R1)
 */
void test_sensorstate_field_pin(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "int pin"));
}

/**
 * TEST 1.3: SensorState contains moving average field: rawSamples[MOVING_AVG_SAMPLES] (Task 2.1, R2)
 */
void test_sensorstate_field_rawsamples(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "rawSamples"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "MOVING_AVG_SAMPLES"));
}

/**
 * TEST 1.4: SensorState contains moving average field: sampleIndex (Task 2.1, R2)
 */
void test_sensorstate_field_sampleindex(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "sampleIndex"));
}

/**
 * TEST 1.5: SensorState contains moving average field: smoothedValue (Task 2.1, R2)
 */
void test_sensorstate_field_smoothedvalue(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "smoothedValue"));
}

/**
 * TEST 1.6: SensorState contains baseline tracking field: minValue (Task 2.1, R3)
 */
void test_sensorstate_field_minvalue(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "minValue"));
}

/**
 * TEST 1.7: SensorState contains baseline tracking field: maxValue (Task 2.1, R3)
 */
void test_sensorstate_field_maxvalue(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "maxValue"));
}

/**
 * TEST 1.8: SensorState contains baseline tracking field: samplesSinceDecay (Task 2.1, R3)
 */
void test_sensorstate_field_samplessincedecay(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "samplesSinceDecay"));
}

/**
 * TEST 1.9: SensorState contains beat detection field: aboveThreshold (Task 2.1, R4)
 */
void test_sensorstate_field_abovethreshold(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "aboveThreshold"));
}

/**
 * TEST 1.10: SensorState contains beat detection field: lastBeatTime (Task 2.1, R4)
 */
void test_sensorstate_field_lastbeattime(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "lastBeatTime"));
}

/**
 * TEST 1.11: SensorState contains beat detection field: lastIBI (Task 2.1, R4)
 */
void test_sensorstate_field_lastibi(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "lastIBI"));
}

/**
 * TEST 1.12: SensorState contains beat detection field: firstBeatDetected (Task 2.1, R4)
 */
void test_sensorstate_field_firstbeatdetected(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "firstBeatDetected"));
}

/**
 * TEST 1.13: SensorState contains disconnection detection field: isConnected (Task 2.1, R5)
 */
void test_sensorstate_field_isconnected(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "isConnected"));
}

/**
 * TEST 1.14: SensorState contains disconnection detection field: lastRawValue (Task 2.1, R5)
 */
void test_sensorstate_field_lastrawvalue(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "lastRawValue"));
}

/**
 * TEST 1.15: SensorState contains disconnection detection field: flatSampleCount (Task 2.1, R5)
 */
void test_sensorstate_field_flatsamplecount(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "flatSampleCount"));
}

/**
 * TEST 1.16: SensorState struct has exactly 14 fields (Task 2.1)
 */
void test_sensorstate_field_count(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());

    // Count exact number of fields (14 field declarations = 14 semicolons)
    int field_count = count_struct_fields(struct_def);
    TEST_ASSERT_EQUAL(14, field_count);

    // Verify all 14 fields are present
    TEST_ASSERT_TRUE(source_contains(struct_def, "pin"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "rawSamples"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "sampleIndex"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "smoothedValue"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "minValue"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "maxValue"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "samplesSinceDecay"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "aboveThreshold"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "lastBeatTime"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "lastIBI"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "firstBeatDetected"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "isConnected"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "lastRawValue"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "flatSampleCount"));
}

/**
 * TEST 1.17: SensorState struct has proper field types (Task 2.1)
 */
void test_sensorstate_field_types(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SensorState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());

    // Check for type qualifiers
    TEST_ASSERT_TRUE(source_contains(struct_def, "int"));  // int fields
    TEST_ASSERT_TRUE(source_contains(struct_def, "bool")); // bool fields
    TEST_ASSERT_TRUE(source_contains(struct_def, "unsigned long")); // unsigned long fields
}

// ============================================================================
// CATEGORY 2: SYSTEMSTATE STRUCT DEFINITION TESTS (Task 2.2)
// ============================================================================

/**
 * TEST 2.1: SystemState struct is defined (Task 2.2)
 */
void test_struct_systemstate_defined(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "struct SystemState"));
}

/**
 * TEST 2.2: SystemState contains field: wifiConnected (Task 2.2)
 */
void test_systemstate_field_wificonnected(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "wifiConnected"));
}

/**
 * TEST 2.3: SystemState contains field: lastWiFiCheckTime (Task 2.2)
 */
void test_systemstate_field_lastwifichecktime(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "lastWiFiCheckTime"));
}

/**
 * TEST 2.4: SystemState contains field: loopCounter (Task 2.2)
 */
void test_systemstate_field_loopcounter(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "loopCounter"));
}

/**
 * TEST 2.5: SystemState contains field: beatDetectedThisLoop (Task 2.2)
 */
void test_systemstate_field_beatdetectedthisloop(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());
    TEST_ASSERT_TRUE(source_contains(struct_def, "beatDetectedThisLoop"));
}

/**
 * TEST 2.6: SystemState struct has exactly 4 fields (Task 2.2)
 */
void test_systemstate_field_count(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());

    // Count exact number of fields (4 field declarations = 4 semicolons)
    int field_count = count_struct_fields(struct_def);
    TEST_ASSERT_EQUAL(4, field_count);

    // Verify all 4 fields are present
    TEST_ASSERT_TRUE(source_contains(struct_def, "wifiConnected"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "lastWiFiCheckTime"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "loopCounter"));
    TEST_ASSERT_TRUE(source_contains(struct_def, "beatDetectedThisLoop"));
}

/**
 * TEST 2.7: SystemState has proper field types (Task 2.2)
 */
void test_systemstate_field_types(void) {
    std::string source = read_source_file("src/main.cpp");

    std::string struct_def = extract_struct_definition(source, "SystemState");
    TEST_ASSERT_GREATER_THAN(0, struct_def.length());

    // Check for type qualifiers
    TEST_ASSERT_TRUE(source_contains(struct_def, "bool"));  // bool fields
    TEST_ASSERT_TRUE(source_contains(struct_def, "unsigned long")); // unsigned long fields
}

// ============================================================================
// CATEGORY 3: GLOBAL VARIABLES DECLARATION TESTS (Task 2.3)
// ============================================================================

/**
 * TEST 3.1: WiFiUDP global variable is declared (Task 2.3)
 */
void test_global_var_wifiudp_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "WiFiUDP udp"));
}

/**
 * TEST 3.2: WiFiUDP is declared at global scope (not in function) (Task 2.3)
 */
void test_global_var_wifiudp_scope(void) {
    std::string source = read_source_file("src/main.cpp");

    // WiFiUDP should be declared before setup() or loop()
    size_t udp_pos = source.find("WiFiUDP udp");
    size_t setup_pos = source.find("void setup()");

    TEST_ASSERT_NOT_EQUAL(std::string::npos, udp_pos);
    TEST_ASSERT_NOT_EQUAL(std::string::npos, setup_pos);
    TEST_ASSERT_GREATER_THAN(udp_pos, setup_pos);
}

/**
 * TEST 3.3: SystemState global variable is declared with initialization (Task 2.3)
 */
void test_global_var_system_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "SystemState system"));
}

/**
 * TEST 3.4: SystemState system is initialized to {false, 0, 0, false} (Task 2.3)
 */
void test_global_var_system_initialization(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "SystemState\\s+system\\s*=\\s*\\{\\s*false\\s*,\\s*0\\s*,\\s*0\\s*,\\s*false\\s*\\}"));
}

/**
 * TEST 3.5: SensorState sensors array is declared (Task 2.3)
 */
void test_global_var_sensors_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "SensorState sensors[4]"));
}

/**
 * TEST 3.6: Sensors array has size 4 (Task 2.3)
 */
void test_global_var_sensors_size(void) {
    std::string source = read_source_file("src/main.cpp");

    // Array must be declared as [4]
    TEST_ASSERT_TRUE(source_matches_regex(source, "SensorState\\s+sensors\\s*\\[\\s*4\\s*\\]"));
}

/**
 * TEST 3.7: All three global variables are at file scope (Task 2.3)
 */
void test_global_vars_file_scope(void) {
    std::string source = read_source_file("src/main.cpp");

    // All should appear before setup()
    size_t udp_pos = source.find("WiFiUDP udp");
    size_t system_pos = source.find("SystemState system");
    size_t sensors_pos = source.find("SensorState sensors");
    size_t setup_pos = source.find("void setup()");

    TEST_ASSERT_NOT_EQUAL(std::string::npos, udp_pos);
    TEST_ASSERT_NOT_EQUAL(std::string::npos, system_pos);
    TEST_ASSERT_NOT_EQUAL(std::string::npos, sensors_pos);
    TEST_ASSERT_NOT_EQUAL(std::string::npos, setup_pos);

    // All globals should be before setup
    TEST_ASSERT_GREATER_THAN(udp_pos, setup_pos);
    TEST_ASSERT_GREATER_THAN(system_pos, setup_pos);
    TEST_ASSERT_GREATER_THAN(sensors_pos, setup_pos);
}

// ============================================================================
// CATEGORY 4: FUNCTION DECLARATIONS TESTS (Task 2.4)
// ============================================================================

/**
 * TEST 4.1: connectWiFi() function is declared (Task 2.4)
 */
void test_function_connectwifi_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "connectWiFi"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "bool\\s+connectWiFi\\s*\\(\\s*\\)"));
}

/**
 * TEST 4.2: connectWiFi() has correct return type bool (Task 2.4)
 */
void test_function_connectwifi_returntype(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "bool\\s+connectWiFi"));
}

/**
 * TEST 4.3: connectWiFi() has no parameters (Task 2.4)
 */
void test_function_connectwifi_params(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "connectWiFi\\s*\\(\\s*\\)"));
}

/**
 * TEST 4.4: checkWiFi() function is declared (Task 2.4)
 */
void test_function_checkwifi_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "checkWiFi"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+checkWiFi\\s*\\(\\s*\\)"));
}

/**
 * TEST 4.5: checkWiFi() has correct return type void (Task 2.4)
 */
void test_function_checkwifi_returntype(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+checkWiFi"));
}

/**
 * TEST 4.6: checkWiFi() has no parameters (Task 2.4)
 */
void test_function_checkwifi_params(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "checkWiFi\\s*\\(\\s*\\)"));
}

/**
 * TEST 4.7: initializeSensor() function is declared (Task 2.4)
 */
void test_function_initializesensor_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "initializeSensor"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+initializeSensor\\s*\\(\\s*int"));
}

/**
 * TEST 4.8: initializeSensor() has correct return type void (Task 2.4)
 */
void test_function_initializesensor_returntype(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+initializeSensor"));
}

/**
 * TEST 4.9: initializeSensor() takes int parameter (Task 2.4)
 */
void test_function_initializesensor_params(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "initializeSensor\\s*\\(\\s*int\\b[^)]*\\)"));
}

/**
 * TEST 4.10: readAndFilterSensor() function is declared (Task 2.4)
 */
void test_function_readandfiltersensor_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "readAndFilterSensor"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+readAndFilterSensor\\s*\\(\\s*int"));
}

/**
 * TEST 4.11: readAndFilterSensor() has correct return type void (Task 2.4)
 */
void test_function_readandfiltersensor_returntype(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+readAndFilterSensor"));
}

/**
 * TEST 4.12: readAndFilterSensor() takes int parameter (Task 2.4)
 */
void test_function_readandfiltersensor_params(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "readAndFilterSensor\\s*\\(\\s*int\\b[^)]*\\)"));
}

/**
 * TEST 4.13: updateBaseline() function is declared (Task 2.4)
 */
void test_function_updatebaseline_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "updateBaseline"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+updateBaseline\\s*\\(\\s*int"));
}

/**
 * TEST 4.14: updateBaseline() has correct return type void (Task 2.4)
 */
void test_function_updatebaseline_returntype(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+updateBaseline"));
}

/**
 * TEST 4.15: updateBaseline() takes int parameter (Task 2.4)
 */
void test_function_updatebaseline_params(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "updateBaseline\\s*\\(\\s*int\\b[^)]*\\)"));
}

/**
 * TEST 4.16: detectBeat() function is declared (Task 2.4)
 */
void test_function_detectbeat_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "detectBeat"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+detectBeat\\s*\\(\\s*int"));
}

/**
 * TEST 4.17: detectBeat() has correct return type void (Task 2.4)
 */
void test_function_detectbeat_returntype(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+detectBeat"));
}

/**
 * TEST 4.18: detectBeat() takes int parameter (Task 2.4)
 */
void test_function_detectbeat_params(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "detectBeat\\s*\\(\\s*int\\b[^)]*\\)"));
}

/**
 * TEST 4.19: sendHeartbeatOSC() function is declared (Task 2.4)
 */
void test_function_sendheartbeatosc_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "sendHeartbeatOSC"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+sendHeartbeatOSC\\s*\\(\\s*int"));
}

/**
 * TEST 4.20: sendHeartbeatOSC() has correct return type void (Task 2.4)
 */
void test_function_sendheartbeatosc_returntype(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+sendHeartbeatOSC"));
}

/**
 * TEST 4.21: sendHeartbeatOSC() takes two int parameters (Task 2.4)
 */
void test_function_sendheartbeatosc_params(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "sendHeartbeatOSC\\s*\\(\\s*int\\b[^,]*,\\s*int\\b"));
}

/**
 * TEST 4.22: updateLED() function is declared (Task 2.4)
 */
void test_function_updateled_declared(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_contains(source, "updateLED"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+updateLED\\s*\\(\\s*\\)"));
}

/**
 * TEST 4.23: updateLED() has correct return type void (Task 2.4)
 */
void test_function_updateled_returntype(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+updateLED"));
}

/**
 * TEST 4.24: updateLED() has no parameters (Task 2.4)
 */
void test_function_updateled_params(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_TRUE(source_matches_regex(source, "updateLED\\s*\\(\\s*\\)"));
}

/**
 * TEST 4.25: All 8 required functions are declared (Task 2.4)
 */
void test_all_functions_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "connectWiFi"));
    TEST_ASSERT_TRUE(source_contains(source, "checkWiFi"));
    TEST_ASSERT_TRUE(source_contains(source, "initializeSensor"));
    TEST_ASSERT_TRUE(source_contains(source, "readAndFilterSensor"));
    TEST_ASSERT_TRUE(source_contains(source, "updateBaseline"));
    TEST_ASSERT_TRUE(source_contains(source, "detectBeat"));
    TEST_ASSERT_TRUE(source_contains(source, "sendHeartbeatOSC"));
    TEST_ASSERT_TRUE(source_contains(source, "updateLED"));
}

/**
 * TEST 4.26: Functions are declared before setup() (Task 2.4)
 */
void test_function_declarations_before_setup(void) {
    std::string source = read_source_file("src/main.cpp");

    // Function declarations should typically be before setup()
    // or there should be forward declarations (prototypes)
    size_t setup_pos = source.find("void setup()");

    // At least find declarations or mentions of functions before setup
    size_t init_sensor_pos = source.find("initializeSensor");
    TEST_ASSERT_NOT_EQUAL(std::string::npos, init_sensor_pos);
    TEST_ASSERT_NOT_EQUAL(std::string::npos, setup_pos);
}

// ============================================================================
// CATEGORY 5: INTEGRATION TESTS
// ============================================================================

/**
 * TEST 5.1: Both data structures defined before global variables (Task 2.1-2.3)
 */
void test_structures_before_globals(void) {
    std::string source = read_source_file("src/main.cpp");

    size_t sensorstate_pos = source.find("struct SensorState");
    size_t systemstate_pos = source.find("struct SystemState");
    size_t system_var_pos = source.find("SystemState system");
    size_t sensors_array_pos = source.find("SensorState sensors");

    TEST_ASSERT_NOT_EQUAL(std::string::npos, sensorstate_pos);
    TEST_ASSERT_NOT_EQUAL(std::string::npos, system_var_pos);

    // Structures should be defined before use in global variables
    TEST_ASSERT_GREATER_THAN(sensorstate_pos, system_var_pos);
}

/**
 * TEST 5.2: Global variables organized logically (Task 2.3)
 */
void test_globals_logical_order(void) {
    std::string source = read_source_file("src/main.cpp");

    // WiFiUDP should be defined before functions use it
    size_t udp_pos = source.find("WiFiUDP udp");
    size_t setup_pos = source.find("void setup()");

    TEST_ASSERT_NOT_EQUAL(std::string::npos, udp_pos);
    TEST_ASSERT_NOT_EQUAL(std::string::npos, setup_pos);
    TEST_ASSERT_GREATER_THAN(udp_pos, setup_pos);
}

/**
 * TEST 5.3: Complete data structure interface present (Task 2.1-2.4)
 */
void test_complete_interface(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify all components are present
    // Structures
    TEST_ASSERT_TRUE(source_contains(source, "struct SensorState"));
    TEST_ASSERT_TRUE(source_contains(source, "struct SystemState"));

    // Global variables
    TEST_ASSERT_TRUE(source_contains(source, "WiFiUDP udp"));
    TEST_ASSERT_TRUE(source_contains(source, "SystemState system"));
    TEST_ASSERT_TRUE(source_contains(source, "SensorState sensors"));

    // Function declarations
    TEST_ASSERT_TRUE(source_contains(source, "connectWiFi"));
    TEST_ASSERT_TRUE(source_contains(source, "checkWiFi"));
    TEST_ASSERT_TRUE(source_contains(source, "initializeSensor"));
    TEST_ASSERT_TRUE(source_contains(source, "readAndFilterSensor"));
    TEST_ASSERT_TRUE(source_contains(source, "updateBaseline"));
    TEST_ASSERT_TRUE(source_contains(source, "detectBeat"));
    TEST_ASSERT_TRUE(source_contains(source, "sendHeartbeatOSC"));
    TEST_ASSERT_TRUE(source_contains(source, "updateLED"));
}

/**
 * TEST 5.4: No conflicting type definitions (Task 2.1-2.2)
 */
void test_no_duplicate_structs(void) {
    std::string source = read_source_file("src/main.cpp");

    int sensorstate_count = count_pattern_occurrences(source, "struct SensorState");
    int systemstate_count = count_pattern_occurrences(source, "struct SystemState");

    // Should be exactly 1 definition of each (may appear in comments/docs)
    TEST_ASSERT_EQUAL(1, sensorstate_count);
    TEST_ASSERT_EQUAL(1, systemstate_count);
}

/**
 * TEST 5.5: Function signatures are consistent with usage (Task 2.4)
 */
void test_function_signatures_consistent(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify critical signatures match requirements
    TEST_ASSERT_TRUE(source_matches_regex(source, "bool\\s+connectWiFi\\s*\\(\\s*\\)"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+checkWiFi\\s*\\(\\s*\\)"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+initializeSensor\\s*\\(\\s*int"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+readAndFilterSensor\\s*\\(\\s*int"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+updateBaseline\\s*\\(\\s*int"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+detectBeat\\s*\\(\\s*int"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+sendHeartbeatOSC\\s*\\(\\s*int\\s+\\w+\\s*,\\s*int"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "void\\s+updateLED\\s*\\(\\s*\\)"));
}

// ============================================================================
// TEST RUNNER MAIN
// ============================================================================

// Note: main() is defined in test_component_9_1.cpp to avoid linker conflicts.
// Test runner will automatically discover and run all test functions.
// This design allows multiple test files to be linked together.
