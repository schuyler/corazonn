#!/bin/bash
# Integration test for install-dependencies.sh
# Tests the complete workflow without actually installing packages

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_PASSED=0
TEST_FAILED=0

echo "========================================="
echo "Integration Test: install-dependencies.sh"
echo "========================================="
echo

# Test 1: Dry-run mode completes successfully
echo "Test 1: Dry-run mode (TEST_MODE=1)"
echo "-----------------------------------"
if (cd "$SCRIPT_DIR" && TEST_MODE=1 ./install-dependencies.sh > /tmp/test_output.log 2>&1); then
    echo "[PASS] Script completed with exit code 0"
    TEST_PASSED=$((TEST_PASSED + 1))
else
    echo "[FAIL] Script failed with exit code $?"
    cat /tmp/test_output.log
    TEST_FAILED=$((TEST_FAILED + 1))
fi
echo

# Test 2: Output contains expected messages
echo "Test 2: Output validation"
echo "-------------------------"
output=$(cat /tmp/test_output.log)

checks=(
    "Detected distribution"
    "TEST_MODE: Would run"
    "TEST_MODE: Simulating"
    "Installing Pure Data Externals"
    "All dependencies verified successfully"
)

for check in "${checks[@]}"; do
    if echo "$output" | grep -q "$check"; then
        echo "[PASS] Output contains: $check"
        TEST_PASSED=$((TEST_PASSED + 1))
    else
        echo "[FAIL] Output missing: $check"
        TEST_FAILED=$((TEST_FAILED + 1))
    fi
done
echo

# Test 3: No actual commands executed
echo "Test 3: Safety check (no real installation)"
echo "--------------------------------------------"
if echo "$output" | grep -q "TEST_MODE: Would run.*apt-get"; then
    echo "[PASS] No actual apt-get command executed (TEST_MODE active)"
    TEST_PASSED=$((TEST_PASSED + 1))
else
    echo "[FAIL] Real commands may have been executed (missing TEST_MODE indicator)"
    TEST_FAILED=$((TEST_FAILED + 1))
fi
echo

# Test 4: Unit tests pass
echo "Test 4: Unit test suite"
echo "-----------------------"
if (cd "$SCRIPT_DIR" && ./test-install-dependencies.sh > /tmp/unit_test.log 2>&1); then
    echo "[PASS] All unit tests passed"
    TEST_PASSED=$((TEST_PASSED + 1))
else
    echo "[FAIL] Unit tests failed"
    cat /tmp/unit_test.log
    TEST_FAILED=$((TEST_FAILED + 1))
fi
echo

# Test 5: Script handles unsupported distro
echo "Test 5: Unsupported distribution handling"
echo "------------------------------------------"
OS_RELEASE_FILE="/tmp/test_unsupported_os"
cat > "$OS_RELEASE_FILE" << 'EOF'
ID=gentoo
NAME="Gentoo"
EOF

if (cd "$SCRIPT_DIR" && OS_RELEASE_FILE="$OS_RELEASE_FILE" ./install-dependencies.sh > /tmp/unsupported.log 2>&1); then
    echo "[FAIL] Should have failed for unsupported distro"
    TEST_FAILED=$((TEST_FAILED + 1))
else
    if grep -q "Unsupported Linux distribution" /tmp/unsupported.log; then
        echo "[PASS] Correctly rejected unsupported distribution"
        TEST_PASSED=$((TEST_PASSED + 1))
    else
        echo "[FAIL] Failed for wrong reason"
        cat /tmp/unsupported.log
        TEST_FAILED=$((TEST_FAILED + 1))
    fi
fi
rm -f "$OS_RELEASE_FILE"
echo

# Summary
echo "========================================="
echo "Integration Test Results"
echo "========================================="
echo "Passed: $TEST_PASSED"
echo "Failed: $TEST_FAILED"
echo

if [ $TEST_FAILED -eq 0 ]; then
    echo "All integration tests passed!"
    exit 0
else
    echo "Some integration tests failed"
    exit 1
fi
