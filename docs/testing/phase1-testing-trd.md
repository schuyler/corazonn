# Heartbeat Firmware - Phase 1 Testing Infrastructure TRD
## OSC Protocol Simulation & Validation

**Version:** 2.0  
**Date:** 2025-11-08  
**Purpose:** Define requirements for OSC protocol testing environment (no hardware)  
**Audience:** Coding agent implementing simulation and validation tools

**⚠️ CRITICAL: IMPLEMENTATION ORDER**
```
Step 1: Complete this document (testing infrastructure)
Step 2: Validate testing infrastructure (all tests pass)
Step 3: Then proceed to heartbeat-phase1-firmware-implementation-trd.md
```
This testing infrastructure MUST be complete and working before implementing firmware.

**Estimated Implementation Time:** 2-4 hours

---

## 1. Objective

Create simulation environment to validate OSC messaging protocol before ESP32 hardware arrives. All code runs on development machine (Linux/Mac/Windows).

**Deliverables:**
1. ESP32 simulator - sends OSC messages mimicking hardware behavior
2. OSC receiver - validates message format and tracks statistics  
3. Automated test suite - validates protocol correctness
4. Integration test - end-to-end validation

**Success Criteria:**
- Simulator generates valid OSC messages at realistic rates
- Receiver validates message format and content
- All automated tests pass
- Integration test runs for 60 seconds without errors

---

## 2. OSC Protocol Specification

### 2.1 Message Format

**Address Pattern:**
```
/heartbeat/N
```
Where N is sensor ID: 0, 1, 2, or 3

**Type Tag:**
```
,i
```
Single int32 argument

**Argument:**
```
Inter-beat interval (IBI) in milliseconds
Valid range: 300 to 3000 (inclusive)
```

**Complete Message Example:**
```
/heartbeat/0 847
```
Meaning: Sensor 0 detected heartbeat, 847ms since previous beat

### 2.2 Binary Encoding

OSC messages must conform to OSC 1.0 specification:

**Structure:**
1. Address string (null-terminated, padded to multiple of 4 bytes)
2. Type tag string (comma prefix, null-terminated, padded to multiple of 4)
3. Arguments (4 bytes per int32, big-endian)

**Example Binary Layout:** (24 bytes total for `/heartbeat/0 847`)
```
Offset  Hex                                         ASCII
------  ------------------------------------------  ---------------
0x00    2F 68 65 61 72 74 62 65 61 74 2F 30 00 00  /heartbeat/0..
0x10    00 00 2C 69 00 00 00 00 03 4F              ..,i.....O
```

**Validation Requirements:**
- Address string exactly matches pattern `/heartbeat/[0-3]`
- Type tag is exactly `,i\0\0` (4 bytes)
- Argument is 4-byte signed integer, big-endian
- Total message size is 24 bytes

### 2.3 Network Protocol

**Transport:** UDP (User Datagram Protocol)

**Addressing:**
- Server (receiver) listens on: `0.0.0.0:8000` (all interfaces, port 8000)
- Client (simulator) sends from: ephemeral source port

**⚠️ CRITICAL - Phase 1 Configuration:**
For Phase 1 testing, simulator and receiver MUST run on same machine:
- Simulator sends to: `127.0.0.1:8000` (localhost)
- Receiver listens on: `0.0.0.0:8000` (accepts from any interface)

Future phases will use network address `192.168.50.100` for ESP32 hardware.

**Reliability:** 
- No acknowledgment required (fire-and-forget)
- No retransmission on packet loss
- Messages are independent (no sequence numbers)

**Configuration:**
- Server IP: `127.0.0.1` (localhost for Phase 1)
- Server Port: `8000` (configurable via command-line)
- Protocol: IPv4 UDP

---

## 3. Component Specifications

### 3.1 ESP32 Simulator

**Purpose:** Simulate 1-4 ESP32 sensor units sending heartbeat messages

**Requirements:**

**R1: Multi-Sensor Support**
- MUST support simulating 1 to 4 sensors simultaneously
- Each sensor MUST have unique ID (0-3)
- Sensors MUST operate independently (separate threads/processes)

**R2: Heartbeat Generation**
- MUST generate IBI values based on target BPM
- MUST add realistic variance using uniform random distribution
- Variance calculation: `variance = random.uniform(-0.05, 0.05) * base_ibi`
- This creates ±5% variation around base value (mimics natural heart rate variability)
- MUST clamp IBI to valid range (300-3000ms)
- IBI calculation: `base_ibi = 60000 / target_bpm`

