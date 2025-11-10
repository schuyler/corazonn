"""Backend factory for loading lighting implementations."""

from typing import Type
from .base import LightingBackend

BACKENDS = {}

# Kasa (always available - primary backend)
from .kasa_backend import KasaBackend
BACKENDS['kasa'] = KasaBackend

# Wyze (optional - requires wyze-sdk)
try:
    from .wyze_backend import WyzeBackend
    BACKENDS['wyze'] = WyzeBackend
except ImportError:
    pass  # wyze-sdk not installed

# WLED (optional - requires requests for future features)
try:
    from .wled_backend import WLEDBackend
    BACKENDS['wled'] = WLEDBackend
except ImportError:
    pass  # requests not installed

def create_backend(config: dict) -> LightingBackend:
    """
    Factory function to instantiate the configured backend.

    Args:
        config: Full configuration dict

    Returns:
        Instantiated backend object

    Raises:
        ValueError: If backend name invalid or not found
    """
    backend_name = config.get('lighting', {}).get('backend')

    if not backend_name:
        raise ValueError("Config missing 'lighting.backend'")

    if backend_name not in BACKENDS:
        available = ', '.join(BACKENDS.keys())
        raise ValueError(
            f"Unknown backend: '{backend_name}'\n"
            f"Available backends: {available}"
        )

    backend_class = BACKENDS[backend_name]
    return backend_class(config)
