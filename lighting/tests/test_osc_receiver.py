#!/usr/bin/env python3
"""Test suite for OSC receiver module.

Tests for:
1. handle_pulse() - OSC message parsing and validation
2. start_osc_server() - OSC server initialization
3. Integration with backends
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from osc_receiver import bpm_to_hue, handle_pulse, start_osc_server
from backends.base import LightingBackend


# =============================================================================
# Tests for handle_pulse() Function
# =============================================================================

class TestHandlePulse:
    """Tests for handle_pulse() message handler."""

    def test_handle_pulse_valid_ibi_in_range(self):
        """Valid IBI (300-3000ms) should call backend.pulse()."""
        # Create mock backend
        backend = Mock(spec=LightingBackend)
        backend.get_bulb_for_zone.return_value = 'bulb_192.168.1.100'

        config = {'osc': {'listen_port': 8001}}

        # Test with IBI = 500ms
        # BPM = 60000 / 500 = 120
        # hue = bpm_to_hue(120) = 0
        handle_pulse('/light/1/pulse', 500, backend, config)

        backend.get_bulb_for_zone.assert_called_once_with(1)
        backend.pulse.assert_called_once_with('bulb_192.168.1.100', 0, 1)

    def test_handle_pulse_calculates_correct_bpm(self):
        """Should correctly calculate BPM from IBI."""
        backend = Mock(spec=LightingBackend)
        backend.get_bulb_for_zone.return_value = 'bulb_test'

        config = {'osc': {'listen_port': 8001}}

        # IBI = 600ms => BPM = 60000 / 600 = 100
        # hue = bpm_to_hue(100) = 60
        handle_pulse('/light/0/pulse', 600, backend, config)

        backend.pulse.assert_called_once()
        # Verify hue is 60 (from bpm_to_hue(100))
        call_args = backend.pulse.call_args
        assert call_args[0][1] == 60  # hue argument

    def test_handle_pulse_ibi_below_minimum(self):
        """IBI below 300ms should log warning and return."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.logger') as mock_logger:
            handle_pulse('/light/2/pulse', 200, backend, config)

            # Should log warning about invalid IBI
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert 'IBI' in warning_msg or 'invalid' in warning_msg.lower()

        # Backend should NOT be called
        backend.pulse.assert_not_called()

    def test_handle_pulse_ibi_above_maximum(self):
        """IBI above 3000ms should log warning and return."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.logger') as mock_logger:
            handle_pulse('/light/3/pulse', 3500, backend, config)

            # Should log warning about invalid IBI
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert 'IBI' in warning_msg or 'invalid' in warning_msg.lower()

        # Backend should NOT be called
        backend.pulse.assert_not_called()

    def test_handle_pulse_ibi_boundary_values(self):
        """Test IBI boundary values (300 and 3000)."""
        backend = Mock(spec=LightingBackend)
        backend.get_bulb_for_zone.return_value = 'bulb_test'
        config = {'osc': {'listen_port': 8001}}

        # Test minimum valid: 300ms
        handle_pulse('/light/0/pulse', 300, backend, config)
        backend.pulse.assert_called_once()
        backend.reset_mock()
        backend.get_bulb_for_zone.return_value = 'bulb_test'

        # Test maximum valid: 3000ms
        handle_pulse('/light/0/pulse', 3000, backend, config)
        backend.pulse.assert_called_once()

    def test_handle_pulse_parses_zone_correctly(self):
        """Should correctly parse zone number from address."""
        backend = Mock(spec=LightingBackend)
        backend.get_bulb_for_zone.return_value = 'bulb_test'
        config = {'osc': {'listen_port': 8001}}

        # Test zone 0
        handle_pulse('/light/0/pulse', 1000, backend, config)
        backend.get_bulb_for_zone.assert_called_with(0)
        backend.reset_mock()
        backend.get_bulb_for_zone.return_value = 'bulb_test'

        # Test zone 3
        handle_pulse('/light/3/pulse', 1000, backend, config)
        backend.get_bulb_for_zone.assert_called_with(3)

    def test_handle_pulse_invalid_address_format(self):
        """Invalid address format should be caught and logged."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.logger') as mock_logger:
            # Invalid format: missing zone
            handle_pulse('/light/pulse', 1000, backend, config)

            # Should log error
            mock_logger.error.assert_called()

        backend.pulse.assert_not_called()

    def test_handle_pulse_exception_handling(self):
        """Any exception should be caught and logged."""
        backend = Mock(spec=LightingBackend)
        backend.get_bulb_for_zone.return_value = 'bulb_test'
        # Make pulse() raise an exception
        backend.pulse.side_effect = Exception('Backend error')

        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.logger') as mock_logger:
            # Should not raise, but log error
            handle_pulse('/light/0/pulse', 1000, backend, config)

            mock_logger.error.assert_called()

    def test_handle_pulse_backend_not_found(self):
        """If zone not configured, should handle gracefully."""
        backend = Mock(spec=LightingBackend)
        backend.get_bulb_for_zone.return_value = None
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.logger') as mock_logger:
            handle_pulse('/light/0/pulse', 1000, backend, config)

            # Should log that bulb not found (or similar)
            # May log as error or warning
            assert mock_logger.warning.called or mock_logger.error.called

    def test_handle_pulse_logs_debug_info(self):
        """Should log debug information about pulse."""
        backend = Mock(spec=LightingBackend)
        backend.get_bulb_for_zone.return_value = 'bulb_test'
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.logger') as mock_logger:
            handle_pulse('/light/0/pulse', 1000, backend, config)

            # Should log debug information
            mock_logger.debug.assert_called()
            debug_msg = str(mock_logger.debug.call_args)
            # Should contain zone, BPM, and/or hue
            assert 'zone' in debug_msg.lower() or \
                   'bpm' in debug_msg.lower() or \
                   'hue' in debug_msg.lower()


