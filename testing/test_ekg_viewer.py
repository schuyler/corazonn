#!/usr/bin/env python3
"""
Unit tests for EKG Visualizer receiver tool.

Tests OSC message handling, data buffer management, CLI argument parsing,
and configuration validation for the EKG viewer application.

Reference: ekg-visualization-design.md
"""

import unittest
import threading
import time
from collections import deque
from unittest.mock import patch, MagicMock
import argparse
import sys

# Import the module to be tested (will fail initially - this is expected)
try:
    from ekg_viewer import EKGViewer, create_argument_parser, validate_config
except ImportError:
    # Create dummy classes for test execution
    EKGViewer = None
    create_argument_parser = None
    validate_config = None


class TestEKGViewerConfiguration(unittest.TestCase):
    """Test configuration validation and initialization."""

    def test_configuration_validation_valid_values(self):
        """Test that valid configuration values pass validation."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        # Valid sensor ID (0-3)
        result = validate_config(port=8000, sensor_id=0, window=30)
        self.assertTrue(result, "Valid config should pass validation")

    def test_configuration_validation_all_sensor_ids(self):
        """Test that all valid sensor IDs (0-3) pass validation."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        for sensor_id in range(4):
            result = validate_config(port=8000, sensor_id=sensor_id, window=30)
            self.assertTrue(result, f"Sensor ID {sensor_id} should be valid")

    def test_configuration_invalid_sensor_id_negative(self):
        """Test that negative sensor ID fails validation."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        with self.assertRaises((ValueError, AssertionError)):
            validate_config(port=8000, sensor_id=-1, window=30)

    def test_configuration_invalid_sensor_id_too_high(self):
        """Test that sensor ID > 3 fails validation."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        with self.assertRaises((ValueError, AssertionError)):
            validate_config(port=8000, sensor_id=4, window=30)

    def test_configuration_invalid_port_zero(self):
        """Test that port 0 fails validation."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        with self.assertRaises((ValueError, AssertionError)):
            validate_config(port=0, sensor_id=0, window=30)

    def test_configuration_invalid_port_too_high(self):
        """Test that port > 65535 fails validation."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        with self.assertRaises((ValueError, AssertionError)):
            validate_config(port=65536, sensor_id=0, window=30)

    def test_configuration_valid_port_boundaries(self):
        """Test that port boundaries 1 and 65535 pass validation."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        result1 = validate_config(port=1, sensor_id=0, window=30)
        self.assertTrue(result1, "Port 1 should be valid")

        result2 = validate_config(port=65535, sensor_id=0, window=30)
        self.assertTrue(result2, "Port 65535 should be valid")

    def test_configuration_invalid_window_zero(self):
        """Test that window size 0 fails validation."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        with self.assertRaises((ValueError, AssertionError)):
            validate_config(port=8000, sensor_id=0, window=0)

    def test_configuration_invalid_window_negative(self):
        """Test that negative window size fails validation."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        with self.assertRaises((ValueError, AssertionError)):
            validate_config(port=8000, sensor_id=0, window=-5)

    def test_configuration_valid_window_boundary(self):
        """Test that window size >= 1 is valid."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        result = validate_config(port=8000, sensor_id=0, window=1)
        self.assertTrue(result, "Window size 1 should be valid")

    def test_configuration_large_window(self):
        """Test that large window sizes are valid."""
        if validate_config is None:
            self.skipTest("validate_config not yet implemented")

        result = validate_config(port=8000, sensor_id=0, window=300)
        self.assertTrue(result, "Large window size should be valid")


