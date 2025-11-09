# Heartbeat Installation - Lighting Design

## System Overview
Room-scale ambient lighting using Wyze A19 RGB bulbs controlled via Python bridge that receives OSC messages from Pure Data audio server. Lighting provides synchronized visual feedback to heartbeat data through color-coded zones and breathing pulse effects.

**Architecture**: ESP32 (WiFi/OSC) → Linux Server (Pd) → Python Bridge → Wyze Cloud API → 4-6 RGB Bulbs

---

## Component List

### Lighting Hardware
- **4-6x Wyze Color Bulbs A19** (1100 lumens each, RGB+white)
  - Smart bulb with app control
  - WiFi connectivity (2.4GHz)
  - Color temperature: 1800K-6500K
  - RGB color range: Full spectrum
  - Cost: ~$15-20 each
- **4-6x Lamp fixtures** (existing or new)
  - Standard E26/E27 sockets
  - Positioned in corners and/or walls
  - Open/translucent shades preferred for better color diffusion

### Software Components
- **Python 3.8+** (on same Linux server as Pure Data)
  - OSC receiver library: `python-osc`
  - Wyze API library: `wyze-sdk` or custom HTTP client
- **Wyze account** with bulbs registered
- **Home Assistant** (optional, alternative control method)

### Network Requirements
- Bulbs on same WiFi network as server
- Internet access for Wyze Cloud API (unless using local control)
- Port 8001 available for lighting OSC receiver

---

## Physical Installation

### Space Layout
```
Installation area: 12' x 18' (or smaller)
Participant layout: Spoke pattern, heads toward center

        Wall 1 (12')
    [B1]         [B2]
       \         /
        \   P1  /
         \  |  /
      P2--[C]--P4
         /  |  \
        /   P3  \
       /         \
    [B3]         [B4]
        Wall 2 (12')
    
    [B5]   [B6] (optional midpoints)
```

### Bulb Placement Options

**4-Bulb Configuration** (minimum, maps to 4 participants):
- B1: Northwest corner (Participant 1 zone)
- B2: Northeast corner (Participant 4 zone)
- B3: Southwest corner (Participant 2 zone)
- B4: Southeast corner (Participant 3 zone)

**6-Bulb Configuration** (recommended, better coverage):
- B1-B4: Corners as above
- B5: Midpoint of long wall, left side
- B6: Midpoint of long wall, right side

**Mounting Height**:
- 6-8 feet above floor (standard ceiling height)
- Lampshades/fixtures aimed at walls/ceiling for indirect diffusion
- Avoid direct view from lying participants

### Zone Assignment

**Participant to Bulb Mapping** (4-bulb config):
```
Sensor 0 (Participant 1, North)  → Bulb 1 (NW corner)
Sensor 1 (Participant 2, West)   → Bulb 3 (SW corner)
Sensor 2 (Participant 3, South)  → Bulb 4 (SE corner)
Sensor 3 (Participant 4, East)   → Bulb 2 (NE corner)
```

**6-bulb enhancement**: B5 and B6 provide ambient fill, respond to group average

---

## Wyze Bulb Technical Specifications

### Control Methods

**Option A: Wyze Cloud API** (recommended for reliability)
- HTTP REST API calls
- Requires internet connection
- Latency: 200-500ms typical
- No local network dependency
- Rate limits: ~1 request/second per bulb

**Option B: Local LAN Control** (if available)
- Direct UDP/TCP to bulb IP
- Latency: 50-150ms
- Requires reverse engineering or unofficial libraries
- May break with firmware updates

**Option C: Home Assistant Integration**
- Python calls Home Assistant API
- HA controls Wyze bulbs via integration
- Adds extra hop but more reliable
- Latency: 250-600ms

### Bulb Capabilities

**Brightness**:
- Range: 1-100%
- Recommended operating range: 20-80% (leaves headroom for pulses)
- Fade time control: Yes (200ms-2000ms supported)

**Color**:
- RGB: Full spectrum via HSV values
- White: 1800K-6500K color temperature
- Color accuracy: Consumer-grade (adequate for ambient effects)

**Response Time**:
- Command processing: 100-200ms
- Fade execution: As specified (200ms-2000ms)
- Total latency: 300-700ms from OSC message to visible change

**Power**:
- 9W power consumption
- 1100 lumens output
- Power factor: >0.9

---

## OSC Protocol Specification

### Message Format

**Individual pulse command**:
```
Address: /light/N/pulse
Arguments: <int32> ibi_ms
Example: /light/0/pulse 847

Triggers heartbeat fade effect for bulb N
```

**Color update command**:
```
Address: /light/N/color
Arguments: <int32> hue, <int32> saturation, <int32> value
Example: /light/0/color 240 80 60

Hue: 0-360 degrees (0=red, 120=green, 240=blue)
Saturation: 0-100%
Value (brightness): 0-100%
```

**Group mode command**:
```
Address: /light/mode
Arguments: <string> mode_name
Example: /light/mode convergence

Switches all bulbs to coordinated effect mode
```

