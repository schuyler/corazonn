# Amor Installation Process Management
#
# Start all processes: foreman start
# Start specific: foreman start processor,audio
# Scale processes: foreman start -c processor=1,audio=1
#
# Port topology:
#   processor (8000) -> audio (8001), lighting (8002)
#   launchpad (8001, 8005) <-> sequencer (8003) -> audio routing (8004)

# Core beat detection - receives PPG from ESP32s
processor: python3 -m amor.processor --input-port 8000 --audio-port 8001 --lighting-port 8002

# Audio playback - receives beat events from processor
audio: python3 -m amor.audio --port 8001

# Lighting control - receives beat events from processor
lighting: cd lighting && python3 src/main.py

# Sample/loop sequencer - manages audio routing and loop state
sequencer: python3 -m amor.sequencer

# Launchpad MIDI bridge - hardware controller (optional if no Launchpad)
launchpad: python3 -m amor.launchpad

# Visualization for debugging (optional)
# viewer: python3 -m amor.viewer --ppg-id 0
