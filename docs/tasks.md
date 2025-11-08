# Phase 1 Testing Infrastructure - Task Breakdown

Reference: `p1-tst-trd.md`

## Prerequisites

- [ ] **Task 0.1**: Verify Python 3.8+ installed
  - Run: `python3 --version`
  - Expected: Python 3.8.0 or higher

- [x] **Task 0.2**: Install python-osc package
  - Run: `pip3 install python-osc`
  - Verify: `python3 -c "from pythonosc import udp_client; print('OK')"`
  - Expected output: `OK`
  - **Status**: Completed - python-osc 1.9.3 installed

- [ ] **Task 0.3**: Verify UDP port 8000 available
  - Run: `netstat -an | grep 8000`
  - Expected: No output (port free)

## Component 1: Project Structure Setup

- [x] **Task 1.1**: Create testing directory structure
  - Create: `testing/` directory in project root
  - Create: `testing/README.md` with basic usage instructions
  - **Status**: Completed (pre-existing)

- [x] **Task 1.2**: Create requirements.txt
  - Create: `testing/requirements.txt`
  - Content: `python-osc>=1.8.0`
  - **Status**: Completed (pre-existing)

## Component 2: OSC Receiver

- [x] **Task 2.1**: Create osc_receiver.py skeleton
  - File: `testing/osc_receiver.py`
  - Imports: `pythonosc.osc_server`, `pythonosc.dispatcher`
  - Command-line args: `--port`, `--stats-interval`
  - Main function with argument parsing
  - **Status**: Completed - 233 lines, single-threaded architecture

- [x] **Task 2.2**: Implement message reception (R7)
  - Create OSC server listening on configurable port (default 8000)
  - Bind to 0.0.0.0 (all interfaces)
  - Create dispatcher for `/heartbeat/*` pattern
  - **Status**: Completed - BlockingOSCUDPServer on 0.0.0.0:8000 (R19 single-threaded)

- [x] **Task 2.3**: Implement message validation (R8)
  - Validate address pattern matches `/heartbeat/[0-3]`
  - Validate sensor ID in range 0-3
  - Validate IBI in range 300-3000ms
  - Print warnings for invalid messages
  - **Status**: Completed - includes type validation, precompiled regex

- [x] **Task 2.4**: Implement statistics tracking (R9)
  - Track total messages received
  - Track valid vs invalid counts
  - Track per-sensor counters (array of 4)
  - Track per-sensor IBI values for averaging
  - Calculate average BPM per sensor: `MS_PER_MINUTE / avg_ibi`
  - **Status**: Completed - single-threaded (no locking needed)

- [x] **Task 2.5**: Implement console output (R10)
  - Print each valid message: `[/heartbeat/N] IBI: VALUE ms, BPM: VALUE`
  - Print warnings for invalid messages
  - Periodic statistics every 10 seconds (configurable)
  - **Status**: Completed - time-checked in message handler (prints when messages arrive)

- [x] **Task 2.6**: Implement signal handling (R13)
  - Handle KeyboardInterrupt (Ctrl+C)
  - Print final statistics on exit
  - Print parseable final line: `RECEIVER_FINAL_STATS: total=NNN, valid=NNN, ...`
  - **Status**: Completed - graceful shutdown, smart blank line handling

- [x] **Task 2.7**: Test receiver manually
  - Start receiver: `python3 testing/osc_receiver.py`
  - Verify startup message printed
  - Test with netcat or manual UDP send (optional)
  - Verify Ctrl+C works and prints statistics
  - **Status**: Completed - startup tested, validation logic verified

**Component 2 Notes**:
- Refactored to single-threaded event loop per TRD R19 requirement
- Fixed bugs identified during code review:
  - Added type validation to prevent TypeError crashes
  - Precompiled regex pattern for performance
  - Fixed timing drift (advance by interval not current time)
  - Smart blank line handling in shutdown
  - MS_PER_MINUTE constant eliminates magic numbers
- Architecture: BlockingOSCUDPServer, no threading, no locking
- Stats print when interval elapsed AND message arrives (acceptable tradeoff)
- All requirements R7-R13 implemented and tested
- Ready for integration with ESP32 simulator (Component 3)

## Component 3: ESP32 Simulator

- [x] **Task 3.1**: Create esp32_simulator.py skeleton
  - File: `testing/esp32_simulator.py`
  - Imports: `pythonosc.udp_client`, `threading`, `time`, `random`
  - Command-line args: `--sensors`, `--bpm`, `--server`, `--port`
  - Main function with argument parsing
  - **Status**: Completed - 324 lines, full implementation with all requirements

