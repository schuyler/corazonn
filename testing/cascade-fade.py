#!/usr/bin/env python3
"""Heartbeat-style pulse cascade for Kasa bulbs.

Mimics physiological heartbeat timing:
- Instant attack (snap to peak)
- Long decay over multiple inter-beat intervals (IBI)
"""

import asyncio
import time
from kasa import Discover

# Heartbeat timing for 70 BPM
BPM = 70
IBI_MS = int(60000 / BPM)  # Inter-beat interval in milliseconds (857ms at 70 BPM)

# Symmetric fade in/out with peak in phase with beat
# Each transition needs >= 2s (2.33 beats), use 3 beats
FADE_IN_BEATS = 3
FADE_OUT_BEATS = 3
CYCLE_BEATS = FADE_IN_BEATS + FADE_OUT_BEATS  # 6 beats total

FADE_IN_MS = IBI_MS * FADE_IN_BEATS  # 2571ms
FADE_OUT_MS = IBI_MS * FADE_OUT_BEATS  # 2571ms
CYCLE_MS = IBI_MS * CYCLE_BEATS  # 5142ms


async def heartbeat_pulse(device, hue=0, saturation=75, base_brightness=30, peak_brightness=100, phase_offset_ms=0, start_time=None):
    """Pulse a bulb with smooth fade in/out, peak in phase with beat.

    6-beat cycle at 70 BPM:
    - Beat 0: Start fade in (30% → 100%)
    - Beat 3: Peak at 100%, start fade out (100% → 30%)
    - Beat 6: Back to baseline, ready for next cycle

    Args:
        device: Kasa device object
        hue: Color hue (0-360)
        saturation: Color saturation (0-100)
        base_brightness: Baseline brightness (0-100)
        peak_brightness: Peak brightness (0-100)
        phase_offset_ms: Initial delay before starting cycle (for staggering)
        start_time: Reference time for relative peak logging
    """
    try:
        light = device.modules.get("Light")
        if not light:
            print(f"Error: {device.alias} has no Light module")
            return

        # Wait for phase offset (creates ripple effect)
        if phase_offset_ms > 0:
            await asyncio.sleep(phase_offset_ms / 1000.0)

        # Run continuous pulse cycle
        while True:
            # Fade in: smooth rise to peak
            await light.set_hsv(hue, saturation, peak_brightness, transition=FADE_IN_MS)
            await asyncio.sleep(FADE_IN_MS / 1000.0)

            # Log peak timing
            if start_time is not None:
                elapsed = time.time() - start_time
                print(f"  {device.alias} PEAK at {elapsed:.3f}s (brightness={peak_brightness})")

            # Fade out: smooth fall to baseline
            await light.set_hsv(hue, saturation, base_brightness, transition=FADE_OUT_MS)
            await asyncio.sleep(FADE_OUT_MS / 1000.0)

    except Exception as e:
        print(f"Error pulsing {device.alias}: {e}")


async def heartbeat_cascade():
    """Run heartbeat pulse cascade in a loop until interrupted."""
    discovered = await Discover.discover()

    if not discovered:
        print("No bulbs found on network")
        return

    # Sort by alias to ensure consistent order
    devices = sorted(discovered.values(), key=lambda d: d.alias)

    # Zone-to-hue mapping from lighting.yaml
    hue_map = {
        "Corazon 0": 0,    # Red
        "Corazon 1": 320,  # Deep Pink/Magenta
        "Corazon 2": 280,  # Purple/Violet
        "Corazon 3": 240,  # Deep Blue
    }

    print(f"Starting heartbeat cascade on {len(devices)} bulbs")
    print(f"BPM: {BPM} | IBI: {IBI_MS}ms")
    print(f"Cycle: {CYCLE_BEATS} beats ({CYCLE_MS}ms) | Fade in: {FADE_IN_BEATS} beats | Fade out: {FADE_OUT_BEATS} beats")
    print(f"Peak in phase at beat {FADE_IN_BEATS}")
    print("Ctrl+C to stop...\n")

    # Initialize all bulbs to base brightness (ensure they're in "on" state)
    print("Initializing bulbs to baseline...")
    for device in devices:
        await device.update()
        light = device.modules.get("Light")
        if light:
            hue = hue_map.get(device.alias, 0)
            await light.set_hsv(hue, 75, 30, transition=0)  # 30% brightness baseline

    await asyncio.sleep(0.5)  # Let all bulbs stabilize
    print("Ready!\n")

    # Calculate phase offsets for ripple effect (evenly distributed across cycle)
    phase_offset_per_bulb_ms = CYCLE_MS // len(devices)

    print(f"Phase offset per bulb: {phase_offset_per_bulb_ms}ms ({phase_offset_per_bulb_ms / IBI_MS:.1f} beats)\n")

    # Capture start time for relative peak logging
    ripple_start_time = time.time()

    try:
        # Run all bulbs concurrently with staggered phase offsets
        tasks = [
            heartbeat_pulse(
                device,
                hue=hue_map.get(device.alias, 0),
                base_brightness=30,
                peak_brightness=100,
                phase_offset_ms=i * phase_offset_per_bulb_ms,
                start_time=ripple_start_time
            )
            for i, device in enumerate(devices)
        ]

        await asyncio.gather(*tasks)

    except KeyboardInterrupt:
        print("\n\nStopping heartbeat cascade...")

    # Turn off all lights at the end
    print("Turning off all lights...")
    for device in devices:
        await device.turn_off()
        print(f"  {device.alias}: off")


if __name__ == "__main__":
    asyncio.run(heartbeat_cascade())