**R3: Message Transmission**
- MUST send OSC message for each simulated heartbeat
- MUST use correct address pattern `/heartbeat/N`
- MUST include IBI as int32 argument
- MUST send to configurable IP:port

**R4: Timing Accuracy**
- MUST sleep for IBI duration between messages (simulates real heartbeat timing)
- Message rate SHOULD match configured BPM (±5%)
- Example: 60 BPM = ~1 message per second per sensor

**R5: Configuration**
- MUST accept command-line arguments:
  - `--sensors N` (number of sensors, 1-4)
  - `--bpm CSV` (comma-separated BPM values, one per sensor)
  - `--server IP` (destination IP, default 127.0.0.1)
  - `--port N` (destination port, default 8000)

**R6: Output & Monitoring**
- MUST print each message sent to stdout
- Format: `[Sensor N] Sent /heartbeat/N IBI_VALUE (#COUNT)`
- MUST track and report message count per sensor
- MUST handle Ctrl+C gracefully using KeyboardInterrupt exception
- On shutdown: MUST print final statistics in parseable format

**Final Statistics Format (for integration test parsing):**
```
SIMULATOR_FINAL_STATS: sensor_0=N, sensor_1=N, sensor_2=N, sensor_3=N, total=N
```
Where N is the message count for each sensor.

**Example Usage:**
```bash
# Single sensor at 60 BPM
simulator --sensors 1 --bpm 60

# Four sensors at different rates  
simulator --sensors 4 --bpm 60,72,58,80

# Send to remote server
simulator --sensors 4 --bpm 65,70,75,80 --server 192.168.50.100
```

**BPM-to-IBI Examples:**
- 40 BPM → 1500ms IBI
- 60 BPM → 1000ms IBI  
- 75 BPM → 800ms IBI
- 100 BPM → 600ms IBI
- 120 BPM → 500ms IBI

### 3.2 OSC Receiver

**Purpose:** Receive and validate OSC heartbeat messages

**Requirements:**

**R7: Message Reception**
- MUST listen on UDP port 8000 (configurable)
- MUST accept messages from any source IP
- MUST parse OSC messages using OSC 1.0 specification

**R8: Validation**
- MUST validate address pattern matches `/heartbeat/[0-3]`
- MUST validate sensor ID is in range 0-3
- MUST validate IBI is in range 300-3000ms
- MUST reject malformed messages with error output

**R9: Statistics Tracking**
- MUST track total messages received
- MUST track valid vs invalid message count
- MUST track messages per sensor (array of 4 counters)
- MUST calculate average IBI per sensor
- MUST calculate average BPM per sensor: `bpm = 60000 / avg_ibi`

**R10: Output**
- MUST print each valid message to stdout
- Format: `[/heartbeat/N] IBI: VALUE ms, BPM: VALUE`
- MUST print warnings for invalid messages
- MUST print statistics periodically (every 10 seconds)

**R11: Statistics Report Format**
```
==================================================
STATISTICS
==================================================
Runtime: XX.Xs
Total messages: NNN
Valid: NNN
Invalid: NNN
Message rate: N.NN msg/sec

Sensor 0: NNN msgs, avg XXXms IBI (XX.X BPM)
Sensor 1: NNN msgs, avg XXXms IBI (XX.X BPM)
Sensor 2: NNN msgs, avg XXXms IBI (XX.X BPM)
Sensor 3: NNN msgs, avg XXXms IBI (XX.X BPM)
==================================================
```

**R11b: Shutdown Statistics (for integration test parsing)**
On KeyboardInterrupt, MUST print parseable final line:
```
RECEIVER_FINAL_STATS: total=NNN, valid=NNN, invalid=NNN, sensor_0=NNN, sensor_1=NNN, sensor_2=NNN, sensor_3=NNN
```

**R12: Configuration**
- MUST accept command-line arguments:
  - `--port N` (listen port, default 8000)
  - `--stats-interval N` (seconds between statistics, default 10)

**R13: Signal Handling**
- MUST handle KeyboardInterrupt exception (Ctrl+C)
- MUST print final statistics before exiting
- MUST use try/except KeyboardInterrupt pattern in main()

