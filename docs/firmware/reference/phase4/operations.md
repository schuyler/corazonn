# Phase 4 Operations: Production, Troubleshooting, Deployment

## 5. Production Configuration

### 5.1 Production Settings

Before festival deployment, configure these constants in `main.cpp`:

**Network Configuration (MUST change for your environment):**
```cpp
// Network - CHANGE THESE FOR DEPLOYMENT
const char* WIFI_SSID = "festival-network";      // Festival WiFi SSID
const char* WIFI_PASSWORD = "secure-password";   // Password from organizers
const IPAddress SERVER_IP(192, 168, 1, 100);    // Audio server IP (VERIFY)
const uint16_t SERVER_PORT = 8000;               // OSC port
```

**Debug Level (PRODUCTION MODE):**
```cpp
#define DEBUG_LEVEL 0  // Minimal serial output for production
```

**Signal Processing Tuning (adjust if needed after testing):**
```cpp
const float THRESHOLD_FRACTION = 0.6;   // May need adjustment per installation
const int MIN_SIGNAL_RANGE = 50;        // Noise floor depends on environment
```

### 5.2 Production Validation Checklist

Before deploying to festival, validate all items:

**Hardware Setup:**
- [ ] All 4 sensors mounted securely
- [ ] ESP32 powered reliably (USB or external 5V)
- [ ] Pulse sensors labeled 0-3 clearly (for technician reference)
- [ ] WiFi antenna not obstructed
- [ ] Status LED visible to technicians
- [ ] Cables and connections protected from water/damage

**Configuration Validation:**
- [ ] WiFi credentials correct (tested on-site with actual network)
- [ ] Server IP correct (verified with ping from ESP32 network)
- [ ] DEBUG_LEVEL = 0 (production mode, no debug output)
- [ ] Threshold tuned for installation environment (via testing phase)
- [ ] Sensors respond consistently to all test subjects

**Testing Completed:**
- [ ] Single-sensor test successful
- [ ] 4-person concurrent test successful (all sensors working)
- [ ] 30+ minute stability test passed (no crashes)
- [ ] WiFi resilience validated
- [ ] BPM accuracy acceptable (±5 BPM)
- [ ] Server receives and processes all messages correctly
- [ ] Audio synthesis responds correctly to beat messages

**Documentation:**
- [ ] Sensor-to-person mapping documented
- [ ] WiFi network details recorded securely
- [ ] Server IP and port documented
- [ ] Troubleshooting guide available on-site
- [ ] Emergency reset procedure documented
- [ ] Backup ESP32 units programmed and ready

### 5.3 Production Serial Output

**DEBUG_LEVEL = 0 (Production Mode):**

ESP32 produces minimal output:
```
=== Heartbeat Installation - Phase 4 ===
OSC Integration & Production Validation
Connecting to WiFi: festival-network
Connected! IP: 192.168.1.42
Setup complete. Starting beat detection...
```

No further output unless errors occur. Benefits:
- Minimal serial buffer usage
- No performance overhead from logging
- Clean monitor output for technicians
- Errors still visible if they occur

**DEBUG_LEVEL = 1 (Testing Mode for troubleshooting):**

If issues occur during festival:
```
[0] Beat at 12847ms, IBI=867ms
[2] Beat at 13021ms, IBI=742ms
[1] Beat at 13198ms, IBI=923ms
WiFi disconnected, reconnecting...
```

Switch to Level 1 if issues occur during festival, back to Level 0 when stable.

---

## 6. Acceptance Criteria

### 6.1 Phase 4 Complete

All of these criteria MUST be met before acceptance:

**Integration Requirements:**
- ✅ Phase 3 beat detection + Phase 1 OSC messaging integrated
- ✅ Real sensor IBIs transmitted (no test values)
- ✅ `sendHeartbeatOSC()` called on every beat detection
- ✅ LED responds to real beats (not timer-based)

**Functional Requirements:**
- ✅ All 4 sensors detect beats independently
- ✅ OSC messages format correct: `/heartbeat/[0-3] <int32>`
- ✅ BPM accuracy ±5 BPM vs smartphone reference
- ✅ First beat detection: no OSC sent (correct behavior)
- ✅ Subsequent beats: IBI calculated and sent correctly
- ✅ Disconnection detection working (<1 sec response)
- ✅ Reconnection automatic (<3 sec resume)

