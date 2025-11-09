## Audio Pipeline Phase 1 - Pure Data OSC → Stereo Audio

Reference: `../reference/phase1-trd.md`

### Prerequisites

- [ ] **Task 0.1**: Verify Python 3.8+ installed
  - Run: `python3 --version`
  - Expected: Python 3.8.0 or higher
  - **Status**: Required for test scripts

- [ ] **Task 0.2**: Install python-osc package
  - Run: `pip3 install python-osc`
  - Verify: `python3 -c "from pythonosc import udp_client; print('OK')"`
  - Expected output: `OK`
  - **Status**: Required for test-osc-sender.py

- [ ] **Task 0.3**: Run automated Pure Data installation (TRD R41-R47)
  - Run: `cd /home/user/corazonn/audio/scripts && ./install-dependencies.sh`
  - Script will detect distribution and install Pd + externals
  - Verify: `pd -version` shows Pd-0.52-1 or newer
  - Verify externals: `[packOSC]`, `[unpackOSC]`, `[udpsend]`, `[udpreceive]` create without errors
  - **Status**: Automated installation completes successfully

- [ ] **Task 0.4**: Configure audio interface (TRD R1, R48-R54)
  - Run: `cd /home/user/corazonn/audio/scripts && ./detect-audio-interface.sh`
  - Script will detect USB audio interfaces and generate ~/.asoundrc
  - Test: `speaker-test -t sine -f 440 -c 2 -l 1` produces tone
  - Fallback: Built-in audio acceptable for development
  - **Status**: Audio output verified, ~/.asoundrc configured

- [ ] **Task 0.5**: Verify sample library exists (TRD R3-R4)
  - Check: `/home/user/corazonn/audio/samples/percussion/starter/` directory exists
  - Verify files present:
    - `kick-01.wav`
    - `snare-01.wav`
    - `hat-01.wav`
    - `clap-01.wav`
  - Run: `soxi /home/user/corazonn/audio/samples/percussion/starter/*.wav`
  - Verify all: 48000 Hz, 1 channel (mono), 16-bit
  - **Status**: Starter pack verified (4 samples, pre-normalized)

- [ ] **Task 0.6**: Verify testing infrastructure exists
  - Check: `/home/user/corazonn/testing/esp32_simulator.py` exists
  - Check: `/home/user/corazonn/testing/osc_receiver.py` exists
  - Verify: Both scripts executable or can run with `python3`
  - If missing: test-osc-sender.py (Task 2.1) provides standalone testing
  - **Status**: Testing tools available for integration testing

### Component 1: Project Structure

- [ ] **Task 1.1**: Create directory structure
  - Create: `/home/user/corazonn/audio/` (if not exists)
  - Create: `/home/user/corazonn/audio/patches/`
  - Create: `/home/user/corazonn/audio/samples/percussion/starter/`
  - Create: `/home/user/corazonn/audio/scripts/`
  - **Status**: Directory structure matches TRD Section 13.1

- [ ] **Task 1.2**: Create audio README
  - File: `/home/user/corazonn/audio/README.md`
  - Document: Quick start guide
  - Document: How to run Pd patch
  - Document: How to test with test-osc-sender.py
  - Document: Integration with ESP32 simulator
  - Include troubleshooting section from TRD Section 10
  - **Status**: README complete with navigation

### Component 2: Test Infrastructure Scripts

- [ ] **Task 2.1**: Create test-osc-sender.py (TRD R33-R40)
  - File: `/home/user/corazonn/audio/scripts/test-osc-sender.py`
  - Imports: `pythonosc.udp_client`, `argparse`, `time`, `random`, `threading`
  - Arguments: `--port` (default 8000), `--sensors` (default 4), `--host` (default 127.0.0.1)
  - **Status**: Script skeleton with argument parsing

- [ ] **Task 2.2**: Implement IBI generation (TRD R36)
  - Function: `generate_ibi()` returns random int in 600-1200ms range
  - Add ±10% variation: `int(base_ibi * random.uniform(0.9, 1.1))`
  - Clamp to 300-3000ms range
  - **Status**: IBI generation realistic (50-100 BPM)

- [ ] **Task 2.3**: Implement sensor threads (TRD R35, R37)
  - Function: `sensor_thread(sensor_id, client)`
  - Loop: Generate IBI, send OSC, sleep for IBI duration
  - Create thread per sensor (independent timing)
  - Use threading.Event for clean shutdown
  - **Status**: Multi-sensor support with independent timing

- [ ] **Task 2.4**: Implement OSC sending (TRD R34, R38)
  - Create `SimpleUDPClient(host, port)`
  - Send message: `client.send_message(f"/heartbeat/{sensor_id}", ibi)`
  - Print: `f"Sent /heartbeat/{sensor_id} {ibi}"`
  - **Status**: OSC messages sent to configured host:port

