# Operations & Testing

## 10. Validation & Testing

### 10.1 Prerequisites (Phase 2 Specific)

**MUST have:**
- ✅ Phase 1 firmware tested and working
- ✅ PulseSensor physically connected to GPIO 32
- ✅ Python OSC receiver running
- ✅ Smartphone heart rate app for BPM validation

### 10.2 Validation Procedure

**Step 1: Start Receiver**
```bash
python3 osc_receiver.py --port 8000
```

**Step 2: Upload Phase 2 Firmware**
```bash
pio run --target upload && pio device monitor
```

**Step 3: Verify Startup**
Expected serial output:
```
=== Heartbeat Installation - Phase 2 ===
Real Heartbeat Detection
Sensor ID: 0
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.50.42
First ADC reading: 2456
Sensor initialized. Ready for heartbeat detection.
Setup complete. Place finger on sensor to begin.
```

**Step 4: Apply Finger to Sensor**
- Place fingertip on PulseSensor (cover LED completely)
- Apply gentle, steady pressure
- Hold still for 10 seconds

**Expected Serial Output:**
```
First beat detected
Beat detected, IBI=847ms, BPM=70
Beat detected, IBI=856ms, BPM=70
Beat detected, IBI=843ms, BPM=71
...
```

**Expected Receiver Output:**
```
[/heartbeat/0] IBI: 847ms, BPM: 70.8
[/heartbeat/0] IBI: 856ms, BPM: 70.1
[/heartbeat/0] IBI: 843ms, BPM: 71.2
...
```

**Step 5: Validate LED Behavior**
- Before finger applied: Solid ON (WiFi connected)
- After beats start: Brief flicker on each beat (50ms pulse)

**Step 6: Test Disconnection**
- Remove finger from sensor
- Expected serial output within 1 second:
  ```
  Sensor disconnected
  ```
- Expected receiver: No more messages
- LED stays solid ON (WiFi still connected)

**Step 7: Test Reconnection**
- Reapply finger to sensor
- Expected serial output within 3 seconds:
  ```
  Sensor reconnected
  First beat detected
  Beat detected, IBI=XXXms, BPM=XX
  ```
- Expected receiver: Messages resume

**Step 8: BPM Accuracy Check**
- Use smartphone heart rate app simultaneously
- Compare app BPM to serial output BPM
- Acceptable: ±5 BPM difference
- If outside range: Tune `THRESHOLD_FRACTION` (see Section 11)

**Step 9: Extended Run (30 Minutes)**
- Keep finger on sensor
- Monitor serial output and receiver
- Check for:
  - ✅ No crashes or resets
  - ✅ Consistent BPM (±10 BPM variation normal)
  - ✅ No WiFi disconnections
  - ✅ No memory issues

### 10.3 Multi-Unit Testing (Phase 2)

**Requirements:**
- Program 2-4 ESP32s with Phase 2 firmware
- Each unit has unique SENSOR_ID (0, 1, 2, 3)
- All units connected to same WiFi network

**Test Procedure:**
1. Start single Python receiver
2. Power all ESP32s simultaneously
3. Apply different fingers to each sensor
4. Verify receiver shows messages from all sensor IDs
5. Verify each sensor has independent BPM
6. Remove one finger, verify only that sensor stops sending

**Expected Result:**
- 4 independent heartbeat streams
- No interference between sensors
- Different BPM values per person

---

## 11. Tuning & Optimization

### 11.1 Threshold Tuning

**Symptom: Missed Beats (gaps > 2 seconds)**
- Cause: Threshold too high for weak signals
- Solution: Reduce `THRESHOLD_FRACTION` from 0.6 to 0.5
- Test incrementally: 0.6 → 0.55 → 0.5

**Symptom: False Beats (BPM > 120 at rest)**
- Cause: Threshold too low, noise triggers beats
- Solution: Increase `THRESHOLD_FRACTION` from 0.6 to 0.7
- Test incrementally: 0.6 → 0.65 → 0.7

**Symptom: BPM Incorrect (±10+ BPM vs phone app)**
- Cause: Poor sensor contact or movement
- Solution: Improve physical sensor placement, hold still

### 11.2 Debug Output Levels

**Level 0: Production (Default)**
```cpp
// In detectBeat(), keep only beat messages
Serial.print("Beat detected, IBI=");
Serial.println(ibi);
```

