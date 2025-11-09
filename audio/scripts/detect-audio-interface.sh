#!/bin/bash
# Detect and configure ALSA audio interface for Pure Data
# Part of Heartbeat Installation - Audio Pipeline Phase 1
#
# Requirements: R48-R54
# - R48: Run aplay -l and parse output
# - R49: Identify USB audio interfaces by card name
# - R50: Generate ~/.asoundrc with detected card number
# - R51: Test audio output with speaker-test
# - R52: If no USB interface, offer to configure built-in audio
# - R53: Backup existing ~/.asoundrc before overwriting
# - R54: Print final configuration summary

set -uo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running in dry-run mode
DRY_RUN="${DRY_RUN:-0}"

# Print functions (all output to stderr to avoid interfering with return values)
info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if aplay is available
check_dependencies() {
    if ! command -v aplay &> /dev/null; then
        error "aplay command not found"
        echo "" >&2
        echo "Please install alsa-utils:" >&2
        echo "  Debian/Ubuntu: sudo apt-get install alsa-utils" >&2
        echo "  Fedora: sudo dnf install alsa-utils" >&2
        echo "  Arch: sudo pacman -S alsa-utils" >&2
        exit 1
    fi

    if ! command -v speaker-test &> /dev/null; then
        warning "speaker-test command not found (audio testing will be skipped)"
    fi
}

# R48: Run aplay -l and parse output
# R49: Identify USB audio interfaces by card name
detect_usb_audio() {
    local aplay_output
    local card_num=""
    local card_name=""
    local device_num="0"

    info "Detecting audio interfaces..."
    aplay_output=$(aplay -l 2>/dev/null)

    if [[ -z "$aplay_output" ]]; then
        error "No audio devices found"
        return 1
    fi

    # Display available devices
    echo "" >&2
    echo "Available audio devices:" >&2
    echo "----------------------------------------" >&2
    echo "$aplay_output" >&2
    echo "----------------------------------------" >&2
    echo "" >&2

    # Search for USB audio interfaces using keywords
    # Priority: USB, Scarlett, Focusrite, External
    while IFS= read -r line; do
        if [[ "$line" =~ ^card\ ([0-9]+):\ [^[]+\[([^]]+)\] ]]; then
            local num="${BASH_REMATCH[1]}"
            local name="${BASH_REMATCH[2]}"

            # Check for USB audio keywords
            if [[ "$name" =~ (USB|Scarlett|Focusrite|External) ]]; then
                card_num="$num"
                card_name="$name"
                success "Detected USB audio interface: $card_name (card $card_num)"
                break  # Use first match
            fi
        fi
    done <<< "$aplay_output"

    # R52: If no USB interface, offer to configure built-in audio
    if [[ -z "$card_num" ]]; then
        warning "No USB audio interface detected"
        echo "" >&2
        echo "Would you like to configure built-in audio instead?" >&2
        echo "This is acceptable for testing, but production deployment" >&2
        echo "should use a dedicated USB audio interface." >&2
        echo "" >&2

        # Extract first available card
        if [[ "$aplay_output" =~ ^card\ ([0-9]+):\ [^[]+\[([^]]+)\] ]]; then
            local builtin_num="${BASH_REMATCH[1]}"
            local builtin_name="${BASH_REMATCH[2]}"

            echo "Available: card $builtin_num - $builtin_name" >&2
            echo "" >&2
            read -p "Configure card $builtin_num? [y/N] " -n 1 -r
            echo "" >&2

            if [[ $REPLY =~ ^[Yy]$ ]]; then
                card_num="$builtin_num"
                card_name="$builtin_name"
                info "Using built-in audio: $builtin_name (card $builtin_num)"
            else
                error "No audio interface configured"
                return 1
            fi
        else
            error "Could not parse audio device information"
            return 1
        fi
    fi

    echo "$card_num|$card_name|$device_num"
}

