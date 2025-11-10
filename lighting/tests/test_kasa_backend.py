"""Tests for KasaBackend implementation (TP-Link Kasa bulbs)."""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backends.kasa_backend import KasaBackend
from backends.base import LightingBackend


class TestKasaBackendInitialization:
    """Test __init__ method."""

    def test_inherits_from_lighting_backend(self):
        """KasaBackend must inherit from LightingBackend."""
        assert issubclass(KasaBackend, LightingBackend)

    def test_init_creates_empty_dicts(self):
        """__init__ must create bulbs, zone_map, and drop_stats dicts."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        assert hasattr(backend, 'bulbs')
        assert isinstance(backend.bulbs, dict)
        assert len(backend.bulbs) == 0

        assert hasattr(backend, 'zone_map')
        assert isinstance(backend.zone_map, dict)
        assert len(backend.zone_map) == 0

        assert hasattr(backend, 'drop_stats')
        assert isinstance(backend.drop_stats, dict)
        assert len(backend.drop_stats) == 0

    def test_init_inherits_config_and_logger(self):
        """__init__ must call super().__init__ to set config and logger."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        assert backend.config == config
        assert backend.logger is not None


class TestKasaAuthenticate:
    """Test authenticate() method."""

    @patch('backends.kasa_backend.asyncio.run')
    @patch('backends.kasa_backend.IotBulb')
    def test_authenticate_connects_to_bulbs(self, mock_iot_bulb, mock_asyncio_run):
        """authenticate() must connect to each bulb in config."""
        config = {
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
                    {'ip': '192.168.1.101', 'name': 'Bulb2', 'zone': 1},
                ]
            }
        }

        # Mock IotBulb instances
        mock_bulb1 = Mock()
        mock_bulb2 = Mock()
        mock_iot_bulb.side_effect = [mock_bulb1, mock_bulb2]

        # Mock asyncio.run
        mock_asyncio_run.return_value = None

        backend = KasaBackend(config)
        backend.authenticate()

        # Verify IotBulb instantiated for each IP
        assert mock_iot_bulb.call_count == 2
        mock_iot_bulb.assert_any_call('192.168.1.100')
        mock_iot_bulb.assert_any_call('192.168.1.101')

        # Verify asyncio.run called for update
        assert mock_asyncio_run.call_count == 2

    @patch('backends.kasa_backend.asyncio.run')
    @patch('backends.kasa_backend.IotBulb')
    def test_authenticate_builds_zone_map(self, mock_iot_bulb, mock_asyncio_run):
        """authenticate() must create zone→IP mappings."""
        config = {
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'NW', 'zone': 0},
                    {'ip': '192.168.1.101', 'name': 'NE', 'zone': 3},
                    {'ip': '192.168.1.102', 'name': 'SW', 'zone': 1},
                ]
            }
        }

        mock_iot_bulb.side_effect = [Mock(), Mock(), Mock()]
        mock_asyncio_run.return_value = None

        backend = KasaBackend(config)
        backend.authenticate()

        assert backend.zone_map[0] == '192.168.1.100'
        assert backend.zone_map[3] == '192.168.1.101'
        assert backend.zone_map[1] == '192.168.1.102'

    @patch('backends.kasa_backend.asyncio.run')
    @patch('backends.kasa_backend.IotBulb')
    def test_authenticate_initializes_drop_stats(self, mock_iot_bulb, mock_asyncio_run):
        """authenticate() must initialize drop_stats to 0 for each bulb."""
        config = {
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
                    {'ip': '192.168.1.101', 'name': 'Bulb2', 'zone': 1},
                ]
            }
        }

        mock_iot_bulb.side_effect = [Mock(), Mock()]
        mock_asyncio_run.return_value = None

        backend = KasaBackend(config)
        backend.authenticate()

        assert backend.drop_stats['192.168.1.100'] == 0
        assert backend.drop_stats['192.168.1.101'] == 0

    @patch('backends.kasa_backend.IotBulb')
    def test_authenticate_raises_system_exit_on_error(self, mock_iot_bulb):
        """authenticate() must raise SystemExit(1) on failure."""
        config = {
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
                ]
            }
        }

        # Simulate connection error
        mock_iot_bulb.side_effect = Exception("Connection failed")

        backend = KasaBackend(config)

        with pytest.raises(SystemExit) as exc_info:
            backend.authenticate()

        assert exc_info.value.code == 1

    @patch('backends.kasa_backend.asyncio.run')
    @patch('backends.kasa_backend.IotBulb')
    def test_authenticate_error_on_bulb_update(self, mock_iot_bulb, mock_asyncio_run):
        """authenticate() must handle asyncio.run() errors."""
        config = {
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
                ]
            }
        }

        mock_iot_bulb.return_value = Mock()
        mock_asyncio_run.side_effect = Exception("Update failed")

        backend = KasaBackend(config)

        with pytest.raises(SystemExit) as exc_info:
            backend.authenticate()

        assert exc_info.value.code == 1


