# Operations: Testing, Troubleshooting & Success Metrics

---

## 10. Validation & Testing

### 10.1 Single-Sensor Smoke Test

**Purpose:** Validate one sensor independently

**Procedure:**
1. Upload firmware with DEBUG_LEVEL = 2
2. Place one finger on Sensor 0 (GPIO 32)
3. Monitor serial output

**Expected Output:**
```
=== Heartbeat Installation - Phase 3 ===
Multi-Sensor Beat Detection
Initialized sensor 0 on GPIO 32
Initialized sensor 1 on GPIO 33
Initialized sensor 2 on GPIO 34
Initialized sensor 3 on GPIO 35
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.1.42
Setup complete. Starting multi-sensor detection...

[0]=2456 [1]=2391 [2]=0 [3]=2678
[0]=2467 [1]=2401 [2]=0 [3]=2689
[0] First beat at 3421ms (no message sent)
[0]=2489 [1]=2423 [2]=0 [3]=2701
[0] Beat at 4287ms, IBI=866ms
[0]=2512 [1]=2445 [2]=0 [3]=2715
[0] Beat at 5156ms, IBI=869ms
```

**Validation:**
- ✅ Sensor 0 shows pulsing values (2400-2800 typical range)
- ✅ Sensors 1-3 show steady baseline (no finger)
- ✅ First beat detected, no message sent
- ✅ Subsequent beats send OSC with IBI
- ✅ IBI values reasonable (600-1200ms = 50-100 BPM)

### 10.2 Single-Person Multi-Sensor Test

**Purpose:** Validate sensor independence (one finger at a time)

**Procedure:**
1. DEBUG_LEVEL = 1 (testing)
2. Place finger on Sensor 0 for 10 seconds
3. Move to Sensor 1 for 10 seconds
4. Move to Sensor 2 for 10 seconds
5. Move to Sensor 3 for 10 seconds

**Expected Behavior:**
- Only active sensor sends messages
- Inactive sensors show no beats (no false positives)
- LED blinks on beats from any sensor
- Python receiver shows messages from one sensor at a time

**Validation:**
- ✅ No crosstalk (inactive sensors silent)
- ✅ Each sensor detects beats correctly
- ✅ BPM consistent across all sensors (±5 BPM)

### 10.3 Multi-Person Test

**Purpose:** Validate concurrent operation with 2-4 people

**Procedure:**
1. DEBUG_LEVEL = 1
2. 2-4 people each place finger on different sensor
3. Run for 5 minutes
4. Monitor Python receiver

**Expected Output (Receiver):**
```
[/heartbeat/0] IBI: 856ms, BPM: 70.1
[/heartbeat/2] IBI: 742ms, BPM: 80.9
[/heartbeat/1] IBI: 923ms, BPM: 65.0
[/heartbeat/0] IBI: 861ms, BPM: 69.7
[/heartbeat/3] IBI: 678ms, BPM: 88.5
[/heartbeat/2] IBI: 739ms, BPM: 81.2
```

**Validation:**
- ✅ All active sensors send messages
- ✅ Messages interleaved (independent timing)
- ✅ BPM values reasonable for all people
- ✅ No missed beats (no gaps > 2 seconds)
- ✅ LED blinks on beats from any sensor

### 10.4 Disconnection/Reconnection Test

**Purpose:** Validate disconnection detection

**Procedure:**
1. Finger on Sensor 0, wait for beats
2. Remove finger, wait 2 seconds
3. Reapply finger

**Expected Behavior:**
```
[0] Beat at 12847ms, IBI=856ms
[0] Beat at 13703ms, IBI=856ms
[0] Sensor disconnected
(no messages for 2 seconds)
[0] Sensor reconnected
[0] Beat at 16421ms, IBI=2718ms  // Large IBI = time since last beat
[0] Beat at 17289ms, IBI=868ms
```

**Validation:**
- ✅ Messages stop within 1 second of finger removal
- ✅ Messages resume within 3 seconds of finger reapplication
- ✅ First IBI after reconnect is large (accurate)
- ✅ Subsequent IBIs normal

### 10.5 Extended Duration Test

**Purpose:** Validate stability and memory safety

**Procedure:**
1. 2-4 people on sensors
2. Run for 30+ minutes
3. Monitor serial and receiver

**Validation:**
- ✅ No crashes or resets
- ✅ No WiFi disconnections (or auto-reconnects if drops)
- ✅ Consistent beat detection throughout
- ✅ No memory issues (fixed allocation, no leaks)
- ✅ LED continues to respond

