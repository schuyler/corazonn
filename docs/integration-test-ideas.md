# Integration Test Ideas

## Overview

Integration tests validate components working together end-to-end using emulators (PPG, Kasa, Launchpad).

## Implemented Tests ✓

### Beat Flow (test_beat_flow.py)
- **PPG → Processor → Audio/Lighting** - 9 tests
  - Beat message format and timing validation
  - Multi-PPG routing (independent channels)
  - BPM accuracy and intensity values
  - Timestamp freshness (<500ms)

### Sampler Integration (test_sampler_integration.py)
- **Recording & Playback Workflow** - 17 tests
  - Start/stop recording with status broadcasts
  - Assignment mode and virtual channel playback
  - Sequencer-to-sampler integration (scene button control)
  - Error handling (concurrent recording, timeouts)

### Lighting Integration (test_lighting_integration.py)
- **PPG → Processor → Lighting → Kasa** - 8 tests
  - Kasa bulb HSV state changes on beats
  - Pulse timing patterns (rise/fall)
  - Multi-zone routing and concurrent operation

### Sequencer Integration (test_sequencer_integration.py)
- **Launchpad → Sequencer → Audio** - 8 tests
  - Button presses trigger routing updates
  - LED state updates
  - Loop toggle control (start/stop)
  - Multi-PPG independent routing

### Capture/Replay Cycle (test_capture_replay.py)
- **Record → Replay → Detect** - 10 tests
  - Binary file recording with PPGL format validation
  - Replay timing and message transmission
  - End-to-end capture → replay → beat detection
  - Binary format compatibility validation
  - Note: 7/10 tests pass reliably; 3 have intermittent test isolation issues

## High Priority Gaps

### 1. Audio Effects Integration
**Test: PPG → Processor → Audio with Effects**
- No tests for biometric-responsive effects (Reverb, Phaser)
- Verify effect parameters change with BPM/intensity
- Test multiple effect chains on different PPGs
- Validate per-PPG effect routing

### 2. Full System Integration
**Test: All Components Running**
- Start PPG + processor + audio + lighting + sequencer + sampler
- Run for 30 seconds
- Verify all subsystems communicate correctly
- Check for resource leaks or threading issues

### 3. Error Handling & Recovery
**Stale Timestamps**
- Send beat with 600ms old timestamp
- Verify audio/lighting drop the message
- Check `dropped_messages` counter increments

**Dropout Recovery**
- Trigger dropout: `ppg_emulator.trigger_dropout(beats=5)`
- Verify processor handles signal loss
- Check beat detection resumes after dropout

**Component Restart**
- Kill component process mid-run
- Restart component
- Verify system recovers without manual intervention

## Implementation Notes

### Test Utilities (tests/integration/utils.py)
- `OSCMessageCapture` - Listen on port, collect messages
- `ComponentManager` - Start/stop components with cleanup
- Pytest fixtures in `conftest.py` for common setups

### Implementation Priority
1. **Audio effects** - Tests biometric-responsive audio processing
2. **Full system** - Comprehensive integration of all components
3. **Error recovery** - Ensures robustness under failure conditions
