#!/bin/bash
# Start FluidSynth daemon for MIDI output
#
# This script starts FluidSynth with ALSA MIDI and audio output,
# configured for use with amor.midi module.
#
# Usage:
#   ./scripts/start_fluidsynth.sh [soundfont_path] [audio_device]
#
# Examples:
#   ./scripts/start_fluidsynth.sh
#   ./scripts/start_fluidsynth.sh /path/to/custom.sf2
#   ./scripts/start_fluidsynth.sh /path/to/custom.sf2 hw:1,0

set -e

# Default configuration
DEFAULT_SOUNDFONT="/usr/share/sounds/sf2/FluidR3_GM.sf2"
DEFAULT_AUDIO_DEVICE="default"  # ALSA default device (uses dmix for mixing)

# Parse arguments
SOUNDFONT="${1:-$DEFAULT_SOUNDFONT}"
AUDIO_DEVICE="${2:-$DEFAULT_AUDIO_DEVICE}"

# Validate soundfont exists
if [ ! -f "$SOUNDFONT" ]; then
    echo "Error: SoundFont file not found: $SOUNDFONT"
    echo ""
    echo "Install FluidR3_GM soundfont:"
    echo "  sudo apt install fluid-soundfont-gm"
    echo ""
    echo "Or download from:"
    echo "  https://github.com/FluidSynth/fluidsynth/wiki/SoundFont"
    exit 1
fi

# Check if FluidSynth is installed
if ! command -v fluidsynth &> /dev/null; then
    echo "Error: FluidSynth not installed"
    echo ""
    echo "Install with:"
    echo "  sudo apt install fluidsynth"
    exit 1
fi

# Check if FluidSynth is already running
if pgrep -x "fluidsynth" > /dev/null; then
    echo "Warning: FluidSynth is already running"
    echo ""
    echo "Kill existing FluidSynth processes:"
    echo "  pkill fluidsynth"
    echo ""
    read -p "Kill existing processes and continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill fluidsynth
        sleep 1
    else
        exit 1
    fi
fi

echo "Starting FluidSynth daemon..."
echo "  SoundFont: $SOUNDFONT"
echo "  Audio device: $AUDIO_DEVICE"
echo ""

# Start FluidSynth with:
# -a alsa: Use ALSA audio driver
# -m alsa_seq: Use ALSA MIDI sequencer (creates MIDI port)
# -o audio.alsa.device: Specify ALSA audio output device
# -o synth.polyphony: Limit polyphony to prevent degradation
# -o synth.reverb.active: Enable reverb effect
# -o synth.chorus.active: Enable chorus effect
# -g: Gain (volume) 0.0-1.0
fluidsynth \
  -a alsa \
  -m alsa_seq \
  -o audio.alsa.device="$AUDIO_DEVICE" \
  -o synth.polyphony=64 \
  -o synth.reverb.active=yes \
  -o synth.chorus.active=yes \
  -g 0.5 \
  "$SOUNDFONT"

# Note: FluidSynth runs in foreground by default
# Press Ctrl+C to stop

# To run in background, add & at the end and redirect output:
# fluidsynth [...options...] "$SOUNDFONT" > /tmp/fluidsynth.log 2>&1 &
# echo $! > /tmp/fluidsynth.pid
