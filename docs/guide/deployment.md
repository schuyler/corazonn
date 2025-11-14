# Amor Deployment Checklist

Step-by-step checklist for first deployment. Follow in order.

---

## PHASE 1: PRE-DEPLOYMENT SETUP

### Infrastructure

- [ ] WiFi network operational
- [ ] WiFi SSID and password available
- [ ] Server host has static or reserved IP address
- [ ] Note server IP: `_______________`

### Hardware

- [ ] USB audio interface connected (or built-in audio working)
- [ ] Speakers/headphones connected and tested
- [ ] Novation Launchpad connected via USB (optional)
- [ ] ESP32 units available (×4) with PPG sensors attached
- [ ] ESP32 units have power (USB power banks or cables)

### Kasa Smart Bulb Setup (MUST DO FIRST)

- [ ] Download Kasa app on phone
- [ ] Power on each Kasa bulb
- [ ] Add each bulb to WiFi network via Kasa app
- [ ] Verify bulbs controllable via app
- [ ] Note: Bulbs MUST be on SAME network as server

### Software Dependencies

- [ ] Check Python version: `python3 --version` (must be 3.10+)
- [ ] Check PortAudio installed:
  ```bash
  python3 -c "import sounddevice; print('OK')"
  ```
- [ ] Python dependencies installed:
  ```bash
  uv sync
  # OR
  pip install -e ".[audio,lighting,sequencer]"
  ```

- [ ] PlatformIO installed for firmware:
  ```bash
  pip install platformio
  ```

- [ ] Check network connectivity:
  ```bash
  ping 8.8.8.8
  ```

---

## PHASE 2: CONFIGURATION FILES

### Create Required Directories

- [ ] Create sampler data directory:
  ```bash
  mkdir -p data
  ```

- [ ] Create sequencer state directory:
  ```bash
  mkdir -p amor/state
  ```

### Firmware Configuration (per ESP32 unit)

- [ ] Copy config template:
  ```bash
  cd firmware/amor
  cp include/config.h.example include/config.h
  ```

- [ ] Edit `firmware/amor/include/config.h`:
  - [ ] Set `WIFI_SSID` to your network name
  - [ ] Set `WIFI_PASSWORD` to your network password
  - [ ] Set `SERVER_IP` to server host IP from Phase 1
  - [ ] Set `PPG_ID` to `0` (for first unit)
  - [ ] Set `PPG_GPIO` to `32` (WROOM) or `4` (S3)

### Lighting Configuration

- [ ] Discover Kasa bulbs on network:
  ```bash
  python3 lighting/tools/discover-kasa.py
  ```

- [ ] Note bulb IP addresses:
  - Bulb 1: `_______________`
  - Bulb 2: `_______________`
  - Bulb 3: `_______________`
  - Bulb 4: `_______________`

- [ ] Edit `amor/config/lighting.yaml`:
  - [ ] Update bulb IP addresses
  - [ ] Assign bulbs to zones (0-3)
  - [ ] Verify hue mappings (0-3 colors)

---

## PHASE 3: PREPARE SAMPLE LIBRARY (PRIORITY 1)

### Verify Sample Configuration

- [ ] Verify `amor/config/samples.yaml` exists
- [ ] Review sample configuration:
  ```bash
  cat amor/config/samples.yaml
  ```

### Check Existing Samples

- [ ] Check PPG sample directory:
  ```bash
  ls -lh audio/sounds/ppg_samples/
  ```
- [ ] Count PPG samples:
  ```bash
  ls audio/sounds/ppg_samples/ | wc -l
  ```
  **Note**: For full testing, need at least 2 banks × 8 samples × 4 PPGs = 64 samples minimum. The 'default' bank is required, plus at least one other bank for testing Control Mode 2 (bank switching).

- [ ] Check ambient loop directory:
  ```bash
  ls -lh audio/sounds/ambient_loops/
  ```
- [ ] Count ambient loops (need 32 total):
  ```bash
  ls audio/sounds/ambient_loops/ | wc -l
  ```

### Download Freesound Library (if needed)

- [ ] If samples are missing, set up Freesound credentials:
  ```bash
  cp .env.example .env
  ```
- [ ] Edit `.env` file:
  - [ ] Add `FREESOUND_CLIENT_ID`
  - [ ] Add `FREESOUND_CLIENT_SECRET`

