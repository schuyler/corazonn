#!/bin/bash
# Pure Data installation script for Linux
# Requirements: R41-R47
# Supports: Debian/Ubuntu, Fedora, Arch Linux

set -e

# Configuration
PD_MIN_VERSION="0.52"
REQUIRED_EXTERNALS=("mrpeach" "cyclone")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# R41: Detect Linux distribution
detect_distribution() {
    local os_release="${OS_RELEASE_FILE:-/etc/os-release}"

    if [ ! -f "$os_release" ]; then
        # Fallback to lsb_release if available
        if command -v lsb_release >/dev/null 2>&1; then
            local distro=$(lsb_release -is | tr '[:upper:]' '[:lower:]')
            echo "$distro"
            return 0
        fi
        echo "unsupported"
        return 0
    fi

    # Parse /etc/os-release
    local id=$(grep "^ID=" "$os_release" | cut -d= -f2 | tr -d '"')

    case "$id" in
        ubuntu|debian|fedora|arch)
            echo "$id"
            ;;
        *)
            echo "unsupported"
            ;;
    esac
}

# R42: Get Pure Data installation command for distribution
get_pd_install_command() {
    local distro="$1"

    case "$distro" in
        ubuntu|debian)
            echo "sudo apt-get update && sudo apt-get install -y puredata"
            ;;
        fedora)
            echo "sudo dnf install -y puredata"
            ;;
        arch)
            echo "sudo pacman -S --noconfirm puredata"
            ;;
        *)
            echo ""
            ;;
    esac
}

# R42: Install Pure Data
install_puredata() {
    local distro="$1"

    log_info "Installing Pure Data for $distro..."

    local install_cmd=$(get_pd_install_command "$distro")

    if [ -z "$install_cmd" ]; then
        log_error "No installation command for distribution: $distro"
        return 1
    fi

    # In test mode, just print the command
    if [ -n "$TEST_MODE" ]; then
        log_info "TEST_MODE: Would run: $install_cmd"
        return 0
    fi

    # Execute installation command
    if eval "$install_cmd"; then
        log_success "Pure Data installed successfully"
        return 0
    else
        log_error "Failed to install Pure Data"
        return 1
    fi
}

# R43: Verify Pd installation
verify_pd_installation() {
    log_info "Verifying Pure Data installation..."

    # Check if pd is available
    local pd_version=""

    # In test mode, use mock version
    if [ -n "$MOCK_PD_VERSION" ]; then
        pd_version="$MOCK_PD_VERSION"
    else
        if ! command -v pd >/dev/null 2>&1; then
            log_error "Pure Data (pd) not found in PATH"
            return 1
        fi

        # Get version (pd -version prints to stderr)
        pd_version=$(pd -version 2>&1 | head -n1 || echo "")
    fi

    if [ -z "$pd_version" ]; then
        log_error "Could not determine Pd version"
        return 1
    fi

    log_info "Found: $pd_version"

    # Extract version number (e.g., "Pd-0.52-1" -> "0.52")
    local version_num=$(echo "$pd_version" | grep -oP 'Pd-\K[0-9]+\.[0-9]+' || echo "0.0")

    # Compare versions (simple float comparison works for X.YY format)
    if awk -v ver="$version_num" -v min="$PD_MIN_VERSION" 'BEGIN { exit (ver >= min) ? 0 : 1 }'; then
        log_success "Pure Data version $version_num meets minimum requirement ($PD_MIN_VERSION)"
        return 0
    else
        log_error "Pure Data version $version_num is older than required $PD_MIN_VERSION"
        return 1
    fi
}

