# Phase 2 Overview

**Version:** 1.0
**Date:** 2025-11-09
**Purpose:** Define ESP32 firmware requirements for ADC sampling, signal processing, beat detection, and real heartbeat OSC transmission

## 0. Prerequisites

### 0.1 Phase 1 Completion

**MUST have completed:**
- ✅ Phase 1 firmware uploaded and running
- ✅ WiFi connection stable
- ✅ OSC messages successfully transmitted to server
- ✅ Python OSC receiver validates message format
- ✅ 5-minute stability test passed

**Verify Phase 1 working:**
```bash
# Terminal 1: Start receiver
python3 osc_receiver.py --port 8000

# Terminal 2: Monitor ESP32 serial output
pio device monitor

# Should see test messages flowing at 1 Hz
```

### 0.2 Hardware Setup

**MUST complete before coding:**

**Step 1: Connect PulseSensor**
```
PulseSensor:
  Signal wire (purple/white) → ESP32 GPIO 32 (ADC1_CH4)
  VCC wire (red) → ESP32 3.3V
  GND wire (black) → ESP32 GND
```

**Step 2: Verify Sensor Connection**
```cpp
// Test code to verify sensor connected:
void setup() {
    Serial.begin(115200);
    pinMode(32, INPUT);
}
void loop() {
    int raw = analogRead(32);
    Serial.println(raw);
    delay(100);
}
// Expected: Values change 2000-3000 range when finger applied
//           Values ~0 or constant when no finger
```

**Step 3: Physical Setup**
- PulseSensor should be secured (tape or mounting bracket)
- Sensor LED should face outward (detects reflected light)
- Cable connections should be stable (no loose jumper wires)

---

## 1. Objective

Implement ESP32 firmware that reads analog sensor data, detects heartbeats using adaptive threshold algorithm, calculates inter-beat intervals, and transmits real heartbeat timing via OSC. Replaces Phase 1 test values with actual physiological data.

### Deliverables

- Single `main.cpp` source file (builds on Phase 1 structure)
- ADC sampling at 50 Hz per sensor
- Moving average filter for noise reduction
- Adaptive baseline tracking (handles varying signal amplitude)
- Beat detection with refractory period
- Real IBI calculation and OSC transmission
- Sensor disconnection detection
- Validated against real heartbeat data

### Success Criteria

- Firmware uploads to ESP32 without errors
- Detects heartbeats within 3 seconds of finger application
- BPM accuracy within ±5 BPM vs smartphone app
- Runs for 30+ minutes without crashes
- Handles sensor disconnect/reconnect gracefully
- OSC messages contain real IBI data (not test values)

---

## 2. Architecture Overview

### 2.1 Execution Model

**Single-threaded non-blocking architecture (same as Phase 1):**
- `setup()`: Initialize hardware, WiFi (reuse Phase 1), configure ADC, initialize sensor state
- `loop()`: Sample sensors at 50Hz, process signal, detect beats, send OSC, update LED
- No RTOS tasks, no interrupts (keep Phase 1 simplicity)

**Timing:**
- Phase 1: 1000ms test message interval → **Phase 2: 20ms ADC sample interval (50Hz)**
- Use `millis()` for non-blocking timing (same as Phase 1)
- Main loop cycles every ~20ms (vs Phase 1 10ms)

### 2.2 Data Flow

```
ADC Sample (50Hz) → Moving Average Filter → Baseline Tracking →
Beat Detection (threshold + refractory) → IBI Calculation → OSC Transmission
```

### 2.3 State Machine (Phase 2 Extension)

```
STARTUP → WIFI_CONNECTING → WIFI_CONNECTED → SENSOR_INIT → RUNNING
                ↓                                              ↓
           ERROR_HALT                                  SENSOR_DISCONNECTED
                                                               ↓
                                                        (auto-reconnect)
```

**New States:**
- `SENSOR_INIT`: First ADC reading, initialize moving average buffer
- `SENSOR_DISCONNECTED`: Flat signal detected, stop sending OSC
- `RUNNING`: Normal operation with beat detection

---

## Related Documentation

- **[Configuration](configuration.md)** - Libraries, constants, and data structures
- **[Implementation](implementation.md)** - Program flow and code structure
- **[Operations](operations.md)** - Testing and troubleshooting

---

## Estimated Timeline

- **Code implementation:** 3-4 hours
- **Testing and tuning:** 2 hours
- **Total:** 5-6 hours