- [ ] Authenticate with Freesound:
  ```bash
  cd audio
  python download_freesound_library.py auth
  ```

- [ ] Follow authentication instructions in terminal
- [ ] Download sample library:
  ```bash
  python download_freesound_library.py download
  cd ..
  ```

- [ ] Wait for download to complete (may take several minutes)

### Verify Complete Sample Library

- [ ] Verify PPG samples exist (minimum 64 for 2-bank testing):
  ```bash
  ls audio/sounds/ppg_samples/ | wc -l
  # Minimum: 64 (2 banks × 8 samples × 4 PPGs)
  # Optimal: 256 (8 banks × 8 samples × 4 PPGs)
  ```

- [ ] Check samples.yaml structure has multiple banks:
  ```bash
  grep -A 3 "ppg_0:" amor/config/samples.yaml | grep -E "^\s+\w+:"
  # Should show bank names like: default:, bank1:, etc.
  ```

- [ ] Verify at least 'default' and one other bank exist
- [ ] Note available bank names: `_______________`

- [ ] Verify all 32 ambient loops exist:
  ```bash
  ls audio/sounds/ambient_loops/ | wc -l
  # Should show: 32
  ```

- [ ] Test play a sample file (verify audio working):
  ```bash
  # If you have aplay installed:
  aplay audio/sounds/ppg_samples/kick_001.wav
  # OR
  # play audio/sounds/ppg_samples/kick_001.wav
  ```

**Important**: Control Mode 2 (PPG Sample Bank Select) requires at least 2 banks to be testable. If you only have the 'default' bank, bank switching will appear to work but won't produce audible differences.

---

## PHASE 4: FLASH ESP32 UNITS (PRIORITY 2)

### Unit 0

- [ ] Connect ESP32 unit 0 via USB
- [ ] Verify `PPG_ID` is `0` in `config.h`
- [ ] Flash firmware:
  ```bash
  cd firmware/amor
  pio run --target upload
  ```
- [ ] Open serial monitor (press Ctrl+C to exit):
  ```bash
  pio device monitor
  # Alternative with filtering:
  # pio device monitor | grep -i "wifi\|server\|connected"
  ```
- [ ] Verify WiFi connection in serial output
- [ ] Verify "Connected to server" message
- [ ] Press Ctrl+C to exit monitor
- [ ] Disconnect USB, power from battery

### Unit 1

- [ ] Connect ESP32 unit 1 via USB
- [ ] Edit `config.h`: Change `PPG_ID` to `1`
- [ ] Flash firmware: `pio run --target upload`
- [ ] Monitor serial: `pio device monitor`
- [ ] Verify WiFi and server connection
- [ ] Disconnect USB, power from battery

### Unit 2

- [ ] Connect ESP32 unit 2 via USB
- [ ] Edit `config.h`: Change `PPG_ID` to `2`
- [ ] Flash firmware: `pio run --target upload`
- [ ] Monitor serial: `pio device monitor`
- [ ] Verify WiFi and server connection
- [ ] Disconnect USB, power from battery

### Unit 3

- [ ] Connect ESP32 unit 3 via USB
- [ ] Edit `config.h`: Change `PPG_ID` to `3`
- [ ] Flash firmware: `pio run --target upload`
- [ ] Monitor serial: `pio device monitor`
- [ ] Verify WiFi and server connection
- [ ] Disconnect USB, power from battery

### Test ESP32 Admin Commands (Port 8006)

- [ ] Verify all 4 ESP32 units are powered on and connected
- [ ] Send restart command to unit 0:
  ```bash
  oscsend localhost 8006 /esp32/restart i 0
  ```
- [ ] Monitor serial output on unit 0
- [ ] Verify unit 0 restarts (see "Rebooting..." message)
- [ ] Verify unit 0 reconnects to WiFi
- [ ] Verify unit 0 resumes sending PPG data
- [ ] Test restart on unit 1:
  ```bash
  oscsend localhost 8006 /esp32/restart i 1
  ```
- [ ] Verify unit 1 restarts and reconnects
- [ ] Verify units 0 and 1 both sending data after restart

**Note**: Admin commands useful for remote restart without physical access to ESP32 units.

---

## PHASE 5: START PROCESSOR (PRIORITY 3)

### Launch Processor

