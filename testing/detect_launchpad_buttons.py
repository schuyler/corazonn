#!/usr/bin/env python3
"""
MIDI Note Detector for Novation Launchpad

Press buttons on your Launchpad and this script will print the MIDI note
numbers. Use this to verify the actual button mappings for scene and control
buttons (which are currently unverified in the codebase).

Run this script, then press each button on your Launchpad and note the
output. Record the note numbers for:
- All 8 scene buttons (right side)
- All 8 control buttons (top side)
- A few grid buttons (for verification)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import mido
except ImportError:
    print("ERROR: mido not installed. Run: pip install mido python-rtmidi")
    sys.exit(1)


def find_launchpad_input():
    """Find and open the Launchpad MIDI input port."""
    input_names = mido.get_input_names()
    print("Available MIDI inputs:")
    for name in input_names:
        print(f"  - {name}")

    launchpad_input = None
    for name in input_names:
        if "Launchpad" in name:
            launchpad_input = mido.open_input(name)
            print(f"\nConnected to: {name}")
            return launchpad_input

    if not launchpad_input:
        print("\nERROR: Launchpad not found in MIDI inputs")
        print("Make sure your Launchpad is connected and powered on")
        sys.exit(1)


def main():
    """Listen for MIDI messages and print note numbers."""
    print("=" * 70)
    print("NOVATION LAUNCHPAD - MIDI NOTE DETECTOR")
    print("=" * 70)
    print()

    midi_input = find_launchpad_input()

    print()
    print("Press buttons on your Launchpad and their MIDI note numbers will appear below.")
    print("Note down the numbers for scene buttons (right side) and control buttons (top).")
    print()
    print("Press Ctrl+C to exit.")
    print("-" * 70)
    print()

    note_ranges = {
        'grid_11_18': (11, 18),
        'grid_21_28': (21, 28),
        'grid_81_88': (81, 88),
        'unknown_89_96': (89, 96),
        'unknown_104_111': (104, 111),
    }

    pressed_notes = set()

    try:
        for msg in midi_input:
            if msg.type == 'note_on' and msg.velocity > 0:
                note = msg.note
                pressed_notes.add(note)

                # Categorize the note
                category = "UNKNOWN"
                for range_name, (start, end) in note_ranges.items():
                    if start <= note <= end:
                        category = range_name
                        break

                print(f"PRESSED: Note {note:3d} (0x{note:02x})  [{category}]")

            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                note = msg.note
                print(f"RELEASED: Note {note:3d} (0x{note:02x})")

            elif msg.type == 'control_change':
                cc_num = msg.control
                value = msg.value
                print(f"CONTROL CHANGE: CC {cc_num:3d} = {value:3d}")

    except KeyboardInterrupt:
        print()
        print()
        print("=" * 70)
        print("SUMMARY OF DETECTED NOTES")
        print("=" * 70)

        if pressed_notes:
            print()
            print("All notes detected (in order):")
            for note in sorted(pressed_notes):
                print(f"  Note {note:3d} (0x{note:02x})")

            print()
            print("Grid buttons (11-88):")
            grid_notes = [n for n in pressed_notes if 11 <= n <= 88]
            if grid_notes:
                for note in sorted(grid_notes):
                    print(f"  Note {note}")
            else:
                print("  (none detected)")

            print()
            print("Scene button candidates (89-96):")
            scene_notes = [n for n in pressed_notes if 89 <= n <= 96]
            if scene_notes:
                for note in sorted(scene_notes):
                    print(f"  Note {note}")
            else:
                print("  (none detected)")

            print()
            print("Control button candidates (104-111):")
            control_notes = [n for n in pressed_notes if 104 <= n <= 111]
            if control_notes:
                for note in sorted(control_notes):
                    print(f"  Note {note}")
            else:
                print("  (none detected)")

            print()
            print("Other notes (unexpected):")
            other_notes = [n for n in pressed_notes if not (11 <= n <= 88 or 89 <= n <= 96 or 104 <= n <= 111)]
            if other_notes:
                for note in sorted(other_notes):
                    print(f"  Note {note}")
            else:
                print("  (none detected)")
        else:
            print()
            print("No button presses detected. Make sure your Launchpad is connected.")

        print()
        print("=" * 70)
        midi_input.close()
        print("Closed MIDI connection")


if __name__ == "__main__":
    main()
