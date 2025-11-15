#!/usr/bin/env python3
"""Test if Kasa bulbs respond to brightness commands."""

import asyncio
import time
from kasa import Discover

async def test_brightness():
    """Test bulb brightness changes."""
    print("Discovering bulbs...")
    discovered = await Discover.discover()

    if not discovered:
        print("No bulbs found")
        return

    # Get first bulb
    device = list(discovered.values())[0]
    await device.update()

    print(f"\nTesting bulb: {device.alias}")
    light = device.modules.get("Light")

    if not light:
        print("No Light module found!")
        return

    print("\nTest 1: Set to 10% brightness (baseline)")
    await light.set_hsv(0, 75, 10, transition=0)
    await asyncio.sleep(2)

    print("Test 2: Set to 100% brightness (pulse max)")
    await light.set_hsv(0, 75, 100, transition=0)
    await asyncio.sleep(2)

    print("Test 3: Fade from 10% to 100% over 2 seconds")
    await light.set_hsv(0, 75, 10, transition=0)
    await asyncio.sleep(1)
    await light.set_hsv(0, 75, 100, transition=2000)
    await asyncio.sleep(3)

    print("Test 4: Fade from 100% to 10% over 2 seconds")
    await light.set_hsv(0, 75, 10, transition=2000)
    await asyncio.sleep(3)

    print("\nTest complete. Did you see the brightness changes?")

if __name__ == "__main__":
    asyncio.run(test_brightness())