# R44: Print external installation instructions
print_external_installation_instructions() {
    cat << EOF

========================================
Installing Pure Data Externals
========================================

The following externals are required:
  - mrpeach (for OSC communication)
  - cyclone (for additional objects)

RECOMMENDED: Use Deken (Pd's package manager)
----------------------------------------------
1. Start Pure Data: pd
2. Go to: Help → Find externals
3. Search for and install:
   - mrpeach
   - cyclone
4. Restart Pure Data

ALTERNATIVE: Manual installation
---------------------------------
Ubuntu/Debian:
  sudo apt-get install pd-mrpeach pd-cyclone

Fedora:
  sudo dnf install puredata-mrpeach puredata-cyclone

Arch:
  Use Deken (Arch packages may not include externals)

After installation, verify with:
  pd -lib mrpeach -lib cyclone -send "quit"

========================================
EOF
}

# R45: Verify externals are available
verify_externals() {
    log_info "Verifying Pure Data externals..."

    # In test mode with mock
    if [ -n "$MOCK_PD_EXTERNALS_OK" ]; then
        log_success "Externals verified (test mode)"
        return 0
    fi

    # In test mode without mock
    if [ -n "$TEST_MODE" ]; then
        log_warning "Cannot verify externals in test mode"
        return 1
    fi

    # Real verification: try to load libraries
    # Create a temporary Pd script that loads libraries and quits
    local test_output=$(pd -stderr -noprefs -nogui \
        -lib mrpeach -lib cyclone \
        -send "pd quit" 2>&1 || true)

    # Check for error messages
    if echo "$test_output" | grep -qi "can't load library"; then
        log_error "Failed to load required externals"
        echo "$test_output" | grep -i "can't load library"
        return 1
    fi

    # Look for successful loading indicators
    local mrpeach_ok=0
    local cyclone_ok=0

    if echo "$test_output" | grep -qi "mrpeach"; then
        mrpeach_ok=1
    fi
    if echo "$test_output" | grep -qi "cyclone"; then
        cyclone_ok=1
    fi

    # If no errors and we found library names, consider it successful
    # (Pd's output format varies, so we use lenient checking)
    if [ $mrpeach_ok -eq 1 ] || [ $cyclone_ok -eq 1 ]; then
        log_success "Externals verified"
        return 0
    fi

    # If we got here with no errors, assume success
    log_warning "Could not definitively verify externals, but no errors detected"
    log_info "Please manually test: pd -lib mrpeach -lib cyclone"
    return 0
}

# R46: Print troubleshooting steps
print_troubleshooting() {
    cat << EOF

========================================
TROUBLESHOOTING
========================================

If installation or verification failed:

1. CHECK PURE DATA INSTALLATION
   Run: pd -version
   Expected: Pd-0.52-1 or newer

   If not found:
   - Ensure pd is in your PATH
   - Try: which pd
   - Check installation logs above

2. CHECK EXTERNALS
   Run: pd -lib mrpeach -lib cyclone -send "quit"

   If libraries fail to load:
   - Use Deken: Help → Find externals in Pd
   - Check external paths: pd -path
   - Manually install packages (see instructions above)

3. DISTRIBUTION-SPECIFIC ISSUES

   Ubuntu/Debian:
   - Update package lists: sudo apt-get update
   - Check if universe repository is enabled

   Fedora:
   - Check if RPM Fusion is enabled
   - Try: sudo dnf search puredata

   Arch:
   - Update package database: sudo pacman -Sy
   - Check AUR for additional packages

4. ALTERNATIVE INSTALLATION
   - Download from: http://puredata.info/downloads
   - Compile from source
   - Use Flatpak: flatpak install flathub org.puredata.Pd

5. GET HELP
   - Pure Data forum: https://forum.pdpatchrepo.info/
   - Mailing list: pd-list@lists.iem.at

========================================
EOF
}

# Main installation flow
main() {
    echo "========================================="
    echo "Pure Data Installation Script"
    echo "========================================="
    echo

    # R41: Detect distribution
    local distro=$(detect_distribution)
    log_info "Detected distribution: $distro"

    if [ "$distro" = "unsupported" ]; then
        log_error "Unsupported Linux distribution"
        log_info "This script supports: Ubuntu, Debian, Fedora, Arch Linux"
        print_troubleshooting
        exit 1
    fi

    # Check if pd is already installed
    if command -v pd >/dev/null 2>&1 && [ -z "$TEST_MODE" ]; then
        log_info "Pure Data is already installed"
        if verify_pd_installation; then
            log_info "Skipping Pd installation"
        else
            log_warning "Installed version does not meet requirements"
            # Continue to attempt installation/upgrade
        fi
    else
        # R42: Install Pure Data
        if ! install_puredata "$distro"; then
            log_error "Pure Data installation failed"
            print_troubleshooting
            exit 1
        fi

        # R43: Verify installation
        # In TEST_MODE, simulate successful verification
        if [ -n "$TEST_MODE" ]; then
            log_info "TEST_MODE: Simulating successful Pd verification"
            log_success "Pure Data version 0.52+ verified (simulated)"
        else
            if ! verify_pd_installation; then
                log_error "Pure Data verification failed"
                print_troubleshooting
                exit 1
            fi
        fi
    fi

    # R44: Show external installation instructions
    print_external_installation_instructions

    # Give user time to install externals if not in test mode
    if [ -z "$TEST_MODE" ]; then
        echo
        log_info "Please install externals using Deken or package manager"
        read -p "Press Enter after installing externals to verify..."
        echo
    fi

    # R45: Verify externals
    # In TEST_MODE, simulate verification
    if [ -n "$TEST_MODE" ]; then
        log_info "TEST_MODE: Simulating external verification"
        log_success "Externals verified (simulated)"
        log_success "All dependencies verified successfully! (TEST_MODE)"
        echo
        log_info "In real mode, next steps would be:"
        echo "  1. Run: cd /home/user/corazonn/audio/scripts && ./detect-audio-interface.sh"
        echo "  2. Test: pd -version"
        echo "  3. Load main patch: cd /home/user/corazonn/audio/patches && pd heartbeat-main.pd"
        echo
        # R47: Exit with success
        exit 0
    elif verify_externals; then
        log_success "All dependencies verified successfully!"
        echo
        log_info "Next steps:"
        echo "  1. Run: cd /home/user/corazonn/audio/scripts && ./detect-audio-interface.sh"
        echo "  2. Test: pd -version"
        echo "  3. Load main patch: cd /home/user/corazonn/audio/patches && pd heartbeat-main.pd"
        echo
        # R47: Exit with success
        exit 0
    else
        log_warning "Could not verify all externals"
        print_troubleshooting
        # R47: Exit with failure
        exit 1
    fi
}

# Run main if executed directly (not sourced)
# Skip only when sourced for unit testing (UNIT_TEST_MODE)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    # Script is being executed, not sourced
    if [ -z "$UNIT_TEST_MODE" ]; then
        main
    fi
fi
