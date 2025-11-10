# Heartbeat Lighting Bridge - Phase 1 MVP

Python OSC bridge for controlling smart RGB lighting based on heartbeat data from the Pure Data audio pipeline.

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configure Backend

```bash
# Copy example config
cp config.yaml.example config.yaml

# Edit config.yaml and set your backend choice
```

### 3. Discover Bulbs

**For Kasa (TP-Link) bulbs:**
```bash
python3 tools/discover-kasa.py
```

**For Wyze bulbs:**
```bash
python3 tools/discover-wyze.py --email your@email.com --password yourpassword
```

**For WLED devices:**
```bash
python3 tools/discover-wled.py
```

Copy the discovered IPs/MACs into your `config.yaml` file.

### 4. Run the Bridge

```bash
cd lighting
python3 src/main.py
```

The bridge listens on port 8001 for OSC messages from the Pure Data audio pipeline.

## Backend Selection

Choose one backend in `config.yaml`:

| Backend | Control | Latency | Drop Rate | Best For |
|---------|---------|---------|-----------|----------|
| **kasa** | Local TCP | ~100ms | Minimal | Production (recommended) |
| **wyze** | Cloud HTTP | ~400ms | 50-75% | Wyze bulb owners |
| **wled** | Local UDP | ~5ms | None | DIY LED strips |

**Recommendation:** Use Kasa backend for production installations.

## Configuration

Edit `config.yaml` to:
- Select backend (`lighting.backend`)
- Configure OSC port (default: 8001)
- Adjust effect parameters (brightness, pulse timing)
- Map bulbs to zones (0-3)

**Config validation:**
- Zones must be 0-3 and unique
- Brightness/saturation: 0-100
- Hue: 0-360
- Port: 1-65535

## Integration with Audio Pipeline

The lighting bridge receives OSC messages from the Pure Data audio pipeline:

```
Pure Data Patch (heartbeat-main.pd)
  ↓ OSC/UDP port 8001
Lighting Bridge (this component)
  ↓ Backend protocol
Smart RGB Bulbs (4 zones)
```

**OSC Message Format:**
```
/light/N/pulse <ibi_ms>
```
Where N is zone (0-3) and ibi_ms is inter-beat interval in milliseconds.

## Testing

**Run unit tests:**
```bash
cd lighting
python3 -m pytest tests/ -v
```

**Standalone OSC test** (with bridge running):
```bash
python3 tests/test_standalone.py
```

## Troubleshooting

**Port 8001 already in use:**
```bash
# Find process using port
lsof -ti:8001 | xargs kill
```

**Kasa authentication failed:**
- Check bulb IP addresses in config.yaml
- Verify bulbs are on same network
- Run discovery tool to confirm IPs

**No bulbs pulse:**
- Check zone mapping in config.yaml
- Verify OSC messages arriving (check logs)
- Confirm backend section matches selected backend

**High drop rate:**
- Expected for Wyze backend (cloud latency)
- Check logs/lighting.log for details

## Architecture

```
OSC Receiver → Effect Calculation → Backend Interface → Bulbs
  (port 8001)   (BPM→hue mapping)   (abstraction)      (hardware)
```

The backend abstraction allows swapping between Kasa/Wyze/WLED without changing effect logic.

## File Organization

```
lighting/
├── src/
│   ├── main.py              # Entry point
│   ├── osc_receiver.py      # OSC handling + effects
│   └── backends/
│       ├── base.py          # LightingBackend interface
│       ├── kasa_backend.py  # Kasa implementation
│       ├── wyze_backend.py  # Wyze implementation
│       └── wled_backend.py  # WLED implementation
├── tools/                   # Discovery utilities
├── tests/                   # Unit + integration tests
├── logs/                    # Runtime logs
├── config.yaml             # Your config (gitignored)
└── config.yaml.example     # Template
```

## Reference

- **TRD:** `/docs/lighting/reference/trd.md` - Complete technical specification
- **Design:** `/docs/lighting/reference/design.md` - Full system vision
- **Tasks:** `/docs/lighting/tasks/phase1-mvp.md` - Implementation checklist