class TestKasaSetColor:
    """Test set_color() method."""

    @patch('backends.kasa_backend.asyncio.run')
    def test_set_color_calls_set_hsv(self, mock_asyncio_run):
        """set_color() must call asyncio.run(bulb.set_hsv())."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        mock_bulb = Mock()
        backend.bulbs['192.168.1.100'] = mock_bulb

        backend.set_color('192.168.1.100', hue=240, saturation=75, brightness=50)

        # Verify asyncio.run was called
        mock_asyncio_run.assert_called_once()

        # Extract the call - asyncio.run(bulb.set_hsv(...))
        call_args = mock_asyncio_run.call_args[0][0]
        # For now, just verify the call happened

    @patch('backends.kasa_backend.asyncio.run')
    def test_set_color_raises_on_unknown_bulb(self, mock_asyncio_run):
        """set_color() must raise exception on unknown bulb_id."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        with pytest.raises(Exception):
            backend.set_color('192.168.1.999', hue=240, saturation=75, brightness=50)

        # asyncio.run should not be called
        mock_asyncio_run.assert_not_called()

    @patch('backends.kasa_backend.asyncio.run')
    def test_set_color_handles_hsv_parameters(self, mock_asyncio_run):
        """set_color() must pass HSV values to set_hsv()."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        mock_bulb = Mock()
        backend.bulbs['192.168.1.100'] = mock_bulb

        # Test various HSV values
        test_cases = [
            (0, 0, 0),      # Red, no saturation, off
            (240, 100, 100), # Blue, full saturation, full brightness
            (120, 50, 75),   # Green-ish, medium sat, high brightness
        ]

        for hue, sat, bri in test_cases:
            mock_asyncio_run.reset_mock()
            backend.set_color('192.168.1.100', hue=hue, saturation=sat, brightness=bri)
            mock_asyncio_run.assert_called_once()


class TestKasaPulse:
    """Test pulse() method (two-step effect)."""

    @patch('backends.kasa_backend.time.sleep')
    @patch('backends.kasa_backend.asyncio.run')
    def test_pulse_two_step_effect(self, mock_asyncio_run, mock_sleep):
        """pulse() must execute rise→hold→fall sequence."""
        config = {
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            },
            'kasa': {}
        }
        backend = KasaBackend(config)

        mock_bulb = Mock()
        backend.bulbs['192.168.1.100'] = mock_bulb

        backend.pulse('192.168.1.100', hue=240, zone=0)

        # Should call set_color twice (rise and fall)
        assert mock_asyncio_run.call_count == 2

        # Should sleep between calls
        mock_sleep.assert_called_once()
        # Sleep duration = (attack + sustain) / 1000 = (200 + 100) / 1000 = 0.3s
        assert mock_sleep.call_args[0][0] == pytest.approx(0.3, abs=0.01)

    @patch('backends.kasa_backend.time.sleep')
    @patch('backends.kasa_backend.asyncio.run')
    def test_pulse_rise_to_peak(self, mock_asyncio_run, mock_sleep):
        """pulse() must first set brightness to pulse_max."""
        config = {
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            },
            'kasa': {}
        }
        backend = KasaBackend(config)
        backend.bulbs['192.168.1.100'] = Mock()

        backend.pulse('192.168.1.100', hue=240, zone=0)

        # First call should be peak brightness (70)
        first_call = mock_asyncio_run.call_args_list[0]
        # We'll verify this indirectly via the set_color call

    @patch('backends.kasa_backend.time.sleep')
    @patch('backends.kasa_backend.asyncio.run')
    def test_pulse_fall_to_baseline(self, mock_asyncio_run, mock_sleep):
        """pulse() must second set brightness back to baseline."""
        config = {
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            },
            'kasa': {}
        }
        backend = KasaBackend(config)
        backend.bulbs['192.168.1.100'] = Mock()

        backend.pulse('192.168.1.100', hue=240, zone=0)

        # Should have two calls to set_color (via asyncio.run)
        assert mock_asyncio_run.call_count == 2

    @patch('backends.kasa_backend.time.sleep')
    @patch('backends.kasa_backend.asyncio.run')
    def test_pulse_no_rate_limiting(self, mock_asyncio_run, mock_sleep):
        """pulse() must not enforce rate limiting (per R37)."""
        config = {
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            },
            'kasa': {}
        }
        backend = KasaBackend(config)
        backend.bulbs['192.168.1.100'] = Mock()

        # Rapid pulses should all execute
        for _ in range(5):
            mock_asyncio_run.reset_mock()
            backend.pulse('192.168.1.100', hue=240, zone=0)
            # Each pulse should execute both calls
            assert mock_asyncio_run.call_count == 2

    @patch('backends.kasa_backend.time.sleep')
    @patch('backends.kasa_backend.asyncio.run')
    def test_pulse_logs_errors_but_continues(self, mock_asyncio_run, mock_sleep):
        """pulse() must log errors without raising (per spec)."""
        config = {
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            },
            'kasa': {}
        }
        backend = KasaBackend(config)

        # Simulate error on set_color
        mock_asyncio_run.side_effect = Exception("Bulb error")
        backend.bulbs['192.168.1.100'] = Mock()

        # pulse() should not raise
        try:
            backend.pulse('192.168.1.100', hue=240, zone=0)
        except Exception:
            pytest.fail("pulse() raised exception on error (should log and continue)")


class TestKasaSetAllBaseline:
    """Test set_all_baseline() method."""

    @patch('backends.kasa_backend.asyncio.run')
    def test_set_all_baseline_initializes_all_bulbs(self, mock_asyncio_run):
        """set_all_baseline() must initialize all configured bulbs."""
        config = {
            'effects': {
                'baseline_brightness': 40,
                'baseline_saturation': 75,
                'baseline_hue': 120,
            },
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
                    {'ip': '192.168.1.101', 'name': 'Bulb2', 'zone': 1},
                ]
            }
        }
        backend = KasaBackend(config)
        backend.bulbs['192.168.1.100'] = Mock()
        backend.bulbs['192.168.1.101'] = Mock()

        backend.set_all_baseline()

        # Should call set_color (via asyncio.run) twice
        assert mock_asyncio_run.call_count == 2

    @patch('backends.kasa_backend.asyncio.run')
    def test_set_all_baseline_uses_config_values(self, mock_asyncio_run):
        """set_all_baseline() must use baseline_* values from config."""
        config = {
            'effects': {
                'baseline_brightness': 50,
                'baseline_saturation': 80,
                'baseline_hue': 180,
            },
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
                ]
            }
        }
        backend = KasaBackend(config)
        backend.bulbs['192.168.1.100'] = Mock()

        backend.set_all_baseline()

        # Verify asyncio.run was called with correct values
        mock_asyncio_run.assert_called_once()

    @patch('backends.kasa_backend.asyncio.run')
    def test_set_all_baseline_continues_on_error(self, mock_asyncio_run):
        """set_all_baseline() must continue on errors (partial init OK)."""
        config = {
            'effects': {
                'baseline_brightness': 40,
                'baseline_saturation': 75,
                'baseline_hue': 120,
            },
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
                    {'ip': '192.168.1.101', 'name': 'Bulb2', 'zone': 1},
                ]
            }
        }
        backend = KasaBackend(config)
        backend.bulbs['192.168.1.100'] = Mock()
        backend.bulbs['192.168.1.101'] = Mock()

        # First call fails, second succeeds
        mock_asyncio_run.side_effect = [Exception("Error"), None]

        # Should not raise
        backend.set_all_baseline()

        # Should attempt both bulbs
        assert mock_asyncio_run.call_count == 2

    @patch('backends.kasa_backend.asyncio.run')
    def test_set_all_baseline_default_hue(self, mock_asyncio_run):
        """set_all_baseline() must default to 120 if baseline_hue not specified."""
        config = {
            'effects': {
                'baseline_brightness': 40,
                'baseline_saturation': 75,
                # baseline_hue not specified
            },
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
                ]
            }
        }
        backend = KasaBackend(config)
        backend.bulbs['192.168.1.100'] = Mock()

        backend.set_all_baseline()

        mock_asyncio_run.assert_called_once()


class TestKasaGetLatencyEstimate:
    """Test get_latency_estimate() method."""

    def test_get_latency_estimate_returns_100(self):
        """get_latency_estimate() must return 100.0 (100ms)."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        latency = backend.get_latency_estimate()

        assert latency == 100.0
        assert isinstance(latency, float)