- [x] **Task 3.2**: Implement BPM-to-IBI conversion (R2)
  - Function: Calculate base IBI from BPM: `60000 / bpm`
  - Add variance: `random.uniform(-0.05, 0.05) * base_ibi`
  - Clamp to valid range: 300-3000ms
  - **Status**: Completed - calculate_base_ibi(), generate_ibi_with_variance(), clamp_ibi(), calculate_ibi()

- [x] **Task 3.3**: Implement OSC message construction (R3)
  - Create OSC client for target IP:port
  - Build message with address: `/heartbeat/N`
  - Add int32 argument: IBI value
  - **Status**: Completed - SimpleUDPClient with send_message() in sensor_thread()

- [x] **Task 3.4**: Implement single sensor thread (R1, R4)
  - Create sensor thread class/function
  - Loop: Generate IBI, send message, sleep for IBI duration
  - Track message count per sensor
  - Handle thread-safe counter increment
  - **Status**: Completed - sensor_thread() function with shutdown_event and print_lock

- [x] **Task 3.5**: Implement multi-sensor support (R1)
  - Create N threads (1-4) based on `--sensors` argument
  - Each thread operates independently
  - Parse comma-separated BPM values
  - Assign unique sensor ID (0-3) to each thread
  - **Status**: Completed - main() creates threads in loop (lines 287-297)

- [x] **Task 3.6**: Implement console output (R6)
  - Print each message sent: `[Sensor N] Sent /heartbeat/N IBI_VALUE (#COUNT)`
  - Use thread-safe printing
  - Track message count per sensor
  - **Status**: Completed - print_message() with print_lock, sensor_message_counts[] tracking

- [x] **Task 3.7**: Implement signal handling and statistics (R6)
  - Handle KeyboardInterrupt (Ctrl+C)
  - Stop all threads gracefully
  - Print final statistics: `SIMULATOR_FINAL_STATS: sensor_0=N, sensor_1=N, ...`
  - **Status**: Completed - try/except KeyboardInterrupt in main(), shutdown_event, format_final_statistics()

- [x] **Task 3.8**: Test simulator manually
  - Start receiver in terminal 1
  - Start simulator in terminal 2: `python3 testing/esp32_simulator.py --sensors 1 --bpm 60`
  - Verify messages appear in receiver
  - Test with 4 sensors: `--sensors 4 --bpm 60,72,58,80`
  - Verify Ctrl+C works on both
  - **Status**: Completed - verified with receiver, all sensors working, graceful shutdown confirmed

**Component 3 Notes**:
- All requirements R1-R6 implemented
- Input validation includes sensor count (1-4), BPM range (20-200), BPM count match
- IBI calculation uses variance (±5%) with clamping to 300-3000ms
- Thread-safe output using print_lock, daemon threads with graceful shutdown
- Final statistics format: `SIMULATOR_FINAL_STATS: sensor_0=N, sensor_1=N, sensor_2=N, sensor_3=N, total=N`
- Tested with single sensor and 4 sensors at different BPM rates
- Ready for integration test with receiver (Component 5)

## Component 4: Unit Tests

- [x] **Task 4.1**: Create test_osc_protocol.py skeleton
  - File: `testing/test_osc_protocol.py`
  - Import: `unittest`, `pythonosc`
  - Create test class inheriting from `unittest.TestCase`
  - **Status**: Completed - TestOSCProtocol class with 8 test methods

- [x] **Task 4.2**: Implement address pattern tests (R14)
  - Test valid patterns: `/heartbeat/0`, `/heartbeat/1`, `/heartbeat/2`, `/heartbeat/3`
  - Test invalid patterns rejected
  - Verify exact string match
  - **Status**: Completed - test_message_address_format tests all 4 sensor IDs

- [x] **Task 4.3**: Implement argument type tests (R14)
  - Test argument is int32 type
  - Test message binary encoding (24 bytes)
  - Verify null padding
  - **Status**: Completed - test_message_argument_type, test_message_encoding, test_message_null_padding
  - Explicitly verifies both address and type tag null padding

- [x] **Task 4.4**: Implement data validation tests (R15)
  - Test IBI range validation (300-3000)
  - Test values outside range rejected
  - Test sensor ID range (0-3)
  - Test sensor IDs outside range rejected
  - **Status**: Completed - test_ibi_range_validation and test_sensor_id_range with boundary cases

- [x] **Task 4.5**: Implement BPM calculation tests (R16)
  - Test: 1000ms → 60.0 BPM
  - Test: 857ms → 70.0 BPM (±0.5)
  - Test: 750ms → 80.0 BPM
  - Test: 600ms → 100.0 BPM
  - **Status**: Completed - test_bpm_calculation tests receiver's actual implementation

