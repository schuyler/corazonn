# corazonn

**Amor** - A real-time biometric art system that transforms heartbeats into synchronized audio and lighting experiences.

## Architecture

ESP32 sensors capture raw PPG (photoplethysmogram) data and stream it via OSC to a Python processor that detects heartbeats in real-time. Beat events drive audio synthesis and networked lighting control.

## Project Structure

```
corazonn/
├── amor/                   # Python processor, lighting, audio, control
│   ├── processor.py        # PPG processing and beat detection
│   ├── lighting.py         # Smart bulb control via OSC
│   ├── lighting_programs.py # 6 stateful lighting programs
│   ├── audio.py            # Audio synthesis engine
│   ├── launchpad.py        # Novation Launchpad control surface
│   └── simulator/          # PPG, Kasa, Launchpad emulators
├── firmware/amor/          # ESP32 firmware (raw PPG streaming)
├── audio/                  # Audio samples and utilities
├── testing/                # Protocol validation and test utilities
└── docs/                   # Technical specifications
```

## Quick Start

### Run the full system with simulators

```bash
# Install dependencies
uv sync

# Start all services (processor, audio, lighting, simulators)
uvicorn --env-file Procfile
```

### Hardware Setup

1. **Flash ESP32 firmware:**
   ```bash
   cd firmware/amor
   # Copy and configure wifi credentials
   cp include/config.h.example include/config.h
   # Edit config.h with your WiFi and server details
   platformio run --target upload
   ```

2. **Start the processor:**
   ```bash
   python -m amor.processor
   ```

3. **Start lighting control:**
   ```bash
   python -m amor.lighting
   ```

See `docs/firmware/amor-technical-reference.md` for detailed hardware setup.

## OSC Protocol

### PPG Data (ESP32 → Processor)
- Address: `/ppg/{ppg_id}` where ppg_id is 0-3
- Arguments: `[sample1, sample2, sample3, sample4, sample5, timestamp_ms]`
- Port: 8000
- Rate: 10 bundles/sec (50 samples/sec per sensor)
- Sample range: 0-4095 (12-bit ADC)

### Beat Events (Processor → Lighting/Audio)
- Address: `/beat/{ppg_id}`
- Arguments: `[ibi_ms]` (inter-beat interval in milliseconds)
- Port: 8002
- Valid IBI range: 300-3000 ms (20-200 BPM)

### Lighting Control (User → Lighting)
- Port: 8003
- Programs: soft_pulse, rotating_gradient, breathing_sync, convergence, wave_chase, intensity_reactive

See `docs/firmware/amor-technical-reference.md` for complete protocol specification.

## License

[Add license information]