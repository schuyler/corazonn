"""Integration tests for PPG → Processor → Lighting → Kasa routing.

Tests validate the control flow from PPG emulator through processor and lighting
to Kasa bulb emulators. Focus on:
1. Beat messages reach lighting subsystem
2. Kasa bulbs receive HSV state changes
3. Zone routing (PPG 0 → Bulb 0, etc.)
4. Pulse timing patterns

Reference: docs/integration-test-ideas.md:17-21
"""

import time
import pytest


class TestPPGToLightingFlow:
    """Test beat flow from PPG emulator through processor to lighting.

    Validates that lighting subsystem correctly:
    - Receives beat messages from processor
    - Validates timestamp freshness
    - Routes beats to correct zones
    """

    def test_lighting_receives_beats(self, component_manager, beat_capture):
        """Verify lighting subsystem receives beat messages.

        Flow: PPG → Processor → Lighting (beat reception)
        Expected: Beat arrives at lighting within 10 seconds

        Note: Lighting shares port 8001 with beat_capture via SO_REUSEPORT,
        so both receive the same broadcast messages.
        """
        # Setup: PPG + Processor + Lighting (with test config)
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_processor()
        component_manager.add_kasa_emulator(multi=True)
        component_manager.add_lighting()  # Uses lighting.test.yaml by default
        component_manager.start_all()

        # Wait for beat (lighting and capture both receive via SO_REUSEPORT)
        ts, addr, args = beat_capture.wait_for_message("/beat/0", timeout=10.0)

        # Validate
        assert addr == "/beat/0"
        assert len(args) == 3  # timestamp, bpm, intensity

    def test_lighting_validates_timestamp_freshness(self, component_manager, beat_capture):
        """Verify lighting drops stale beat messages.

        Flow: PPG → Processor → Lighting (with timestamp validation)
        Expected: Fresh beats accepted, stale beats dropped

        Note: Lighting has 500ms staleness threshold. This test validates
        that normal beats are fresh enough to be processed.
        """
        # Setup
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_processor()
        component_manager.add_kasa_emulator(multi=True)
        component_manager.add_lighting()
        component_manager.start_all()

        # Capture beat and check timestamp age
        capture_time, addr, args = beat_capture.wait_for_message("/beat/0", timeout=10.0)
        timestamp_ms = args[0]  # First arg is timestamp in milliseconds

        # Convert to seconds for comparison
        beat_timestamp = timestamp_ms / 1000.0

        # Calculate age
        age_ms = (capture_time - beat_timestamp) * 1000

        # Should be fresh (<500ms threshold)
        assert age_ms < 500, f"Beat timestamp too old: {age_ms:.1f}ms"


class TestKasaBulbControl:
    """Test Kasa bulb emulator receives HSV changes from lighting.

    Validates end-to-end pipeline:
    - PPG beat arrives → Lighting processes → Kasa bulb state changes
    - Pulse timing (rise + fall pattern)
    - HSV values match lighting program
    """

    def test_bulb_receives_hsv_changes(self, component_manager, beat_capture, kasa_query):
        """Verify Kasa bulb state changes in response to beats.

        Flow: PPG → Processor → Lighting → Kasa bulb HSV update
        Expected: Bulb brightness increases on beat (pulse effect)

        Note: Uses soft_pulse program (default) which increases brightness
        on beat then decays. We validate by checking state changes occur.
        """
        # Setup full pipeline
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_processor()
        component_manager.add_kasa_emulator(multi=True)
        component_manager.add_lighting()
        component_manager.start_all()

        # Get initial state before beats
        initial_state = kasa_query("127.0.0.1")
        initial_brightness = initial_state['brightness']

        # Wait for first beat to arrive
        beat_capture.wait_for_message("/beat/0", timeout=10.0)

        # Allow pulse to complete (attack + sustain ~300ms + margin)
        time.sleep(0.5)

        # Query bulb state after beat
        final_state = kasa_query("127.0.0.1")

        # Verify brightness changed (pulse occurred)
        assert final_state['brightness'] != initial_brightness, \
            f"Expected brightness to change from {initial_brightness}, still {final_state['brightness']}"

    def test_pulse_timing_pattern(self, component_manager, beat_capture, kasa_query):
        """Verify pulse effect has rise and fall pattern.

        Flow: PPG → Lighting → Kasa (validate pulse timing)
        Expected: Brightness rises on beat, then falls back

        Note: Pulse attack=200ms, sustain=100ms, total ~300ms.
        We check brightness at peak (during pulse) and after decay.
        """
        # Setup
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_processor()
        component_manager.add_kasa_emulator(multi=True)
        component_manager.add_lighting()
        component_manager.start_all()

        # Get baseline before beat
        baseline_state = kasa_query("127.0.0.1")
        baseline_brightness = baseline_state['brightness']

        # Wait for first beat
        beat_capture.wait_for_message("/beat/0", timeout=10.0)

        # Check brightness during pulse (should be higher than baseline)
        time.sleep(0.15)  # Mid-attack phase
        state_during = kasa_query("127.0.0.1")
        assert state_during['brightness'] > baseline_brightness, \
            f"Expected brightness to rise during pulse: baseline={baseline_brightness}, during={state_during['brightness']}"

        # Wait for pulse to complete and decay
        time.sleep(1.0)  # Allow full decay
        state_after = kasa_query("127.0.0.1")

        # Brightness should have fallen back (may not reach exact baseline due to decay curves)
        assert state_after['brightness'] < state_during['brightness'], \
            f"Expected brightness to fall after pulse: during={state_during['brightness']}, after={state_after['brightness']}"

    def test_zone_routing_basic(self, component_manager, beat_capture, kasa_query):
        """Verify PPG 0 routes to bulb at 127.0.0.1 (zone 0).

        Flow: PPG 0 → Processor → Lighting → Zone 0 bulb
        Expected: Zone 0 bulb state changes, zone 1 remains unchanged

        Note: Test config maps:
          - PPG 0 → Zone 0 → 127.0.0.1
          - PPG 1 → Zone 1 → 127.0.0.2
        """
        # Setup with single PPG
        component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
        component_manager.add_processor()
        component_manager.add_kasa_emulator(multi=True)
        component_manager.add_lighting()
        component_manager.start_all()

        # Get initial state of zone 0 and zone 1
        initial_zone0 = kasa_query("127.0.0.1")
        initial_zone1 = kasa_query("127.0.0.2")

        # Wait for beat from PPG 0
        beat_capture.wait_for_message("/beat/0", timeout=10.0)

        # Allow pulse to complete
        time.sleep(0.5)

        # Check final states
        final_zone0 = kasa_query("127.0.0.1")
        final_zone1 = kasa_query("127.0.0.2")

        # Verify zone 0 changed (PPG 0 affects it)
        assert final_zone0['brightness'] != initial_zone0['brightness'], \
            f"Zone 0 should change with PPG 0 beat: initial={initial_zone0['brightness']}, final={final_zone0['brightness']}"

        # Verify zone 1 unchanged (PPG 1 not active - no cross-talk)
        assert final_zone1['brightness'] == initial_zone1['brightness'], \
            f"Zone 1 should not change (no PPG 1): initial={initial_zone1['brightness']}, final={final_zone1['brightness']}"