- [ ] Open new terminal window
- [ ] Navigate to project: `cd /home/user/corazonn`
- [ ] Start processor:
  ```bash
  python -m amor.processor --input-port 8000 --beats-port 8001
  ```

### Verify Processor

- [ ] Wait 5 seconds for buffer initialization
- [ ] Check processor logs show "Listening for PPG data on port 8000"
- [ ] Place finger on PPG sensor (any unit)
- [ ] Check processor logs show PPG data received: `Received /ppg/0`
- [ ] Check processor logs show beat detection: `Beat detected from PPG 0`
- [ ] Check BPM appears reasonable (40-200 range)
- [ ] Leave processor running in this terminal

---

## PHASE 6: START AUDIO ENGINE (PRIORITY 4)

### Launch Audio

- [ ] Open new terminal window
- [ ] Navigate to project: `cd /home/user/corazonn`
- [ ] Start audio:
  ```bash
  python -m amor.audio --port 8001 --control-port 8003
  ```

### Verify Audio

- [ ] Check audio logs show "Listening for beat events on port 8001"
- [ ] Check audio logs show beat events received: `Received /beat/0`
- [ ] Place finger on PPG sensor
- [ ] Listen for sample playback on heartbeats
- [ ] Verify samples are audible
- [ ] Verify beats sync with heartbeat rhythm
- [ ] Leave audio running in this terminal

---

## PHASE 7: START SEQUENCER (PRIORITY 5)

### Launch Sequencer

- [ ] Open new terminal window
- [ ] Navigate to project: `cd /home/user/corazonn`
- [ ] Start sequencer:
  ```bash
  python -m amor.sequencer
  ```

### Verify Sequencer

- [ ] Check sequencer logs show initialization
- [ ] Check logs show "Listening on port 8003"
- [ ] Leave sequencer running in this terminal

---

## PHASE 8: START LAUNCHPAD (PRIORITY 6)

### Launch Launchpad

- [ ] Verify Launchpad connected via USB:
  ```bash
  lsusb | grep -i novation
  ```

- [ ] Open new terminal window
- [ ] Navigate to project: `cd /home/user/corazonn`
- [ ] Start Launchpad:
  ```bash
  python -m amor.launchpad
  ```

### Verify Launchpad

- [ ] Check logs show "Entered Programmer Mode"
- [ ] Check logs show "Connected to Launchpad"
- [ ] Verify grid lights up
- [ ] Place finger on PPG sensor
- [ ] Verify LED pulses on beats (grid row 0 column 0)
- [ ] Leave Launchpad running in this terminal

### Test Basic Sample Selection (Normal Mode)

Before testing control modes, verify normal Launchpad operation:

- [ ] Press button at row 0, column 0 (PPG 0, sample 0)
- [ ] Verify button lights up
- [ ] Verify other buttons in row 0 turn off (radio behavior)
- [ ] Place finger on PPG 0 sensor
- [ ] Verify sample 0 plays on beats
- [ ] Press button at row 0, column 3 (PPG 0, sample 3)
- [ ] Verify button lights up, column 0 turns off
- [ ] Verify sample 3 plays on beats (different sound)
- [ ] Test PPG 1: Press row 1, column 2
- [ ] Verify independent selection per PPG (radio per row)
- [ ] Test PPG 2: Press row 2, column 5
- [ ] Test PPG 3: Press row 3, column 7
- [ ] Verify each PPG can select different samples (0-7 in default bank)

**Note**: From this point forward, you can use the Launchpad for easier testing instead of manual OSC commands.

---

## PHASE 9: TEST SEQUENCER CONTROL MODES (PRIORITY 7)

The Launchpad has 4 modal control modes accessed via the top row control buttons. Test each mode to verify modal operation.

### Control Mode Basics

- [ ] Verify only one control mode can be active at a time
- [ ] Verify scene buttons (right side) are disabled when in control mode
- [ ] Verify pressing active control button again exits the mode

### Control 0: Lighting Program Select (Session Button)

- [ ] Press "Session" button (top row, rightmost position)
- [ ] Verify Session button LED lights up (mode active)
- [ ] Verify grid row 0 shows 6 lit buttons (programs 0-5)
- [ ] Verify rows 1-7 are dark (unused)
- [ ] Press row 0, column 1 (rotating_gradient program)
- [ ] Verify lighting changes to rotating gradient pattern
- [ ] Verify mode stays active (can select another program)
- [ ] Press Session button again to exit mode
- [ ] Verify grid returns to normal PPG/loop display
- [ ] Verify lighting program selection persisted

