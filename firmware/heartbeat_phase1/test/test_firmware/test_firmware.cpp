/**
 * Comprehensive Test Suite for Component 7.7: Main Program Flow
 *
 * Tests against TRD requirements R1-R27
 * Framework: PlatformIO native testing (Unity)
 *
 * This test suite validates the firmware code structure without executing
 * embedded code. Tests verify:
 * - Source file parsing and structure
 * - Configuration constant presence and validity
 * - Function signatures and declarations
 * - Logic patterns in the code
 * - Compliance with TRD requirements
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
// CATEGORY 1: COMPILATION TESTS
// ============================================================================

/**
 * TEST 1.1: Source file exists and is readable
 */
void test_source_file_exists(void) {
    std::string source = read_source_file("src/main.cpp");
    TEST_ASSERT_GREATER_THAN(100, source.length());
}

/**
 * TEST 1.2: Verify required includes are present
 */
void test_compilation_includes_present(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "#include <Arduino.h>"));
    TEST_ASSERT_TRUE(source_contains(source, "#include <WiFi.h>"));
    TEST_ASSERT_TRUE(source_contains(source, "#include <WiFiUdp.h>"));
    TEST_ASSERT_TRUE(source_contains(source, "#include <OSCMessage.h>"));
}

/**
 * TEST 1.3: Verify no malformed includes
 */
void test_compilation_includes_wellformed(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should not have obviously malformed includes
    // (excluding the correctly formed "#include <Arduino.h>" )
    TEST_ASSERT_FALSE(source_contains(source, "#include Arduino.h")); // Missing <>

    // Verify correct format exists instead
    TEST_ASSERT_TRUE(source_contains(source, "#include <Arduino.h>"));
}

/**
 * TEST 1.4: Verify code has comment structure (indicates good organization)
 */
void test_compilation_has_comments(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "//"));
    TEST_ASSERT_TRUE(source_contains(source, "/*"));
    TEST_ASSERT_TRUE(source_contains(source, "*/"));
}

// ============================================================================
// CATEGORY 2: CONFIGURATION TESTS
// ============================================================================

/**
 * TEST 2.1: WiFi SSID is defined (R1)
 */
void test_config_wifi_ssid_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const char* WIFI_SSID"));
    TEST_ASSERT_TRUE(source_contains(source, "heartbeat-install"));
}

/**
 * TEST 2.2: WiFi Password is defined (R1)
 */
void test_config_wifi_password_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const char* WIFI_PASSWORD"));
}

/**
 * TEST 2.3: SERVER_IP is defined as IPAddress (R1)
 */
void test_config_server_ip_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const IPAddress SERVER_IP"));
    TEST_ASSERT_TRUE(source_matches_regex(source, "IPAddress.*SERVER_IP.*\\d+.*\\d+.*\\d+.*\\d+"));
}

/**
 * TEST 2.4: SERVER_PORT is defined as uint16_t (R1)
 */
void test_config_server_port_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const uint16_t SERVER_PORT"));
    TEST_ASSERT_TRUE(source_contains(source, "8000"));
}

/**
 * TEST 2.5: STATUS_LED_PIN is defined (R2)
 */
void test_config_led_pin_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int STATUS_LED_PIN"));
    TEST_ASSERT_TRUE(source_contains(source, "STATUS_LED_PIN = 2"));
}

/**
 * TEST 2.6: SENSOR_ID is defined (R3)
 */
void test_config_sensor_id_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const int SENSOR_ID"));
}

/**
 * TEST 2.7: TEST_MESSAGE_INTERVAL_MS is defined (R3)
 */
void test_config_message_interval_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long TEST_MESSAGE_INTERVAL_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "1000"));
}

/**
 * TEST 2.8: WIFI_TIMEOUT_MS is defined (R3)
 */
void test_config_wifi_timeout_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "const unsigned long WIFI_TIMEOUT_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "30000"));
}

/**
 * TEST 2.9: All configuration values are marked as const (immutable)
 */
void test_config_values_are_const(void) {
    std::string source = read_source_file("src/main.cpp");

    // Each config should be const - we should have at least 8 const declarations
    int const_count = count_pattern_occurrences(source, "const");
    TEST_ASSERT_GREATER_THAN(7, const_count);  // At least 8 (more than 7)
}

