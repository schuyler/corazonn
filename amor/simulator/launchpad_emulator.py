#!/usr/bin/env python3
"""
Launchpad Emulator - Integration Testing

Emulates Launchpad Mini MK3 for integration testing without hardware.
Provides programmatic button press interface and LED state tracking.

Features:
- OSC-based button press emulation
- LED state tracking from sequencer commands
- Programmatic API for automated testing
- Optional interactive CLI mode
"""

import sys
import time
import signal
import argparse
import threading
from typing import Dict, Tuple, Optional
from pythonosc import udp_client, dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer


class LaunchpadEmulator:
    """Emulated Launchpad Mini MK3 controller.

    Sends OSC control messages to sequencer (port 8003) and
    receives LED commands from sequencer (port 8005).

    Args:
        control_port: Port to send control messages (default: 8003)
        led_port: Port to receive LED commands (default: 8005)
    """

    def __init__(self, control_port: int = 8003, led_port: int = 8005):
        self.control_port = control_port
        self.led_port = led_port

        # OSC client for control messages
        self.control_client = udp_client.SimpleUDPClient("127.0.0.1", control_port)

        # LED state tracking: (row, col) -> (color, mode)
        self.led_state: Dict[Tuple[int, int], Tuple[int, int]] = {}

        # Server for LED commands
        self.led_server: Optional[BlockingOSCUDPServer] = None
        self.server_thread: Optional[threading.Thread] = None

        # Statistics
        self.button_presses = 0
        self.led_commands = 0

        # Control flags
        self.running = False

    def start(self):
        """Start LED command listener."""
        self.running = True

        # Setup LED command server
        led_dispatcher = dispatcher.Dispatcher()
        led_dispatcher.map("/led/*/*", self._handle_led_command)
        self.led_server = BlockingOSCUDPServer(("0.0.0.0", self.led_port), led_dispatcher)

        # Start server in thread
        self.server_thread = threading.Thread(target=self.led_server.serve_forever, daemon=True)
        self.server_thread.start()

        time.sleep(0.1)  # Wait for server to bind
        print(f"Launchpad Emulator listening for LED commands on port {self.led_port}")

    def stop(self):
        """Stop the emulator."""
        self.running = False
        if self.led_server:
            self.led_server.shutdown()
        print(f"\nLaunchpad Emulator stopped.")
        print(f"  Button presses sent: {self.button_presses}")
        print(f"  LED commands received: {self.led_commands}")

    def _handle_led_command(self, address: str, *args):
        """Handle LED command from sequencer.

        OSC format: /led/{row}/{col} [color, mode]
        """
        parts = address.split('/')
        if len(parts) != 4 or len(args) < 2:
            return

        try:
            row = int(parts[2])
            col = int(parts[3])
            color = int(args[0])
            mode = int(args[1])

            self.led_state[(row, col)] = (color, mode)
            self.led_commands += 1

        except (ValueError, IndexError):
            pass

    def get_led_state(self, row: int, col: int) -> Optional[Tuple[int, int]]:
        """Get current LED state at position.

        Returns:
            Tuple of (color, mode) or None if not set
        """
        return self.led_state.get((row, col))

    def press_ppg_button(self, ppg_id: int, column: int):
        """Press PPG selection button.

        Args:
            ppg_id: PPG sensor ID (0-3)
            column: Column to select (0-7)
        """
        if not (0 <= ppg_id <= 3 and 0 <= column <= 7):
            raise ValueError(f"Invalid button position: ({ppg_id}, {column})")

        self.control_client.send_message(f"/select/{ppg_id}", [column])
        self.button_presses += 1
        print(f"[EMU] PPG {ppg_id} -> Column {column}")

    def toggle_loop(self, loop_id: int):
        """Toggle latching loop.

        Args:
            loop_id: Loop ID (0-31)
        """
        if not (0 <= loop_id <= 31):
            raise ValueError(f"Invalid loop ID: {loop_id}")

        self.control_client.send_message("/loop/toggle", [loop_id])
        self.button_presses += 1
        print(f"[EMU] Toggle Loop {loop_id}")

    def momentary_loop(self, loop_id: int, state: int):
        """Trigger momentary loop press/release.

        Args:
            loop_id: Loop ID (0-31)
            state: 1 for press, 0 for release
        """
        if not (0 <= loop_id <= 31):
            raise ValueError(f"Invalid loop ID: {loop_id}")
        if state not in (0, 1):
            raise ValueError(f"Invalid state: {state} (must be 0 or 1)")

        self.control_client.send_message("/loop/momentary", [loop_id, state])
        self.button_presses += 1
        action = "Press" if state else "Release"
        print(f"[EMU] {action} Momentary Loop {loop_id}")

    def press_momentary_loop(self, loop_id: int, duration: float = 0.5):
        """Press and hold momentary loop for duration.

        Args:
            loop_id: Loop ID (0-31)
            duration: Hold duration in seconds (default: 0.5)
        """
        self.momentary_loop(loop_id, 1)  # Press
        time.sleep(duration)
        self.momentary_loop(loop_id, 0)  # Release

    def get_ppg_selection(self, ppg_id: int) -> Optional[int]:
        """Get currently selected column for PPG row.

        Returns:
            Column number (0-7) or None if unknown
        """
        # Find selected button in PPG row (mode=1 is pulse/selected)
        for col in range(8):
            state = self.led_state.get((ppg_id, col))
            if state and state[1] == 1:  # mode=1 is pulse (selected)
                return col
        return None

    def print_led_grid(self):
        """Print current LED grid state."""
        print("\nLED Grid State:")
        print("  " + "".join(f"{c:3}" for c in range(8)))
        for row in range(8):
            line = f"{row}: "
            for col in range(8):
                state = self.led_state.get((row, col))
                if state:
                    color, mode = state
                    if color == 0:
                        line += " . "
                    else:
                        line += f"{color:2} " if mode == 0 else f"{color:2}*"
                else:
                    line += " ? "
            print(line)