**Global brightness**:
```
Address: /light/master/brightness
Arguments: <int32> brightness
Example: /light/master/brightness 50

Sets baseline brightness for all bulbs (0-100%)
```

### OSC Port Assignment
```
Pure Data OSC Input: Port 8000 (heartbeat data from ESP32)
Python Lighting Bridge OSC Input: Port 8001 (lighting commands from Pd)
```

### Message Generation in Pure Data

**Heartbeat pulse**:
```
[r beat-N]  // From sensor processing
|
[t b f]     // Trigger + IBI value
|    |
|    [prepend /light/N/pulse]
|    |
|    [oscformat]
|    |
[s to-lighting-bridge]
```

**BPM to color mapping**:
```
[r bpm-smoothed-N]
|
[clip 40 120]           // Clamp to reasonable range
|
[expr (120-$f1)*3]      // Map BPM to hue (240=blue/slow, 0=red/fast)
|
[pack f 80 f]           // Hue, fixed saturation, brightness
|
[prepend /light/N/color]
|
[s to-lighting-bridge]
```

---

## Python Bridge Architecture

### High-Level Design

```
┌─────────────────────────────────────────┐
│  OSC Receiver (port 8001)               │
│  Threaded listener on UDP               │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Message Router                         │
│  Parses OSC, routes to handlers         │
└──────────────┬──────────────────────────┘
               │
     ┌─────────┼─────────┐
     │         │         │
┌────▼───┐ ┌──▼───┐ ┌───▼────┐
│ Pulse  │ │Color │ │ Mode   │
│Handler │ │Handler│ │Handler │
└────┬───┘ └──┬───┘ └───┬────┘
     │        │          │
┌────▼────────▼──────────▼─────────────┐
│  Effect Generator                    │
│  Calculates brightness curves,       │
│  timing, color transitions           │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│  Wyze API Client                     │
│  Authenticates, sends HTTP commands  │
│  Handles rate limiting, retries      │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│  Wyze Cloud → Bulbs                  │
└──────────────────────────────────────┘
```

### Core Modules

**1. osc_receiver.py**
- Listens on port 8001
- Parses OSC messages using `python-osc`
- Dispatches to appropriate handlers
- Non-blocking threaded operation

**2. effect_engine.py**
- **PulseEffect class**: Generates brightness fade curves
- **ColorMapper class**: BPM → hue/saturation calculations
- **ModeManager class**: Coordinated multi-bulb effects
- **TimingCompensator class**: Predicts bulb latency, sends early

**3. wyze_client.py**
- Authenticates with Wyze API (username, password, API key)
- Sends bulb control commands (brightness, color, power)
- Implements rate limiting (1 req/sec/bulb)
- Retry logic on failures
- Caches bulb states to minimize API calls

**4. main.py**
- Initializes all modules
- Config file loading (bulb IDs, credentials)
- Logging setup
- Graceful shutdown handling

### Configuration File

**lighting_config.yaml**:
```yaml
wyze:
  email: "user@example.com"
  password: "secure_password"
  api_key: "wyze_api_key_here"

osc:
  listen_port: 8001
  pd_ip: "127.0.0.1"

bulbs:
  - id: "bulb_mac_address_1"
    name: "NW Corner"
    zone: 0  # Participant 0
    position: [0, 1]  # Normalized coords for spatial effects
  - id: "bulb_mac_address_2"
    name: "NE Corner"
    zone: 3
    position: [1, 1]
  - id: "bulb_mac_address_3"
    name: "SW Corner"
    zone: 1
    position: [0, 0]
  - id: "bulb_mac_address_4"
    name: "SE Corner"
    zone: 2
    position: [1, 0]

effects:
  baseline_brightness: 40  # Percent
  pulse_min: 20            # Percent
  pulse_max: 70            # Percent
  fade_time: 600           # Milliseconds
  latency_compensation: 300  # Milliseconds (measured)

logging:
  level: INFO
  file: "/var/log/heartbeat-lighting.log"
```

---

## Effect Specifications

### Effect 1: Individual Heartbeat Pulse

**Trigger**: `/light/N/pulse <ibi>`

**Behavior**:
1. Calculate current BPM from IBI
2. Map BPM to color (hue): `hue = (120 - bpm) * 3`
   - 40 BPM → hue 240° (blue, calm)
   - 80 BPM → hue 120° (green, neutral)
   - 120 BPM → hue 0° (red, excited)
3. Set saturation: 70-80% (vibrant but not harsh)
4. Brightness curve:
   ```
   baseline → max (200ms linear rise)
   max (sustain 100ms)
   max → baseline (600ms exponential decay)
   ```
5. Send bulb command: `set_color(hue, sat, brightness_curve)`

**Timing**:
- Total effect duration: 900ms (matches heartbeat natural pulse)
- Send command at: `heartbeat_time - latency_compensation`
- Overlapping pulses: Additive (if new beat before fade complete)

