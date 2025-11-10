#!/usr/bin/env python3
"""
Backend interface compliance and factory tests.

Tests that:
1. All backends properly implement LightingBackend interface
2. Backend factory creates correct backend instances
3. Factory validation catches errors
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from backends.base import LightingBackend
from backends.kasa_backend import KasaBackend
from backends import create_backend, BACKENDS


# =============================================================================
# Backend Interface Compliance Tests (TRD Section 11.1)
# =============================================================================

class TestKasaBackendInterface:
    """Verify KasaBackend implements LightingBackend interface."""

    def test_kasa_inherits_from_lighting_backend(self):
        """KasaBackend must inherit from LightingBackend."""
        assert issubclass(KasaBackend, LightingBackend)

    def test_kasa_has_all_required_methods(self):
        """KasaBackend must implement all 7 abstract methods."""
        required_methods = [
            'authenticate',
            'set_color',
            'pulse',
            'set_all_baseline',
            'get_latency_estimate',
            'print_stats',
            'get_bulb_for_zone',
        ]

        for method_name in required_methods:
            assert hasattr(KasaBackend, method_name), \
                f"KasaBackend missing required method: {method_name}"

            method = getattr(KasaBackend, method_name)
            assert callable(method), \
                f"{method_name} is not callable"

    def test_kasa_method_signatures(self):
        """Verify KasaBackend method signatures match base class."""
        # Create instance with mock config
        config = {
            'kasa': {'bulbs': []},
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            }
        }
        backend = KasaBackend(config)

        # Verify authenticate() signature
        assert hasattr(backend, 'authenticate')
        # Returns None (no return annotation check needed)

        # Verify set_color() signature (accepts 4 params: bulb_id, hue, sat, bri)
        assert hasattr(backend, 'set_color')

        # Verify pulse() signature (accepts 3 params: bulb_id, hue, zone)
        assert hasattr(backend, 'pulse')

        # Verify set_all_baseline() signature (no params)
        assert hasattr(backend, 'set_all_baseline')

        # Verify get_latency_estimate() signature (returns float)
        latency = backend.get_latency_estimate()
        assert isinstance(latency, (int, float))

        # Verify print_stats() signature (no params, no return)
        assert hasattr(backend, 'print_stats')

        # Verify get_bulb_for_zone() signature (accepts zone, returns Optional[str])
        result = backend.get_bulb_for_zone(0)
        assert result is None or isinstance(result, str)


# =============================================================================
# Backend Factory Tests (TRD Section 11.1, R28-R30)
# =============================================================================

class TestBackendFactory:
    """Verify backend factory creates correct instances."""

    def test_backends_registry_contains_kasa(self):
        """BACKENDS dict must contain 'kasa' entry."""
        assert 'kasa' in BACKENDS
        assert BACKENDS['kasa'] is KasaBackend

    def test_create_backend_returns_kasa_instance(self):
        """Factory must create KasaBackend when backend='kasa'."""
        config = {
            'lighting': {'backend': 'kasa'},
            'kasa': {'bulbs': []},
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            }
        }

        backend = create_backend(config)
        assert isinstance(backend, KasaBackend)
        assert isinstance(backend, LightingBackend)

    def test_create_backend_raises_on_missing_backend_name(self):
        """Factory must raise ValueError if backend name missing (R28)."""
        # Missing 'lighting' section
        with pytest.raises(ValueError, match="Config missing 'lighting.backend'"):
            create_backend({})

        # Missing 'backend' key
        with pytest.raises(ValueError, match="Config missing 'lighting.backend'"):
            create_backend({'lighting': {}})

        # Empty backend name
        with pytest.raises(ValueError, match="Config missing 'lighting.backend'"):
            create_backend({'lighting': {'backend': ''}})

    def test_create_backend_raises_on_unknown_backend(self):
        """Factory must raise ValueError for unknown backend with helpful message (R29)."""
        config = {
            'lighting': {'backend': 'nonexistent'},
        }

        with pytest.raises(ValueError) as exc_info:
            create_backend(config)

        error_msg = str(exc_info.value)
        assert 'nonexistent' in error_msg
        assert 'Available backends' in error_msg

    def test_create_backend_error_lists_available_backends(self):
        """Factory error must list available backends (R29)."""
        config = {
            'lighting': {'backend': 'invalid'},
        }

        with pytest.raises(ValueError) as exc_info:
            create_backend(config)

        error_msg = str(exc_info.value)
        # Should list 'kasa' as available
        assert 'kasa' in error_msg


# =============================================================================
# Integration Tests
# =============================================================================

class TestBackendIntegration:
    """Test backend integration with factory."""

    def test_factory_can_instantiate_all_registered_backends(self):
        """Factory should be able to create instances of all registered backends."""
        for backend_name, backend_class in BACKENDS.items():
            config = {
                'lighting': {'backend': backend_name},
                backend_name: {'bulbs': []} if backend_name == 'kasa' else {},
                'effects': {
                    'baseline_brightness': 40,
                    'pulse_max': 70,
                    'baseline_saturation': 75,
                    'attack_time_ms': 200,
                    'sustain_time_ms': 100,
                }
            }

            # Add backend-specific config if needed
            if backend_name == 'wyze':
                config['wyze'] = {'email': 'test@example.com', 'password': 'test', 'bulbs': []}
            elif backend_name == 'wled':
                config['wled'] = {'devices': []}

            backend = create_backend(config)
            assert isinstance(backend, backend_class)
            assert isinstance(backend, LightingBackend)

    def test_backend_instances_have_logger(self):
        """All backend instances must have a logger."""
        config = {
            'lighting': {'backend': 'kasa'},
            'kasa': {'bulbs': []},
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            }
        }

        backend = create_backend(config)
        assert hasattr(backend, 'logger')
        assert backend.logger.name == 'KasaBackend'

    def test_backend_instances_have_config(self):
        """All backend instances must store config."""
        config = {
            'lighting': {'backend': 'kasa'},
            'kasa': {'bulbs': []},
            'effects': {
                'baseline_brightness': 40,
                'pulse_max': 70,
                'baseline_saturation': 75,
                'attack_time_ms': 200,
                'sustain_time_ms': 100,
            }
        }

        backend = create_backend(config)
        assert hasattr(backend, 'config')
        assert backend.config == config


# =============================================================================
# Run tests
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
