"""Test suite for lighting effects calculation."""
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from osc_receiver import bpm_to_hue


class TestBpmToHue:
    """Tests for BPM to hue color mapping."""

    def test_bpm_to_hue_40_bpm_maps_to_240_degrees(self):
        """40 BPM should map to 240° (blue, calm)."""
        assert bpm_to_hue(40) == 240

    def test_bpm_to_hue_80_bpm_maps_to_120_degrees(self):
        """80 BPM should map to 120° (green, neutral)."""
        assert bpm_to_hue(80) == 120

    def test_bpm_to_hue_120_bpm_maps_to_0_degrees(self):
        """120 BPM should map to 0° (red, excited)."""
        assert bpm_to_hue(120) == 0

    def test_bpm_clamping_low(self):
        """BPM below 40 should be clamped to 40 (240°)."""
        assert bpm_to_hue(30) == 240
        assert bpm_to_hue(0) == 240
        assert bpm_to_hue(-10) == 240

    def test_bpm_clamping_high(self):
        """BPM above 120 should be clamped to 120 (0°)."""
        assert bpm_to_hue(150) == 0
        assert bpm_to_hue(200) == 0
        assert bpm_to_hue(1000) == 0

    def test_bpm_intermediate_values(self):
        """Test intermediate values within valid range."""
        # 60 BPM: halfway between 40 and 80
        # hue = 240 - ((60 - 40) / 80) * 240 = 240 - (20/80) * 240 = 240 - 60 = 180
        assert bpm_to_hue(60) == 180

        # 100 BPM: halfway between 80 and 120
        # hue = 240 - ((100 - 40) / 80) * 240 = 240 - (60/80) * 240 = 240 - 180 = 60
        assert bpm_to_hue(100) == 60

    def test_bpm_to_hue_returns_integer(self):
        """Result should always be an integer."""
        result = bpm_to_hue(75)
        assert isinstance(result, int)

    def test_bpm_to_hue_with_float_input(self):
        """Should handle float BPM values."""
        # 70.5 BPM
        # hue = 240 - ((70.5 - 40) / 80) * 240 = 240 - (30.5/80) * 240 = 240 - 91.5 = 148.5
        # Should be converted to int: 148
        result = bpm_to_hue(70.5)
        assert result == 148
        assert isinstance(result, int)
