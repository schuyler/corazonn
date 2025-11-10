# Phase 1 Firmware - Network API

[**Back to Index**](index.md)

**Version:** 3.0 | **Date:** 2025-11-09

Functions for WiFi connection management and monitoring.

---

## 6.1 WiFi Connection

**Function:** `connectWiFi()`

**Signature:**
```cpp
bool connectWiFi();
```

**Purpose:** Establish WiFi connection with timeout

**Requirements:**

**R1: WiFi Initialization**
- MUST call `WiFi.mode(WIFI_STA)` before `WiFi.begin()`
- MUST call `WiFi.begin(WIFI_SSID, WIFI_PASSWORD)`
- MUST print "Connecting to WiFi: [SSID]" to serial

**R2: Connection Wait Loop**
- MUST poll `WiFi.status()` until `WL_CONNECTED` OR timeout
- MUST timeout after `WIFI_TIMEOUT_MS` milliseconds
- MUST use non-blocking delay (check millis() each iteration)
- MUST blink LED during connection attempt (100ms on/off)

**R3: Success Behavior**
- MUST set `state.wifiConnected = true`
- MUST turn LED solid ON
- MUST print "Connected! IP: [IP_ADDRESS]" to serial
- MUST return `true`

**R4: Failure Behavior**
- MUST print "WiFi connection timeout" to serial
- MUST leave LED in last blink state
- MUST return `false`

**Example Serial Output (Success):**
```
Connecting to WiFi: heartbeat-install
Connected! IP: 192.168.50.42
```

**Example Serial Output (Failure):**
```
Connecting to WiFi: heartbeat-install
WiFi connection timeout
```

**Implementation Notes:**

Use `millis()` to track elapsed time for timeout. The non-blocking approach prevents the main firmware from hanging if WiFi is unreachable. The 30-second timeout (WIFI_TIMEOUT_MS) allows sufficient time for WiFi connection negotiation while not blocking indefinitely.

The LED blinking provides visual feedback during connection attempts. Use a fast blink pattern (100ms on, 100ms off = 5 Hz) to indicate connection-in-progress state.

After successful connection, leave the LED solid ON to indicate ready status.

---

## 6.4 WiFi Status Monitoring

**Function:** `checkWiFi()`

**Signature:**
```cpp
void checkWiFi();
```

**Purpose:** Monitor WiFi connection, attempt reconnection if dropped

**Requirements:**

**R12: Status Check**
- MUST check `WiFi.status()` for current connection state
- If `WL_CONNECTED`: Set `state.wifiConnected = true`
- If not `WL_CONNECTED`: Set `state.wifiConnected = false`

**R13: Reconnection Logic**
- If disconnected: MUST call `WiFi.reconnect()`
- MUST print "WiFi disconnected, reconnecting..." to serial
- WiFi.reconnect() is **non-blocking** - returns immediately, reconnection happens in background
- May take 5-30 seconds to reconnect
- ESP32 WiFi stack handles reconnection attempts automatically
- No timeout needed - will keep trying indefinitely

**R14: Call Frequency**
- SHOULD be called every 5 seconds (not every loop iteration)
- Use static variable with `millis()` timer to rate-limit checks
- Static variable MUST be initialized to 0 (causes immediate first check)

**Pseudocode:**
```
static last_check_time = 0  # Initialize to 0

function checkWiFi():
    if millis() - last_check_time < 5000:
        return  # Check at most every 5 seconds

    last_check_time = millis()

    if WiFi.status() != WL_CONNECTED:
        state.wifiConnected = false
        print("WiFi disconnected, reconnecting...")
        WiFi.reconnect()
    else:
        state.wifiConnected = true
```

**Note on millis() Rollover:**

The expression `millis() - last_check_time` works correctly even after millis() rolls over at 49.7 days due to unsigned arithmetic properties. Do not "fix" this with additional rollover handling.

**Implementation Notes:**

The 5-second check interval reduces CPU usage and prevents excessive WiFi stack polling. The static variable persists across function calls, allowing rate-limiting without global state.

The `WiFi.reconnect()` call is non-blocking, meaning it starts the reconnection process but returns immediately. The ESP32 WiFi stack manages the actual reconnection in the background. Subsequent calls to `checkWiFi()` will see the updated connection status.

This function monitors ongoing connection health, complementing the initial `connectWiFi()` function that establishes the first connection.

---

**Related sections:**
- See [configuration.md](configuration.md) for WiFi configuration constants
- See [implementation.md](implementation.md) for how to call these functions in setup() and loop()
- See [api-status.md](api-status.md) for LED feedback during connection states
