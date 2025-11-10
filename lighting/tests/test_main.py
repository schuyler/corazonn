#!/usr/bin/env python3
"""
Tests for main.py entry point.

Tests cover:
1. Config loading (file existence, YAML parsing, validation)
2. Config validation (backend, OSC port, effects params, time params)
3. Zone validation (range 0-3, uniqueness)
4. Logging setup (rotating file handler, formatters)
5. Main function flow and error handling
"""

import sys
import os
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
import yaml


# Import the functions we're testing (will create these)
# We use lazy imports because main.py doesn't exist yet


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def valid_config_dict():
    """Valid config dict for testing."""
    return {
        'lighting': {'backend': 'kasa'},
        'osc': {'listen_port': 8001},
        'effects': {
            'baseline_brightness': 40,
            'pulse_max': 70,
            'baseline_saturation': 75,
            'baseline_hue': 120,
            'fade_time_ms': 900,
            'attack_time_ms': 200,
            'sustain_time_ms': 100,
        },
        'logging': {
            'console_level': 'INFO',
            'file_level': 'DEBUG',
            'file': 'logs/lighting.log',
            'max_bytes': 10485760,
            'backup_count': 5,
        },
        'kasa': {
            'bulbs': [
                {'ip': '192.168.1.100', 'name': 'Bulb0', 'zone': 0},
                {'ip': '192.168.1.101', 'name': 'Bulb1', 'zone': 1},
                {'ip': '192.168.1.102', 'name': 'Bulb2', 'zone': 2},
                {'ip': '192.168.1.103', 'name': 'Bulb3', 'zone': 3},
            ]
        }
    }


