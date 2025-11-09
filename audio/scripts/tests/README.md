# Test Suite for detect-audio-interface.sh

This directory contains TDD tests for the audio interface detection script.

## Test Files

### test-detect-audio-interface.sh
Unit tests for the parsing logic. Tests the core `parse_aplay_output` function with various fixture files.

**Run:**
```bash
./test-detect-audio-interface.sh
```

**Coverage:**
- USB audio interface detection (Scarlett keyword)
- Focusrite keyword detection
- Generic USB keyword detection
- External keyword detection
- Built-in audio fallback (no USB detected)

### test-detect-integration.sh
Integration tests for the full script. Uses mocked `aplay` commands and temporary HOME directories.

**Run:**
```bash
./test-detect-integration.sh
```

**Coverage:**
- End-to-end USB detection with all fixture types
- Dry-run mode safety (no files created)
- Backup of existing .asoundrc files
- Correct .asoundrc generation

## Test Fixtures

Located in `fixtures/` directory:

- `aplay-usb-scarlett.txt` - System with Scarlett 2i2 USB on card 1
- `aplay-usb-focusrite.txt` - System with Focusrite Scarlett Solo on card 2
- `aplay-generic-usb.txt` - System with generic USB audio device on card 1
- `aplay-external.txt` - System with External sound card on card 3
- `aplay-builtin-only.txt` - System with only built-in audio (no USB)

## Running All Tests

```bash
cd /home/user/corazonn/audio/scripts/tests
./test-detect-audio-interface.sh && ./test-detect-integration.sh
```

## Test-Driven Development Approach

1. Created test fixtures with sample `aplay -l` output
2. Wrote unit tests for parsing logic
3. Implemented script with verified parsing
4. Created integration tests for full script behavior
5. All tests passing before deployment

## Test Results

**Unit Tests:** 5/5 passing
**Integration Tests:** 6/6 passing

All requirements R48-R54 verified through automated tests.
