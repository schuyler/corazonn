# Amor Integration Testing Design

## Overview

This document outlines the automated integration testing environment for the Amor system. The design focuses on hardware emulation, component orchestration, and end-to-end validation without requiring physical devices.

## Architecture

### Hardware Emulation Layer

Three emulators replace physical hardware dependencies:

1. **PPG Sensor Emulator** (`amor/simulator/ppg_emulator.py`)
   - Emulates ESP32 PPG sensors
   - Generates realistic cardiac waveforms with configurable BPM
   - Sends OSC messages at 10 Hz (matching real hardware)
   - Supports dropout injection for error testing
   - Programmable API for test scenarios

2. **Launchpad Emulator** (`amor/simulator/launchpad_emulator.py`)
   - Emulates Novation Launchpad MIDI controller
   - Sends OSC control messages (button presses)
   - Receives and tracks LED state from sequencer
   - Interactive CLI mode for manual testing
   - Programmatic API for automated tests

3. **Kasa Bulb Emulator** (`amor/simulator/kasa_emulator.py`)
   - Emulates TP-Link Kasa smart bulbs
   - Implements Kasa TCP protocol (encrypted)
   - Tracks HSV state changes
   - Multi-bulb support (4 zones)
   - State inspection for validation

### Component Orchestration

**Procfile.test** coordinates all components:

```
# Hardware layer
ppg0, ppg1, ppg2, ppg3    - 4 emulated PPG sensors
bulbs                      - 4 emulated Kasa bulbs
launchpad                  - Emulated MIDI controller

# Amor components
processor                  - Beat detection
audio                      - Sample playback
lighting                   - Bulb control (uses test config)
sequencer                  - State management
```

Run with: `honcho -f Procfile.test start`

### Configuration

**Test Configuration** (`amor/config/lighting.test.yaml`):
- Points to emulated bulbs on localhost (127.0.0.1-4:9999)
- Same effect parameters as production
- Requires loopback aliases: `sudo ifconfig lo:1 127.0.0.2 up` (etc.)

## Integration Test Scenarios

### 1. End-to-End Beat Flow

**Purpose:** Validate complete signal path from PPG → audio/lighting

**Steps:**
1. Start all components via Procfile.test
2. PPG emulators generate heartbeats at different BPMs
3. Processor detects beats and broadcasts
4. Audio engine plays samples with correct routing
5. Lighting engine pulses bulbs

**Validation:**
- Audio messages received with correct PPG routing
- Kasa emulators show state changes (H/S/B)
- Timing within latency thresholds (<500ms)

**Automation:**
```python
# Test script example
ppg = PPGEmulator(ppg_id=0, bpm=75)
bulb_monitor = KasaBulbEmulator(ip="127.0.0.1")

# Start components
ppg.run_async()
bulb_monitor.run_async()

# Wait for beats
time.sleep(5)

# Validate
assert bulb_monitor.state_changes > 5, "No pulses detected"
assert 70 < ppg.bpm < 80, "BPM drift"
```

### 2. Sequencer Routing

**Purpose:** Validate Launchpad → Sequencer → Audio routing

**Steps:**
1. Start emulated Launchpad + sequencer + audio
2. Press PPG button: `emulator.press_ppg_button(ppg_id=0, column=3)`
3. Verify LED update: `assert emulator.get_led_state(0, 3) == (COLOR_CYAN, MODE_PULSE)`
4. Trigger beat from PPG 0
5. Verify audio plays sample from column 3

**Validation:**
- LED state matches expected (color, mode)
- Audio routing updated correctly
- No message drops

### 3. Multi-Sensor Coordination

**Purpose:** Validate 4 simultaneous PPG streams

**Steps:**
1. Start 4 PPG emulators with different BPMs (60, 70, 80, 90)
2. Verify processor handles all streams
3. Verify correct zone routing (PPG 0 → Zone 0, etc.)
4. Verify no cross-talk between zones

**Validation:**
- All 4 bulbs pulsing independently
- Beat rates match configured BPMs (±5%)
- No dropped messages (check stats)

### 4. Error Recovery

**Purpose:** Validate system resilience

**Steps:**
1. Start full system
2. Inject dropout: `ppg_emulator.trigger_dropout(beats=5)`
3. Kill and restart processor
4. Kill and restart audio engine
5. Verify system recovers

**Validation:**
- Dropout logged but no crashes
- Component restarts don't lose state
- Beat detection resumes after dropout
- Audio/lighting reconnect automatically

### 5. Timestamp Validation

**Purpose:** Validate timing accuracy

**Steps:**
1. Start PPG → processor → audio/lighting
2. Measure beat event timestamps
3. Inject 600ms delay (simulate network lag)
4. Verify stale messages dropped