### Control 1: BPM Multiplier (User 1 Button)

- [ ] Press "User 1" button (top row, second from right)
- [ ] Verify User 1 button LED lights up (mode active)
- [ ] Verify grid row 0 shows 8 lit buttons (multipliers)
- [ ] Verify rows 1-7 are dark (unused)
- [ ] Press row 0, column 4 (2x multiplier)
- [ ] Verify beats play at 2x speed (both audio and lighting)
- [ ] Place finger on PPG sensor, verify doubled beat rate
- [ ] Press row 0, column 2 (1x - back to normal)
- [ ] Verify beats return to normal rate
- [ ] Press User 1 button again to exit mode
- [ ] Verify grid returns to normal display

### Control 2: PPG Sample Bank Select (Mixer Button)

- [ ] Press "Mixer" button (top row, second from left)
- [ ] Verify Mixer button LED lights up (mode active)
- [ ] Verify grid shows 8×8 matrix (all rows lit)
- [ ] Verify current bank for each PPG is highlighted
- [ ] Press row 0, column 1 (PPG 0 → bank 1)
- [ ] Verify PPG 0 now plays samples from bank 1
- [ ] Place finger on PPG 0 sensor, verify different samples available
- [ ] Press row 1, column 2 (PPG 1 → bank 2)
- [ ] Press row 2, column 3 (PPG 2 → bank 3)
- [ ] Verify each PPG can be on different bank independently
- [ ] Press Mixer button again to exit mode
- [ ] Verify bank selections persisted

### Control 3: Audio Effects Assignment (User 2 Button)

**Note**: This mode may not be fully implemented yet. Test what's available.

- [ ] Press "User 2" button (top row, leftmost position)
- [ ] Verify User 2 button LED lights up (mode active)
- [ ] Verify grid shows 8 rows (one per PPG 0-7)
- [ ] Verify column 0 (Clear) and columns 1-5 (effects) are lit
- [ ] Press row 0, column 1 (Reverb on PPG 0)
- [ ] Verify reverb effect applied to PPG 0 samples
- [ ] Press row 0, column 3 (Delay on PPG 0)
- [ ] Verify both reverb and delay active (stacked effects)
- [ ] Press row 0, column 0 (Clear all effects for PPG 0)
- [ ] Verify effects cleared, PPG 0 back to dry sound
- [ ] Test effect on PPG 1: row 1, column 2 (Phaser)
- [ ] Press User 2 button again to exit mode
- [ ] Verify grid returns to normal display

### Mode Switching

- [ ] Press Session button (Control 0)
- [ ] Verify mode activates
- [ ] Press Mixer button (Control 2) without exiting first
- [ ] Verify Session button turns off
- [ ] Verify Mixer button lights up
- [ ] Verify grid updates to show bank selection layout
- [ ] Verify only one mode active at a time

---

## PHASE 10: TEST AMBIENT LOOPS (PRIORITY 8)

### Test Latching Loops (Using Launchpad)

- [ ] Press button at row 4, column 0 on Launchpad
- [ ] Verify button lights up
- [ ] Verify ambient loop starts playing
- [ ] Press same button again
- [ ] Verify button turns off
- [ ] Verify loop stops (toggle behavior)
- [ ] Test multiple latching loops (rows 4-5, up to 6 max)

### Test Momentary Loops (Using Launchpad)

- [ ] Press and hold button at row 6, column 0
- [ ] Verify button lights while held
- [ ] Verify ambient loop plays while held
- [ ] Release button
- [ ] Verify button turns off
- [ ] Verify loop stops immediately
- [ ] Test multiple momentary loops (rows 6-7, up to 4 max)

### Alternative: Test via OSC Commands

If Launchpad not available, test via OSC:

- [ ] Start loop 0:
  ```bash
  oscsend localhost 8003 /loop/start i 0
  ```
- [ ] Verify loop plays
- [ ] Stop loop 0:
  ```bash
  oscsend localhost 8003 /loop/stop i 0
  ```
- [ ] Verify loop stops

**Note**: Loops 0-15 are latching (toggle behavior), loops 16-31 are momentary (play while active).

