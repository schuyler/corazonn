"""Backend factory for loading lighting implementations."""

from typing import Type
from .base import LightingBackend
from .kasa_backend import KasaBackend

BACKENDS = {
    'kasa': KasaBackend,
}

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