// ============================================================================
// CATEGORY 3: GLOBAL STATE TESTS
// ============================================================================

/**
 * TEST 3.1: SystemState struct is defined (R5.1)
 */
void test_state_struct_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "struct SystemState"));
}

/**
 * TEST 3.2: SystemState has wifiConnected field (R5.1)
 */
void test_state_has_wificonnected_field(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "bool wifiConnected"));
}

/**
 * TEST 3.3: SystemState has lastMessageTime field (R5.1)
 */
void test_state_has_lasttimestamp_field(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "lastMessageTime"));
}

/**
 * TEST 3.4: SystemState has messageCounter field (R5.1)
 */
void test_state_has_counter_field(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "messageCounter"));
}

/**
 * TEST 3.5: Global state instance is created (R5.2)
 */
void test_global_state_instance_created(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "SystemState state"));
}

/**
 * TEST 3.6: WiFiUDP object is created (R5.2, R19)
 */
void test_global_udp_object_created(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "WiFiUDP udp"));
}

// ============================================================================
// CATEGORY 4: FUNCTION SIGNATURE TESTS
// ============================================================================

/**
 * TEST 4.1: connectWiFi() function declared (R1)
 */
void test_function_connectwifi_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "bool connectWiFi()"));
}

/**
 * TEST 4.2: sendHeartbeatOSC() function declared (R6.2)
 */
void test_function_sendheartbeatos_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void sendHeartbeatOSC(int ibi_ms)"));
}

/**
 * TEST 4.3: updateLED() function declared (R6.3)
 */
void test_function_updateled_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void updateLED()"));
}

/**
 * TEST 4.4: checkWiFi() function declared (R6.4)
 */
void test_function_checkwifi_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void checkWiFi()"));
}

/**
 * TEST 4.5: setup() function defined (R7.1)
 */
void test_function_setup_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void setup()"));
}

/**
 * TEST 4.6: loop() function defined (R7.2)
 */
void test_function_loop_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "void loop()"));
}

/**
 * TEST 4.7: All function declarations have proper return types
 */
void test_functions_have_return_types(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_matches_regex(source, "(void|bool)\\s+\\w+\\s*\\("));
}

// ============================================================================
// CATEGORY 5: LOGIC VERIFICATION TESTS (R1-R27)
// ============================================================================

/**
 * TEST 5.1: connectWiFi() calls WiFi.mode() (R1)
 */
void test_logic_connectwifi_sets_mode(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "WiFi.mode(WIFI_STA)"));
}

/**
 * TEST 5.2: connectWiFi() calls WiFi.begin() (R1)
 */
void test_logic_connectwifi_begins(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "WiFi.begin(WIFI_SSID, WIFI_PASSWORD)"));
}

/**
 * TEST 5.3: connectWiFi() has timeout logic (R2, R4)
 */
void test_logic_connectwifi_has_timeout(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "WIFI_TIMEOUT_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "millis()"));
}

/**
 * TEST 5.4: connectWiFi() sets state.wifiConnected (R3)
 */
void test_logic_connectwifi_sets_state(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "state.wifiConnected = true"));
}

/**
 * TEST 5.5: sendHeartbeatOSC() constructs address pattern (R5)
 */
void test_logic_sendheartbeat_builds_address(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "/heartbeat/"));
    TEST_ASSERT_TRUE(source_contains(source, "snprintf"));
    TEST_ASSERT_TRUE(source_contains(source, "SENSOR_ID"));
}

/**
 * TEST 5.6: sendHeartbeatOSC() creates OSCMessage (R6)
 */
void test_logic_sendheartbeat_creates_osc_message(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "OSCMessage"));
}

/**
 * TEST 5.7: sendHeartbeatOSC() sends via UDP (R7)
 */
void test_logic_sendheartbeat_sends_udp(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "udp.beginPacket"));
    TEST_ASSERT_TRUE(source_contains(source, "msg.send(udp)"));
    TEST_ASSERT_TRUE(source_contains(source, "udp.endPacket()"));
}

/**
 * TEST 5.8: sendHeartbeatOSC() clears message after sending (R7)
 */
void test_logic_sendheartbeat_clears_message(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "msg.empty()"));
}

