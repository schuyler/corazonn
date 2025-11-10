# API: WiFi Status Monitoring

WiFi connectivity monitoring and management.

---

## 6.7 WiFi Status Monitoring

**Function:** `checkWiFi()`

**Signature:**
```cpp
void checkWiFi();
```

**Purpose:** Monitor WiFi connection status and reconnect if needed

**Requirements:**

**R26: WiFi Check Logic**
- Check WiFi.status() every 5 seconds
- If disconnected: Call WiFi.reconnect(), set system.wifiConnected = false
- If connected: Set system.wifiConnected = true
- Non-blocking operation

**Implementation:**
```cpp
void checkWiFi() {
  static unsigned long lastCheckTime = 0;
  unsigned long now = millis();

  // Check every 5 seconds
  if (now - lastCheckTime >= 5000) {
    lastCheckTime = now;

    if (WiFi.status() == WL_CONNECTED) {
      system.wifiConnected = true;
    } else {
      system.wifiConnected = false;
      WiFi.reconnect();  // Attempt to reconnect
    }
  }
}
```

**Timing:**
- Check interval: 5 seconds
- Processing: <2ms per check
- Non-blocking (no delays)

**Call Location:**
- Called from main `loop()` function
- Runs continuously regardless of sampling rate

**Example Usage:**
```cpp
void loop() {
  static unsigned long lastSampleTime = 0;
  unsigned long currentTime = millis();

  // Sensor processing every 20ms (50Hz)
  if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    // ... sensor processing ...
  }

  // WiFi check every 5 seconds
  checkWiFi();

  delay(1);
}
```

---

## Same as Phase 1

This function is unchanged from Phase 1 implementation. Use existing WiFi functions from Phase 1 if available:

**Related Functions from Phase 1:**
- `connectWiFi()` — Initial WiFi connection (called from setup())
- `checkWiFi()` — Status monitoring (called from loop())

---

## WiFi State Machine

```
DISCONNECTED
    ↓
WiFi.reconnect()
    ↓
CONNECTING (attempts: 0-20, ~5 seconds)
    ├─ Success → CONNECTED
    │ (LED: solid on, messages sent)
    │
    └─ Timeout → DISCONNECTED
      (LED: rapid blink, messages blocked)
```

---

## Connection Status Updates

**system.wifiConnected:**
- `true`: WiFi connected, OSC messages will be sent
- `false`: WiFi disconnected, OSC messages blocked (no error thrown, just silent)

**LED Feedback:**
- Connected (true): LED solid on
- Disconnected (false): LED rapid blink (10Hz)

**OSC Transmission:**
- Connected: sendHeartbeatOSC() sends messages successfully
- Disconnected: sendHeartbeatOSC() still called but packets lost (normal UDP behavior)

---

## Reconnection Behavior

**Automatic Reconnection:**
- WiFi.reconnect() attempts to connect without full rescan
- Faster than WiFi.begin() if credentials stored
- Typical reconnection time: 2-5 seconds

**No Active Monitoring:**
- Connection assumed stable once established
- Only passive monitoring (status check every 5 seconds)
- Handles unexpected disconnections (signal loss, AP restart)

**Message Handling During Disconnect:**
- sendHeartbeatOSC() still called but packets don't reach server
- No error messages (fire-and-forget UDP)
- Beat detection continues locally (no gaps in detection)
- When WiFi reconnects, messages resume transmission

---

## Troubleshooting WiFi Issues

**Connection Timeout:**
- Check SSID and password are correct
- Verify 2.4GHz network (ESP32 supports both, but 5GHz has range issues)
- Check AP is reachable

**Intermittent Disconnections:**
- Check WiFi signal strength (should be -80dBm or better)
- Move AP closer to ESP32 or reduce obstacles
- Check for interference (microwaves, other 2.4GHz devices)

**Messages Not Received:**
- Check SERVER_IP is correct and on same network
- Check SERVER_PORT matches receiver (default 8000)
- Verify firewall allows UDP on that port

---

## Related Documentation

- [Configuration](configuration.md) — Network constants (WIFI_SSID, WIFI_PASSWORD, SERVER_IP, SERVER_PORT)
- [API: Status](api-status.md) — LED feedback reflects WiFi status
- [Implementation](implementation.md) — setup() and loop() integration
- [Operations](operations.md) — WiFi troubleshooting section

---

**Next Step:** Review [Implementation](implementation.md) for program flow integration