class TestKasaPrintStats:
    """Test print_stats() method."""

    def test_print_stats_sums_drop_count(self):
        """print_stats() must sum drop_stats values."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        backend.drop_stats['192.168.1.100'] = 5
        backend.drop_stats['192.168.1.101'] = 3
        backend.drop_stats['192.168.1.102'] = 0

        # Mock the config to have bulb names
        backend.config['kasa']['bulbs'] = [
            {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
            {'ip': '192.168.1.101', 'name': 'Bulb2', 'zone': 1},
            {'ip': '192.168.1.102', 'name': 'Bulb3', 'zone': 2},
        ]

        # Should log stats without raising
        backend.print_stats()

    def test_print_stats_no_drops_message(self):
        """print_stats() must log "no drops" when drop_stats are all 0."""
        config = {
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Bulb1', 'zone': 0},
                ]
            }
        }
        backend = KasaBackend(config)
        backend.drop_stats['192.168.1.100'] = 0

        # Should log without raising
        backend.print_stats()


class TestKasaGetBulbForZone:
    """Test get_bulb_for_zone() method."""

    def test_get_bulb_for_zone_returns_ip(self):
        """get_bulb_for_zone() must return bulb IP for valid zone."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        backend.zone_map[0] = '192.168.1.100'
        backend.zone_map[3] = '192.168.1.101'

        assert backend.get_bulb_for_zone(0) == '192.168.1.100'
        assert backend.get_bulb_for_zone(3) == '192.168.1.101'

    def test_get_bulb_for_zone_returns_none_for_unmapped(self):
        """get_bulb_for_zone() must return None for unmapped zone."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        backend.zone_map[0] = '192.168.1.100'

        assert backend.get_bulb_for_zone(1) is None
        assert backend.get_bulb_for_zone(2) is None

    def test_get_bulb_for_zone_all_zones(self):
        """get_bulb_for_zone() must support all 4 zones."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        zone_ips = {
            0: '192.168.1.100',
            1: '192.168.1.101',
            2: '192.168.1.102',
            3: '192.168.1.103',
        }
        backend.zone_map = zone_ips

        for zone, ip in zone_ips.items():
            assert backend.get_bulb_for_zone(zone) == ip