**Pseudo-code**:
```python
def handle_pulse(zone, ibi_ms):
    bpm = 60000 / ibi_ms
    hue = clip((120 - bpm) * 3, 0, 360)
    saturation = 75
    
    baseline = config.baseline_brightness
    pulse_max = config.pulse_max
    
    # Generate fade curve
    curve = [
        (0, baseline),           # Start
        (200, pulse_max),        # Peak
        (300, pulse_max),        # Sustain
        (900, baseline)          # Return
    ]
    
    # Compensate for latency
    send_time = now() - config.latency_compensation
    
    # Send to bulb
    bulb = get_bulb_for_zone(zone)
    bulb.set_color_fade(hue, saturation, curve)
```

### Effect 2: Group Breathing

**Trigger**: All bulbs sync to average group BPM

**Calculation**:
```python
avg_bpm = mean([bpm[0], bpm[1], bpm[2], bpm[3]])  # Only connected sensors
avg_ibi_ms = 60000 / avg_bpm
```

**Behavior**:
- All bulbs fade in sync at average group heartbeat rate
- Color: Unified (e.g., warm amber, or mode-dependent)
- Creates whole-room "breathing" effect
- Slower, gentler than individual pulses (longer fade times)

**Activation**:
- Mode selected via Launchpad or default fallback
- Individual pulses still visible as small variations on top

### Effect 3: Convergence Detection

**Trigger**: When 2+ participants' BPMs within 5% of each other

**Detection logic**:
```python
for i in range(4):
    for j in range(i+1, 4):
        if abs(bpm[i] - bpm[j]) / min(bpm[i], bpm[j]) < 0.05:
            converged_pairs.append((i, j))
```

**Behavior**:
- Converged participants' bulbs shift to matching color
- Saturation increases (more vivid)
- Slight brightness boost (+10%)
- Visual reward for synchronization

**Full convergence** (all 4 within 5%):
- All bulbs: Pure white flash (1 second)
- Return to unified color (gold or mode-dependent)
- Special audio trigger sent to Pd (optional)

### Effect 4: Zone Waves

**Trigger**: `/light/mode wave`

**Behavior**:
- Each heartbeat creates brightness wave that ripples to adjacent bulbs
- Timing: Bulb N triggers → Bulb N+1 after 150ms → Bulb N+2 after 300ms
- Creates spatial flow, even with asynchronous heartbeats

**Implementation**:
```python
def handle_pulse_wave(origin_zone, ibi_ms):
    for bulb in all_bulbs:
        distance = spatial_distance(origin_zone, bulb.zone)
        delay_ms = distance * 150  # 150ms per unit distance
        schedule_pulse(bulb, delay_ms)
```

### Effect 5: Mode-Linked Ambient

**Trigger**: Audio mode changes in Pure Data

**Behavior**:
| Audio Mode | Lighting Color | Brightness | Dynamics |
|------------|---------------|------------|----------|
| Percussion | Warm white (3000K) | 50% baseline | Sharp pulses |
| Tonal | Cool blue-purple (hue 240-270) | 40% baseline | Smooth fades |
| Ambient | Deep blue-green (hue 180-210) | 30% baseline | Very slow breathing |
| Breathing | Warm amber (hue 30-45) | 45% baseline | Long inhale/exhale curves |

**Transition**:
- Cross-fade over 2 seconds when mode changes
- Individual heartbeat pulses overlay on top

---

## Brightness and Color Calculations

### BPM to Hue Mapping

**Linear mapping** (default):
```python
def bpm_to_hue(bpm):
    # 40 BPM → 240° (blue)
    # 80 BPM → 120° (green)
    # 120 BPM → 0° (red/orange)
    bpm_clamped = clip(bpm, 40, 120)
    hue = 240 - ((bpm_clamped - 40) / 80) * 240
    return hue
```

**Alternative: Perceptual mapping**:
```python
def bpm_to_hue_perceptual(bpm):
    # Blue (calm): 40-60 BPM
    # Green (neutral): 60-80 BPM  
    # Yellow-orange (active): 80-100 BPM
    # Red (intense): 100-120 BPM
    if bpm < 60:
        return lerp(240, 180, (bpm - 40) / 20)  # Blue to cyan
    elif bpm < 80:
        return lerp(180, 120, (bpm - 60) / 20)  # Cyan to green
    elif bpm < 100:
        return lerp(120, 30, (bpm - 80) / 20)   # Green to orange
    else:
        return lerp(30, 0, (bpm - 100) / 20)    # Orange to red
```

### Brightness Fade Curves

