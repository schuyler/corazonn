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

Find bulb names on your network (configuration uses names, not IPs):

```bash
python3 testing/discover-kasa.py
```

**Note:** The lighting system discovers bulbs by name dynamically, so you don't need static IP addresses. Just ensure bulbs have unique, recognizable names set in the Kasa app.

### Bulb Configuration

```yaml
kasa:
  bulbs:
    - name: "Corazon 0"
      zone: 0

    - name: "Corazon 1"
      zone: 1

    - name: "Corazon 2"
      zone: 2

    - name: "Corazon 3"
      zone: 3
```

**Parameters:**
- `name` - Bulb name as configured in Kasa app (required, must match exactly)
- `zone` - Zone assignment 0-3 (required)

**Notes:**
- Bulbs are discovered dynamically by name at startup
- IP addresses are resolved automatically
- Multiple bulbs can be assigned to the same zone

## Lighting Effects Configuration

```yaml
effects:
  baseline_brightness: 40    # Resting brightness (0-100%)
  pulse_max: 70              # Peak brightness during pulse (0-100%)
  baseline_saturation: 75    # Color saturation (0-100%)
```

### Effect Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `baseline_brightness` | 0-100 | Brightness when no pulse detected |
| `pulse_max` | 0-100 | Maximum brightness during pulse |
| `baseline_saturation` | 0-100 | Color saturation level |

### Hardware Constraints

**TP-Link Kasa bulbs require >= 2000ms for smooth transitions.** All lighting programs automatically adapt fade durations to respect this constraint:

- Beat-triggered programs use BPM-adaptive fades (smallest integer multiple of IBI >= 2000ms)
- Continuous-update programs throttle to 2-second intervals with smooth transitions
- At 70 BPM: fade duration = 3 beats (2571ms)
- At 120 BPM: fade duration = 4 beats (2000ms)

## Lighting Programs

Select active lighting program:

```yaml
program:
  active: "fast_attack"
  config: {}
```

### Available Programs

**Beat-Synchronized Programs:**

- **`fast_attack`** (default) - Instant attack to peak, BPM-adaptive smooth fade to baseline
  - Quick, responsive feel with smooth decay
  - Fade duration automatically scales with heart rate (2-4 beats)
  - **Per-zone:** Each zone pulses independently when its PPG sensor detects a beat

- **`slow_pulse`** - Symmetric fade-in and fade-out with peaks synchronized to beats
  - Smooth rise to peak (2-3 beats), hold at peak, smooth fade to baseline (2-3 beats)
  - Phase protection: ignores beats during active fades
  - Meditative, breathing-like effect
  - **Per-zone:** Each zone has independent state machine

- **`intensity_slow_pulse`** - Slow pulse with BPM and intensity reactivity
  - Combines slow_pulse state machine with reactive colors
  - Hue changes with BPM (blue=calm/40 BPM, red=active/120 BPM)
  - Saturation modulates with signal quality
  - **Per-zone:** Each zone reacts independently with own colors and timing

**Continuous Effect Programs:**

- **`rotating_gradient`** - Continuously rotating color gradient
  - Updates every 2 seconds with smooth hue transitions
  - Default rotation speed: 30°/sec (12 second full rotation)
  - Beat pulses overlay on current gradient color
  - **Synchronized gradient, per-zone pulses:** Gradient rotates uniformly, each zone pulses independently

- **`breathing_sync`** - All zones breathe together at average group BPM
  - Synchronized whole-room breathing effect
  - Updates every 2 seconds with smooth transitions
  - Encourages group heart rate synchronization
  - **Fully synchronized:** All zones display identical color and brightness

**Interactive Programs:**

- **`convergence`** - Highlights when participants' heart rates synchronize
  - Detects convergence when BPMs within 5% threshold
  - Converged zones shift to gold color
  - Non-converged zones drift back to defaults
  - **Per-zone pulses, group-reactive colors:** Each zone pulses independently, colors respond to group synchronization

- **`wave_chase`** - Sequential pulse cascade through zones
  - Beat triggers staggered pulses across 4 zones
  - Default stagger: 500ms between zones
  - Creates ripple effect around room
  - **Per-zone trigger, synchronized cascade:** One zone's beat creates coordinated effect across all zones

- **`intensity_reactive`** - Fast attack with BPM/intensity reactive colors
  - Hue responds to BPM (blue=calm, red=active)
  - Saturation responds to signal quality
  - Fast attack smooth fade for pulses
  - **Per-zone:** Each zone reacts independently with own colors based on its PPG signal

### Program Configuration

Programs can be configured with optional parameters:

```yaml
program:
  active: "rotating_gradient"
  config:
    rotation_speed: 15.0  # Degrees per second (slower rotation)
```

**Configuration Options:**

- `rotating_gradient`:
  - `rotation_speed`: Rotation speed in degrees/second (default: 30.0)

- `breathing_sync`:
  - `base_hue`: Breathing color hue (default: 200, calm blue)
  - `min_brightness`: Minimum brightness (default: 20)
  - `max_brightness`: Maximum brightness (default: 60)

- `convergence`:
  - `convergence_threshold`: BPM difference ratio for convergence (default: 0.05)
  - `convergence_hue`: Hue for converged zones (default: 45, gold)
  - `convergence_saturation`: Saturation for converged zones (default: 90)

- `wave_chase`:
  - `stagger_ms`: Time offset between zone pulses (default: 500ms)

- `intensity_reactive`, `intensity_slow_pulse`:
  - `min_saturation`: Minimum saturation for low intensity (default: 50)
  - `max_saturation`: Maximum saturation for high intensity (default: 100)

### Switching Programs at Runtime

Use OSC to switch programs without restarting:

```bash
# Switch to slow pulse
oscsend localhost 8003 /program s slow_pulse

# Switch to rotating gradient
oscsend localhost 8003 /program s rotating_gradient
```

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

- All bulbs must be on the same local network as the host running `amor.lighting`
- Bulbs are discovered via UDP broadcast (no static IPs required)
- Firewall must allow:
  - UDP broadcast for bulb discovery
  - Outbound TCP connections on port 9999 (Kasa protocol)
- Bulbs must have unique names configured in the Kasa app

## Troubleshooting

**Bulb not found:**
- Verify bulb name matches exactly (case-sensitive)
- Check bulb is on same network
- Run `python3 testing/discover-kasa.py` to see available bulbs
- Ensure firewall allows UDP broadcast

**Choppy or laggy transitions:**
- All programs automatically respect 2s minimum transition time
- Network latency adds ~100ms control delay
- Beat rate >60 BPM may cause overlapping fades (expected behavior)
