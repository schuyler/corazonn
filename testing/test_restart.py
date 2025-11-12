#!/usr/bin/env python3
"""
Test script for OSC restart functionality.

Sends restart commands to amor components to verify the OSC restart listener implementation.

Usage:
    python3 testing/test_restart.py <component> [port]

Examples:
    python3 testing/test_restart.py processor       # Restart processor on default port 8000
    python3 testing/test_restart.py audio 8004      # Restart audio on port 8004
    python3 testing/test_restart.py lighting        # Restart lighting on default port 8002
    python3 testing/test_restart.py sequencer       # Restart sequencer on default port 8003
    python3 testing/test_restart.py launchpad       # Restart launchpad on default port 8005
"""

import argparse
import sys
from pythonosc.udp_client import SimpleUDPClient

# Default ports for each component
COMPONENT_PORTS = {
    'processor': 8000,
    'audio': 8004,      # Control port for audio
    'lighting': 8002,
    'sequencer': 8003,
    'launchpad': 8005,  # LED command port for launchpad
}

def send_restart_command(component: str, port: int):
    """Send restart command to a component.

    Args:
        component: Component name (processor, audio, lighting, sequencer, launchpad)
        port: OSC port to send to
    """
    client = SimpleUDPClient("127.0.0.1", port)
    address = f"/restart/{component}"

    print(f"Sending restart command to {component}...")
    print(f"  Address: {address}")
    print(f"  Port: {port}")

    client.send_message(address, [])

    print(f"✓ Restart command sent successfully")
    print(f"\nThe component should:")
    print(f"  1. Print restart notification")
    print(f"  2. Perform cleanup")
    print(f"  3. Print statistics")
    print(f"  4. Exit with code 0")
    print(f"  5. Be restarted by supervisor (if running under one)")

def main():
    parser = argparse.ArgumentParser(
        description="Test OSC restart functionality for amor components"
    )
    parser.add_argument(
        "component",
        choices=list(COMPONENT_PORTS.keys()),
        help="Component to restart"
    )
    parser.add_argument(
        "port",
        type=int,
        nargs='?',
        help="OSC port (default: component's default port)"
    )

    args = parser.parse_args()

    # Use specified port or default for component
    port = args.port if args.port else COMPONENT_PORTS[args.component]

    # Validate port range
    if port < 1 or port > 65535:
        print(f"ERROR: Port must be in range 1-65535, got {port}", file=sys.stderr)
        sys.exit(1)

    send_restart_command(args.component, port)

if __name__ == "__main__":
    main()
