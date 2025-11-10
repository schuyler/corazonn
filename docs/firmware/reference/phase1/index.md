# Phase 1 Firmware TRD - Navigation Guide

**Version:** 3.0
**Last Updated:** 2025-11-09
**Purpose:** ESP32 WiFi + OSC Messaging Implementation

## Quick Reference: Where to Find X

| Looking for... | See file | Section |
|---|---|---|
| Prerequisites and setup | [overview.md](overview.md) | 0.1, 0.2 |
| Project goals and deliverables | [overview.md](overview.md) | 1 |
| Architecture and state machine | [overview.md](overview.md) | 2 |
| Libraries to install | [configuration.md](configuration.md) | 3 |
| WiFi SSID, password, SERVER_IP | [configuration.md](configuration.md) | 4.1 |
| LED pin and SENSOR_ID settings | [configuration.md](configuration.md) | 4.2, 4.3 |
| SystemState struct | [configuration.md](configuration.md) | 5 |
| connectWiFi() function | [api-network.md](api-network.md) | 6.1 |
| checkWiFi() function | [api-network.md](api-network.md) | 6.4 |
| sendHeartbeatOSC() function | [api-messaging.md](api-messaging.md) | 6.2 |
| updateLED() function | [api-status.md](api-status.md) | 6.3 |
| setup() and loop() code | [implementation.md](implementation.md) | 7.1, 7.2 |
| Project structure and platformio.ini | [implementation.md](implementation.md) | 8 |
| Build and upload commands | [implementation.md](implementation.md) | 9 |
| Testing your firmware | [operations.md](operations.md) | 10 |
| Acceptance criteria and success | [operations.md](operations.md) | 11, 14 |
| Troubleshooting guide | [operations.md](operations.md) | 13 |
| Known limitations | [operations.md](operations.md) | 12 |

## Reading Order

**First time?** Read in this order:

1. [overview.md](overview.md) - Understand the goals and architecture
2. [configuration.md](configuration.md) - Learn about configuration and data structures
3. [api-network.md](api-network.md), [api-messaging.md](api-messaging.md), [api-status.md](api-status.md) - Study each function specification
4. [implementation.md](implementation.md) - See how to implement and build
5. [operations.md](operations.md) - Validation, testing, and troubleshooting

**Implementing?** Use [api-network.md](api-network.md), [api-messaging.md](api-messaging.md), [api-status.md](api-status.md), and [implementation.md](implementation.md).

**Testing?** Jump to [operations.md](operations.md) section 10.

**Fixing issues?** Go to [operations.md](operations.md) section 13.

## Key Facts

- **Target:** ESP32-WROOM-32 (any ESP32 with WiFi)
- **Framework:** Arduino via PlatformIO CLI
- **WiFi:** 2.4GHz networks only (ESP32 limitation)
- **Messaging:** OSC via UDP on port 8000
- **Message Rate:** 1 Hz (1 message per second)
- **LED Pin:** GPIO 2 (built-in)
- **Serial Baud:** 115200
- **Estimated Time:** 2-3 hours code + 1 hour testing

## Implementation Requirements

- Firmware must compile without errors
- Must connect to WiFi within 30 seconds
- Must send OSC messages at 1 Hz (±10%)
- Python receiver must validate 0 invalid messages
- Must run 5+ minutes without crashes
- LED must indicate WiFi connection status

## Critical Prerequisites

**MUST complete before starting:**

1. PlatformIO CLI installed and tested
2. ESP32 platform available (espressif32)
3. USB drivers working (see [overview.md](overview.md) section 0.1)
4. Testing infrastructure built and running (separate TRD: `heartbeat-phase1-testing-infrastructure-trd.md`)
5. Python OSC receiver running on development machine

---

**Next Steps:**

- Read [overview.md](overview.md) to understand prerequisites and goals
- Proceed to [configuration.md](configuration.md) for setup details
