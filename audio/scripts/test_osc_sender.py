#!/usr/bin/env python3
"""
Test suite for test-osc-sender.py
Tests requirements R33-R40 from phase1-trd.md

Run with: python3 -m pytest test_osc_sender.py -v
Or: python3 test_osc_sender.py
"""

import sys
import threading
import time
import unittest
from io import StringIO
from unittest.mock import Mock, MagicMock, patch, call
import importlib.util

# Import the module under test (use relative path for portability)
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(script_dir, "test-osc-sender.py")
spec = importlib.util.spec_from_file_location(
    "test_osc_sender_module",
    script_path
)
osc_sender = importlib.util.module_from_spec(spec)
spec.loader.exec_module(osc_sender)


class TestOSCSenderArguments(unittest.TestCase):
    """Test command-line argument parsing (R33)"""

    def test_r33_accepts_port_argument(self):
        """R33: Should accept --port <int> argument"""
        args = osc_sender.parse_arguments(['--port', '8000'])
        self.assertEqual(args.port, 8000)

    def test_r33_accepts_sensors_argument(self):
        """R33: Should accept --sensors <int> argument"""
        args = osc_sender.parse_arguments(['--port', '8000', '--sensors', '4'])
        self.assertEqual(args.sensors, 4)

    def test_r33_default_sensors_value(self):
        """R33: Should default to 1 sensor"""
        args = osc_sender.parse_arguments(['--port', '8000'])
        self.assertEqual(args.sensors, 1)

    def test_validate_port_range(self):
        """Port should be in valid range 1-65535"""
        args = Mock(port=8000, sensors=1)
        is_valid, _ = osc_sender.validate_arguments(args)
        self.assertTrue(is_valid)

        args = Mock(port=0, sensors=1)
        is_valid, _ = osc_sender.validate_arguments(args)
        self.assertFalse(is_valid)

        args = Mock(port=65536, sensors=1)
        is_valid, _ = osc_sender.validate_arguments(args)
        self.assertFalse(is_valid)

    def test_validate_sensors_positive(self):
        """Sensor count should be positive"""
        args = Mock(port=8000, sensors=1)
        is_valid, _ = osc_sender.validate_arguments(args)
        self.assertTrue(is_valid)

        args = Mock(port=8000, sensors=0)
        is_valid, _ = osc_sender.validate_arguments(args)
        self.assertFalse(is_valid)


class TestIBIGeneration(unittest.TestCase):
    """Test IBI value generation (R36)"""

    def test_r36_random_base_ibi_in_valid_range(self):
        """R36: Base IBI should be in range 600-1200ms"""
        for _ in range(100):
            ibi = osc_sender.random_base_ibi()
            self.assertGreaterEqual(ibi, 600)
            self.assertLessEqual(ibi, 1200)

    def test_r36_variation_per_beat(self):
        """R36: Each beat should have ±10% variation"""
        base_ibi = 900
        # Test multiple times to check variance is applied
        results = []
        for _ in range(100):
            ibi = osc_sender.generate_ibi_with_variance(base_ibi)
            results.append(ibi)
            # Should be within ±10% of base
            min_expected = int(base_ibi * 0.9)
            max_expected = int(base_ibi * 1.1)
            self.assertGreaterEqual(ibi, min_expected)
            self.assertLessEqual(ibi, max_expected)

        # Verify that we get variation (not all the same)
        self.assertGreater(len(set(results)), 10, "IBI values should vary")

    def test_ibi_generation_randomness(self):
        """IBI values should vary (not constant)"""
        results = []
        for _ in range(50):
            ibi = osc_sender.generate_ibi()
            results.append(ibi)

        # Should have variation
        self.assertGreater(len(set(results)), 10, "Generated IBI values should vary")

    def test_generated_ibi_reasonable_range(self):
        """Generated IBI should be in reasonable range considering variance"""
        # Min possible: 600 * 0.9 = 540
        # Max possible: 1200 * 1.1 = 1320
        for _ in range(100):
            ibi = osc_sender.generate_ibi()
            self.assertGreaterEqual(ibi, 540)
            self.assertLessEqual(ibi, 1320)


