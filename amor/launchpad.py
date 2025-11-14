#!/usr/bin/env python3
"""
Amor Launchpad Bridge - MIDI ↔ OSC translator for Launchpad MK1.

Pure I/O translation layer between Launchpad MK1 MIDI and OSC protocol.
Handles button presses, LED feedback, and beat pulse visualization.

NOTE: This implementation is verified for Launchpad MK1 hardware only.
MIDI mappings are specific to the Novation Launchpad model in use.

Architecture:
    MIDI Input → OSC Control Messages → Sequencer (PORT_CONTROL)
    Sequencer (PORT_CONTROL) → OSC LED Commands → MIDI Output (broadcast bus)
    Processor (PORT_BEATS) → OSC Beat Messages → LED Pulse Effects

Grid Layout (8×8):
    Rows 0-3: PPG sample selection (radio buttons)
    Rows 4-5: Latching loops (toggle on/off)
    Rows 6-7: Momentary loops (play while pressed)

See docs/amor-sequencer-design.md for complete protocol specification.
"""

import sys
import signal
import threading
import time
from typing import Optional, Dict, Set, Tuple
from pythonosc import udp_client, dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

from amor import osc
from amor.log import get_logger

logger = get_logger("launchpad")

try:
    import mido
except ImportError:
    logger.error("mido not installed. Run: pip install mido python-rtmidi")
    sys.exit(1)


# ============================================================================
# CONSTANTS
# ============================================================================

# Port assignments (use osc.py constants)
PORT_BEAT_INPUT = osc.PORT_BEATS      # Beat messages from processor (SO_REUSEPORT)
PORT_CONTROL_OUTPUT = osc.PORT_CONTROL  # Control messages to sequencer (broadcast)
PORT_LED_INPUT = osc.PORT_CONTROL       # LED commands from sequencer (broadcast bus)

# Launchpad device name patterns
LAUNCHPAD_NAMES = ["Launchpad"]

# SysEx message to enter Programmer Mode
SYSEX_PROGRAMMER_MODE = [0xF0, 0x00, 0x20, 0x29, 0x02, 0x0D, 0x0E, 0x01, 0xF7]

# LED color palette indices (Novation Launchpad)
COLOR_OFF = 0
COLOR_DIM_BLUE = 45         # Unselected PPG buttons
COLOR_BRIGHT_CYAN = 37      # Selected PPG button (static)
COLOR_GREEN = 21            # Active latching loop
COLOR_YELLOW = 13           # Active momentary loop (pressed)

# Beat pulse timing (seconds)
BEAT_FLASH_DURATION = 0.1   # Duration for row flash
BEAT_PULSE_DURATION = 0.15  # Duration for selected button pulse

# Grid dimensions
GRID_ROWS = 8
GRID_COLS = 8

# Control button mappings (Launchpad MK1 - VERIFIED WITH HARDWARE)
# Scene buttons (right side, 8 buttons) - send Note messages
# Pattern: note = 8 + (scene_id * 16)
SCENE_BUTTON_NOTES = [8, 24, 40, 56, 72, 88, 104, 120]

# Control buttons (top row, 8 buttons) - send Control Change (CC) messages, NOT Note messages!
# CC numbers 104-111 with values: 127 = pressed, 0 = released
CONTROL_BUTTON_CCS = list(range(104, 112))  # CC 104-111


# ============================================================================
# GRID MAPPING
# ============================================================================

