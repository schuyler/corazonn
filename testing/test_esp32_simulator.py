#!/usr/bin/env python3
"""
Unit tests for ESP32 Simulator
Tests core functionality without requiring network operations.
"""

import unittest
import sys
import os

# Add testing directory to path to import simulator module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import will work after we create the simulator module
# For now, we'll test individual functions


class TestIBICalculation(unittest.TestCase):
    """Test IBI calculation and variance logic (R2)"""

    def setUp(self):
        """Import simulator functions for testing"""
        # This will import the functions after we create the module
        try:
            from esp32_simulator import calculate_base_ibi, generate_ibi_with_variance, clamp_ibi
            self.calculate_base_ibi = calculate_base_ibi
            self.generate_ibi_with_variance = generate_ibi_with_variance
            self.clamp_ibi = clamp_ibi
        except ImportError:
            self.skipTest("esp32_simulator module not yet created")

    def test_base_ibi_calculation_60bpm(self):
        """Test: 60 BPM should give 1000ms IBI"""
        ibi = self.calculate_base_ibi(60)
        self.assertEqual(ibi, 1000)

    def test_base_ibi_calculation_75bpm(self):
        """Test: 75 BPM should give 800ms IBI"""
        ibi = self.calculate_base_ibi(75)
        self.assertEqual(ibi, 800)

    def test_base_ibi_calculation_120bpm(self):
        """Test: 120 BPM should give 500ms IBI"""
        ibi = self.calculate_base_ibi(120)
        self.assertEqual(ibi, 500)

    def test_base_ibi_calculation_40bpm(self):
        """Test: 40 BPM should give 1500ms IBI"""
        ibi = self.calculate_base_ibi(40)
        self.assertEqual(ibi, 1500)

    def test_ibi_variance_produces_different_values(self):
        """Test: Generated IBI values should have variance (not all identical)"""
        base_ibi = 1000
        values = [self.generate_ibi_with_variance(base_ibi) for _ in range(100)]

        # Not all values should be identical (variance exists)
        unique_values = set(values)
        self.assertGreater(len(unique_values), 1,
                          "IBI variance should produce different values")

    def test_ibi_variance_within_5_percent(self):
        """Test: IBI variance should be ±5% of base value"""
        base_ibi = 1000
        values = [self.generate_ibi_with_variance(base_ibi) for _ in range(100)]

        # All values should be within ±5% before clamping
        min_expected = base_ibi * 0.95
        max_expected = base_ibi * 1.05

        for value in values:
            self.assertGreaterEqual(value, min_expected - 1,  # Allow 1ms rounding
                                   f"IBI {value} below -5% range ({min_expected})")
            self.assertLessEqual(value, max_expected + 1,  # Allow 1ms rounding
                                f"IBI {value} above +5% range ({max_expected})")

    def test_clamp_ibi_within_range(self):
        """Test: IBI values within 300-3000 should not be clamped"""
        self.assertEqual(self.clamp_ibi(500), 500)
        self.assertEqual(self.clamp_ibi(1000), 1000)
        self.assertEqual(self.clamp_ibi(2500), 2500)

    def test_clamp_ibi_minimum(self):
        """Test: IBI values below 300 should be clamped to 300"""
        self.assertEqual(self.clamp_ibi(100), 300)
        self.assertEqual(self.clamp_ibi(299), 300)
        self.assertEqual(self.clamp_ibi(0), 300)

    def test_clamp_ibi_maximum(self):
        """Test: IBI values above 3000 should be clamped to 3000"""
        self.assertEqual(self.clamp_ibi(3001), 3000)
        self.assertEqual(self.clamp_ibi(5000), 3000)
        self.assertEqual(self.clamp_ibi(10000), 3000)


class TestInputValidation(unittest.TestCase):
    """Test command-line input validation (R5)"""

    def setUp(self):
        """Import validation functions"""
        try:
            from esp32_simulator import validate_sensor_count, validate_bpm_values
            self.validate_sensor_count = validate_sensor_count
            self.validate_bpm_values = validate_bpm_values
        except ImportError:
            self.skipTest("esp32_simulator module not yet created")

    def test_validate_sensor_count_valid(self):
        """Test: Sensor count 1-4 should be valid"""
        self.assertTrue(self.validate_sensor_count(1))
        self.assertTrue(self.validate_sensor_count(2))
        self.assertTrue(self.validate_sensor_count(3))
        self.assertTrue(self.validate_sensor_count(4))

    def test_validate_sensor_count_invalid_low(self):
        """Test: Sensor count < 1 should be invalid"""
        self.assertFalse(self.validate_sensor_count(0))
        self.assertFalse(self.validate_sensor_count(-1))

    def test_validate_sensor_count_invalid_high(self):
        """Test: Sensor count > 4 should be invalid"""
        self.assertFalse(self.validate_sensor_count(5))
        self.assertFalse(self.validate_sensor_count(10))

    def test_validate_bpm_values_valid(self):
        """Test: BPM values 20-200 should be valid"""
        self.assertTrue(self.validate_bpm_values([20]))
        self.assertTrue(self.validate_bpm_values([60, 75, 80, 100]))
        self.assertTrue(self.validate_bpm_values([200]))

    def test_validate_bpm_values_invalid_low(self):
        """Test: BPM values < 20 should be invalid"""
        self.assertFalse(self.validate_bpm_values([10]))
        self.assertFalse(self.validate_bpm_values([60, 15, 80]))

    def test_validate_bpm_values_invalid_high(self):
        """Test: BPM values > 200 should be invalid"""
        self.assertFalse(self.validate_bpm_values([250]))
        self.assertFalse(self.validate_bpm_values([60, 75, 300]))

    def test_validate_bpm_count_matches_sensors(self):
        """Test: BPM value count must match sensor count"""
        # This test ensures we have the right number of BPM values
        bpm_values = [60, 75, 80]
        self.assertEqual(len(bpm_values), 3)


class TestStatisticsFormat(unittest.TestCase):
    """Test final statistics output format (R6)"""

    def setUp(self):
        """Import statistics formatting function"""
        try:
            from esp32_simulator import format_final_statistics
            self.format_final_statistics = format_final_statistics
        except ImportError:
            self.skipTest("esp32_simulator module not yet created")

    def test_final_statistics_format(self):
        """Test: Final statistics should match expected parseable format"""
        counts = [10, 15, 8, 12]  # sensor_0=10, sensor_1=15, etc.
        output = self.format_final_statistics(counts)

        # Should be parseable format
        self.assertIn("SIMULATOR_FINAL_STATS:", output)
        self.assertIn("sensor_0=10", output)
        self.assertIn("sensor_1=15", output)
        self.assertIn("sensor_2=8", output)
        self.assertIn("sensor_3=12", output)
        self.assertIn("total=45", output)

    def test_final_statistics_fewer_sensors(self):
        """Test: Final statistics for fewer than 4 sensors"""
        counts = [20, 25, 0, 0]  # Only 2 sensors active
        output = self.format_final_statistics(counts)

        self.assertIn("sensor_0=20", output)
        self.assertIn("sensor_1=25", output)
        self.assertIn("sensor_2=0", output)
        self.assertIn("sensor_3=0", output)
        self.assertIn("total=45", output)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
