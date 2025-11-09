# Heartbeat Installation - Audio Output Design

## System Overview
Linux audio server (Raspberry Pi or NUC) receives OSC heartbeat messages via WiFi, processes them in Pure Data to generate synchronized audio output, and routes stereo signal through USB audio interface to mixer and speakers. Optional MIDI controller provides real-time control over sound palettes and interaction modes.

**Architecture**: ESP32 (WiFi/OSC) → Linux Server (Pd) → USB Audio Interface → Mixer → Speakers

---

## Component List

### Core Audio Components
- **1x Raspberry Pi 4** (2GB+ RAM) or NUC with Debian
  - Provides: Pure Data host, OSC receiver, audio processing
  - WiFi connectivity for private network
- **1x USB Audio Interface** (Focusrite Scarlett 2i2 1st gen or similar)
  - Balanced 1/4" TRS outputs to mixer
  - 48kHz/24-bit capability
  - Linux ALSA-compatible
- **1x Novation Launchpad** (any generation, ~$30-60 used)
  - 64 velocity-sensitive pads
  - RGB LED feedback
  - USB-powered

### Connectivity
- **2x TRS cables** (1/4" balanced, 3-6ft)
  - Audio interface to mixer
- **2x USB cables** (Type A to B/Micro/C)
  - Audio interface and Launchpad to Pi/NUC
- **1x Ethernet cable** (optional, for wired network)
  - Fallback if WiFi unreliable

### Power & Backup
- **1x USB power bank** (10,000mAh minimum)
  - UPS for Pi, 4+ hour runtime
- **1x USB stick** (8GB+)
  - Backup Pd patches, sample libraries

### Audio Content
- **Sample libraries** (sourced from Freesound.org, BBC Sound Effects)
  - Percussion: kicks, snares, hats, claps, toms
  - Tonal: bells, chimes, singing bowls, synthesized tones
  - Ambient: drones, textures, nature sounds, breath
  - One-shots: special effects for conducting/events

---

## Network Configuration

### Private WiFi Setup
```
SSID: heartbeat-install
Password: [secure password]
Channel: 1 or 6 or 11 (least congested)
Mode: 2.4GHz only (ESP32 compatibility)
```

### IP Addressing
| Device | IP Address | Role |
|--------|-----------|------|
| WiFi Router | 192.168.50.1 | Gateway |
| ESP32 (sensors) | 192.168.50.10 | OSC sender |
| Pi/NUC (audio) | 192.168.50.100 | OSC receiver |
| Laptop (optional) | DHCP | Control/monitoring |

### OSC Configuration
```
Protocol: UDP
Port: 8000
Message format: /heartbeat/N <int32>ibi_ms
Accept from: Any IP on 192.168.50.0/24 network
```

---

## Pure Data Architecture

### Main Patch Structure

```
┌─────────────────────────────────────────┐
│  OSC Input                              │
│  [udpreceive 8000] → [unpackOSC]       │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│  Message Router                         │
│  [route /heartbeat/0 /heartbeat/1       │
│         /heartbeat/2 /heartbeat/3]      │
└─┬────┬────┬────┬─────────────────────────┘
  │    │    │    │
┌─▼────▼────▼────▼─────────────────────────┐
│  Per-Sensor Processing (4 channels)     │
│  • IBI validation (300-3000ms)          │
│  • BPM calculation (60000/IBI)          │
│  • Disconnection timeout (5 sec)        │
│  • Beat trigger generation              │
└─┬────┬────┬────┬─────────────────────────┘
  │    │    │    │
┌─▼────▼────▼────▼─────────────────────────┐
│  Sound Generation                        │
│  • Sample playback [readsf~]            │
│  • Synthesis oscillators [osc~]         │
│  • Envelopes [line~] [vline~]           │
└─┬────┬────┬────┬─────────────────────────┘
  │    │    │    │
┌─▼────▼────▼────▼─────────────────────────┐
│  Spatial Positioning                     │
│  • Pan law: constant power (-3dB)       │
│  • Positions: L=0, L/C=0.33, R/C=0.67, R=1│
└─┬────┬────┬────┬─────────────────────────┘
  │    │    │    │
┌─▼────▼────▼────▼─────────────────────────┐
│  Effects Processing                      │
│  • Reverb [freeverb~]                   │
│  • Limiter [hip~] + [clip~]             │
│  • EQ [bp~] [lop~] [hip~]               │
└─┬──────────────────────────────────────┬─┘
  │                                      │
┌─▼──────────────────────────────────────▼─┐
│  Master Output                           │
│  [dac~ 1 2] → USB Audio Interface        │
└──────────────────────────────────────────┘
```

### Subpatches Organization

**pd osc-input**: OSC message reception and parsing
- Network receive object
- Message validation
- Error handling

**pd sensor-N-process** (4 instances): Per-sensor signal processing
- IBI validation and filtering
- BPM calculation with smoothing
- Disconnection detection
- Beat event generation

**pd sound-engine**: Audio generation core
- Sample loading and playback
- Synthesis voice management
- Envelope generators
- Mode switching logic

**pd spatial-mixer**: Stereo positioning
- 4-channel to 2-channel mixdown
- Constant-power panning
- Individual channel level control

**pd effects-chain**: Master effects
- Reverb (adjustable wet/dry)
- Compression/limiting
- EQ (optional)

**pd midi-control**: Launchpad interface
- MIDI input handling
- LED feedback output
- Parameter mapping

---

## OSC Message Handling

### Message Format
```
Address pattern: /heartbeat/N
Type tag: i (int32)
Argument: IBI in milliseconds
Example: /heartbeat/0 847
```

### Validation Rules

**IBI Range Check**:
```
IF ibi_ms < 300 THEN reject  // >200 BPM (physiologically unlikely)
IF ibi_ms > 3000 THEN reject // <20 BPM (sensor disconnected)
ELSE accept and process
```

**Disconnection Detection**:
```
last_message_time[N] = current_time
IF (current_time - last_message_time[N]) > 5000ms THEN
  sensor_connected[N] = false
  fade_out_channel(N, 2000ms)  // 2-second fade
END
```

**Reconnection**:
```
When valid message arrives after disconnection:
  sensor_connected[N] = true
  fade_in_channel(N, 1000ms)  // 1-second fade
  first_beat[N] = true  // Reset beat tracking
```

### BPM Calculation

**Simple Method** (initial implementation):
```
bpm = 60000 / ibi_ms
```

**Smoothed Method** (for display/slow parameters):
```
bpm_history[N] = [last 5 IBIs]
bpm_smoothed = 60000 / mean(bpm_history[N])
```

**Update rate**: Every beat (variable timing)

---

## Lighting Bridge Integration

### OSC Output to Lighting System

**Purpose**: Forward heartbeat events to separate lighting control system for synchronized visual feedback.

**Implementation**:
```
Address: /light/N/pulse
Type tag: i (int32)
Argument: IBI in milliseconds (same as received from sensor)
Port: 8001 (UDP)
Destination: 127.0.0.1 (localhost)
```

**Message flow**:
```
[r ibi-valid-0]      # Valid heartbeat from sensor 0
|
[prepend /light/0/pulse]
|
[packOSC]            # mrpeach OSC formatter
|
[udpsend]
|
[connect 127.0.0.1 8001(
|
[send(
```

**Repeat for sensors 1-3** with addresses `/light/1/pulse`, `/light/2/pulse`, `/light/3/pulse`

**Lighting bridge behavior**:
- Python process listening on port 8001
- Receives heartbeat events from Pure Data
- Controls LED strips via ESP32 controllers
- Synchronizes visual feedback with audio output

**Integration notes**:
- Fire-and-forget: No retry logic if lighting bridge not running
- Independent systems: Audio continues if lighting fails
- Same IBI value forwarded unchanged for timing consistency
- See `docs/lighting/trd.md` for lighting system details

---

## Sound Generation Strategies

### Mode 1: Polyrhythmic Percussion

**Concept**: Each heartbeat triggers percussion sample, creating emergent polyrhythm

**Implementation**:
- Sensor 0: Kick drum (low frequency anchor)
- Sensor 1: Snare/clap (mid-range punctuation)
- Sensor 2: Hi-hat/shaker (high-frequency texture)
- Sensor 3: Tom/rim (melodic percussion)

**Sample playback**:
```
[readsf~ 2] // 2-channel stereo sample
[*~ 0.8]    // Velocity scaling
[line~ 0 50] // 50ms fade-in to prevent clicks
```

**Variations**:
- Velocity from recent BPM (faster = louder)
- Sample selection cycles through bank
- Randomized sample start position

### Mode 2: Tonal/Harmonic

**Concept**: Heartbeats trigger sustained tones that pulse with beats

**Implementation**:
```
Base frequency = 55Hz * (bpm / 60)  // Map BPM to pitch
Harmonic series: 1x, 2x, 3x, 5x base frequency
Each sensor = different harmonic
Envelope: 100ms attack, sustain until next beat, 200ms release
```

**Synthesis**:
```
[osc~ $frequency] // Sine wave oscillator
[*~ $envelope]    // Amplitude envelope
[hip~ 20]         // Remove DC offset
```

**Convergence detection**:
```
IF abs(bpm[0] - bpm[1]) < 3 THEN
  add_harmonic(perfect_fifth)  // Reward synchronization
END
```

### Mode 3: Ambient Soundscape

**Concept**: Heartbeats modulate continuous textures

**Implementation**:
- Base layer: Continuous drone (synth or long sample loop)
- Each heartbeat: Briefly increases brightness/volume
- BPM controls filter cutoff frequency
- Spatial position modulates delay time

**Processing chain**:
```
[noise~]           // White noise source
[bp~ $bpm*10]      // Bandpass filter, BPM-controlled center
[*~ $heartbeat]    // Amplitude modulation on beat
[rev3~]            // Reverb for space
```

### Mode 4: Breathing Influence

**Concept**: IBI history reveals breathing pattern, sonified as evolving texture

**Implementation**:
- Track IBI variance over 10-beat window
- High variance = breath-influenced = ascending melodic phrase
- Low variance = steady state = sustained pad
- Encourages participants to notice breath-heart coupling

**Algorithm**:
```
variance = std_dev(last_10_ibis[N])
IF variance > 50ms THEN
  pitch_envelope = ascending  // Inhale phase
ELSE
  pitch_envelope = sustained  // Exhale/steady
END
```

---

## Spatial Audio Design

### Participant Positioning

**Physical layout** (lying down, heads to center):
```
        P1 (0°)
         |
         |
P2 (90°)-+-P4 (270°)
         |
         |
        P3 (180°)
```

**Stereo mapping**:
```
P1: Pan = 0.00  (hard left, 0°)
P2: Pan = 0.33  (left-center, 90°)
P3: Pan = 0.67  (right-center, 180°)
P4: Pan = 1.00  (hard right, 270°)
```

### Panning Algorithm

**Constant-power pan law** (maintains perceived loudness):
```
left_gain = cos(pan * π/2)
right_gain = sin(pan * π/2)

Examples:
pan=0.00: L=1.00, R=0.00
pan=0.33: L=0.88, R=0.48
pan=0.67: L=0.48, R=0.88
pan=1.00: L=0.00, R=1.00
```

**Pd implementation**:
```
[expr cos($f1*1.5708)] → left channel multiplier
[expr sin($f1*1.5708)] → right channel multiplier
```

### Dynamic Positioning (Future Enhancement)

**Heart rate influences position**:
- Faster BPM → drift toward center (excitement/engagement)
- Slower BPM → drift toward edge (relaxation/meditation)
- Creates subtle "breathing" of soundfield

---

## Launchpad Control Mapping

### Physical Layout (8x8 grid)

```
┌────────────────────────────────────────┐
│ ROW 8: Global controls                 │
│   [Mode] [Rev] [Vol+] [Vol-] [!] [!] [!] [Reset]
│                                        │
│ ROW 7: Special events                  │
│   [Build] [Release] [Sparse] [Dense] [!] [!] [!] [!]
│                                        │
│ ROW 6: Sound palettes (toggle modes)  │
│   [Perc] [Tonal] [Ambient] [Breath] [!] [!] [!] [!]
│                                        │
│ ROWS 1-5: Per-participant controls    │
│   COL1   COL2   COL3   COL4  (sensors 0-3)
│   [Sample A]                           │
│   [Sample B]                           │
│   [Sample C]                           │
│   [Sample D]                           │
│   [One-shot]                           │
└────────────────────────────────────────┘

Legend:
[!] = Unassigned (future expansion)
```

### MIDI Note Mapping

**Note numbering** (Launchpad standard):
- Row 1, Col 1 = Note 0
- Row 1, Col 8 = Note 7
- Row 8, Col 1 = Note 56
- Row 8, Col 8 = Note 63

**Control assignments**:

| Function | MIDI Note | Behavior | LED State |
|----------|-----------|----------|-----------|
| Mode: Percussion | 40 | Toggle percussion mode | Bright = active |
| Mode: Tonal | 41 | Toggle tonal mode | Bright = active |
| Mode: Ambient | 42 | Toggle ambient mode | Bright = active |
| Mode: Breathing | 43 | Toggle breathing mode | Bright = active |
| Reverb amount | 49 | Cycle: dry/wet/drenched | Brightness = amount |
| Volume up | 50 | Increase 3dB | Pulse on press |
| Volume down | 51 | Decrease 3dB | Pulse on press |
| Build tension | 32 | Ramp up filter/distortion | Pulse during build |
| Release | 33 | Return to baseline | Flash on trigger |
| Sparse | 34 | Reduce trigger probability | Dim = fewer beats |
| Dense | 35 | Add layers/harmonics | Bright = more active |
| Reset | 55 | Clear all states, reload samples | Flash red |
| Sensor N Sample A-D | N*8 to N*8+3 | Select sample for sensor N | Bright = selected |
| Sensor N One-shot | N*8+4 | Manual trigger for sensor N | Flash on trigger |

### LED Feedback

**Color scheme**:
- Red: Mode/state indicators
- Green: Active/enabled
- Amber: Armed/ready
- Off: Inactive

**Brightness levels**:
- Full: Currently selected/active
- Medium: Available but not selected
- Dim: Disabled state
- Pulsing: Quantized trigger pending

**Pd MIDI output**:
```
[makenote 60 500] // Note, velocity, duration
[noteout 1]       // Send to Launchpad
```

---

## Quantization System

### Beat Grid Generation

**Master clock**: Derived from most stable (lowest variance) heartbeat
```
Select reference sensor:
  variance[N] = std_dev(last_10_ibis[N])
  master = argmin(variance)
  
Master beat interval = ibi[master]
```

**Quantization targets**:
- **On-beat**: Trigger exactly on next detected heartbeat (any sensor)
- **Downbeat**: Trigger on next reference sensor beat
- **Bar**: Trigger on 4th beat (4-beat cycle)

### Trigger Buffer

**Implementation**:
```
When Launchpad pad pressed:
  IF quantization_enabled THEN
    add_to_trigger_queue(pad_id, next_beat_time)
  ELSE
    trigger_immediately(pad_id)
  END
```

**Queue processing**:
```
On each heartbeat:
  FOR each queued_trigger:
    IF current_time >= trigger_time THEN
      execute_trigger()
      remove_from_queue()
    END
  END
```

**Visual feedback**: Launchpad LED pulses to show armed state

---

## Effects Chain

### Reverb

**Algorithm**: Freeverb (built-in Pd external)

**Parameters**:
```
Room size: 0.85 (medium-large space)
Damping: 0.5 (balanced frequency response)
Wet/Dry: 0.3 (default, adjustable via Launchpad)
Width: 1.0 (full stereo)
```

**Routing**:
```
[sound_engine] → [*~ 0.3] → [freeverb~] → [+~] → [master]
             └──────────────────────────────┘
             Dry signal bypass
```

### Limiter/Compressor

**Purpose**: Prevent clipping when all 4 hearts trigger simultaneously

**Implementation**:
```
[clip~ -0.95 0.95]  // Hard limiter at -0.5dB
[lop~ 10]           // Smoothing filter to reduce distortion
```

**Threshold calculation**:
```
Peak level = 4 sensors * max_sample_amplitude
Limiter threshold = -3dB below 0dBFS
```

### Optional EQ

**High-pass filter**: Remove rumble
```
[hip~ 40]  // 40Hz cutoff
```

**Low-pass filter**: Reduce harshness (if needed)
```
[lop~ 8000]  // 8kHz cutoff (only if samples too bright)
```

---

## Audio Interface Configuration

### ALSA Settings

**Raspberry Pi/Debian configuration**:
```bash
# Check available devices
aplay -l

# Set default device in ~/.asoundrc
pcm.!default {
    type hw
    card 1  # USB audio interface (usually card 1)
    device 0
}

ctl.!default {
    type hw
    card 1
}
```

### Pd Audio Settings

**Startup flags**:
```bash
pd -nogui -alsa -audiodev 4 -channels 2 -r 48000 -audiobuf 64 heartbeat-main.pd
```

**Parameter explanation**:
- `-nogui`: Headless mode (for remote control)
- `-alsa`: Use ALSA audio backend
- `-audiodev 4`: Audio interface device number (check with `aplay -l`)
- `-channels 2`: Stereo output
- `-r 48000`: 48kHz sample rate
- `-audiobuf 64`: 64-sample buffer (~1.3ms latency)

**Auto-start on boot** (systemd service):
```ini
[Unit]
Description=Heartbeat Installation Audio
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/pd -nogui -alsa -audiodev 4 -channels 2 -r 48000 -audiobuf 64 /home/pi/heartbeat/heartbeat-main.pd
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Latency Budget

| Stage | Typical | Maximum |
|-------|---------|---------|
| ESP32 → network | 10ms | 25ms |
| Network → Pd OSC parse | 1ms | 5ms |
| Pd processing | 3ms | 10ms |
| Audio buffer (64 samples @ 48kHz) | 1.3ms | 1.3ms |
| USB transfer | 2ms | 5ms |
| DAC conversion | 1ms | 2ms |
| **Total: Beat → speakers** | **18ms** | **48ms** |

**Acceptable range**: <50ms (imperceptible to humans)

---

## Sample Management

### Directory Structure

```
/home/pi/heartbeat/
├── heartbeat-main.pd          # Main patch
├── pd-subpatches/             # Subpatch files
│   ├── osc-input.pd
│   ├── sensor-process.pd
│   ├── sound-engine.pd
│   ├── spatial-mixer.pd
│   ├── effects-chain.pd
│   └── midi-control.pd
├── samples/                   # Audio samples
│   ├── percussion/
│   │   ├── kick-01.wav
│   │   ├── snare-01.wav
│   │   ├── hat-01.wav
│   │   └── clap-01.wav
│   ├── tonal/
│   │   ├── bell-C.wav
│   │   ├── bell-E.wav
│   │   ├── bowl-A.wav
│   │   └── chime-G.wav
│   ├── ambient/
│   │   ├── drone-low.wav
│   │   ├── texture-breath.wav
│   │   └── pad-warm.wav
│   └── oneshots/
│       ├── swell-01.wav
│       ├── impact-01.wav
│       └── release-01.wav
└── backup/                    # Version control
    └── [timestamped copies]
```

### Sample Specifications

**Format**:
- File type: WAV (uncompressed)
- Bit depth: 16-bit or 24-bit
- Sample rate: 48kHz (matches audio interface)
- Channels: Mono or stereo

**Length guidelines**:
- Percussion: 0.5-2 seconds
- Tonal: 3-10 seconds (with decay)
- Ambient: 10-30 seconds (loopable)
- One-shots: 2-5 seconds

**Normalization**:
- Peak level: -6dBFS (headroom for mixing)
- RMS level: -18dBFS average (consistent loudness)

### Sample Loading

**Pd objects**:
```
[soundfiler]  // Load entire file into array
[readsf~]     // Stream from disk (for long samples)
```

**Pre-loading strategy**:
- Load all samples at patch startup
- Store in named arrays (e.g., [table kick-01])
- Reduces disk access latency during performance

**Memory management**:
```
Estimate: 100 samples × 5 seconds × 48kHz × 2 bytes = ~48MB
Raspberry Pi 4 (2GB RAM): Plenty of headroom
```

---

## Testing Procedures

### Pre-Hardware Testing (Days 1-3)

**Test 1: Simulated heartbeats**
```python
# fake_heartbeat.py
from pythonosc import udp_client
import time, random

client = udp_client.SimpleUDPClient("127.0.0.1", 8000)

# Simulate 4 participants with different heart rates
bpms = [65, 72, 58, 80]

while True:
    for i, bpm in enumerate(bpms):
        ibi = int(60000 / bpm)
        variance = random.randint(-50, 50)
        client.send_message(f"/heartbeat/{i}", ibi + variance)
        time.sleep((ibi + variance) / 1000.0)
```

**Validation**:
- [ ] Pd receives all 4 OSC messages
- [ ] Sounds trigger at expected intervals
- [ ] Stereo panning correct (P1=left, P4=right)
- [ ] BPM calculations accurate (±2 BPM)

**Test 2: OSC message validation**
- Send IBI < 300ms → verify rejection
- Send IBI > 3000ms → verify rejection
- Stop sending messages → verify 5-second timeout, fade-out

**Test 3: Launchpad control**
- Press mode buttons → verify audio changes
- Press one-shot triggers → verify quantized firing
- Adjust reverb → verify wet/dry change
- LED feedback matches pad state

**Test 4: Extended duration**
- Run fake_heartbeat.py for 30+ minutes
- Monitor CPU usage (`top` command)
- Check for audio glitches or memory leaks
- Verify stable operation

### Hardware Integration Testing (Days 5-6)

**Test 5: ESP32 to Pd integration**
- Connect real ESP32 with sensors
- Single person testing
- Verify latency <50ms (use oscilloscope or visual cue)
- Compare BPM to smartphone heart rate app (±5 BPM)

**Test 6: Multi-sensor operation**
- 2-4 participants with sensors
- Verify independent channels
- Check for crosstalk or interference
- Validate spatial positioning audibly

**Test 7: Mode switching during operation**
- Start in percussion mode
- Switch to tonal while sensors active
- Verify smooth transition, no crashes
- Test all 4 modes in sequence

**Test 8: Disconnection handling**
- Remove finger from sensor during session
- Verify timeout detection (5 sec)
- Verify fade-out smooth
- Reapply sensor → verify fade-in

**Test 9: Launchpad conducting**
- Participants lie with sensors active
- Operator triggers one-shots via Launchpad
- Verify quantization to heartbeats
- Test "build tension" and "release" functions

### System Reliability Testing (Day 7)

**Test 10: WiFi dropout recovery**
- Disconnect WiFi AP during operation
- Verify Pi attempts reconnection
- Restore WiFi → verify automatic recovery
- Check audio continues with frozen BPMs

**Test 11: Power cycle recovery**
- Full system power off/on
- Verify Pd auto-starts (systemd)
- Verify patch loads correctly
- Sensors reconnect automatically

**Test 12: Hot-swap audio interface**
- Unplug USB audio interface during operation
- Plug in spare interface
- Verify Pd recognizes new device
- Audio resumes (may need Pd restart)

**Test 13: Festival simulation**
- 30+ minute continuous operation
- Simulated participant turnover (disconnect/reconnect sensors)
- Random mode switching via Launchpad
- Monitor system temperature, CPU, memory
- Zero crashes required for acceptance

### Acceptance Criteria
- [ ] Latency beat-to-sound <50ms (95th percentile)
- [ ] All 4 sensors operate simultaneously without interference
- [ ] Launchpad controls responsive (<100ms)
- [ ] Mode switching seamless (no audio dropouts)
- [ ] 1-hour continuous operation without crashes
- [ ] Automatic recovery from common failures (WiFi, sensor disconnect)
- [ ] Stereo imaging clear and matches participant positions
- [ ] Effects (reverb, limiting) function correctly
- [ ] Sample playback glitch-free

---

## Backup & Fallback Strategies

### System Redundancy

**Primary system**:
- Raspberry Pi 4 + Focusrite Scarlett 2i2
- Pd patch auto-starts on boot

**Backup system** (hot-standby):
- Laptop (Linux or macOS) with Pd installed
- Same patches on USB stick
- Plug-and-play replacement (5 min swap)

**Component spares**:
- Second USB audio interface onsite
- Backup USB cables
- Spare Launchpad (optional, can operate without)

### Failure Modes & Recovery

| Failure | Detection | Recovery Time | Procedure |
|---------|-----------|---------------|-----------|
| Pi freeze/crash | Watchdog timeout | 30 seconds | Auto-reboot via watchdog |
| Pd crash | Systemd monitoring | 3 seconds | Auto-restart via systemd |
| WiFi dropout | ESP32/Pd timeout | 10-30 seconds | Auto-reconnect |
| Audio interface failure | No sound output | 2 minutes | Hot-swap USB interface |
| Complete Pi failure | System unresponsive | 5 minutes | Swap to backup laptop |
| Power failure | Immediate | N/A | UPS provides 4+ hours |
| Sample file corruption | Load error at startup | 5 minutes | Restore from USB backup |

### Watchdog Configuration

**Hardware watchdog** (Raspberry Pi built-in):
```bash
# Enable in /boot/config.txt
dtparam=watchdog=on

# Install watchdog daemon
sudo apt-get install watchdog

# Configure /etc/watchdog.conf
watchdog-device = /dev/watchdog
watchdog-timeout = 15
max-load-1 = 24
```

**Behavior**: Reboots Pi if system unresponsive for 15 seconds

### Systemd Service Management

**Pd service file**: `/etc/systemd/system/heartbeat-audio.service`

**Restart policy**:
- Automatic restart on crash
- 3-second delay between restarts
- Unlimited restart attempts

**Manual control**:
```bash
sudo systemctl start heartbeat-audio    # Start
sudo systemctl stop heartbeat-audio     # Stop
sudo systemctl restart heartbeat-audio  # Restart
sudo systemctl status heartbeat-audio   # Check status
journalctl -u heartbeat-audio -f        # View logs
```

### Data Backup

**Version control**:
```bash
cd /home/pi/heartbeat
git init
git add *.pd samples/
git commit -m "Initial version"

# Before each modification
git commit -am "Description of changes"
```

**USB backup** (pre-festival):
- Copy entire `/home/pi/heartbeat/` directory
- Include systemd service file
- Document IP addresses and passwords

**Cloud backup** (optional):
- Upload patches to GitHub private repo
- Accessible from any device for emergency rebuild

---

## Performance Optimization

### CPU Usage Targets

**Raspberry Pi 4 capabilities**:
- Quad-core 1.5GHz ARM Cortex-A72
- Target usage: <50% on single core
- Headroom for WiFi, OSC processing, system overhead

**Pd optimization strategies**:
- Use block-based processing (`[block~ 64]`)
- Pre-load samples (avoid disk I/O during performance)
- Minimize GUI updates (use `-nogui` for deployment)
- Efficient DSP chains (avoid redundant calculations)

**Monitoring**:
```bash
# Real-time CPU usage
top -p $(pgrep pd)

# Temperature (thermal throttling risk)
vcgencmd measure_temp
```

### Memory Management

**Sample library footprint**:
- 100 samples × 5 sec × 48kHz × 2 bytes = 48MB
- Raspberry Pi 4 (2GB): 2.5% RAM usage

**Pd heap**:
- Typical usage: 50-100MB
- Pi 4 headroom: 1.8GB+ available

**Monitoring**:
```bash
free -h
```

### Audio Buffer Tuning

**Trade-off**: Latency vs stability

**Settings**:
- Development: `-audiobuf 128` (2.7ms, very stable)
- Production: `-audiobuf 64` (1.3ms, slightly less stable)
- High-performance: `-audiobuf 32` (0.7ms, requires fast USB)

**Testing**: Run for 30 minutes at each setting, monitor for glitches

### Network Optimization

**Private WiFi advantages**:
- No competing traffic
- Low latency (<5ms)
- Predictable bandwidth

**QoS settings** (router):
- Prioritize UDP port 8000 (OSC)
- Disable power saving on WiFi
- Use 20MHz channel width (better range)

---

## Future Enhancements

### Software Additions (Post-v1.0)

**Synchronization detection**:
- Cross-correlation algorithm between sensor pairs
- Trigger special audio event when BPMs converge (<3% difference)
- Visual feedback via Launchpad LEDs

**Data logging**:
- Record all IBI values to CSV
- Post-session analysis (heart rate variability, synchronization events)
- Participant feedback correlation

**Adaptive audio**:
- Machine learning to predict next beat (Kalman filter)
- Pre-trigger samples for tighter sync
- Evolving soundscape based on session duration

**Web dashboard**:
- Real-time visualization of 4 heartbeats
- Current BPM display
- Mode and parameter status
- Accessible from any device on network

**Waveform transmission**:
- ESP32 sends full pulse shape (20 samples per beat)
- Richer audio synthesis possibilities
- Pulse transit time measurement

### Hardware Additions

**Additional MIDI controllers**:
- Knob controller for continuous parameters (reverb, filter cutoff)
- Foot pedal for hands-free mode switching

**Multi-channel audio**:
- 4-channel interface for quadraphonic output
- Surround sound immersion
- Per-participant speaker placement

**LED integration**:
- Send OSC to LED ESP32 from Pd
- Synchronized visual feedback
- Overhead or floor-mounted strips

**Projection mapping**:
- OSC to video software (TouchDesigner, Resolume)
- Visual representation of heartbeat data
- Projected onto ceiling above participants

### Interaction Modes

**Competitive mode**:
- Fastest heart rate gets loudest sound
- Encourages active engagement vs meditation

**Cooperative mode**:
- Group average BPM controls master tempo
- Collective relaxation rewarded

**Narrative arc**:
- Session progresses through sonic stages over 10+ minutes
- Introduction → exploration → convergence → resolution
- Scripted or adaptive based on participant behavior

---

## Installation Checklist

### Pre-Festival Setup (1 week before)

- [ ] Acquire audio interface (Focusrite Scarlett 2i2)
- [ ] Acquire MIDI controller (Novation Launchpad)
- [ ] Install Pure Data on Pi/NUC (`sudo apt-get install puredata`)
- [ ] Download sample libraries (Freesound.org, BBC Sound Effects)
- [ ] Configure ALSA audio settings
- [ ] Build Pd patch (osc-input, sound-engine, spatial-mixer, effects-chain, midi-control subpatches)
- [ ] Test with fake_heartbeat.py simulator
- [ ] Configure systemd service for auto-start
- [ ] Set up private WiFi network
- [ ] Configure static IP for Pi
- [ ] Test Launchpad MIDI control
- [ ] Prepare backup USB with patches and samples
- [ ] Install and test watchdog daemon
- [ ] Run 30-minute stress test
- [ ] Charge UPS power bank

### Day-Of Setup (Festival)

- [ ] Connect Pi to power (via UPS)
- [ ] Connect Focusrite to Pi via USB
- [ ] Connect Launchpad to Pi via USB
- [ ] Connect Focusrite outputs to mixer (TRS cables)
- [ ] Connect mixer outputs to speakers
- [ ] Power on WiFi router (private network)
- [ ] Verify Pi boots and Pd auto-starts (check LED or SSH)
- [ ] Test OSC reception (ping from laptop)
- [ ] Test audio output (play test tone)
- [ ] Test Launchpad controls (LED feedback)
- [ ] Verify ESP32 connects to WiFi
- [ ] End-to-end test: sensor on finger → sound output
- [ ] Set mixer levels (start conservative, -10dB)
- [ ] Test with volunteer participant
- [ ] Adjust reverb, EQ, levels to room acoustics
- [ ] Document working configuration (IP addresses, mixer settings)

### During Operation

- [ ] Monitor Pi temperature (`vcgencmd measure_temp`)
- [ ] Check for audio glitches (listen actively)
- [ ] Respond to participant requests (mode switches via Launchpad)
- [ ] Watch for sensor disconnections (visual cues or SSH monitoring)
- [ ] Be prepared to hot-swap audio interface if needed
- [ ] Backup laptop ready nearby

### Post-Festival

- [ ] Power down gracefully (`sudo shutdown -h now`)
- [ ] Backup any logs or data (`journalctl -u heartbeat-audio > logs.txt`)
- [ ] Document what worked and what didn't
- [ ] Upload patches to GitHub
- [ ] Archive sample libraries
- [ ] Write post-mortem notes for future installations

---

## Troubleshooting Guide

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| No sound output | Audio interface not detected | Check `aplay -l`, verify USB connection |
| | Pd not outputting | Check `[dac~]` object, verify audio settings |
| | Mixer volume too low | Increase mixer input gain |
| | Wrong output routing | Verify TRS cables to correct mixer channels |
| Launchpad not responding | MIDI not connected | Check USB connection, verify with `aconnect -l` |
| | Wrong MIDI channel | Check Pd `[notein]` object setup |
| OSC messages not arriving | WiFi not connected | Check Pi WiFi status, reconnect to network |
| | Wrong IP address | Verify ESP32 sending to correct Pi IP |
| | Firewall blocking port | Disable firewall or allow UDP 8000 |
| Audio glitching/crackling | Buffer too small | Increase `-audiobuf` value (64→128) |
| | CPU overload | Reduce Pd patch complexity, check `top` |
| | USB bandwidth issue | Use powered USB hub for audio interface |
| Latency too high | Large audio buffer | Decrease `-audiobuf` value (128→64) |
| | Network latency | Check WiFi signal strength, reduce distance |
| Sensor not detected in Pd | Sensor disconnected physically | Check ESP32, reconnect sensor |
| | ESP32 not sending | Check ESP32 serial monitor for errors |
| | IBI out of range | Adjust validation thresholds in Pd |
| Pi overheating/throttling | Inadequate cooling | Add heatsink or fan, reduce ambient temperature |
| | CPU overload | Reduce sample rate or patch complexity |
| Pd crashes on startup | Corrupted patch | Restore from USB backup |
| | Missing sample files | Check sample directory, verify paths |
| | Wrong Pd version | Reinstall Pd, use compatible version |
| Reverb too muddy | Damping too low | Increase damping parameter (0.5→0.7) |
| | Room size too large | Decrease room size parameter |
| Sounds not panned correctly | Pan object misconfigured | Check pan law formula, verify output routing |
| | Speakers swapped | Swap L/R cables at mixer |

---

## Reference Resources

### Pure Data Learning
- **Official documentation**: https://puredata.info/docs
- **FLOSS Manual**: http://write.flossmanuals.net/pure-data/
- **Miller Puckette's book**: "The Theory and Technique of Electronic Music"
- **YouTube**: Dr. Rafael Hernandez Pure Data tutorials

### OSC Protocol
- **Specification**: http://opensoundcontrol.org/spec-1_0
- **python-osc library**: https://pypi.org/project/python-osc/

### Audio Sources
- **Freesound.org**: https://freesound.org/ (CC-licensed samples)
- **BBC Sound Effects**: https://sound-effects.bbcrewind.co.uk/ (free for personal use)
- **Samples From Mars**: https://samplesfrommars.com/ (free packs available)

### Hardware Documentation
- **Focusrite Scarlett**: https://focusrite.com/en/usb-audio-interface/scarlett/scarlett-2i2
- **Novation Launchpad**: https://novationmusic.com/en/launch/launchpad-x
- **Raspberry Pi audio**: https://www.raspberrypi.org/documentation/configuration/audio-config.md

---

## Appendix: Sample Pd Code Snippets

### OSC Input (pd osc-input subpatch)
```
[udpreceive 8000]
|
[unpackOSC]
|
[routeOSC /heartbeat/0 /heartbeat/1 /heartbeat/2 /heartbeat/3]
|           |           |           |
[s ibi-0]   [s ibi-1]   [s ibi-2]   [s ibi-3]
```

**Note:** Uses mrpeach library for OSC handling. Install via: `Help → Find Externals → mrpeach`

### IBI Validation and BPM Calculation
```
[r ibi-0]
|
[select] <- reject if <300 or >3000
|
[t f f]
|    |
|    [expr 60000/$f1] -> BPM
|
[s valid-ibi-0]
```

### Beat Trigger Generation
```
[r valid-ibi-0]
|
[t b] <- bang on valid IBI
|
[s beat-0] -> to sound engine
```

### Sample Playback
```
[r beat-0]
|
[t b b]
|    |
|    [0, 1 50( -> 50ms fade-in envelope
|    |
|    [line~]
|    |
[readsf~ 2] -> load kick-01.wav
|
[*~] <- apply envelope
|
[s audio-0] -> to spatial mixer
```

### Stereo Panning (constant power)
```
[r audio-0]
[r pan-0] <- 0.0 for sensor 0
|
[t f f]
|    |
|    [expr sin($f1*1.5708)]
|    |
|    [*~] -> right channel
|
[expr cos($f1*1.5708)]
|
[*~] -> left channel
```

### Master Output with Limiter
```
[r mix-left]  [r mix-right]
|             |
[freeverb~]   [freeverb~]
|             |
[clip~ -0.95 0.95]
|             |
[dac~ 1 2]
```

---

*Document Version: 1.0*
*Last Updated: 2025-11-06*
*Companion to: heartbeat-input-hardware-design.md, heartbeat-firmware-design.md*
*Implementation: Pure Data + ALSA on Linux*