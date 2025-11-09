# Heartbeat Installation - Audio Pipeline Phase 1 TRD
## Pure Data OSC → Stereo Audio Output

**Version:** 1.0
**Date:** 2025-11-09
**Purpose:** Define Phase 1 audio pipeline for heartbeat-triggered percussion
**Audience:** Implementation (self or coding agent)
**Hardware:** Linux audio server, Focusrite Scarlett 2i2, speakers
**Software:** Pure Data (Pd-extended or Pd vanilla + externals)
**Dependencies:** ESP32 firmware sending OSC heartbeat messages

**Estimated Implementation Time:** 3-4 hours

---

## 1. Objective

Implement Pure Data patch that receives OSC heartbeat messages and generates stereo audio output with spatially-positioned percussion samples.

**Phase 1 MVP Scope:**
- Receive OSC from ESP32 firmware (port 8000)
- Trigger percussion sample playback on heartbeat
- 4-channel stereo panning (4 fixed positions)
- Send OSC lighting commands (port 8001)
- Single percussion sample per sensor

**Success Criteria:**
- ✅ Pd receives OSC messages from firmware (or simulator)
- ✅ Audio triggers on each heartbeat
- ✅ Stereo positioning correct (Sensor 0=L, Sensor 3=R)
- ✅ Lighting OSC messages sent to Python bridge
- ✅ Runs for 30+ minutes without audio glitches
- ✅ Latency <50ms (heartbeat → audio)

---

## 2. Architecture

### 2.1 Data Flow

```
ESP32 Firmware (×4 sensors)
      ↓
   OSC/UDP :8000
      ↓
Pure Data Patch (THIS DOCUMENT)
   ├─→ Audio Synthesis
   │   └─→ USB Audio Interface → Speakers
   └─→ OSC/UDP :8001
       └─→ Python Lighting Bridge
```

### 2.2 Pd Patch Structure

```
Main Patch: heartbeat-main.pd
├── pd osc-input          (OSC receiver, port 8000)
├── pd sensor-N-process   (×4, beat validation)
├── pd sound-engine       (sample playback)
├── pd spatial-mixer      (4→2 channel stereo)
├── pd lighting-output    (OSC sender, port 8001)
└── [dac~ 1 2]           (stereo output)
```

### 2.3 Execution Model

- Pure Data main thread handles all processing
- Audio block size: 64 samples @ 48kHz (1.3ms)
- OSC processed in audio callback (lock-free)
- Sample playback via [readsf~] (streaming from disk)

---

## 3. Prerequisites

### 3.1 Pure Data Installation

**Required version:** Pd vanilla 0.52+ OR Pd-extended

**Linux installation:**
```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install puredata

# Verify
pd -version
# Expected: Pd-0.52-1 or newer
```

**Required externals:**
```bash
# Install via Pd menu: Help → Find Externals
- mrpeach (OSC library)
- cyclone (audio utilities)

# Or via command line
pd -lib mrpeach -lib cyclone
```

**Verify externals:**
Open Pd, create objects:
- `[packOSC]` - should create (OSC formatting)
- `[unpackOSC]` - should create (OSC parsing)
- `[udpsend]` - should create (OSC output)
- `[udpreceive 8000]` - should create (OSC input)

### 3.2 Audio Interface Setup

**ALSA configuration:**

**R1: Configure USB audio interface as default device**

```bash
# List audio devices
aplay -l

# Example output:
# card 0: PCH [HDA Intel PCH]         # Built-in audio
# card 1: USB [Scarlett 2i2 USB]      # Focusrite interface

# Create ~/.asoundrc
cat > ~/.asoundrc << 'EOF'
pcm.!default {
    type hw
    card 1    # USB audio interface (check aplay -l)
    device 0
}

ctl.!default {
    type hw
    card 1
}
EOF
```

**Test audio:**
```bash
# Generate test tone (440Hz sine, 2 seconds)
speaker-test -t sine -f 440 -c 2 -l 1
# Should hear tone from both speakers
```

**R2: Configure Pd audio settings**
- Sample rate: 48000 Hz
- Audio buffer: 64 samples (1.3ms latency, adjust if glitches)
- Channels: 2 (stereo output)
- Audio API: ALSA
- Device: hw:1,0 (USB interface)

---

## 4. Sample Library Setup

### 4.1 Directory Structure

**R3: Create sample directory**

