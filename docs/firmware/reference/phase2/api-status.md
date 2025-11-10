# Status API

## LED Status Indication

### updateLED()

**Signature:**
```cpp
void updateLED();
```

**Purpose:** Update LED state based on WiFi and beat detection status

**Called from:** Main loop, every iteration (multiple times per second)

**Parameters:** None (uses global state variables)

**Return:** None (directly controls GPIO)

---

## LED States (Phase 2 Enhanced)

**WiFi Connecting:** Blink at 5 Hz (100ms on/off)
- Pattern: 100ms ON, 100ms OFF, repeat
- Indicates system starting up, waiting for WiFi

**WiFi Connected, No Beat:** Solid ON
- LED stays high
- Indicates system ready, waiting for heartbeat

**Beat Detected:** 50ms pulse (briefly brighter, then return to solid)
- 50ms brief pulse when beat detected
- Both states are HIGH (subtle visual feedback)
- Can be enhanced with external LED on different pin if needed

---

## Requirements

**R22: LED States (Phase 2 Enhanced)**
- **WiFi Connecting:** Blink at 5 Hz (100ms on/off) - Phase 1 behavior
- **WiFi Connected, No Beat:** Solid ON - Phase 1 behavior
- **Beat Detected:** 50ms pulse (briefly brighter, then return to solid) - Phase 2 new

**R23: Beat Pulse Implementation**
- When beat detected (call from `detectBeat()`): Set global `ledPulseTime = millis()`
- In `updateLED()`:
  - IF `millis() - ledPulseTime < 50`: Keep LED HIGH (pulse duration)
  - ELSE: Return to solid HIGH (normal connected state)

**R24: State Determination**
- Priority order:
  1. If WiFi not connected: Blink at 5 Hz
  2. If beat pulse active (<50ms since pulse): HIGH
  3. Else: Solid HIGH (connected, waiting for beats)

---

## Global Variables

```cpp
// Declared globally (Section 5.3)
static unsigned long ledPulseTime = 0;  // Time when LED pulse started
```

Used to track when last beat was detected for pulse duration.

---

## Implementation

**Modified Pseudocode:**
```
# ledPulseTime is a global variable (declared in Section 5.3)

function updateLED():
    if NOT state.wifiConnected:
        # Blink during connection
        digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2)
    else if (millis() - ledPulseTime < 50):
        # Beat pulse active
        digitalWrite(STATUS_LED_PIN, HIGH)
    else:
        # Solid on when connected
        digitalWrite(STATUS_LED_PIN, HIGH)

function onBeatDetected():
    ledPulseTime = millis()  # Trigger pulse
```

**C++ Implementation:**
```cpp
void updateLED() {
    if (!state.wifiConnected) {
        // Blink at 5 Hz during WiFi connection
        digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
    } else if ((millis() - ledPulseTime) < 50) {
        // Beat pulse active (50ms)
        digitalWrite(STATUS_LED_PIN, HIGH);
    } else {
        // Solid on when connected
        digitalWrite(STATUS_LED_PIN, HIGH);
    }
}
```

---

## Pin Configuration

**Hardware:**
- `STATUS_LED_PIN = 2` (built-in ESP32 LED)
- High = LED ON
- Low = LED OFF

**Initialization:**
```cpp
pinMode(STATUS_LED_PIN, OUTPUT);
digitalWrite(STATUS_LED_PIN, LOW);
```

---

## Blinking Pattern (WiFi Connecting)

**5 Hz blink (100ms period):**
```
(millis() / 100) % 2
```

Divides time into 100ms periods. Alternates between 0 and 1, creating blink.

**Timeline:**
- 0-99ms: 0 (OFF)
- 100-199ms: 1 (ON)
- 200-299ms: 0 (OFF)
- 300-399ms: 1 (ON)
- ...

---

## Beat Pulse Trigger

**Called from `detectBeat()`:**
```cpp
// On valid beat detection (second and subsequent beats)
if (sensor.firstBeatDetected && timeSinceLastBeat >= REFRACTORY_PERIOD_MS) {
    // ... calculate IBI, send OSC ...
    ledPulseTime = millis();  // Trigger LED pulse
}
```

