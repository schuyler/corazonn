#!/bin/bash
# Test script for install-dependencies.sh
# Tests each function without actually installing packages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FAILURES=0
TEST_COUNT=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test helper functions
assert_equals() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    TEST_COUNT=$((TEST_COUNT + 1))
    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}[PASS]${NC} $test_name"
    else
        echo -e "${RED}[FAIL]${NC} $test_name"
        echo "  Expected: $expected"
        echo "  Actual:   $actual"
        TEST_FAILURES=$((TEST_FAILURES + 1))
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local test_name="$3"

    TEST_COUNT=$((TEST_COUNT + 1))
    if [[ "$haystack" == *"$needle"* ]]; then
        echo -e "${GREEN}[PASS]${NC} $test_name"
    else
        echo -e "${RED}[FAIL]${NC} $test_name"
        echo "  Expected to contain: $needle"
        echo "  Actual: $haystack"
        TEST_FAILURES=$((TEST_FAILURES + 1))
    fi
}

assert_exit_code() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    TEST_COUNT=$((TEST_COUNT + 1))
    if [ "$expected" -eq "$actual" ]; then
        echo -e "${GREEN}[PASS]${NC} $test_name"
    else
        echo -e "${RED}[FAIL]${NC} $test_name"
        echo "  Expected exit code: $expected"
        echo "  Actual exit code:   $actual"
        TEST_FAILURES=$((TEST_FAILURES + 1))
    fi
}

# Mock functions for testing
setup_test_env() {
    export TEST_MODE=1
    export OS_RELEASE_FILE="${SCRIPT_DIR}/test_os_release"
    export MOCK_COMMANDS=1
}

cleanup_test_env() {
    rm -f "${OS_RELEASE_FILE}"
    unset TEST_MODE
    unset OS_RELEASE_FILE
    unset MOCK_COMMANDS
}

# Source the install script in test mode
source_install_script() {
    if [ ! -f "${SCRIPT_DIR}/install-dependencies.sh" ]; then
        echo -e "${RED}ERROR:${NC} install-dependencies.sh not found"
        exit 1
    fi

    # Source the script (it should not execute main when UNIT_TEST_MODE is set)
    export UNIT_TEST_MODE=1
    source "${SCRIPT_DIR}/install-dependencies.sh"
}

echo "========================================="
echo "Testing install-dependencies.sh"
echo "========================================="
echo

# Test R41: Distribution detection
test_distribution_detection() {
    echo "--- Testing R41: Distribution Detection ---"

    # Test Ubuntu detection
    cat > "${OS_RELEASE_FILE}" << 'EOF'
ID=ubuntu
ID_LIKE=debian
EOF
    result=$(detect_distribution)
    assert_equals "ubuntu" "$result" "Detect Ubuntu"

    # Test Debian detection
    cat > "${OS_RELEASE_FILE}" << 'EOF'
ID=debian
EOF
    result=$(detect_distribution)
    assert_equals "debian" "$result" "Detect Debian"

    # Test Fedora detection
    cat > "${OS_RELEASE_FILE}" << 'EOF'
ID=fedora
EOF
    result=$(detect_distribution)
    assert_equals "fedora" "$result" "Detect Fedora"

    # Test Arch detection
    cat > "${OS_RELEASE_FILE}" << 'EOF'
ID=arch
EOF
    result=$(detect_distribution)
    assert_equals "arch" "$result" "Detect Arch"

    # Test unsupported distribution
    cat > "${OS_RELEASE_FILE}" << 'EOF'
ID=gentoo
EOF
    result=$(detect_distribution)
    assert_equals "unsupported" "$result" "Detect unsupported distribution"

    echo
}

# Test R42: Pure Data installation commands
test_pd_installation_commands() {
    echo "--- Testing R42: Pd Installation Commands ---"

    # Test Ubuntu/Debian command
    cat > "${OS_RELEASE_FILE}" << 'EOF'
ID=ubuntu
EOF
    cmd=$(get_pd_install_command "ubuntu")
    assert_contains "$cmd" "apt-get install" "Ubuntu uses apt-get"
    assert_contains "$cmd" "puredata" "Ubuntu installs puredata package"

    # Test Fedora command
    cmd=$(get_pd_install_command "fedora")
    assert_contains "$cmd" "dnf install" "Fedora uses dnf"
    assert_contains "$cmd" "puredata" "Fedora installs puredata package"

    # Test Arch command
    cmd=$(get_pd_install_command "arch")
    assert_contains "$cmd" "pacman -S" "Arch uses pacman"
    assert_contains "$cmd" "puredata" "Arch installs puredata package"

    echo
}