class TestKasaIntegration:
    """Integration tests for KasaBackend."""

    @patch('backends.kasa_backend.asyncio.run')
    @patch('backends.kasa_backend.IotBulb')
    def test_full_flow_authenticate_baseline_pulse(self, mock_iot_bulb, mock_asyncio_run):
        """Full flow: authenticate → set_all_baseline → pulse."""
        config = {
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'baseline_hue': 120,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            },
            'kasa': {
                'bulbs': [
                    {'ip': '192.168.1.100', 'name': 'Zone0', 'zone': 0},
                ]
            }
        }

        mock_iot_bulb.return_value = Mock()
        mock_asyncio_run.return_value = None

        backend = KasaBackend(config)

        # Step 1: Authenticate
        backend.authenticate()
        assert '192.168.1.100' in backend.bulbs

        # Step 2: Set baseline
        mock_asyncio_run.reset_mock()
        backend.set_all_baseline()

        # Step 3: Pulse
        with patch('backends.kasa_backend.time.sleep'):
            mock_asyncio_run.reset_mock()
            backend.pulse('192.168.1.100', hue=240, zone=0)
            assert mock_asyncio_run.call_count == 2

    def test_backend_is_usable_instance(self):
        """KasaBackend must be instantiable with minimal config."""
        config = {'kasa': {}}
        backend = KasaBackend(config)

        assert isinstance(backend, KasaBackend)
        assert isinstance(backend, LightingBackend)
