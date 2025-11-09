# Firmware Documentation

ESP32 firmware for the Heartbeat Installation project.

## Quick Navigation

**New to the project?**
Start with [Architecture](reference/architecture.md) for the overall design.

**Implementing Phase 1 firmware?**
1. Read [Phase 1 Firmware TRD](reference/phase1-firmware-trd.md) (requirements)
2. Follow [Phase 1 Guides](guides/) step-by-step (01 through 06)
3. Track progress with [Phase 1 Firmware Tasks](tasks/phase1-firmware.md)

**Setting up testing infrastructure?**
See [Testing Documentation](../testing/) for testing TRDs and tasks.

## Organization

### `reference/` - Technical Specifications
Authoritative reference documents defining requirements and architecture.

- **[architecture.md](reference/architecture.md)** - Overall firmware design (multi-phase)
- **[phase1-firmware-trd.md](reference/phase1-firmware-trd.md)** - Phase 1 ESP32 firmware specification

### `guides/` - Implementation Tutorials
Step-by-step guides for implementing firmware. Follow these sequentially.

#### Phase 1: WiFi + OSC
1. **[phase1-01-environment-setup.md](guides/phase1-01-environment-setup.md)** - PlatformIO installation
2. **[phase1-02-firmware-skeleton.md](guides/phase1-02-firmware-skeleton.md)** - Code structure
3. **[phase1-03-wifi-connection.md](guides/phase1-03-wifi-connection.md)** - WiFi connectivity
4. **[phase1-04-osc-messaging.md](guides/phase1-04-osc-messaging.md)** - OSC protocol
5. **[phase1-05-validation.md](guides/phase1-05-validation.md)** - Testing and validation
6. **[phase1-06-implementation-summary.md](guides/phase1-06-implementation-summary.md)** - Implementation review

### `tasks/` - Task Lists
Checklists for tracking implementation progress.

- **[phase1-firmware.md](tasks/phase1-firmware.md)** - Firmware implementation checklist

## Phases

### Phase 1: WiFi + OSC (Complete)
ESP32 connects to WiFi and sends test OSC messages.

### Phase 2+: Future Enhancements
Sensor input, beat detection, multi-sensor support, watchdog timer, OTA updates, etc.

## Development Workflow

```
Read TRD → Follow Guides → Track Tasks
```

1. Read [reference/phase1-firmware-trd.md](reference/phase1-firmware-trd.md) to understand requirements
2. Follow guides sequentially (phase1-01 through phase1-06)
3. Check off tasks in [tasks/phase1-firmware.md](tasks/phase1-firmware.md)
