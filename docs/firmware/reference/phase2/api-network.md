# Network API

## WiFi Connection Functions (Phase 1)

The following functions from Phase 1 remain unchanged in Phase 2. WiFi connection and status monitoring are reused without modification.

### connectWiFi()

**Signature:**
```cpp
bool connectWiFi();
```

**Purpose:** Establish WiFi connection with timeout handling

**Source:** `phase1-firmware-trd.md` Section 6.1

**Key behavior:**
- Connects to WiFi network specified by `WIFI_SSID` and `WIFI_PASSWORD`
- Returns true if connection successful, false if timeout
- Uses `WIFI_TIMEOUT_MS` (30 seconds) as timeout threshold
- Implements non-blocking polling for connection status

**Implementation Details:**
- MUST use `WiFi.begin()` to initiate connection
- MUST check `WiFi.status()` in loop until `WL_CONNECTED` or timeout
- MUST return connection result
- MUST print IP address on successful connection
- MUST print error message on timeout

### checkWiFi()

**Signature:**
```cpp
void checkWiFi();
```

**Purpose:** Monitor WiFi connection and re-connect if needed

**Source:** `phase1-firmware-trd.md` Section 6.4

**Key behavior:**
- Checks WiFi status periodically (rate-limited, not every loop iteration)
- Attempts reconnection if WiFi drops
- Updates `state.wifiConnected` flag
- Used in main loop to maintain connection

**Implementation Details:**
- MUST implement rate limiting (check every ~5 seconds, not every iteration)
- MUST check `WiFi.status()` to detect disconnection
- MUST call `WiFi.reconnect()` if disconnected
- MUST track last check time using `state.lastWiFiCheckTime`

### Notes

- **No changes from Phase 1** - Keep exact implementation
- These functions are called in `setup()` and `loop()` as shown in Phase 1
- Phase 2 only changes what data is transmitted (real IBI instead of test values)
- WiFi infrastructure remains stable and reusable across phases

---

## Related Documentation

- **[Configuration](configuration.md)** - Network configuration constants
- **[Messaging API](api-messaging.md)** - OSC transmission (uses WiFi)
- **[Implementation](implementation.md)** - How WiFi functions integrate with main flow
- **[Operations](operations.md)** - Troubleshooting WiFi issues

---

## Integration in Phase 2

**Called in setup():**
```cpp
state.wifiConnected = connectWiFi();
```

**Called in loop():**
```cpp
checkWiFi();  // Every 5 seconds, rate-limited internally
```

The network API provides the foundation for all OSC messaging. Phase 2 sends real heartbeat data instead of test values, but WiFi communication remains unchanged.