```bash
mkdir -p ~/heartbeat/samples/percussion
cd ~/heartbeat/samples/percussion
```

### 4.2 Sample Acquisition

**R4: Download percussion samples (Freesound.org)**

**Requirements per sample:**
- Format: WAV (uncompressed)
- Bit depth: 16-bit or 24-bit
- Sample rate: 48kHz (matches audio interface)
- Channels: Mono preferred (stereo acceptable)
- Length: 0.5-2 seconds
- Normalization: Peak at -6dBFS (headroom for mixing)

**Recommended sources:**
- Freesound.org (search: "kick", "snare", "hat", "clap")
- Filters: CC0 or CC-BY license, WAV format, >44.1kHz

**Phase 1 minimal set (4 samples):**
```bash
# Download one sample per sensor
kick-01.wav     # Sensor 0 (low frequency anchor)
snare-01.wav    # Sensor 1 (mid-range punctuation)  
hat-01.wav      # Sensor 2 (high-frequency texture)
clap-01.wav     # Sensor 3 (percussive accent)
```

### 4.3 Sample Processing

**R5: Normalize samples to -6dBFS peak**

```bash
# Install sox
sudo apt-get install sox

# Normalize each sample
for file in *.wav; do
    sox "$file" "normalized_$file" norm -6
    mv "normalized_$file" "$file"
done
```

**R6: Convert to 48kHz mono if needed**

```bash
for file in *.wav; do
    sox "$file" -r 48000 -c 1 "converted_$file"
    mv "converted_$file" "$file"
done
```

**R7: Verify sample format**

```bash
soxi *.wav
# Should show:
# Sample Rate : 48000
# Channels    : 1
# Bit Depth   : 16 or 24
```

---

## 5. OSC Protocol

### 5.1 Input Messages (from ESP32)

**Format:**
```
Address: /heartbeat/N
Arguments: <int32> ibi_ms
Example: /heartbeat/0 847
Port: 8000 (UDP)
```

**R8: Receive on port 8000**
**R9: Accept sensor IDs 0-3**
**R10: Validate IBI range 300-3000ms**
**R11: Reject invalid messages (log to Pd console)**

### 5.2 Output Messages (to lighting bridge)

**Format:**
```
Address: /light/N/pulse
Arguments: <int32> ibi_ms
Example: /light/0/pulse 847
Port: 8001 (UDP)
Destination: 127.0.0.1 (localhost)
```

**R12: Send immediately when heartbeat received**
**R13: Forward same IBI value**

---

## 6. Pure Data Patch Specifications

### 6.1 Main Patch (heartbeat-main.pd)

**R14: Audio settings in patch header**
```
[declare -lib mrpeach -lib cyclone]

# Comment block at top:
# Heartbeat Installation - Phase 1
# Audio Output: 48kHz stereo
# OSC Input: port 8000 (heartbeats from ESP32)
# OSC Output: port 8001 (lighting commands)
```

**R15: DSP control**
```
[loadbang]
|
[; pd dsp 1(    # Turn on audio processing
```

**R16: Create subpatch abstractions**
- osc-input.pd (OSC receiver)
- sensor-process.pd (per-sensor processing, create 4 instances)
- sound-engine.pd (sample playback)
- spatial-mixer.pd (stereo panning)
- lighting-output.pd (OSC sender)

### 6.2 OSC Input Subpatch (osc-input.pd)

**R17: UDP receiver**
```
[udpreceive 8000]
|
[unpackOSC]
|
[routeOSC /heartbeat/0 /heartbeat/1 /heartbeat/2 /heartbeat/3]
|           |           |           |
[s ibi-0]   [s ibi-1]   [s ibi-2]   [s ibi-3]
```

**R18: Error handling**
```
[udpreceive 8000]
|
[print OSC-ERROR]    # Print malformed messages
```

### 6.3 Sensor Processing Subpatch (sensor-process.pd)

**Arguments:** `sensor-process.pd N` (where N = 0, 1, 2, 3)

**R19: IBI validation**
```
[r ibi-$1]           # Receive for sensor N
|
[t f f f]            # Trigger 3 outlets
|   |   |
|   |   [s ibi-valid-$1]      # Forward to sound engine
|   |
|   [expr 60000/$f1] # Calculate BPM
|   |
|   [s bpm-$1]       # Send BPM (future use)
|
[moses 300]          # Check lower bound
|
[moses 3001]         # Check upper bound
|
[print VALID-IBI]    # Debug output
```