- [ ] **Task 2.5**: Implement signal handling (TRD R39)
  - Catch KeyboardInterrupt
  - Set shutdown_event for all threads
  - Join all threads with timeout
  - Print final statistics (messages sent per sensor)
  - **Status**: Graceful shutdown with Ctrl+C

- [ ] **Task 2.6**: Test test-osc-sender.py
  - Run: `python3 test-osc-sender.py --port 8000 --sensors 4`
  - Verify console output shows sent messages
  - Verify different IBI values per sensor
  - Verify Ctrl+C stops cleanly
  - **Status**: Script runs independently, ready for Pd testing

- [ ] **Task 2.7**: Create install-dependencies.sh (TRD R41-R47)
  - File: `/home/user/corazonn/audio/scripts/install-dependencies.sh`
  - Make executable: `chmod +x install-dependencies.sh`
  - Detect distribution: Check `/etc/os-release` or `lsb_release`
  - Install Pd: Distribution-specific commands (apt-get, dnf, pacman)
  - **Status**: Script detects distribution correctly

- [ ] **Task 2.8**: Implement Pd installation (TRD R42-R43)
  - Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y puredata`
  - Fedora: `sudo dnf install -y puredata`
  - Arch: `sudo pacman -S --noconfirm puredata`
  - Verify: `pd -version` exits 0 and prints version
  - **Status**: Pd installs successfully

- [ ] **Task 2.9**: Implement externals installation (TRD R44-R45)
  - Print instructions for manual external installation via Pd GUI
  - Note: Command-line external installation varies by system
  - Provide verification command: `pd -lib mrpeach -lib cyclone -send "quit"`
  - Print troubleshooting: "If externals missing, use Pd menu: Help → Find Externals"
  - **Status**: Installation guide printed

- [ ] **Task 2.10**: Test install-dependencies.sh
  - Run: `./install-dependencies.sh`
  - Verify: Pd installed
  - Verify: Instructions printed for externals
  - Exit code: 0 on success, 1 on failure
  - **Status**: Script completes, Pd ready to use

- [ ] **Task 2.11**: Create detect-audio-interface.sh (TRD R48-R54)
  - File: `/home/user/corazonn/audio/scripts/detect-audio-interface.sh`
  - Make executable: `chmod +x detect-audio-interface.sh`
  - Run: `aplay -l` and capture output
  - Parse: Extract card numbers and names (grep "card")
  - **Status**: Audio devices detected

- [ ] **Task 2.12**: Implement USB interface detection (TRD R49-R50)
  - Search for keywords: "USB", "Scarlett", "Focusrite", "External"
  - Extract card number from first USB match
  - Generate ~/.asoundrc with detected card number
  - Template from TRD Section 3.2 (pcm.!default and ctl.!default)
  - **Status**: USB interface prioritized

- [ ] **Task 2.13**: Implement fallback and testing (TRD R51-R52)
  - If no USB interface: Prompt to use card 0 (built-in)
  - Backup existing ~/.asoundrc to ~/.asoundrc.backup if exists
  - Run: `speaker-test -t sine -f 440 -c 2 -l 1`
  - Print: "Testing audio... you should hear a 440Hz tone for 2 seconds"
  - **Status**: Audio configuration tested

- [ ] **Task 2.14**: Test detect-audio-interface.sh
  - Run: `./detect-audio-interface.sh`
  - Verify: ~/.asoundrc created or updated
  - Verify: Backup created if file existed
  - Verify: speaker-test produces audible tone
  - **Status**: Script configures audio correctly

### Component 3: Main Patch Structure

- [ ] **Task 3.1**: Create heartbeat-main.pd skeleton (TRD R14)
  - File: `/home/user/corazonn/audio/patches/heartbeat-main.pd`
  - Add header comment block:
    ```
    Heartbeat Installation - Phase 1
    Audio Output: 48kHz stereo
    OSC Input: port 8000 (heartbeats from ESP32)
    OSC Output: port 8001 (lighting commands)
    ```
  - Add: `[declare -lib mrpeach -lib cyclone]`
  - Add: `[declare -path ../samples/percussion/starter]` (TRD R23)
  - **Status**: Patch opens in Pd without errors

- [ ] **Task 3.2**: Implement DSP control (TRD R15)
  - Add: `[loadbang]` object
  - Connect to: `[; pd dsp 1(` message
  - Add comment: "Auto-start DSP on patch load"
  - **Status**: DSP turns on automatically when patch loads

- [ ] **Task 3.3**: Add subpatch placeholders (TRD R16)
  - Add: `[pd osc-input]` (create empty subpatch)
  - Add: `[pd sensor-0-process]`, `[pd sensor-1-process]`, `[pd sensor-2-process]`, `[pd sensor-3-process]`
  - Add: `[pd sound-engine]`
  - Add: `[pd spatial-mixer]`
  - Note: Lighting output will be added in Task 8.6 as 4 abstraction instances
  - Add: `[dac~ 1 2]` for stereo output
  - **Status**: Main patch structure complete, ready for subpatch implementation

### Component 4: OSC Input Subpatch

- [ ] **Task 4.1**: Create osc-input.pd (TRD R17)
  - Open subpatch: `[pd osc-input]` in heartbeat-main.pd
  - Add: `[udpreceive 8000]` object
  - Add: `[unpackOSC]` object below udpreceive
  - Connect: udpreceive → unpackOSC
  - **Status**: OSC receiver listening on port 8000

- [ ] **Task 4.2**: Implement message routing (TRD R6-R8)
  - Add: `[routeOSC /heartbeat/0 /heartbeat/1 /heartbeat/2 /heartbeat/3]`
  - Connect: unpackOSC → routeOSC
  - Add 4 outlets from routeOSC
  - **Status**: Messages routed by sensor ID

- [ ] **Task 4.3**: Implement send buses (TRD R17)
  - Add: `[s ibi-0]` connected to /heartbeat/0 outlet
  - Add: `[s ibi-1]` connected to /heartbeat/1 outlet
  - Add: `[s ibi-2]` connected to /heartbeat/2 outlet
  - Add: `[s ibi-3]` connected to /heartbeat/3 outlet
  - **Status**: IBI values broadcast to sensor processing subpatches

- [ ] **Task 4.4**: Implement error handling (TRD R18)
  - Add: `[print OSC-ERROR]` connected to unpackOSC right outlet (errors)
  - Test: Send malformed OSC, verify console prints error
  - **Status**: Malformed messages logged to Pd console

### Component 5: Sensor Processing Subpatch

- [ ] **Task 5.1**: Create sensor-process.pd abstraction (TRD R19)
  - Create file: `/home/user/corazonn/audio/patches/sensor-process.pd`
  - This will be instantiated 4 times with argument: `[sensor-process 0]`, `[sensor-process 1]`, etc.
  - Add comment: "Sensor ID: $1"
  - Note: IBI input will be received via `[r ibi-$1]` in Task 5.2
  - **Status**: Abstraction file created

- [ ] **Task 5.2**: Implement IBI reception (TRD R19)
  - Add: `[r ibi-$1]` (receive for sensor N, using creation argument)
  - Add: `[t f f f]` (trigger 3 copies)
  - **Status**: IBI received and split for validation, forwarding, BPM calc

- [ ] **Task 5.3**: Implement IBI validation (TRD R9-R10, R19-R20)
  - From leftmost trigger outlet:
  - Add: `[moses 300]` (split at lower bound)
  - From right outlet (< 300): `[print INVALID-IBI-LOW]` → block
  - From left outlet (>= 300): `[moses 3001]` (split at upper bound)
  - From left outlet (300-3000): `[print VALID-IBI]` → continue
  - From right outlet (> 3000): `[print INVALID-IBI-HIGH]` → block
  - **Status**: Only valid IBIs (300-3000ms) pass through

- [ ] **Task 5.4**: Forward valid IBI (TRD R19)
  - From valid path: `[s ibi-valid-$1]`
  - This will be received by sound-engine and lighting-output
  - **Status**: Valid IBIs broadcast to downstream subpatches

- [ ] **Task 5.5**: Implement BPM calculation (TRD R19)
  - From middle trigger outlet:
  - Add: `[expr 60000/$f1]` (convert IBI to BPM)
  - Add: `[s bpm-$1]` (send for future use)
  - Add: `[print BPM]` for debugging
  - **Status**: BPM calculated and available (not used in Phase 1)

- [ ] **Task 5.6**: Implement disconnection detection (TRD R55)
  - From rightmost trigger outlet (Task 5.2):
  - Add: `[t b b]` (trigger 2 bangs: one to cancel pending delay, one to schedule new delay)
  - Connect first bang to `[delay 5000]` right inlet (cancel any pending disconnection event)
  - Connect second bang to `[delay 5000]` left inlet (schedule disconnection in 5000ms)
  - From delay outlet: Connect to `[s sensor-disconnected-$1]` (broadcast disconnection event)
  - Signal flow: Each IBI cancels the pending timeout and schedules a new one; if 5 seconds pass without an IBI, delay fires
  - **Status**: Disconnection detected after 5 seconds of no messages

- [ ] **Task 5.7**: Implement fade-out on disconnection (TRD R56)
  - Add: `[loadbang]` (initialize on patch load)
  - Add: `[1(` message (set initial gain to 1.0)
  - Connect loadbang → 1 message → line~
  - Add: `[r sensor-disconnected-$1]` (receive disconnection event from Task 5.6)
  - Add: `[0 2000(` message (fade to 0 over 2000ms)
  - Connect to same `[line~]` object (both loadbang and disconnection messages feed same line~)
  - Add: `[s~ channel-gain-$1]` (send~ for audio-rate gain control)
  - Connect line~ output → send~
  - **Status**: Channels initialize at full gain and fade out smoothly over 2 seconds on disconnection

- [ ] **Task 5.8**: Implement fade-in on reconnection (TRD R57)
  - Add: `[r ibi-valid-$1]` (detect any valid IBI = potential reconnection)
  - Connect directly to `[snapshot~]` to sample current gain level from line~
  - From snapshot~ output: `[< 0.5]` (check if currently faded out, threshold at half volume)
  - Add: `[sel 1]` (select "true" case when gain is low = was disconnected)
  - Connect to `[1 1000(` message (fade to 1 over 1000ms)
  - Connect to same `[line~]` as Task 5.7 (all three message sources feed same line~)
  - Integration: Only sends fade-in message when currently faded out, preventing repeated fade-ins
  - **Status**: Reconnected channels fade in smoothly over 1 second, with state tracking to avoid repeated fades

- [ ] **Task 5.9**: Update main patch with sensor-process instances
  - In heartbeat-main.pd:
  - Replace `[pd sensor-0-process]` with `[sensor-process 0]`
  - Replace `[pd sensor-1-process]` with `[sensor-process 1]`
  - Replace `[pd sensor-2-process]` with `[sensor-process 2]`
  - Replace `[pd sensor-3-process]` with `[sensor-process 3]`
  - **Status**: 4 sensor processors instantiated with unique IDs

### Component 6: Sound Engine Subpatch

- [ ] **Task 6.1**: Create sound-engine.pd skeleton (TRD R21)
  - Open subpatch: `[pd sound-engine]` in heartbeat-main.pd
  - Add comment: "Table-based sample playback - 4 percussion samples"
  - **Status**: Sound engine subpatch created

- [ ] **Task 6.2**: Implement sample table creation (TRD R21)
  - Add: `[table sample-0]` (Pd menu: Put → Array)
  - Configure: Name="sample-0", Size=96000 (2 sec @ 48kHz initial), Save contents=yes
  - Repeat for: `[table sample-1]`, `[table sample-2]`, `[table sample-3]`
  - **Status**: 4 sample tables created (will auto-resize on load)

- [ ] **Task 6.3**: Implement sample loading (TRD R21)
  - Add: `[loadbang]`
  - Add: `[t b b b b]` (trigger 4 bangs)
  - Connect each bang to sample loading chain:
    - Bang 1: `[read -resize kick-01.wav sample-0(` → `[soundfiler]` → `[s sample-0-length]`
    - Bang 2: `[read -resize snare-01.wav sample-1(` → `[soundfiler]` → `[s sample-1-length]`
    - Bang 3: `[read -resize hat-01.wav sample-2(` → `[soundfiler]` → `[s sample-2-length]`
    - Bang 4: `[read -resize clap-01.wav sample-3(` → `[soundfiler]` → `[s sample-3-length]`
  - **Status**: Samples load into tables at patch startup

- [ ] **Task 6.4**: Verify sample loading
  - Open heartbeat-main.pd
  - Check Pd console for errors
  - Expected: "read 48000 samples into table sample-0" (or similar)
  - If errors: Check `[declare -path]` in main patch, verify sample files exist
  - **Status**: All 4 samples loaded without errors

- [ ] **Task 6.5**: Implement sensor 0 playback chain (TRD R22)
  - Add: `[r ibi-valid-0]` (trigger on valid IBI)
  - Add: `[t b b]` (split into 2 bangs)
  - Left bang: Trigger sample playback
  - Right bang: Get sample length and start phasor
  - Add: `[r sample-0-length]` → `[/ 48000]` (convert samples to seconds)
  - Add: `[* 1000]` (convert seconds to milliseconds for line~)
  - Create message box: `[0, 1 $1(` (format: start at 0, ramp to 1 over $1 ms)
  - Connect millisecond value to message box inlet
  - Add: `[line~]` (generates audio-rate ramp 0→1 over sample duration)
  - Note: line~ uses comma-separated format "initial_value, target_value time_ms"
  - **Status**: Time-varying phasor controls sample position with correct message format

- [ ] **Task 6.6**: Implement sensor 0 table reading (TRD R22)
  - From line~ output (normalized 0→1 position):
    - Connect to: `[*~ ]` (multiply~ object, create with right inlet)
    - Connect `[r sample-0-length]` to `[sig~]` (convert control-rate to audio-rate)
    - Connect `[sig~]` output to right inlet of *~ (scale normalized position to sample indices)
  - Note: This converts 0.0→1.0 ramp into 0→length sample indices
  - Connect *~ output to: `[tabread4~ sample-0]` (4-point interpolation table reader)
  - Signal flow: line~ generates position → *~ scales to indices → tabread4~ reads samples
  - **Status**: Sample playback with smooth interpolation

- [ ] **Task 6.7**: Implement sensor 0 envelope (TRD R22)
  - Add: `[r ibi-valid-0]` (separate receive for envelope trigger)
  - From left bang path (Task 6.5):
    - Connect to: `[1 5, 0 5 40(` message
    - Format: vline~ accepts target/time pairs, with optional delay as third parameter
    - Breakdown: "1 5" = ramp to 1.0 in 5ms (attack), "0 5 40" = after 40ms delay, ramp to 0 in 5ms (release)
    - Total envelope: 5ms attack + 40ms sustain + 5ms release = 50ms
    - Connect to: `[vline~]` (precise audio-rate envelope generator)
  - Add: `[*~]` (multiply sample output by envelope)
  - Connect tabread4~ → *~ ← vline~
  - **Status**: Sample plays with 50ms anti-click envelope

- [ ] **Task 6.8**: Output sensor 0 audio (TRD R22)
  - Add: `[r~ channel-gain-0]` (receive fade gain from Task 5.7/5.8)
  - Add: `[*~]` (multiply envelope output by channel gain for disconnect/reconnect fading)
  - Connect envelope output (from Task 6.7) to left inlet of *~
  - Connect channel-gain to right inlet of *~
  - Add: `[s~ audio-out-0]` (send~ for audio-rate signal)
  - Connect *~ output → send~
  - Signal flow: Sample playback with envelope gets multiplied by channel gain before output
  - **Status**: Sensor 0 audio signal available to spatial mixer with disconnect/reconnect fading

- [ ] **Task 6.9**: Duplicate for sensors 1-3 (TRD R22)
  - Copy entire chain from 6.5-6.8 three times
  - Sensor 1: Use ibi-valid-1, sample-1, sample-1-length, channel-gain-1, audio-out-1
  - Sensor 2: Use ibi-valid-2, sample-2, sample-2-length, channel-gain-2, audio-out-2
  - Sensor 3: Use ibi-valid-3, sample-3, sample-3-length, channel-gain-3, audio-out-3
  - Important: Each sensor must multiply by its channel-gain before sending to audio-out (as in Task 6.8)
  - **Status**: All 4 sensors have independent playback chains with disconnect/reconnect fading

### Component 7: Spatial Mixer Subpatch

- [ ] **Task 7.1**: Create spatial-mixer.pd skeleton (TRD R24)
  - Open subpatch: `[pd spatial-mixer]` in heartbeat-main.pd
  - Add comment: "Constant-power stereo panning - 4 sensors to 2 channels"
  - **Status**: Spatial mixer subpatch created

- [ ] **Task 7.2**: Implement sensor 0 panning (pan=0.0, full left) (TRD R24)
  - Add: `[r~ audio-out-0]` (receive audio from sound engine)
  - Add: `[t a a]` (split audio signal to L and R)
  - Left channel: `[*~ 1.0]` → `[s~ mix-left]` (cos(0*π/2) = 1.0)
  - Right channel: `[*~ 0.0]` → `[s~ mix-right]` (sin(0*π/2) = 0.0)
  - Verify: L²+R² = 1.0²+0.0² = 1.0 (constant power law)
  - **Status**: Sensor 0 panned hard left

- [ ] **Task 7.3**: Implement sensor 1 panning (pan=0.33, left-center) (TRD R24)
  - Add: `[r~ audio-out-1]`
  - Add: `[t a a]`
  - Calculate gains: cos(0.33*π/2) ≈ 0.87, sin(0.33*π/2) ≈ 0.49
  - Left channel: `[*~ 0.87]` → `[s~ mix-left]`
  - Right channel: `[*~ 0.49]` → `[s~ mix-right]`
  - Verify: L²+R² = 0.87²+0.49² = 0.76+0.24 ≈ 1.0 (constant power law)
  - **Status**: Sensor 1 panned left-center

- [ ] **Task 7.4**: Implement sensor 2 panning (pan=0.67, right-center) (TRD R24)
  - Add: `[r~ audio-out-2]`
  - Add: `[t a a]`
  - Calculate gains: cos(0.67*π/2) ≈ 0.49, sin(0.67*π/2) ≈ 0.87
  - Left channel: `[*~ 0.49]` → `[s~ mix-left]`
  - Right channel: `[*~ 0.87]` → `[s~ mix-right]`
  - Verify: L²+R² = 0.49²+0.87² = 0.24+0.76 ≈ 1.0 (constant power law)
  - **Status**: Sensor 2 panned right-center

- [ ] **Task 7.5**: Implement sensor 3 panning (pan=1.0, full right) (TRD R24)
  - Add: `[r~ audio-out-3]`
  - Add: `[t a a]`
  - Left channel: `[*~ 0.0]` → `[s~ mix-left]` (cos(1*π/2) = 0.0)
  - Right channel: `[*~ 1.0]` → `[s~ mix-right]` (sin(1*π/2) = 1.0)
  - Verify: L²+R² = 0.0²+1.0² = 1.0 (constant power law)
  - **Status**: Sensor 3 panned hard right

- [ ] **Task 7.6**: Implement channel summing (TRD R25)
  - Left channel: `[r~ mix-left]` (receives 4 signals from Tasks 7.2-7.5)
  - Right channel: `[r~ mix-right]` (receives 4 signals from Tasks 7.2-7.5)
  - Note: Pure Data's send~/receive~ architecture automatically sums multiple sources
  - Implementation: When multiple `[s~ mix-left]` objects send to same name, `[r~ mix-left]` outputs their sum
  - This is built-in behavior - no explicit summing object needed
  - **Status**: All sensors mixed to stereo via automatic signal summing

- [ ] **Task 7.7**: Implement clipping protection (TRD R25)
  - Add: `[clip~ -0.95 0.95]` to left channel
  - Add: `[clip~ -0.95 0.95]` to right channel
  - Add comment: "Safety limiter prevents distortion when all 4 sensors trigger"
  - **Status**: Output protected from clipping

- [ ] **Task 7.8**: Connect to DAC (TRD R25)
  - Add: `[dac~ 1 2]` in main patch (if not already present from Task 3.3)
  - Connect spatial-mixer left output → dac~ left inlet
  - Connect spatial-mixer right output → dac~ right inlet
  - **Status**: Audio routed to stereo output

### Component 8: Lighting Output Subpatch

- [ ] **Task 8.1**: Create lighting-output.pd abstraction (TRD R26)
  - Create file: `/home/user/corazonn/audio/patches/lighting-output.pd`
  - This will be instantiated 4 times with argument: `[lighting-output 0]`, etc.
  - Add comment: "Forward heartbeat to lighting bridge - Sensor ID: $1"
  - Note: IBI input will be received via `[r ibi-valid-$1]` in Task 8.2
  - **Status**: Lighting output abstraction created

- [ ] **Task 8.2**: Implement OSC address formatting (TRD R11, R26)
  - Add: `[r ibi-valid-$1]`
  - Add: `[t f f]` (split IBI value)
  - Right outlet: `[f $1]` (get sensor ID from creation argument)
  - Add: `[makefilename /light/%d/pulse]` (create address string)
  - **Status**: OSC address formatted as /light/N/pulse

- [ ] **Task 8.3**: Implement OSC message packing (TRD R26)
  - Add: `[prepend]` (combine address and IBI value)
  - Connect address string to right inlet of prepend
  - Connect IBI value to left inlet of prepend
  - Add: `[packOSC]` (convert to OSC binary format)
  - **Status**: OSC message packed correctly

- [ ] **Task 8.4**: Implement UDP sender (TRD R11-R13, R26)
  - Add: `[udpsend]`
  - Connect packOSC → udpsend
  - Add: `[loadbang]` → `[connect 127.0.0.1 8001(` → udpsend
  - Add comment: "Connect to localhost:8001 (lighting bridge)"
  - **Status**: OSC messages sent to lighting bridge

- [ ] **Task 8.5**: Implement connection feedback (TRD R27)
  - Add: `[loadbang]`
  - Add: `[makefilename Lighting-OSC-connected-to-port-8001-for-sensor-%d]`
  - Feed $1 (sensor ID) to makefilename
  - Add: `[print]`
  - **Status**: Connection logged to Pd console at startup

- [ ] **Task 8.6**: Update main patch with lighting-output instances
  - In heartbeat-main.pd:
  - Replace `[pd lighting-output]` with 4 instances:
    - `[lighting-output 0]`
    - `[lighting-output 1]`
    - `[lighting-output 2]`
    - `[lighting-output 3]`
  - **Status**: 4 lighting outputs instantiated

### Component 9: Testing

- [ ] **Task 9.1**: Configure Pd audio settings (TRD R2)
  - Open heartbeat-main.pd
  - Menu: Media → Audio Settings
  - Set sample rate: 48000
  - Set audio buffer: 64 (or 128 if glitches occur)
  - Set channels: 2 (stereo)
  - Set Audio API: ALSA (Linux) or appropriate for OS
  - Set Device: hw:1,0 (USB interface) or hw:0,0 (built-in)
  - **Status**: Audio settings match hardware configuration

- [ ] **Task 9.2**: Test DSP startup
  - Open heartbeat-main.pd
  - Check Pd console: Should print "DSP ON" automatically via loadbang
  - Menu: Media → Audio ON should show checkmark
  - **Status**: DSP auto-starts correctly

- [ ] **Task 9.3**: Test sample loading
  - Open heartbeat-main.pd
  - Check Pd console for sample loading messages
  - Expected: "read NNNNN samples into table sample-0" (×4)
  - If errors: Verify `[declare -path]` and sample file locations
  - **Status**: All samples loaded without errors

- [ ] **Task 9.4**: Test OSC receiver standalone (TRD R28-R29)
  - Terminal 1: Open Pd patch: `cd /home/user/corazonn/audio/patches && pd heartbeat-main.pd`
  - Terminal 2: Run test sender: `cd /home/user/corazonn/audio/scripts && python3 test-osc-sender.py --port 8000 --sensors 4`
  - Verify Pd console shows "VALID-IBI" messages at ~60-100 per minute per sensor
  - **Status**: OSC messages received and validated

- [ ] **Task 9.5**: Test audio output (TRD R30)
  - With test sender running (Task 9.4):
  - Listen for percussion samples triggering
  - Verify 4 distinct sounds (kick, snare, hat, clap)
  - Verify timing matches test sender output (~1 beat per second per sensor)
  - **Status**: Audio triggers on heartbeat messages

- [ ] **Task 9.6**: Test stereo positioning (TRD R30)
  - With test sender running (Task 9.4):
  - Use headphones for clear stereo separation
  - Verify sensor 0 (kick) comes from hard left
  - Verify sensor 3 (clap) comes from hard right
  - Verify sensors 1 and 2 positioned in center-left and center-right
  - **Status**: Spatial positioning correct and audible

- [ ] **Task 9.7**: Test lighting OSC output (TRD R31)
  - Terminal 1: Pd patch running with test sender (Task 9.4)
  - Terminal 3: `cd /home/user/corazonn/testing && python3 osc_receiver.py --port 8001`
  - Verify receiver shows "/light/N/pulse" messages
  - Verify IBI values match input messages from test sender
  - Verify all 4 sensor IDs appear (0-3)
  - **Status**: Lighting OSC forwarded correctly

- [ ] **Task 9.8**: Test with ESP32 simulator (TRD Section 7.2)
  - Stop test-osc-sender.py
  - Terminal 2: `cd /home/user/corazonn/testing && python3 esp32_simulator.py --port 8000 --sensors 4 --bpm 60,72,58,80`
  - Verify Pd receives messages (console shows VALID-IBI)
  - Verify audio output matches 4 different heart rates
  - Verify stereo positioning matches sensor IDs
  - **Status**: Integration with firmware simulator successful

- [ ] **Task 9.9**: Run 30-minute stability test (TRD Success Criteria)
  - Start: Pd patch + ESP32 simulator (or test sender)
  - Monitor: Pd console for errors
  - Monitor: CPU usage with `top -p $(pgrep pd)` in Terminal 4
  - Listen: For audio glitches, dropouts, or pops
  - Check: No crashes, no error messages
  - Verify: CPU usage < 30% throughout test
  - **Status**: Runs for 30+ minutes without glitches

- [ ] **Task 9.10**: Measure latency (TRD R32, Section 8)
  - Method 1 (visual): Observe test sender output vs audio
  - Method 2 (precise): Use oscilloscope if available (LED → audio out)
  - Acceptable: < 50ms (imperceptible to audience)
  - If > 50ms: Reduce audio buffer size or check system load
  - **Status**: Latency measured and acceptable

### Component 10: Documentation & Completion

- [ ] **Task 10.1**: Create sample library README
  - File: `/home/user/corazonn/audio/samples/README.md`
  - Document: Starter pack files and licenses (CC0)
  - Document: Freesound.org attribution with creator names and URLs
  - Document: Curated expansion pack links (search URLs by category)
  - Document: Processing instructions (sox commands from TRD Section 4.3)
  - Document: Format requirements (48kHz, mono, -6dBFS, WAV)
  - Document: Directory organization for custom samples
  - **Status**: Sample README complete with attribution and expansion guide

- [ ] **Task 10.2**: Document Pd patch architecture
  - Update: `/home/user/corazonn/audio/README.md`
  - Document: Patch structure (main + 6 subpatches)
  - Document: Data flow (OSC input → processing → audio + lighting output)
  - Document: How to modify samples (change [declare -path] or filenames)
  - Document: How to adjust panning (modify pan calculations in spatial-mixer)
  - **Status**: Architecture documented for future modifications

- [ ] **Task 10.3**: Document testing procedures
  - Update: `/home/user/corazonn/audio/README.md`
  - Document: Standalone testing (test-osc-sender.py workflow)
  - Document: Integration testing (ESP32 simulator workflow)
  - Document: How to verify OSC reception (console output)
  - Document: How to verify lighting output (osc_receiver.py on port 8001)
  - Document: Troubleshooting checklist (TRD Section 10)
  - **Status**: Testing procedures clearly documented

- [ ] **Task 10.4**: Verify all acceptance criteria (TRD Section 9)
  - ✅ Pd patch runs without errors
  - ✅ Receives OSC from simulator (or real ESP32s)
  - ✅ Audio triggers within 50ms of heartbeat
  - ✅ 4 samples play independently
  - ✅ Stereo panning correct (audible L/R separation)
  - ✅ Lighting OSC messages sent
  - ✅ No audio glitches over 30 minutes
  - ✅ Latency <50ms (measured)
  - ✅ CPU usage <30%
  - **Status**: All 9 acceptance criteria met

- [ ] **Task 10.5**: Validate audio and sample requirements (TRD R1-R5)
  - Verify R1: Audio interface configured (48kHz stereo output)
  - Verify R2: Pd audio settings correct (sample rate, buffer size)
  - Verify R3: Sample library directory structure exists
  - Verify R4: All 4 starter samples present and valid format
  - Verify R5: Sample playback tested and working
  - **Status**: Audio interface and sample library requirements verified

- [ ] **Task 10.6**: Validate OSC protocol implementation (TRD R6-R13)
  - Verify R6-R8: OSC input receives /heartbeat/N messages
  - Verify R9-R10: IBI validation (300-3000ms range enforced)
  - Verify R11-R13: OSC output sends /light/N/pulse to port 8001
  - Test: Send invalid IBIs and verify rejection
  - Test: Monitor lighting OSC output with osc_receiver.py
  - **Status**: OSC protocol fully compliant with TRD specification

- [ ] **Task 10.7**: Validate Pd patch structure (TRD R14-R27)
  - Verify R14-R16: Main patch structure (DSP control, subpatches, DAC)
  - Verify R17-R18: OSC input subpatch (udpreceive, routing, error handling)
  - Verify R19-R20: Sensor processing (IBI validation, forwarding, BPM calc)
  - Verify R21-R23: Sound engine (sample loading, playback, tables)
  - Verify R24-R25: Spatial mixer (constant-power panning, summing, clipping)
  - Verify R26-R27: Lighting output (OSC formatting, UDP sending)
  - **Status**: All Pd subpatches implement TRD requirements correctly

- [ ] **Task 10.8**: Validate support scripts (TRD R28-R54)
  - Verify R28-R32: Testing requirements (OSC reception, audio output, latency)
  - Verify R33-R40: test-osc-sender.py (IBI generation, multi-sensor, OSC sending)
  - Verify R41-R47: install-dependencies.sh (distribution detection, Pd installation)
  - Verify R48-R54: detect-audio-interface.sh (USB detection, .asoundrc generation)
  - Test: Run all scripts and verify successful execution
  - **Status**: All support scripts functional and meet TRD requirements

- [ ] **Task 10.9**: Validate disconnection handling (TRD R55-R57)
  - Verify R55: Disconnection detection after 5 seconds without messages
  - Verify R56: Fade-out on disconnection (2 second ramp to zero)
  - Verify R57: Fade-in on reconnection (1 second ramp to full volume)
  - Test: Stop test sender for one sensor, verify fade-out, restart, verify fade-in
  - Test: Monitor audio levels during disconnect/reconnect transitions
  - **Status**: Disconnection handling smooth and imperceptible to audience

- [ ] **Task 10.10**: Update completion status
  - Update: `docs/audio/tasks/phase1-audio.md` (this file)
  - Mark completion date
  - Note any deviations from TRD (if any)
  - Document any issues encountered and solutions
  - **Status**: Phase 1 audio pipeline complete

---

## Task Execution Notes

**Order**: Tasks should be completed in sequence within each component. Components 2 and 3 can be done in parallel, but all prerequisites (Component 0-1) must complete first.

**Testing Strategy**:
- Components 0-2: Setup and infrastructure (testable independently)
- Components 3-8: Incremental Pd patch development (test each subpatch as completed)
- Component 9: Full integration and stability testing
- Component 10: Documentation and acceptance

**Hardware Required**:
- Linux machine with audio output (USB audio interface recommended, built-in acceptable)
- Speakers or headphones (headphones better for stereo testing)
- ESP32s with firmware (optional - can use simulators)

**Software Required**:
- Pure Data 0.52+ with mrpeach and cyclone externals
- Python 3.8+ with python-osc library
- ALSA audio system (Linux)
- Testing infrastructure from Components 1-5 (ESP32 simulator)

**Dependencies**:
- Testing infrastructure (testing/esp32_simulator.py, testing/osc_receiver.py) should exist from prior phases
- If not available, test-osc-sender.py provides standalone testing capability

**Time Estimate**:
- Prerequisites (Component 0): 20-30 min (mostly automated)
- Project structure (Component 1): 10 min
- Test scripts (Component 2): 60-90 min
- Main patch (Component 3): 15 min
- OSC input (Component 4): 20 min
- Sensor processing (Component 5): 45 min
- Sound engine (Component 6): 60 min
- Spatial mixer (Component 7): 30 min
- Lighting output (Component 8): 30 min
- Testing (Component 9): 60 min (+ 30 min stability test)
- Documentation (Component 10): 30 min
- **Total: 6-7 hours** (including 30-minute stability test)

**Acceptance**: Phase 1 complete when all tasks checked off, patch runs for 30+ minutes without errors, and all 9 acceptance criteria verified.

**Key Features Delivered**:
- Pure Data patch receiving OSC heartbeat messages
- 4-channel sample playback with stereo panning
- OSC forwarding to lighting bridge
- Automated testing infrastructure
- Complete documentation for expansion
- Stable operation for installation use