# Test R43: Pd verification
test_pd_verification() {
    echo "--- Testing R43: Pd Verification ---"

    # This test checks the verification logic
    # We'll mock the pd command in the install script

    # Test successful verification
    export MOCK_PD_VERSION="Pd-0.52-1"
    if verify_pd_installation > /dev/null 2>&1; then
        echo -e "${GREEN}[PASS]${NC} Verify Pd 0.52+ succeeds"
    else
        echo -e "${RED}[FAIL]${NC} Verify Pd 0.52+ succeeds"
        TEST_FAILURES=$((TEST_FAILURES + 1))
    fi
    TEST_COUNT=$((TEST_COUNT + 1))

    # Test failed verification (old version)
    export MOCK_PD_VERSION="Pd-0.48-1"
    if verify_pd_installation > /dev/null 2>&1; then
        echo -e "${RED}[FAIL]${NC} Verify Pd 0.48 fails"
        TEST_FAILURES=$((TEST_FAILURES + 1))
    else
        echo -e "${GREEN}[PASS]${NC} Verify Pd 0.48 fails"
    fi
    TEST_COUNT=$((TEST_COUNT + 1))

    # Test no pd installed
    export MOCK_PD_VERSION=""
    if verify_pd_installation > /dev/null 2>&1; then
        echo -e "${RED}[FAIL]${NC} Verify missing Pd fails"
        TEST_FAILURES=$((TEST_FAILURES + 1))
    else
        echo -e "${GREEN}[PASS]${NC} Verify missing Pd fails"
    fi
    TEST_COUNT=$((TEST_COUNT + 1))

    unset MOCK_PD_VERSION
    echo
}

# Test R44-R45: External installation and verification
test_externals() {
    echo "--- Testing R44-R45: Externals ---"

    # Test that installation instructions are printed
    output=$(print_external_installation_instructions)
    assert_contains "$output" "mrpeach" "Instructions mention mrpeach"
    assert_contains "$output" "cyclone" "Instructions mention cyclone"

    # Test external verification logic
    export MOCK_PD_EXTERNALS_OK=1
    if verify_externals > /dev/null 2>&1; then
        echo -e "${GREEN}[PASS]${NC} Verify externals succeeds when available"
    else
        echo -e "${RED}[FAIL]${NC} Verify externals succeeds when available"
        TEST_FAILURES=$((TEST_FAILURES + 1))
    fi
    TEST_COUNT=$((TEST_COUNT + 1))

    unset MOCK_PD_EXTERNALS_OK
    if verify_externals > /dev/null 2>&1; then
        echo -e "${RED}[FAIL]${NC} Verify externals fails when missing"
        TEST_FAILURES=$((TEST_FAILURES + 1))
    else
        echo -e "${GREEN}[PASS]${NC} Verify externals fails when missing"
    fi
    TEST_COUNT=$((TEST_COUNT + 1))

    echo
}

# Test R46: Troubleshooting output
test_troubleshooting() {
    echo "--- Testing R46: Troubleshooting ---"

    output=$(print_troubleshooting)
    assert_contains "$output" "TROUBLESHOOTING" "Output mentions troubleshooting"
    assert_contains "$output" "pd -version" "Output shows version command"

    echo
}

# Main test execution
main() {
    setup_test_env
    source_install_script

    test_distribution_detection
    test_pd_installation_commands
    test_pd_verification
    test_externals
    test_troubleshooting

    cleanup_test_env

    echo "========================================="
    echo "Test Results: $((TEST_COUNT - TEST_FAILURES))/$TEST_COUNT passed"
    echo "========================================="

    if [ $TEST_FAILURES -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}$TEST_FAILURES test(s) failed${NC}"
        exit 1
    fi
}

main
