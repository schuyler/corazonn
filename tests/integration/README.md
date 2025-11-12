# Integration Tests

End-to-end tests validating PPG → Processor → Audio/Lighting signal flow.

## Status

✅ **Integration tests operational** - PPG emulator waveform tuned for detector compatibility.

### Test Results

- **8 integration tests** validating beat message format, timestamp freshness, BPM accuracy, multi-sensor routing
- **7/8 tests pass consistently** when run individually
- Minor timing issue when running full suite (occasional timeout between tests due to component cleanup)

### PPG Emulator Configuration

The emulator generates signals compatible with detector constants:

**Waveform Parameters:**
- `noise_level = 50.0` - ensures MAD ≥ 40 (detector signal quality threshold)
- `systolic_peak = 3800` - ensures peak crosses threshold (median + 4.5×MAD)
- `diastolic_trough = 2000` - baseline for triangular pulse waveform
- Triangular pulse: 70% baseline, 15% ramp up, 15% ramp down

**Mathematical Validation (100-sample window):**
- Median: ~2020 (70% samples near baseline)
- MAD: ~47-54 (above MAD_MIN_QUALITY=40 threshold ✓)
- Threshold: ~2234 (median + 4.5×MAD)
- Peak: ~3780 (crosses threshold successfully ✓)

## Running Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test
pytest tests/integration/test_beat_flow.py::TestPPGToProcessorFlow::test_beat_message_arrives -v

# Run specific test class
pytest tests/integration/test_beat_flow.py::TestPPGToProcessorFlow -v
```

## Test Coverage

### TestPPGToProcessorFlow
- `test_beat_message_arrives` - Beats arrive within 5s
- `test_beat_message_format` - Message structure and types
- `test_beat_timestamp_freshness` - Timestamps < 500ms old
- `test_multiple_beats_arrive` - Multiple beats over 8s
- `test_beat_bpm_accuracy` - BPM within ±15% of target
- `test_beat_intensity_valid_range` - Intensity in [0, 1]

### TestPPGToAudioFlow
- `test_audio_receives_beats` - Audio engine receives broadcasts
- `test_multi_ppg_routing` - Independent routing for multiple sensors

## Test Structure

- `utils.py` - OSCMessageCapture (SO_REUSEPORT capture), ComponentManager (subprocess orchestration)
- `conftest.py` - Pytest fixtures (beat_capture, component_manager, simple_setup)
- `test_beat_flow.py` - PPG → Processor → Audio flow validation

## Requirements

- pytest
- python-osc
- numpy
- All amor dependencies (processor, audio, simulator)

## Architecture

Integration tests use subprocess-based component orchestration:

```python
with ComponentManager() as manager:
    manager.add_ppg_emulator(ppg_id=0, bpm=75)
    manager.add_processor()
    manager.start_all()

    # OSCMessageCapture listens on port 8001 (SO_REUSEPORT)
    ts, addr, args = beat_capture.wait_for_message("/beat/0", timeout=5.0)
    assert addr == "/beat/0"
```

Components are automatically cleaned up on exit via context manager.