**Performance Requirements:**
- ✅ Latency <25ms (95th percentile, beat to network)
- ✅ 30+ minute stability test passes
- ✅ No crashes, resets, or memory issues
- ✅ WiFi auto-reconnect validated
- ✅ Consistent performance (no degradation)

**Validation Requirements:**
- ✅ Single-sensor test successful
- ✅ Multi-sensor test successful (2-4 people)
- ✅ Python receiver validates all messages
- ✅ Zero invalid OSC messages
- ✅ Zero packet loss (<1% acceptable)
- ✅ Server-side processing working

**Production Requirements:**
- ✅ DEBUG_LEVEL 0 tested (production mode)
- ✅ Configuration documented
- ✅ On-site WiFi validated
- ✅ 4-person end-to-end test passed
- ✅ Emergency procedures documented

### 6.2 Ready for Festival Deployment

System is production-ready when all items verified:

- ✅ Complete data pipeline validated (sensor → ESP32 → network → server → audio)
- ✅ Multi-person testing successful (4 simultaneous users)
- ✅ Extended duration test passed (60+ minutes)
- ✅ On-site WiFi tested and stable
- ✅ Audio synthesis responds correctly to heartbeat messages
- ✅ Technicians trained on system monitoring and troubleshooting
- ✅ Troubleshooting procedures documented and tested
- ✅ Backup ESP32 units programmed and ready
- ✅ Power supply reliable and tested
- ✅ Physical installation secure and accessible

---

## 7. Known Limitations

### 7.1 Intentional Simplifications

Not implemented in Phase 4 (acceptable for art installation):
- No waveform transmission (only IBI intervals)
- No HRV (heart rate variability) analysis
- No beat prediction or anticipation
- No multi-server broadcasting
- No onboard BPM calculation (server does this)
- No quality metrics per beat (SNR, confidence)
- No NTP time synchronization
- No SD card logging
- No web-based configuration interface
- No OTA (over-the-air) firmware updates

These could be added in future versions if needed, but not required for festival.

### 7.2 Environmental Limitations

System performance affected by:

**Ambient Light:**
- Optical sensors sensitive to bright light
- Mitigation: Shield sensors if possible

**Cold Hands:**
- Reduced peripheral blood flow affects signal quality
- Mitigation: Ask participants to warm up before use

**Movement:**
- Large motions create artifacts
- Mitigation: Ask participants to keep hands relatively still

**WiFi Congestion:**
- Festival WiFi with many users may cause intermittent dropouts
- Mitigation: Use dedicated network for heartbeat system if possible

**Distance:**
- ESP32 WiFi range ~30m from access point
- Mitigation: Position router centrally in installation area

### 7.3 Algorithm Limitations

**Beat Detection Algorithm:**
- **Fixed threshold fraction:** May not be optimal for all users (tunable constant THRESHOLD_FRACTION)
- **Moving average lag:** 50ms delay in signal (acceptable for this application)
- **Baseline adaptation:** 3-second time constant (may miss very rapid amplitude changes)
- **Refractory period:** Enforces max 200 BPM (protects against false triggers)

These are acceptable tradeoffs for real-time beat detection in art installation.

### 7.4 Protocol Limitations

**UDP OSC Transmission:**
- **No acknowledgment:** ESP32 doesn't know if server received message
- **No packet ordering:** Messages may arrive out of order (rare on local WiFi)
- **No automatic discovery:** Server IP must be configured manually
- **Fire-and-forget:** Lost packets not retransmitted

Acceptable because:
- Occasional dropped beat event is not critical (next beat arrives soon)
- Local WiFi has very low packet loss (<0.1% typical)
- Server handles out-of-order messages correctly (timestamps available)
- Simplicity and low latency more important than guaranteed delivery

---

## 8. Troubleshooting

### 8.1 Integration Issues

**Symptom: Beats detected but no OSC messages**

Debug steps:
1. Set DEBUG_LEVEL = 2
2. Check serial output for "OSC sent:" messages
3. Verify `sendHeartbeatOSC()` is being called

Possible causes:
- `sendHeartbeatOSC()` not called in `detectBeat()`
- Function signature mismatch (missing sensorIndex parameter)
- WiFi disconnected (check `wifiConnected` state)

