#!/usr/bin/env python3
"""
Bootstrap script to test Novation Launchpad functionality.
Reads note events and toggles LED on each button press.
"""

import mido
import sys
import time
from typing import Dict

# Color palette (Original Launchpad)
# Velocity bits: [0-1] = red brightness, [4-5] = green brightness
# Brightness levels: 0=off, 1=low, 2=medium, 3=full
COLOR_OFF = 0
COLOR_CYCLE = [
    1,   # Red low    (0000 0001)
    2,   # Red medium (0000 0010)
    3,   # Red full   (0000 0011)
    17,  # Yellow low (0001 0001 = red low + green low)
    34,  # Yellow med (0010 0010 = red med + green med)
    51,  # Yellow full (0011 0011 = red full + green full)
    16,  # Green low  (0001 0000)
    32,  # Green med  (0010 0000)
    48,  # Green full (0011 0000)
]
COLOR_NAMES = {
    0: "OFF",
    1: "RED-LO",
    2: "RED-MD",
    3: "RED-FL",
    17: "YEL-LO",
    34: "YEL-MD",
    51: "YEL-FL",
    16: "GRN-LO",
    32: "GRN-MD",
    48: "GRN-FL",
}


def find_launchpad_ports():
    """Find Launchpad MIDI input and output ports."""
    input_names = mido.get_input_names()
    output_names = mido.get_output_names()

    launchpad_in = None
    launchpad_out = None

    for name in input_names:
        if 'Launchpad' in name and 'MIDI' in name:
            launchpad_in = name
            break

    for name in output_names:
        if 'Launchpad' in name and 'MIDI' in name:
            launchpad_out = name
            break

    return launchpad_in, launchpad_out


def set_led(port, note: int, color: int):
    """Set LED color for a given note."""
    msg = mido.Message('note_on', note=note, velocity=color)
    port.send(msg)


def main():
    # Find Launchpad ports
    print("Searching for Launchpad...")
    input_name, output_name = find_launchpad_ports()

    if not input_name or not output_name:
        print("ERROR: Launchpad not found")
        print("\nAvailable input ports:")
        for name in mido.get_input_names():
            print(f"  - {name}")
        print("\nAvailable output ports:")
        for name in mido.get_output_names():
            print(f"  - {name}")
        sys.exit(1)

    print(f"Input:  {input_name}")
    print(f"Output: {output_name}")

    # Initialize ports as None for cleanup
    midi_in = None
    midi_out = None

    # Open MIDI ports
    midi_in = mido.open_input(input_name)
    midi_out = mido.open_output(output_name)

    # Reset Launchpad on startup to clear any previous state
    print("Sending initial reset...")
    midi_out.send(mido.Message('control_change', control=0, value=0))

    # Track button states (note -> color_index)
    button_states: Dict[int, int] = {}

    print("\nListening for button presses (Ctrl+C to exit)...")
    print("Cycle: Red(Lo/Md/Fl) -> Yellow(Lo/Md/Fl) -> Green(Lo/Md/Fl) -> Off\n")

    try:
        while True:
            # Use iter_pending() instead of blocking iterator for clean shutdown
            for msg in midi_in.iter_pending():
                # Only process button up events (note_off or note_on with velocity 0)
                is_button_up = (msg.type == 'note_off' or
                               (msg.type == 'note_on' and msg.velocity == 0))

                if is_button_up:
                    note = msg.note

                    # Cycle to next color
                    current_index = button_states.get(note, -1)
                    next_index = (current_index + 1) % (len(COLOR_CYCLE) + 1)
                    button_states[note] = next_index

                    # Determine color and set LED
                    if next_index < len(COLOR_CYCLE):
                        color = COLOR_CYCLE[next_index]
                    else:
                        color = COLOR_OFF

                    set_led(midi_out, note, color)

                    # Log
                    color_name = COLOR_NAMES.get(color, "UNKNOWN")
                    print(f"Note {note:3d}: {color_name:6s} (velocity={color})")

            # Small sleep to avoid burning CPU
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\nShutting down...")

        # Turn off all LEDs
        print("Clearing all LEDs...")
        for note in button_states.keys():
            set_led(midi_out, note, COLOR_OFF)

    finally:
        # Reset Launchpad BEFORE closing ports
        print("Resetting Launchpad...")
        if midi_out:
            try:
                # Send reset command (CC 0 = 0)
                midi_out.send(mido.Message('control_change', control=0, value=0))
                print("Reset command sent (CC 0 = 0)")
                # Give device time to process reset before closing port
                time.sleep(0.2)
            except Exception as e:
                print(f"Reset failed: {e}")

        if midi_in:
            midi_in.close()
        if midi_out:
            midi_out.close()
        print("Done.")


if __name__ == '__main__':
    main()
