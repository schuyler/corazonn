#!/usr/bin/env python3
"""
Command-line tools for the Amor OSC stack.

Usage:
    python -m amor.cli <address> [arg1] [arg2] ...
"""

import sys
from amor.osc import (
    BroadcastUDPClient,
    PORT_PPG,
    PORT_BEATS,
    PORT_CONTROL,
    PORT_ESP32_ADMIN,
)


def infer_port(address: str) -> int:
    """Infer the appropriate OSC port based on the message address.

    Routes messages to the correct port based on address patterns:
    - /beat/* → PORT_BEATS (8001)
    - /ppg/* → PORT_PPG (8000)
    - /control, /select/*, /loop/*, /route/*, /led/*, /sampler/*, /program/*, /scene, /status/* → PORT_CONTROL (8003)
    - /admin/*, /esp32/* → PORT_ESP32_ADMIN (8006)

    Args:
        address: OSC address string (e.g., "/beat/0", "/select/3")

    Returns:
        Port number for the message
    """
    if address.startswith("/beat/"):
        return PORT_BEATS
    if address.startswith("/ppg/"):
        return PORT_PPG
    if address.startswith("/admin/") or address.startswith("/esp32/"):
        return PORT_ESP32_ADMIN
    return PORT_CONTROL


def parse_argument(arg: str):
    """Parse a command-line argument to the appropriate type.

    Attempts to convert string arguments to int or float, preserving
    strings if conversion fails.
    """
    try:
        return int(arg)
    except ValueError:
        pass
    try:
        return float(arg)
    except ValueError:
        pass
    return arg


def send_osc_message(address: str, args: list, port: int = None, host: str = "255.255.255.255"):
    """Send an OSC message to the amor stack."""
    if port is None:
        port = infer_port(address)

    with BroadcastUDPClient(host, port) as client:
        client.send_message(address, args)
        print(f"Sent to {host}:{port} → {address} {args}")


def main():
    """CLI entry point for sending OSC messages."""
    if len(sys.argv) < 2:
        print("Usage: python -m amor <address> [arg1] [arg2] ...")
        print()
        print("Examples:")
        print("  python -m amor /select/3 5")
        print("  python -m amor /loop/toggle 2")
        print("  python -m amor /led/0/0 63 1")
        print("  python -m amor /route/0 4")
        print()
        print("Ports are inferred from address:")
        print("  /beat/*       → PORT_BEATS (8001)")
        print("  /ppg/*        → PORT_PPG (8000)")
        print("  /admin/*      → PORT_ESP32_ADMIN (8006)")
        print("  everything else → PORT_CONTROL (8003)")
        sys.exit(1)

    address = sys.argv[1]
    args = [parse_argument(arg) for arg in sys.argv[2:]]

    send_osc_message(address, args)


if __name__ == "__main__":
    main()
