# Lighting Configuration

Configuration file: `amor/config/lighting.yaml`

## Zone Configuration

Maps 4 PPG sensors to color zones:

```yaml
zones:
  0:
    name: "Person 1"
    hue: 0          # Red

  1:
    name: "Person 2"
    hue: 320        # Deep Pink/Magenta

  2:
    name: "Person 3"
    hue: 280        # Purple/Violet

  3:
    name: "Person 4"
    hue: 240        # Deep Blue
```

**Hue Range:** 0-360 (HSV color wheel degrees)

## Kasa Smart Bulb Configuration

### Bulb Discovery

Find bulb IP addresses on your network:

```bash
python3 lighting/tools/discover-kasa.py
```

### Bulb Configuration

```yaml
kasa:
  bulbs:
    - ip: "192.168.1.100"
      name: "NW Corner"
      zone: 0

    - ip: "192.168.1.101"
      name: "NE Corner"
      zone: 1

    - ip: "192.168.1.102"
      name: "SW Corner"
      zone: 2

    - ip: "192.168.1.103"
      name: "SE Corner"
      zone: 3
```

**Parameters:**
- `ip` - Bulb IP address (required)
- `name` - Descriptive name (required)
- `zone` - Zone assignment 0-3 (required)

Multiple bulbs can be assigned to the same zone.

## Lighting Effects Configuration

```yaml
effects:
  baseline_brightness: 40    # Resting brightness (0-100%)
  pulse_max: 70              # Peak brightness during pulse (0-100%)
  baseline_saturation: 75    # Color saturation (0-100%)
  attack_time_ms: 200        # Rise time to peak brightness
  sustain_time_ms: 100       # Hold time at peak brightness
```

### Effect Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `baseline_brightness` | 0-100 | Brightness when no pulse detected |
| `pulse_max` | 0-100 | Maximum brightness during pulse |
| `baseline_saturation` | 0-100 | Color saturation level |
| `attack_time_ms` | 0-5000 | Time to reach peak brightness (ms) |
| `sustain_time_ms` | 0-5000 | Time to hold at peak brightness (ms) |

**Note:** Decay back to baseline is automatic.

## Lighting Programs

Select active lighting program:

```yaml
program:
  active: "soft_pulse"
  config: {}
```

### Available Programs

- `soft_pulse` - Smooth brightness pulsing on heartbeat (default)
- `rotating_gradient` - Continuous rotating color gradient with beat pulses
- `breathing_sync` - All zones breathe together at average BPM
- `convergence` - Highlights synchronized zones
- `wave_chase` - Beat creates traveling wave through adjacent zones
- `intensity_reactive` - Brightness and saturation respond to PPG signal quality

## Command-Line Options

```bash
python -m amor.lighting [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | 8002 | OSC beat event port |
| `--config` | `amor/config/lighting.yaml` | Configuration file path |

### Examples

```bash
# Basic usage
python -m amor.lighting

# Custom configuration
python -m amor.lighting --config custom_lighting.yaml

# Custom port
python -m amor.lighting --port 9002
```

## Network Requirements

- All bulbs must be on the same network as the host running `amor.lighting`
- Bulbs must have static IP addresses or DHCP reservations
- Firewall must allow outbound connections on port 9999 (Kasa protocol)