- [x] **Task 4.6**: Implement variance tests (R17)
  - Generate 100 IBI values with variance
  - Verify not all identical
  - Verify within ±5% of base value
  - **Status**: Completed - test_ibi_variance generates 100 samples with helper function

- [x] **Task 4.7**: Add test runner
  - Add `if __name__ == '__main__': unittest.main()`
  - Run: `python3 testing/test_osc_protocol.py`
  - Verify all tests pass
  - **Status**: Completed - all 8 tests pass in 0.001s

**Component 4 Notes**:
- Comprehensive test coverage with 8 tests covering R14-R18
- Code review identified and fixed critical issues:
  - Added explicit address null padding verification (R14)
  - Changed BPM test to validate receiver implementation (not just formula)
- Tests verify both message construction (pythonosc) and validation (receiver)
- All tests pass with proper exit codes (0 on success)
- Execution time well under 5-second requirement (0.001s)
- Ready for integration with Component 3 (ESP32 Simulator) when available

## Component 5: Integration Test

- [ ] **Task 5.1**: Create test_integration.py skeleton
  - File: `testing/test_integration.py`
  - Imports: `subprocess`, `time`, `signal`, `re`
  - Main function for test orchestration

- [ ] **Task 5.2**: Implement receiver process management (R20)
  - Start receiver with `subprocess.Popen()`
  - Capture stdout
  - Wait for "OSC Receiver listening" message (5 sec timeout)
  - Fail test if receiver doesn't start

- [ ] **Task 5.3**: Implement simulator process management (R20)
  - Start simulator with 4 sensors
  - Configure: `--sensors 4 --bpm 60,72,58,80`
  - Capture stdout
  - Run for 10 seconds

- [ ] **Task 5.4**: Implement process shutdown (R20, R24)
  - Send SIGINT to simulator
  - Wait for `SIMULATOR_FINAL_STATS:` line
  - Send SIGINT to receiver
  - Wait for `RECEIVER_FINAL_STATS:` line
  - Force kill with SIGKILL if timeout (5 seconds)

- [ ] **Task 5.5**: Implement statistics parsing (R21)
  - Parse simulator final stats line
  - Parse receiver final stats line
  - Extract: total, valid, invalid, per-sensor counts
  - Use regex or string split

- [ ] **Task 5.6**: Implement validation checks (R22)
  - Verify all 4 sensors sent messages (sensor_N > 0)
  - Verify invalid=0
  - Verify message rate 3.5-4.5 msg/sec
  - Verify message loss < 10%
  - Print pass/fail summary

- [ ] **Task 5.7**: Test integration test
  - Run: `python3 testing/test_integration.py`
  - Verify test completes successfully
  - Verify all checks pass
  - Verify processes cleaned up

## Component 6: Documentation

- [ ] **Task 6.1**: Create testing/README.md
  - Document installation steps
  - Document how to run each component
  - Document expected output
  - Document troubleshooting common issues

- [ ] **Task 6.2**: Add usage examples
  - Example: Single sensor test
  - Example: Multi-sensor test
  - Example: Running full test suite
  - Example: Integration test

## Validation & Acceptance

- [ ] **Task 7.1**: Run complete test sequence
  - Run unit tests: All pass
  - Run manual receiver+simulator test: 30 seconds, no errors
  - Run multi-sensor test: 4 sensors, 30 seconds, all active
  - Run integration test: Passes all checks

- [ ] **Task 7.2**: Verify acceptance criteria from TRD
  - Unit tests pass in < 5 seconds
  - Simulator runs 60+ seconds without crashes
  - Receiver runs 60+ seconds without crashes
  - Message loss < 1% over 60 seconds
  - BPM accuracy within ±2 BPM

- [ ] **Task 7.3**: Document completion
  - Update this file with completion status
  - Note any deviations from TRD
  - Document any issues encountered
  - Mark Phase 1 testing infrastructure complete

---

## Task Execution Notes

**Order**: Tasks should be completed in sequence within each component. Components 2 and 3 can be done in parallel, but both must be complete before Component 5 (integration test).

**Testing**: Test each component after completion before moving to next component.

**Acceptance**: Each task complete when code works and meets requirements referenced in parentheses (e.g., R7 = Requirement 7 from p1-tst-trd.md).

**Time Estimate**:
- Prerequisites: 10 min
- Component 1: 10 min
- Component 2: 45-60 min
- Component 3: 45-60 min
- Component 4: 30-45 min
- Component 5: 30-45 min
- Component 6: 20 min
- Validation: 30 min
- **Total: 3.5-4.5 hours**
