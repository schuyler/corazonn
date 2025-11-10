# Phase 1 Firmware - Status API

[**Back to Index**](index.md)

**Version:** 3.0 | **Date:** 2025-11-09

Function for LED status indication.

---

## 6.3 LED Status Indication

**Function:** `updateLED()`

**Signature:**
```cpp
void updateLED();
```

**Purpose:** Update LED state based on system status

**Requirements:**

**R9: LED States**
- **WiFi Connecting:** Blink at 5 Hz (100ms on, 100ms off)
- **WiFi Connected:** Solid ON
- **No state for message pulse in Phase 1** (simplified)

**R10: State Determination**
- MUST check `state.wifiConnected`
- If false: Blink at 5 Hz using `(millis() / 100) % 2`
- If true: Solid HIGH

**R11: LED Control**
- MUST use `digitalWrite(STATUS_LED_PIN, HIGH/LOW)`
- Non-blocking (no delays)

**Pseudocode:**
```
function updateLED():
    if not state.wifiConnected:
        # Blink during connection
        led_state = (millis() / 100) % 2
        digitalWrite(STATUS_LED_PIN, led_state)
    else:
        # Solid on when connected
        digitalWrite(STATUS_LED_PIN, HIGH)
```

**Implementation Notes:**

**LED State Machine:**

The LED provides visual feedback for two states:

1. **Disconnected (blinking):** When `state.wifiConnected` is false, the LED blinks at 5 Hz. This indicates the device is attempting to connect or waiting for connection.

2. **Connected (solid):** When `state.wifiConnected` is true, the LED remains solid ON. This confirms WiFi connection is active and messages are being transmitted.

**Blink Calculation:**

The expression `(millis() / 100) % 2` produces:
- 0 for 100ms intervals where millis() / 100 is even
- 1 for 100ms intervals where millis() / 100 is odd

This creates a 5 Hz blink pattern (100ms on, 100ms off) without any delays. The millis() timer is typically accessed every 10ms in the loop, providing smooth updates.

**Non-Blocking Design:**

The function performs no blocking operations (no delays). It checks the current time via `millis()` and updates the LED state immediately. This allows the main loop to continue running without interruption.

**LED Pin Configuration:**

The STATUS_LED_PIN (GPIO 2 by default) must be configured as OUTPUT in `setup()` before calling this function. See [implementation.md](implementation.md) for pinMode() setup.

---

**LED Behavior Timeline:**

```
startup                              connected (solid)
  ↓                                      ↓
[blink] → [blink] → ... → [connected] → [--------]
  5Hz      5Hz           transition    (always on)
```

---

**Related sections:**
- See [configuration.md](configuration.md) for STATUS_LED_PIN setting
- See [api-network.md](api-network.md) for WiFi connection state that drives LED behavior
- See [implementation.md](implementation.md) for setup() and loop() integration