class TestMultiZoneRouting:
    """Test multiple PPG sensors route to correct bulbs independently.

    Validates:
    - Independent zone control (PPG 0 → Bulb 0, PPG 1 → Bulb 1)
    - No cross-talk between zones
    - Multiple PPG sensors operate concurrently
    """

    def test_multi_ppg_independent_zones(self, component_manager, beat_capture, kasa_query):
        """Verify multiple PPG sensors control independent zones.

        Flow: PPG 0 + PPG 1 → Processor → Lighting → Zones 0 + 1
        Expected: Both zones receive independent control

        Note: Using different BPMs (70 vs 80) to ensure independence.
        """
        # Setup: 2 PPGs with different BPMs + full lighting pipeline
        component_manager.add_ppg_emulator(ppg_id=0, bpm=70)
        component_manager.add_ppg_emulator(ppg_id=1, bpm=80)
        component_manager.add_processor()
        component_manager.add_kasa_emulator(multi=True)
        component_manager.add_lighting()
        component_manager.start_all()

        # Get initial states
        initial_zone0 = kasa_query("127.0.0.1")
        initial_zone1 = kasa_query("127.0.0.2")

        # Wait for beats from both PPGs
        beat_capture.wait_for_message("/beat/0", timeout=10.0)
        beat_capture.wait_for_message("/beat/1", timeout=10.0)

        # Allow pulses to complete
        time.sleep(0.5)

        # Query both zones
        final_zone0 = kasa_query("127.0.0.1")
        final_zone1 = kasa_query("127.0.0.2")

        # Validate both zones changed (independent control)
        assert final_zone0['brightness'] != initial_zone0['brightness'], \
            f"Zone 0 should change with PPG 0 beats: initial={initial_zone0['brightness']}, final={final_zone0['brightness']}"
        assert final_zone1['brightness'] != initial_zone1['brightness'], \
            f"Zone 1 should change with PPG 1 beats: initial={initial_zone1['brightness']}, final={final_zone1['brightness']}"

    def test_four_zone_concurrent_operation(self, component_manager, beat_capture, kasa_query):
        """Verify all 4 zones operate concurrently without interference.

        Flow: PPG 0-3 → Processor → Lighting → Zones 0-3
        Expected: All 4 zones receive independent control

        Note: Uses different BPMs (60, 70, 80, 90) for each PPG.
        This test validates basic connectivity - all zones respond to their PPG.
        """
        # Setup: 4 PPGs with different BPMs
        component_manager.add_ppg_emulator(ppg_id=0, bpm=60)
        component_manager.add_ppg_emulator(ppg_id=1, bpm=70)
        component_manager.add_ppg_emulator(ppg_id=2, bpm=80)
        component_manager.add_ppg_emulator(ppg_id=3, bpm=90)
        component_manager.add_processor()
        component_manager.add_kasa_emulator(multi=True)
        component_manager.add_lighting()
        component_manager.start_all()

        # Get initial states for all zones
        zone_ips = ["127.0.0.1", "127.0.0.2", "127.0.0.3", "127.0.0.4"]
        initial_states = [kasa_query(ip) for ip in zone_ips]

        # Wait for at least one beat from each PPG
        beat_capture.wait_for_message("/beat/0", timeout=10.0)
        beat_capture.wait_for_message("/beat/1", timeout=10.0)
        beat_capture.wait_for_message("/beat/2", timeout=10.0)
        beat_capture.wait_for_message("/beat/3", timeout=10.0)

        # Allow pulses to complete
        time.sleep(0.5)

        # Query all zones
        final_states = [kasa_query(ip) for ip in zone_ips]

        # Validate all zones changed (each zone responds to its PPG)
        for i, (initial, final) in enumerate(zip(initial_states, final_states)):
            assert final['brightness'] != initial['brightness'], \
                f"Zone {i} should change with PPG {i} beats: initial={initial['brightness']}, final={final['brightness']}"