Solution:
```cpp
// In detectBeat(), verify this code exists:
if (sensors[sensorIndex].firstBeatDetected) {
    sendHeartbeatOSC(sensorIndex, (int)ibi);  // Must have both parameters
    system.beatDetectedThisLoop = true;
}
```

### 8.2 OSC Format Issues

**Symptom: Python receiver shows "Invalid OSC message"**

Debug steps:
1. Use Wireshark to capture raw UDP packets
2. Check OSC message binary format
3. Verify type tag is `,i` (int32)

Possible causes:
- Wrong argument type (e.g., float instead of int32)
- Missing null termination in address string
- Incorrect `msg.send()` sequence

Solution:
```cpp
// Verify exact sequence:
OSCMessage msg(oscAddress);
msg.add((int32_t)ibi_ms);  // Cast to int32_t explicitly
udp.beginPacket(SERVER_IP, SERVER_PORT);
msg.send(udp);
udp.endPacket();
msg.empty();  // Don't forget this
```

### 8.3 High Latency

**Symptom: Latency >50ms consistently**

Debug steps:
1. Measure latency with DEBUG_LEVEL = 2 timestamps
2. Check WiFi signal strength (`WiFi.RSSI()`)
3. Monitor network with ping tests

Possible causes:
- WiFi congestion or interference
- Router overloaded
- Network path through multiple hops
- ESP32 too far from router

Solutions:
- Move ESP32 closer to router
- Use 2.4GHz channel with less interference
- Dedicate router to heartbeat system if possible
- Increase WiFi transmit power if supported

### 8.4 Packet Loss

**Symptom: Python receiver missing messages (>1% loss)**

Debug steps:
1. Count beats in serial output (DEBUG_LEVEL = 1)
2. Count messages in Python receiver
3. Compare counts after 5 minutes

Possible causes:
- WiFi signal weak
- Network congestion
- Receiver buffer overflow
- Firewall dropping UDP packets

Solutions:
- Improve WiFi signal strength
- Reduce competing WiFi traffic
- Check firewall rules on server
- Use dedicated network if possible

### 8.5 BPM Inaccuracy

**Symptom: BPM differs by >5 BPM from smartphone reference**

Debug steps:
1. Set DEBUG_LEVEL = 2
2. Check raw ADC values (should oscillate)
3. Check baseline min/max (should track signal)
4. Check threshold crossing events

Possible causes:
- THRESHOLD_FRACTION too high or too low
- Sensor contact poor
- Ambient light interference
- Movement artifacts

Solutions:
- Adjust THRESHOLD_FRACTION (try 0.5-0.7 range)
- Improve finger contact (press firmer on sensor)
- Shield sensors from ambient light
- Ask participant to stay relatively still

---

## 9. Next Steps After Phase 4

### 9.1 Server-Side Integration

After Phase 4 firmware is validated, integrate with audio server:

**Pure Data OSC Receiver:**
- Implement OSC listener on port 8000
- Parse `/heartbeat/[0-3]` messages
- Extract IBI int32 values
- Map to audio synthesis parameters

**Audio Synthesis:**
- Convert IBI to BPM: `60000 / ibi_ms`
- Map BPM to audio parameters (pitch, rhythm, amplitude)
- Synchronize audio with beat events
- Handle 4 independent audio channels (one per sensor)

**Lighting Control (Optional):**
- Send beat events to lighting system
- Synchronize lights with heartbeats
- Map sensor positions to light fixtures

### 9.2 On-Site Installation Testing

Before festival opening, validate on actual hardware:

**Network Setup:**
- Configure festival WiFi credentials
- Test ESP32 connects reliably
- Measure WiFi signal strength at installation
- Verify server reachable from ESP32 network

**Multi-Person Test:**
- 4 volunteers test all sensors simultaneously
- Run for 15+ minutes
- Validate audio synthesis responds correctly
- Check for crosstalk or interference

**Environmental Adaptation:**
- Test in actual lighting conditions
- Adjust THRESHOLD_FRACTION if needed
- Test with various skin tones and hand temperatures
- Document any tuning changes

**Technician Training:**
- Show how to monitor system status (LED, serial)
- Demonstrate reset procedure
- Explain common issues and solutions
- Provide troubleshooting checklist

### 9.3 Monitoring and Maintenance

**Continuous Monitoring During Festival:**
- Server logs all OSC messages with timestamps
- Track packet loss and latency metrics
- Alert on sustained WiFi disconnections
- Monitor sensor health (beats per minute)