### 3.3 Test Suite

**Purpose:** Automated validation of OSC protocol implementation

**Requirements:**

**R14: Protocol Format Tests**
- MUST verify address pattern format for all sensor IDs (0-3)
- MUST verify argument is int32 type
- MUST verify message binary encoding (24 bytes)
- MUST verify null padding in address and type tag strings

**R15: Data Validation Tests**
- MUST verify IBI values in valid range (300-3000)
- MUST reject IBI values outside range
- MUST verify sensor IDs in valid range (0-3)
- MUST reject sensor IDs outside range

**R16: BPM Calculation Tests**
- MUST verify BPM calculation: `bpm = 60000 / ibi`
- Test cases (exact or within 0.5 BPM):
  - 1000ms → 60.0 BPM
  - 857ms → 70.0 BPM
  - 750ms → 80.0 BPM
  - 600ms → 100.0 BPM

**R17: Variance Tests**
- MUST verify generated IBI values have variance
- Generated IBIs MUST NOT all be identical
- Variance SHOULD be ±5% of base value (verified over 100+ samples)

**R18: Test Execution**
- Tests MUST run via single command
- ALL tests MUST pass for success
- MUST report pass/fail for each test
- Exit code 0 on success, non-zero on failure

**Example Test Output:**
```
test_message_address_format ... ok
test_message_argument_type ... ok
test_ibi_range_validation ... ok
test_sensor_id_range ... ok
test_message_encoding ... ok
test_bpm_calculation ... ok
test_message_size ... ok
test_ibi_variance ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.123s

OK
```

### 3.4 Integration Test

**Purpose:** End-to-end validation of simulator → receiver communication

**Requirements:**

**R19: Concurrency Model**
- MUST use Python `threading` module (not multiprocessing)
- Simulator: One thread per sensor
- Receiver: Single-threaded event loop
- Reason: Threads share signal handlers, simplifies Ctrl+C handling

**R20: Test Procedure**
1. Start receiver process using `subprocess.Popen()`
2. Wait for receiver startup confirmation
3. Monitor receiver stdout for "OSC Receiver listening" message
4. Wait up to 5 seconds for confirmation, fail if timeout
5. Start simulator (4 sensors at 60, 72, 58, 80 BPM)
6. Run for 10 seconds
7. Send SIGINT (Ctrl+C) to simulator
8. Wait for simulator to print `SIMULATOR_FINAL_STATS:` line
9. Send SIGINT to receiver
10. Wait for receiver to print `RECEIVER_FINAL_STATS:` line
11. Parse both statistics lines and validate

**R21: Statistics Extraction**
- MUST capture stdout from both processes
- MUST parse final statistics lines using regex or string split
- Format: `KEY=value, KEY=value, ...`
- Extract counters: simulator totals, receiver totals, per-sensor counts

**R22: Success Criteria**
- All 4 sensors MUST send messages (sensor_N > 0 for N=0,1,2,3)
- Receiver MUST show invalid=0 (no invalid messages)
- Total message rate SHOULD be 3.5-4.5 msg/sec (4 sensors × ~1 Hz each)
- Message loss SHOULD be < 10% (receiver_total ≥ 0.9 × simulator_total)
  - Note: UDP may drop packets, 10% loss acceptable for test

**R23: Test Execution**
- MUST run via single command
- MUST automatically start/stop processes
- MUST timeout after 30 seconds if hung
- MUST report pass/fail with summary

**R24: Error Handling**
- If receiver fails to start: Print stderr, fail test
- If simulator fails to start: Stop receiver, print stderr, fail test
- If processes don't stop within 5 seconds: Force kill with SIGKILL

**Example Output:**
```
============================================================
INTEGRATION TEST: Simulator → Receiver
============================================================

[1/4] Starting receiver...
      Receiver started (PID 12345)

[2/4] Starting simulator (4 sensors, 10 seconds)...
      Simulator started (PID 12346)

[3/4] Running test for 10 seconds...

[4/4] Stopping processes...

============================================================
TEST COMPLETE
============================================================

Results:
  ✓ All 4 sensors sent messages
  ✓ 0 invalid messages
  ✓ Message rate: 4.1 msg/sec
  ✓ BPM accuracy within ±2 BPM
```

---

## 4. Validation Requirements

### 4.1 Unit Test Acceptance Criteria

