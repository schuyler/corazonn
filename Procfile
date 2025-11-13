# Amor Installation Process Management
#
# Start all processes: foreman start
# Start specific: foreman start processor,audio
# Scale processes: foreman start -c processor=1,audio=1
#
# Port topology (broadcast bus architecture with SO_REUSEPORT):
#   8000: PPG data - ESP32 -> Processor + Viewer
#   8001: Beat events - Processor -> Audio + Lighting + Viewer
#   8003: Control bus - Sequencer <-> Audio <-> Launchpad
#   8006: ESP32 admin - restart commands

# Core beat detection - receives PPG from ESP32s, broadcasts beats
processor: python3 -m amor.processor --input-port 8000 --beats-port 8001

# Audio playback - receives beat events (8001) and control messages (8003)
audio: python3 -m amor.audio --port 8001 --control-port 8003

# Lighting control - receives beat events from processor
lighting: python3 -m amor.lighting --config amor/config/lighting.yaml

# Sample/loop sequencer - manages audio routing and loop state
sequencer: python3 -m amor.sequencer

# Launchpad MIDI bridge - hardware controller (optional if no Launchpad)
launchpad: python3 -m amor.launchpad

# Sampler - records PPG data and plays back on virtual channels 4-7
sampler: python3 -m amor.sampler

# Visualization for debugging (optional)
# viewer: python3 -m amor.viewer --ppg-id 0