**Pulse Duration:**
- 50ms window after beat detection
- `millis() - ledPulseTime < 50` evaluates to true for ~50ms
- After 50ms, LED returns to normal state (still HIGH when connected)

---

## Visual Feedback Summary

| State | LED Pattern | Meaning |
|-------|-------------|---------|
| Startup | Blinking | Connecting to WiFi |
| Ready | Solid ON | Connected, waiting for heartbeat |
| Beat Detected | 50ms pulse | Heartbeat detected |
| Sensor Disconnected | Solid ON | WiFi still connected, waiting for sensor |
| Error | Blinking | WiFi connection lost |

---

## Enhanced LED Feedback (Optional)

The current implementation uses only the built-in GPIO 2 LED. For more visible feedback:

**Option 1: Add external LED on different pin**
```cpp
const int BEAT_LED_PIN = 4;  // External LED on GPIO 4

void updateLED() {
    if (!state.wifiConnected) {
        digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
        digitalWrite(BEAT_LED_PIN, LOW);  // Off during connection
    } else if ((millis() - ledPulseTime) < 50) {
        digitalWrite(STATUS_LED_PIN, HIGH);
        digitalWrite(BEAT_LED_PIN, HIGH);  // Bright pulse on beat
    } else {
        digitalWrite(STATUS_LED_PIN, HIGH);
        digitalWrite(BEAT_LED_PIN, LOW);   // Dim when no beat
    }
}
```

**Option 2: PWM for brightness variation**
```cpp
const int BEAT_LED_PIN = 4;  // PWM-capable pin

void updateLED() {
    if (!state.wifiConnected) {
        digitalWrite(STATUS_LED_PIN, (millis() / 100) % 2);
        analogWrite(BEAT_LED_PIN, 0);  // Off
    } else if ((millis() - ledPulseTime) < 50) {
        digitalWrite(STATUS_LED_PIN, HIGH);
        analogWrite(BEAT_LED_PIN, 255);  // Full brightness
    } else {
        digitalWrite(STATUS_LED_PIN, HIGH);
        analogWrite(BEAT_LED_PIN, 50);   // Dim
    }
}
```

---

## Integration in Main Loop

```cpp
void loop() {
    static unsigned long lastSampleTime = 0;

    checkWiFi();  // WiFi monitoring (rate-limited)

    unsigned long currentTime = millis();
    if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
        lastSampleTime = currentTime;

        // Signal processing pipeline
        int rawValue = analogRead(SENSOR_PIN);
        updateMovingAverage(rawValue);
        updateBaseline();
        checkDisconnection(rawValue);
        detectBeat();  // May set ledPulseTime
    }

    updateLED();  // Called every loop iteration, checks ledPulseTime
    delay(1);
}
```

**Called Frequency:**
- Every loop iteration (multiple times per 20ms sample interval)
- Non-blocking, minimal CPU impact

---

## Related Documentation

- **[Configuration](configuration.md)** - LED pin definition
- **[Beat Detection API](api-beat-detection.md)** - Sets ledPulseTime on valid beat
- **[Network API](api-network.md)** - WiFi status affects LED pattern
- **[Implementation](implementation.md)** - Integration in main loop

---

## Troubleshooting LED Issues

**LED never turns on:**
- Check `STATUS_LED_PIN = 2` is correct for your board
- Verify `pinMode()` call in setup()
- Test with simple blink code

**LED doesn't blink during WiFi connection:**
- Check WiFi connection logic
- Verify `state.wifiConnected` is being updated
- Check blink period calculation

**No pulse on beat detection:**
- Verify beats are being detected (check serial output)
- Check `ledPulseTime` is being set in detectBeat()
- Verify pulse duration threshold (50ms) is correct

**LED always on:**
- Normal behavior when WiFi connected
- Check that beats are being detected (separate issue)
- LED should flicker briefly on each beat if enabled
