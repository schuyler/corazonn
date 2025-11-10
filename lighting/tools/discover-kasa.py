#!/usr/bin/env python3
"""Discover Kasa bulbs on local network."""

import asyncio
from kasa import Discover

async def main():
    print("Scanning for Kasa devices...")
    devices = await Discover.discover()

    bulbs = [dev for dev in devices.values() if dev.is_bulb]

    if not bulbs:
        print("No Kasa bulbs found on network")
        return

    print(f"\nFound {len(bulbs)} Kasa bulbs:\n")

    for bulb in bulbs:
        await bulb.update()
        print(f"Name: {bulb.alias}")
        print(f"  IP (for config): {bulb.host}")
        print(f"  Model: {bulb.model}")
        print(f"  MAC: {bulb.mac}")
        print()

if __name__ == '__main__':
    asyncio.run(main())