# =============================================================================
# Tests for start_osc_server() Function
# =============================================================================

class TestStartOscServer:
    """Tests for start_osc_server() function."""

    def test_start_osc_server_creates_dispatcher(self):
        """Should create a Dispatcher for routing OSC messages."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 8001}}

        # Mock the Dispatcher and server
        with patch('osc_receiver.Dispatcher') as mock_dispatcher_class, \
             patch('osc_receiver.BlockingOSCUDPServer') as mock_server_class:

            mock_dispatcher = MagicMock()
            mock_dispatcher_class.return_value = mock_dispatcher

            # Mock server to not actually run
            mock_server = MagicMock()
            mock_server_class.return_value = mock_server
            mock_server.serve_forever.side_effect = KeyboardInterrupt()

            try:
                start_osc_server(config, backend)
            except KeyboardInterrupt:
                pass

            # Dispatcher should be created
            mock_dispatcher_class.assert_called_once()

    def test_start_osc_server_maps_pulse_handler(self):
        """Should map /light/*/pulse address to handler."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.Dispatcher') as mock_dispatcher_class, \
             patch('osc_receiver.BlockingOSCUDPServer') as mock_server_class:

            mock_dispatcher = MagicMock()
            mock_dispatcher_class.return_value = mock_dispatcher

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server
            mock_server.serve_forever.side_effect = KeyboardInterrupt()

            try:
                start_osc_server(config, backend)
            except KeyboardInterrupt:
                pass

            # dispatcher.map should be called with /light/*/pulse
            mock_dispatcher.map.assert_called_once()
            call_args = mock_dispatcher.map.call_args
            assert call_args[0][0] == '/light/*/pulse'

    def test_start_osc_server_creates_blocking_server(self):
        """Should create BlockingOSCUDPServer with correct address and port."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.Dispatcher') as mock_dispatcher_class, \
             patch('osc_receiver.BlockingOSCUDPServer') as mock_server_class:

            mock_dispatcher = MagicMock()
            mock_dispatcher_class.return_value = mock_dispatcher

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server
            mock_server.serve_forever.side_effect = KeyboardInterrupt()

            try:
                start_osc_server(config, backend)
            except KeyboardInterrupt:
                pass

            # Server should be created with 0.0.0.0 and port from config
            mock_server_class.assert_called_once()
            call_args = mock_server_class.call_args
            # First arg should be address tuple ("0.0.0.0", port)
            assert call_args[0][0] == ("0.0.0.0", 8001)

    def test_start_osc_server_binds_to_all_interfaces(self):
        """Should bind to 0.0.0.0 to listen on all network interfaces."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.Dispatcher') as mock_dispatcher_class, \
             patch('osc_receiver.BlockingOSCUDPServer') as mock_server_class:

            mock_dispatcher = MagicMock()
            mock_dispatcher_class.return_value = mock_dispatcher

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server
            mock_server.serve_forever.side_effect = KeyboardInterrupt()

            try:
                start_osc_server(config, backend)
            except KeyboardInterrupt:
                pass

            # Verify binding to 0.0.0.0
            call_args = mock_server_class.call_args
            address = call_args[0][0]
            assert address[0] == "0.0.0.0"

    def test_start_osc_server_uses_configured_port(self):
        """Should use port from config."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 9999}}

        with patch('osc_receiver.Dispatcher') as mock_dispatcher_class, \
             patch('osc_receiver.BlockingOSCUDPServer') as mock_server_class:

            mock_dispatcher = MagicMock()
            mock_dispatcher_class.return_value = mock_dispatcher

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server
            mock_server.serve_forever.side_effect = KeyboardInterrupt()

            try:
                start_osc_server(config, backend)
            except KeyboardInterrupt:
                pass

            # Verify correct port
            call_args = mock_server_class.call_args
            port = call_args[0][0][1]
            assert port == 9999

    def test_start_osc_server_logs_startup_message(self):
        """Should log message indicating server is listening."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.Dispatcher') as mock_dispatcher_class, \
             patch('osc_receiver.BlockingOSCUDPServer') as mock_server_class, \
             patch('osc_receiver.logger') as mock_logger:

            mock_dispatcher = MagicMock()
            mock_dispatcher_class.return_value = mock_dispatcher

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server
            mock_server.serve_forever.side_effect = KeyboardInterrupt()

            try:
                start_osc_server(config, backend)
            except KeyboardInterrupt:
                pass

            # Should log info about listening
            mock_logger.info.assert_called()
            log_msg = str(mock_logger.info.call_args).lower()
            assert 'listening' in log_msg or '8001' in log_msg

    def test_start_osc_server_calls_serve_forever(self):
        """Should call serve_forever() to start blocking server."""
        backend = Mock(spec=LightingBackend)
        config = {'osc': {'listen_port': 8001}}

        with patch('osc_receiver.Dispatcher') as mock_dispatcher_class, \
             patch('osc_receiver.BlockingOSCUDPServer') as mock_server_class:

            mock_dispatcher = MagicMock()
            mock_dispatcher_class.return_value = mock_dispatcher

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server
            mock_server.serve_forever.side_effect = KeyboardInterrupt()

            try:
                start_osc_server(config, backend)
            except KeyboardInterrupt:
                pass

            # serve_forever should be called
            mock_server.serve_forever.assert_called_once()


# =============================================================================
# Integration Tests
# =============================================================================

class TestOscReceiverIntegration:
    """Integration tests for OSC receiver with backends."""

    def test_osc_receiver_module_imports(self):
        """OSC receiver module should import without errors."""
        # This is already tested by imports at top, but explicit test
        from osc_receiver import bpm_to_hue, handle_pulse, start_osc_server

        assert callable(bpm_to_hue)
        assert callable(handle_pulse)
        assert callable(start_osc_server)

    def test_osc_receiver_no_backend_specific_imports(self):
        """OSC receiver should not import backend-specific modules."""
        # Read the module source and verify no backend-specific imports
        import osc_receiver
        import inspect

        source = inspect.getsource(osc_receiver)

        # Should not import specific backends
        assert 'from backends.kasa_backend' not in source
        assert 'import kasa_backend' not in source
        assert 'from backends.wyze_backend' not in source
        assert 'import wyze_backend' not in source

        # Should only import base
        assert 'from backends.base import LightingBackend' in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
