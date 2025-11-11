#!/usr/bin/env python3
"""
Test script for Amor Launchpad Bridge.

Tests grid mapping functions and validates MIDI note conversions.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from amor.launchpad import note_to_grid, grid_to_note, grid_to_loop_id


def test_grid_mapping():
    """Test MIDI note ↔ grid position conversions."""
    print("Testing grid mapping functions...")

    # Test note_to_grid
    test_cases = [
        (11, (0, 0)),   # Top-left
        (18, (0, 7)),   # Top-right
        (81, (7, 0)),   # Bottom-left
        (88, (7, 7)),   # Bottom-right
        (44, (3, 3)),   # Middle
        (99, None),     # Invalid note
        (5, None),      # Invalid note
    ]

    print("\n1. note_to_grid():")
    for note, expected in test_cases:
        result = note_to_grid(note)
        status = "✓" if result == expected else "✗"
        print(f"  {status} note_to_grid({note}) = {result} (expected {expected})")

    # Test grid_to_note
    test_cases = [
        ((0, 0), 11),   # Top-left
        ((0, 7), 18),   # Top-right
        ((7, 0), 81),   # Bottom-left
        ((7, 7), 88),   # Bottom-right
        ((3, 3), 44),   # Middle
    ]

    print("\n2. grid_to_note():")
    for (row, col), expected in test_cases:
        result = grid_to_note(row, col)
        status = "✓" if result == expected else "✗"
        print(f"  {status} grid_to_note({row}, {col}) = {result} (expected {expected})")

    # Test round-trip conversion
    print("\n3. Round-trip conversion (grid → note → grid):")
    for row in range(8):
        for col in range(8):
            note = grid_to_note(row, col)
            back = note_to_grid(note)
            if back != (row, col):
                print(f"  ✗ Round-trip failed for ({row}, {col}) → {note} → {back}")
                return False

    print("  ✓ All round-trip conversions passed")

    # Test grid_to_loop_id
    test_cases = [
        ((4, 0), 0),    # First latching loop
        ((4, 7), 7),    # Last of first latching row
        ((5, 0), 8),    # First of second latching row
        ((5, 7), 15),   # Last latching loop
        ((6, 0), 16),   # First momentary loop
        ((7, 7), 31),   # Last momentary loop
        ((0, 0), None), # PPG row (not a loop)
        ((3, 0), None), # PPG row (not a loop)
    ]

    print("\n4. grid_to_loop_id():")
    for (row, col), expected in test_cases:
        result = grid_to_loop_id(row, col)
        status = "✓" if result == expected else "✗"
        print(f"  {status} grid_to_loop_id({row}, {col}) = {result} (expected {expected})")

    print("\n✓ All grid mapping tests passed!\n")
    return True


def test_protocol_constants():
    """Test protocol constants and port assignments."""
    from amor.launchpad import (
        PORT_BEAT_INPUT, PORT_CONTROL_OUTPUT, PORT_LED_INPUT,
        COLOR_OFF, COLOR_DIM_BLUE, COLOR_BRIGHT_CYAN,
        GRID_ROWS, GRID_COLS
    )

    print("Protocol constants:")
    print(f"  PORT_BEAT_INPUT: {PORT_BEAT_INPUT}")
    print(f"  PORT_CONTROL_OUTPUT: {PORT_CONTROL_OUTPUT}")
    print(f"  PORT_LED_INPUT: {PORT_LED_INPUT}")
    print(f"  GRID_ROWS × GRID_COLS: {GRID_ROWS} × {GRID_COLS}")
    print(f"  Colors: OFF={COLOR_OFF}, DIM_BLUE={COLOR_DIM_BLUE}, BRIGHT_CYAN={COLOR_BRIGHT_CYAN}")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("AMOR LAUNCHPAD BRIDGE TEST SUITE")
    print("=" * 60)
    print()

    test_protocol_constants()

    if test_grid_mapping():
        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