**Test Suite MUST:**
- ✅ Run without errors
- ✅ Pass all 8+ tests
- ✅ Complete in < 5 seconds
- ✅ Exit code 0 on success

### 4.2 Simulator Acceptance Criteria

**Simulator MUST:**
- ✅ Start without errors
- ✅ Send messages at correct rate (±10% of expected)
- ✅ Generate valid OSC messages (passes receiver validation)
- ✅ Support 1-4 sensors simultaneously
- ✅ Respond to Ctrl+C (graceful shutdown)
- ✅ Run for 60+ seconds without crashes

### 4.3 Receiver Acceptance Criteria

**Receiver MUST:**
- ✅ Start without errors
- ✅ Receive messages from simulator
- ✅ Validate message format correctly
- ✅ Calculate BPM accurately (±0.5 BPM)
- ✅ Track statistics for all sensors
- ✅ Run for 60+ seconds without crashes

### 4.4 Integration Test Acceptance Criteria

**Integration Test MUST:**
- ✅ Complete without errors
- ✅ All processes start successfully
- ✅ Message flow confirmed (simulator → receiver)
- ✅ No invalid messages reported
- ✅ Message rate within expected range (3.5-4.5 msg/sec for 4 sensors)
- ✅ All processes stop cleanly

---

## 5. Performance Requirements

### 5.1 Latency

**Requirement:** Message latency < 10ms
- Definition: Time from simulator send() to receiver handler() called
- Measurement: Log timestamps at send and receive
- Acceptable: 0-10ms on localhost
- Warning: 10-50ms (acceptable but investigate)
- Failure: >50ms (indicates network or processing issue)

### 5.2 Message Rate

**Per Sensor:**
- 40 BPM: ~0.67 msg/sec
- 60 BPM: ~1.0 msg/sec
- 80 BPM: ~1.33 msg/sec
- 100 BPM: ~1.67 msg/sec

**Total (4 Sensors):**
- All at 60 BPM: ~4 msg/sec
- Mixed rates: 3-6 msg/sec typical

**Tolerance:** ±10% of expected rate

### 5.3 Reliability

**Message Loss:**
- Acceptable: < 1% loss over 60 second test
- Measurement: Compare simulator send count to receiver count
- Note: UDP may drop packets, especially on congested networks

**Stability:**
- MUST run for 60 seconds without crashes
- MUST handle 1000+ messages without memory leaks
- MUST maintain consistent performance (no degradation over time)

---

## 6. Error Handling Requirements

### 6.1 Invalid Input Handling

**Simulator MUST handle:**
- Invalid sensor count (< 1 or > 4): Error message, exit
- Invalid BPM values (< 20 or > 200): Error message, exit
- Unreachable server: Continue sending, log errors
- Invalid IP address: Error message, exit

**Receiver MUST handle:**
- Port already in use: Error message, exit
- Invalid OSC messages: Log warning, continue
- Out-of-range IBI: Log warning, count as invalid, continue
- Out-of-range sensor ID: Log warning, count as invalid, continue

### 6.2 Error Messages

**Format:**
```
ERROR: <component>: <description>
```

**Examples:**
```
ERROR: Simulator: Invalid sensor count: 5 (must be 1-4)
ERROR: Receiver: Port 8000 already in use
WARNING: Receiver: IBI out of range: 5000ms (sensor 2)
```

---

## 7. Dependencies

### 7.1 Required Software

**Python:** Version 3.8 or higher

**Python Packages:**
- `python-osc` (OSC message parsing and construction)

**⚠️ CRITICAL - Package Name vs Import Name:**
- **PyPI package name:** `python-osc` (used in pip install)
- **Python import name:** `pythonosc` (used in code)
- This is intentional - do not install package named "pythonosc"

**Installation:**
```bash
pip3 install python-osc
```

**Verification:**
```bash
python3 -c "from pythonosc import udp_client, osc_server; print('OK')"
```
Expected output: `OK`

If you see `ModuleNotFoundError: No module named 'pythonosc'`, the package was not installed correctly.

**Optional: Virtual Environment (recommended)**
```bash
python3 -m venv heartbeat-env
source heartbeat-env/bin/activate  # Linux/Mac
# OR
heartbeat-env\Scripts\activate  # Windows

pip3 install python-osc
```

### 7.2 Operating System