### Verify Loop Limits

- [ ] Start 6 latching loops (0-5)
- [ ] Verify all 6 play simultaneously
- [ ] Try to start 7th latching loop
- [ ] Verify oldest loop stops (loop 0)
- [ ] Start 4 momentary loops
- [ ] Try to start 5th momentary loop
- [ ] Verify oldest momentary loop stops

---

## PHASE 11: START LIGHTING (PRIORITY 9)

### Launch Lighting

- [ ] Open new terminal window
- [ ] Navigate to project: `cd /home/user/corazonn`
- [ ] Start lighting:
  ```bash
  python -m amor.lighting --config amor/config/lighting.yaml
  ```

### Verify Lighting

- [ ] Check lighting logs show "Connected to N bulbs"
- [ ] Check logs show "Listening for beat events on port 8001"
- [ ] Place finger on PPG sensor unit 0
- [ ] Verify zone 0 bulbs pulse on beats
- [ ] Test unit 1 → verify zone 1 bulbs pulse
- [ ] Test unit 2 → verify zone 2 bulbs pulse
- [ ] Test unit 3 → verify zone 3 bulbs pulse

### Test BPM Color Mapping

- [ ] Slow heartbeat (relax, breathe slowly)
- [ ] Verify bulbs show blue/cooler colors
- [ ] Fast heartbeat (light exercise, tap quickly)
- [ ] Verify bulbs show red/warmer colors

### Test Lighting Programs

**Using Launchpad** (recommended):
- [ ] Press "Session" button (top left control button)
- [ ] Verify lighting program changes
- [ ] Check bulbs show different behavior
- [ ] Press Session button multiple times to cycle through programs

**Alternative via OSC commands**:
- [ ] Send program change (use program name as string):
  ```bash
  oscsend localhost 8003 /program s rotating_gradient
  ```

- [ ] Verify program switches (check different behavior)
- [ ] Test other programs:
  ```bash
  oscsend localhost 8003 /program s soft_pulse
  oscsend localhost 8003 /program s breathing_sync
  oscsend localhost 8003 /program s convergence
  oscsend localhost 8003 /program s wave_chase
  oscsend localhost 8003 /program s intensity_reactive
  ```

- [ ] Leave lighting running in this terminal

---

## PHASE 12: START SAMPLER (PRIORITY 10)

### Launch Sampler

- [ ] Open new terminal window
- [ ] Navigate to project: `cd /home/user/corazonn`
- [ ] Start sampler:
  ```bash
  python -m amor.sampler
  ```

### Verify Sampler

- [ ] Check sampler logs show "Listening for PPG data on port 8000"
- [ ] Check logs show "Listening for control messages on port 8003"
- [ ] Leave sampler running in this terminal

### Test Recording (Using Launchpad)

- [ ] Place finger on PPG sensor unit 0
- [ ] Press scene button 0 (right side of grid)
- [ ] Verify button lights up (recording indicator)
- [ ] Keep finger on sensor for 10-15 seconds
- [ ] Press scene button 0 again to stop
- [ ] Verify button turns off
- [ ] Check sampler logs show "Recording stopped for PPG 0"
- [ ] Verify file created in `/data/` directory:
  ```bash
  ls -lh data/
  ```

### Test Playback (Using Launchpad)

- [ ] Press scene button 4 (right side of grid)
- [ ] Verify button lights up (playback indicator)
- [ ] Verify recorded heartbeat plays on virtual channel 4
- [ ] Verify audio logs show beats from channel 4: `Received /beat/4`
- [ ] Verify samples trigger on recorded rhythm
- [ ] Press scene button 4 again to stop
- [ ] Verify button turns off

### Alternative: Test via OSC Commands

If Launchpad not available:

- [ ] Start recording:
  ```bash
  oscsend localhost 8003 /sampler/record i 0
  ```
- [ ] Wait 10-15 seconds, then stop:
  ```bash
  oscsend localhost 8003 /sampler/stop i 0
  ```
- [ ] Assign to virtual channel 4:
  ```bash
  oscsend localhost 8003 /sampler/assign ii 0 4
  ```
- [ ] Start playback:
  ```bash
  oscsend localhost 8003 /sampler/play i 4
  ```
- [ ] Stop playback:
  ```bash
  oscsend localhost 8003 /sampler/stop i 4
  ```

