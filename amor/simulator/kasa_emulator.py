#!/usr/bin/env python3
"""
Kasa Bulb Emulator - Integration Testing

Emulates TP-Link Kasa smart bulbs for integration testing without hardware.
Tracks HSV state changes and provides inspection API.

Features:
- Emulates Kasa bulb state (on/off, HSV, brightness)
- Simple TCP server responding to python-kasa protocol
- State inspection API
- Multi-bulb support

Note: This is a simplified emulator for testing. It implements minimal
protocol support sufficient for amor lighting integration tests.
"""

import sys
import time
import signal
import argparse
import asyncio
import json
import struct
from typing import Dict, Optional, Tuple


class KasaBulbEmulator:
    """Emulated Kasa smart bulb.

    Simulates a TP-Link Kasa KL130 smart bulb with HSV color control.

    Args:
        ip: IP address to bind to (default: 127.0.0.1)
        port: TCP port to listen on (default: 9999)
        name: Bulb name (default: Emulated Bulb)
    """

    def __init__(self, ip: str = "127.0.0.1", port: int = 9999, name: str = "Emulated Bulb"):
        self.ip = ip
        self.port = port
        self.name = name

        # Bulb state
        self.is_on = True
        self.hue = 120  # Green
        self.saturation = 75
        self.brightness = 40
        self.color_temp = 0  # Not used for HSV mode

        # Statistics
        self.command_count = 0
        self.state_changes = 0

        # Server and shutdown control
        self.server = None
        self.running = False
        self.shutdown_event = None
        self.loop = None

    def set_hsv(self, hue: int, saturation: int, brightness: int):
        """Set HSV values (0-360 hue, 0-100 sat/brightness)."""
        old_state = (self.hue, self.saturation, self.brightness)
        self.hue = max(0, min(360, hue))
        self.saturation = max(0, min(100, saturation))
        self.brightness = max(0, min(100, brightness))
        self.is_on = True

        new_state = (self.hue, self.saturation, self.brightness)
        if old_state != new_state:
            self.state_changes += 1
            print(f"[{self.name}] HSV: H={self.hue}° S={self.saturation}% B={self.brightness}%")

    def get_state(self) -> Dict:
        """Get current bulb state."""
        return {
            "name": self.name,
            "is_on": self.is_on,
            "hue": self.hue,
            "saturation": self.saturation,
            "brightness": self.brightness,
            "command_count": self.command_count,
            "state_changes": self.state_changes,
        }

    def _encrypt(self, data: str) -> bytes:
        """Encrypt command using Kasa XOR cipher."""
        key = 171
        result = []
        for char in data:
            val = ord(char)
            result.append(val ^ key)
            key = val ^ key
        return bytes(result)

    def _decrypt(self, data: bytes) -> str:
        """Decrypt command using Kasa XOR cipher."""
        key = 171
        result = []
        for byte in data:
            val = byte ^ key
            key = byte
            result.append(chr(val))
        return ''.join(result)

    def _process_command(self, cmd_json: str) -> str:
        """Process Kasa JSON command and return response."""
        self.command_count += 1

        try:
            cmd = json.loads(cmd_json)

            # Handle system info request
            if "system" in cmd and "get_sysinfo" in cmd["system"]:
                return json.dumps({
                    "system": {
                        "get_sysinfo": {
                            "sw_ver": "1.0.0",
                            "hw_ver": "1.0",
                            "model": "KL130(US)",
                            "deviceId": "EMULATOR",
                            "hwId": "EMULATOR",
                            "alias": self.name,
                            "relay_state": 1 if self.is_on else 0,
                            "on_time": 0,
                            "light_state": {
                                "on_off": 1 if self.is_on else 0,
                                "mode": "normal",
                                "hue": self.hue,
                                "saturation": self.saturation,
                                "brightness": self.brightness,
                                "color_temp": self.color_temp,
                            },
                            "err_code": 0
                        }
                    }
                })

            # Handle HSV set command
            if "smartlife.iot.smartbulb.lightingservice" in cmd:
                lighting = cmd["smartlife.iot.smartbulb.lightingservice"]
                if "transition_light_state" in lighting:
                    state = lighting["transition_light_state"]

                    # Update state from command
                    if "hue" in state:
                        self.hue = state["hue"]
                    if "saturation" in state:
                        self.saturation = state["saturation"]
                    if "brightness" in state:
                        self.brightness = state["brightness"]
                    if "on_off" in state:
                        self.is_on = bool(state["on_off"])

                    self.state_changes += 1
                    print(f"[{self.name}] HSV: H={self.hue}° S={self.saturation}% B={self.brightness}%")

                    return json.dumps({
                        "smartlife.iot.smartbulb.lightingservice": {
                            "transition_light_state": {
                                "err_code": 0
                            }
                        }
                    })

            # Default response
            return json.dumps({"err_code": 0})

        except Exception as e:
            print(f"[{self.name}] Error processing command: {e}")
            return json.dumps({"err_code": -1})

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection."""
        addr = writer.get_extra_info('peername')

        try:
            # Read length prefix (4 bytes, big-endian)
            length_bytes = await reader.read(4)
            if not length_bytes:
                return

            length = struct.unpack(">I", length_bytes)[0]

            # Read encrypted command
            encrypted = await reader.read(length)
            if not encrypted:
                return

            # Decrypt and process
            cmd_json = self._decrypt(encrypted)
            response_json = self._process_command(cmd_json)

            # Encrypt response
            response_encrypted = self._encrypt(response_json)

            # Send length prefix + encrypted response
            response_length = struct.pack(">I", len(response_encrypted))
            writer.write(response_length + response_encrypted)
            await writer.drain()

        except Exception as e:
            print(f"[{self.name}] Error handling client {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _run_server(self):
        """Run TCP server."""
        self.shutdown_event = asyncio.Event()

        self.server = await asyncio.start_server(
            self._handle_client,
            self.ip,
            self.port
        )

        addr = self.server.sockets[0].getsockname()
        print(f"[{self.name}] Kasa emulator running on {addr}")

        # Wait for shutdown signal instead of serve_forever()
        await self.shutdown_event.wait()

        # Clean shutdown
        self.server.close()
        await self.server.wait_closed()

    def run(self):
        """Start the emulator."""
        self.running = True
        print(f"Starting Kasa Bulb Emulator: {self.name}")
        print(f"  Address: {self.ip}:{self.port}")
        print(f"  Initial state: H={self.hue}° S={self.saturation}% B={self.brightness}%")

        try:
            # Save event loop reference for stop()
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_server())
        except KeyboardInterrupt:
            pass
        finally:
            self._print_stats()

    def stop(self):
        """Stop the emulator (thread-safe)."""
        self.running = False

        # Trigger shutdown event if running
        if self.shutdown_event and self.loop:
            self.loop.call_soon_threadsafe(self.shutdown_event.set)

    def _print_stats(self):
        """Print final statistics."""
        print(f"\n[{self.name}] Stopped.")
        print(f"  Commands received: {self.command_count}")
        print(f"  State changes: {self.state_changes}")


class MultiBulbEmulator:
    """Manages multiple Kasa bulb emulators.

    Args:
        bulb_configs: List of (ip, port, name) tuples
    """

    def __init__(self, bulb_configs: list):
        self.bulbs = [
            KasaBulbEmulator(ip, port, name)
            for ip, port, name in bulb_configs
        ]
        self.tasks = []
        self.loop = None

    async def _run_all(self):
        """Run all bulbs concurrently."""
        # Initialize shutdown events for all bulbs
        for bulb in self.bulbs:
            bulb.shutdown_event = asyncio.Event()

        # Start all servers
        tasks = [
            asyncio.create_task(bulb._run_server())
            for bulb in self.bulbs
        ]
        self.tasks = tasks
        await asyncio.gather(*tasks, return_exceptions=True)

    def run(self):
        """Start all emulators."""
        print(f"Starting {len(self.bulbs)} Kasa bulb emulators...")

        for bulb in self.bulbs:
            print(f"  {bulb.name}: {bulb.ip}:{bulb.port}")

        try:
            # Save event loop reference for stop()
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_all())
        except KeyboardInterrupt:
            pass
        finally:
            self._print_stats()

    def stop(self):
        """Stop all emulators (thread-safe)."""
        if self.loop:
            for bulb in self.bulbs:
                bulb.running = False
                if bulb.shutdown_event:
                    self.loop.call_soon_threadsafe(bulb.shutdown_event.set)

    def _print_stats(self):
        """Print final statistics for all bulbs."""
        print("\nStopping all emulators...")
        for bulb in self.bulbs:
            print(f"\n[{bulb.name}] Statistics:")
            print(f"  Commands: {bulb.command_count}")
            print(f"  State changes: {bulb.state_changes}")
            print(f"  Final state: H={bulb.hue}° S={bulb.saturation}% B={bulb.brightness}%")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Kasa bulb emulator for integration testing")
    parser.add_argument("--ip", type=str, default="127.0.0.1",
                       help="IP address to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9999,
                       help="TCP port to listen on (default: 9999)")
    parser.add_argument("--name", type=str, default="Emulated Bulb",
                       help="Bulb name (default: Emulated Bulb)")
    parser.add_argument("--multi", action="store_true",
                       help="Run 4 bulbs for 4-zone testing")

    args = parser.parse_args()

    if args.multi:
        # Run 4 bulbs for full system testing
        # Uses different loopback IPs on standard Kasa port (9999)
        # Setup: See amor/simulator/README.md for platform-specific instructions
        bulb_configs = [
            ("127.0.0.1", 9999, "Zone 0 - Red"),
            ("127.0.0.2", 9999, "Zone 1 - Green"),
            ("127.0.0.3", 9999, "Zone 2 - Blue"),
            ("127.0.0.4", 9999, "Zone 3 - Yellow"),
        ]
        emulator = MultiBulbEmulator(bulb_configs)
    else:
        emulator = KasaBulbEmulator(ip=args.ip, port=args.port, name=args.name)

    # Signal handlers (let emulator finish gracefully)
    def signal_handler(sig, frame):
        emulator.stop()
        # Don't call sys.exit() - let run() finish naturally

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    emulator.run()

    # Exit cleanly after run() completes
    sys.exit(0)


if __name__ == "__main__":
    main()
