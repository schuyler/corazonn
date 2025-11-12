"""State inspection utilities for emulators."""

from typing import Dict, Optional, Tuple, Any
import time

# import requests  # Reserved for future remote inspection feature


class BulbStateInspector:
    """Inspects Kasa bulb emulator state via HTTP or direct access.

    Provides convenient assertions for validating bulb state changes
    in integration tests.

    Example:
        inspector = BulbStateInspector(ip="127.0.0.1", port=9999)
        inspector.assert_brightness_above(50, timeout=2.0)
        inspector.assert_hue_in_range(110, 130)
    """

    def __init__(self, emulator=None, ip: Optional[str] = None, port: Optional[int] = None):
        """Initialize bulb state inspector.

        Args:
            emulator: Direct reference to KasaBulbEmulator instance (if available)
            ip: IP address of bulb emulator (for remote inspection)
            port: TCP port of bulb emulator
        """
        self.emulator = emulator
        self.ip = ip
        self.port = port

    def get_state(self) -> Dict[str, Any]:
        """Get current bulb state.

        Returns:
            Dictionary with keys: name, is_on, hue, saturation, brightness,
            command_count, state_changes
        """
        if self.emulator:
            return self.emulator.get_state()
        else:
            raise NotImplementedError(
                "Remote state inspection not yet implemented. "
                "Pass emulator instance directly for now."
            )

    def get_brightness(self) -> int:
        """Get current brightness (0-100)."""
        return int(self.get_state()["brightness"])

    def get_hue(self) -> int:
        """Get current hue (0-360)."""
        return int(self.get_state()["hue"])

    def get_saturation(self) -> int:
        """Get current saturation (0-100)."""
        return int(self.get_state()["saturation"])

    def get_state_changes(self) -> int:
        """Get count of state changes since start."""
        return int(self.get_state()["state_changes"])

    def wait_for_state_change(self, initial_count: Optional[int] = None, timeout: float = 5.0) -> bool:
        """Wait for bulb state to change.

        Args:
            initial_count: Starting state change count (None to fetch current)
            timeout: Maximum seconds to wait

        Returns:
            True if state changed, False if timeout
        """
        if initial_count is None:
            initial_count = self.get_state_changes()

        start = time.time()
        while time.time() - start < timeout:
            if self.get_state_changes() > initial_count:
                return True
            time.sleep(0.05)
        return False

    def assert_brightness_above(self, threshold: int, timeout: float = 5.0) -> None:
        """Assert brightness rises above threshold within timeout.

        Args:
            threshold: Minimum brightness value
            timeout: Maximum seconds to wait

        Raises:
            AssertionError: If brightness doesn't exceed threshold
        """
        start = time.time()
        while time.time() - start < timeout:
            brightness = self.get_brightness()
            if brightness > threshold:
                return
            time.sleep(0.05)

        brightness = self.get_brightness()
        raise AssertionError(
            f"Brightness {brightness} did not exceed {threshold} within {timeout}s"
        )

    def assert_brightness_below(self, threshold: int, timeout: float = 5.0) -> None:
        """Assert brightness falls below threshold within timeout.

        Args:
            threshold: Maximum brightness value
            timeout: Maximum seconds to wait

        Raises:
            AssertionError: If brightness doesn't fall below threshold
        """
        start = time.time()
        while time.time() - start < timeout:
            brightness = self.get_brightness()
            if brightness < threshold:
                return
            time.sleep(0.05)

        brightness = self.get_brightness()
        raise AssertionError(
            f"Brightness {brightness} did not fall below {threshold} within {timeout}s"
        )

    def assert_hue_in_range(self, min_hue: int, max_hue: int) -> None:
        """Assert hue is within specified range.

        Args:
            min_hue: Minimum hue (0-360)
            max_hue: Maximum hue (0-360)

        Raises:
            AssertionError: If hue outside range
        """
        hue = self.get_hue()
        assert min_hue <= hue <= max_hue, \
            f"Hue {hue}° outside range [{min_hue}°, {max_hue}°]"

    def assert_state_changes(self, min_changes: int, timeout: float = 5.0) -> None:
        """Assert at least min_changes state changes occurred.

        Args:
            min_changes: Minimum expected state changes
            timeout: Time to wait for changes

        Raises:
            AssertionError: If not enough state changes
        """
        initial = self.get_state_changes()
        time.sleep(timeout)
        final = self.get_state_changes()
        changes = final - initial

        assert changes >= min_changes, \
            f"Expected at least {min_changes} state changes, got {changes}"