**Supported:**
- Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)
- macOS 10.15+ (Catalina or newer)
- Windows 10/11 (via native Python or WSL2)

**Network Requirements:**
- UDP port 8000 available (or configurable alternative)
- Loopback interface functional (127.0.0.1)
- No firewall blocking UDP on test port

**Platform-Specific Notes:**
- **Linux:** Commands shown use Linux syntax (e.g., `tcpdump -i lo`)
- **macOS:** Use `lo0` instead of `lo` for loopback interface
- **Windows:** Some debugging commands may differ or require alternatives

---

## 8. Testing Procedure

### 8.1 Prerequisite Verification

```bash
# 1. Check Python version
python3 --version
# Expected: Python 3.8.0 or higher

# 2. Install dependencies
pip3 install python-osc

# 3. Verify installation
python3 -c "from pythonosc import udp_client; print('OK')"
# Expected: OK

# 4. Check port availability
netstat -an | grep 8000
# Expected: No output (port free)
```

### 8.2 Test Execution Sequence

**Step 1: Unit Tests**
```bash
python3 test_osc_protocol.py
```
Expected: All tests pass, exit code 0

**Step 2: Manual Receiver Test**
```bash
# Terminal 1: Start receiver
python3 osc_receiver.py --port 8000

# Terminal 2: Start simulator
python3 esp32_simulator.py --sensors 1 --bpm 60

# Expected: Receiver shows ~1 msg/sec from sensor 0
# Run for 30 seconds, then Ctrl+C both
```

**Step 3: Multi-Sensor Test**
```bash
# Terminal 1: Start receiver
python3 osc_receiver.py --port 8000

# Terminal 2: Start 4-sensor simulator
python3 esp32_simulator.py --sensors 4 --bpm 60,72,58,80

# Expected: Receiver shows ~4 msg/sec from sensors 0-3
# Run for 30 seconds, verify all 4 sensors active
```

**Step 4: Integration Test**
```bash
python3 test_integration.py
```
Expected: Test completes successfully, all checks pass

### 8.3 Validation Checklist

After completing test sequence:

**Unit Tests:**
- [ ] All tests pass
- [ ] No errors or warnings
- [ ] Execution time < 5 seconds

**Simulator:**
- [ ] Starts without errors
- [ ] Sends messages at correct rate
- [ ] All 4 sensors work independently
- [ ] Graceful shutdown on Ctrl+C
- [ ] Statistics printed on exit

**Receiver:**
- [ ] Starts without errors
- [ ] Receives messages from all sensors
- [ ] 0 invalid messages (when simulator working correctly)
- [ ] BPM calculations accurate (±0.5 BPM)
- [ ] Statistics printed every 10 seconds

**Integration:**
- [ ] Test runs to completion
- [ ] All processes start/stop cleanly
- [ ] Message flow confirmed
- [ ] No errors or warnings

---

## 9. Troubleshooting Guide

### 9.1 Common Issues

**Issue: "Module not found: pythonosc"**
- Cause: python-osc package not installed
- Note: Package name is `python-osc`, import name is `pythonosc` (this is correct)
- Solution: `pip3 install python-osc`
- Verify: `python3 -c "import pythonosc; print('OK')"`

**Issue: "Address already in use"**
- Cause: Port 8000 already bound to another process
- Solution Option 1: Use different port: `--port 8001`
- Solution Option 2 (Linux/Mac): Find and kill process:
  ```bash
  # Linux/Mac
  lsof -ti:8000 | xargs kill
  
  # Or check what's using it:
  lsof -i:8000
  ```
- Solution Option 3 (Windows):
  ```cmd
  netstat -ano | findstr :8000
  taskkill /PID <pid> /F
  ```

**Issue: "No messages received"**
- Causes:
  1. Firewall blocking UDP port
  2. Simulator sending to wrong IP/port
  3. Receiver on different interface
  4. Simulator and receiver using different ports
- Solutions:
  1. Linux: `sudo ufw allow 8000/udp`
     macOS: System Preferences → Security & Privacy → Firewall
     Windows: Windows Defender Firewall → Advanced settings
  2. Verify simulator `--server 127.0.0.1` matches receiver IP
  3. Receiver uses `0.0.0.0` to listen on all interfaces
  4. Both must use same port number (default 8000)