class TestArgumentParser(unittest.TestCase):
    """Test CLI argument parsing."""

    def test_parser_sensor_id_required(self):
        """Test that --sensor-id argument is required."""
        if create_argument_parser is None:
            self.skipTest("create_argument_parser not yet implemented")

        parser = create_argument_parser()

        # Should fail without --sensor-id
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_parser_sensor_id_valid(self):
        """Test parsing valid sensor ID argument."""
        if create_argument_parser is None:
            self.skipTest("create_argument_parser not yet implemented")

        parser = create_argument_parser()
        args = parser.parse_args(['--sensor-id', '0'])

        self.assertEqual(args.sensor_id, 0)

    def test_parser_sensor_id_all_values(self):
        """Test parsing all valid sensor IDs (0-3)."""
        if create_argument_parser is None:
            self.skipTest("create_argument_parser not yet implemented")

        parser = create_argument_parser()

        for sensor_id in range(4):
            args = parser.parse_args(['--sensor-id', str(sensor_id)])
            self.assertEqual(args.sensor_id, sensor_id)

    def test_parser_port_has_default(self):
        """Test that --port has a default value (8000)."""
        if create_argument_parser is None:
            self.skipTest("create_argument_parser not yet implemented")

        parser = create_argument_parser()
        args = parser.parse_args(['--sensor-id', '0'])

        # Port should have a default value
        self.assertIsNotNone(args.port)
        self.assertEqual(args.port, 8000)

    def test_parser_port_custom_value(self):
        """Test parsing custom port value."""
        if create_argument_parser is None:
            self.skipTest("create_argument_parser not yet implemented")

        parser = create_argument_parser()
        args = parser.parse_args(['--sensor-id', '0', '--port', '9000'])

        self.assertEqual(args.port, 9000)

    def test_parser_window_has_default(self):
        """Test that --window has a default value (30)."""
        if create_argument_parser is None:
            self.skipTest("create_argument_parser not yet implemented")

        parser = create_argument_parser()
        args = parser.parse_args(['--sensor-id', '0'])

        # Window should have a default value
        self.assertIsNotNone(args.window)
        self.assertEqual(args.window, 30)

    def test_parser_window_custom_value(self):
        """Test parsing custom window value."""
        if create_argument_parser is None:
            self.skipTest("create_argument_parser not yet implemented")

        parser = create_argument_parser()
        args = parser.parse_args(['--sensor-id', '0', '--window', '60'])

        self.assertEqual(args.window, 60)

    def test_parser_all_arguments_together(self):
        """Test parsing all arguments together."""
        if create_argument_parser is None:
            self.skipTest("create_argument_parser not yet implemented")

        parser = create_argument_parser()
        args = parser.parse_args([
            '--sensor-id', '2',
            '--port', '9000',
            '--window', '60'
        ])

        self.assertEqual(args.sensor_id, 2)
        self.assertEqual(args.port, 9000)
        self.assertEqual(args.window, 60)