**Exponential decay** (natural heartbeat feel):
```python
def brightness_curve(t, baseline, peak, total_duration):
    # t: time since pulse start (0 to total_duration)
    # Returns brightness value 0-100
    
    attack_time = 200  # ms to peak
    sustain_time = 100  # ms at peak
    
    if t < attack_time:
        # Linear rise
        return baseline + (peak - baseline) * (t / attack_time)
    elif t < attack_time + sustain_time:
        # Sustain at peak
        return peak
    else:
        # Exponential decay
        decay_t = t - (attack_time + sustain_time)
        decay_duration = total_duration - attack_time - sustain_time
        decay_factor = exp(-3 * decay_t / decay_duration)  # e^-3 ≈ 0.05 at end
        return baseline + (peak - baseline) * decay_factor
```

**Linear decay** (simpler, lower CPU):
```python
def brightness_curve_linear(t, baseline, peak, total_duration):
    attack_time = 200
    if t < attack_time:
        return baseline + (peak - baseline) * (t / attack_time)
    else:
        decay_t = t - attack_time
        decay_duration = total_duration - attack_time
        return peak - (peak - baseline) * (decay_t / decay_duration)
```

### Saturation Control

**Fixed saturation** (simplest):
- All effects: 75% saturation (vibrant but not harsh)

**Dynamic saturation**:
```python
def calculate_saturation(bpm, signal_strength):
    # Lower BPM → lower saturation (more pastel)
    # Higher signal strength → higher saturation (more vivid)
    
    base_sat = 50 + (bpm - 40) * 0.3  # 50-74% based on BPM
    signal_bonus = signal_strength * 20  # 0-20% based on signal
    return clip(base_sat + signal_bonus, 40, 90)
```

---

## Latency Compensation

### Measurement Procedure

**Test setup**:
1. Place camera facing one bulb
2. Python script sends brightness command with timestamp
3. Record video at 240fps (or use light sensor)
4. Analyze video frame-by-frame to measure visible change
5. Calculate: `latency = visible_change_time - command_sent_time`

**Expected results**:
- Wyze Cloud API: 300-500ms typical
- Home Assistant: 400-700ms typical  
- Local control (if available): 100-200ms

**Repeat test**:
- Different times of day (network load)
- Different bulbs (consistency check)
- Take median of 10 measurements

### Compensation Strategy

**Predictive sending**:
```python
# In Pure Data, on beat detection:
current_time = millis()
compensated_time = current_time - measured_latency
send_osc_with_timestamp("/light/N/pulse", ibi, compensated_time)
```

**Python bridge**:
```python
def handle_pulse(zone, ibi, timestamp):
    # timestamp already compensated by Pd
    # Send immediately to bulb
    bulb.set_brightness_fade(baseline, peak, fade_time)
```

**Adaptive compensation** (advanced):
```python
class LatencyTracker:
    def __init__(self):
        self.history = []
        self.current_estimate = 300  # Initial guess
    
    def update(self, sent_time, observed_change_time):
        measured = observed_change_time - sent_time
        self.history.append(measured)
        if len(self.history) > 20:
            self.history.pop(0)
        # Exponential moving average
        self.current_estimate = 0.9 * self.current_estimate + 0.1 * measured
    
    def get_compensation(self):
        return self.current_estimate
```

---

## Launchpad Control Integration

### Additional Lighting Controls

**Launchpad layout extension**:
```
ROW 8: [...existing...] [Bright+] [Bright-] [Mode Cycle]
ROW 7: [Light Mode 1] [Light Mode 2] [Light Mode 3] [Light Mode 4]
```

**MIDI to OSC mapping** (in Pure Data):
```
[notein]
|
[sel 57]  // Note 57 = Brightness Up button
|
[t b]
|
[+ 10]  // Increase by 10%
|
[clip 10 100]
|
[prepend /light/master/brightness]
|
[s to-lighting-bridge]
```

### Lighting Modes (mapped to Row 7)

**Mode 1: Individual** (default)
- Each participant's zone pulses independently
- Color based on their BPM
- No coordination between zones

**Mode 2: Group Breathing**
- All zones sync to average BPM
- Unified color
- Whole-room pulse

**Mode 3: Convergence Highlight**
- Individual pulses as baseline
- Synchronized pairs shift to matching colors
- Full sync triggers white flash

**Mode 4: Zone Waves**
- Heartbeats trigger spatial ripples
- Creates flow around room
- More dynamic, less meditative

### LED Feedback on Launchpad

**Lighting mode buttons**:
- Active mode: Bright LED
- Inactive modes: Dim LED
- Mode change: Flash briefly

**Brightness buttons**:
- Pulse on each press
- Brightness proportional to current master level

---

## Pure Data Integration

### Subpatch: pd lighting-output

**Structure**:
```
┌────────────────────────────────────────┐
│  [r beat-0]  [r beat-1]  [r beat-2]    │
│      |          |          |           │
│  [r bpm-0]   [r bpm-1]   [r bpm-2]     │
└──────┬──────────┬──────────┬───────────┘
       │          │          │
┌──────▼──────────▼──────────▼───────────┐
│  Lighting Message Generator            │
│  • /light/N/pulse with IBI             │
│  • /light/N/color with BPM→hue         │
└──────────────┬─────────────────────────┘
               │
┌──────────────▼─────────────────────────┐
│  [udpsend]                             │
│  Destination: 127.0.0.1:8001           │
└────────────────────────────────────────┘
```

