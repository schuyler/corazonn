# Follow Your Heart (Corazonn)

**The Experience:**

Participants lie on their backs in a dimly lit room, each resting a hand on a weighted fabric sensor pad. Within seconds, their heartbeat is detected and the room responds with synchronized sound and light.

Each heartbeat triggers a sustained tonal sampleâ€”tubular bells or similar resonant sounds. With multiple participants (up to 4), individual rhythms layer into emergent polyrhythms. A 72 BPM heart rate creates one pattern while 58 BPM adds slower counterpoint. No two sessions sound identical.

Colored lights pulse with each heartbeat. Each participant's zone responds to their physiology, spatially mapping the group's collective rhythms. As participants relax, heart rates may decrease and potentially synchronize, triggering special audio or lighting events.

A fifth participant can operate a Novation Launchpad MIDI controller to shape the experienceâ€”selecting samples, switching modes, adjusting effects, and controlling lighting patternsâ€”essentially conducting the installation in real-time.

Participants enter/exit freely. Sensors auto-detect connection/disconnection, fading sounds over 1-2 seconds. Sessions run 5+ minutes.

**Technical Architecture:**

Four wireless sensor units, each containing a PulseSensor.com optical sensor, ESP32-S3 microcontroller, and USB battery pack in an 8"Ã—8" weighted fabric pad. Each operates independently for 6-8 hours per charge. The ESP32 samples the sensor at 50Hz, bundles 5 samples every 100ms, and transmits via WiFi using OSC protocol.

A Python sensor processor receives raw photoplethysmography data on port 8000, detects heartbeats using threshold-crossing algorithm with noise rejection, calculates BPM from inter-beat intervals, and publishes beat events to ports 8001 (audio) and 8002 (lighting).

Python audio engine receives beat events and plays WAV samples (sustained tones like tubular bells) via USB audio interface (M-Audio Mobile Pre) to stereo speakers. Each participant has independent audio channel allowing overlapping playback.

Python lighting controller receives beat events and controls 4 TP-Link Kasa smart bulbs via local LAN (python-kasa library). BPM maps to color (slow=blue, fast=red), pulsing from baseline to full brightness on each beat.

Optional Novation Launchpad provides 64-pad MIDI grid for live control (via mido library), with rows per participant and columns per function.

All components communicate via OSC, can start/stop independently, and run on Lenovo M73 running Debian 13 connected to private WiFi network for festival deployment.