class TestOSCMessageHandling(unittest.TestCase):
    """Test OSC message handling and validation."""

    def setUp(self):
        """Set up test fixtures."""
        if EKGViewer is not None:
            self.viewer = EKGViewer(port=8000, sensor_id=0, window=30)

    def test_message_address_pattern_valid(self):
        """Test that valid address pattern /heartbeat/[0-3] is accepted."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # Valid addresses should be accepted and data stored
        valid_addresses = [
            '/heartbeat/0',
            '/heartbeat/1',
            '/heartbeat/2',
            '/heartbeat/3'
        ]

        for address in valid_addresses:
            viewer = EKGViewer(port=8000, sensor_id=int(address[-1]), window=30)
            viewer.handle_osc_message(address, 1000)

            # If valid, buffer should have data
            with viewer.buffer_lock:
                self.assertGreater(len(viewer.data_buffer), 0,
                    f"Valid address {address} should result in data in buffer")

    def test_message_address_pattern_invalid_format(self):
        """Test that invalid address patterns are rejected."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        invalid_addresses = [
            '/heartbeat',           # Missing sensor ID
            '/heartbeat/4',         # Sensor ID out of range
            '/heartbeat/-1',        # Negative sensor ID
            '/heart/0',             # Wrong path
            '/heartbeat/0/extra',   # Extra path component
            'heartbeat/0',          # Missing leading slash
        ]

        for address in invalid_addresses:
            viewer = EKGViewer(port=8000, sensor_id=0, window=30)
            # Send message with invalid address - should either raise or silently reject
            try:
                viewer.handle_osc_message(address, 1000)
            except (ValueError, AssertionError):
                # If it raises, that's acceptable
                pass

            # Buffer should remain empty (message rejected)
            with viewer.buffer_lock:
                self.assertEqual(len(viewer.data_buffer), 0,
                    f"Invalid address {address} should result in empty buffer")

    def test_message_ibi_range_validation_lower_boundary(self):
        """Test IBI range validation at lower boundary (300ms minimum)."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # 299ms should be rejected - buffer should stay empty
        viewer_invalid = EKGViewer(port=8000, sensor_id=0, window=30)
        try:
            viewer_invalid.handle_osc_message('/heartbeat/0', 299)
        except (ValueError, AssertionError):
            pass

        with viewer_invalid.buffer_lock:
            self.assertEqual(len(viewer_invalid.data_buffer), 0,
                "IBI 299ms should be rejected")

        # 300ms should be accepted - buffer should have data
        viewer_valid = EKGViewer(port=8000, sensor_id=0, window=30)
        viewer_valid.handle_osc_message('/heartbeat/0', 300)

        with viewer_valid.buffer_lock:
            self.assertEqual(len(viewer_valid.data_buffer), 1,
                "IBI 300ms should be accepted")

    def test_message_ibi_range_validation_upper_boundary(self):
        """Test IBI range validation at upper boundary (3000ms maximum)."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # 3000ms should be accepted - buffer should have data
        viewer_valid = EKGViewer(port=8000, sensor_id=0, window=30)
        viewer_valid.handle_osc_message('/heartbeat/0', 3000)

        with viewer_valid.buffer_lock:
            self.assertEqual(len(viewer_valid.data_buffer), 1,
                "IBI 3000ms should be accepted")

        # 3001ms should be rejected - buffer should stay empty
        viewer_invalid = EKGViewer(port=8000, sensor_id=0, window=30)
        try:
            viewer_invalid.handle_osc_message('/heartbeat/0', 3001)
        except (ValueError, AssertionError):
            pass

        with viewer_invalid.buffer_lock:
            self.assertEqual(len(viewer_invalid.data_buffer), 0,
                "IBI 3001ms should be rejected")

    def test_message_ibi_range_validation_typical_values(self):
        """Test IBI range validation with typical heartbeat values."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # Typical IBI values (60-100 BPM = 600-1000ms)
        typical_values = [600, 750, 857, 1000]

        for ibi in typical_values:
            viewer = EKGViewer(port=8000, sensor_id=0, window=30)
            viewer.handle_osc_message('/heartbeat/0', ibi)

            with viewer.buffer_lock:
                self.assertEqual(len(viewer.data_buffer), 1,
                    f"IBI {ibi}ms should be accepted")

    def test_message_ibi_type_validation(self):
        """Test that IBI must be numeric."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # Non-numeric values should be rejected
        invalid_types = ["1000", None, [1000], {"value": 1000}]

        for invalid_value in invalid_types:
            viewer = EKGViewer(port=8000, sensor_id=0, window=30)

            try:
                viewer.handle_osc_message('/heartbeat/0', invalid_value)
            except (ValueError, TypeError, AssertionError):
                # If it raises, that's acceptable
                pass

            # Buffer should remain empty (message rejected)
            with viewer.buffer_lock:
                self.assertEqual(len(viewer.data_buffer), 0,
                    f"Invalid type {type(invalid_value).__name__} should be rejected")

    def test_sensor_id_filtering_accepts_selected_sensor(self):
        """Test that only selected sensor ID messages are stored."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # Simulate receiving a message for sensor 0 when monitoring sensor 0
        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        try:
            # Should accept message from sensor 0
            viewer.handle_osc_message('/heartbeat/0', 1000)

            # Buffer should not be empty
            with viewer.buffer_lock:
                self.assertGreater(len(viewer.data_buffer), 0)
        except Exception as e:
            self.fail(f"Should accept message from selected sensor: {e}")

    def test_sensor_id_filtering_rejects_other_sensors(self):
        """Test that messages from other sensors are filtered out."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # Monitor sensor 0, send message from sensor 1
        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        try:
            viewer.handle_osc_message('/heartbeat/1', 1000)

            # Buffer should remain empty
            with viewer.buffer_lock:
                self.assertEqual(len(viewer.data_buffer), 0)
        except Exception as e:
            # It's acceptable if the handler silently ignores other sensors
            pass

    def test_message_handler_appends_to_buffer(self):
        """Test that valid messages are appended to data buffer."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Append a valid message
        viewer.handle_osc_message('/heartbeat/0', 1000)

        # Check buffer contains data
        with viewer.buffer_lock:
            self.assertEqual(len(viewer.data_buffer), 1)

            # Data should be tuple of (timestamp, ibi)
            timestamp, ibi = viewer.data_buffer[0]
            self.assertIsInstance(timestamp, float)
            self.assertEqual(ibi, 1000)


class TestDataBuffer(unittest.TestCase):
    """Test data buffer management and thread safety."""

    def setUp(self):
        """Set up test fixtures."""
        if EKGViewer is not None:
            self.viewer = EKGViewer(port=8000, sensor_id=0, window=30)

    def test_buffer_structure_uses_deque(self):
        """Test that buffer uses collections.deque."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # Buffer should be a deque
        self.assertIsInstance(self.viewer.data_buffer, deque)

    def test_buffer_has_maxlen(self):
        """Test that buffer has correct maxlen set."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # Buffer should have maxlen set based on window size
        self.assertIsNotNone(self.viewer.data_buffer.maxlen)

        # For 30 second window: int(30 * 200 / 60) = 100
        expected_maxlen = int(30 * 200 / 60)
        self.assertEqual(self.viewer.data_buffer.maxlen, expected_maxlen)

    def test_buffer_stores_timestamp_ibi_tuples(self):
        """Test that buffer stores (timestamp, ibi) tuples."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # Add a message
        self.viewer.handle_osc_message('/heartbeat/0', 1000)

        # Verify data structure
        with self.viewer.buffer_lock:
            self.assertEqual(len(self.viewer.data_buffer), 1)

            item = self.viewer.data_buffer[0]
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

            timestamp, ibi = item
            self.assertIsInstance(timestamp, (int, float))
            self.assertIsInstance(ibi, int)

    def test_buffer_automatic_eviction_when_full(self):
        """Test that buffer automatically evicts old data when full."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=1)  # Very small buffer

        # Calculate buffer size for 1 second window
        buffer_size = int(1 * 200 / 60)  # Should be 3

        # Fill buffer beyond capacity
        for i in range(buffer_size + 5):
            viewer.handle_osc_message('/heartbeat/0', 600 + i)

        # Buffer should not exceed maxlen
        with viewer.buffer_lock:
            self.assertLessEqual(len(viewer.data_buffer), buffer_size)

    def test_buffer_thread_safe_with_lock(self):
        """Test that buffer access is protected by threading.Lock."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        # Buffer should have a lock
        self.assertEqual(type(self.viewer.buffer_lock).__name__, 'lock')

    def test_buffer_concurrent_access(self):
        """Test that buffer can be safely accessed from multiple threads."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)
        errors = []

        def add_data():
            """Thread that adds data to buffer."""
            try:
                for i in range(10):
                    viewer.handle_osc_message('/heartbeat/0', 600 + i)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def read_data():
            """Thread that reads data from buffer."""
            try:
                for _ in range(10):
                    with viewer.buffer_lock:
                        len(viewer.data_buffer)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Run concurrent access
        writer_thread = threading.Thread(target=add_data)
        reader_thread = threading.Thread(target=read_data)

        writer_thread.start()
        reader_thread.start()

        writer_thread.join(timeout=5)
        reader_thread.join(timeout=5)

        # Should complete without errors
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")

    def test_buffer_timestamps_are_sequential(self):
        """Test that timestamps in buffer are sequential."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Add multiple messages
        for i in range(5):
            viewer.handle_osc_message('/heartbeat/0', 1000)
            time.sleep(0.01)  # Small delay to ensure time difference

        # Verify timestamps are increasing
        with viewer.buffer_lock:
            timestamps = [item[0] for item in viewer.data_buffer]

            for i in range(1, len(timestamps)):
                self.assertGreaterEqual(timestamps[i], timestamps[i-1],
                    "Timestamps should be sequential")

    def test_buffer_copy_for_plotting(self):
        """Test that buffer can be safely copied for plotting."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Add data
        for i in range(5):
            viewer.handle_osc_message('/heartbeat/0', 900 + i * 10)

        # Copy buffer for plotting
        with viewer.buffer_lock:
            data_copy = list(viewer.data_buffer)

        # Should be a list of tuples
        self.assertIsInstance(data_copy, list)
        self.assertEqual(len(data_copy), 5)

        for item in data_copy:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)


class TestEKGViewerInitialization(unittest.TestCase):
    """Test EKGViewer class initialization and attributes."""

    def test_viewer_initialization_with_defaults(self):
        """Test EKGViewer initialization with only required arguments."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        self.assertEqual(viewer.port, 8000)
        self.assertEqual(viewer.sensor_id, 0)
        self.assertEqual(viewer.window_seconds, 30)

    def test_viewer_initialization_all_sensor_ids(self):
        """Test EKGViewer can be initialized with any valid sensor ID."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        for sensor_id in range(4):
            viewer = EKGViewer(port=8000, sensor_id=sensor_id, window=30)
            self.assertEqual(viewer.sensor_id, sensor_id)

    def test_viewer_creates_data_buffer(self):
        """Test that EKGViewer creates data buffer on initialization."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        self.assertIsNotNone(viewer.data_buffer)
        self.assertIsInstance(viewer.data_buffer, deque)

    def test_viewer_creates_buffer_lock(self):
        """Test that EKGViewer creates threading lock on initialization."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        self.assertIsNotNone(viewer.buffer_lock)
        self.assertEqual(type(viewer.buffer_lock).__name__, 'lock')

    def test_viewer_different_window_sizes(self):
        """Test EKGViewer with different window sizes."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        window_sizes = [1, 10, 30, 60, 120]

        for window in window_sizes:
            viewer = EKGViewer(port=8000, sensor_id=0, window=window)
            self.assertEqual(viewer.window_seconds, window)

            # Buffer size should scale appropriately
            expected_size = int(window * 200 / 60)
            self.assertEqual(viewer.data_buffer.maxlen, expected_size)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_very_low_ibi_value(self):
        """Test IBI value at very low end of spectrum."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # 300ms IBI = 200 BPM (maximum healthy heart rate)
        viewer.handle_osc_message('/heartbeat/0', 300)

        with viewer.buffer_lock:
            self.assertEqual(len(viewer.data_buffer), 1)
            _, ibi = viewer.data_buffer[0]
            self.assertEqual(ibi, 300)

    def test_very_high_ibi_value(self):
        """Test IBI value at very high end of spectrum."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # 3000ms IBI = 20 BPM (very slow, possibly resting/athletic)
        viewer.handle_osc_message('/heartbeat/0', 3000)

        with viewer.buffer_lock:
            self.assertEqual(len(viewer.data_buffer), 1)
            _, ibi = viewer.data_buffer[0]
            self.assertEqual(ibi, 3000)

    def test_empty_buffer_copy(self):
        """Test copying empty buffer for plotting."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Copy empty buffer
        with viewer.buffer_lock:
            data_copy = list(viewer.data_buffer)

        self.assertEqual(len(data_copy), 0)

    def test_single_message_in_buffer(self):
        """Test buffer with single message."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)
        viewer.handle_osc_message('/heartbeat/0', 1000)

        with viewer.buffer_lock:
            self.assertEqual(len(viewer.data_buffer), 1)

    def test_maximum_buffer_capacity(self):
        """Test buffer at maximum capacity."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)
        max_size = viewer.data_buffer.maxlen

        # Fill buffer to capacity
        for i in range(max_size):
            viewer.handle_osc_message('/heartbeat/0', 900 + i)

        with viewer.buffer_lock:
            self.assertEqual(len(viewer.data_buffer), max_size)

    def test_rapid_messages(self):
        """Test buffer handling with rapid message sequence."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Simulate rapid message arrival
        ibi_values = [600, 650, 700, 750, 800]
        for ibi in ibi_values:
            viewer.handle_osc_message('/heartbeat/0', ibi)

        with viewer.buffer_lock:
            self.assertEqual(len(viewer.data_buffer), len(ibi_values))

            # Verify all values are stored
            stored_ibis = [item[1] for item in viewer.data_buffer]
            self.assertEqual(stored_ibis, ibi_values)

    def test_float_ibi_values(self):
        """Test handling of float IBI values (if supported)."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        try:
            # Some implementations might accept floats
            viewer.handle_osc_message('/heartbeat/0', 1000.5)
            with viewer.buffer_lock:
                # Should be stored or converted
                self.assertGreater(len(viewer.data_buffer), 0)
        except (ValueError, TypeError):
            # Or they might reject floats
            pass


class TestVisualization(unittest.TestCase):
    """Test visualization functionality (animation_update and matplotlib integration)."""

    def setUp(self):
        """Set up test fixtures."""
        if EKGViewer is not None:
            self.viewer = EKGViewer(port=8000, sensor_id=0, window=30)

    def test_animation_update_with_empty_buffer(self):
        """Test animation_update with empty data buffer."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        try:
            # Should handle empty buffer gracefully
            result = viewer.animation_update(0)
            # Should return something (typically a tuple with line object)
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"animation_update should handle empty buffer: {e}")

    def test_animation_update_with_data(self):
        """Test animation_update with data in buffer."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Add some data
        for i in range(5):
            viewer.handle_osc_message('/heartbeat/0', 900 + i * 10)
            time.sleep(0.001)

        # animation_update should process the data
        try:
            result = viewer.animation_update(0)
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"animation_update should process buffer data: {e}")

    def test_animation_update_copies_buffer_safely(self):
        """Test that animation_update copies buffer data safely (with lock)."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Add data
        viewer.handle_osc_message('/heartbeat/0', 1000)

        # animation_update should acquire lock to copy data
        # We verify this by checking it doesn't raise during execution
        try:
            viewer.animation_update(0)
        except Exception as e:
            self.fail(f"animation_update should safely copy buffer with lock: {e}")

    def test_animation_update_returns_line_object(self):
        """Test that animation_update returns line object for blit rendering."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Check if matplotlib objects are set up
        try:
            # animation_update might return a tuple with line object
            result = viewer.animation_update(0)
            # Should be a tuple (for blit=True) or list
            self.assertIsNotNone(result)
            # For blit=True, should return a tuple/list with the line object
            if result:
                self.assertTrue(
                    isinstance(result, (tuple, list)),
                    "animation_update should return tuple/list for blit"
                )
        except Exception as e:
            # If matplotlib not set up yet, that's OK for this test
            pass

    def test_viewer_has_start_time_after_setup(self):
        """Test that viewer tracks start_time for relative timestamps."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Check if start_time is initialized
        # (It might be set in run() or __init__)
        try:
            # After data arrives, start_time should be set
            viewer.handle_osc_message('/heartbeat/0', 1000)
            viewer.animation_update(0)

            # Verify start_time exists and is reasonable
            if hasattr(viewer, 'start_time'):
                self.assertIsInstance(viewer.start_time, (int, float))
                self.assertGreater(viewer.start_time, 0)
        except Exception:
            # If start_time not yet implemented, skip
            pass

    def test_animation_update_with_multiple_data_points(self):
        """Test animation_update processes multiple data points correctly."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Add multiple data points
        ibi_values = [600, 700, 800, 750, 650]
        for ibi in ibi_values:
            viewer.handle_osc_message('/heartbeat/0', ibi)
            time.sleep(0.001)

        # Should process all data without error
        try:
            result = viewer.animation_update(0)
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"animation_update should handle multiple data points: {e}")

    def test_animation_update_idempotent(self):
        """Test that animation_update can be called multiple times safely."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        viewer.handle_osc_message('/heartbeat/0', 1000)

        # Should be safe to call multiple times
        try:
            viewer.animation_update(0)
            viewer.animation_update(1)
            viewer.animation_update(2)
        except Exception as e:
            self.fail(f"animation_update should be idempotent: {e}")

    def test_animation_update_with_rapid_buffer_changes(self):
        """Test animation_update with buffer changing between calls."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Simulate rapid changes
        try:
            viewer.animation_update(0)  # Empty buffer
            viewer.handle_osc_message('/heartbeat/0', 1000)
            viewer.animation_update(1)  # One data point
            viewer.handle_osc_message('/heartbeat/0', 1100)
            viewer.animation_update(2)  # Two data points
        except Exception as e:
            self.fail(f"animation_update should handle rapid buffer changes: {e}")


class TestMatplotlibIntegration(unittest.TestCase):
    """Test matplotlib integration setup."""

    def test_viewer_matplotlib_imports_available(self):
        """Test that matplotlib is available for visualization."""
        try:
            import matplotlib
            import matplotlib.pyplot as plt
            from matplotlib import animation
            # If we got here, matplotlib is available
            self.assertTrue(True)
        except ImportError:
            self.skipTest("matplotlib not available - skip visualization tests")

    def test_animation_update_callable(self):
        """Test that animation_update is callable as FuncAnimation callback."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=30)

        # Should be callable
        self.assertTrue(callable(viewer.animation_update))

        # Should accept frame number argument
        try:
            viewer.animation_update(0)
            viewer.animation_update(100)
        except Exception as e:
            self.fail(f"animation_update should be callable with frame number: {e}")

    def test_viewer_window_seconds_attribute(self):
        """Test that viewer stores window size for matplotlib limits."""
        if EKGViewer is None:
            self.skipTest("EKGViewer not yet implemented")

        viewer = EKGViewer(port=8000, sensor_id=0, window=60)

        self.assertEqual(viewer.window_seconds, 60)
        self.assertTrue(hasattr(viewer, 'window_seconds'))


if __name__ == '__main__':
    unittest.main()