**Validation:**
- Fresh beats (<500ms) processed
- Stale beats (≥500ms) dropped with log message
- Stats show dropped_messages counter increments

## Testing Infrastructure

### Message Capture

```python
class OSCMessageCapture:
    """Captures OSC messages for validation."""

    def __init__(self, port: int):
        self.messages = []
        self.server = ReusePortBlockingOSCUDPServer(
            ("0.0.0.0", port),
            self._capture_handler
        )

    def _capture_handler(self, address, *args):
        self.messages.append((time.time(), address, args))

    def assert_received(self, address_pattern, timeout=5.0):
        """Assert message received within timeout."""
        start = time.time()
        while time.time() - start < timeout:
            if any(addr.startswith(address_pattern) for _, addr, _ in self.messages):
                return True
            time.sleep(0.1)
        raise AssertionError(f"No message matching {address_pattern}")
```

### Timing Helpers

```python
def assert_within_ms(timestamp_ms: int, max_age_ms: int = 500):
    """Assert timestamp is within max_age_ms of now."""
    now_ms = time.time() * 1000
    age_ms = now_ms - timestamp_ms
    assert age_ms < max_age_ms, f"Timestamp too old: {age_ms}ms"
```

### State Inspection

All emulators provide `.get_state()` methods:

```python
# PPG state
ppg_state = ppg_emulator.get_state()
assert ppg_state['bpm'] == 75.0

# Launchpad state
selected = launchpad_emulator.get_ppg_selection(ppg_id=0)
assert selected == 3

# Kasa bulb state
bulb_state = kasa_emulator.get_state()
assert bulb_state['brightness'] > 40  # Pulsing
```

## CI/CD Integration

### Automated Test Suite

```bash
#!/bin/bash
# tests/integration/run_tests.sh

# Start emulators + components
honcho -f Procfile.test start &
HONCHO_PID=$!

# Wait for initialization
sleep 5

# Run test suite
pytest tests/integration/ -v

# Cleanup
kill $HONCHO_PID
```

### Test Matrix

- **Beat Flow:** All PPG → processor → audio/lighting combinations
- **Routing:** All 32 sample selections (4 PPG × 8 columns)
- **Loops:** 16 latching + 16 momentary loops
- **Error Cases:** Dropouts, restarts, stale timestamps

### Coverage Metrics

- Message path coverage (all OSC routes exercised)
- State transition coverage (all sequencer states)
- Error path coverage (all error handlers triggered)

## Performance Benchmarks

### Latency Targets

- PPG → Processor → Beat event: <50ms
- Beat → Audio playback: <100ms
- Beat → Bulb pulse start: <200ms
- End-to-end (PPG → Bulb): <300ms

### Throughput Targets

- 4 PPG streams @ 10 Hz = 40 msg/s
- Processor → Audio/Lighting: 80 msg/s (2 destinations)
- Sequencer control: 10 msg/s (human interaction rate)

### Measurement

```python
class LatencyMonitor:
    """Measures end-to-end latency."""

    def measure_ppg_to_bulb(self):
        ppg_capture = OSCMessageCapture(8000)
        beat_capture = OSCMessageCapture(8002)

        # Wait for messages
        time.sleep(1)

        # Match PPG → Beat timestamps
        for ppg_time, ppg_addr, ppg_args in ppg_capture.messages:
            for beat_time, beat_addr, beat_args in beat_capture.messages:
                if self._matches(ppg_args, beat_args):
                    latency_ms = (beat_time - ppg_time) * 1000
                    print(f"Latency: {latency_ms:.1f}ms")
                    assert latency_ms < 300
```

## Future Enhancements

### Additional Test Scenarios

1. **Concurrent Users:** Multiple Launchpads (different sequencer instances)
2. **Network Partitions:** Simulate UDP packet loss
3. **Load Testing:** Stress test with 100+ Hz PPG rates
4. **Long-running:** 24-hour soak test for memory leaks

### Test Tooling

1. **Web Dashboard:** Real-time visualization of test execution
2. **Trace Viewer:** Message flow visualization
3. **Replay Tool:** Record/replay OSC sessions
4. **Mutation Testing:** Inject protocol errors

### Chaos Engineering

1. **Random Failures:** Kill random components during execution
2. **Clock Skew:** Simulate system time drift
3. **Resource Exhaustion:** CPU/memory pressure
4. **Byzantine Faults:** Corrupt OSC messages

## Conclusion

The integration testing environment provides:

✅ **No hardware dependencies** - All devices emulated
✅ **Programmatic control** - Automated test scenarios
✅ **State inspection** - Validate internal state
✅ **CI/CD ready** - Run in containerized environments
✅ **Realistic protocols** - Emulators match real hardware

This enables rapid iteration, regression testing, and confidence in system-level behavior before hardware deployment.
