# Heartbeat Installation - Input Hardware Design

## System Overview
Four independent wireless sensor units, each containing an optical pulse sensor, ESP32 microcontroller, and battery pack. Each ESP32 samples its sensor, detects heartbeats, calculates BPM, and transmits data via WiFi/OSC to Linux audio server.

**Architecture**: Sensor+ESP32+Battery (×4) → WiFi → Linux Server

---

## Component List

### Per Sensor Unit (×4)
- **1x ESP32 Development Board** (ESP32-WROOM-32, $8-10 each)
  - Provides: Analog input, WiFi, USB programming
  - Compact form factor (avoid DevKit V1, too large)
- **1x PulseSensor.com Optical Pulse Sensor with Mounting Bracket**
  - Output: 0-3V analog signal
  - Power: 3-5V, ~4mA
- **1x USB Power Bank** (2000-5000mAh, slim profile)
  - Runtime: 4-10 hours per charge
  - USB output → ESP32 micro-USB/USB-C input
- **3x Jumper Wires** (female-to-female, 10cm)
  - Sensor Signal → GPIO
  - Sensor VCC → 3.3V
  - Sensor GND → GND
- **Optional: 1x LED + 220Ω resistor** (for visual heartbeat confirmation)

### Sensor Pad Materials (×4)
- **8"x8" fabric squares** (felt, canvas, or velvet)
- **1-2 lbs fill material** (rice, sand, or poly pellets)
- **Thread, needle**
- **Velcro strip or zipper** (4-6", for battery access)

### Spares
- **1x Backup ESP32** (pre-programmed, identical firmware)
- **1x Backup power bank**

---

## Pin Assignments (Per ESP32)

| Function | ESP32 Pin | Notes |
|----------|-----------|-------|
| Sensor Signal | GPIO 32 (ADC1_CH4) | Analog input, safe for WiFi |
| Status LED (optional) | GPIO 2 | Built-in LED on most boards |
| Sensor VCC | 3.3V Pin | Connect to sensor power |
| Sensor GND | GND Pin | Common ground |

**Firmware Configuration**: Each unit programmed with unique SENSOR_ID (0-3)

---

## Wiring Diagram (Per Unit)

```
PulseSensor:
  Signal wire → ESP32 GPIO 32
  VCC wire → ESP32 3.3V
  GND wire → ESP32 GND

Power Bank USB → ESP32 USB port

Optional LED:
  ESP32 GPIO 2 → 220Ω resistor → LED + → LED - → GND
```

**No soldering required**: Use female-to-female jumper wires

---

## Power Requirements (Per Unit)

### Current Draw
- ESP32: 200-500mA (WiFi active, peak)
- PulseSensor: 4mA
- Optional LED: 10-20mA
- **Total: ~250-520mA typical**

### Battery Runtime
- 2000mAh power bank: 4-8 hours
- 5000mAh power bank: 10-20 hours
- 10,000mAh power bank: 20-40 hours

### Charging
- USB-C or micro-USB (depends on power bank)
- Charge time: 2-6 hours (depending on capacity)
- Charge all 4 units simultaneously with multi-port USB charger

---

## Sensor Pad Construction

### Materials Per Pad
- 8"x8" fabric square (2 pieces for front/back)
- 1-2 cups rice, sand, or poly pellets
- PulseSensor with mounting bracket
- ESP32 (compact model)
- USB power bank (slim profile)
- 3 jumper wires (10cm female-to-female)
- 4-6" Velcro strip or zipper
- Thread, needle

### Assembly Steps
1. Cut two 8"x8" fabric squares
2. Sew PulseSensor bracket to center of top square
3. Sew three edges (inside-out), leave one side open
4. Turn right-side-out
5. Create internal pocket for ESP32 + battery:
   - Sew fabric divider inside to separate electronics from fill material
   - Position near edge with opening
6. Install Velcro/zipper on fourth edge for battery access
7. Connect sensor to ESP32 (3 jumper wires)
8. Place ESP32 and battery in electronics pocket
9. Fill weight compartment with 1-2 lbs material
10. Close Velcro/zipper

### Design Notes
- **Battery access**: Velcro/zipper allows removing battery for charging without disassembling pad
- **ESP32 protection**: Keep in separate pocket from fill material
- **Sensor positioning**: Bracket on top surface, clear of fill material
- **Cable management**: Short jumper wires keep connections compact

### Testing Each Pad
- [ ] Sensor registers pulse when pressed
- [ ] ESP32 powers on from battery
- [ ] Status LED blinks when programmed
- [ ] Weighted pad stable, doesn't slide on floor
- [ ] Battery easily removable for charging

---

## WiFi Configuration

### Network Setup
All 4 ESP32s connect to same WiFi network:
```cpp
const char* WIFI_SSID = "heartbeat-install";
const char* WIFI_PASSWORD = "secure_password";
const IPAddress SERVER_IP(192, 168, 50, 100);  // Audio server
const int SERVER_PORT = 8000;
```

### Firmware Differences Per Unit
```cpp
// sensor_config.h
#define SENSOR_ID 0  // Change to 1, 2, 3 for other units

// OSC messages sent:
// /heartbeat/0 <ibi_ms>  for unit 0
// /heartbeat/1 <ibi_ms>  for unit 1
// etc.
```

### IP Addressing
- ESP32s use DHCP (dynamic IP) - simplest
- Alternative: Static IPs if router allows (192.168.50.11-14)
- Server at fixed IP: 192.168.50.100

---

## Status Indicators

### LED Behavior (GPIO 2)
- **Solid on**: WiFi connected, awaiting heartbeats
- **Blinking (1Hz)**: Heartbeat detected
- **Rapid blink (10Hz)**: WiFi connecting
- **Off**: Not powered

### Serial Monitor (Development Only)
- Detected beat timestamps
- Calculated BPM
- WiFi connection status
- OSC message transmission confirmation

---

## Testing Checklist

### Individual Unit Testing
- [ ] ESP32 powers on from battery
- [ ] WiFi connection successful
- [ ] Status LED behavior correct
- [ ] Sensor detects pulse when fingertip applied
- [ ] Beat detection triggers consistently
- [ ] BPM calculation within ±5 of phone app
- [ ] OSC messages received at server
- [ ] 15-minute continuous operation without errors
- [ ] Battery lasts expected duration

### Multi-Unit Testing
- [ ] All 4 units connect to WiFi simultaneously
- [ ] Independent beat detection per unit
- [ ] Different BPM values for different users
- [ ] No interference between units
- [ ] Server receives all 4 data streams

### OSC Transmission Testing
- [ ] UDP packets received at server
- [ ] Message format correct: `/heartbeat/N <ibi_ms>`
- [ ] Latency <50ms from beat to message receipt
- [ ] No dropped messages under continuous operation

### Physical Installation Testing
- [ ] Pads positioned in spoke pattern
- [ ] No WiFi dead zones at any position
- [ ] Battery removal/replacement easy
- [ ] 30+ minute test session successful

### Failure Mode Testing
- [ ] Sensor disconnected: Unit stops sending, auto-resumes when reconnected
- [ ] No heartbeat detected: Unit continues WiFi connection
- [ ] WiFi drops: Auto-reconnect without restart
- [ ] Power cycle: System reinitializes cleanly
- [ ] Battery depleted: Unit stops gracefully, resumes when charged

---

## Firmware Upload Process

### Initial Programming (All Units)
1. Connect ESP32 to computer via USB
2. Open Arduino IDE
3. Load heartbeat firmware
4. Edit `sensor_config.h`: Set `SENSOR_ID` (0, 1, 2, or 3)
5. Edit WiFi credentials
6. Upload to ESP32
7. Verify via serial monitor
8. Disconnect USB, power from battery
9. Repeat for remaining 3 units

### Identifying Units
**Physical labeling**: Mark each pad with its ID (0-3) using fabric marker or tag

---

## Known Limitations

### Hardware Constraints
- 3.3V analog input only (PulseSensor compatible)
- WiFi range: ~30m from access point
- Battery requires periodic charging (4-20 hours depending on capacity)

### Signal Quality
- Optical sensors sensitive to ambient light (cover during use)
- Fingertip pressure affects signal amplitude
- Cold hands reduce signal quality
- Movement artifacts can cause false beats

### Environmental
- WiFi interference in crowded 2.4GHz environments
- Multiple ESP32s may strain router (use quality router)
- Heat dissipation minimal, no cooling needed

---

## Advantages of Wireless Architecture

- **No cable management**: Participants lie down freely
- **Faster setup**: No hub wiring, no breadboard
- **Simpler debugging**: Test each unit independently
- **More reliable**: No fragile solder joints
- **Easier maintenance**: Swap out individual units without disturbing others
- **Scalable**: Add/remove sensors easily

---

## Future Expansion Considerations

### Potential Additions (Per Unit)
- **Larger battery**: Extended runtime for multi-day festivals
- **External antenna**: Stronger WiFi signal
- **SD card logging**: Local data backup
- **OLED display**: On-device BPM display

### Not Included in This Design
- Audio output (separate system)
- LED visualization (handled by lighting system or separate ESP32)
- Haptic feedback (removed for simplicity)

---

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| No power | Battery depleted | Charge battery, check USB connection to ESP32 |
| No WiFi connection | Wrong credentials or out of range | Serial monitor for error, move closer to router |
| Flat signal (no pulse) | Sensor not touching skin | Adjust finger position, check sensor wiring |
| Erratic readings | Loose jumper wire | Check 3 sensor connections |
| No beat detection | Signal too weak/strong | Adjust sensor placement, check analog pin |
| Unit stops working | Battery died | Charge battery |
| All units have issues | Router problem | Restart WiFi router |
| BPM incorrect | Threshold miscalibration | Check firmware threshold settings |

---

## Design Decisions Summary

### Why Wireless (vs Hub)?
- Eliminates cable fabrication (RJ-45 crimping, soldering)
- No fragile wired connections
- Simpler installation and maintenance
- Similar total cost
- Better for drop-in/drop-out usage pattern

### Why Individual Batteries (vs Central Power)?
- No power cables across floor
- Portable sensor pads
- Graceful degradation (one battery dies, others continue)

### Why GPIO 32 (vs Other Pins)?
- ADC1 channel (WiFi compatible)
- Safe for all ESP32 boot modes
- 12-bit resolution (0-4095)

---

## Next Steps

1. **Component arrival** - Verify all parts present
2. **Single unit prototype** - Test one sensor + ESP32 + battery
3. **Firmware development** - See heartbeat-firmware-design.md
4. **Program all 4 units** - Different SENSOR_ID per unit
5. **OSC communication** - Verify server receives data from all units
6. **Construct sensor pads** - Sew fabric with Velcro access
7. **Extended testing** - 30+ minute multi-person session
8. **Final validation** - Drop-in/drop-out usage scenarios

---

*Document Version: 2.0*
*Last Updated: 2025-11-07*
*Architecture: Wireless independent sensor units*
*Scope: Input hardware - sensors with ESP32 and battery in weighted fabric pads*