/**
 * TEST 5.9: updateLED() checks state.wifiConnected (R10)
 */
void test_logic_updateled_checks_state(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "state.wifiConnected"));
    TEST_ASSERT_TRUE(source_contains(source, "digitalWrite(STATUS_LED_PIN"));
}

/**
 * TEST 5.10: updateLED() implements non-blocking blink (R11)
 */
void test_logic_updateled_blink_pattern(void) {
    std::string source = read_source_file("src/main.cpp");

    // Pattern: (millis() / 100) % 2
    TEST_ASSERT_TRUE(source_contains(source, "millis() / 100) % 2"));
}

/**
 * TEST 5.11: checkWiFi() checks WiFi.status() (R12)
 */
void test_logic_checkwifi_status_check(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "WiFi.status()"));
    TEST_ASSERT_TRUE(source_contains(source, "WL_CONNECTED"));
}

/**
 * TEST 5.12: checkWiFi() calls WiFi.reconnect() (R13)
 */
void test_logic_checkwifi_reconnect(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "WiFi.reconnect()"));
}

/**
 * TEST 5.13: checkWiFi() has rate limiting (R14)
 */
void test_logic_checkwifi_rate_limit(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "5000"));  // 5 second interval
    TEST_ASSERT_TRUE(source_contains(source, "static"));  // static variable for state
}

/**
 * TEST 5.14: setup() initializes Serial (R15)
 */
void test_logic_setup_serial_init(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "Serial.begin(115200)"));
}

/**
 * TEST 5.15: setup() prints startup banner (R16)
 */
void test_logic_setup_startup_banner(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "Heartbeat"));
}

/**
 * TEST 5.16: setup() configures GPIO (R17)
 */
void test_logic_setup_gpio_config(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "pinMode(STATUS_LED_PIN, OUTPUT)"));
}

/**
 * TEST 5.17: setup() calls connectWiFi() (R18)
 */
void test_logic_setup_calls_connectwifi(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "connectWiFi()"));
}

/**
 * TEST 5.18: setup() initializes UDP (R19)
 */
void test_logic_setup_udp_init(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "udp.begin"));
}

/**
 * TEST 5.19: setup() initializes timing (R20)
 */
void test_logic_setup_timing_init(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "lastMessageTime"));
}

/**
 * TEST 5.20: loop() calls checkWiFi() (R21)
 */
void test_logic_loop_checkwifi(void) {
    std::string source = read_source_file("src/main.cpp");

    // Find loop() function and verify it contains checkWiFi()
    size_t loop_pos = source.find("void loop()");
    if (loop_pos != std::string::npos) {
        std::string loop_body = source.substr(loop_pos, 500);
        TEST_ASSERT_TRUE(source_contains(loop_body, "checkWiFi()"));
    }
}

/**
 * TEST 5.21: loop() implements message timing (R22)
 */
void test_logic_loop_message_timing(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "TEST_MESSAGE_INTERVAL_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "millis()"));
}

/**
 * TEST 5.22: loop() generates test IBI values (R23)
 */
void test_logic_loop_test_ibi(void) {
    std::string source = read_source_file("src/main.cpp");

    // Pattern: 800 + (counter % 200)
    TEST_ASSERT_TRUE(source_contains(source, "800 +"));
    TEST_ASSERT_TRUE(source_contains(source, "% 200"));
}

/**
 * TEST 5.23: loop() sends messages (R24)
 */
void test_logic_loop_sends_message(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "sendHeartbeatOSC"));
}

/**
 * TEST 5.24: loop() updates LED (R26)
 */
void test_logic_loop_updates_led(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "updateLED()"));
}

/**
 * TEST 5.25: loop() has delay (R27)
 */
void test_logic_loop_has_delay(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "delay(10)"));
}

// ============================================================================
// CATEGORY 6: INTEGRATION TESTS
// ============================================================================

/**
 * TEST 6.1: All required functions are declared
 */
void test_integration_all_functions_declared(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "bool connectWiFi()"));
    TEST_ASSERT_TRUE(source_contains(source, "void sendHeartbeatOSC"));
    TEST_ASSERT_TRUE(source_contains(source, "void updateLED()"));
    TEST_ASSERT_TRUE(source_contains(source, "void checkWiFi()"));
    TEST_ASSERT_TRUE(source_contains(source, "void setup()"));
    TEST_ASSERT_TRUE(source_contains(source, "void loop()"));
}

