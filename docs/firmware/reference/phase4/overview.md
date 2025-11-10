# Phase 4 Overview: Prerequisites, Objective, Architecture

## 0. Prerequisites

Before implementing Phase 4, validate that Phase 1 and Phase 3 are independently working.

### 0.1 Phase 1 Completion

Phase 1 provides WiFi connectivity and OSC message transmission infrastructure.

**MUST be validated before Phase 4:**
- ✅ WiFi connection stable (connects within 30 seconds)
- ✅ OSC message formatting correct (`/heartbeat/N <int32>`)
- ✅ Test messages (800-999ms) received by Python receiver
- ✅ LED feedback working (blink → solid)
- ✅ `sendHeartbeatOSC()` function proven reliable

**Verify Phase 1:**
```bash
cd /home/sderle/fw-phase-3/firmware/heartbeat_phase1
pio run --target upload && pio device monitor

# Should see:
# - WiFi connected
# - Messages sent at 1 Hz
# - Test IBI values 800-999ms
```

**Reference:** `docs/firmware/reference/phase1-firmware-trd.md`

### 0.2 Phase 3 Completion

Phase 3 provides multi-sensor beat detection algorithm.

**MUST be implemented and validated:**
- ✅ 4 sensors sampling at 50Hz
- ✅ Moving average filter (5-sample window)
- ✅ Adaptive baseline tracking
- ✅ Threshold-based beat detection
- ✅ IBI calculation per sensor
- ✅ Disconnection detection
- ✅ Independent per-sensor state

**Implementation Options:**

Phase 3 TRD exists (`docs/firmware/reference/phase3-firmware-trd.md`) but implementation directory may not exist yet. Agent has two options:

1. **Implement Phase 3 first (Sequential - Recommended)**
   - Follow Phase 3 TRD completely
   - Validate Phase 3 independently
   - Then proceed to Phase 4 integration

2. **Implement Phase 3 + Phase 4 together (Unified - Faster)**
   - Create `firmware/heartbeat_phase4/` directly
   - Implement both phases together
   - Follow both TRDs in parallel
   - Validate complete system end-to-end

**Reference:** `docs/firmware/reference/phase3-firmware-trd.md`

### 0.3 Testing Infrastructure

Validation requires specific tools and network setup.

**MUST be ready:**
- ✅ Python OSC receiver running on port 8000
- ✅ Development machine IP configured correctly
- ✅ 4 pulse sensors connected to GPIO 32-35
- ✅ Physical setup allows multiple people to test simultaneously

**Python Receiver Setup:**
See `docs/firmware/guides/phase1-05-validation.md` for complete receiver implementation.

---

## 1. Objective

Integrate Phase 3's real beat detection with Phase 1's OSC messaging infrastructure to complete the full data pipeline from pulse sensor to audio server. Validate end-to-end functionality and production readiness.

### Deliverables

- Single `main.cpp` combining Phase 3 beat detection + Phase 1 OSC messaging
- Real sensor-derived IBI values transmitted via OSC (no more test values)
- Complete validation that beats flow correctly to server
- Production-ready configuration (DEBUG_LEVEL 0)
- Documentation of integration points and testing procedures

### Success Criteria

**Functional Requirements:**
- Real beats from all 4 sensors transmitted via OSC
- OSC message format matches architecture spec
- BPM accuracy ±5 BPM vs smartphone reference
- Latency <25ms from beat detection to network transmission
- 30+ minute stability test passes
- Server-side validation confirms all messages valid

**Production Requirements:**
- Production mode (DEBUG_LEVEL 0) tested and validated
- WiFi resilience validated under sensor load
- Configuration documented and tested on-site
- Technician procedures documented

### Estimated Implementation Time

- **Integration:** 3-4 hours
- **Validation:** 3-4 hours
- **Total:** 6-8 hours

---

## 2. Architecture Overview

### 2.1 Integration Points

Phase 4 bridges two independently working systems into a complete pipeline.

**Data Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 3 (Implemented)                   │
│  Sensor → ADC → Moving Avg → Baseline → Beat Detection     │
│                                             ↓                │
│                                         IBI value           │
└─────────────────────────────────────────────────────────────┘
                                             ↓
                                    **INTEGRATION POINT**
                                             ↓
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 1 (Validated)                     │
│  sendHeartbeatOSC(sensorIndex, ibi_ms)                     │
│           ↓                                                  │
│  OSC Message → WiFiUDP → Network → Server                  │
└─────────────────────────────────────────────────────────────┘
```

**Key Integration Point:**
- Phase 3 `detectBeat()` calls `sendHeartbeatOSC(sensorIndex, ibi)` on beat detection
- Phase 1 `sendHeartbeatOSC()` formats OSC correctly and transmits
- **Phase 4 validates this integration works in production**

### 2.2 What Phase 4 Adds

**Technical changes (minimal):**
- Update `sendHeartbeatOSC()` signature to accept `sensorIndex` parameter
- Remove test message generation code from loop()
- Replace 1Hz timer with real-time beat detection triggers
- Validate LED feedback responds to real beats
- Add production configuration validation

**Primary focus:**
- **End-to-end testing** of complete data pipeline
- **Server-side validation** that messages are correct and timely
- **Production readiness** checks (stability, WiFi resilience, error handling)
- **Performance validation** (latency, throughput, reliability)

### 2.3 Execution Model

**Same as Phase 3, now with real OSC transmission:**

- `setup()`: Initialize hardware, WiFi, sensors, UDP
- `loop()` @ 50Hz:
  1. Sample all 4 sensors (ADC reads)
  2. Process each sensor (filter, baseline, threshold)
  3. Detect beats (rising edge + refractory check)
  4. **Immediately send OSC on beat detection** (Phase 1 infrastructure)
  5. Update LED (flash on any beat)
  6. Monitor WiFi status

**Timing Budget:**
- Target: 20ms per sampling cycle (50Hz per sensor)
- Beat detection: <1ms computational overhead
- OSC transmission: 1-5ms typical UDP send
- **Total latency budget: <25ms from beat to network**

### 2.4 Architecture References

**OSC Protocol (see architecture.md):**
- Address pattern: `/heartbeat/N` where N = 0-3
- Argument: single int32 (IBI in milliseconds)
- Transport: UDP, fire-and-forget
- No BPM calculation on ESP32 (server does this)

**Network Configuration (see architecture.md):**
- Fixed destination IP and port (configured at compile time)
- UDP socket, no discovery
- Packet size ~24 bytes (no fragmentation)

**Beat Detection (see architecture.md):**
- Adaptive threshold: 60% of signal range
- Refractory period: 300ms (max 200 BPM)
- First beat: no OSC sent (no reference point)
- Subsequent beats: IBI = time since last beat

---

## Next Steps

Proceed to [Configuration](./configuration.md) to understand:
- Code structure and file organization
- Configuration constants
- Integration requirements R1-R6

Then see [API Integration](./api-integration.md) for detailed integration specifications.