**Message generation**:
```
// On each heartbeat (any sensor)
[r beat-N]
|
[t b f]  // Trigger + IBI value
|    |
|    [pack f N]  // IBI, sensor index
|    |
|    [prepend /light]
|    |
|    [prepend N]
|    |
|    [prepend /pulse]
|    |
[oscformat]
|
[s to-udp-lighting]


// Color updates (on BPM change)
[r bpm-smoothed-N]
|
[change]  // Only on BPM change (reduce traffic)
|
[t f f]
|    |
|    [expr (120-$f1)*3]  // BPM to hue
|    |
|    [pack f 75 f]  // Hue, saturation, brightness
|    |
[prepend /light/N/color]
|
[oscformat]
|
[s to-udp-lighting]
```

### UDP Send Configuration

**Pd object**:
```
[udpsend]
|
[connect 127.0.0.1 8001(  // Lighting bridge on same machine
```

**Bandwidth estimate**:
- 4 sensors × 60-120 BPM = 240-480 pulse messages/minute
- 4 sensors × ~1 color update/10 sec = 24 color messages/minute
- Total: ~500 messages/minute = 8-9 messages/second
- Negligible network load (~200 bytes/sec)

---

## Python Bridge Implementation Notes

### Threading Model

**Main thread**: Event loop for OSC receiver
**Worker threads**: One per bulb for API calls

```python
import threading
from queue import Queue

class BulbController:
    def __init__(self, bulb_id):
        self.bulb_id = bulb_id
        self.command_queue = Queue()
        self.worker = threading.Thread(target=self._process_commands)
        self.worker.start()
    
    def _process_commands(self):
        while True:
            cmd = self.command_queue.get()
            self._execute_bulb_command(cmd)
            time.sleep(1.0)  // Rate limit: 1 cmd/sec/bulb
    
    def enqueue_pulse(self, hue, sat, curve):
        self.command_queue.put({
            'type': 'pulse',
            'hue': hue,
            'saturation': sat,
            'curve': curve
        })
```

### Rate Limiting

**Wyze API limits** (estimated):
- 1 request per second per bulb
- 60 requests per minute per account

**Queue-based throttling**:
```python
class RateLimiter:
    def __init__(self, max_per_second):
        self.max_rate = max_per_second
        self.last_call = time.time()
    
    def acquire(self):
        now = time.time()
        time_since_last = now - self.last_call
        if time_since_last < (1.0 / self.max_rate):
            sleep_time = (1.0 / self.max_rate) - time_since_last
            time.sleep(sleep_time)
        self.last_call = time.time()
```

**Command coalescing**:
- If multiple pulses queued for same bulb, merge into single command
- Only send most recent color update if queue backed up

### Error Handling

**API call failures**:
```python
def send_bulb_command(bulb_id, command, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = wyze_api.set_bulb_color(bulb_id, command)
            return response
        except WyzeAPIException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  // Exponential backoff
                continue
            else:
                log_error(f"Failed to control bulb {bulb_id}: {e}")
                return None
```

**Bulb offline handling**:
- If bulb doesn't respond, mark as offline
- Stop sending commands to offline bulbs
- Periodically retry (every 30 seconds)
- Log warning, continue with remaining bulbs

**Network outage**:
- Python bridge continues receiving OSC
- Commands queue up (max queue size: 100)
- When network returns, send most recent state only (not full queue)

---

## Testing Procedures

### Development Testing (No Hardware)

**Test 1: OSC message parsing**
```python
# test_osc_receiver.py
from pythonosc import osc_message_builder, udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 8001)

# Test pulse message
client.send_message("/light/0/pulse", 850)

# Test color message  
client.send_message("/light/0/color", [240, 75, 60])

# Verify: Python bridge logs received messages correctly
```

**Test 2: Effect calculations**
```python
# test_effects.py
from effect_engine import bpm_to_hue, brightness_curve

# Test BPM to hue mapping
assert bpm_to_hue(40) == 240  # Blue
assert bpm_to_hue(80) == 120  # Green
assert bpm_to_hue(120) == 0   # Red

# Test brightness curve
curve = brightness_curve(t=0, baseline=40, peak=70, duration=900)
assert curve == 40  # At start

curve = brightness_curve(t=200, baseline=40, peak=70, duration=900)
assert curve == 70  # At peak

curve = brightness_curve(t=900, baseline=40, peak=70, duration=900)
assert abs(curve - 40) < 5  # Near baseline at end
```

**Test 3: Wyze API mock**
```python
# Mock API for testing without real bulbs
class MockWyzeAPI:
    def __init__(self):
        self.bulb_states = {}
    
    def set_color(self, bulb_id, hue, sat, brightness):
        self.bulb_states[bulb_id] = {
            'hue': hue,
            'saturation': sat,
            'brightness': brightness,
            'timestamp': time.time()
        }
        print(f"Mock: Bulb {bulb_id} → H:{hue} S:{sat} V:{brightness}")
        return True
```

