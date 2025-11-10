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
- ESP32-S3 microcontroller
- PulseSensor.com optical PPG sensor
- Battery pack (USB power bank)
- GPIO 32 for analog input (ADC1_CH4)

**Behavior:**
- Sample PPG sensor at configurable rate (start with 50Hz = 20ms intervals)
- Bundle N samples (start with 10 samples = 200ms per bundle)
- Transmit via WiFi/OSC to sensor processor
- Each unit has unique PPG_ID (0-3)

**OSC Message:**
```
Route: /ppg/raw
Args: [ppg_id, sample1, sample2, ..., sampleN, timestamp1, timestamp2, ..., timestampN]
Destination: 127.0.0.1:8000 (or sensor processor IP)
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

**OSC Input:**
- Listen on port 8000
- Receive `/ppg/raw` messages from 4 ESP32 units

**OSC Output:**
- Publish to port 8001 (audio engine)
- Publish to port 8002 (lighting controller)

**Processing:**
- Maintain rolling buffer per PPG (5-10 seconds of samples)
- Detect beats via amplitude threshold crossing
- Calculate BPM from inter-beat intervals (IBI)
- Calculate intensity from signal strength (optional, can start at 0.0)
- Smooth BPM with median of recent IBIs (noise resistance)

**Beat Message:**
```
Route: /beat/{ppg_id}
Args: [timestamp, bpm, intensity]
  timestamp (float): Unix time - when beat occurred or will occur
  bpm (float): Current BPM estimate (40-150 typical)
  intensity (float): Signal strength 0.0-1.0 (0.0 if unavailable)
```

**Initial implementation:** Publish `timestamp=now`, `intensity=0.0`

---

### 3. Audio Engine (audio_engine.py)

**Purpose:** Receive beat events, play sound samples

**Input:**
- Listen on port 8001
- Handle `/beat/{ppg_id}` messages

**Behavior:**
- Load 4 sound samples (one per PPG)
- On beat message: play corresponding sample
- Timestamp handling: initially play immediately, future can add scheduling

**Output:** USB audio interface → speakers

---

### 4. Lighting Controller (lighting_controller.py)

**Purpose:** Receive beat events, pulse smart bulbs

**Input:**
- Listen on port 8002
- Handle `/beat/{ppg_id}` messages

**Behavior:**
- Control 4 Kasa smart bulbs (one per PPG)
- Map BPM to hue: slow (40 BPM) = blue (240°), fast (120 BPM) = red (0°)
- On beat message: pulse bulb brightness and/or color

**Output:** Kasa smart bulb API (local LAN control)

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
│ - Bundle 10 samples every 200ms                         │
│ - Send /ppg/raw to port 8000                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Sensor Processor (sensor_processor.py)                  │
│ - Buffer samples per PPG                                │
│ - Detect beats via threshold                            │
│ - Calculate BPM from IBI                                │
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

### Phase 1: Basic Communication (Monday)
1. ESP32 firmware: Sample at 50Hz, bundle 10, send OSC
2. Sensor processor: Receive bundles, log to console
3. Verify: See PPG values changing on finger contact

### Phase 2: Beat Detection (Monday/Tuesday)
4. Sensor processor: Threshold detection, calculate BPM
5. Sensor processor: Publish `/beat/{ppg_id}` messages
6. Test: Inject fake beats, verify reception at 8001/8002

### Phase 3: Audio & Lighting (Tuesday)
7. Audio engine: Load samples, play on beat
8. Lighting controller: Connect Kasa bulbs, pulse on beat
9. Test: End-to-end with real PPG sensors

### Phase 4: Refinement (Tuesday if time)
10. Tune beat detection thresholds
11. Add BPM smoothing
12. Test with multiple participants

---

## Testing & Debugging

**Test sensor processor without ESP32:**
```python
# test_inject_ppg.py
from pythonosc import udp_client
import time, random

client = udp_client.SimpleUDPClient("127.0.0.1", 8000)

# Send fake PPG samples
while True:
    samples = [2048 + random.randint(-200, 200) for _ in range(10)]
    timestamps = [int(time.time() * 1000) + i*20 for i in range(10)]
    client.send_message("/ppg/raw", [0] + samples + timestamps)
    time.sleep(0.2)
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
amor/
├── firmware/
│   └── amor-esp32/           # ESP32 firmware (Arduino/PlatformIO)
├── python/
│   ├── sensor_processor.py   # Port 8000 input, 8001/8002 output
│   ├── audio_engine.py        # Port 8001 input, audio output
│   ├── lighting_controller.py # Port 8002 input, bulb control
│   ├── test_inject_ppg.py     # Fake PPG data generator
│   └── test_inject_beats.py   # Fake beat event generator
├── sounds/
│   ├── ppg_0.wav
│   ├── ppg_1.wav
│   ├── ppg_2.wav
│   └── ppg_3.wav
└── docs/
    └── amor-technical-reference.md  # This file
```

---

## Quick Reference

**ESP32 OSC Output:**
```
/ppg/raw [ppg_id, s1, s2, ..., sN, t1, t2, ..., tN]
→ Port 8000
```

**Sensor Processor OSC Output:**
```
/beat/{ppg_id} [timestamp, bpm, intensity]
→ Port 8001 (audio)
→ Port 8002 (lighting)
```

**BPM Calculation:**
```python
ibi_ms = timestamp_current - timestamp_previous
bpm = 60000 / ibi_ms
# Use median of last 5-10 IBIs for stability
```

**BPM to Color (Lighting):**
```python
hue = (120 - bpm) * 3  # Blue (240°) at 40 BPM, Red (0°) at 120 BPM
hue = max(0, min(360, hue))
```

---

**Last Updated:** 2025-11-11  
**Status:** Ready for implementation
