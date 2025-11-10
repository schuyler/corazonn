# Amor - Heartbeat Installation Technical Reference

**Codebase:** amor (Spanish: love)  
**Version:** 1.0  
**Date:** 2025-11-11

---

## Architecture Overview

Four independent ESP32 units with PulseSensor PPG sensors stream raw photoplethysmography data via WiFi/OSC to a Python sensor processor. The processor detects heartbeats and publishes beat events. Separate Python processes consume beat events to generate audio and lighting effects.

**Design principle:** Components communicate via OSC, can start/stop independently, protocol locked for implementation.

---

## Components

### 1. ESP32 Firmware (amor-firmware)

**Hardware per unit:**
- ESP32-WROOM (testing) or ESP32-S3 (production) microcontroller
- PulseSensor.com optical PPG sensor
- Battery pack (USB power bank)
- Analog input: configurable GPIO (ADC1_CH4 on WROOM, ADC1_CH3 on S3, 12-bit 0-4095)

**Build system:** PlatformIO

**Libraries:**
- OSC: CNMAT/OSC Arduino library (https://github.com/CNMAT/OSC)
- WiFi: Built-in ESP32 WiFi library
- Time: millis() for timestamps (no NTP required)

**Behavior:**
- Sample PPG sensor at configurable rate (start with 50Hz = 20ms intervals)
- Bundle N samples (start with 5 samples = 100ms per bundle)
- Transmit via WiFi/OSC to sensor processor
- Each unit has unique PPG_ID (0-3)
- WiFi reconnection: retry every 5 seconds on disconnect, continue sampling locally

**Network Configuration:**
Configuration provided via `config.h` (not committed to git):
```cpp
#define WIFI_SSID "network_name"
#define WIFI_PASSWORD "password"
#define SERVER_IP "192.168.1.100"  // Sensor processor IP
#define SERVER_PORT 8000
#define PPG_ID 0            // Unique per unit: 0, 1, 2, or 3
#define PPG_GPIO 32         // GPIO 32 for WROOM, GPIO 4 for S3
```

**OSC Message:**
```
Route: /ppg/{ppg_id}  where ppg_id ∈ {0,1,2,3}
Args: [sample1, sample2, ..., sampleN, timestamp_ms]
  sample1...sampleN (int): ADC values 0-4095 (N=5 initially)
  timestamp_ms (int): millis() when first sample taken
Type tags: [i, i, i, i, i, i]  # For N=5: 5 samples + timestamp
Destination: {SERVER_IP}:{SERVER_PORT} (from config.h)
```

**Signal characteristics:**
- ADC range: 0-4095 (ESP32 12-bit)
- Idle (no contact): ~2048 ± noise
- Active signal: Oscillates with heartbeat waveform
- Contact/movement affects baseline and amplitude

**Sample rate notes:**
- 50Hz (20ms): Adequate for basic beat detection, low bandwidth
- 100Hz (10ms): Better waveform resolution
- 500Hz (2ms): Manufacturer recommended for medical accuracy (optional future upgrade)

---

### 2. Sensor Processor (sensor_processor.py)

**Purpose:** Receive raw PPG samples, detect beats, publish beat events

**Library:** python-osc (pythonosc)

**OSC Input:**
- Listen on port 8000
- Receive `/ppg/{ppg_id}` messages from 4 ESP32 units (4 separate routes: `/ppg/0` through `/ppg/3`)

**OSC Output:**
- Publish to port 8001 (audio engine) AND port 8002 (lighting controller)
- Implementation: Create two `SimpleUDPClient` instances, send same message to both

**Processing:**
- Maintain rolling buffer per PPG: **300 samples (6 seconds at 50Hz)**
- Detect beats via threshold crossing algorithm:
  * Calculate rolling mean and stddev over 2-second window (100 samples)
  * Threshold = mean + (0.6 × stddev)
  * Detect when signal crosses threshold upward
  * Debounce: Ignore crossings < 400ms apart (prevents double-triggers, max 150 BPM)
- Calculate BPM from inter-beat intervals (IBI):
  * Validate IBI: reject if < 400ms or > 2000ms (150-30 BPM range)
  * Smooth BPM using median of last 5 valid IBIs
- Calculate intensity from signal amplitude (Phase 6):
  * `amplitude = max(recent_samples) - min(recent_samples)`
  * `intensity = min(1.0, amplitude / 2048)`  # Normalize to 0-1
- Noise rejection:
  * If stddev > mean: likely movement artifact, pause beat detection
  * Resume when signal stabilizes (stddev < 0.3 × mean for 2 seconds)

**Beat Message:**
```
Route: /beat/{ppg_id}
Args: [timestamp, bpm, intensity]
  timestamp (float): Unix time (seconds) via time.time() - when beat occurred
  bpm (float): Current BPM estimate (40-150 typical)
  intensity (float): Signal strength 0.0-1.0 (0.0 if unavailable)
Type tags: [f, f, f]
```

**Initial implementation:** Publish `timestamp=time.time()`, `intensity=0.0`

**Startup behavior:**
1. Collect minimum 5 seconds of samples before starting detection
2. Detect first beat: store timestamp, no message sent yet
3. Detect second beat: calculate first IBI, send beat message with BPM = 60/IBI, intensity=0.0
4. Subsequent beats: use median of last N IBIs (N = min(5, available_IBIs))

**Note on timestamps:** ESP32 uses millis() for relative time in PPG bundles. Sensor processor uses time.time() (absolute Unix time) for beat messages. No synchronization needed since timestamps are per-component.

---

### 3. Audio Engine (audio_engine.py)

**Purpose:** Receive beat events, play sound samples

**Libraries:**
- python-osc (pythonosc) for OSC input
- sounddevice + soundfile for audio playback

**Input:**
- Listen on port 8001
- Handle `/beat/{ppg_id}` messages (4 separate routes: `/beat/0` through `/beat/3`)

**Behavior:**
- Load 4 sound samples (one per PPG)
  * Format: WAV, 44.1kHz, 16-bit, mono or stereo
  * Files: `sounds/ppg_0.wav` through `sounds/ppg_3.wav`
- On beat message: play corresponding sample
- Concurrent playback: Each PPG has independent audio channel (allow overlaps)
- Timestamp handling: play immediately if < 500ms old, drop if older

**Output:** USB audio interface → speakers

---

### 4. Lighting Controller (lighting_controller.py)

**Purpose:** Receive beat events, pulse smart bulbs

**Libraries:**
- python-osc (pythonosc) for OSC input
- python-kasa for bulb control (install: `pip install python-kasa`)

**Input:**
- Listen on port 8002
- Handle `/beat/{ppg_id}` messages (4 separate routes: `/beat/0` through `/beat/3`)

**Behavior:**
- Control 4 TP-Link Kasa smart bulbs (one per PPG)
- Discovery: Use `await Discover.discover()` to find bulbs on LAN
- Map BPM to hue: slow (40 BPM) = blue (240°), fast (120 BPM) = red (0°)
- Pulse behavior on beat:
  * Flash bulb to 100% brightness over 100ms
  * Hold at 100% for 50ms
  * Fade to 50% baseline over 200ms
  * Color (hue) changes with BPM, saturation stays at 100%

**Output:** Kasa smart bulb API (local LAN control, asyncio-based)

---

## Beat Message Protocol (LOCKED)

**Route:** `/beat/{ppg_id}` where ppg_id ∈ {0,1,2,3}

**Arguments:** `[timestamp, bpm, intensity]`

| Field | Type | Description | Initial Value |
|-------|------|-------------|---------------|
| timestamp | float | Unix time of beat | `time.time()` when detected |
| bpm | float | Current BPM estimate | Calculated from IBI median |
| intensity | float | Signal strength 0-1 | `0.0` (calculate later) |

**Consumer contract:**
- MUST accept all three arguments
- MUST handle past timestamps (>100ms old): play immediately or drop
- MAY handle future timestamps: schedule or play immediately
- MAY ignore intensity if 0.0

**Protocol evolution:** Timestamp interpretation can evolve from instantaneous to predictive without breaking consumers.

---

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│ ESP32 Units (×4)                                        │
│ - Sample PPG at 50Hz                                    │
│ - Bundle 5 samples every 100ms                          │
│ - Send /ppg/{ppg_id} to port 8000                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Sensor Processor (sensor_processor.py)                  │
│ - Buffer 300 samples per PPG (6 sec)                    │
│ - Detect beats via threshold crossing                   │
│ - Calculate BPM from median of IBIs                     │
│ - Publish /beat/{ppg_id} to ports 8001, 8002           │
└────────────┬───────────────────┬────────────────────────┘
             │                   │
             ▼                   ▼
┌─────────────────────┐  ┌──────────────────────┐
│ Audio Engine        │  │ Lighting Controller  │
│ (port 8001)         │  │ (port 8002)          │
│ - Play samples      │  │ - Pulse bulbs        │
│ - USB audio out     │  │ - BPM → color        │
└─────────────────────┘  └──────────────────────┘
```

---

## Network Configuration

**WiFi:** All devices on same network (private AP recommended)

**Port allocation:**
- 8000: ESP32 → Sensor Processor (raw PPG)
- 8001: Sensor Processor → Audio Engine (beats)
- 8002: Sensor Processor → Lighting Controller (beats)

**IP addressing:** DHCP acceptable, sensor processor at known/static IP

---

## Implementation Phases

**CRITICAL PATH: Firmware must be completed first**

### Phase 1: ESP32 Firmware (Priority 1)
1. Configure PlatformIO project for ESP32-WROOM/S3
2. Implement WiFi connection with config.h
3. Implement PPG sampling at 50Hz on configured PPG_GPIO
4. Implement bundling (5 samples) and OSC transmission
5. Test: Verify OSC messages received by test script

### Phase 2: Sensor Processor (Priority 2)
6. Receive `/ppg/{ppg_id}` bundles, log to console
7. Implement rolling buffer (300 samples per PPG)
8. Implement threshold-based beat detection
9. Calculate BPM from IBIs with validation
10. Publish `/beat/{ppg_id}` to dual ports

### Phase 3: Audio & Lighting (Priority 3)
11. Audio engine: Load WAV samples, play on beat
12. Lighting controller: Connect Kasa bulbs, pulse with BPM→color mapping
13. Test: End-to-end with real PPG sensors

### Phase 4: Refinement
14. Tune beat detection thresholds and noise rejection
15. Verify BPM smoothing (median of 5 IBIs)
16. Test with all 4 units simultaneously

---

## Testing & Debugging

**Test sensor processor without ESP32:**
```python
# test_inject_ppg.py
from pythonosc import udp_client
import time, random

client = udp_client.SimpleUDPClient("127.0.0.1", 8000)

# Send fake PPG samples (5 samples per bundle, matching ESP32 format)
ppg_id = 0
timestamp_start = int(time.time() * 1000)  # millis since epoch for testing
while True:
    samples = [2048 + random.randint(-200, 200) for _ in range(5)]
    timestamp_ms = int((time.time() - timestamp_start) * 1000)  # Simulated millis()
    client.send_message(f"/ppg/{ppg_id}", samples + [timestamp_ms])
    time.sleep(0.1)  # 100ms = 5 samples at 50Hz
```

**Test audio/lighting without sensor processor:**
```python
# test_inject_beats.py
from pythonosc import udp_client
import time

audio = udp_client.SimpleUDPClient("127.0.0.1", 8001)
lighting = udp_client.SimpleUDPClient("127.0.0.1", 8002)

# Send fake beats at 72 BPM
while True:
    now = time.time()
    audio.send_message("/beat/0", [now, 72.0, 0.5])
    lighting.send_message("/beat/0", [now, 72.0, 0.5])
    time.sleep(60/72)  # 72 BPM
```

**Component independence:**
- Kill and restart any process without affecting others
- Inject test data at any layer
- Monitor console output for debugging

---

## PPG Signal Notes

**Waveform:** Rapid upward rise → peak → fall → baseline (repeats with heartbeat)

**Beat detection:** Detect upward threshold crossing at ~50% of signal amplitude range

**Common issues:**
- Movement artifacts (major) - participants must stay still
- Poor finger contact - adjust pressure
- Ambient light interference - shield sensor
- Baseline drift - use adaptive threshold or high-pass filter

**Best practices:**
- Earlobe: Less movement noise, good signal
- Fingertip: Good capillary density, easier mounting
- Consistent gentle pressure during session

---

## Future Enhancements

**Phase 5: Predictive Timing**
- Sensor processor publishes `timestamp = now + (60/bpm)`
- Consumers schedule actions for future beat
- Latency compensation per component

**Phase 6: Intensity Effects**
- Calculate signal amplitude during IBI → intensity
- Lighting: modulate brightness by intensity
- Audio: modulate velocity/volume by intensity

**Phase 7: Higher Sample Rate**
- Increase to 100-500Hz for better waveform resolution
- Improves beat detection accuracy
- Test bandwidth and processing requirements first

---

## File Structure

```
corazonn/
├── firmware/
│   └── amor/                 # ESP32 firmware (PlatformIO)
├── testing/
│   ├── sensor_processor.py   # Port 8000 input, 8001/8002 output
│   ├── test_inject_ppg.py    # Fake PPG data generator
│   └── test_inject_beats.py  # Fake beat event generator
├── audio/
│   ├── audio_engine.py       # Port 8001 input, audio output
│   ├── sounds/
│   │   ├── ppg_0.wav
│   │   ├── ppg_1.wav
│   │   ├── ppg_2.wav
│   │   └── ppg_3.wav
├── lighting/
│   └── lighting_controller.py # Port 8002 input, bulb control
└── docs/
    └── firmware/
        └── amor-technical-reference.md  # This file
```

---

## Python Dependencies

Create `requirements.txt`:
```
pythonosc>=1.8.0
sounddevice>=0.4.6
soundfile>=0.12.1
python-kasa>=0.5.0
numpy>=1.21.0
```

Install: `pip install -r requirements.txt`

---

## Quick Reference

**ESP32 OSC Output:**
```
/ppg/{ppg_id} [sample1, sample2, ..., sampleN, timestamp_ms]
→ Port 8000
→ ppg_id ∈ {0,1,2,3} in route
→ N=5 samples initially
→ timestamp_ms = millis() on ESP32
```

**Sensor Processor OSC Output:**
```
/beat/{ppg_id} [timestamp, bpm, intensity]
→ Port 8001 (audio)
→ Port 8002 (lighting)
→ timestamp = time.time() (Unix seconds)
```

**BPM Calculation:**
```python
ibi_sec = timestamp_current - timestamp_previous
bpm = 60.0 / ibi_sec
# Use median of last 5 IBIs for stability
# Validate: 400ms < IBI < 2000ms (150-30 BPM)
```

**BPM to Color (Lighting):**
```python
bpm_clamped = max(40, min(120, bpm))  # Clamp to expected range
hue = (120 - bpm_clamped) * 3  # Blue (240°) at 40 BPM, Red (0°) at 120 BPM
hue = max(0, min(360, hue))
```

---

**Last Updated:** 2025-11-11  
**Status:** Ready for implementation