### Hardware Integration Testing

**Test 4: Single bulb control**
- Python bridge running with real Wyze credentials
- Send manual OSC message: `/light/0/pulse 850`
- Verify: Bulb brightens and fades
- Measure: Latency from command send to visible change

**Test 5: All bulbs simultaneously**
- Send pulse commands to all 4 zones at once
- Verify: All bulbs respond without conflicts
- Check: No API rate limiting errors in logs

**Test 6: Sustained pulse stream**
- Simulate continuous heartbeats (60 BPM per sensor)
- Run for 5 minutes
- Verify: No command queue buildup, all pulses executed
- Monitor: Python bridge CPU/memory usage

**Test 7: Latency measurement**
- Use light sensor or high-speed camera
- Send pulse command with precise timestamp
- Measure actual bulb response time
- Calculate compensation offset
- Update config: `latency_compensation` value

**Test 8: BPM to color mapping**
- Manually send BPM values from 40-120
- Verify color progression: blue → green → yellow → red
- Validate smooth transitions

### System Integration Testing

**Test 9: Pd to Python to bulbs**
- Full system: ESP32 sensors → Pd → Python bridge → bulbs
- Single participant with sensor
- Verify: Heartbeats trigger bulb pulses
- Check: Color matches heart rate (calm = blue, fast = red)

**Test 10: Multi-participant coordination**
- 2-4 people with sensors
- Verify: Each zone responds independently
- Test: Convergence detection (sync two people's BPMs)
- Validate: Bulbs shift to matching color

**Test 11: Mode switching**
- Start in individual mode
- Switch to group breathing via Launchpad
- Verify: All bulbs sync to average BPM
- Switch to wave mode
- Verify: Ripple effects visible

**Test 12: Extended duration**
- Run full system for 30+ minutes
- Monitor: Python bridge stability (no memory leaks)
- Check: Bulb responsiveness doesn't degrade
- Verify: No dropped commands in logs

### Acceptance Criteria

- [ ] Bulb responds to pulse command within 500ms (95th percentile)
- [ ] All 4-6 bulbs operate simultaneously without interference
- [ ] Color accurately reflects BPM (visual inspection)
- [ ] Brightness fades smooth and natural (no flicker)
- [ ] Mode switching works reliably (<2 sec transition)
- [ ] 30-minute continuous operation without failures
- [ ] Python bridge auto-recovers from API errors
- [ ] Latency compensation reduces perceived delay to <300ms
- [ ] Launchpad controls responsive (<200ms)

---

## Deployment Configuration

### Systemd Service

**File**: `/etc/systemd/system/heartbeat-lighting.service`

```ini
[Unit]
Description=Heartbeat Installation Lighting Bridge
After=network.target heartbeat-audio.service
Requires=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/heartbeat
ExecStart=/usr/bin/python3 /home/pi/heartbeat/lighting_bridge/main.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Enable and start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable heartbeat-lighting
sudo systemctl start heartbeat-lighting
```

### Directory Structure

```
/home/pi/heartbeat/
├── heartbeat-main.pd          # Main Pd patch
├── lighting_bridge/           # Python bridge
│   ├── main.py
│   ├── osc_receiver.py
│   ├── effect_engine.py
│   ├── wyze_client.py
│   ├── config.yaml
│   └── requirements.txt
├── logs/
│   ├── lighting.log
│   └── wyze_api.log
└── backup/
    └── [timestamped configs]
```

### Python Dependencies

**requirements.txt**:
```
python-osc==1.8.1
pyyaml==6.0
requests==2.31.0
wyze-sdk==1.3.0  # Or alternative Wyze library
```

**Installation**:
```bash
cd /home/pi/heartbeat/lighting_bridge
pip3 install -r requirements.txt
```

### Environment Variables

**For Wyze credentials** (alternative to config file):
```bash
export WYZE_EMAIL="user@example.com"
export WYZE_PASSWORD="secure_password"
export WYZE_API_KEY="api_key_here"
```

**Security note**: Use environment variables or keyring for production, not plaintext config

---

## Monitoring and Debugging

### Logging Configuration

**Python logging setup**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/heartbeat/logs/lighting.log'),
        logging.StreamHandler()  # Also print to console
    ]
)

logger = logging.getLogger('heartbeat-lighting')
```

**Log levels**:
- DEBUG: All OSC messages, effect calculations
- INFO: Bulb commands sent, mode changes
- WARNING: API errors, rate limit hits
- ERROR: Bulb offline, critical failures

### Metrics to Track

**Per-session statistics**:
- Total pulses received: 4 counters (one per sensor)
- Bulb commands sent: 6 counters (one per bulb)
- API failures: Count and timestamps
- Average latency: Running average of command → visible change
- Peak brightness: Maximum value reached per bulb

**Real-time monitoring**:
```bash
# Tail logs
tail -f /home/pi/heartbeat/logs/lighting.log