**R20: Invalid IBI handling**
```
# If IBI < 300 or > 3000
[print INVALID-IBI]
# Don't forward to sound engine
```

### 6.4 Sound Engine Subpatch (sound-engine.pd)

**R21: Sample loading (Phase 1: 4 samples hardcoded)**

```
# Load samples at patch startup
[loadbang]
|
[t b b b b]
|   |   |   |
|   |   |   [open /home/user/heartbeat/samples/percussion/clap-01.wav(
|   |   |   |
|   |   |   [readsf~ 1]       # Sensor 3
|   |   |   |
|   |   |   [s audio-3]
|   |   |
|   |   [open .../hat-01.wav(
|   |   |
|   |   [readsf~ 1]           # Sensor 2
|   |   |
|   |   [s audio-2]
|   |
|   [open .../snare-01.wav(
|   |
|   [readsf~ 1]               # Sensor 1
|   |
|   [s audio-1]
|
[open .../kick-01.wav(
|
[readsf~ 1]                   # Sensor 0
|
[s audio-0]
```

**R22: Sample playback triggering**

```
[r ibi-valid-0]
|
[t b]                         # Convert to bang
|
[1, 0 50(                     # 50ms fade-in envelope
|
[line~]
|
[*~ ]  <---  [r audio-0]      # Apply envelope
|
[s audio-out-0]               # To spatial mixer
```

**Repeat for sensors 1-3**

**R23: Sample path configuration**
- Use absolute paths (not relative)
- Verify files exist at startup
- Print error if sample missing

### 6.5 Spatial Mixer Subpatch (spatial-mixer.pd)

**R24: Constant-power panning**

**Pan positions (0.0 = hard left, 1.0 = hard right):**
- Sensor 0: 0.00 (full left)
- Sensor 1: 0.33 (left-center)
- Sensor 2: 0.67 (right-center)
- Sensor 3: 1.00 (full right)

**Pan law:**
```
Left gain  = cos(pan × π/2)
Right gain = sin(pan × π/2)
```

**Implementation per sensor:**
```
[r audio-out-0]
|
[t a a]
|    |
|    [expr sin(0.0*1.5708)]   # Right gain (0.0 for sensor 0)
|    |
|    [*~]                     # Right channel
|    |
|    [s mix-right]
|
[expr cos(0.0*1.5708)]        # Left gain (1.0 for sensor 0)
|
[*~]                          # Left channel
|
[s mix-left]
```

**Sensor pan values:**
- Sensor 0: pan = 0.0
- Sensor 1: pan = 0.33
- Sensor 2: pan = 0.67
- Sensor 3: pan = 1.0

**R25: Mix all channels**
```
[r mix-left]  [r mix-right]
|             |
[+~]          [+~]            # Sum all left, all right
|             |
[dac~ 1 2]                    # Output to audio interface
```

### 6.6 Lighting Output Subpatch (lighting-output.pd)

**R26: Forward heartbeat to lighting bridge**

```
[r ibi-valid-0]
|
[t f f]
|    |
|    [pack f 0]               # IBI, sensor ID
|    |
|    [prepend /light]
|    |
|    [prepend 0]
|    |
|    [prepend /pulse]
|    |
[packOSC]
|
[udpsend]
|
[connect 127.0.0.1 8001(
|
[send(
```

**Repeat for sensors 1-3**

**R27: Connection feedback**
```
[loadbang]
|
[print Lighting-OSC-connected-to-port-8001]
```

---

## 7. Testing Infrastructure Integration

### 7.1 ESP32 Simulator

**Use existing simulator from firmware testing:**

```bash
# Terminal 1: Start Pd patch
pd ~/heartbeat/patches/heartbeat-main.pd

# Terminal 2: Run simulator
python3 esp32_simulator.py --port 8000 --sensors 4
```

**R28: Simulator generates realistic IBIs**
- BPM range: 50-100 (600-1200ms IBI)
- Variation: ±10% per beat
- Independent timing per sensor

### 7.2 Validation Points

**R29: Verify OSC reception**
- Pd console shows "VALID-IBI" messages
- Rate: 50-100 messages/minute per sensor

**R30: Verify audio output**
- Hear percussion samples at heartbeat rate
- Stereo positioning: Sensor 0=left, Sensor 3=right

