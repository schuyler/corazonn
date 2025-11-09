#!/bin/bash
# Integration tests for detect-audio-interface.sh
# Tests the full script with mocked aplay command

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="${SCRIPT_DIR}/fixtures"
MAIN_SCRIPT="${SCRIPT_DIR}/../detect-audio-interface.sh"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Test the script with a mocked aplay command
test_with_fixture() {
    local fixture_name="$1"
    local expected_card="$2"
    local expected_name="$3"

    info "Testing with fixture: $fixture_name"

    # Create a temporary mock aplay script
    local mock_dir=$(mktemp -d)
    local mock_aplay="$mock_dir/aplay"

    cat > "$mock_aplay" << EOF
#!/bin/bash
if [[ "\$1" == "-l" ]]; then
    cat "${FIXTURES_DIR}/${fixture_name}.txt"
else
    exit 1
fi
EOF
    chmod +x "$mock_aplay"

    # Create temporary HOME for this test
    local temp_home=$(mktemp -d)

    # Run the script with mocked aplay and DRY_RUN mode
    local output
    output=$(PATH="$mock_dir:$PATH" HOME="$temp_home" DRY_RUN=1 bash "$MAIN_SCRIPT" 2>&1 <<< "")

    # Check if the expected card was detected
    if echo "$output" | grep -q "Card Number:  $expected_card" && \
       echo "$output" | grep -q "Card Name:    $expected_name"; then
        pass "Detected correct card: $expected_card ($expected_name)"
    else
        fail "Card detection for $fixture_name"
        echo "Expected: card=$expected_card, name=$expected_name"
        echo "Output:"
        echo "$output"
    fi

    # Cleanup
    rm -rf "$mock_dir" "$temp_home"
}

# Test 1: USB Scarlett detection
test_usb_scarlett() {
    test_with_fixture "aplay-usb-scarlett" "1" "Scarlett 2i2 USB"
}

# Test 2: Focusrite detection
test_focusrite() {
    test_with_fixture "aplay-usb-focusrite" "2" "Focusrite Scarlett Solo"
}

# Test 3: Generic USB detection
test_generic_usb() {
    test_with_fixture "aplay-generic-usb" "1" "USB Audio Device"
}

# Test 4: External device detection
test_external() {
    test_with_fixture "aplay-external" "3" "External Sound Card"
}

# Test 5: Dry-run mode doesn't create files
test_dry_run_safety() {
    info "Testing dry-run safety (no files created)"

    local temp_home=$(mktemp -d)
    local mock_dir=$(mktemp -d)
    local mock_aplay="$mock_dir/aplay"

    cat > "$mock_aplay" << 'EOF'
#!/bin/bash
cat << 'APLAY_OUTPUT'
**** List of PLAYBACK Hardware Devices ****
card 1: USB [Scarlett 2i2 USB], device 0: USB Audio [USB Audio]
APLAY_OUTPUT
EOF
    chmod +x "$mock_aplay"

    # Run in dry-run mode
    PATH="$mock_dir:$PATH" HOME="$temp_home" DRY_RUN=1 bash "$MAIN_SCRIPT" 2>&1 <<< "" > /dev/null

    # Check that no .asoundrc was created
    if [[ ! -f "$temp_home/.asoundrc" ]]; then
        pass "Dry-run mode does not create .asoundrc"
    else
        fail "Dry-run mode created .asoundrc file"
    fi

    rm -rf "$mock_dir" "$temp_home"
}

# Test 6: Backup existing .asoundrc
test_backup_existing() {
    info "Testing backup of existing .asoundrc"

    local temp_home=$(mktemp -d)
    local mock_dir=$(mktemp -d)
    local mock_aplay="$mock_dir/aplay"

    # Create existing .asoundrc
    echo "existing config" > "$temp_home/.asoundrc"

    cat > "$mock_aplay" << 'EOF'
#!/bin/bash
cat << 'APLAY_OUTPUT'
**** List of PLAYBACK Hardware Devices ****
card 1: USB [Scarlett 2i2 USB], device 0: USB Audio [USB Audio]
APLAY_OUTPUT
EOF
    chmod +x "$mock_aplay"

    # Run script (not dry-run, but with mocked environment)
    PATH="$mock_dir:$PATH" HOME="$temp_home" bash "$MAIN_SCRIPT" 2>&1 <<< $'\n' > /dev/null

    # Check that backup was created
    if [[ -f "$temp_home/.asoundrc.backup" ]] && \
       grep -q "existing config" "$temp_home/.asoundrc.backup"; then
        pass "Existing .asoundrc backed up correctly"
    else
        fail "Backup not created or incorrect"
    fi

    rm -rf "$mock_dir" "$temp_home"
}

# Run all tests
echo "========================================="
echo "Integration tests for detect-audio-interface.sh"
echo "========================================="
echo ""

test_usb_scarlett
test_focusrite
test_generic_usb
test_external
test_dry_run_safety
test_backup_existing

echo ""
echo "========================================="
echo "Test Results"
echo "========================================="
echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Failed:${NC} $TESTS_FAILED"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}All integration tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
