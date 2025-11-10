"""Abstract base class for lighting backends."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging

class LightingBackend(ABC):
    """
    Interface that all lighting backends must implement.

    Backends handle authentication, device discovery, and bulb control
    for specific hardware/API platforms (Kasa, Wyze, WLED, etc).
    """

    def __init__(self, config: dict):
        """
        Initialize backend with configuration.

        Args:
            config: Full config dict (backend can access its own section)
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def authenticate(self) -> None:
        """
        Initialize connection to lighting system.

        For cloud backends: Perform login, get tokens
        For local backends: Discover devices on network

        Raises:
            SystemExit: On authentication failure (prevents startup)
        """
        pass

    @abstractmethod
    def set_color(self, bulb_id: str, hue: int, saturation: int, brightness: int) -> None:
        """
        Set bulb to specific HSV values.

        Args:
            bulb_id: Backend-specific bulb identifier (IP, MAC, etc)
            hue: 0-360 degrees
            saturation: 0-100 percent
            brightness: 0-100 percent

        Raises:
            Exception: On communication failure (logged, not fatal)
        """
        pass

    @abstractmethod
    def pulse(self, bulb_id: str, hue: int, zone: int) -> None:
        """
        Execute two-step brightness pulse effect.

        Implementation must:
        1. Rise to pulse_max brightness
        2. Sleep for attack + sustain time
        3. Fall back to baseline brightness
        4. Handle rate limiting if needed
        5. Record drop statistics

        Args:
            bulb_id: Backend-specific bulb identifier
            hue: Target hue (0-360) for this pulse
            zone: Zone number (0-3) for logging
        """
        pass

    @abstractmethod
    def set_all_baseline(self) -> None:
        """
        Initialize all configured bulbs to baseline state.

        Called once on startup. Sets all bulbs to baseline brightness,
        saturation, and default hue.
        """
        pass

    @abstractmethod
    def get_latency_estimate(self) -> float:
        """
        Return typical command latency in milliseconds.

        Used for logging/diagnostics. Returns:
        - Kasa: 50-150ms
        - Wyze: 300-500ms
        - WLED: <10ms
        """
        pass

    @abstractmethod
    def print_stats(self) -> None:
        """
        Print statistics on shutdown (drop rates, errors, etc).

        Called during graceful shutdown (Ctrl+C).
        """
        pass

    @abstractmethod
    def get_bulb_for_zone(self, zone: int) -> Optional[str]:
        """
        Map zone number to bulb ID.

        Args:
            zone: Zone number (0-3)

        Returns:
            bulb_id or None if zone not configured
        """
        pass
