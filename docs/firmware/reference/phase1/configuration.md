# Phase 1 Firmware - Configuration & Data Structures

[**Back to Index**](index.md)

**Version:** 3.0 | **Date:** 2025-11-09

---

## 3. Required Libraries

### 3.1 Arduino Libraries

**Built-in (no installation):**
- `WiFi.h` - ESP32 WiFi stack
- `WiFiUdp.h` - UDP socket implementation

**External (installed via platformio.ini lib_deps):**
- `OSC` by Adrian Freed (CNMat)
  - Version: latest available (3.5.8+ from GitHub repository)
  - Provides: `OSCMessage.h`, `OSCBundle.h`
  - Installation: Automatically via `lib_deps = https://github.com/CNMAT/OSC.git` in platformio.ini
  - Note: PlatformIO registry version (1.0.0) is outdated; use GitHub directly

### 3.2 Library Usage

**WiFi.h:**
```cpp
WiFi.mode(WIFI_STA);          // Station mode (client)
WiFi.begin(ssid, password);   // Connect to AP
WiFi.status();                // Check connection status
WiFi.localIP();               // Get assigned IP
WiFi.reconnect();             // Attempt reconnection
```

**WiFiUdp.h:**
```cpp
WiFiUDP udp;
udp.begin(localPort);         // Bind to local port (use 0 for any)
udp.beginPacket(ip, port);    // Start packet
udp.write(buffer, length);    // Add data
udp.endPacket();              // Send packet
```

**OSCMessage.h:**
```cpp
OSCMessage msg("/address/pattern");
msg.add((int32_t)value);      // Add int32 argument
msg.send(udp);                // Send via UDP object
msg.empty();                  // Clear for reuse
```

---

## 4. Configuration Constants

### 4.1 Network Configuration

**MUST be user-configurable (edit before upload):**

```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "your-password-here";
const IPAddress SERVER_IP(192, 168, 1, 100);  // CHANGE THIS: Your dev machine's IP
const uint16_t SERVER_PORT = 8000;
```

**⚠️ CRITICAL - SERVER_IP Configuration:**

The ESP32 hardware CANNOT use `127.0.0.1` (that would be its own localhost).
You MUST use your development machine's IP address on the WiFi network.

**Finding your development machine's IP:**
- **Linux:** `ip addr show` or `ifconfig` (look for wlan0 or eth0 inet address)
- **macOS:** System Preferences → Network → WiFi → Advanced → TCP/IP (IPv4 Address)
- **Windows:** `ipconfig` (look for IPv4 Address under WiFi adapter)

Example: If your dev machine shows `192.168.1.100`, use:
```cpp
const IPAddress SERVER_IP(192, 168, 1, 100);
```

The ESP32 will connect to WiFi, get its own IP (e.g., `192.168.1.42`), and send messages to your dev machine at `192.168.1.100:8000` where the Python receiver is listening.

**Requirements:**
- `WIFI_SSID`: String, max 32 characters, **2.4GHz network only** (ESP32 does not support 5GHz)
- `WIFI_PASSWORD`: String, max 63 characters, WPA2
- `SERVER_IP`: IPv4 address of development machine running Python receiver
- `SERVER_PORT`: UDP port 8000 (matches testing infrastructure)

### 4.2 Hardware Configuration

```cpp
const int STATUS_LED_PIN = 2;  // Built-in LED (GPIO 2 on most ESP32 boards)
```

**Requirements:**
- LED pin MUST be output-capable GPIO
- GPIO 2 is standard built-in LED on ESP32 DevKit boards
- May need adjustment for other board variants

### 4.3 System Configuration

```cpp
const int SENSOR_ID = 0;  // Unique sensor ID: 0, 1, 2, or 3
const unsigned long TEST_MESSAGE_INTERVAL_MS = 1000;  // 1 second
const unsigned long WIFI_TIMEOUT_MS = 30000;  // 30 seconds
```

**Requirements:**
- `SENSOR_ID`: Integer 0-3, unique per ESP32 unit
- `TEST_MESSAGE_INTERVAL_MS`: Milliseconds between messages (Phase 1: 1000)
- `WIFI_TIMEOUT_MS`: Max time to wait for WiFi connection

---

## 5. Data Structures

### 5.1 System State

**Purpose:** Track WiFi connection and message timing

```cpp
struct SystemState {
    bool wifiConnected;           // Current WiFi connection status
    unsigned long lastMessageTime;  // millis() of last message sent
    uint32_t messageCounter;      // Total messages sent
};
```

**Requirements:**
- `wifiConnected`: Set true when WiFi.status() == WL_CONNECTED
- `lastMessageTime`: Updated each time message sent
- `messageCounter`: Incremented each time message sent, rolls over at UINT32_MAX

**Initial Values:**
```cpp
SystemState state = {
    .wifiConnected = false,
    .lastMessageTime = 0,
    .messageCounter = 0
};
```

### 5.2 Global Objects

```cpp
WiFiUDP udp;          // UDP socket for OSC transmission
SystemState state;    // System state (defined above)
```

---

**Related sections:**
- See [api-network.md](api-network.md) for WiFi connection functions
- See [api-messaging.md](api-messaging.md) for OSC message function
- See [implementation.md](implementation.md) for how to use these configurations