def interactive_mode(emulator: LaunchpadEmulator):
    """Interactive CLI mode for manual testing."""
    print("\nInteractive Mode")
    print("Commands:")
    print("  p <ppg_id> <col>  - Press PPG button (e.g., 'p 0 3')")
    print("  t <loop_id>       - Toggle loop (e.g., 't 5')")
    print("  m <loop_id>       - Momentary loop (e.g., 'm 16')")
    print("  s                 - Show LED grid")
    print("  q                 - Quit")

    while emulator.running:
        try:
            cmd = input("\n> ").strip().split()
            if not cmd:
                continue

            if cmd[0] == 'q':
                break
            elif cmd[0] == 's':
                emulator.print_led_grid()
            elif cmd[0] == 'p' and len(cmd) == 3:
                ppg_id = int(cmd[1])
                col = int(cmd[2])
                emulator.press_ppg_button(ppg_id, col)
            elif cmd[0] == 't' and len(cmd) == 2:
                loop_id = int(cmd[1])
                emulator.toggle_loop(loop_id)
            elif cmd[0] == 'm' and len(cmd) == 2:
                loop_id = int(cmd[1])
                emulator.press_momentary_loop(loop_id)
            else:
                print("Unknown command")

        except (ValueError, IndexError) as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            break


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Launchpad emulator for integration testing")
    parser.add_argument("--control-port", type=int, default=8003,
                       help="Port to send control messages (default: 8003)")
    parser.add_argument("--led-port", type=int, default=8005,
                       help="Port to receive LED commands (default: 8005)")
    parser.add_argument("--interactive", action="store_true",
                       help="Run in interactive mode")

    args = parser.parse_args()

    emulator = LaunchpadEmulator(
        control_port=args.control_port,
        led_port=args.led_port
    )

    # Signal handlers
    def signal_handler(sig, frame):
        emulator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    emulator.start()

    if args.interactive:
        interactive_mode(emulator)
    else:
        print("Launchpad Emulator running. Press Ctrl+C to exit.")
        try:
            while emulator.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    emulator.stop()


if __name__ == "__main__":
    main()
