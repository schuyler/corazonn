# Phase 3 Firmware TRD - Documentation Index

**Heartbeat Firmware - Phase 3: Multi-Sensor Beat Detection**

Version 1.0 | Published 2025-11-09 | Status: Ready for implementation

---

## Quick Start

1. Start with [Overview](overview.md) for context and prerequisites
2. Configure your environment in [Configuration](configuration.md)
3. Implement functions using the API reference guides (see below)
4. Follow [Implementation](implementation.md) for main program flow
5. Validate using [Operations](operations.md) testing procedures

---

## Documentation Map

### Understanding the System
- **[Overview](overview.md)** — Prerequisites, objectives, and architecture overview
  - Section 0: Prerequisites (Phase 1 completion, hardware setup)
  - Section 1: Objective (deliverables and success criteria)
  - Section 2: Architecture overview (execution model, state machine, data flow)

### Configuration & Setup
- **[Configuration](configuration.md)** — Libraries, constants, and data structures
  - Section 3: Required libraries (Arduino, OSC, PlatformIO)
  - Section 4: Configuration constants (network, hardware, signal processing, beat detection)
  - Section 5: Data structures (SensorState, SystemState)

### API Reference

#### Sensor Operations
- **[API: Sensors](api-sensors.md)** — Hardware sampling and signal filtering
  - Function 6.1: `initializeSensor()` — Initialize sensor state
  - Function 6.2: `readAndFilterSensor()` — ADC read with moving average filter

#### Signal Processing
- **[API: Signal Processing](api-signal-processing.md)** — Adaptive baseline tracking
  - Function 6.3: `updateBaseline()` — Exponential decay baseline with instant expansion

#### Beat Detection
- **[API: Beat Detection](api-beat-detection.md)** — Core beat detection algorithm
  - Function 6.4: `detectBeat()` — Rising edge detection with refractory period

#### Data Transmission
- **[API: Messaging](api-messaging.md)** — OSC message construction and transmission
  - Function 6.5: `sendHeartbeatOSC()` — Send heartbeat data via OSC/UDP

#### System Control
- **[API: Status](api-status.md)** — LED feedback and visual indication
  - Function 6.6: `updateLED()` — WiFi and beat indication

- **[API: Network](api-network.md)** — WiFi connectivity monitoring
  - Function 6.7: `checkWiFi()` — Monitor and maintain WiFi connection

### Implementation & Compilation
- **[Implementation](implementation.md)** — Program structure and compilation
  - Section 7: Main program flow (`setup()` and `loop()`)
  - Section 8: Complete program structure
  - Section 9: Compilation and upload commands

### Testing & Operations
- **[Operations](operations.md)** — Validation, testing, troubleshooting
  - Section 10: Validation and testing procedures (smoke test to extended duration)
  - Section 11: Acceptance criteria
  - Section 12: Known limitations
  - Section 13: Troubleshooting guide
  - Section 14: Success metrics
  - Appendix: Sample serial output (production, testing, verbose)

---

## Key Specifications at a Glance

| Specification | Value |
|---|---|
| Target Platform | ESP32-WROOM-32 |
| Framework | Arduino (PlatformIO CLI) |
| Sensors | 4 optical pulse sensors (GPIO 32-35) |
| Sampling Rate | 50 Hz per sensor |
| ADC Resolution | 12-bit (0-4095) |
| WiFi Protocol | OSC over UDP |
| Beat Detection | Rising edge with refractory period |
| Moving Average Window | 5 samples (100 ms) |
| Baseline Decay Interval | 150 samples (3 seconds) |
| Refractory Period | 300 ms (max 200 BPM) |
| Target BPM Accuracy | ±5 BPM vs smartphone reference |
| Beat to OSC Latency | <25 ms |
| Stability Requirement | 30+ minutes continuous |

---

## Cross-References

**By Function Requirement Number:**
- R1-R8: Sensor initialization ([API: Sensors](api-sensors.md))
- R9-R11: Moving average filtering ([API: Sensors](api-sensors.md))
- R12-R14: Baseline tracking ([API: Signal Processing](api-signal-processing.md))
- R15-R19: Beat detection algorithm ([API: Beat Detection](api-beat-detection.md))
- R20-R23: OSC transmission ([API: Messaging](api-messaging.md))
- R24-R25: LED feedback ([API: Status](api-status.md))
- R26-R31: setup() function ([Implementation](implementation.md))
- R32-R36: loop() function ([Implementation](implementation.md))

---

## File Organization

```
docs/firmware/reference/phase3/
├── index.md                      # This file - navigation guide
├── overview.md                   # System overview & prerequisites
├── configuration.md              # Libraries, constants, data structures
├── api-sensors.md               # Sensor initialization & filtering
├── api-signal-processing.md     # Baseline tracking algorithm
├── api-beat-detection.md        # Beat detection algorithm
├── api-messaging.md             # OSC message transmission
├── api-status.md                # LED feedback
├── api-network.md               # WiFi monitoring
├── implementation.md             # Program flow & compilation
└── operations.md                # Testing, troubleshooting, metrics
```

---

## Dependencies

**Prerequisites:**
- Phase 1 firmware (WiFi + OSC infrastructure) MUST be completed and validated
- PlatformIO CLI configured
- Python 3 receiver script for validation

**Hardware:**
- ESP32-WROOM-32
- 4 optical pulse sensors with 12-bit ADC output
- 3.3V stable power supply

---

## Implementation Checklist

- [ ] Read Overview for context
- [ ] Configure constants in Configuration
- [ ] Implement API functions per specifications
- [ ] Implement main program flow (setup/loop)
- [ ] Compile without errors
- [ ] Run single-sensor smoke test
- [ ] Validate multi-sensor operation
- [ ] Complete stability test (30+ minutes)
- [ ] Achieve ±5 BPM accuracy vs smartphone
- [ ] Ready for festival deployment

---

## Contact & Support

For detailed implementation guidance, see specific sections:
- Algorithm questions: [API: Beat Detection](api-beat-detection.md)
- Compilation issues: [Implementation](implementation.md)
- Test failures: [Operations](operations.md)

**Document Status:** Ready for implementation
**Estimated Time:** 4-6 hours (code) + 2-3 hours (testing)
**Next Phase:** Phase 4 - Audio synthesis integration