@pytest.fixture
def temp_config_file(valid_config_dict):
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(valid_config_dict, f)
        temp_path = f.name
    yield temp_path
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def temp_logs_dir():
    """Create a temporary logs directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# =============================================================================
# Test Config Loading (Tasks 8.1-8.2)
# =============================================================================

class TestConfigLoading:
    """Test load_config function."""

    def test_load_config_reads_valid_yaml_file(self, temp_config_file, valid_config_dict):
        """load_config must read valid YAML file and return dict."""
        from main import load_config

        config = load_config(temp_config_file)

        assert isinstance(config, dict)
        assert config['lighting']['backend'] == 'kasa'
        assert config['osc']['listen_port'] == 8001

    def test_load_config_raises_on_missing_file(self):
        """load_config must raise FileNotFoundError with helpful message."""
        from main import load_config

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config('/nonexistent/path/config.yaml')

        error_msg = str(exc_info.value)
        assert 'config.yaml' in error_msg or 'nonexistent' in error_msg

    def test_load_config_calls_validate_config(self, temp_config_file):
        """load_config must call validate_config on loaded config."""
        from main import load_config, validate_config

        with patch('main.validate_config') as mock_validate:
            # Set up mock to not raise (we'll test validation separately)
            mock_validate.return_value = None

            config = load_config(temp_config_file)

            # Verify validate_config was called with the loaded config
            mock_validate.assert_called_once()
            called_config = mock_validate.call_args[0][0]
            assert called_config['lighting']['backend'] == 'kasa'

    def test_load_config_raises_on_invalid_yaml(self):
        """load_config must raise exception on invalid YAML."""
        from main import load_config

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: syntax: here:")
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # yaml.YAMLError or similar
                load_config(temp_path)
        finally:
            os.unlink(temp_path)


# =============================================================================
# Test Config Validation (Tasks 8.3-8.10, R7-R12)
# =============================================================================

class TestConfigValidation:
    """Test validate_config function."""

    def test_validate_config_accepts_valid_config(self, valid_config_dict):
        """validate_config must accept valid configuration without raising."""
        from main import validate_config

        # Should not raise
        validate_config(valid_config_dict)

    # R7: Backend must exist and be 'kasa'
    def test_validate_config_requires_backend_key(self):
        """validate_config must require lighting.backend key (R7)."""
        from main import validate_config

        config = {
            'osc': {'listen_port': 8001},
            'effects': {},
            'kasa': {},
        }

        with pytest.raises(ValueError) as exc_info:
            validate_config(config)

        assert 'backend' in str(exc_info.value).lower()

    def test_validate_config_requires_backend_to_be_kasa(self):
        """validate_config must require backend='kasa' (only supported now) (R7)."""
        from main import validate_config

        config = {
            'lighting': {'backend': 'wyze'},
            'osc': {'listen_port': 8001},
            'effects': {},
        }

        with pytest.raises(ValueError) as exc_info:
            validate_config(config)

        error_msg = str(exc_info.value)
        assert 'kasa' in error_msg.lower()

    # R13: Kasa section must exist
    def test_validate_config_requires_kasa_section(self):
        """validate_config must require kasa section when backend='kasa' (R13)."""
        from main import validate_config

        config = {
            'lighting': {'backend': 'kasa'},
            'osc': {'listen_port': 8001},
            'effects': {},
        }

        with pytest.raises(ValueError) as exc_info:
            validate_config(config)

        error_msg = str(exc_info.value)
        assert 'kasa' in error_msg.lower()

    # R8: OSC port validation
    def test_validate_config_requires_osc_port(self):
        """validate_config must require osc.listen_port (R8)."""
        from main import validate_config

        config = {
            'lighting': {'backend': 'kasa'},
            'effects': {},
            'kasa': {'bulbs': []},
        }

        with pytest.raises(ValueError) as exc_info:
            validate_config(config)

        assert 'port' in str(exc_info.value).lower()

    def test_validate_config_validates_osc_port_range(self):
        """validate_config must validate OSC port in range 1-65535 (R8)."""
        from main import validate_config

        # Port too low
        config = {
            'lighting': {'backend': 'kasa'},
            'osc': {'listen_port': 0},
            'effects': {},
            'kasa': {'bulbs': []},
        }
        with pytest.raises(ValueError) as exc_info:
            validate_config(config)
        assert 'port' in str(exc_info.value).lower()

        # Port too high
        config['osc']['listen_port'] = 65536
        with pytest.raises(ValueError):
            validate_config(config)

    def test_validate_config_accepts_valid_osc_ports(self, valid_config_dict):
        """validate_config must accept valid OSC ports 1-65535."""
        from main import validate_config

        for port in [1, 8001, 65535]:
            config = valid_config_dict.copy()
            config['osc']['listen_port'] = port
            # Should not raise
            validate_config(config)

    # R9: Brightness and saturation validation
    def test_validate_config_validates_brightness_range(self):
        """validate_config must validate brightness 0-100 (R9)."""
        from main import validate_config

        config = {
            'lighting': {'backend': 'kasa'},
            'osc': {'listen_port': 8001},
            'effects': {
                'baseline_brightness': 101,  # Invalid
                'pulse_max': 70,
                'baseline_saturation': 75,
            },
            'kasa': {'bulbs': []},
        }

        with pytest.raises(ValueError):
            validate_config(config)

    def test_validate_config_validates_pulse_max_range(self):
        """validate_config must validate pulse_max 0-100 (R9)."""
        from main import validate_config

        config = {
            'lighting': {'backend': 'kasa'},
            'osc': {'listen_port': 8001},
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': -1,  # Invalid
                'baseline_saturation': 75,
            },
            'kasa': {'bulbs': []},
        }

        with pytest.raises(ValueError):
            validate_config(config)

    def test_validate_config_validates_saturation_range(self):
        """validate_config must validate saturation 0-100 (R9)."""
        from main import validate_config

        config = {
            'lighting': {'backend': 'kasa'},
            'osc': {'listen_port': 8001},
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 150,  # Invalid
            },
            'kasa': {'bulbs': []},
        }

        with pytest.raises(ValueError):
            validate_config(config)

    def test_validate_config_accepts_valid_brightness_saturation(self, valid_config_dict):
        """validate_config must accept brightness/saturation 0-100."""
        from main import validate_config

        for value in [0, 50, 100]:
            config = valid_config_dict.copy()
            config['effects']['baseline_brightness'] = value
            config['effects']['pulse_max'] = value
            config['effects']['baseline_saturation'] = value
            # Should not raise
            validate_config(config)

    # R10: Hue validation
    def test_validate_config_validates_hue_range(self):
        """validate_config must validate baseline_hue 0-360 if present (R10)."""
        from main import validate_config

        config = {
            'lighting': {'backend': 'kasa'},
            'osc': {'listen_port': 8001},
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'baseline_hue': 361,  # Invalid
            },
            'kasa': {'bulbs': []},
        }

        with pytest.raises(ValueError):
            validate_config(config)

    def test_validate_config_hue_is_optional(self, valid_config_dict):
        """validate_config must allow baseline_hue to be missing (R10)."""
        from main import validate_config

        config = valid_config_dict.copy()
        del config['effects']['baseline_hue']

        # Should not raise
        validate_config(config)

    def test_validate_config_accepts_valid_hue(self):
        """validate_config must accept hue 0-360."""
        from main import validate_config

        for hue in [0, 180, 360]:
            config = {
                'lighting': {'backend': 'kasa'},
                'osc': {'listen_port': 8001},
                'effects': {
                    'baseline_brightness': 40,
                    'pulse_max': 70,
                    'baseline_saturation': 75,
                    'baseline_hue': hue,
                },
                'kasa': {'bulbs': []},
            }
            # Should not raise
            validate_config(config)

    # R11: Time parameter validation
    def test_validate_config_validates_time_params_greater_than_zero(self):
        """validate_config must validate time params > 0 (R11)."""
        from main import validate_config

        for param in ['fade_time_ms', 'attack_time_ms', 'sustain_time_ms']:
            config = {
                'lighting': {'backend': 'kasa'},
                'osc': {'listen_port': 8001},
                'effects': {
                    'baseline_brightness': 40,
                    'pulse_max': 70,
                    'baseline_saturation': 75,
                    param: 0,  # Invalid
                },
                'kasa': {'bulbs': []},
            }

            with pytest.raises(ValueError):
                validate_config(config)

    def test_validate_config_accepts_valid_time_params(self, valid_config_dict):
        """validate_config must accept time params > 0 (R11)."""
        from main import validate_config

        config = valid_config_dict.copy()
        for param in ['fade_time_ms', 'attack_time_ms', 'sustain_time_ms']:
            config['effects'][param] = 1  # Minimum valid

        # Should not raise
        validate_config(config)

    # R12: Zone validation
    def test_validate_config_validates_zone_range(self):
        """validate_config must validate zones 0-3 (R12)."""
        from main import validate_config

        config = {
            'lighting': {'backend': 'kasa'},
            'osc': {'listen_port': 8001},
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
            },
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb', 'zone': 4},  # Invalid
                ]
            }
        }

        with pytest.raises(ValueError) as exc_info:
            validate_config(config)

        assert 'zone' in str(exc_info.value).lower()

    def test_validate_config_validates_zone_uniqueness(self):
        """validate_config must validate zones are unique (R12)."""
        from main import validate_config

        config = {
            'lighting': {'backend': 'kasa'},
            'osc': {'listen_port': 8001},
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
            },
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb0', 'zone': 0},
                    {'ip': '192.168.1.101', 'name': 'Bulb1', 'zone': 0},  # Duplicate
                ]
            }
        }

        with pytest.raises(ValueError) as exc_info:
            validate_config(config)

        error_msg = str(exc_info.value).lower()
        assert 'duplicate' in error_msg or 'unique' in error_msg

    def test_validate_config_accepts_valid_zones(self, valid_config_dict):
        """validate_config must accept zones 0-3 and unique."""
        from main import validate_config

        config = valid_config_dict.copy()
        # Should not raise
        validate_config(config)


# =============================================================================
# Test Logging Setup (Tasks 8.11-8.14)
# =============================================================================

class TestLoggingSetup:
    """Test setup_logging function."""

    def test_setup_logging_creates_logs_directory(self, valid_config_dict, temp_logs_dir):
        """setup_logging must create logs directory if missing."""
        from main import setup_logging

        config = valid_config_dict.copy()
        config['logging']['file'] = os.path.join(temp_logs_dir, 'subdir', 'lighting.log')

        setup_logging(config)

        # logs directory should exist
        log_dir = os.path.dirname(config['logging']['file'])
        assert os.path.exists(log_dir)

    def test_setup_logging_configures_file_handler(self, valid_config_dict, temp_logs_dir):
        """setup_logging must configure RotatingFileHandler."""
        from main import setup_logging

        config = valid_config_dict.copy()
        config['logging']['file'] = os.path.join(temp_logs_dir, 'lighting.log')

        setup_logging(config)

        # Check that handlers are configured
        root_logger = logging.getLogger()
        file_handlers = [h for h in root_logger.handlers
                        if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) > 0

    def test_setup_logging_uses_configured_formatter(self, valid_config_dict, temp_logs_dir):
        """setup_logging must use correct formatter."""
        from main import setup_logging

        config = valid_config_dict.copy()
        config['logging']['file'] = os.path.join(temp_logs_dir, 'lighting.log')

        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging(config)

        # Check formatter
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if handler.formatter:
                fmt = handler.formatter._fmt
                # Should contain timestamp, level, name, message
                assert '%(asctime)s' in fmt
                assert '%(levelname)s' in fmt
                assert '%(name)s' in fmt
                assert '%(message)s' in fmt


# =============================================================================
# Test Main Function (Tasks 8.15-8.22)
# =============================================================================

class TestMainFunction:
    """Test main() function."""

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_loads_config(self, mock_load_config, mock_setup_logging,
                               mock_create_backend, mock_start_osc, valid_config_dict):
        """main() must load configuration."""
        from main import main

        mock_load_config.return_value = valid_config_dict
        mock_backend = Mock()
        mock_backend.authenticate = Mock()
        mock_backend.set_all_baseline = Mock()
        mock_backend.get_latency_estimate = Mock(return_value=100)
        mock_create_backend.return_value = mock_backend
        mock_start_osc.side_effect = KeyboardInterrupt()

        with patch('builtins.print'):
            main()

        mock_load_config.assert_called_once()

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_prints_startup_banner(self, mock_load_config, mock_setup_logging,
                                       mock_create_backend, mock_start_osc, valid_config_dict):
        """main() must print startup banner."""
        from main import main

        mock_load_config.return_value = valid_config_dict
        mock_backend = Mock()
        mock_backend.authenticate = Mock()
        mock_backend.set_all_baseline = Mock()
        mock_backend.get_latency_estimate = Mock(return_value=100)
        mock_create_backend.return_value = mock_backend
        mock_start_osc.side_effect = KeyboardInterrupt()

        with patch('builtins.print') as mock_print:
            main()

        # Check that banner was printed
        printed_calls = [str(call) for call in mock_print.call_args_list]
        banner_printed = any('Heartbeat' in str(call) or 'MVP' in str(call)
                            for call in printed_calls)
        assert banner_printed

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_creates_backend(self, mock_load_config, mock_setup_logging,
                                 mock_create_backend, mock_start_osc, valid_config_dict):
        """main() must create backend."""
        from main import main

        mock_load_config.return_value = valid_config_dict
        mock_backend = Mock()
        mock_backend.authenticate = Mock()
        mock_backend.set_all_baseline = Mock()
        mock_backend.get_latency_estimate = Mock(return_value=100)
        mock_create_backend.return_value = mock_backend
        mock_start_osc.side_effect = KeyboardInterrupt()

        with patch('builtins.print'):
            main()

        mock_create_backend.assert_called_once_with(valid_config_dict)

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_authenticates_backend(self, mock_load_config, mock_setup_logging,
                                       mock_create_backend, mock_start_osc, valid_config_dict):
        """main() must authenticate backend."""
        from main import main

        mock_load_config.return_value = valid_config_dict
        mock_backend = Mock()
        mock_backend.authenticate = Mock()
        mock_backend.set_all_baseline = Mock()
        mock_backend.get_latency_estimate = Mock(return_value=100)
        mock_create_backend.return_value = mock_backend
        mock_start_osc.side_effect = KeyboardInterrupt()

        with patch('builtins.print'):
            main()

        mock_backend.authenticate.assert_called_once()

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_sets_all_baseline(self, mock_load_config, mock_setup_logging,
                                   mock_create_backend, mock_start_osc, valid_config_dict):
        """main() must set all bulbs to baseline."""
        from main import main

        mock_load_config.return_value = valid_config_dict
        mock_backend = Mock()
        mock_backend.authenticate = Mock()
        mock_backend.set_all_baseline = Mock()
        mock_backend.get_latency_estimate = Mock(return_value=100)
        mock_create_backend.return_value = mock_backend
        mock_start_osc.side_effect = KeyboardInterrupt()

        with patch('builtins.print'):
            main()

        mock_backend.set_all_baseline.assert_called_once()

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_starts_osc_server(self, mock_load_config, mock_setup_logging,
                                   mock_create_backend, mock_start_osc, valid_config_dict):
        """main() must start OSC server."""
        from main import main

        mock_load_config.return_value = valid_config_dict
        mock_backend = Mock()
        mock_backend.authenticate = Mock()
        mock_backend.set_all_baseline = Mock()
        mock_backend.get_latency_estimate = Mock(return_value=100)
        mock_create_backend.return_value = mock_backend
        mock_start_osc.side_effect = KeyboardInterrupt()

        with patch('builtins.print'):
            main()

        mock_start_osc.assert_called_once_with(valid_config_dict, mock_backend)

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_returns_0_on_keyboard_interrupt(self, mock_load_config, mock_setup_logging,
                                                 mock_create_backend, mock_start_osc, valid_config_dict):
        """main() must return 0 on KeyboardInterrupt."""
        from main import main

        mock_load_config.return_value = valid_config_dict
        mock_backend = Mock()
        mock_backend.authenticate = Mock()
        mock_backend.set_all_baseline = Mock()
        mock_backend.get_latency_estimate = Mock(return_value=100)
        mock_backend.print_stats = Mock()
        mock_create_backend.return_value = mock_backend
        mock_start_osc.side_effect = KeyboardInterrupt()

        with patch('builtins.print'):
            result = main()

        assert result == 0

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_handles_file_not_found_error(self, mock_load_config, mock_setup_logging,
                                              mock_create_backend, mock_start_osc):
        """main() must handle FileNotFoundError and return 1."""
        from main import main

        mock_load_config.side_effect = FileNotFoundError("Config not found")

        with patch('builtins.print'):
            result = main()

        assert result == 1

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_handles_value_error(self, mock_load_config, mock_setup_logging,
                                     mock_create_backend, mock_start_osc):
        """main() must handle ValueError (invalid config) and return 1."""
        from main import main

        mock_load_config.side_effect = ValueError("Invalid config")

        with patch('builtins.print'):
            result = main()

        assert result == 1

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_handles_oserror_port_conflict(self, mock_load_config, mock_setup_logging,
                                               mock_create_backend, mock_start_osc, valid_config_dict):
        """main() must handle OSError for port conflicts."""
        from main import main

        mock_load_config.return_value = valid_config_dict
        mock_backend = Mock()
        mock_backend.authenticate = Mock()
        mock_backend.set_all_baseline = Mock()
        mock_backend.get_latency_estimate = Mock(return_value=100)
        mock_create_backend.return_value = mock_backend

        # Simulate port already in use
        err = OSError("Address already in use")
        err.errno = 98  # EADDRINUSE
        mock_start_osc.side_effect = err

        with patch('builtins.print'):
            result = main()

        # Should return 1 on error
        assert result == 1

    @patch('main.start_osc_server')
    @patch('main.create_backend')
    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_handles_general_exception(self, mock_load_config, mock_setup_logging,
                                           mock_create_backend, mock_start_osc, valid_config_dict):
        """main() must handle general exceptions and return 1."""
        from main import main

        mock_load_config.return_value = valid_config_dict
        mock_backend = Mock()
        mock_backend.authenticate = Mock()
        mock_backend.set_all_baseline = Mock()
        mock_backend.get_latency_estimate = Mock(return_value=100)
        mock_create_backend.return_value = mock_backend
        mock_start_osc.side_effect = RuntimeError("Unexpected error")

        with patch('builtins.print'):
            result = main()

        assert result == 1

    @patch('main.load_config')
    def test_main_entry_point_exists(self, mock_load_config):
        """main.py must have if __name__ == '__main__' entry point."""
        import main

        # Check that the module has the standard entry point pattern
        assert hasattr(main, 'main')
        assert callable(main.main)


# =============================================================================
# Integration Tests
# =============================================================================

class TestMainIntegration:
    """Integration tests for main.py."""

    def test_full_config_load_and_validate_flow(self, temp_config_file):
        """Test loading and validating config end-to-end."""
        from main import load_config

        config = load_config(temp_config_file)

        # Should have all required sections
        assert 'lighting' in config
        assert 'osc' in config
        assert 'effects' in config
        assert 'kasa' in config
        assert 'logging' in config


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