class TestOutputFormat(unittest.TestCase):
    """Test print output format (R38)"""

    @patch('sys.stdout', new_callable=StringIO)
    def test_r38_message_format(self, mock_stdout):
        """R38: Should print 'Sent /heartbeat/N <ibi>'"""
        osc_sender.print_message(0, 847, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Sent /heartbeat/0 847", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_r38_multiple_sensors(self, mock_stdout):
        """R38: Should print correct format for different sensors"""
        osc_sender.print_message(3, 691, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Sent /heartbeat/3 691", output)


class TestStatistics(unittest.TestCase):
    """Test statistics formatting"""

    def test_format_final_statistics(self):
        """Statistics should include all sensor counts"""
        counts = {0: 10, 1: 15, 2: 12, 3: 8}
        stats = osc_sender.format_final_statistics(counts)

        self.assertIn("sensor_0=10", stats)
        self.assertIn("sensor_1=15", stats)
        self.assertIn("sensor_2=12", stats)
        self.assertIn("sensor_3=8", stats)
        self.assertIn("total=45", stats)


class TestSensorThread(unittest.TestCase):
    """Test sensor thread behavior"""

    def setUp(self):
        """Reset global state before each test"""
        osc_sender.sensor_message_counts.clear()
        osc_sender.shutdown_event.clear()

    def tearDown(self):
        """Ensure shutdown after each test"""
        osc_sender.shutdown_event.set()
        time.sleep(0.1)  # Allow threads to finish

    @patch('pythonosc.udp_client.SimpleUDPClient')
    @patch('sys.stdout', new_callable=StringIO)
    def test_r34_r35_sends_correct_address(self, mock_stdout, mock_client_class):
        """R34, R35: Should send to 127.0.0.1:<port> with /heartbeat/N address"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Start thread for sensor 0
        thread = threading.Thread(
            target=osc_sender.sensor_thread,
            args=(0, "127.0.0.1", 8000)
        )
        thread.daemon = True
        thread.start()

        # Wait for at least one message
        time.sleep(0.1)
        osc_sender.shutdown_event.set()
        thread.join(timeout=2.0)

        # Verify OSC client was created with correct parameters (R34)
        mock_client_class.assert_called_once_with("127.0.0.1", 8000)

        # Verify send_message was called with correct address pattern (R35)
        self.assertGreater(mock_client.send_message.call_count, 0)
        first_call = mock_client.send_message.call_args_list[0]
        address, ibi = first_call[0]
        self.assertEqual(address, "/heartbeat/0")
        self.assertIsInstance(ibi, int)

    @patch('pythonosc.udp_client.SimpleUDPClient')
    def test_r37_independent_timing(self, mock_client_class):
        """R37: Multiple sensors should send independently"""
        mock_client_class.return_value = MagicMock()

        # Start two sensor threads
        threads = []
        for sensor_id in range(2):
            thread = threading.Thread(
                target=osc_sender.sensor_thread,
                args=(sensor_id, "127.0.0.1", 8000)
            )
            thread.daemon = True
            threads.append(thread)
            thread.start()

        # Let them run briefly
        time.sleep(1.5)
        osc_sender.shutdown_event.set()

        for thread in threads:
            thread.join(timeout=2.0)

        # Both sensors should have sent messages
        self.assertIn(0, osc_sender.sensor_message_counts)
        self.assertIn(1, osc_sender.sensor_message_counts)
        self.assertGreater(osc_sender.sensor_message_counts[0], 0)
        self.assertGreater(osc_sender.sensor_message_counts[1], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests"""

    def setUp(self):
        """Reset global state"""
        osc_sender.sensor_message_counts.clear()
        osc_sender.shutdown_event.clear()

    def tearDown(self):
        """Ensure cleanup"""
        osc_sender.shutdown_event.set()
        time.sleep(0.1)

    @patch('pythonosc.udp_client.SimpleUDPClient')
    def test_r39_shutdown_event_stops_threads(self, mock_client_class):
        """R39: Setting shutdown event should stop sensor threads"""
        mock_client_class.return_value = MagicMock()

        thread = threading.Thread(
            target=osc_sender.sensor_thread,
            args=(0, "127.0.0.1", 8000)
        )
        thread.daemon = True
        thread.start()

        # Let it run briefly
        time.sleep(0.2)

        # Signal shutdown
        osc_sender.shutdown_event.set()

        # Thread should exit
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive(), "Thread should stop after shutdown event")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
