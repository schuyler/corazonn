# corazonn

Heartbeat-driven installation art system with distributed ESP32 sensors, OSC messaging, audio synthesis, and networked lighting control.

## Quick Links

- **Testing & Visualization:** `/testing/README.md` - OSC protocol validation, simulator, and EKG viewer
- **Firmware Development:** `/firmware/README.md` - ESP32 sensor code for heartbeat detection
- **Audio System:** `/audio/README.md` - Pure Data patches for sound synthesis and effects
- **Lighting Control:** `/lighting/README.md` - Python bridge for smart bulb control
- **Project Documentation:** `/docs/` - Design documents, architecture, technical specifications

## Project Structure

```
corazonn/
├── docs/                   # Design documents and specifications
├── firmware/               # ESP32 firmware (heartbeat detection + OSC)
├── audio/                  # Pure Data audio synthesis patches
├── lighting/               # Python lighting control bridge
├── testing/                # Testing tools, simulator, visualization
└── config/                 # Shared configuration files
```

## Development Setup

1. **Testing Infrastructure** (start here)
   ```bash
   cd testing
   pip3 install -r requirements.txt matplotlib
   python3 test_osc_protocol.py       # Unit tests
   python3 esp32_simulator.py --sensors 1 --bpm 60  # Simulate sensor
   python3 ekg_viewer.py --sensor-id 0              # Visualize data
   ```

2. **Firmware Development**
   - See `/firmware/README.md` for ESP32 setup
   - See `/docs/firmware/reference/phase1-firmware-trd.md` for specifications

3. **Audio System**
   - See `/audio/README.md` for Pure Data setup
   - Receives OSC heartbeat messages, generates adaptive soundscape

4. **Lighting Control**
   - See `/lighting/README.md` for Python lighting bridge
   - Controls networked smart bulbs synchronized with heartbeat

## Getting Started

### For Testing & Development

```bash
# Install dependencies
cd testing
pip3 install -r requirements.txt matplotlib

# Run simulator to test OSC protocol
python3 esp32_simulator.py --sensors 1 --bpm 60

# In another terminal, visualize the data
python3 ekg_viewer.py --sensor-id 0
```

### For Hardware Integration

1. Set up ESP32 firmware development environment
2. Flash firmware to sensor units
3. Start the visualization and audio/lighting systems
4. Adjust configuration in `config/` as needed

## OSC Protocol

All components communicate via OSC messages on `/heartbeat/[0-3]` with inter-beat interval (IBI) values in milliseconds.

- Valid IBI range: 300-3000 ms (20-200 BPM)
- Default port: 8000 (configurable)
- Transport: UDP/IPv4

See `/docs/firmware/guides/phase1-04-osc-messaging.md` for detailed specification.

## License

[Add license information]