**Issue: "Messages delayed or lost"**
- Cause: Network congestion or CPU overload
- Solutions:
  1. Close other network applications
  2. Reduce sensor count: `--sensors 2`
  3. Monitor CPU usage (see debugging section)
  4. UDP packet loss is normal - up to 10% acceptable

**Issue: "Integration test timeout"**
- Cause: Receiver not printing startup confirmation
- Check: Receiver stdout contains "OSC Receiver listening"
- Debug: Run receiver manually first to verify output
- Solution: Fix receiver output format or increase timeout

### 9.2 Debugging

**Enable Verbose Output:**
```bash
# Simulator: Already verbose by default (prints each message)

# Receiver: Already verbose by default (prints each received message)
```

**Capture Network Traffic (Linux/Mac):**
```bash
# Linux
sudo tcpdump -i lo port 8000 -A -c 10

# macOS  
sudo tcpdump -i lo0 port 8000 -A -c 10

# Should show OSC message content like "/heartbeat/0" and ",i"
```

**Verify Message Format:**
```bash
# Capture raw UDP packets with hex dump
# Linux
sudo tcpdump -i lo port 8000 -XX -c 5

# macOS
sudo tcpdump -i lo0 port 8000 -XX -c 5

# Look for:
# - "/heartbeat/X" string in ASCII
# - ",i" type tag (2C 69 in hex)
# - 4-byte integer following
```

**Monitor System Resources:**
```bash
# Linux/Mac
top
# Watch Python process CPU/memory

# Windows
Task Manager → Performance tab
```

### 9.3 Platform-Specific Issues

**macOS: "Operation not permitted" for tcpdump**
- Solution: Grant Full Disk Access to Terminal in System Preferences
- Or run: `sudo tcpdump ...`

**Windows: tcpdump not available**
- Alternative: Use Wireshark (GUI packet analyzer)
- Or: Use WSL2 for Linux tools

**Linux: Permission denied on port < 1024**
- Ports below 1024 require root
- Solution: Use port 8000 (already default)

---

## 10. Success Metrics

### 10.1 Phase 1 Completion Criteria

**All of the following MUST be true:**

1. ✅ Unit test suite passes all tests
2. ✅ Simulator sends valid OSC messages for 1-4 sensors
3. ✅ Receiver validates messages and tracks statistics
4. ✅ Integration test passes
5. ✅ 60-second stability test passes (simulator + receiver running)
6. ✅ Message loss < 1% over 60-second test
7. ✅ BPM accuracy within ±2 BPM of configured values
8. ✅ All components handle errors gracefully

### 10.2 Ready for Phase 2

Phase 1 is complete and Phase 2 can begin when:

- ✅ OSC protocol proven correct via tests
- ✅ Message format validated
- ✅ Network communication stable
- ✅ Statistics tracking accurate
- ✅ Documentation complete
- ✅ No known bugs in simulation environment

**Phase 2 Preview:** Will add sensor simulation (ADC values → beat detection algorithm) using synthetic physiological data.

---

## 11. Deliverable File Structure

```
/home/claude/heartbeat-phase1/
├── esp32_simulator.py          # ESP32 behavior simulator
├── osc_receiver.py             # OSC message receiver & validator
├── test_osc_protocol.py        # Unit tests
├── test_integration.py         # Integration test
├── README.md                   # Usage instructions
└── requirements.txt            # Python dependencies
```

**requirements.txt contents:**
```
python-osc>=1.8.0
```

---

## 12. Reference Implementation Notes

These notes guide implementation but are not requirements:

**Suggested Libraries:**
- `pythonosc` for OSC message handling
- `argparse` for command-line argument parsing
- `threading` for multi-sensor simulation
- `unittest` for test framework
- `subprocess` for integration test process management

**Architecture Patterns:**
- Simulator: One thread per sensor, infinite loop sending at IBI intervals
- Receiver: Single-threaded event loop with periodic statistics printing
- Tests: Standard unittest framework with setUp/tearDown

**Performance Considerations:**
- Use `time.sleep()` for timing (adequate precision for heartbeat rates)
- Pre-create OSC clients to avoid per-message overhead
- Use thread-safe counters for statistics

---

*End of Technical Reference Document*

**Document Version:** 1.0  
**Last Updated:** 2025-11-08  
**Status:** Ready for implementation by coding agent  
**Next Document:** heartbeat-firmware-phase2-trd.md (sensor algorithm simulation)
