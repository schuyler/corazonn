# Phase 3 Overview: Prerequisites, Objective & Architecture

**Heartbeat Firmware - Phase 3 Firmware Implementation TRD**

---

## Document Information

**Version:** 1.0
**Date:** 2025-11-09
**Purpose:** Expand from single sensor to 4 sensors with real beat detection algorithm
**Audience:** Coding agent implementing ESP32 firmware
**Hardware:** ESP32-WROOM-32 + 4 optical pulse sensors on GPIO 32-35
**Framework:** Arduino (via PlatformIO CLI)
**Toolchain:** PlatformIO CLI

**Estimated Implementation Time:** 4-6 hours (code) + 2-3 hours (testing)

---

## Prerequisites

### Critical Prerequisites Checklist

⚠️ **CRITICAL: These steps MUST be completed in order**

```
Step 1: Complete Phase 1 (WiFi + OSC messaging with test values)
Step 2: Validate Phase 1 testing infrastructure works
Step 3: Implement this Phase 3 firmware (multi-sensor + beat detection)
Step 4: Test with multiple people/fingers simultaneously
```

Phase 1 WiFi and OSC infrastructure MUST be validated before expanding to sensors.

### 0.1 Phase 1 Completion

**MUST be completed before Phase 3:**
- ✅ WiFi connection stable and tested
- ✅ OSC messaging validated with Python receiver
- ✅ LED feedback working
- ✅ PlatformIO toolchain configured
- ✅ Test messages sent at 1 Hz successfully

**Verify Phase 1 working:**
```bash
# Start receiver
python3 osc_receiver.py --port 8000

# Upload Phase 1 firmware
cd /home/sderle/fw-phase-3/firmware/heartbeat_phase1
pio run --target upload && pio device monitor

# Expected: Messages received, LED solid after WiFi connect
```

### 0.2 Hardware Setup

**Pulse Sensors:**
- Type: Optical pulse sensors (12-bit ADC, 0-4095 range)
- Quantity: 4 sensors
- Connections:
  - Sensor 0: GPIO 32 (ADC1_CH4)
  - Sensor 1: GPIO 33 (ADC1_CH5)
  - Sensor 2: GPIO 34 (ADC1_CH6, input-only)
  - Sensor 3: GPIO 35 (ADC1_CH7, input-only)
- Power: 3.3V from ESP32 VCC
- Ground: Common ground with ESP32

**Important GPIO Notes:**
- GPIO 34-35 are input-only (no pullup/pulldown available)
- All sensors use ADC1 to avoid WiFi conflicts (ADC2 shares pins with WiFi)
- 12-bit resolution: 0-4095 ADC values

**Physical Setup:**
- Mount sensors accessible for fingers/wrists
- Label each sensor with ID (0-3)
- Ensure stable physical mounting (vibration affects readings)
- Shield from ambient light if possible

### 0.3 Testing Requirements

**Single-Person Testing:**
- One finger on one sensor at a time
- Validates per-sensor independence
- Confirms no false positives on idle sensors

**Multi-Person Testing:**
- 2-4 people, each on different sensor
- Validates crosstalk prevention
- Confirms independent state tracking
- Tests concurrent beat detection

---

## 1. Objective

Expand Phase 1 firmware to support 4 pulse sensors with real beat detection algorithm. Maintain WiFi/OSC infrastructure while adding analog sampling, signal processing, and adaptive threshold beat detection.

### Deliverables

- Single `main.cpp` implementing multi-sensor firmware
- 4 independent sensor channels with per-sensor state
- 50Hz sampling rate per sensor
- Moving average filter (5-sample window)
- Adaptive baseline tracking (exponential decay)
- Threshold-based beat detection with refractory period
- Real IBI values (no more test messages)
- LED indicates beats from ANY sensor
- Debug levels for production/testing/verbose

### Success Criteria

- All 4 sensors detect beats independently
- No crosstalk between sensors
- BPM accuracy ±5 BPM vs smartphone app
- Single-person test: Only active sensor sends messages
- Multi-person test: All active sensors send messages
- Latency: Beat to OSC message <25ms
- 30+ minute stability test passes

---

## 2. Architecture Overview

### 2.1 Execution Model

**Polling architecture with precise timing:**

- `setup()`: Initialize hardware, WiFi, sensors, UDP
- `loop()`:
  - Check if 20ms elapsed (50Hz per sensor)
  - Sample all 4 sensors
  - Process each sensor independently
  - Send OSC on beat detection
  - Update LED
  - Monitor WiFi status

**Timing:**
- Target: 20ms per sampling cycle (50Hz)
- Use `millis()` for non-blocking timing
- No interrupts or RTOS tasks (keep Phase 1 simplicity)

### 2.2 State Machine (Per Sensor)

```
INIT → FILLING_BUFFER → TRACKING → BEAT_DETECTED → TRACKING
                             ↓                         ↑
                        DISCONNECTED ←───────────────┘
```

**States:**
- `INIT`: First sample, initialize buffers
- `FILLING_BUFFER`: First 5 samples (until moving average valid)
- `TRACKING`: Normal operation, waiting for beat
- `BEAT_DETECTED`: Beat detected, send OSC, enter refractory
- `DISCONNECTED`: Flat signal or insufficient range

### 2.3 Data Flow

```
Analog Sensor (GPIO 32-35)
    ↓
analogRead() - Raw ADC value (0-4095)
    ↓
Moving Average Filter - 5-sample circular buffer
    ↓
Smoothed Value - Filtered signal
    ↓
Baseline Tracking - Adaptive min/max with decay
    ↓
Threshold Calculation - 60% of signal range
    ↓
Beat Detection - Rising edge + refractory check
    ↓
IBI Calculation - Time since last beat
    ↓
OSC Message - /heartbeat/N <ibi_ms>
    ↓
WiFiUDP → Server
```

---

## Related Documentation

- [Configuration & Data Structures](configuration.md) — Libraries, constants, and state
- [API Reference Index](index.md) — All function specifications
- [Implementation Guide](implementation.md) — Program flow and compilation
- [Operations & Testing](operations.md) — Validation procedures and troubleshooting

---

**Next Step:** Read [Configuration & Data Structures](configuration.md) for details on constants and state structures.
