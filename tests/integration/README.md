# Integration Tests

End-to-end tests validating PPG → Processor → Audio/Lighting signal flow.

## Status

⚠️ **KNOWN ISSUE**: Integration tests currently fail due to PPG emulator waveform incompatibility with detector constants.

### Root Cause

The heartbeat predictor refactor (commit 1754917) introduced stricter signal quality requirements:
- `MAD_MIN_QUALITY = 40` - minimum signal variability
- `MAD_THRESHOLD_K = 4.5` - threshold multiplier tuned for real sensors

The PPG emulator waveform generates signals that either:
1. Have MAD < 40 (rejected as noise floor)
2. Have threshold > peak (no crossings detected)

### Resolution

The emulator waveform needs tuning to match real PPG sensor characteristics. This requires:
- Real sensor data recordings for reference
- Waveform parameters that satisfy both MAD >= 40 and peak > threshold constraints

Until fixed, integration tests serve as infrastructure examples but will timeout waiting for beat messages.

## Running Tests

```bash
# Run all integration tests (will fail until emulator fixed)
pytest tests/integration/

# Run specific test
pytest tests/integration/test_beat_flow.py::TestPPGToProcessorFlow::test_beat_message_arrives -v
```

## Test Structure

- `utils.py` - OSCMessageCapture, ComponentManager utilities
- `conftest.py` - Pytest fixtures for component orchestration
- `test_beat_flow.py` - PPG → Processor → Audio flow validation

## Requirements

- pytest
- python-osc
- numpy
- All amor dependencies (processor, audio, simulator)
