"""
Tests for Kasa Bulb Emulator

Validates HSV state management, protocol encryption, and statistics tracking.
"""

import pytest
import json
from amor.simulator.kasa_emulator import KasaBulbEmulator, MultiBulbEmulator


class TestKasaBulbEmulator:
    """Test KasaBulbEmulator functionality."""

    def test_initialization(self):
        """Test emulator initializes with correct defaults."""
        emulator = KasaBulbEmulator()

        assert emulator.ip == "127.0.0.1"
        assert emulator.port == 9999
        assert emulator.name == "Emulated Bulb"
        assert emulator.is_on == True
        assert emulator.hue == 120  # Green
        assert emulator.saturation == 75
        assert emulator.brightness == 40
        assert emulator.command_count == 0
        assert emulator.state_changes == 0
        assert emulator.running == False

    def test_custom_initialization(self):
        """Test emulator with custom parameters."""
        emulator = KasaBulbEmulator(
            ip="192.168.1.100",
            port=8888,
            name="Test Bulb"
        )

        assert emulator.ip == "192.168.1.100"
        assert emulator.port == 8888
        assert emulator.name == "Test Bulb"

    def test_set_hsv(self):
        """Test HSV state changes."""
        emulator = KasaBulbEmulator()

        # Initial state
        assert emulator.hue == 120
        assert emulator.saturation == 75
        assert emulator.brightness == 40

        # Change HSV
        emulator.set_hsv(hue=0, saturation=100, brightness=80)

        assert emulator.hue == 0
        assert emulator.saturation == 100
        assert emulator.brightness == 80
        assert emulator.is_on == True
        assert emulator.state_changes == 1

    def test_hsv_clamping(self):
        """Test HSV values are clamped to valid ranges."""
        emulator = KasaBulbEmulator()

        # Hue above max (360)
        emulator.set_hsv(hue=400, saturation=50, brightness=50)
        assert emulator.hue == 360

        # Hue below min (0)
        emulator.set_hsv(hue=-10, saturation=50, brightness=50)
        assert emulator.hue == 0

        # Saturation above max (100)
        emulator.set_hsv(hue=180, saturation=150, brightness=50)
        assert emulator.saturation == 100

        # Brightness below min (0)
        emulator.set_hsv(hue=180, saturation=50, brightness=-20)
        assert emulator.brightness == 0

    def test_state_change_tracking(self):
        """Test state_changes counter increments on HSV changes."""
        emulator = KasaBulbEmulator()

        assert emulator.state_changes == 0

        # First change
        emulator.set_hsv(100, 80, 60)
        assert emulator.state_changes == 1

        # Second change
        emulator.set_hsv(200, 90, 70)
        assert emulator.state_changes == 2

        # No change (same values)
        emulator.set_hsv(200, 90, 70)
        assert emulator.state_changes == 2  # Should not increment

    def test_get_state(self):
        """Test get_state returns complete bulb state."""
        emulator = KasaBulbEmulator(name="Test Bulb")
        emulator.set_hsv(240, 80, 60)
        emulator.command_count = 5

        state = emulator.get_state()

        assert state["name"] == "Test Bulb"
        assert state["is_on"] == True
        assert state["hue"] == 240
        assert state["saturation"] == 80
        assert state["brightness"] == 60
        assert state["command_count"] == 5
        assert state["state_changes"] == 1

    def test_encryption_decryption(self):
        """Test Kasa XOR encryption/decryption."""
        emulator = KasaBulbEmulator()

        # Test string
        original = '{"test": "data"}'

        # Encrypt
        encrypted = emulator._encrypt(original)
        assert isinstance(encrypted, bytes)
        assert encrypted != original.encode()

        # Decrypt
        decrypted = emulator._decrypt(encrypted)
        assert decrypted == original

    def test_encryption_key_propagation(self):
        """Test XOR cipher key propagation."""
        emulator = KasaBulbEmulator()

        # Encrypt multiple characters
        original = "Hello"
        encrypted = emulator._encrypt(original)

        # Each byte should be different (key propagates)
        assert len(set(encrypted)) > 1  # Not all same byte

        # Decrypt should recover original
        decrypted = emulator._decrypt(encrypted)
        assert decrypted == original

    def test_process_command_get_sysinfo(self):
        """Test processing get_sysinfo command."""
        emulator = KasaBulbEmulator(name="Test Bulb")
        emulator.set_hsv(180, 70, 50)

        cmd_json = '{"system": {"get_sysinfo": {}}}'
        response_json = emulator._process_command(cmd_json)

        response = json.loads(response_json)

        assert "system" in response
        assert "get_sysinfo" in response["system"]

        sysinfo = response["system"]["get_sysinfo"]
        assert sysinfo["alias"] == "Test Bulb"
        assert sysinfo["model"] == "KL130(US)"
        assert sysinfo["light_state"]["hue"] == 180
        assert sysinfo["light_state"]["saturation"] == 70
        assert sysinfo["light_state"]["brightness"] == 50
        assert sysinfo["err_code"] == 0

    def test_process_command_set_hsv(self):
        """Test processing transition_light_state command."""
        emulator = KasaBulbEmulator()

        cmd_json = '''
        {
            "smartlife.iot.smartbulb.lightingservice": {
                "transition_light_state": {
                    "hue": 240,
                    "saturation": 90,
                    "brightness": 70,
                    "on_off": 1
                }
            }
        }
        '''

        response_json = emulator._process_command(cmd_json)

        # Check response
        response = json.loads(response_json)
        assert response["smartlife.iot.smartbulb.lightingservice"]["transition_light_state"]["err_code"] == 0

        # Check state was updated
        assert emulator.hue == 240
        assert emulator.saturation == 90
        assert emulator.brightness == 70
        assert emulator.is_on == True
        assert emulator.state_changes == 1

    def test_command_count_tracking(self):
        """Test command_count increments on each command."""
        emulator = KasaBulbEmulator()

        assert emulator.command_count == 0

        emulator._process_command('{"system": {"get_sysinfo": {}}}')
        assert emulator.command_count == 1

        emulator._process_command('{"system": {"get_sysinfo": {}}}')
        assert emulator.command_count == 2

    def test_invalid_json_command(self):
        """Test emulator handles invalid JSON gracefully."""
        emulator = KasaBulbEmulator()

        response_json = emulator._process_command('{invalid json')

        response = json.loads(response_json)
        assert response["err_code"] == -1

    def test_multiple_hsv_changes(self):
        """Test emulator handles multiple HSV changes correctly."""
        emulator = KasaBulbEmulator()

        hsv_values = [
            (0, 100, 80),    # Red
            (120, 100, 80),  # Green
            (240, 100, 80),  # Blue
            (60, 100, 80),   # Yellow
        ]

        for i, (h, s, v) in enumerate(hsv_values, 1):
            emulator.set_hsv(h, s, v)
            assert emulator.hue == h
            assert emulator.saturation == s
            assert emulator.brightness == v
            assert emulator.state_changes == i


