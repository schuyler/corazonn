# Phase 2 Firmware TRD - Navigation Guide

**Version:** 1.0
**Last Updated:** 2025-11-09
**Hardware:** ESP32-WROOM-32 with PulseSensor optical pulse sensor
**Framework:** Arduino (via PlatformIO CLI)

This documentation splits the Phase 2 Firmware Technical Reference Document into organized modules for easier navigation and reference.

## Documentation Structure

### Getting Started

- **[Overview](overview.md)** - Prerequisites, objectives, and system architecture
  - Phase 1 completion requirements
  - Hardware setup and validation
  - Phase 2 implementation objectives
  - Execution model and data flow

### Configuration & Setup

- **[Configuration](configuration.md)** - Libraries, constants, and data structures
  - Required Arduino libraries
  - Hardware and network configuration
  - Signal processing parameters
  - Beat detection parameters
  - SystemState and SensorState structures

### API Reference

Core firmware functions organized by responsibility:

- **[Sensor API](api-sensors.md)** - ADC sampling and signal smoothing
  - `initializeSensor()` - ADC configuration and buffer initialization
  - `updateMovingAverage()` - Circular buffer and noise filtering

- **[Signal Processing API](api-signal-processing.md)** - Baseline tracking and connection monitoring
  - `updateBaseline()` - Adaptive baseline with exponential decay
  - `checkDisconnection()` - Flat signal detection and reconnection

- **[Beat Detection API](api-beat-detection.md)** - Heartbeat identification and IBI calculation
  - `detectBeat()` - Threshold detection with refractory period
  - OSC transmission logic

- **[Network API](api-network.md)** - WiFi connection and UDP communication
  - `connectWiFi()` - WiFi connection with timeout (Phase 1)
  - `checkWiFi()` - WiFi status monitoring (Phase 1)

- **[Messaging API](api-messaging.md)** - OSC message construction and transmission
  - `sendHeartbeatOSC()` - OSC message with IBI data (Phase 1)

- **[Status API](api-status.md)** - LED feedback
  - `updateLED()` - WiFi and beat pulse indication

### Implementation

- **[Implementation](implementation.md)** - Program flow and structure
  - `setup()` function - Initialization sequence
  - `loop()` function - Main sampling and processing cycle
  - File organization and code structure
  - PlatformIO configuration
  - Compilation and upload procedures

### Operations & Testing

- **[Operations](operations.md)** - Validation, tuning, troubleshooting
  - Validation and testing procedures
  - Multi-unit testing
  - Parameter tuning for different signal conditions
  - Debug output levels
  - Troubleshooting guide
  - Acceptance criteria
  - Success metrics

## Quick Reference

### Key Constants

```cpp
const int SENSOR_PIN = 32;              // GPIO 32 (ADC1_CH4)
const int SAMPLE_RATE_HZ = 50;          // 50 samples/second
const int SAMPLE_INTERVAL_MS = 20;      // 1000 / 50 = 20ms
const int MOVING_AVG_SAMPLES = 5;       // 100ms smoothing window
const float THRESHOLD_FRACTION = 0.6;   // 60% of signal range above baseline
const unsigned long REFRACTORY_PERIOD_MS = 300;  // Max 200 BPM
```

### Critical Prerequisites

```
Step 1: Complete phase1-firmware-trd.md FIRST
Step 2: Validate Phase 1 WiFi and OSC messaging working
Step 3: Connect PulseSensor hardware (GPIO 32)
Step 4: Then implement this firmware
Step 5: Test with real heartbeat detection
```

### Success Criteria

All of the following MUST be met:

- Firmware compiles without errors
- Detects heartbeats within 3 seconds of finger application
- BPM accuracy within ±5 BPM vs smartphone app
- Runs for 30+ minutes without crashes
- Handles sensor disconnect/reconnect gracefully
- OSC messages contain real IBI data (not test values)

## Document Dependencies

**Requires:** `phase1-firmware-trd.md` (WiFi + OSC messaging)
**Precedes:** `phase3-firmware-trd.md` (4-sensor expansion)

## Implementation Estimate

- **Code implementation:** 3-4 hours
- **Testing and tuning:** 2 hours
- **Total:** 5-6 hours

---

*For detailed specifications on any topic, refer to the corresponding module in the navigation list above.*
