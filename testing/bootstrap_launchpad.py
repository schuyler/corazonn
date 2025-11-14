#!/usr/bin/env python3
"""
Bootstrap script to test Novation Launchpad functionality.
Reads note events and toggles LED on each button press.
"""

import mido
import sys
from typing import Dict

# Color palette (Original Launchpad)
# For original Launchpad: velocity determines brightness/color
# Full brightness colors: 12=red, 28=amber, 60=green, 62=yellow
COLOR_OFF = 0
COLOR_ON = 60  # Green full brightness


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

    # Open MIDI ports
    midi_in = mido.open_input(input_name)
    midi_out = mido.open_output(output_name)

    # Track button states (note -> is_on)
    button_states: Dict[int, bool] = {}

    print("\nListening for button presses (Ctrl+C to exit)...")
    print("Press any button to toggle its LED\n")

    try:
        for msg in midi_in:
            # Only process note_on messages
            if msg.type == 'note_on':
                note = msg.note

                # Toggle state
                is_on = button_states.get(note, False)
                new_state = not is_on
                button_states[note] = new_state

                # Set LED
                color = COLOR_ON if new_state else COLOR_OFF
                set_led(midi_out, note, color)

                # Log
                state_str = "ON " if new_state else "OFF"
                print(f"Note {note:3d}: {state_str} (color={color})")

    except KeyboardInterrupt:
        print("\n\nShutting down...")

        # Turn off all LEDs
        print("Clearing all LEDs...")
        for note in button_states.keys():
            set_led(midi_out, note, COLOR_OFF)

    finally:
        midi_in.close()
        midi_out.close()
        print("Done.")


if __name__ == '__main__':
    main()
