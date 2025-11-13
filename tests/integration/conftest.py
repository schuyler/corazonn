"""Pytest fixtures for integration tests.

Provides reusable fixtures for integration testing:
- beat_capture: OSC message capture on beat port (8001)
- control_capture: OSC message capture on control port (8003)
- component_manager: Component lifecycle manager with auto-cleanup
- launchpad_emulator: Direct LaunchpadEmulator instance for programmatic control
- simple_setup: Basic PPG → Processor setup for common test scenarios

All fixtures handle cleanup automatically via pytest's fixture system.
"""

import pytest
from tests.integration.utils import OSCMessageCapture, ComponentManager
from amor import osc


@pytest.fixture
def beat_capture():
    """Fixture providing OSC message capture on beat port.

    Starts thread-safe OSC capture server on PORT_BEATS (8001) with SO_REUSEPORT.
    Automatically stops capture on teardown.

    Yields:
        OSCMessageCapture: Message capture instance with wait_for_message(),
                          get_messages_by_address(), and clear() methods

    Example:
        def test_beat_message(beat_capture):
            ts, addr, args = beat_capture.wait_for_message("/beat/0", timeout=2.0)
            assert addr == "/beat/0"
    """
    capture = OSCMessageCapture(osc.PORT_BEATS)
    capture.start()
    yield capture
    capture.stop()


@pytest.fixture
def component_manager():
    """Fixture providing component lifecycle management with auto-cleanup.

    Creates ComponentManager for orchestrating multiple components (emulators,
    processor, audio, lighting). Automatically stops all components on teardown.

    Yields:
        ComponentManager: Manager with add_ppg_emulator(), add_processor(),
                         add_audio(), start_all(), and stop_all() methods

    Example:
        def test_processor(component_manager, beat_capture):
            component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
            component_manager.add_processor()
            component_manager.start_all()
            # ... test logic ...
            # Automatic cleanup on teardown
    """
    manager = ComponentManager()
    yield manager
    manager.stop_all()


@pytest.fixture
def simple_setup(component_manager, beat_capture):
    """Fixture providing basic PPG → Processor → Beat capture setup.

    Convenience fixture for common test scenario:
    - 1 PPG emulator (ID 0, 75 BPM)
    - Processor component
    - Beat message capture on port 8001

    All components start automatically and clean up on teardown.

    Yields:
        Tuple of (component_manager, beat_capture)

    Example:
        def test_beat_flow(simple_setup):
            manager, capture = simple_setup
            ts, addr, args = capture.wait_for_message("/beat/0", timeout=2.0)
            assert addr == "/beat/0"
    """
    component_manager.add_ppg_emulator(ppg_id=0, bpm=75)
    component_manager.add_processor()
    component_manager.start_all()

    return component_manager, beat_capture


@pytest.fixture
def control_capture():
    """Fixture providing OSC message capture on control port.

    Starts thread-safe OSC capture server on PORT_CONTROL (8003) with SO_REUSEPORT.
    Captures /route/*, /loop/*, and /select/* messages from sequencer.
    Automatically stops capture on teardown.

    Yields:
        OSCMessageCapture: Message capture instance with wait_for_message(),
                          get_messages_by_address(), and clear() methods

    Example:
        def test_routing(control_capture):
            ts, addr, args = control_capture.wait_for_message("/route/0", timeout=2.0)
            assert args[0] == 5  # Sample ID
    """
    capture = OSCMessageCapture(osc.PORT_CONTROL)
    capture.start()
    yield capture
    capture.stop()


@pytest.fixture
def launchpad_emulator():
    """Fixture providing launchpad emulator with programmatic API.

    Creates LaunchpadEmulator instance (not subprocess) for direct control.
    Provides methods like press_ppg_button(), toggle_loop(), get_led_state().
    Automatically stops emulator on teardown.

    The emulator uses the same control bus (PORT_CONTROL = 8003) for both
    sending button presses and receiving LED commands, matching the real
    launchpad architecture.

    Yields:
        LaunchpadEmulator: Emulator instance with control methods

    Example:
        def test_button_press(launchpad_emulator, control_capture):
            launchpad_emulator.press_ppg_button(0, 5)
            ts, addr, args = control_capture.wait_for_message("/select/0", timeout=2.0)
            assert args[0] == 5
    """
    import time
    from amor.simulator.launchpad_emulator import LaunchpadEmulator
    emulator = LaunchpadEmulator(control_port=8003)
    emulator.start()
    yield emulator
    emulator.stop()
    time.sleep(0.5)  # Allow port to be released
