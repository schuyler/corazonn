# Phase 4 Firmware - OSC Integration & Production Validation

**Version:** 1.0
**Date:** 2025-11-09
**Status:** Ready for implementation

## Overview

Phase 4 integrates Phase 3's beat detection with Phase 1's OSC infrastructure for a complete data pipeline from pulse sensor to audio server.

**Audience:** Coding agent implementing ESP32 firmware
**Hardware:** ESP32-WROOM-32 + 4 optical pulse sensors on GPIO 32-35
**Framework:** Arduino (via PlatformIO CLI)

## Quick Start

1. **[Overview](./overview.md)** - Prerequisites, objective, and architecture
2. **[Configuration](./configuration.md)** - Code structure and implementation approach
3. **[API Integration](./api-integration.md)** - Integration points between Phase 1 and Phase 3
4. **[Implementation](./implementation.md)** - Testing and validation procedures
5. **[Operations](./operations.md)** - Production configuration, troubleshooting, deployment

## Critical Prerequisites

Before implementing Phase 4, validate:

- ✅ **Phase 1** - WiFi + OSC messaging working independently
- ✅ **Phase 3** - Multi-sensor beat detection algorithm validated
- ✅ **Testing Infrastructure** - Python OSC receiver on port 8000
- ✅ **Hardware Setup** - 4 pulse sensors on GPIO 32-35, WiFi connectivity

See [Overview - Prerequisites](./overview.md#0-prerequisites) for validation checklist.

## Key Deliverables

- Single `main.cpp` combining Phase 3 beat detection + Phase 1 OSC messaging
- Real sensor-derived IBI values transmitted via OSC (no test values)
- Complete end-to-end validation from pulse sensor to audio server
- Production-ready configuration (DEBUG_LEVEL 0)
- Documentation of integration points and testing procedures

## Success Criteria

| Aspect | Target | Validation |
|--------|--------|-----------|
| OSC Format | 100% valid messages | Python receiver validation |
| BPM Accuracy | ±5 BPM | vs smartphone reference |
| Latency (95th %) | <25ms | beat to network |
| Stability | 0 crashes | 30+ minute test |
| WiFi Resilience | Auto-reconnect <30s | disconnect/reconnect test |
| Multi-sensor | No crosstalk | 4-person concurrent test |

## Estimated Timeline

- Integration: 3-4 hours
- Validation: 3-4 hours
- **Total: 6-8 hours**

## File Structure

```
firmware/heartbeat_phase4/
├── platformio.ini         # Build configuration
├── src/
│   └── main.cpp          # Integrated firmware
├── include/
│   └── ssid.h            # WiFi credentials (untracked)
└── test/                 # Validation tests
```

## Key Integration Points

**Phase 4 bridges:**

```
Phase 3 (Beat Detection)
    ↓ IBI value
Phase 1 (OSC Messaging)
    ↓ OSC packets
Audio Server
```

- **Phase 3** produces `detectBeat()` events with IBI values
- **Phase 1** has proven `sendHeartbeatOSC()` function
- **Phase 4** validates they work together in production

## Navigation

- See [Configuration](./configuration.md) to understand code structure requirements
- See [API Integration](./api-integration.md) for the six integration requirements (R1-R6)
- See [Implementation](./implementation.md) for test procedures
- See [Operations](./operations.md) for production deployment checklist

## Related Documents

- `docs/firmware/reference/architecture.md` - Overall system design
- `docs/firmware/reference/phase1-firmware-trd.md` - WiFi + OSC infrastructure
- `docs/firmware/reference/phase3-firmware-trd.md` - Multi-sensor beat detection
- `docs/firmware/guides/phase1-05-validation.md` - Python OSC receiver setup

---

**Next Steps:** Start with [Overview](./overview.md) to understand prerequisites and architecture. Then proceed to [Configuration](./configuration.md) for implementation approach.