### Test Multiple Virtual Channels

- [ ] Record from PPG units 1, 2, 3 (repeat recording steps)
- [ ] Assign to virtual channels 5, 6, 7
- [ ] Start all 4 virtual channels simultaneously
- [ ] Verify all play independently with different rhythms
- [ ] Verify audio routing: channels 4-7 map to sample banks 0-3

---

## PHASE 13: FULL SYSTEM INTEGRATION TEST

### All Components Running

- [ ] Verify 6 terminal windows running:
  1. Processor
  2. Audio
  3. Sequencer
  4. Lighting
  5. Sampler
  6. Launchpad (optional)

- [ ] Verify ESP32 units powered on (4 units)
- [ ] Verify Kasa bulbs responsive

### End-to-End Data Flow

- [ ] Place finger on each PPG sensor (0-3 in sequence)
- [ ] Verify processor receives PPG data from all 4 units
- [ ] Verify audio plays samples for all 4 heartbeats
- [ ] Verify lighting pulses in all 4 zones
- [ ] Verify Launchpad LEDs pulse for all 4 PPG units
- [ ] Verify different rhythms for different heartbeats

### Sample Selection (Using Launchpad)

- [ ] Press row 0, column 2 (PPG 0 → sample 2)
- [ ] Verify button lights up, previous button turns off (radio behavior)
- [ ] Verify audio plays different sample on PPG 0 beats
- [ ] Press row 1, column 4 (PPG 1 → sample 4)
- [ ] Press row 2, column 6 (PPG 2 → sample 6)
- [ ] Press row 3, column 1 (PPG 3 → sample 1)
- [ ] Verify each PPG plays assigned sample
- [ ] Verify selections persist across beats

### Ambient Loops (Using Launchpad)

- [ ] Press 3 buttons on rows 4-5 (latching loops)
- [ ] Verify all 3 loops play continuously
- [ ] Hold 2 buttons on rows 6-7 (momentary loops)
- [ ] Verify loops play while held
- [ ] Release momentary buttons, verify they stop
- [ ] Verify loops don't stop on beats
- [ ] Verify PPG samples layer over loops

### Virtual Channels

- [ ] Record from all 4 PPG units
- [ ] Assign recordings to virtual channels 4-7
- [ ] Start all 4 virtual channels
- [ ] Verify 8 total rhythms playing:
  - 4 real (PPG 0-3 from sensors)
  - 4 virtual (channels 4-7 from recordings)

- [ ] Verify audio routing:
  - Channels 0,4 → left pan
  - Channels 1,5 → center-left pan
  - Channels 2,6 → center-right pan
  - Channels 3,7 → right pan

### Stress Test

- [ ] All 4 PPG units active with fingers on sensors
- [ ] All 4 virtual channels playing
- [ ] 6 latching loops active
- [ ] 4 momentary loops active (hold buttons)
- [ ] All 4 lighting zones pulsing
- [ ] Launchpad responding to inputs
- [ ] Verify system remains stable (no crashes)
- [ ] Verify audio quality (no distortion, xruns)
- [ ] Verify timing (no lag, beats sync)

---

## PHASE 14: PERFORMANCE MONITORING

### System Resources

- [ ] Check CPU usage:
  ```bash
  top
  ```

- [ ] Verify CPU < 80% under full load
- [ ] Check memory usage
- [ ] Verify no memory leaks over 5 minutes

### Network Performance

- [ ] Check ESP32 units not dropping packets
- [ ] Open serial monitor on each unit
- [ ] Verify no "WiFi reconnect" messages
- [ ] Verify consistent "Sent PPG data" messages

### Audio Performance

- [ ] Check audio logs for xruns (buffer underruns)
- [ ] Verify no "ALSA xrun" or "PortAudio underrun" messages
- [ ] Verify audio latency < 50ms (beat to sound)
- [ ] Test latency: clap near PPG sensor, verify sample plays immediately

### Lighting Performance

- [ ] Check bulb response time
- [ ] Verify bulbs pulse within 100ms of beat
- [ ] Verify no dropped commands (all beats trigger pulse)
- [ ] Check lighting logs for connection errors

---

## PHASE 15: STARTUP AUTOMATION (Optional)

### Procfile Setup

- [ ] Install foreman:
  ```bash
  gem install foreman
  # OR
  pip install honcho  # Python alternative
  ```