# R53: Backup existing ~/.asoundrc before overwriting
backup_asoundrc() {
    local asoundrc="$HOME/.asoundrc"
    local backup="$HOME/.asoundrc.backup"

    if [[ -f "$asoundrc" ]]; then
        info "Existing .asoundrc found"

        if [[ "$DRY_RUN" == "1" ]]; then
            info "[DRY RUN] Would backup: $asoundrc -> $backup"
        else
            cp "$asoundrc" "$backup"
            success "Backed up to: $backup"
        fi
    fi
}

# R50: Generate ~/.asoundrc with detected card number
generate_asoundrc() {
    local card_num="$1"
    local asoundrc="$HOME/.asoundrc"

    local config="pcm.!default {
    type hw
    card $card_num
    device 0
}

ctl.!default {
    type hw
    card $card_num
}
"

    if [[ "$DRY_RUN" == "1" ]]; then
        info "[DRY RUN] Would write to: $asoundrc"
        echo "----------------------------------------" >&2
        echo "$config" >&2
        echo "----------------------------------------" >&2
    else
        echo "$config" > "$asoundrc"
        success "Generated: $asoundrc"
    fi
}

# R51: Test audio output with speaker-test
test_audio_output() {
    local card_num="$1"

    if ! command -v speaker-test &> /dev/null; then
        warning "speaker-test not available, skipping audio test"
        return 0
    fi

    echo "" >&2
    info "Testing audio output..."
    echo "You should hear a test tone from both speakers/channels." >&2
    echo "This will run for 1 second." >&2
    echo "" >&2
    read -p "Press Enter to start test (or Ctrl+C to skip)..."

    if [[ "$DRY_RUN" == "1" ]]; then
        info "[DRY RUN] Would run: speaker-test -t sine -f 440 -c 2 -l 1"
    else
        # Run speaker-test: 440Hz sine wave, 2 channels, 1 loop
        if speaker-test -t sine -f 440 -c 2 -l 1 -D hw:$card_num,0 2>&1 | grep -q "Time per period"; then
            success "Audio test completed"
        else
            warning "Audio test encountered issues (this may be normal)"
        fi
    fi
}

# R54: Print final configuration summary
print_summary() {
    local card_num="$1"
    local card_name="$2"

    echo "" >&2
    echo "========================================" >&2
    echo "Audio Interface Configuration Summary" >&2
    echo "========================================" >&2
    echo "" >&2
    echo "Card Number:  $card_num" >&2
    echo "Card Name:    $card_name" >&2
    echo "Device:       hw:$card_num,0" >&2
    echo "Config File:  $HOME/.asoundrc" >&2
    echo "" >&2
    echo "Next Steps:" >&2
    echo "  1. Start Pure Data and check audio settings" >&2
    echo "  2. Run: pd -audiobuf 64 -audiodev 1" >&2
    echo "  3. In Pd: Media → Audio Settings" >&2
    echo "     - Set device to: hw:$card_num,0" >&2
    echo "     - Sample rate: 48000 Hz" >&2
    echo "     - Channels: 2 (stereo)" >&2
    echo "" >&2
    success "Configuration complete!"
}

# Main execution
main() {
    echo "========================================" >&2
    echo "ALSA Audio Interface Detection" >&2
    echo "========================================" >&2
    echo "" >&2

    if [[ "$DRY_RUN" == "1" ]]; then
        warning "Running in DRY RUN mode (no files will be modified)"
        echo "" >&2
    fi

    # Check dependencies
    check_dependencies

    # Detect audio interface
    local detection_result
    detection_result=$(detect_usb_audio)

    if [[ $? -ne 0 ]] || [[ -z "$detection_result" ]]; then
        error "Audio detection failed"
        exit 1
    fi

    # Parse detection result
    local card_num=$(echo "$detection_result" | cut -d'|' -f1)
    local card_name=$(echo "$detection_result" | cut -d'|' -f2)
    local device_num=$(echo "$detection_result" | cut -d'|' -f3)

    # Backup existing configuration
    backup_asoundrc

    # Generate new configuration
    generate_asoundrc "$card_num"

    # Test audio output
    test_audio_output "$card_num"

    # Print summary
    print_summary "$card_num" "$card_name"
}

# Run main function
main "$@"
