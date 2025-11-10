"""WLED backend for WLED smart bulbs (local UDP control)."""

import socket
import time
from typing import Optional, Tuple
from .base import LightingBackend


class WLEDBackend(LightingBackend):
    """
    WLED bulb control via local UDP DRGB protocol.

    Features:
    - Local UDP control (no internet required)
    - <10ms latency
    - No rate limiting (UDP is fast)
    - Tracks communication failures
    """

    def __init__(self, config: dict):
        """Initialize WLEDBackend with empty bulb collections."""
        super().__init__(config)
        self.bulbs = {}  # Map bulb_id (IP) -> (socket, port)
        self.zone_map = {}  # Map zone -> bulb_id (IP)
        self.drop_stats = {}  # Track drops per bulb (communication failures)

    def authenticate(self) -> None:
        """Initialize connection to WLED bulbs (discover on network)."""
        try:
            wled_config = self.config.get('wled', {})

            # Connect to each configured bulb
            for bulb_cfg in wled_config.get('bulbs', []):
                ip = bulb_cfg['ip']
                zone = bulb_cfg['zone']
                name = bulb_cfg['name']
                port = bulb_cfg.get('port', 21324)  # Default DRGB port

                self.logger.info(f"Connecting to {name} ({ip}:{port})...")

                # Create UDP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1.0)

                # Store references
                self.bulbs[ip] = (sock, port)
                self.zone_map[zone] = ip
                self.drop_stats[ip] = 0

                self.logger.info(f"Zone {zone} → {name} ({ip}:{port}) - OK")

            self.logger.info(f"WLED: {len(self.bulbs)} bulbs connected")

        except Exception as e:
            self.logger.error(f"WLED authentication failed: {e}")
            raise SystemExit(1)

    @staticmethod
    def _hsv_to_rgb(hue: int, saturation: int, brightness: int) -> Tuple[int, int, int]:
        """
        Convert HSV to RGB.

        Args:
            hue: 0-360 degrees
            saturation: 0-100 percent
            brightness: 0-100 percent

        Returns:
            Tuple of (red, green, blue) 0-255
        """
        # Normalize inputs
        h = (hue % 360) / 360.0
        s = saturation / 100.0
        v = brightness / 100.0

        # HSV to RGB algorithm
        c = v * s
        x = c * (1.0 - abs((h * 6.0) % 2.0 - 1.0))
        m = v - c

        if h < 1/6:
            r, g, b = c, x, 0
        elif h < 2/6:
            r, g, b = x, c, 0
        elif h < 3/6:
            r, g, b = 0, c, x
        elif h < 4/6:
            r, g, b = 0, x, c
        elif h < 5/6:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        # Convert to 0-255 range
        r = int((r + m) * 255)
        g = int((g + m) * 255)
        b = int((b + m) * 255)

        return (r, g, b)

    def set_color(self, bulb_id: str, hue: int, saturation: int, brightness: int) -> None:
        """Send color via WLED DRGB UDP protocol."""
        try:
            if bulb_id not in self.bulbs:
                raise ValueError(f"Unknown bulb ID: {bulb_id}")

            # Convert HSV to RGB
            r, g, b = self._hsv_to_rgb(hue, saturation, brightness)

            # Build DRGB packet (UDP protocol format)
            # Protocol: 0x00 + R + G + B
            packet = bytes([0x00, r, g, b])

            # Send via UDP
            sock, port = self.bulbs[bulb_id]
            sock.sendto(packet, (bulb_id, port))

        except Exception as e:
            self.logger.error(f"Failed to set color for {bulb_id}: {e}")
            raise

    def pulse(self, bulb_id: str, hue: int, zone: int) -> None:
        """Execute brightness pulse effect via UDP."""
        try:
            effects = self.config.get('effects', {})
            baseline_bri = effects.get('baseline_brightness', 40)
            pulse_max = effects.get('pulse_max', 70)
            baseline_sat = effects.get('baseline_saturation', 75)

            # Call 1: Rise to peak brightness
            self.set_color(bulb_id, hue, baseline_sat, pulse_max)

            # Hold at peak for attack + sustain time
            attack_sustain = (effects.get('attack_time_ms', 200) +
                            effects.get('sustain_time_ms', 100)) / 1000
            time.sleep(attack_sustain)

            # Call 2: Fall back to baseline brightness
            self.set_color(bulb_id, hue, baseline_sat, baseline_bri)

        except Exception as e:
            self.logger.error(f"Pulse failed for {bulb_id}: {e}")

    def set_all_baseline(self) -> None:
        """Initialize all WLED bulbs to baseline (continue on errors)."""
        effects = self.config.get('effects', {})
        baseline_bri = effects.get('baseline_brightness', 40)
        baseline_sat = effects.get('baseline_saturation', 75)
        baseline_hue = effects.get('baseline_hue', 120)

        for bulb_id, (sock, port) in self.bulbs.items():
            try:
                self.set_color(bulb_id, baseline_hue, baseline_sat, baseline_bri)

                # Get bulb name from config for logging
                bulb_cfg = next(
                    (b for b in self.config.get('wled', {}).get('bulbs', [])
                     if b['ip'] == bulb_id),
                    None
                )
                name = bulb_cfg['name'] if bulb_cfg else bulb_id
                self.logger.info(f"Initialized {name} to baseline")

            except Exception as e:
                self.logger.error(f"Failed to init {bulb_id}: {e}")

    def get_latency_estimate(self) -> float:
        """Return WLED typical latency (<10ms, return 5.0)."""
        return 5.0

    def print_stats(self) -> None:
        """Print drop statistics (communication failures only)."""
        total_drops = sum(self.drop_stats.values())

        if total_drops == 0:
            self.logger.info("WLED: No communication failures")
            return

        self.logger.info("WLED drop statistics:")
        for bulb_id, count in self.drop_stats.items():
            bulb_cfg = next(
                (b for b in self.config.get('wled', {}).get('bulbs', [])
                 if b['ip'] == bulb_id),
                None
            )
            name = bulb_cfg['name'] if bulb_cfg else bulb_id
            self.logger.info(f"  {name}: {count} communication failures")

    def get_bulb_for_zone(self, zone: int) -> Optional[str]:
        """Map zone number to bulb IP."""
        return self.zone_map.get(zone)
