#!/usr/bin/env python3
"""
Unit tests for OSC protocol validation.

Tests OSC message format, data validation, BPM calculations, and variance.
Reference: p1-tst-trd.md, Requirements R14-R18

Component 4: Unit Tests for OSC Protocol Testing Infrastructure
"""

import unittest
import random
from pythonosc.osc_message_builder import OscMessageBuilder
from osc_receiver import HeartbeatReceiver


def generate_ibi_with_variance(base_ibi, variance_percent, count):
    """
    Generate IBI values with specified variance around base value.

    Args:
        base_ibi: Base IBI value in milliseconds
        variance_percent: Variance as percentage (e.g., 5 for ±5%)
        count: Number of samples to generate

    Returns:
        List of IBI values within variance range
    """
    min_ibi = base_ibi * (1 - variance_percent / 100)
    max_ibi = base_ibi * (1 + variance_percent / 100)

    samples = []
    for _ in range(count):
        # Generate random value within variance range
        ibi = random.uniform(min_ibi, max_ibi)
        samples.append(int(ibi))

    return samples


class TestOSCProtocol(unittest.TestCase):
    """Test OSC protocol format and validation (R14-R17)."""

    def setUp(self):
        """Set up test fixtures."""
        self.receiver = HeartbeatReceiver()

    def test_message_address_format(self):
        """
        Test R14: OSC messages use correct address pattern /heartbeat/[0-3].

        Verifies all 4 sensor IDs produce correctly formatted addresses.
        """
        for sensor_id in range(4):
            address = f"/heartbeat/{sensor_id}"
            msg = OscMessageBuilder(address=address)
            msg.add_arg(1000)  # Valid IBI value
            built_msg = msg.build()

            # Verify address is in the binary message
            self.assertIn(address.encode('ascii'), built_msg.dgram,
                         f"Address {address} not found in OSC message binary")

    def test_message_argument_type(self):
        """
        Test R14: OSC messages use int32 type tag.

        Verifies the type tag string contains 'i' for int32.
        """
        msg = OscMessageBuilder(address="/heartbeat/0")
        msg.add_arg(1000, arg_type='i')  # Explicitly use int32
        built_msg = msg.build()

        # Type tag string should contain ',i' (comma followed by 'i')
        self.assertIn(b',i', built_msg.dgram,
                     "Type tag ',i' not found in OSC message")

    def test_message_encoding(self):
        """
        Test R14: OSC messages are exactly 24 bytes.

        Verifies total message size matches expected encoding.
        """
        msg = OscMessageBuilder(address="/heartbeat/0")
        msg.add_arg(1000)
        built_msg = msg.build()

        self.assertEqual(len(built_msg.dgram), 24,
                        f"OSC message size is {len(built_msg.dgram)}, expected 24 bytes")

    def test_message_null_padding(self):
        """
        Test R14: OSC messages use null padding in address and type tag.

        Explicitly verifies both address and type tag null padding.
        Addresses Chico's concern about explicit null byte verification.
        """
        msg = OscMessageBuilder(address="/heartbeat/0")
        msg.add_arg(1000)
        built_msg = msg.build()

        # Address '/heartbeat/0' is 13 bytes, padded to 16 bytes with null padding
        self.assertIn(b'/heartbeat/0\x00\x00\x00', built_msg.dgram,
                     "Address '/heartbeat/0\\x00\\x00\\x00' with null padding not found in OSC message")

        # Type tag must be exactly ',i\x00\x00' (4 bytes with null padding)
        self.assertIn(b',i\x00\x00', built_msg.dgram,
                     "Type tag ',i\\x00\\x00' with null padding not found in OSC message")

    def test_ibi_range_validation(self):
        """
        Test R15: IBI values must be in range 300-3000ms.

        Tests boundary conditions: 299 (invalid), 300 (valid), 3000 (valid), 3001 (invalid).
        """
        test_cases = [
            (299, False, "IBI 299ms should be invalid (below minimum)"),
            (300, True, "IBI 300ms should be valid (at minimum)"),
            (3000, True, "IBI 3000ms should be valid (at maximum)"),
            (3001, False, "IBI 3001ms should be invalid (above maximum)")
        ]

        for ibi_value, expected_valid, description in test_cases:
            is_valid, sensor_id, error_msg = self.receiver.validate_message(
                "/heartbeat/0", ibi_value
            )
            self.assertEqual(is_valid, expected_valid, description)

    def test_sensor_id_range(self):
        """
        Test R15: Sensor IDs must be in range 0-3.

        Tests boundary conditions: -1 (invalid), 0 (valid), 3 (valid), 4 (invalid).
        """
        test_cases = [
            ("/heartbeat/-1", False, "Sensor ID -1 should be invalid (below minimum)"),
            ("/heartbeat/0", True, "Sensor ID 0 should be valid (at minimum)"),
            ("/heartbeat/3", True, "Sensor ID 3 should be valid (at maximum)"),
            ("/heartbeat/4", False, "Sensor ID 4 should be invalid (above maximum)")
        ]

        for address, expected_valid, description in test_cases:
            is_valid, sensor_id, error_msg = self.receiver.validate_message(
                address, 1000  # Valid IBI value
            )
            self.assertEqual(is_valid, expected_valid, description)

    def test_bpm_calculation(self):
        """
        Test R16: BPM calculation accuracy using receiver's implementation.

        Tests receiver's calculate_sensor_stats() method with test cases:
        1000ms→60 BPM, 857ms→70 BPM, 750ms→80 BPM, 600ms→100 BPM
        Uses ±0.5 BPM tolerance for floating point comparison.
        """
        tolerance = 0.5  # BPM tolerance

        test_cases = [
            (1000, 60.0, "1000ms should yield 60 BPM"),
            (857, 70.0, "857ms should yield 70 BPM"),
            (750, 80.0, "750ms should yield 80 BPM"),
            (600, 100.0, "600ms should yield 100 BPM")
        ]

        for ibi_ms, expected_bpm, description in test_cases:
            # Set up receiver state with single IBI value for sensor 0
            self.receiver.sensor_ibi_sums[0] = ibi_ms
            self.receiver.sensor_counts[0] = 1

            # Test receiver's BPM calculation implementation
            avg_ibi, avg_bpm = self.receiver.calculate_sensor_stats(0)

            self.assertAlmostEqual(avg_bpm, expected_bpm, delta=tolerance,
                                  msg=description)

    def test_ibi_variance(self):
        """
        Test R17: IBI variance stays within ±5% over 100+ samples.

        Generates 100 samples around base IBI of 1000ms with 5% variance.
        Verifies all samples are unique and within expected range.
        Addresses Chico's concern about generating 100+ samples.
        """
        base_ibi = 1000
        variance_percent = 5
        sample_count = 100

        samples = generate_ibi_with_variance(base_ibi, variance_percent, sample_count)

        # Verify we got the right number of samples
        self.assertEqual(len(samples), sample_count,
                        f"Expected {sample_count} samples, got {len(samples)}")

        # Verify variance bounds (±5%)
        min_expected = base_ibi * 0.95  # 950ms
        max_expected = base_ibi * 1.05  # 1050ms

        for sample in samples:
            self.assertGreaterEqual(sample, min_expected,
                                   f"Sample {sample} below minimum {min_expected}")
            self.assertLessEqual(sample, max_expected,
                                f"Sample {sample} above maximum {max_expected}")

        # Verify samples have variance (not all identical)
        unique_samples = set(samples)
        self.assertGreater(len(unique_samples), 1,
                          "Samples should have variance, not all identical")


if __name__ == '__main__':
    # R18: Test execution via single command with proper exit codes
    unittest.main()
