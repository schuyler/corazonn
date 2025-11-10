# Firmware Documentation

ESP32 firmware for the Heartbeat Installation project. Multi-phase implementation from WiFi connectivity through 4-sensor beat detection and integration.

## Quick Start

1. **Start here:** [Architecture Overview](reference/architecture.md) - System design covering all phases
2. **Choose your phase:** Jump to the phase documentation below
3. **Track progress:** Use the task checklist for your phase

---

## Reference Documentation

### Architecture & Design
- **[architecture.md](reference/architecture.md)** - Overall firmware design, data flow, and multi-phase architecture

### Phase Documentation
Each phase has a complete technical reference and associated task tracking.

#### [Phase 1: WiFi + OSC](reference/phase1/index.md)
**Status:** Complete | **Hardware:** ESP32 | **Features:** WiFi connectivity, OSC messaging
- [Overview](reference/phase1/overview.md) - Goals, architecture, prerequisites
- [Configuration](reference/phase1/configuration.md) - Libraries, constants, data structures
- [Network API](reference/phase1/api-network.md) - WiFi connection and status checking
- [Messaging API](reference/phase1/api-messaging.md) - OSC message transmission
- [Status API](reference/phase1/api-status.md) - LED feedback
- [Implementation](reference/phase1/implementation.md) - Code structure and build instructions
- [Operations](reference/phase1/operations.md) - Testing, validation, troubleshooting
- **Task checklist:** [phase1-firmware.md](tasks/phase1-firmware.md)

#### [Phase 2: Single Sensor + Beat Detection](reference/phase2/index.md)
**Status:** Documented | **Hardware:** ESP32 + PulseSensor | **Features:** Heartbeat detection, adaptive signal processing
- [Overview](reference/phase2/overview.md) - Goals, prerequisites, hardware setup
- [Configuration](reference/phase2/configuration.md) - Libraries, sampling parameters
- [Sensor API](reference/phase2/api-sensors.md) - ADC sampling and signal filtering
- [Signal Processing API](reference/phase2/api-signal-processing.md) - Baseline tracking, disconnect detection
- [Beat Detection API](reference/phase2/api-beat-detection.md) - Heartbeat identification
- [Network API](reference/phase2/api-network.md) - WiFi and OSC (Phase 1 continued)
- [Messaging API](reference/phase2/api-messaging.md) - OSC with IBI data (Phase 1 continued)
- [Status API](reference/phase2/api-status.md) - LED feedback for beats and WiFi
- [Implementation](reference/phase2/implementation.md) - Main loop, file organization
- [Operations](reference/phase2/operations.md) - Testing, tuning, troubleshooting
- **Task checklist:** [phase2-firmware.md](tasks/phase2-firmware.md)

#### [Phase 3: Multi-Sensor Support](reference/phase3/index.md)
**Status:** Documented | **Hardware:** ESP32 + 4x PulseSensor | **Features:** 4-sensor sampling, per-sensor beat detection
- [Overview](reference/phase3/overview.md)
- [Configuration](reference/phase3/configuration.md)
- [Sensor API](reference/phase3/api-sensors.md)
- [Signal Processing API](reference/phase3/api-signal-processing.md)
- [Beat Detection API](reference/phase3/api-beat-detection.md)
- [Network API](reference/phase3/api-network.md)
- [Messaging API](reference/phase3/api-messaging.md)
- [Status API](reference/phase3/api-status.md)
- [Implementation](reference/phase3/implementation.md)
- [Operations](reference/phase3/operations.md)
- **Task checklist:** [phase3-firmware.md](tasks/phase3-firmware.md)

#### [Phase 4: Integration & Robustness](reference/phase4/index.md)
**Status:** Documented | **Hardware:** ESP32 + 4x PulseSensor | **Features:** OTA updates, watchdog, error recovery
- [Overview](reference/phase4/overview.md)
- [Configuration](reference/phase4/configuration.md)
- [API Integration](reference/phase4/api-integration.md)
- [Implementation](reference/phase4/implementation.md)
- [Operations](reference/phase4/operations.md)
- **Task checklist:** [phase4-firmware.md](tasks/phase4-firmware.md)

---

## Implementation Guides

Step-by-step tutorials for Phase 1 implementation (foundation for all phases).

1. **[phase1-01-environment-setup.md](guides/phase1-01-environment-setup.md)** - PlatformIO installation and verification
2. **[phase1-02-firmware-skeleton.md](guides/phase1-02-firmware-skeleton.md)** - Project structure and basic code organization
3. **[phase1-03-wifi-connection.md](guides/phase1-03-wifi-connection.md)** - WiFi connectivity implementation
4. **[phase1-04-osc-messaging.md](guides/phase1-04-osc-messaging.md)** - OSC protocol and message transmission
5. **[phase1-05-validation.md](guides/phase1-05-validation.md)** - Testing and validation procedures
6. **[phase1-06-implementation-summary.md](guides/phase1-06-implementation-summary.md)** - Review and next steps

---

## Typical Workflow

```
Read architecture.md
    ↓
Choose phase and read its index.md
    ↓
For Phase 1: Follow implementation guides (01-06)
    ↓
Read phase-specific API and implementation docs
    ↓
Implement and track progress in task checklist
    ↓
Test using operations guide
```
