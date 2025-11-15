#!/usr/bin/env python3
"""
Test suite for semantic color abstraction in Launchpad bridge.

Tests the Color class, color mappings, and translation functions
for hardware-independent color abstraction.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from amor.launchpad import Color, _MK1_COLORS, _MK1_PULSE_MAP


def test_color_class():
    """Test Color class constants."""
    print("Testing Color class constants...")

    # Verify all expected constants exist
    expected_constants = [
        ('OFF', 0),
        ('RED_LOW', 1),
        ('RED_MED', 2),
        ('RED_FULL', 3),
        ('YELLOW_LOW', 4),
        ('YELLOW_MED', 5),
        ('YELLOW_FULL', 6),
        ('GREEN_LOW', 7),
        ('GREEN_MED', 8),
        ('GREEN_FULL', 9),
    ]

    all_passed = True
    for name, expected_value in expected_constants:
        if not hasattr(Color, name):
            print(f"  ✗ Color.{name} not defined")
            all_passed = False
        else:
            actual_value = getattr(Color, name)
            if actual_value == expected_value:
                print(f"  ✓ Color.{name} = {actual_value}")
            else:
                print(f"  ✗ Color.{name} = {actual_value} (expected {expected_value})")
                all_passed = False

    return all_passed


def test_mk1_colors_mapping():
    """Test _MK1_COLORS mapping from semantic to hardware values."""
    print("\nTesting _MK1_COLORS mapping...")

    expected_mapping = {
        Color.OFF: 0,
        Color.RED_LOW: 1,
        Color.RED_MED: 2,
        Color.RED_FULL: 3,
        Color.YELLOW_LOW: 17,
        Color.YELLOW_MED: 34,
        Color.YELLOW_FULL: 51,
        Color.GREEN_LOW: 16,
        Color.GREEN_MED: 32,
        Color.GREEN_FULL: 48,
    }

    all_passed = True
    for semantic_color, expected_hw_value in expected_mapping.items():
        if semantic_color not in _MK1_COLORS:
            print(f"  ✗ Color {semantic_color} not in _MK1_COLORS")
            all_passed = False
        else:
            actual_hw_value = _MK1_COLORS[semantic_color]
            if actual_hw_value == expected_hw_value:
                print(f"  ✓ _MK1_COLORS[{semantic_color}] = {actual_hw_value}")
            else:
                print(f"  ✗ _MK1_COLORS[{semantic_color}] = {actual_hw_value} "
                      f"(expected {expected_hw_value})")
                all_passed = False

    return all_passed


def test_mk1_pulse_map():
    """Test _MK1_PULSE_MAP for color brightness transitions."""
    print("\nTesting _MK1_PULSE_MAP...")

    expected_pulse_map = {
        0: 0,      # Off stays off
        16: 32,    # Green low -> green med
        32: 48,    # Green med -> green full
        48: 51,    # Green full -> yellow full (brightest)
        51: 51,    # Yellow full stays at max
        1: 2,      # Red low -> red med
        2: 3,      # Red med -> red full
        3: 3,      # Red full stays at max
        17: 34,    # Yellow low -> yellow med
        34: 51,    # Yellow med -> yellow full
    }

    all_passed = True
    for base_color, expected_pulse_color in expected_pulse_map.items():
        if base_color not in _MK1_PULSE_MAP:
            print(f"  ✗ Base color {base_color} not in _MK1_PULSE_MAP")
            all_passed = False
        else:
            actual_pulse_color = _MK1_PULSE_MAP[base_color]
            if actual_pulse_color == expected_pulse_color:
                print(f"  ✓ _MK1_PULSE_MAP[{base_color}] = {actual_pulse_color}")
            else:
                print(f"  ✗ _MK1_PULSE_MAP[{base_color}] = {actual_pulse_color} "
                      f"(expected {expected_pulse_color})")
                all_passed = False

    return all_passed


def test_color_translation():
    """Test semantic color translation to hardware values."""
    print("\nTesting semantic color translation...")

    test_cases = [
        (Color.OFF, 0),
        (Color.GREEN_FULL, 48),
        (Color.GREEN_LOW, 16),
        (Color.GREEN_MED, 32),
        (Color.YELLOW_FULL, 51),
        (Color.RED_FULL, 3),
        (Color.RED_MED, 2),
        (Color.RED_LOW, 1),
        (Color.YELLOW_LOW, 17),
        (Color.YELLOW_MED, 34),
    ]

    all_passed = True
    for semantic_color, expected_hw_value in test_cases:
        hw_value = _MK1_COLORS.get(semantic_color, None)
        if hw_value == expected_hw_value:
            print(f"  ✓ Color.{semantic_color} → {hw_value}")
        else:
            print(f"  ✗ Color.{semantic_color} → {hw_value} (expected {expected_hw_value})")
            all_passed = False

    return all_passed


def test_pulse_color_calculation():
    """Test pulse color brightness calculation."""
    print("\nTesting pulse color calculation...")

    test_cases = [
        # Green sequence
        (0, 0),      # Off stays off
        (16, 32),    # Green low -> green med
        (32, 48),    # Green med -> green full
        (48, 51),    # Green full -> yellow (brightest)
        # Red sequence
        (1, 2),      # Red low -> red med
        (2, 3),      # Red med -> red full
        (3, 3),      # Red full stays max
        # Yellow sequence
        (17, 34),    # Yellow low -> yellow med
        (34, 51),    # Yellow med -> yellow full
        (51, 51),    # Yellow full stays max
    ]

    all_passed = True
    for base_hw_color, expected_pulse_color in test_cases:
        pulse_color = _MK1_PULSE_MAP.get(base_hw_color, base_hw_color)
        if pulse_color == expected_pulse_color:
            print(f"  ✓ Pulse({base_hw_color}) → {pulse_color}")
        else:
            print(f"  ✗ Pulse({base_hw_color}) → {pulse_color} (expected {expected_pulse_color})")
            all_passed = False

    return all_passed


def main():
    """Run all color abstraction tests."""
    print("=" * 70)
    print("SEMANTIC COLOR ABSTRACTION TEST SUITE")
    print("=" * 70)
    print()

    success = True
    success = test_color_class() and success
    success = test_mk1_colors_mapping() and success
    success = test_mk1_pulse_map() and success
    success = test_color_translation() and success
    success = test_pulse_color_calculation() and success

    print()
    if success:
        print("=" * 70)
        print("ALL TESTS PASSED")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print("SOME TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