**Daily Checks:**
- Verify all 4 sensors responding
- Check WiFi connection stable
- Test audio synthesis working
- Inspect physical hardware (connections, mounting)

**Backup Procedures:**
- Keep backup ESP32 programmed and ready
- Document quick replacement procedure
- Maintain spare pulse sensors
- Keep WiFi credentials accessible

---

## 10. Document References

### 10.1 Related Documents in This Repository

**Architecture:**
- `docs/firmware/reference/architecture.md` - Overall system design, OSC protocol specification

**Previous Phases:**
- `docs/firmware/reference/phase1-firmware-trd.md` - WiFi + OSC infrastructure
- `docs/firmware/reference/phase3-firmware-trd.md` - Multi-sensor beat detection

**Testing:**
- `firmware/heartbeat_phase1/TEST_SUITE_GUIDE.md` - Phase 1 validation procedures
- `docs/firmware/guides/phase1-05-validation.md` - Python OSC receiver setup

**Implementation Reference:**
- `firmware/heartbeat_phase1/src/main.cpp` - Phase 1 reference code
- `firmware/heartbeat_phase4/src/main.cpp` - Phase 4 integrated code (to be created)

### 10.2 Key Architecture References

**OSC Protocol (from architecture.md):**
- Address pattern: `/heartbeat/N` where N = 0-3
- Argument: single int32 (IBI in milliseconds)
- Transport: UDP, fire-and-forget
- No BPM calculation on ESP32 (server does this)

**Network Configuration (from architecture.md):**
- Fixed destination IP and port (configured at compile time)
- UDP socket, no discovery mechanism
- Packet size ~24 bytes (no fragmentation)

**Beat Detection (from architecture.md):**
- Adaptive threshold: 60% of signal range
- Refractory period: 300ms (max 200 BPM)
- First beat: no OSC sent (no reference point)
- Subsequent beats: IBI = time since last beat

---

## 11. Success Metrics Summary

### 11.1 Technical Metrics

| Metric | Target | Test Method | Required |
|--------|--------|-------------|----------|
| OSC format correctness | 100% valid | Python receiver validation | ✅ |
| BPM accuracy | ±5 BPM | vs smartphone reference | ✅ |
| Latency (95th %ile) | <25ms | Timestamp comparison | ✅ |
| Packet loss | <1% | Receiver statistics | ✅ |
| Stability (30min) | 0 crashes | Extended duration test | ✅ |
| WiFi resilience | Auto-reconnect <30s | Disconnect/reconnect test | ✅ |
| Multi-sensor independence | No crosstalk | 4-person test | ✅ |
| Production mode | Clean operation | DEBUG_LEVEL 0 test | ✅ |

### 11.2 Qualitative Assessment

System is ready for deployment when:
- Technician can set up and validate system in <15 minutes
- Non-technical users can apply finger and see immediate response
- Audio synthesis clearly driven by heartbeat rhythms
- System runs unattended for hours without intervention
- Occasional packet loss or disconnection doesn't disrupt experience
- Visual feedback (LED) provides clear status indication
- Troubleshooting procedures effective and documented

---

## 12. Conclusion

Phase 4 completes the firmware data pipeline by integrating:
- **Phase 1's** proven WiFi and OSC messaging infrastructure
- **Phase 3's** multi-sensor beat detection algorithm
- **End-to-end validation** from pulse sensor to audio server

**Result: A production-ready system that**
- Detects real heartbeats from 4 independent sensors
- Transmits IBI values via OSC with <25ms latency
- Operates reliably for hours without intervention
- Handles WiFi disruptions gracefully
- Provides clear visual feedback
- Integrates seamlessly with audio synthesis server

**Implementation focus:** Integration and validation, not new feature development. Most code already exists in Phase 1 and Phase 3; Phase 4 ensures they work together correctly in production.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-09
**Status:** Ready for implementation

**Dependencies:**
- Phase 1 (WiFi + OSC infrastructure) - IMPLEMENTED
- Phase 3 (Multi-sensor beat detection) - SPECIFIED IN TRD, NOT YET IMPLEMENTED

**Estimated Time:** 3-4 hours integration + 3-4 hours validation
**Next Step:** Implement Phase 3 if not done, then integrate with Phase 4 requirements