**Level 1: Detailed Debug (Enable for Tuning)**
```cpp
// In loop(), every 1 second:
if (state.loopCounter % 50 == 0) {
    Serial.print("Smoothed: ");
    Serial.print(sensor.smoothedValue);
    Serial.print(" Min: ");
    Serial.print(sensor.minValue);
    Serial.print(" Max: ");
    Serial.print(sensor.maxValue);
    Serial.print(" Threshold: ");
    Serial.println(sensor.minValue + (int)((sensor.maxValue - sensor.minValue) * THRESHOLD_FRACTION));
}
```

**Level 2: Raw Data (Enable for Hardware Debug)**
```cpp
// In loop(), every sample:
Serial.print("Raw: ");
Serial.print(rawValue);
Serial.print(" Smoothed: ");
Serial.println(sensor.smoothedValue);
```

**Warning:** Level 2 generates 50 lines/second and can overflow the serial buffer if run continuously. Recommend using only for short diagnostic tests (< 10 seconds).

### 11.3 Parameter Recommendations

**Conservative (fewer false beats, may miss weak beats):**
```cpp
const float THRESHOLD_FRACTION = 0.7;
const int MIN_SIGNAL_RANGE = 80;
const unsigned long REFRACTORY_PERIOD_MS = 350;
```

**Sensitive (catches weak beats, may have false triggers):**
```cpp
const float THRESHOLD_FRACTION = 0.5;
const int MIN_SIGNAL_RANGE = 30;
const unsigned long REFRACTORY_PERIOD_MS = 250;
```

**Default (balanced, works for most users):**
```cpp
const float THRESHOLD_FRACTION = 0.6;
const int MIN_SIGNAL_RANGE = 50;
const unsigned long REFRACTORY_PERIOD_MS = 300;
```

---

## 12. Acceptance Criteria

### 12.1 Compilation

**MUST:**
- ✅ Compile without errors
- ✅ Compile without warnings (or only benign warnings)
- ✅ Binary size < 550KB (reasonable headroom)

### 12.2 Runtime Behavior

**MUST:**
- ✅ Connect to WiFi within 30 seconds
- ✅ Initialize sensor successfully
- ✅ Detect heartbeats within 3 seconds of finger application
- ✅ BPM accuracy within ±5 BPM vs smartphone app
- ✅ OSC messages contain real IBI values (not test values)
- ✅ Python receiver validates all messages (0 invalid)
- ✅ Run for 30+ minutes without crashes
- ✅ LED indicates WiFi connection and beat pulses

### 12.3 Signal Processing

**MUST:**
- ✅ Moving average smooths noisy signals
- ✅ Baseline adapts to different signal amplitudes
- ✅ No false beats from noise
- ✅ No missed beats from weak signals (with proper tuning)
- ✅ Refractory period prevents double-triggers

### 12.4 Disconnection Handling

**MUST:**
- ✅ Detect sensor removal within 1 second
- ✅ Stop sending OSC messages when disconnected
- ✅ Auto-reconnect within 3 seconds of reapplication
- ✅ Resume beat detection after reconnection
- ✅ No crashes when sensor removed/reapplied

### 12.5 Multi-Unit Operation

**MUST:**
- ✅ 4 units operate simultaneously without interference
- ✅ Each unit sends independent heartbeat data
- ✅ Receiver distinguishes all sensor IDs correctly
- ✅ No network congestion (4 sensors × 60-120 BPM = 240-480 msg/min total)

---

## 13. Known Limitations (Phase 2)

**Carried Over from Phase 1:**
- No watchdog timer (will add in Phase 3)
- No sophisticated LED feedback (just on/pulse)
- No power management
- No OTA updates
- No configuration web interface

**Phase 2 Specific:**
- Single sensor only (GPIO 32) - Phase 3 will add 4 sensors
- Fixed threshold fraction (not auto-adaptive per user)
- No waveform transmission (only IBI)
- No HRV analysis
- Optical sensor sensitive to ambient light, movement, cold hands

**These will be addressed in later phases.**

---

## 14. Troubleshooting

### 14.1 Sensor Issues

**No ADC readings (values stuck at 0 or 4095)**
- Check wiring: Signal to GPIO 32, VCC to 3.3V, GND to GND
- Verify PulseSensor LED is on (indicates power)
- Test with multimeter: Signal pin should vary 1-3V when finger applied

**ADC readings constant (no variation)**
- Sensor not detecting pulse
- Try different finger (index or middle finger best)
- Apply more/less pressure
- Cover sensor LED completely (block ambient light)
- Check sensor LED facing outward (detects reflected light)

**Erratic readings (wild fluctuations)**
- Loose jumper wire connection
- Re-seat all 3 connections
- Check for broken wire
- Move cables away from power wires (reduce EMI)

### 14.2 Beat Detection Issues