- [ ] Verify Procfile exists:
  ```bash
  cat Procfile
  ```

- [ ] Test automated startup:
  ```bash
  foreman start
  # OR
  honcho start
  ```

- [ ] Verify all services start in single terminal
- [ ] Verify all services show logs with colored prefixes

### Systemd Services (Production)

- [ ] Create systemd service file: `/etc/systemd/system/amor.service`
- [ ] Configure service to run Procfile on boot
- [ ] Enable service: `sudo systemctl enable amor`
- [ ] Start service: `sudo systemctl start amor`
- [ ] Check status: `sudo systemctl status amor`
- [ ] Verify auto-restart on failure

---

## TROUBLESHOOTING

### ESP32 Not Connecting

- [ ] Check WiFi credentials in `config.h`
- [ ] Verify server IP is correct
- [ ] Check ESP32 and server on same network
- [ ] Check firewall allows UDP port 8000
- [ ] Try pinging server from another device

### No Audio Output

- [ ] Check audio device available: `aplay -l`
- [ ] Check volume not muted: `alsamixer`
- [ ] Verify sample files exist
- [ ] Check audio logs for file loading errors
- [ ] Test system audio: `speaker-test -c 2`

### Bulbs Not Responding

- [ ] Verify bulbs on network: `ping <bulb_ip>`
- [ ] Check bulb IPs in `lighting.yaml`
- [ ] Rediscover bulbs: `python3 lighting/tools/discover-kasa.py`
- [ ] Check firewall allows port 9999
- [ ] Try manual control: `kasa --host <ip> on`

### Launchpad Not Detected

- [ ] Check USB connection: `lsusb | grep -i novation`
- [ ] Check MIDI ports: `python -m mido.ports`
- [ ] Try different USB port
- [ ] Check permissions: add user to `audio` group
- [ ] Restart Launchpad (unplug/replug)

### High CPU Usage

- [ ] Check number of active loops (reduce to < 10)
- [ ] Check virtual channels (reduce to < 4)
- [ ] Check audio voice limit in `samples.yaml`
- [ ] Reduce lighting update rate
- [ ] Close unused applications

### Audio Latency / Xruns

- [ ] Increase audio buffer size (edit `audio.py`)
- [ ] Close background applications
- [ ] Use dedicated audio interface (not built-in)
- [ ] Disable WiFi power saving
- [ ] Use wired ethernet instead of WiFi

---

## PHASE 16: HEALTH CHECK

### System Stability

- [ ] All services running without error messages for 2 minutes
- [ ] No Python exceptions in any terminal
- [ ] No OSC connection errors

### ESP32 Reconnection Test

- [ ] Unplug one ESP32 unit
- [ ] Wait 10 seconds
- [ ] Replug unit (power back on)
- [ ] Verify it reconnects within 30 seconds
- [ ] Check serial monitor shows "Connected to server"
- [ ] Verify beats resume from that PPG unit
- [ ] Check processor logs show PPG data received

### Network Resilience

- [ ] Disconnect server WiFi (if applicable)
- [ ] Wait 5 seconds
- [ ] Reconnect WiFi
- [ ] Verify ESP32 units reconnect
- [ ] Verify system resumes normal operation

### Configuration Backup

- [ ] Create backup of working configuration:
  ```bash
  tar -czf amor-config-backup-$(date +%Y%m%d).tar.gz \
    firmware/amor/include/config.h \
    amor/config/ \
    amor/state/ \
    .env
  ```

- [ ] Note backup location: `_______________`

---

## DEPLOYMENT COMPLETE

### Final Checklist

- [ ] All 6 services running without errors
- [ ] All 4 ESP32 units sending data
- [ ] Audio playing samples on all heartbeats
- [ ] Lighting syncing to all heartbeats
- [ ] Launchpad responsive to all controls
- [ ] Sampler recording and playing virtual channels
- [ ] System stable for 10+ minutes
- [ ] Performance metrics acceptable (CPU, latency)

### Notes / Issues

```
[Space for deployment notes]
```

### Next Steps

- [ ] Create backup configuration
- [ ] Document any configuration changes
- [ ] Test with actual participants
- [ ] Prepare for extended run (overnight test)
- [ ] Plan for teardown/packing

---

**Deployment Date:** _______________

**Deployed By:** _______________

**Location:** _______________