### 10.6 BPM Accuracy Test

**Purpose:** Validate against smartphone reference

**Procedure:**
1. Install heart rate app on smartphone (e.g., "Instant Heart Rate")
2. Simultaneously measure:
   - Smartphone finger sensor
   - ESP32 sensor (same finger on different hand)
3. Compare BPM over 1 minute

**Validation:**
- ✅ BPM within ±5 BPM of smartphone
- ✅ Steady state BPM stable (not jumping wildly)

---

## 11. Acceptance Criteria

### 11.1 Compilation & Upload

**MUST:**
- ✅ Compile without errors
- ✅ Upload successfully
- ✅ Binary size < 500KB
- ✅ RAM usage < 10KB

### 11.2 Single-Sensor Operation

**MUST:**
- ✅ Detect beats within 3 seconds of finger application
- ✅ BPM accuracy ±5 BPM vs smartphone
- ✅ First beat: no message sent (correct behavior)
- ✅ Subsequent beats: IBI messages sent
- ✅ Disconnection detected within 1 second
- ✅ Reconnection detected within 3 seconds

### 11.3 Multi-Sensor Operation

**MUST:**
- ✅ All 4 sensors operate simultaneously
- ✅ No crosstalk (inactive sensors silent)
- ✅ Independent beat detection per sensor
- ✅ LED responds to beats from ANY sensor
- ✅ 2-4 person test successful

### 11.4 Reliability

**MUST:**
- ✅ 30+ minute stability test passes
- ✅ No crashes or watchdog resets
- ✅ WiFi resilience (auto-reconnect if drops)
- ✅ Consistent performance (no degradation)

### 11.5 Protocol Validation

**MUST:**
- ✅ OSC messages format correct: `/heartbeat/[0-3] <int32>`
- ✅ All messages received by Python receiver
- ✅ 0 invalid messages
- ✅ Latency <25ms (beat to network)

---

## 12. Known Limitations (Phase 3)

**Intentional Simplifications:**
- No waveform transmission (only IBI)
- No HRV analysis
- Fixed threshold fraction (not adaptive per user)
- No calibration UI
- No SD card logging
- No NTP time sync
- Single server destination
- No beat prediction

**Algorithm Limitations:**
- Moving average lag: 50ms
- Baseline adaptation: 3 second time constant
- Threshold may not be optimal for all users (tunable via constant)
- Sensitive to ambient light and movement

**Hardware Limitations:**
- 12-bit ADC (adequate but not clinical)
- GPIO 34-35 input-only (no pullup/pulldown)
- WiFi range ~30m from AP

**These are acceptable for festival installation. Future phases could address if needed.**

---

## 13. Troubleshooting

### 13.1 No Beats Detected

**Symptom:** Sensor connected, but no beats detected

**Debug Steps:**
1. Set DEBUG_LEVEL = 2
2. Check raw ADC values:
   - Should oscillate (e.g., 2400-2800)
   - If flat (constant value): Sensor disconnected or poor contact
3. Check baseline min/max:
   - Range should be > 50 ADC units
   - If < 50: Signal too weak
4. Check smoothed value crosses threshold

**Solutions:**
- Improve finger contact (press firmer)
- Shield from ambient light
- Adjust THRESHOLD_FRACTION (try 0.5 or 0.7)
- Increase MIN_SIGNAL_RANGE if noisy environment

### 13.2 False Beats / Double Triggers

**Symptom:** Too many beats, unrealistic BPM (>150)

**Debug Steps:**
1. Check if refractory period enforced (should see "ignored" if DEBUG_LEVEL 2)
2. Observe signal: High noise or vibration?

**Solutions:**
- Increase REFRACTORY_PERIOD_MS to 400ms
- Increase THRESHOLD_FRACTION to 0.7 (higher threshold)
- Stabilize physical mounting (reduce vibration)

### 13.3 Missed Beats

**Symptom:** Gaps > 2 seconds between beats

**Debug Steps:**
1. Check signal amplitude (min/max range)
2. Check if threshold too high

**Solutions:**
- Decrease THRESHOLD_FRACTION to 0.5
- Improve sensor contact
- Warm up hands (cold reduces signal)

### 13.4 Crosstalk Between Sensors

**Symptom:** Inactive sensors show beats

**Debug Steps:**
1. Verify each sensor has independent SensorState struct
2. Check sensorIndex passed correctly to all functions
3. Confirm no global variables shared between sensors

**Cause:** Likely bug in per-sensor state management

### 13.5 WiFi Issues