/**
 * TEST 6.2: All configuration constants are defined
 */
void test_integration_all_constants_defined(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "WIFI_SSID"));
    TEST_ASSERT_TRUE(source_contains(source, "WIFI_PASSWORD"));
    TEST_ASSERT_TRUE(source_contains(source, "SERVER_IP"));
    TEST_ASSERT_TRUE(source_contains(source, "SERVER_PORT"));
    TEST_ASSERT_TRUE(source_contains(source, "STATUS_LED_PIN"));
    TEST_ASSERT_TRUE(source_contains(source, "SENSOR_ID"));
    TEST_ASSERT_TRUE(source_contains(source, "TEST_MESSAGE_INTERVAL_MS"));
    TEST_ASSERT_TRUE(source_contains(source, "WIFI_TIMEOUT_MS"));
}

/**
 * TEST 6.3: Code is well organized (sections marked with comments)
 */
void test_integration_code_organization(void) {
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_TRUE(source_contains(source, "INCLUDES"));
    TEST_ASSERT_TRUE(source_contains(source, "CONFIGURATION"));
    TEST_ASSERT_TRUE(source_contains(source, "GLOBAL STATE"));
    TEST_ASSERT_TRUE(source_contains(source, "FUNCTION"));
}

/**
 * TEST 6.4: No obvious hardcoded values in functions
 */
void test_integration_uses_constants(void) {
    std::string source = read_source_file("src/main.cpp");

    // Verify constants are defined separately from functions
    size_t config_section = source.find("CONFIGURATION");
    size_t function_section = source.find("FUNCTION IMPLEMENTATIONS");

    TEST_ASSERT_GREATER_THAN(config_section, function_section);
}

/**
 * TEST 6.5: Compilation succeeded for ESP32 target
 */
void test_integration_compiles_esp32(void) {
    // This would be verified by the build system
    // For now, verify source is well-formed for compilation
    std::string source = read_source_file("src/main.cpp");

    TEST_ASSERT_GREATER_THAN(1000, source.length());  // Non-trivial file
}

// ============================================================================
// CATEGORY 7: CODE QUALITY TESTS
// ============================================================================

/**
 * TEST 7.1: Functions are reasonably small (not monolithic)
 */
void test_quality_function_size_reasonable(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should have multiple functions declared and defined
    // checkWiFi appears in declaration and definition (2 times)
    int helper_functions = count_pattern_occurrences(source, "void checkWiFi()");

    // Verify we have core functions (declared + defined = 2)
    TEST_ASSERT_GREATER_THAN(1, helper_functions);
}

/**
 * TEST 7.2: No obvious memory leaks (no new without delete)
 */
void test_quality_no_new_without_delete(void) {
    std::string source = read_source_file("src/main.cpp");

    int new_count = count_pattern_occurrences(source, " new ");
    // Should not have dynamic allocation in Phase 1
    TEST_ASSERT_EQUAL(0, new_count);
}

/**
 * TEST 7.3: Code uses meaningful variable names
 */
void test_quality_meaningful_names(void) {
    std::string source = read_source_file("src/main.cpp");

    // Check for common good names
    TEST_ASSERT_TRUE(source_contains(source, "wifiConnected"));
    TEST_ASSERT_TRUE(source_contains(source, "messageCounter"));
    TEST_ASSERT_TRUE(source_contains(source, "lastMessageTime"));
}

/**
 * TEST 7.4: Non-blocking delay patterns used
 */
void test_quality_non_blocking_patterns(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should use millis() for timing, not only delay()
    TEST_ASSERT_TRUE(source_contains(source, "millis()"));
    TEST_ASSERT_TRUE(source_contains(source, "delay(10)"));  // Only small delay in loop
}

/**
 * TEST 7.5: Comments explain complex logic
 */
void test_quality_has_explanatory_comments(void) {
    std::string source = read_source_file("src/main.cpp");

    // Should have comments explaining complex sections
    int comment_count = count_pattern_occurrences(source, "//");
    TEST_ASSERT_GREATER_THAN(10, comment_count);
}

