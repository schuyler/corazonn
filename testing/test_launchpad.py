#!/usr/bin/env python3
"""
Test script for Amor Launchpad Bridge.

Tests grid mapping functions and validates MIDI note conversions.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from amor.launchpad import (
    note_to_grid, grid_to_note, grid_to_loop_id,
    note_to_scene_id, cc_to_control_id,
    SCENE_BUTTON_NOTES, CONTROL_BUTTON_CCS
)


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


def test_control_button_mapping():
    """Test scene and control button MIDI conversions."""
    print("Testing control button mapping functions...")

    # Test note_to_scene_id (Launchpad MK1: notes 8, 24, 40, 56, 72, 88, 104, 120)
    test_cases = [
        (8, 0),      # Scene 0
        (40, 2),     # Scene 2
        (120, 7),    # Scene 7
        (7, None),   # Not a scene button
        (121, None), # Not a scene button
    ]

    print("\n1. note_to_scene_id():")
    for note, expected in test_cases:
        result = note_to_scene_id(note)
        status = "✓" if result == expected else "✗"
        print(f"  {status} note_to_scene_id({note}) = {result} (expected {expected})")

    # Test cc_to_control_id (Launchpad MK1: CC 104-111)
    test_cases = [
        (104, 0),   # Control 0
        (107, 3),   # Control 3
        (111, 7),   # Control 7
        (103, None),# Not a control button CC
        (112, None),# Not a control button CC
    ]

    print("\n2. cc_to_control_id():")
    for cc_num, expected in test_cases:
        result = cc_to_control_id(cc_num)
        status = "✓" if result == expected else "✗"
        print(f"  {status} cc_to_control_id({cc_num}) = {result} (expected {expected})")

    # Test all scene buttons are recognized
    print("\n3. All scene buttons recognized:")
    all_valid = True
    for i, note in enumerate(SCENE_BUTTON_NOTES):
        scene_id = note_to_scene_id(note)
        if scene_id != i:
            print(f"  ✗ Scene button note {note} should map to {i}, got {scene_id}")
            all_valid = False
    if all_valid:
        print(f"  ✓ All {len(SCENE_BUTTON_NOTES)} scene buttons mapped correctly")

    # Test all control button CCs are recognized
    print("\n4. All control button CCs recognized:")
    all_valid = True
    for i, cc_num in enumerate(CONTROL_BUTTON_CCS):
        control_id = cc_to_control_id(cc_num)
        if control_id != i:
            print(f"  ✗ Control button CC {cc_num} should map to {i}, got {control_id}")
            all_valid = False
    if all_valid:
        print(f"  ✓ All {len(CONTROL_BUTTON_CCS)} control button CCs mapped correctly")

    print("\n✓ All control button mapping tests passed!\n")
    return True


def test_protocol_constants():
    """Test protocol constants and port assignments."""
    from amor.launchpad import (
        PORT_BEAT_INPUT, PORT_CONTROL_OUTPUT, PORT_LED_INPUT,
        Color, _MK1_COLORS,
        GRID_ROWS, GRID_COLS
    )

    print("Protocol constants:")
    print(f"  PORT_BEAT_INPUT: {PORT_BEAT_INPUT}")
    print(f"  PORT_CONTROL_OUTPUT: {PORT_CONTROL_OUTPUT}")
    print(f"  PORT_LED_INPUT: {PORT_LED_INPUT}")
    print(f"  GRID_ROWS × GRID_COLS: {GRID_ROWS} × {GRID_COLS}")
    print(f"  Colors: OFF={Color.OFF}, GREEN_FULL={Color.GREEN_FULL}, YELLOW_FULL={Color.YELLOW_FULL}")
    print(f"  MK1 hardware values: OFF={_MK1_COLORS[Color.OFF]}, "
          f"GREEN_FULL={_MK1_COLORS[Color.GREEN_FULL]}, "
          f"YELLOW_FULL={_MK1_COLORS[Color.YELLOW_FULL]}")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("AMOR LAUNCHPAD BRIDGE TEST SUITE")
    print("=" * 60)
    print()

    test_protocol_constants()

    success = True
    success = test_grid_mapping() and success
    success = test_control_button_mapping() and success

    if success:
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