class TestMultiBulbEmulator:
    """Test MultiBulbEmulator functionality."""

    def test_initialization(self):
        """Test multi-bulb emulator initializes correctly."""
        bulb_configs = [
            ("127.0.0.1", 9999, "Bulb 1"),
            ("127.0.0.2", 9999, "Bulb 2"),
        ]

        emulator = MultiBulbEmulator(bulb_configs)

        assert len(emulator.bulbs) == 2
        assert emulator.bulbs[0].name == "Bulb 1"
        assert emulator.bulbs[1].name == "Bulb 2"
        assert emulator.bulbs[0].ip == "127.0.0.1"
        assert emulator.bulbs[1].ip == "127.0.0.2"

    def test_four_bulb_configuration(self):
        """Test typical 4-bulb setup."""
        bulb_configs = [
            ("127.0.0.1", 9999, "Zone 0 - Red"),
            ("127.0.0.2", 9999, "Zone 1 - Green"),
            ("127.0.0.3", 9999, "Zone 2 - Blue"),
            ("127.0.0.4", 9999, "Zone 3 - Yellow"),
        ]

        emulator = MultiBulbEmulator(bulb_configs)

        assert len(emulator.bulbs) == 4

        # Verify each bulb
        for i, bulb in enumerate(emulator.bulbs):
            assert bulb.ip == f"127.0.0.{i+1}"
            assert bulb.port == 9999
            assert "Zone" in bulb.name

    def test_independent_bulb_state(self):
        """Test bulbs maintain independent state."""
        bulb_configs = [
            ("127.0.0.1", 9999, "Bulb 1"),
            ("127.0.0.2", 9999, "Bulb 2"),
        ]

        emulator = MultiBulbEmulator(bulb_configs)

        # Set different HSV for each bulb
        emulator.bulbs[0].set_hsv(0, 100, 80)
        emulator.bulbs[1].set_hsv(240, 50, 60)

        # Verify independence
        assert emulator.bulbs[0].hue == 0
        assert emulator.bulbs[0].saturation == 100
        assert emulator.bulbs[0].brightness == 80

        assert emulator.bulbs[1].hue == 240
        assert emulator.bulbs[1].saturation == 50
        assert emulator.bulbs[1].brightness == 60

    def test_statistics_per_bulb(self):
        """Test each bulb tracks its own statistics."""
        bulb_configs = [
            ("127.0.0.1", 9999, "Bulb 1"),
            ("127.0.0.2", 9999, "Bulb 2"),
        ]

        emulator = MultiBulbEmulator(bulb_configs)

        # Different activity on each bulb
        emulator.bulbs[0].set_hsv(100, 80, 70)
        emulator.bulbs[0].set_hsv(110, 80, 70)

        emulator.bulbs[1].set_hsv(200, 60, 50)

        # Statistics should be independent
        assert emulator.bulbs[0].state_changes == 2
        assert emulator.bulbs[1].state_changes == 1