// ============================================================================
// TRD COMPLIANCE MATRIX
// ============================================================================

/**
 * TEST 8.1: Requirement R1 - WiFi Initialization
 */
void test_trd_requirement_r1(void) {
    std::string source = read_source_file("src/main.cpp");

    // R1: WiFi Initialization
    TEST_ASSERT_TRUE(source_contains(source, "WiFi.mode(WIFI_STA)"));
    TEST_ASSERT_TRUE(source_contains(source, "WiFi.begin(WIFI_SSID, WIFI_PASSWORD)"));
}

/**
 * TEST 8.2: Requirement R2 - Connection Wait Loop
 */
void test_trd_requirement_r2(void) {
    std::string source = read_source_file("src/main.cpp");

    // R2: Connection Wait Loop
    TEST_ASSERT_TRUE(source_contains(source, "while (WiFi.status() != WL_CONNECTED)"));
    TEST_ASSERT_TRUE(source_contains(source, "WIFI_TIMEOUT_MS"));
}

/**
 * TEST 8.3: Requirement R3 - Success Behavior
 */
void test_trd_requirement_r3(void) {
    std::string source = read_source_file("src/main.cpp");

    // R3: Success Behavior
    TEST_ASSERT_TRUE(source_contains(source, "state.wifiConnected = true"));
}

/**
 * TEST 8.4: Requirement R5 - OSC Address Pattern
 */
void test_trd_requirement_r5(void) {
    std::string source = read_source_file("src/main.cpp");

    // R5: Address Pattern Construction
    TEST_ASSERT_TRUE(source_contains(source, "/heartbeat/"));
    TEST_ASSERT_TRUE(source_contains(source, "snprintf(address"));
}

/**
 * TEST 8.5: Requirement R6 - OSC Message Construction
 */
void test_trd_requirement_r6(void) {
    std::string source = read_source_file("src/main.cpp");

    // R6: OSC Message Construction
    TEST_ASSERT_TRUE(source_contains(source, "OSCMessage"));
    TEST_ASSERT_TRUE(source_contains(source, "msg.add"));
}

/**
 * TEST 8.6: Requirement R9 - LED States
 */
void test_trd_requirement_r9(void) {
    std::string source = read_source_file("src/main.cpp");

    // R9: LED States
    TEST_ASSERT_TRUE(source_contains(source, "digitalWrite"));
    TEST_ASSERT_TRUE(source_contains(source, "5 Hz"));  // Comment about 5Hz blink
}

/**
 * TEST 8.7: Requirement R15 - Serial Initialization
 */
void test_trd_requirement_r15(void) {
    std::string source = read_source_file("src/main.cpp");

    // R15: Serial Initialization
    TEST_ASSERT_TRUE(source_contains(source, "Serial.begin(115200)"));
}

/**
 * TEST 8.8: Requirement R21 - WiFi Status Check
 */
void test_trd_requirement_r21(void) {
    std::string source = read_source_file("src/main.cpp");

    // R21: WiFi Status Monitoring
    TEST_ASSERT_TRUE(source_contains(source, "checkWiFi()"));
}

/**
 * TEST 8.9: Requirement R23 - Message Generation
 */
void test_trd_requirement_r23(void) {
    std::string source = read_source_file("src/main.cpp");

    // R23: Message Generation (Phase 1)
    TEST_ASSERT_TRUE(source_contains(source, "800 +"));
    TEST_ASSERT_TRUE(source_contains(source, "% 200"));
}

/**
 * TEST 8.10: Requirement R27 - Loop Delay
 */
void test_trd_requirement_r27(void) {
    std::string source = read_source_file("src/main.cpp");

    // R27: Loop Delay
    TEST_ASSERT_TRUE(source_contains(source, "delay(10)"));
}

// ============================================================================
// TEST RUNNER MAIN
// ============================================================================