class LaunchpadStateInspector:
    """Inspects Launchpad emulator state.

    Provides convenient assertions for validating LED state and button
    selections in integration tests.

    Example:
        inspector = LaunchpadStateInspector(emulator)
        inspector.assert_led_state(row=0, col=3, color=COLOR_CYAN, mode=MODE_PULSE)
        inspector.assert_ppg_selected(ppg_id=0, column=3)
    """

    def __init__(self, emulator):
        """Initialize launchpad state inspector.

        Args:
            emulator: LaunchpadEmulator instance
        """
        self.emulator = emulator

    def get_led_state(self, row: int, col: int) -> Optional[Tuple[int, int]]:
        """Get LED state at position.

        Args:
            row: Row index (0-3)
            col: Column index (0-7)

        Returns:
            Tuple of (color, mode) or None if unset
        """
        return self.emulator.get_led_state(row, col)

    def get_ppg_selection(self, ppg_id: int) -> Optional[int]:
        """Get selected column for PPG row.

        Args:
            ppg_id: PPG ID (0-3)

        Returns:
            Selected column index (0-7) or None if none selected
        """
        return self.emulator.get_ppg_selection(ppg_id)

    def assert_led_state(self, row: int, col: int, color: int, mode: int, timeout: float = 2.0) -> None:
        """Assert LED has expected color and mode.

        Args:
            row: Row index (0-3)
            col: Column index (0-7)
            color: Expected color code
            mode: Expected mode (0=static, 1=pulse, 2=flash)
            timeout: Maximum seconds to wait for state

        Raises:
            AssertionError: If LED state doesn't match
        """
        start = time.time()
        while time.time() - start < timeout:
            state = self.get_led_state(row, col)
            if state == (color, mode):
                return
            time.sleep(0.05)

        state = self.get_led_state(row, col)
        raise AssertionError(
            f"LED ({row}, {col}) state {state} != expected ({color}, {mode})"
        )

    def assert_ppg_selected(self, ppg_id: int, column: int, timeout: float = 2.0) -> None:
        """Assert PPG has selected column.

        Args:
            ppg_id: PPG ID (0-3)
            column: Expected selected column (0-7)
            timeout: Maximum seconds to wait

        Raises:
            AssertionError: If selection doesn't match
        """
        start = time.time()
        while time.time() - start < timeout:
            selected = self.get_ppg_selection(ppg_id)
            if selected == column:
                return
            time.sleep(0.05)

        selected = self.get_ppg_selection(ppg_id)
        raise AssertionError(
            f"PPG {ppg_id} selected column {selected} != expected {column}"
        )


class PPGStateInspector:
    """Inspects PPG emulator state.

    Provides convenient access to PPG emulator parameters and statistics.

    Example:
        inspector = PPGStateInspector(emulator)
        inspector.assert_bpm_in_range(70, 80)
        inspector.assert_messages_sent(min_count=10)
    """

    def __init__(self, emulator):
        """Initialize PPG state inspector.

        Args:
            emulator: PPGEmulator instance
        """
        self.emulator = emulator

    def get_bpm(self) -> float:
        """Get current BPM setting."""
        return float(self.emulator.bpm)

    def get_message_count(self) -> int:
        """Get total OSC messages sent."""
        return int(self.emulator.message_count)

    def is_in_dropout(self) -> bool:
        """Check if currently in dropout."""
        return bool(self.emulator.in_dropout)

    def assert_bpm_in_range(self, min_bpm: float, max_bpm: float) -> None:
        """Assert BPM is within range.

        Args:
            min_bpm: Minimum BPM
            max_bpm: Maximum BPM

        Raises:
            AssertionError: If BPM outside range
        """
        bpm = self.get_bpm()
        assert min_bpm <= bpm <= max_bpm, \
            f"BPM {bpm} outside range [{min_bpm}, {max_bpm}]"

    def assert_messages_sent(self, min_count: int, timeout: float = 5.0) -> None:
        """Assert at least min_count messages were sent.

        Args:
            min_count: Minimum expected message count
            timeout: Time to wait for messages

        Raises:
            AssertionError: If not enough messages sent
        """
        initial = self.get_message_count()
        time.sleep(timeout)
        final = self.get_message_count()
        sent = final - initial

        assert sent >= min_count, \
            f"Expected at least {min_count} messages, got {sent}"