# Watch Python process
top -p $(pgrep -f lighting_bridge)

# Check OSC traffic
sudo tcpdump -i lo port 8001 -A
```

### Debug Mode

**Enable verbose logging**:
```yaml
# In config.yaml
logging:
  level: DEBUG
  
debug:
  log_osc_messages: true
  log_effect_calculations: true
  log_api_requests: true
```

**Output example**:
```
2025-11-06 14:32:01 - DEBUG - OSC received: /light/0/pulse 847
2025-11-06 14:32:01 - DEBUG - BPM: 70.8, Hue: 147.6
2025-11-06 14:32:01 - DEBUG - Brightness curve: [40, 52, 64, 70, 68, 65, ...]
2025-11-06 14:32:01 - INFO  - Sending to Bulb 1: H:148 S:75 V:70
2025-11-06 14:32:01 - DEBUG - API response: 200 OK, latency: 287ms
```

---

## Failure Modes and Recovery

### Common Issues

| Symptom | Cause | Recovery |
|---------|-------|----------|
| No bulb response | Python bridge not running | `systemctl restart heartbeat-lighting` |
| | Bulb offline | Check bulb power, WiFi connection |
| | Wrong bulb ID in config | Verify MAC addresses in config.yaml |
| Delayed response (>1 sec) | High latency | Increase `latency_compensation` value |
| | Rate limiting | Reduce message frequency in Pd |
| All bulbs same color | Wrong zone mapping | Check bulb-to-zone assignments |
| | Group mode active | Switch to individual mode |
| Flickering | Overlapping pulses | Increase pulse duration |
| | API retry spam | Check logs, fix network issues |
| Color wrong | BPM calculation error | Verify BPM values in Pd output |
| | Hue mapping inverted | Check `bpm_to_hue()` formula |
| Python crash | Uncaught exception | Check logs, systemd auto-restarts |
| | Memory leak | Monitor with `top`, restart if needed |
| Bulb unresponsive | Firmware issue | Power cycle bulb |
| | Network congestion | Restart router |

### Auto-Recovery Mechanisms

**Systemd watchdog**:
```python
import systemd.daemon

def heartbeat_loop():
    while True:
        # ... do work ...
        systemd.daemon.notify('WATCHDOG=1')  # Keep-alive
        time.sleep(5)
```

**API retry with backoff**:
- First failure: Retry after 1 second
- Second failure: Retry after 2 seconds
- Third failure: Retry after 4 seconds
- After 3 failures: Mark bulb offline, log error

**Queue overflow protection**:
```python
if command_queue.qsize() > 100:
    logger.warning("Queue overflow, dropping old commands")
    # Keep only most recent 10 commands
    command_queue = Queue()
    for cmd in most_recent_commands[-10:]:
        command_queue.put(cmd)
```

---

## Performance Optimization

### CPU Usage

**Target**: <5% CPU on Raspberry Pi 4

**Optimization strategies**:
- Use linear brightness curves (not exponential) if CPU constrained
- Coalesce rapid color updates (send only every 500ms)
- Pre-calculate color tables (BPM → hue lookup)
- Batch API calls when possible (single request for multiple bulbs)

**CPU monitoring**:
```bash
# Check Python bridge CPU usage
ps aux | grep lighting_bridge

