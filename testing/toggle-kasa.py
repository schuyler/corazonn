#!/usr/bin/env python3
"""Toggle Kasa bulbs on and off."""

import asyncio
import sys
from kasa import Discover


async def toggle_all():
    """Discover all bulbs and toggle their power state."""
    discovered = await Discover.discover()

    if not discovered:
        print("No bulbs found on network")
        return

    for ip, device in discovered.items():
        await device.update()
        if device.is_on:
            await device.turn_off()
            print(f"{device.alias}: off")
        else:
            await device.turn_on()
            print(f"{device.alias}: on")


async def turn_on_all():
    """Turn on all bulbs."""
    discovered = await Discover.discover()

    if not discovered:
        print("No bulbs found on network")
        return

    for ip, device in discovered.items():
        await device.update()
        if not device.is_on:
            await device.turn_on()
            print(f"{device.alias}: on")


async def turn_off_all():
    """Turn off all bulbs."""
    discovered = await Discover.discover()

    if not discovered:
        print("No bulbs found on network")
        return

    for ip, device in discovered.items():
        await device.update()
        if device.is_on:
            await device.turn_off()
            print(f"{device.alias}: off")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "on":
            asyncio.run(turn_on_all())
        elif cmd == "off":
            asyncio.run(turn_off_all())
        elif cmd == "toggle":
            asyncio.run(toggle_all())
        else:
            print("Usage: toggle-kasa.py [on|off|toggle]")
            sys.exit(1)
    else:
        asyncio.run(toggle_all())
