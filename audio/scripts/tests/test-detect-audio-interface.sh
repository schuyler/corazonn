#!/bin/bash
# Test harness for detect-audio-interface.sh parsing logic
# Tests parsing of aplay -l output without modifying system configuration

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="${SCRIPT_DIR}/fixtures"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test result reporting
pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo -e "  Expected: $2"
    echo -e "  Got: $3"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Extract the parsing function we'll test
# This simulates the core logic of detect-audio-interface.sh
parse_aplay_output() {
    local aplay_output="$1"
    local card_num=""
    local card_name=""

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
                break  # Use first match
            fi
        fi
    done <<< "$aplay_output"

    echo "${card_num}|${card_name}"
}

# Test 1: Detect Scarlett USB interface
test_scarlett_usb() {
    info "Test 1: Detect Scarlett USB interface"
    local fixture="${FIXTURES_DIR}/aplay-usb-scarlett.txt"
    local output=$(cat "$fixture")
    local result=$(parse_aplay_output "$output")
    local card_num=$(echo "$result" | cut -d'|' -f1)
    local card_name=$(echo "$result" | cut -d'|' -f2)

    if [[ "$card_num" == "1" ]] && [[ "$card_name" == "Scarlett 2i2 USB" ]]; then
        pass "Detected Scarlett USB on card 1"
    else
        fail "Scarlett USB detection" "card=1, name=Scarlett 2i2 USB" "card=$card_num, name=$card_name"
    fi
}

# Test 2: Detect Focusrite interface
test_focusrite() {
    info "Test 2: Detect Focusrite interface"
    local fixture="${FIXTURES_DIR}/aplay-usb-focusrite.txt"
    local output=$(cat "$fixture")
    local result=$(parse_aplay_output "$output")
    local card_num=$(echo "$result" | cut -d'|' -f1)
    local card_name=$(echo "$result" | cut -d'|' -f2)

    if [[ "$card_num" == "2" ]] && [[ "$card_name" == "Focusrite Scarlett Solo" ]]; then
        pass "Detected Focusrite on card 2"
    else
        fail "Focusrite detection" "card=2, name=Focusrite Scarlett Solo" "card=$card_num, name=$card_name"
    fi
}

# Test 3: Detect generic USB audio device
test_generic_usb() {
    info "Test 3: Detect generic USB audio device"
    local fixture="${FIXTURES_DIR}/aplay-generic-usb.txt"
    local output=$(cat "$fixture")
    local result=$(parse_aplay_output "$output")
    local card_num=$(echo "$result" | cut -d'|' -f1)
    local card_name=$(echo "$result" | cut -d'|' -f2)

    if [[ "$card_num" == "1" ]] && [[ "$card_name" == "USB Audio Device" ]]; then
        pass "Detected generic USB device on card 1"
    else
        fail "Generic USB detection" "card=1, name=USB Audio Device" "card=$card_num, name=$card_name"
    fi
}

# Test 4: Detect External keyword
test_external() {
    info "Test 4: Detect External keyword"
    local fixture="${FIXTURES_DIR}/aplay-external.txt"
    local output=$(cat "$fixture")
    local result=$(parse_aplay_output "$output")
    local card_num=$(echo "$result" | cut -d'|' -f1)
    local card_name=$(echo "$result" | cut -d'|' -f2)

    if [[ "$card_num" == "3" ]] && [[ "$card_name" == "External Sound Card" ]]; then
        pass "Detected External device on card 3"
    else
        fail "External device detection" "card=3, name=External Sound Card" "card=$card_num, name=$card_name"
    fi
}

# Test 5: No USB interface found (built-in only)
test_builtin_only() {
    info "Test 5: No USB interface found (built-in only)"
    local fixture="${FIXTURES_DIR}/aplay-builtin-only.txt"
    local output=$(cat "$fixture")
    local result=$(parse_aplay_output "$output")
    local card_num=$(echo "$result" | cut -d'|' -f1)

    if [[ -z "$card_num" ]]; then
        pass "Correctly identified no USB interface"
    else
        fail "Built-in only detection" "empty card_num" "card=$card_num"
    fi
}

# Run all tests
echo "========================================="
echo "Testing detect-audio-interface.sh parsing"
echo "========================================="
echo ""

test_scarlett_usb
test_focusrite
test_generic_usb
test_external
test_builtin_only

echo ""
echo "========================================="
echo "Test Results"
echo "========================================="
echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Failed:${NC} $TESTS_FAILED"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
