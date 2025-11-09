# install-dependencies.sh - Pure Data Installation Script

Test-driven implementation of Pure Data installation for Linux systems.

## Requirements Coverage

This script implements Technical Reference Document (TRD) requirements R41-R47:

- **R41**: Detect Linux distribution (Debian/Ubuntu/Fedora/Arch)
- **R42**: Install Pure Data via package manager
- **R43**: Verify Pd installation (version 0.52+)
- **R44**: Install mrpeach and cyclone externals
- **R45**: Verify externals available
- **R46**: Print troubleshooting steps on failure
- **R47**: Exit with code 0 on success, 1 on failure

## Usage

### Normal Installation

```bash
cd /home/user/corazonn/audio/scripts
./install-dependencies.sh
```

The script will:
1. Auto-detect your Linux distribution
2. Install Pure Data using the appropriate package manager
3. Verify Pd version is 0.52+
4. Display instructions for installing externals
5. Wait for you to install externals (using Deken or package manager)
6. Verify externals are available
7. Show next steps on success

### Dry-Run Mode (No Installation)

To see what the script would do without actually installing:

```bash
export TEST_MODE=1
./install-dependencies.sh
```

Output shows:
- Detected distribution
- Commands that would be executed
- Simulated verification results

This is useful for:
- Understanding what the script does
- Testing on systems where you don't have sudo
- Verifying the script logic before actual installation

## Testing

### Run Unit Tests

```bash
cd /home/user/corazonn/audio/scripts
./test-install-dependencies.sh
```

Tests verify:
- Distribution detection for Ubuntu, Debian, Fedora, Arch
- Correct package manager commands for each distribution
- Version verification logic (accepts 0.52+, rejects older)
- External installation instructions
- Troubleshooting output

Expected output:
```
=========================================
Testing install-dependencies.sh
=========================================

--- Testing R41: Distribution Detection ---
[PASS] Detect Ubuntu
[PASS] Detect Debian
[PASS] Detect Fedora
[PASS] Detect Arch
[PASS] Detect unsupported distribution

... (more tests)

=========================================
Test Results: 20/20 passed
=========================================
All tests passed!
```

### Test Coverage

The test suite covers:
- **5 tests** for distribution detection (R41)
- **6 tests** for installation commands (R42)
- **3 tests** for Pd verification (R43)
- **4 tests** for externals (R44-R45)
- **2 tests** for troubleshooting output (R46)

Exit codes (R47) are tested implicitly throughout.

## Supported Distributions

| Distribution | Package Manager | Command |
|--------------|----------------|---------|
| Ubuntu       | apt-get        | `sudo apt-get update && sudo apt-get install -y puredata` |
| Debian       | apt-get        | `sudo apt-get update && sudo apt-get install -y puredata` |
| Fedora       | dnf            | `sudo dnf install -y puredata` |
| Arch Linux   | pacman         | `sudo pacman -S --noconfirm puredata` |

## External Installation

The script provides instructions for installing required externals:

### Recommended: Deken (Pd's Package Manager)

1. Start Pure Data: `pd`
2. Go to: Help → Find externals
3. Search for and install:
   - `mrpeach` (for OSC communication)
   - `cyclone` (for additional objects)
4. Restart Pure Data

### Alternative: System Package Manager

**Ubuntu/Debian:**
```bash
sudo apt-get install pd-mrpeach pd-cyclone
```

**Fedora:**
```bash
sudo dnf install puredata-mrpeach puredata-cyclone
```

**Arch:**
Use Deken (AUR packages may not include externals)

## Verification

The script verifies:

1. **Pure Data version**: Checks `pd -version` outputs 0.52 or newer
2. **Externals**: Attempts to load libraries with `pd -lib mrpeach -lib cyclone`

Manual verification:
```bash
# Check Pd version
pd -version
# Should output: Pd-0.52-1 or newer

# Check externals
pd -lib mrpeach -lib cyclone -send "quit"
# Should load without "can't load library" errors
```

## Troubleshooting

If installation fails, the script prints detailed troubleshooting steps covering:

1. Pd installation verification
2. External loading issues
3. Distribution-specific problems
4. Alternative installation methods
5. Community support resources

View troubleshooting output:
```bash
# In the install script, it's shown on failure
# Or run manually:
./install-dependencies.sh 2>&1 | grep -A 50 "TROUBLESHOOTING"
```

## Implementation Details

### Test-Driven Development

This script was implemented using TDD:

1. **Tests written first** - `test-install-dependencies.sh` defines expected behavior
2. **Implementation to pass tests** - `install-dependencies.sh` implements functions
3. **Verification** - Tests confirm all requirements met

### Script Structure

```bash
install-dependencies.sh
├── detect_distribution()              # R41
├── get_pd_install_command()           # R42
├── install_puredata()                 # R42
├── verify_pd_installation()           # R43
├── print_external_installation_instructions()  # R44
├── verify_externals()                 # R45
├── print_troubleshooting()            # R46
└── main()                             # R47 (exit codes)
```

### Test Modes

- **UNIT_TEST_MODE**: Set when sourcing for unit tests (prevents main() execution)
- **TEST_MODE**: Dry-run mode (simulates installation without executing commands)

### Mock Environment

For testing, the script supports:
- `OS_RELEASE_FILE`: Override `/etc/os-release` path
- `MOCK_PD_VERSION`: Simulate `pd -version` output
- `MOCK_PD_EXTERNALS_OK`: Simulate successful external verification

## Exit Codes

- **0**: Success - Pd and externals installed and verified
- **1**: Failure - Installation failed, verification failed, or unsupported distribution

## Next Steps

After successful installation:

1. **Configure audio interface:**
   ```bash
   cd /home/user/corazonn/audio/scripts
   ./detect-audio-interface.sh
   ```

2. **Test Pure Data:**
   ```bash
   pd -version
   ```

3. **Load main patch:**
   ```bash
   cd /home/user/corazonn/audio/patches
   pd heartbeat-main.pd
   ```

## Development

### Adding Support for New Distributions

1. Update `detect_distribution()` to recognize new ID
2. Add case in `get_pd_install_command()` with package manager command
3. Add test case in `test_distribution_detection()`
4. Add test case in `test_pd_installation_commands()`
5. Run tests to verify

### Modifying Version Requirements

To change minimum Pd version:
1. Update `PD_MIN_VERSION` variable in `install-dependencies.sh`
2. Update test cases in `test_pd_verification()`
3. Update documentation

## Files

- `install-dependencies.sh` - Main installation script (380 lines)
- `test-install-dependencies.sh` - Unit test suite (260 lines)
- `README-install-dependencies.md` - This documentation

## License

Part of the Corazonn heartbeat installation project.