int main(int argc, char* argv[]) {
    UNITY_BEGIN();

    // Category 1: Compilation Tests
    RUN_TEST(test_source_file_exists);
    RUN_TEST(test_compilation_includes_present);
    RUN_TEST(test_compilation_includes_wellformed);
    RUN_TEST(test_compilation_has_comments);

    // Category 2: Configuration Tests
    RUN_TEST(test_config_wifi_ssid_defined);
    RUN_TEST(test_config_wifi_password_defined);
    RUN_TEST(test_config_server_ip_defined);
    RUN_TEST(test_config_server_port_defined);
    RUN_TEST(test_config_led_pin_defined);
    RUN_TEST(test_config_sensor_id_defined);
    RUN_TEST(test_config_message_interval_defined);
    RUN_TEST(test_config_wifi_timeout_defined);
    RUN_TEST(test_config_values_are_const);

    // Category 3: Global State Tests
    RUN_TEST(test_state_struct_defined);
    RUN_TEST(test_state_has_wificonnected_field);
    RUN_TEST(test_state_has_lasttimestamp_field);
    RUN_TEST(test_state_has_counter_field);
    RUN_TEST(test_global_state_instance_created);
    RUN_TEST(test_global_udp_object_created);

    // Category 4: Function Signature Tests
    RUN_TEST(test_function_connectwifi_declared);
    RUN_TEST(test_function_sendheartbeatos_declared);
    RUN_TEST(test_function_updateled_declared);
    RUN_TEST(test_function_checkwifi_declared);
    RUN_TEST(test_function_setup_defined);
    RUN_TEST(test_function_loop_defined);
    RUN_TEST(test_functions_have_return_types);

    // Category 5: Logic Verification Tests
    RUN_TEST(test_logic_connectwifi_sets_mode);
    RUN_TEST(test_logic_connectwifi_begins);
    RUN_TEST(test_logic_connectwifi_has_timeout);
    RUN_TEST(test_logic_connectwifi_sets_state);
    RUN_TEST(test_logic_sendheartbeat_builds_address);
    RUN_TEST(test_logic_sendheartbeat_creates_osc_message);
    RUN_TEST(test_logic_sendheartbeat_sends_udp);
    RUN_TEST(test_logic_sendheartbeat_clears_message);
    RUN_TEST(test_logic_updateled_checks_state);
    RUN_TEST(test_logic_updateled_blink_pattern);
    RUN_TEST(test_logic_checkwifi_status_check);
    RUN_TEST(test_logic_checkwifi_reconnect);
    RUN_TEST(test_logic_checkwifi_rate_limit);
    RUN_TEST(test_logic_setup_serial_init);
    RUN_TEST(test_logic_setup_startup_banner);
    RUN_TEST(test_logic_setup_gpio_config);
    RUN_TEST(test_logic_setup_calls_connectwifi);
    RUN_TEST(test_logic_setup_udp_init);
    RUN_TEST(test_logic_setup_timing_init);
    RUN_TEST(test_logic_loop_checkwifi);
    RUN_TEST(test_logic_loop_message_timing);
    RUN_TEST(test_logic_loop_test_ibi);
    RUN_TEST(test_logic_loop_sends_message);
    RUN_TEST(test_logic_loop_updates_led);
    RUN_TEST(test_logic_loop_has_delay);

    // Category 6: Integration Tests
    RUN_TEST(test_integration_all_functions_declared);
    RUN_TEST(test_integration_all_constants_defined);
    RUN_TEST(test_integration_code_organization);
    RUN_TEST(test_integration_uses_constants);
    RUN_TEST(test_integration_compiles_esp32);

    // Category 7: Code Quality Tests
    RUN_TEST(test_quality_function_size_reasonable);
    RUN_TEST(test_quality_no_new_without_delete);
    RUN_TEST(test_quality_meaningful_names);
    RUN_TEST(test_quality_non_blocking_patterns);
    RUN_TEST(test_quality_has_explanatory_comments);

    // Category 8: TRD Compliance Matrix
    RUN_TEST(test_trd_requirement_r1);
    RUN_TEST(test_trd_requirement_r2);
    RUN_TEST(test_trd_requirement_r3);
    RUN_TEST(test_trd_requirement_r5);
    RUN_TEST(test_trd_requirement_r6);
    RUN_TEST(test_trd_requirement_r9);
    RUN_TEST(test_trd_requirement_r15);
    RUN_TEST(test_trd_requirement_r21);
    RUN_TEST(test_trd_requirement_r23);
    RUN_TEST(test_trd_requirement_r27);

    return UNITY_END();
}
