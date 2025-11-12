# Integration Test Ideas

## Overview

With validated emulators (46 tests passing), we can now test amor components working together end-to-end.

## Test Categories

### 1. Beat Flow Tests

**PPG → Processor → Audio**
- Start PPG emulator (75 BPM) + processor + audio
- Verify beat messages arrive at audio within 100ms
- Check correct sample playback based on routing
- Validate timestamp freshness (<500ms)

**PPG → Processor → Lighting**
- Start PPG emulator + processor + lighting (test config)
- Verify Kasa emulator receives HSV changes
- Check pulse timing (rise + fall pattern)
- Validate zone routing (PPG 0 → Bulb 0, etc.)

### 2. Sequencer Integration Tests

**Launchpad → Sequencer → Audio Routing**
- Start launchpad emulator + sequencer + audio
- Press PPG button: `emulator.press_ppg_button(0, 5)`
- Verify LED state updates to selected (mode=1)
- Trigger beat from PPG 0
- Assert audio plays sample from column 5

**Loop Toggle Control**
- Toggle loop: `emulator.toggle_loop(3)`
- Verify loop starts/stops
- Check LED state reflects active status

### 3. Multi-Sensor Coordination

**Four PPG Streams**
- Start 4 PPG emulators (60, 70, 80, 90 BPM)
- Start processor + audio + lighting
- Run for 10 seconds
- Verify all 4 sensors detected independently
- Check no cross-talk (PPG 0 beats → Bulb 0 only)
- Validate beat rates match configured BPMs (±5%)

### 4. Error Handling Tests

**Stale Timestamps**
- Send beat with 600ms old timestamp
- Verify audio/lighting drop the message
- Check `dropped_messages` counter increments

**Dropout Recovery**
- Trigger dropout: `ppg_emulator.trigger_dropout(beats=5)`
- Verify processor handles signal loss
- Check beat detection resumes after dropout

**Component Restart**
- Kill audio process mid-run
- Restart audio
- Verify system recovers without manual intervention

### 5. Performance Tests

**Latency Measurements**
- Capture PPG message timestamp
- Capture beat message timestamp
- Capture audio play timestamp
- Assert: PPG→beat <50ms, beat→audio <100ms

**Throughput Under Load**
- Run 4 PPG @ 90 BPM = ~6 beats/sec = ~48 OSC msg/sec
- Monitor for dropped messages
- Verify <1% drop rate over 60 seconds

## Implementation Approach

```python
# tests/integration/test_beat_flow.py
def test_ppg_to_audio_latency(start_components):
    ppg = PPGEmulator(ppg_id=0, bpm=75)
    audio_monitor = OSCMessageCapture(port=8001)

    ppg.run_async()
    time.sleep(2)  # Warmup

    # Capture timing
    start = time.time()
    audio_monitor.wait_for_message("/beat/0", timeout=2.0)
    latency = time.time() - start

    assert latency < 0.1  # 100ms
```

## Test Utilities Needed

- `OSCMessageCapture`: Listen on port, collect messages
- `ComponentManager`: Start/stop amor components
- `timing_assert`: Assert timing within tolerance
- `state_inspector`: Query emulator state for validation

## Next Steps

1. Create `tests/integration/` directory
2. Build test utilities (message capture, component manager)
3. Implement 2-3 basic flow tests
4. Add to CI/CD pipeline