**No beats detected (ADC working, no "Beat detected" messages)**
- Enable debug output (Level 1) to see threshold values
- Check signal range: Should be > 50 ADC units when finger applied
- If range < 50: Adjust finger pressure, try different finger
- If range > 50 but no beats: Lower `THRESHOLD_FRACTION` to 0.5

**False beats (BPM > 150 at rest)**
- Threshold too low
- Increase `THRESHOLD_FRACTION` to 0.7
- Check for movement (hold finger very still)
- Increase `MIN_SIGNAL_RANGE` to 80

**Missed beats (gaps > 2 seconds)**
- Threshold too high for weak signals
- Decrease `THRESHOLD_FRACTION` to 0.5
- Improve sensor contact (more pressure)
- Check sensor not covered by external light (cover with hand)

**BPM incorrect (±10+ BPM difference)**
- Poor sensor contact
- Movement during measurement
- Compare to multiple phone apps (some apps inaccurate)
- Try different finger
- Ensure sensor LED fully covered

### 14.3 Disconnection Issues

**"Sensor disconnected" immediately after startup**
- No finger on sensor (expected behavior)
- Sensor not actually connected (check wiring)

**"Sensor disconnected" while finger applied**
- Sensor signal too weak (range < 50)
- Increase finger pressure
- Try different finger
- Check sensor power (LED should be bright)

**"Sensor reconnected" flapping (rapid connect/disconnect)**
- Borderline signal quality
- Increase `MIN_SIGNAL_RANGE` to 80 (more stable threshold)
- Improve sensor contact

### 14.4 Performance Issues

**Loop running slow (sample rate < 50 Hz)**
- Too much serial output (disable Level 2 debug)
- WiFi congestion (check router)
- Reduce serial baud rate (unlikely with 115200)

**Memory issues (crashes after long runtime)**
- Check for memory leaks with serial output
- Monitor free heap: `Serial.println(ESP.getFreeHeap())`
- Should be stable (no fixed-size data structures should leak)

---

## 15. Success Metrics

### 15.1 Phase 2 Firmware Complete

**All criteria MUST be met:**

1. ✅ Firmware compiles without errors
2. ✅ Uploads to ESP32 successfully
3. ✅ WiFi connection stable (Phase 1 functionality maintained)
4. ✅ ADC sampling at 50 Hz
5. ✅ Moving average filter working
6. ✅ Baseline tracking adapts to signal
7. ✅ Beats detected within 3 seconds of finger application
8. ✅ BPM accuracy ±5 BPM vs smartphone app
9. ✅ OSC messages contain real IBI values
10. ✅ Python receiver validates all messages
11. ✅ Sensor disconnection detected within 1 second
12. ✅ Auto-reconnection working
13. ✅ 30-minute stability test passes
14. ✅ Multi-unit test passes (2+ ESP32s simultaneously)
15. ✅ Code organized and commented

### 15.2 Ready for Phase 3

Phase 2 complete, proceed to Phase 3 when:

- ✅ Single sensor heartbeat detection reliable
- ✅ Signal processing algorithm tuned
- ✅ Disconnection handling robust
- ✅ BPM accuracy validated
- ✅ OSC messaging proven with real data
- ✅ Code structure ready to add 3 more sensors

**Phase 3 Preview:** Will add 3 more sensors (GPIO 33, 34, 35), independent state tracking per sensor, concurrent beat detection on all 4 channels, and multi-sensor OSC transmission.

---

## Related Documentation

- **[Overview](overview.md)** - Phase 2 objectives
- **[Configuration](configuration.md)** - Parameter tuning
- **[Implementation](implementation.md)** - Code structure
- **[API Functions](api-sensors.md)** - Individual function reference

---

## Testing Checklist

Use this checklist to validate Phase 2 implementation:

- [ ] Phase 1 verified working first
- [ ] PulseSensor connected to GPIO 32
- [ ] Python receiver configured on port 8000
- [ ] Firmware compiles without errors
- [ ] Firmware uploads to ESP32
- [ ] Startup messages appear on serial
- [ ] ADC readings visible in debug output
- [ ] Finger application triggers beats
- [ ] Serial output shows real BPM values
- [ ] Receiver shows OSC messages with real IBI
- [ ] BPM accuracy ±5 BPM vs smartphone app
- [ ] LED solid when connected
- [ ] LED pulses on beats
- [ ] Sensor disconnection detected
- [ ] Sensor reconnection detected
- [ ] 30-minute stability test passes
- [ ] Multi-unit test passes
- [ ] No compile warnings
- [ ] No runtime errors or crashes
- [ ] Ready for Phase 3

*End of Operations Guide*