def note_to_grid(note: int) -> Optional[Tuple[int, int]]:
    """Convert MIDI note number to grid row/column.

    Launchpad grid pads map to notes 11-18, 21-28, ..., 81-88.

    Args:
        note: MIDI note number (11-88)

    Returns:
        Tuple of (row, col) where row/col are 0-7, or None if invalid note

    Examples:
        >>> note_to_grid(11)  # Top-left button
        (0, 0)
        >>> note_to_grid(88)  # Bottom-right button
        (7, 7)
    """
    row = (note // 10) - 1
    col = (note % 10) - 1

    if row < 0 or row >= GRID_ROWS or col < 0 or col >= GRID_COLS:
        return None

    return row, col


def grid_to_note(row: int, col: int) -> int:
    """Convert grid row/column to MIDI note number.

    Args:
        row: Grid row (0-7)
        col: Grid column (0-7)

    Returns:
        MIDI note number (11-88)

    Examples:
        >>> grid_to_note(0, 0)  # Top-left button
        11
        >>> grid_to_note(7, 7)  # Bottom-right button
        88
    """
    return (row + 1) * 10 + (col + 1)


def grid_to_loop_id(row: int, col: int) -> Optional[int]:
    """Convert grid position to loop ID for rows 4-7.

    Args:
        row: Grid row (4-7)
        col: Grid column (0-7)

    Returns:
        Loop ID (0-31) or None if row is not 4-7

    Examples:
        >>> grid_to_loop_id(4, 0)  # First latching loop
        0
        >>> grid_to_loop_id(7, 7)  # Last momentary loop
        31
    """
    if row < 4 or row > 7:
        return None

    return (row - 4) * 8 + col


def note_to_scene_id(note: int) -> Optional[int]:
    """Convert MIDI note to scene button ID (0-7).

    Args:
        note: MIDI note number (89-96 for scene buttons)

    Returns:
        Scene ID (0-7) or None if not a scene button

    Examples:
        >>> note_to_scene_id(89)  # Scene 0
        0
        >>> note_to_scene_id(96)  # Scene 7
        7
    """
    if note in SCENE_BUTTON_NOTES:
        return SCENE_BUTTON_NOTES.index(note)
    return None


def note_to_control_id(note: int) -> Optional[int]:
    """Convert MIDI note to control button ID (0-7).

    Args:
        note: MIDI note number (104-111 for control buttons)

    Returns:
        Control ID (0-7) or None if not a control button

    Examples:
        >>> note_to_control_id(104)  # Control 0
        0
        >>> note_to_control_id(111)  # Control 7
        7
    """
    if note in CONTROL_BUTTON_NOTES:
        return CONTROL_BUTTON_NOTES.index(note)
    return None


def cc_to_control_id(cc_num: int) -> Optional[int]:
    """Convert MIDI Control Change number to control button ID (0-7).

    Args:
        cc_num: MIDI CC number (104-111 for control buttons)

    Returns:
        Control ID (0-7) or None if not a control button CC

    Examples:
        >>> cc_to_control_id(104)  # Control 0
        0
        >>> cc_to_control_id(111)  # Control 7
        7
    """
    if cc_num in CONTROL_BUTTON_CCS:
        return CONTROL_BUTTON_CCS.index(cc_num)
    return None


# ============================================================================
# LAUNCHPAD BRIDGE
# ============================================================================

class LaunchpadBridge:
    """MIDI ↔ OSC bridge for Novation Launchpad.

    Responsibilities:
        - Translate MIDI button presses to OSC control messages
        - Translate OSC LED commands to MIDI output
        - Listen for beat messages and pulse LEDs on beats
        - Maintain LED state for selection and loop status

    State:
        selected_columns: dict[int, int] - PPG ID (0-3) → selected column (0-7)
        active_loops: set[int] - Set of active loop IDs (0-31)
        pressed_momentary: set[int] - Set of currently pressed momentary loop IDs
    """

    def __init__(self, midi_input: mido.ports.BaseInput,
                 midi_output: mido.ports.BaseOutput):
        """Initialize Launchpad bridge.

        Args:
            midi_input: Mido input port for Launchpad
            midi_output: Mido output port for Launchpad
        """
        self.midi_input = midi_input
        self.midi_output = midi_output

        # OSC clients for sending control messages
        self.control_client = udp_client.SimpleUDPClient("127.0.0.1", PORT_CONTROL_OUTPUT)

        # LED state tracking (protected by state_lock)
        self.selected_columns: Dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
        self.active_loops: Set[int] = set()
        self.pressed_momentary: Set[int] = set()
        self.led_colors: Dict[Tuple[int, int], int] = {}  # (row, col) -> color
        self.led_modes: Dict[Tuple[int, int], int] = {}  # (row, col) -> mode
        self.scene_led_colors: Dict[int, int] = {}  # scene_id -> color
        self.scene_led_modes: Dict[int, int] = {}  # scene_id -> mode

        # Beat pulse timing state (protected by timer_lock)
        self.pulse_timers: Dict[int, threading.Timer] = {}

        # Threading locks
        self.state_lock = threading.Lock()  # Protects LED state, selections, loops
        self.timer_lock = threading.Lock()  # Protects pulse_timers dict

        # Statistics
        self.stats = osc.MessageStatistics()

        # Shutdown flag
        self.running = True

    def start(self):
        """Start the Launchpad bridge.

        Initializes:
            1. Enter Programmer Mode via SysEx
            2. Initialize LED grid (PPG row 0 selected, all loops off)
            3. Start MIDI input thread
            4. Start OSC servers for LED commands and beat messages
        """
        logger.info("Starting Launchpad Bridge...")

        # Enter Programmer Mode
        self._enter_programmer_mode()

        # Initialize LED grid
        self._initialize_leds()

        # Start MIDI input thread
        midi_thread = threading.Thread(target=self._midi_input_loop, daemon=True)
        midi_thread.start()

        # Start OSC servers
        self._start_osc_servers()

    def _enter_programmer_mode(self):
        """Send SysEx message to enter Programmer Mode."""
        sysex_msg = mido.Message('sysex', data=SYSEX_PROGRAMMER_MODE[1:-1])
        self.midi_output.send(sysex_msg)
        logger.info("Entered Programmer Mode")

    def _initialize_leds(self):
        """Initialize LED grid to default state.

        PPG rows (0-3): Column 0 selected (bright cyan with pulse), others dim blue (flash)
        Loop rows (4-7): All off (static)
        """
        # PPG rows: initial state matches what sequencer will send
        for row in range(4):
            for col in range(8):
                if col == 0:
                    color = COLOR_BRIGHT_CYAN
                    mode = 1  # PULSE mode for selected
                else:
                    color = COLOR_DIM_BLUE
                    mode = 2  # FLASH mode for unselected
                self.led_colors[(row, col)] = color
                self.led_modes[(row, col)] = mode
                self._set_led(row, col, color)

        # Loop rows: all off, static
        for row in range(4, 8):
            for col in range(8):
                self.led_colors[(row, col)] = COLOR_OFF
                self.led_modes[(row, col)] = 0  # STATIC mode
                self._set_led(row, col, COLOR_OFF)

        logger.info("Initialized LED grid")

    def _set_led(self, row: int, col: int, color: int, velocity: Optional[int] = None):
        """Set LED color using MIDI Note On message.

        Args:
            row: Grid row (0-7)
            col: Grid column (0-7)
            color: Color palette index (0-127)
            velocity: Optional velocity override (default: use color as velocity)
        """
        note = grid_to_note(row, col)
        vel = velocity if velocity is not None else color
        msg = mido.Message('note_on', note=note, velocity=vel)
        self.midi_output.send(msg)

    def _set_scene_led(self, scene_id: int, color: int):
        """Set scene button LED color using MIDI Note On message.

        Args:
            scene_id: Scene button ID (0-7)
            color: Color palette index (0-127)
        """
        if not 0 <= scene_id <= 7:
            logger.warning(f"Invalid scene_id {scene_id}, must be 0-7")
            return

        note = SCENE_BUTTON_NOTES[scene_id]
        msg = mido.Message('note_on', note=note, velocity=color)
        self.midi_output.send(msg)

    def _calculate_pulse_color(self, base_color: int) -> int:
        """Calculate brighter pulse color from base color.

        Uses a simple offset to create a brighter variant for beat pulses.
        Can be enhanced with a lookup table if specific colors need custom mappings.

        Args:
            base_color: Base color palette index (0-127)

        Returns:
            Pulse color palette index (brighter variant)
        """
        # Simple offset approach - add 4 for brighter variant
        pulse_color = base_color + 4
        return min(pulse_color, 127)  # Clamp to valid palette range

    def _midi_input_loop(self):
        """MIDI input processing loop (runs in separate thread).

        Note: This uses blocking iteration over self.midi_input.
        On shutdown, the thread will exit when self.running becomes False,
        but may block until the next MIDI message arrives.
        """
        logger.info("MIDI input thread started")

        # Note: mido's input port iteration is blocking. The running flag
        # check will only execute between messages. For clean shutdown,
        # OSC servers are stopped which is more critical than this thread.
        for msg in self.midi_input:
            if not self.running:
                break

            if msg.type == 'note_on' or msg.type == 'note_off':
                self._handle_button_event(msg)
            elif msg.type == 'control_change':
                self._handle_control_change(msg)

        logger.info("MIDI input thread exiting")

    def _handle_button_event(self, msg: mido.Message):
        """Handle button press/release from Launchpad.

        Args:
            msg: MIDI message (note_on or note_off)
        """
        is_press = msg.type == 'note_on' and msg.velocity > 0
        self.stats.increment('button_events')

        # Try grid button first
        grid_pos = note_to_grid(msg.note)
        if grid_pos is not None:
            row, col = grid_pos

            # PPG rows (0-3): Radio button selection
            if row < 4:
                if is_press:
                    self._handle_ppg_selection(row, col)

            # Loop rows (4-5): Latching toggles
            elif row < 6:
                if is_press:
                    self._handle_loop_toggle(row, col)

            # Loop rows (6-7): Momentary triggers
            else:
                self._handle_loop_momentary(row, col, is_press)
            return

        # Try scene button
        scene_id = note_to_scene_id(msg.note)
        if scene_id is not None:
            self._handle_scene_button(scene_id, is_press)
            return

        # Try control button
        control_id = note_to_control_id(msg.note)
        if control_id is not None:
            self._handle_control_button(control_id, is_press)
            return

        # Unknown button - log and ignore
        self.stats.increment('unknown_button_events')
        logger.warning(f"Unknown button press: note {msg.note}, type {msg.type}, velocity {msg.velocity}")

    def _handle_ppg_selection(self, row: int, col: int):
        """Handle PPG sample selection button press.

        Args:
            row: PPG ID (0-3)
            col: Column selection (0-7)
        """
        ppg_id = row

        with self.state_lock:
            old_col = self.selected_columns[ppg_id]

            # Update state
            self.selected_columns[ppg_id] = col

            # Update LEDs (deselect old, select new) and store colors/modes
            self.led_colors[(row, old_col)] = COLOR_DIM_BLUE
            self.led_modes[(row, old_col)] = 2  # FLASH mode for unselected
            self._set_led(row, old_col, COLOR_DIM_BLUE)

            self.led_colors[(row, col)] = COLOR_BRIGHT_CYAN
            self.led_modes[(row, col)] = 1  # PULSE mode for selected
            self._set_led(row, col, COLOR_BRIGHT_CYAN)

        # Send OSC message to sequencer (outside lock)
        self.control_client.send_message(f"/select/{ppg_id}", [col])
        self.stats.increment('select_messages')

    def _handle_loop_toggle(self, row: int, col: int):
        """Handle latching loop toggle button press.

        Args:
            row: Grid row (4-5)
            col: Grid column (0-7)
        """
        loop_id = grid_to_loop_id(row, col)
        if loop_id is None:
            return

        with self.state_lock:
            # Toggle state and update LED with stored color/mode
            if loop_id in self.active_loops:
                self.active_loops.remove(loop_id)
                self.led_colors[(row, col)] = COLOR_OFF
                self.led_modes[(row, col)] = 0  # STATIC mode
                self._set_led(row, col, COLOR_OFF)
            else:
                self.active_loops.add(loop_id)
                self.led_colors[(row, col)] = COLOR_GREEN
                self.led_modes[(row, col)] = 0  # STATIC mode
                self._set_led(row, col, COLOR_GREEN)

        # Send OSC message to sequencer (outside lock)
        self.control_client.send_message("/loop/toggle", [loop_id])
        self.stats.increment('loop_toggle_messages')

    def _handle_loop_momentary(self, row: int, col: int, is_press: bool):
        """Handle momentary loop button press/release.

        Args:
            row: Grid row (6-7)
            col: Grid column (0-7)
            is_press: True if pressed, False if released
        """
        loop_id = grid_to_loop_id(row, col)
        if loop_id is None:
            return

        state = 1 if is_press else 0

        with self.state_lock:
            # Update state and LED with stored color/mode
            if is_press:
                self.pressed_momentary.add(loop_id)
                self.led_colors[(row, col)] = COLOR_YELLOW
                self.led_modes[(row, col)] = 0  # STATIC mode
                self._set_led(row, col, COLOR_YELLOW)
            else:
                self.pressed_momentary.discard(loop_id)
                self.led_colors[(row, col)] = COLOR_OFF
                self.led_modes[(row, col)] = 0  # STATIC mode
                self._set_led(row, col, COLOR_OFF)

        # Send OSC message to sequencer (outside lock)
        self.control_client.send_message("/loop/momentary", [loop_id, state])
        self.stats.increment('loop_momentary_messages')

    def _handle_scene_button(self, scene_id: int, is_press: bool):
        """Handle scene button press/release.

        Args:
            scene_id: Scene ID (0-7)
            is_press: True if pressed, False if released
        """
        state = 1 if is_press else 0

        # Send OSC message to sequencer
        self.control_client.send_message("/scene", [scene_id, state])
        self.stats.increment('scene_button_messages')

    def _handle_control_button(self, control_id: int, is_press: bool):
        """Handle control button press/release.

        Args:
            control_id: Control ID (0-7)
            is_press: True if pressed, False if released
        """
        state = 1 if is_press else 0

        # Send OSC message to sequencer
        self.control_client.send_message("/control", [control_id, state])
        self.stats.increment('control_button_messages')

    def _handle_control_change(self, msg: mido.Message):
        """Handle Control Change (CC) message from Launchpad.

        Control buttons on Launchpad MK1 send CC messages (not Note messages).
        CC 104-111 with values 127=pressed, 0=released.

        Args:
            msg: MIDI control_change message
        """
        control_id = cc_to_control_id(msg.control)
        if control_id is None:
            return

        is_press = msg.value > 64  # 127 = pressed, 0 = released
        self._handle_control_button(control_id, is_press)

    def _start_osc_servers(self):
        """Start OSC servers for LED commands and beat messages."""
        # LED command server (port 8005)
        led_dispatcher = dispatcher.Dispatcher()
        led_dispatcher.map("/led/*/*", self._handle_led_command)
        led_dispatcher.map("/led/scene/*", self._handle_scene_led_command)
        led_server = BlockingOSCUDPServer(("0.0.0.0", PORT_LED_INPUT), led_dispatcher)

        # Beat message server (port 8001, ReusePort)
        beat_dispatcher = dispatcher.Dispatcher()
        beat_dispatcher.map("/beat/*", self._handle_beat_message)
        beat_server = osc.ReusePortBlockingOSCUDPServer(("0.0.0.0", PORT_BEAT_INPUT), beat_dispatcher)

        # Start servers in threads
        led_thread = threading.Thread(target=led_server.serve_forever, daemon=True)
        beat_thread = threading.Thread(target=beat_server.serve_forever, daemon=True)

        led_thread.start()
        beat_thread.start()

        # Wait for threads to initialize and bind sockets
        time.sleep(0.1)

        logger.info(f"Listening for LED commands on port {PORT_LED_INPUT}")
        logger.info(f"Listening for beat messages on port {PORT_BEAT_INPUT} (ReusePort)")

        # Store servers for shutdown
        self.led_server = led_server
        self.beat_server = beat_server

        # Send ready signal to sequencer for state restoration
        ready_client = udp_client.SimpleUDPClient("127.0.0.1", PORT_CONTROL_OUTPUT)
        ready_client.send_message("/status/ready/launchpad", [])
        logger.info("Sent ready signal to sequencer")

    def _handle_led_command(self, address: str, *args):
        """Handle LED command from sequencer.

        OSC format: /led/{row}/{col} [color, mode]

        Args:
            address: OSC address (/led/row/col)
            args: [color, mode] where mode is 0=static, 1=pulse, 2=flash
        """
        # Parse address
        parts = address.split('/')
        if len(parts) != 4:
            return

        try:
            row = int(parts[2])
            col = int(parts[3])
        except (ValueError, IndexError):
            return

        if len(args) < 2:
            return

        color = int(args[0])
        mode = int(args[1])

        # Validate mode
        if mode not in (0, 1, 2):
            logger.warning(f"Invalid LED mode {mode} for position ({row},{col}), ignoring")
            self.stats.increment('invalid_messages')
            return

        with self.state_lock:
            # Store color and mode for beat pulse behavior
            self.led_colors[(row, col)] = color
            self.led_modes[(row, col)] = mode

            # Set LED to current color
            self._set_led(row, col, color)

        self.stats.increment('led_commands')

    def _handle_scene_led_command(self, address: str, *args):
        """Handle scene LED command from sequencer.

        OSC format: /led/scene/{scene_id} [color, mode]

        Args:
            address: OSC address (/led/scene/scene_id)
            args: [color, mode] where mode is 0=static, 1=pulse, 2=flash/blink
        """
        # Parse address
        parts = address.split('/')
        if len(parts) != 4:
            return

        try:
            scene_id = int(parts[3])
        except (ValueError, IndexError):
            return

        if not 0 <= scene_id <= 7:
            logger.warning(f"Invalid scene_id {scene_id}, must be 0-7")
            self.stats.increment('invalid_messages')
            return

        if len(args) < 2:
            return

        try:
            color = int(args[0])
            mode = int(args[1])
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid color/mode values for scene {scene_id}: {e}")
            self.stats.increment('invalid_messages')
            return

        # Validate mode
        if mode not in (0, 1, 2):
            logger.warning(f"Invalid LED mode {mode} for scene {scene_id}, ignoring")
            self.stats.increment('invalid_messages')
            return

        with self.state_lock:
            # Store color and mode for reference
            self.scene_led_colors[scene_id] = color
            self.scene_led_modes[scene_id] = mode

            # Set scene LED
            # NOTE: Mode behavior (pulse/flash) not actively managed by bridge.
            # Sequencer is responsible for implementing blinking by repeatedly
            # sending LED updates (e.g., alternating color/off for flash effect).
            # This matches the design where sequencer controls all LED timing.
            self._set_scene_led(scene_id, color)

        self.stats.increment('led_commands')

    def _handle_beat_message(self, address: str, *args):
        """Handle beat message for LED pulse effect.

        OSC format: /beat/{ppg_id} [timestamp, bpm, intensity]

        Pulse effect based on LED mode:
            mode=0 (static): No pulse effect
            mode=1 (pulse): Pulse button brighter (typically selected button)
            mode=2 (flash): Flash button on beat (typically unselected buttons)

        Args:
            address: OSC address (/beat/ppg_id)
            args: Beat parameters (timestamp, bpm, intensity)
        """
        # Parse PPG ID from address
        parts = address.split('/')
        if len(parts) != 3:
            return

        try:
            ppg_id = int(parts[2])
        except (ValueError, IndexError):
            return

        if ppg_id < 0 or ppg_id > 3:
            return

        row = ppg_id

        self.stats.increment('beat_messages')

        # Snapshot state atomically at pulse time
        with self.state_lock:
            selected_col = self.selected_columns[ppg_id]
            # Capture color/mode snapshot for restoration
            color_snapshot = {}
            for col in range(8):
                color_snapshot[col] = self.led_colors.get((row, col), COLOR_DIM_BLUE)
                mode = self.led_modes.get((row, col), 0)

                # Apply beat effect based on each button's mode
                if mode == 1:  # PULSE mode (selected button pulses brighter)
                    if col == selected_col:
                        pulse_color = self._calculate_pulse_color(color_snapshot[col])
                        self._set_led(row, col, pulse_color)
                elif mode == 2:  # FLASH mode (entire row flashes)
                    pulse_color = self._calculate_pulse_color(color_snapshot[col])
                    self._set_led(row, col, pulse_color)
                # mode == 0 (STATIC): do nothing on beat

        # Schedule restoration using snapshot (not live state)
        def restore_colors():
            with self.state_lock:
                for col in range(8):
                    # Restore from snapshot captured at pulse time
                    self._set_led(row, col, color_snapshot[col])

        # Update timers atomically
        with self.timer_lock:
            # Cancel any existing timer for this row
            if row in self.pulse_timers:
                self.pulse_timers[row].cancel()

            # Start new timer
            timer = threading.Timer(BEAT_PULSE_DURATION, restore_colors)
            timer.start()
            self.pulse_timers[row] = timer

    def shutdown(self):
        """Shutdown the Launchpad bridge gracefully."""
        logger.info("Shutting down Launchpad Bridge...")
        self.running = False

        # Cancel all pulse timers (thread-safe)
        with self.timer_lock:
            for timer in self.pulse_timers.values():
                timer.cancel()
            self.pulse_timers.clear()

        # Clear LED grid
        for row in range(8):
            for col in range(8):
                self._set_led(row, col, COLOR_OFF)

        # Clear scene LEDs
        for scene_id in range(8):
            self._set_scene_led(scene_id, COLOR_OFF)

        # Close MIDI ports
        self.midi_input.close()
        self.midi_output.close()

        # Shutdown OSC servers
        if hasattr(self, 'led_server'):
            self.led_server.shutdown()
        if hasattr(self, 'beat_server'):
            self.beat_server.shutdown()

        # Print statistics
        self.stats.print_stats("LAUNCHPAD BRIDGE STATISTICS")


# ============================================================================
# MAIN
# ============================================================================

def find_launchpad() -> Tuple[Optional[str], Optional[str]]:
    """Find Launchpad MIDI ports.

    Returns:
        Tuple of (input_port_name, output_port_name) or (None, None) if not found
    """
    input_ports = mido.get_input_names()
    output_ports = mido.get_output_names()

    input_port = None
    output_port = None

    for name in LAUNCHPAD_NAMES:
        for port in input_ports:
            if name in port:
                input_port = port
                break
        for port in output_ports:
            if name in port:
                output_port = port
                break

    return input_port, output_port


def main():
    """Main entry point for Launchpad bridge."""
    logger.info("=" * 60)
    logger.info("AMOR LAUNCHPAD BRIDGE")
    logger.info("=" * 60)

    # Find Launchpad
    input_port, output_port = find_launchpad()

    if input_port is None or output_port is None:
        logger.warning("Launchpad not found")
        logger.warning("Bridge will not start (hardware not connected)")
        logger.info("Available MIDI input ports:")
        for port in mido.get_input_names():
            logger.info(f"  - {port}")
        logger.info("Available MIDI output ports:")
        for port in mido.get_output_names():
            logger.info(f"  - {port}")
        logger.info("Exiting gracefully (not an error condition)")
        sys.exit(0)

    logger.info(f"Found Launchpad:")
    logger.info(f"  Input: {input_port}")
    logger.info(f"  Output: {output_port}")

    # Open MIDI ports
    midi_input = mido.open_input(input_port)
    midi_output = mido.open_output(output_port)

    # Create and start bridge
    bridge = LaunchpadBridge(midi_input, midi_output)

    # Setup signal handlers
    def signal_handler(sig, frame):
        bridge.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start bridge
    bridge.start()

    logger.info("Launchpad bridge running. Press Ctrl+C to exit.")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.shutdown()


if __name__ == "__main__":
    main()