# Profile hot spots
python3 -m cProfile -s cumtime main.py
```

### Memory Usage

**Target**: <50MB RAM

**Memory-efficient practices**:
- Fixed-size command queues (max 100 entries)
- No unbounded logging buffers (rotate logs)
- Clear effect history after each pulse
- Limit brightness curve sample points (20-50 samples max)

### Network Bandwidth

**Estimate**:
- OSC input: 500 messages/min × 50 bytes = 25 KB/min (negligible)
- Wyze API: 240-480 commands/min × 500 bytes = 120-240 KB/min (negligible)

**Total**: <5 KB/sec, well within WiFi capacity

---

## Future Enhancements

### Software Improvements

**Local Wyze control**:
- Reverse-engineer local UDP protocol
- Reduce latency to <100ms
- Eliminate internet dependency

**Effect presets**:
- Saveable lighting "scenes"
- Quick recall via Launchpad
- Exportable config files

**Web dashboard**:
- Real-time bulb status display
- Manual bulb control (testing)
- Effect parameter tuning
- Session statistics

**Data logging**:
- Record all lighting events to database
- Post-session analysis
- Heatmaps of activity by zone
- Correlation with audio metrics

**Adaptive effects**:
- Learn optimal color mappings from participant feedback
- Auto-adjust latency compensation over time
- Predict next heartbeat for proactive sending

### Hardware Additions

**More bulbs**:
- 8-10 bulbs for larger spaces
- Mid-wall positions for better coverage
- Ceiling-mounted spots for directional effects

**DMX integration**:
- Professional stage lighting control
- Faster response times (<50ms)
- More precise color/brightness
- Requires DMX interface (~$50)

**Addressable LED strips**:
- Supplement bulbs with WS2812B strips
- Perimeter lighting for immersion
- Controlled by separate ESP32 or same Python bridge

### Interaction Modes

**Participant color selection**:
- Each person picks their zone color at start
- Launchpad pads become color palette
- Personal customization

**Breathing coach mode**:
- Lighting leads ideal breathing rhythm
- Participants try to match
- Feedback when synchronized

**Narrative lighting**:
- Scripted color journey over 10+ minutes
- Introduction (cool blues) → Exploration (warm spectrum) → Convergence (unified white) → Resolution (golden amber)

**Competitive mode**:
- Fastest heart rate gets brightest bulb
- Gamification for active engagement

---

## Installation Checklist

### Pre-Installation (1 week before)

- [ ] Purchase 4-6 Wyze Color Bulbs A19
- [ ] Install bulbs in lamp fixtures around space
- [ ] Position fixtures in corners/walls (6-8 ft height)
- [ ] Test bulbs via Wyze app (connectivity, color range)
- [ ] Install Python dependencies on Raspberry Pi
- [ ] Configure Wyze account credentials
- [ ] Test bulb control via Python script
- [ ] Measure bulb latency (camera or light sensor)
- [ ] Update `latency_compensation` in config
- [ ] Build Pd lighting-output subpatch
- [ ] Test OSC communication (Pd to Python)
- [ ] Configure systemd service
- [ ] Run extended test (30+ minutes)

### Day-Of Setup (Festival)

- [ ] Power on all lamp fixtures
- [ ] Verify bulbs on WiFi network (Wyze app)
- [ ] Start Python lighting bridge (`systemctl start`)
- [ ] Verify bridge receiving OSC (check logs)
- [ ] Test single bulb response (manual OSC command)
- [ ] Test all bulbs simultaneously
- [ ] Set baseline brightness (40-50% recommended)
- [ ] End-to-end test: sensor → audio → lighting
- [ ] Adjust brightness for room ambient light level
- [ ] Test mode switching via Launchpad
- [ ] Verify convergence detection with 2 people
- [ ] Document working configuration (bulb IDs, IPs)

### During Operation

- [ ] Monitor Python bridge status (`systemctl status`)
- [ ] Watch for bulb offline warnings in logs
- [ ] Adjust brightness if too bright/dim (Launchpad controls)
- [ ] Switch lighting modes based on audio modes
- [ ] Be prepared to restart bridge if issues arise

### Post-Festival

- [ ] Save session logs for analysis
- [ ] Document any issues encountered
- [ ] Update config for future improvements
- [ ] Backup working configuration
- [ ] Remove bulbs from Wyze account (if temporary install)

---

## Cost Breakdown

| Item | Quantity | Unit Cost | Total |
|------|----------|-----------|-------|
| Wyze Color Bulb A19 | 4-6 | $15-20 | $60-120 |
| Lamp fixtures (if needed) | 4-6 | $10-20 | $40-120 |
| Python libraries | - | Free | $0 |
| Development time | - | - | - |
| **Total** | | | **$100-240** |

**Within budget**: Yes, leaves $260-400 for sensor/audio hardware

---

## Troubleshooting Quick Reference

| Symptom | Quick Fix |
|---------|-----------|
| Bulb not responding | 1. Check power, 2. Verify WiFi, 3. Restart bridge |
| Delayed (>1 sec) | Increase `latency_compensation` in config |
| Wrong colors | Check BPM values in Pd, verify hue formula |
| All bulbs synced incorrectly | Verify zone mapping in config.yaml |
| Python crash | `journalctl -u heartbeat-lighting` for errors |
| Flickering | Reduce message rate in Pd or increase fade time |
| API rate limit errors | Add delay in Python or reduce Pd message frequency |

---

## Reference Resources

### Wyze Integration
- **Wyze Developer API**: https://wyze-developers.com/
- **python-wyze-sdk**: https://github.com/shauntarves/wyze-sdk-python
- **Home Assistant Wyze**: https://www.home-assistant.io/integrations/wyze/

### OSC Libraries
- **python-osc**: https://pypi.org/project/python-osc/
- **OSC specification**: http://opensoundcontrol.org/

### Color Theory
- **HSV color model**: https://en.wikipedia.org/wiki/HSL_and_HSV
- **Color psychology**: Warm colors (red/orange) = excitement, Cool colors (blue/green) = calm

### Smart Home Control
- **Home Assistant API**: https://developers.home-assistant.io/docs/api/rest/
- **MQTT for IoT**: https://mqtt.org/ (alternative control protocol)

---

*Document Version: 1.0*
*Last Updated: 2025-11-06*
*Companion to: heartbeat-input-hardware-design.md, heartbeat-firmware-design.md, heartbeat-audio-output-design.md*
*Implementation: Python 3.8+ with Wyze SDK on Linux*