**R31: Verify lighting OSC**
```bash
# Terminal 3: Monitor lighting messages
python3 osc_receiver.py --port 8001

# Should show: /light/N/pulse messages
```

---

## 8. Latency Budget

**Target: <50ms total (heartbeat event → audio output)**

| Stage | Typical | Maximum |
|-------|---------|---------|
| ESP32 → network | 10ms | 25ms |
| Network → Pd OSC parse | 1ms | 5ms |
| Pd processing | 3ms | 10ms |
| Audio buffer (64 samples @ 48kHz) | 1.3ms | 1.3ms |
| USB transfer | 2ms | 5ms |
| DAC conversion | 1ms | 2ms |
| **Total** | **18ms** | **48ms** |

**R32: Measure actual latency**
- Use oscilloscope: LED pulse (ESP32) → audio output
- Or: Click track + visual cue
- Acceptable: <50ms

---

## 9. Acceptance Criteria

**Phase 1 Complete:**

- ✅ Pd patch runs without errors
- ✅ Receives OSC from simulator (or real ESP32s)
- ✅ Audio triggers within 50ms of heartbeat
- ✅ 4 samples play independently
- ✅ Stereo panning correct (audible L/R separation)
- ✅ Lighting OSC messages sent
- ✅ No audio glitches over 30 minutes
- ✅ Latency <50ms (measured)
- ✅ CPU usage <30% (monitor with `top`)

---

## 10. Troubleshooting

### 10.1 No Audio Output

**Check audio interface:**
```bash
aplay -l                      # Verify card 1 exists
speaker-test -c 2 -D hw:1,0   # Test direct output
```

**Check Pd DSP:**
- Pd menu: Media → Audio ON (or Ctrl+/)
- Pd console: "DSP ON" message

**Check sample paths:**
- Pd console: "couldn't open ..." errors
- Use absolute paths in patch

### 10.2 OSC Not Received

**Check port binding:**
```bash
sudo netstat -uln | grep 8000
# Should show: 0.0.0.0:8000
```

**Check firewall:**
```bash
sudo ufw allow 8000/udp
```

**Check Pd console:**
- Should print OSC-ERROR for malformed messages
- No output = nothing received

### 10.3 Audio Glitches/Clicks

**Increase audio buffer:**
```bash
pd -audiobuf 128    # Default 64, try 128 or 256
```

**Check CPU usage:**
```bash
top -p $(pgrep pd)
# If >80%, reduce sample rate or simplify patch
```

**Check disk I/O:**
```bash
iostat -x 1
# High %util = disk bottleneck, use SSD
```

### 10.4 Wrong Stereo Positioning

**Verify pan calculations:**
- Sensor 0 should be hard left
- Sensor 3 should be hard right
- Test with headphones for clear separation

**Check speaker connections:**
- Swap L/R cables if reversed

---

## 11. Known Limitations (Phase 1)

**Intentional simplifications:**
- Single sample per sensor (no variety)
- No reverb or effects
- No Launchpad control
- Hardcoded sample paths
- No visual feedback in patch
- No BPM-based parameter mapping
- No sample randomization
- No velocity scaling

**These will be addressed in Phase 2+**

---

## 12. Next Steps (Phase 2 Preview)

**Phase 2 additions:**
- Multiple samples per sensor (randomization)
- Reverb effect ([freeverb~])
- Sample banks (switch between sets)
- BPM-based velocity scaling

**Phase 3 additions:**
- Launchpad MIDI input
- Sample selection via grid
- One-shot triggers
- LED feedback

---

## 13. File Deliverables

**Required files:**
```
~/heartbeat/
├── patches/
│   ├── heartbeat-main.pd
│   ├── osc-input.pd
│   ├── sensor-process.pd
│   ├── sound-engine.pd
│   ├── spatial-mixer.pd
│   └── lighting-output.pd
├── samples/
│   └── percussion/
│       ├── kick-01.wav
│       ├── snare-01.wav
│       ├── hat-01.wav
│       └── clap-01.wav
└── docs/
    └── audio-phase1-trd.md (this document)
```

---

*End of Technical Reference Document*

**Document Version:** 1.0  
**Last Updated:** 2025-11-09  
**Status:** Ready for implementation  
**Estimated Effort:** 3-4 hours  
**Dependencies:** ESP32 firmware (or simulator), USB audio interface, sample library