**Same as Phase 1 troubleshooting:**
- Connection timeout: Check SSID/password, 2.4GHz network
- Messages not received: Check SERVER_IP, firewall
- Disconnections: Check WiFi range, interference

---

## 14. Success Metrics

### 14.1 Phase 3 Complete

**All criteria MUST be met:**

1. ✅ Firmware compiles and uploads without errors
2. ✅ All 4 sensors initialized correctly
3. ✅ Single-sensor test: Beats detected, BPM accurate
4. ✅ Single-person multi-sensor test: No crosstalk
5. ✅ Multi-person test: All sensors operate independently
6. ✅ BPM accuracy ±5 BPM vs smartphone
7. ✅ Disconnection detection working (1 sec timeout)
8. ✅ Reconnection automatic (3 sec response)
9. ✅ LED feedback for beats from any sensor
10. ✅ 30-minute stability test passes
11. ✅ Python receiver validates all messages
12. ✅ Debug levels 0/1/2 all functional

### 14.2 Ready for Festival Deployment

Phase 3 complete, system ready for installation when:

- ✅ Multi-sensor operation validated
- ✅ Beat detection reliable
- ✅ No crosstalk confirmed
- ✅ Extended duration testing passed
- ✅ WiFi resilience tested
- ✅ LED feedback clear
- ✅ Code clean and commented
- ✅ DEBUG_LEVEL 0 tested (production mode)

**Next Steps:**
- Integrate with audio synthesis (server-side)
- Test full system with Pure Data patches
- Festival installation and validation

---

## Appendix: Sample Serial Output

### Level 0 (Production)
```
=== Heartbeat Installation - Phase 3 ===
Multi-Sensor Beat Detection
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.1.42
Setup complete. Starting multi-sensor detection...
```
(No further output during operation)

### Level 1 (Testing)
```
=== Heartbeat Installation - Phase 3 ===
Multi-Sensor Beat Detection
Initialized sensor 0 on GPIO 32
Initialized sensor 1 on GPIO 33
Initialized sensor 2 on GPIO 34
Initialized sensor 3 on GPIO 35
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.1.42
Setup complete. Starting multi-sensor detection...

[0] First beat at 3421ms (no message sent)
[1] First beat at 3856ms (no message sent)
[0] Beat at 4287ms, IBI=866ms
[2] First beat at 4501ms (no message sent)
[0] Beat at 5156ms, IBI=869ms
[1] Beat at 5234ms, IBI=1378ms
[2] Beat at 5389ms, IBI=888ms
[3] First beat at 5672ms (no message sent)
[0] Beat at 6021ms, IBI=865ms
[1] Beat at 6103ms, IBI=869ms
[2] Beat at 6278ms, IBI=889ms
[3] Beat at 6547ms, IBI=875ms
```

### Level 2 (Verbose Debug)
```
=== Heartbeat Installation - Phase 3 ===
Multi-Sensor Beat Detection
Initialized sensor 0 on GPIO 32
Initialized sensor 1 on GPIO 33
Initialized sensor 2 on GPIO 34
Initialized sensor 3 on GPIO 35
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.1.42
Setup complete. Starting multi-sensor detection...

[0]=2456 [1]=2391 [2]=0 [3]=2678
[0]=2467 [1]=2401 [2]=0 [3]=2689
[0]=2489 [1]=2423 [2]=0 [3]=2701
[0]=2512 [1]=2445 [2]=0 [3]=2715
[0] min=2200 max=2800 thresh=2560
[0]=2534 [1]=2467 [2]=0 [3]=2728
[0] BEAT at 3421ms, IBI=0ms (first, not sent)
[0]=2556 [1]=2489 [2]=0 [3]=2741
[0]=2578 [1]=2511 [2]=0 [3]=2754
[1] min=2100 max=2700 thresh=2460
[1] BEAT at 3856ms, IBI=0ms (first, not sent)
[0]=2545 [1]=2489 [2]=0 [3]=2767
[0]=2523 [1]=2467 [2]=0 [3]=2780
[0] BEAT at 4287ms, IBI=866ms
Sent OSC: /heartbeat/0 866
```

---

## Related Documentation

- [Implementation](implementation.md) — Program flow and compilation
- [API Reference Index](index.md) — All functions and specifications
- [Configuration](configuration.md) — Constants for tuning

---

**Status:** Ready for implementation and testing
**Estimated Time:** 4-6 hours (code) + 2-3 hours (testing)
**Next Phase:** Phase 4 - Audio synthesis integration
