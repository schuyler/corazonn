# API: LED Status Indication

LED feedback for WiFi status and beat detection.

---

## 6.6 LED Status Indication

**Function:** `updateLED()`

**Signature:**
```cpp
void updateLED();
```

**Purpose:** Visual feedback for system state and beat detection from any sensor

**LED States:**
- **WiFi connecting:** Rapid blink 10Hz (50ms on/off)
- **WiFi connected, no beats:** Solid ON
- **Beat detected:** 50ms pulse (briefly brighter or just visible pulse)

**Requirements:**

**R24: LED States**
- **WiFi connecting:** Rapid blink 10Hz (50ms on/off)
- **WiFi connected, no beats:** Solid ON
- **Beat detected:** 50ms pulse (briefly brighter or just visible pulse)

**R25: Implementation**
```cpp
static unsigned long ledPulseTime = 0;
const int LED_PULSE_DURATION = 50;  // 50ms for visibility

if (!system.wifiConnected) {
  // Rapid blink while connecting
  digitalWrite(STATUS_LED_PIN, (millis() / 50) % 2);
} else if (system.beatDetectedThisLoop) {
  // Beat detected: turn on and record time
  digitalWrite(STATUS_LED_PIN, HIGH);
  ledPulseTime = millis();
} else if (millis() - ledPulseTime < LED_PULSE_DURATION) {
  // Keep on during pulse duration
  digitalWrite(STATUS_LED_PIN, HIGH);
} else {
  // Solid on when connected and idle
  digitalWrite(STATUS_LED_PIN, HIGH);
}

// Clear flag for next iteration
system.beatDetectedThisLoop = false;
```

**Requirements:**
- LED blinks on beat from ANY sensor (not just sensor 0)
- Pulse duration 50ms (clearly visible)
- Non-blocking (no delays)
- Static variable `ledPulseTime` tracks pulse timing

**State Logic Flowchart:**
```
┌─────────────────────────────────┐
│ Check system.wifiConnected      │
└─────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
   NO        YES
    │         │
    │    ┌────┴─────────────────────────────┐
    │    │ Check system.beatDetectedThisLoop│
    │    └────┬─────────────────────────────┘
    │         │
    │     ┌───┴───┐
    │     │       │
    │    YES     NO
    │     │       │
    │     │    ┌──┴──────────────────────┐
    │     │    │ Check pulse duration    │
    │     │    │ (millis - ledPulseTime) │
    │     │    └──┬───────────────────┬──┘
    │     │       │                   │
    │     │      <50ms              ≥50ms
    │     │       │                   │
    ├─────┼───────┼─────────────────┬─┴──┐
│ LED ON: Blink (50Hz) │ LED ON: Pulse │ LED ON: Solid │ LED ON: Solid │
└─────────────────────┴──────────────┴────┘
```

**Timing Details:**

**WiFi Connecting Blink:**
```
(millis() / 50) % 2
↓
Every 50ms, toggle between 0 and 1
↓
Blink frequency: 10Hz (1000ms / (50ms * 2))
```

**Beat Pulse:**
```
LED ON immediately when beat detected
↓
Record ledPulseTime = millis()
↓
Keep LED on for 50ms after beat
↓
Then revert to solid on (if connected) or blinking (if disconnecting)
```

**Example Timing Sequence:**

```
Time  | WiFi | Beat | LED State     | Action
------|------|------|---------------|------------------
0ms   | No   | -    | Blink ON      | Connecting (50Hz)
50ms  | No   | -    | Blink OFF     | Connecting (50Hz)
100ms | No   | -    | Blink ON      | Connecting (50Hz)
150ms | No   | -    | Blink OFF     | Connecting (50Hz)
200ms | Yes  | -    | Solid ON      | Connected, no beat
250ms | Yes  | -    | Solid ON      | Connected, no beat
300ms | Yes  | YES  | Solid ON      | Beat detected, pulse starts
350ms | Yes  | -    | Solid ON      | Pulse ongoing (10ms into 50ms)
350ms | Yes  | -    | Solid ON      | Pulse ongoing
400ms | Yes  | -    | Solid ON      | Pulse complete (50ms passed)
450ms | Yes  | -    | Solid ON      | Idle
```

**Change from Phase 1:**
- Phase 1: LED responded to message sends (test values)
- Phase 3: LED responds to real beat detection instead
- Now synchronized with actual heartbeat events

---

## Implementation Notes

**Non-Blocking Design:**
- No `delay()` calls
- Uses `millis()` for timing
- Static variable persists across calls
- Safe to call every 20ms

**Multiple Sensors:**
- LED responds to beats from ANY sensor
- If multiple sensors beat near-simultaneously, LED shows single 50ms pulse
- No "flicker" or multiple pulses (non-overlapping detection due to refractory period)

**Visibility Considerations:**
- 50ms pulse clearly visible at human perception speeds
- LED remains bright when connected (positive feedback)
- Rapid blinking immediately indicates connection issue

---

## Related Documentation

- [Configuration](configuration.md) — STATUS_LED_PIN constant
- [API: Beat Detection](api-beat-detection.md) — Sets system.beatDetectedThisLoop
- [Implementation](implementation.md) — Called from main loop()

---

**Next Step:** Implement WiFi monitoring with [API: Network](api-network.md)
