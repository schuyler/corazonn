#!/usr/bin/env python3
"""
Sequencer - Amor Launchpad Integration State Manager

Manages sample selection and loop control state for Launchpad Mini MK3 integration.
Translates button presses from Launchpad Bridge to routing updates for audio engine.

ARCHITECTURE:
- OSC server listening on port 8003 for control messages from Launchpad Bridge
- OSC client sending routing updates to Audio Engine on port 8004
- OSC client sending LED state updates to Launchpad Bridge on port 8005
- Stateful sample selection (4 PPG sensors × 8 samples each)
- Stateful loop management (32 loops: 16 latching + 16 momentary)

STATE:
- sample_map: dict[int, int]      # PPG ID (0-3) → selected column (0-7)
- loop_status: dict[int, bool]    # Loop ID (0-31) → active/inactive

RESPONSIBILITIES:
On control message (from Launchpad Bridge on 8003):
1. Update state (sample_map or loop_status)
2. Send routing update /route/{ppg_id} [sample_id] to Audio (8004)
3. Send loop start/stop commands to Audio (8004)
4. Send LED state updates to Launchpad Bridge (8005)

On startup:
1. Load YAML config (amor/config/samples.yaml)
2. Initialize state (all PPGs → column 0, all loops off)
3. Send initial routing to Audio: /route/{0-3} [0]
4. Start OSC server on 8003

OSC PROTOCOL:

Input on 8003 (from Launchpad Bridge):
    /select/{ppg_id} [column]
      ppg_id: 0-3, column: 0-7
      Action: Update sample_map, send routing update to Audio, update LEDs

    /loop/toggle [loop_id]
      loop_id: 0-31 (rows 4-7, columns 0-7)
      Action: Toggle loop_status, send start/stop to Audio, update LEDs

    /loop/momentary [loop_id] [state]
      loop_id: 0-31, state: 1 (pressed) or 0 (released)
      Action: Send start/stop to Audio based on state, update LEDs

Output on 8004 (to Audio):
    /route/{ppg_id} [sample_id]
      ppg_id: 0-3
      sample_id: 0-7 (column index)
      Sent only when selection changes

    /loop/start [loop_id]
      loop_id: 0-31

    /loop/stop [loop_id]
      loop_id: 0-31

Output on 8005 (to Launchpad Bridge):
    /led/{row}/{col} [color, mode]
      row: 0-7, col: 0-7
      color: 0-127 (Launchpad palette index)
      mode: 0 (static), 1 (pulse), 2 (flash)

USAGE:
    # Start with default settings
    python3 -m amor.sequencer

    # Custom ports
    python3 -m amor.sequencer --control-port 8003 --audio-port 8004 --led-port 8005

    # Custom config
    python3 -m amor.sequencer --config amor/config/samples.yaml

Reference: docs/amor-sequencer-design.md
"""

import argparse
import sys
import re
import json
import time
from pathlib import Path
from typing import Optional, Tuple
import yaml
from pythonosc import dispatcher, udp_client

from amor import osc


# ============================================================================
# STATE PERSISTENCE CONSTANTS
# ============================================================================

STATE_VERSION = 1  # State file format version for future migrations

# ============================================================================
# LED COLOR CONSTANTS (Launchpad Mini MK3 Palette)
# ============================================================================

# PPG selection row colors
LED_COLOR_UNSELECTED = 45  # Dim blue
LED_COLOR_SELECTED = 37    # Bright cyan

# Loop row colors
LED_COLOR_LOOP_OFF = 0         # Off
LED_COLOR_LOOP_LATCHING = 21   # Green
LED_COLOR_LOOP_MOMENTARY = 13  # Yellow

# LED modes
LED_MODE_STATIC = 0
LED_MODE_PULSE = 1
LED_MODE_FLASH = 2


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_select_address(address: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """Validate /select/{ppg_id} address pattern.

    Args:
        address: OSC address string (e.g., "/select/0")

    Returns:
        Tuple of (is_valid, ppg_id, error_message):
            - is_valid: True if address matches pattern
            - ppg_id: Extracted PPG ID 0-3, None if invalid
            - error_message: Human-readable error if invalid, None if valid
    """
    pattern = re.compile(r'^/select/([0-3])$')
    match = pattern.match(address)
    if not match:
        return False, None, f"Invalid /select address: {address}"
    ppg_id = int(match.group(1))
    return True, ppg_id, None


def validate_column(column: int) -> Tuple[bool, Optional[str]]:
    """Validate column index is in range 0-7.

    Args:
        column: Column index

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(column, int):
        return False, f"Column must be integer, got {type(column)}"
    if column < 0 or column > 7:
        return False, f"Column must be in range 0-7, got {column}"
    return True, None


def validate_loop_id(loop_id: int) -> Tuple[bool, Optional[str]]:
    """Validate loop ID is in range 0-31.

    Args:
        loop_id: Loop ID

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(loop_id, int):
        return False, f"Loop ID must be integer, got {type(loop_id)}"
    if loop_id < 0 or loop_id > 31:
        return False, f"Loop ID must be in range 0-31, got {loop_id}"
    return True, None


def validate_momentary_state(state: int) -> Tuple[bool, Optional[str]]:
    """Validate momentary state is 0 or 1.

    Args:
        state: Momentary state

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(state, int):
        return False, f"State must be integer, got {type(state)}"
    if state not in (0, 1):
        return False, f"State must be 0 or 1, got {state}"
    return True, None


def loop_id_to_row_col(loop_id: int) -> Tuple[int, int]:
    """Convert loop ID to grid row/column.

    Loop IDs map to rows 4-7:
    - Loop 0-7: Row 4
    - Loop 8-15: Row 5
    - Loop 16-23: Row 6
    - Loop 24-31: Row 7

    Args:
        loop_id: Loop ID 0-31

    Returns:
        Tuple of (row, col)
    """
    row = 4 + (loop_id // 8)
    col = loop_id % 8
    return row, col


# ============================================================================
# CONFIG LOADING
# ============================================================================

def load_config(config_path: str) -> dict:
    """Load and validate YAML configuration.

    Args:
        config_path: Path to samples.yaml

    Returns:
        Parsed configuration dict

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config validation fails
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    # Validate structure
    if 'ppg_samples' not in config:
        raise ValueError("Config missing 'ppg_samples' section")
    if 'ambient_loops' not in config:
        raise ValueError("Config missing 'ambient_loops' section")

    # Validate PPG samples: 4 banks × 8 samples
    ppg_samples = config['ppg_samples']
    if len(ppg_samples) != 4:
        raise ValueError(f"Expected 4 PPG sample banks, got {len(ppg_samples)}")

    for ppg_id in range(4):
        if ppg_id not in ppg_samples:
            raise ValueError(f"Missing PPG sample bank {ppg_id}")
        samples = ppg_samples[ppg_id]
        if len(samples) != 8:
            raise ValueError(f"PPG {ppg_id} must have 8 samples, got {len(samples)}")

    # Validate ambient loops: 16 latching + 16 momentary
    loops = config['ambient_loops']
    if 'latching' not in loops:
        raise ValueError("Config missing 'ambient_loops.latching' section")
    if 'momentary' not in loops:
        raise ValueError("Config missing 'ambient_loops.momentary' section")

    if len(loops['latching']) != 16:
        raise ValueError(f"Expected 16 latching loops, got {len(loops['latching'])}")
    if len(loops['momentary']) != 16:
        raise ValueError(f"Expected 16 momentary loops, got {len(loops['momentary'])}")

    # Validate voice_limit (optional, default 3)
    voice_limit = config.get('voice_limit', 3)
    if not isinstance(voice_limit, int):
        raise ValueError(f"voice_limit must be an integer, got {type(voice_limit).__name__}")
    if voice_limit < 1 or voice_limit > 100:
        raise ValueError(f"voice_limit must be 1-100, got {voice_limit}")
    config['voice_limit'] = voice_limit

    # Check PPG sample file paths (warn if missing, don't fail)
    missing_ppg_samples = []
    for ppg_id, samples in ppg_samples.items():
        for i, sample_path in enumerate(samples):
            if not Path(sample_path).exists():
                missing_ppg_samples.append(f"PPG {ppg_id} sample {i}: {sample_path}")

    # Check loop file paths (warn if missing, don't fail)
    missing_loops = []
    for loop_type in ['latching', 'momentary']:
        for i, loop_path in enumerate(loops[loop_type]):
            if not Path(loop_path).exists():
                missing_loops.append(f"{loop_type.capitalize()} loop {i}: {loop_path}")

    print(f"Loaded config from {config_path}")
    print(f"  PPG samples: 4 banks × 8 samples = 32 total")
    print(f"  Ambient loops: 16 latching + 16 momentary = 32 total")
    print(f"  Voice limit: {config['voice_limit']}")

    if missing_ppg_samples or missing_loops:
        total_missing = len(missing_ppg_samples) + len(missing_loops)
        print(f"\nWARNING: {total_missing} sample files not found (buttons will no-op):")
        for path in missing_ppg_samples[:5]:  # Show first 5
            print(f"  - {path}")
        if len(missing_ppg_samples) > 5:
            print(f"  ... and {len(missing_ppg_samples) - 5} more PPG samples")
        for path in missing_loops[:5]:  # Show first 5
            print(f"  - {path}")
        if len(missing_loops) > 5:
            print(f"  ... and {len(missing_loops) - 5} more loops")
        print(f"Sequencer will run normally. Audio engine handles missing files.\n")
    else:
        print(f"  All file paths validated")

    return config


# ============================================================================
# SEQUENCER CLASS
# ============================================================================

class Sequencer:
    """Stateful sequencer for Launchpad sample selection and loop control.

    Manages mapping between PPG sensors and audio samples, tracks loop states,
    and coordinates OSC communication between Launchpad Bridge and Audio Engine.

    Architecture:
        - OSC server on control_port (default 8003) for Launchpad input
        - OSC client to audio_port (default 8004) for routing/loop commands
        - OSC client to led_port (default 8005) for LED feedback
        - State persistence to state_path (default: amor/state/sequencer_state.json)
        - Graceful recovery via /status/ready handshake

    Attributes:
        control_port (int): Port for receiving control messages (default 8003)
        audio_port (int): Port for sending audio routing (default 8004)
        led_port (int): Port for sending LED updates (default 8005)
        state_path (str): Path to state file (default: amor/state/sequencer_state.json)
        config (dict): Loaded YAML configuration
        sample_map (dict): PPG ID → selected column
        loop_status (dict): Loop ID → active/inactive
        audio_client (udp_client.SimpleUDPClient): OSC client for audio commands
        led_client (udp_client.SimpleUDPClient): OSC client for LED updates
        stats (osc.MessageStatistics): Message counters
    """

    def __init__(
        self,
        config_path: str = "amor/config/samples.yaml",
        control_port: int = 8003,
        audio_port: int = 8004,
        led_port: int = 8005,
        state_path: str = "amor/state/sequencer_state.json"
    ):
        """Initialize sequencer and load configuration.

        Args:
            config_path: Path to samples.yaml (default: amor/config/samples.yaml)
            control_port: Port for receiving control messages (default: 8003)
            audio_port: Port for sending audio routing (default: 8004)
            led_port: Port for sending LED updates (default: 8005)
            state_path: Path to state file (default: amor/state/sequencer_state.json)

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config validation fails or ports are invalid
        """
        # Validate ports
        osc.validate_port(control_port)
        osc.validate_port(audio_port)
        osc.validate_port(led_port)

        self.control_port = control_port
        self.audio_port = audio_port
        self.led_port = led_port
        self.state_path = state_path

        # Load config
        self.config = load_config(config_path)

        # Load persisted state (or initialize defaults)
        self.load_state()

        # Create OSC clients for output
        self.audio_client = udp_client.SimpleUDPClient("127.0.0.1", audio_port)
        self.led_client = udp_client.SimpleUDPClient("127.0.0.1", led_port)

        # Statistics
        self.stats = osc.MessageStatistics()

        print(f"Sequencer initialized")
        print(f"  Control input: port {control_port}")
        print(f"  Audio output: port {audio_port}")
        print(f"  LED output: port {led_port}")
        print(f"  State file: {state_path}")

    def load_state(self):
        """Load state from disk, or initialize defaults if file doesn't exist.

        Loads sample_map and loop_status from JSON state file.
        Falls back to defaults if file missing or corrupt.

        State file format:
            {
                "version": 1,
                "sample_map": {"0": 0, "1": 0, "2": 0, "3": 0},
                "loop_status": {"0": false, "1": false, ...},
                "timestamp": 1234567890.123
            }
        """
        state_path = Path(self.state_path)

        if state_path.exists():
            try:
                with open(state_path, 'r') as f:
                    state = json.load(f)

                # Validate version (for future migrations)
                version = state.get('version', 1)
                if version != STATE_VERSION:
                    print(f"WARNING: State file version {version} != expected {STATE_VERSION}")
                    print(f"         Using defaults. State file may need migration.")
                    self._initialize_default_state()
                    return

                # Load state with integer key conversion (JSON keys are strings)
                self.sample_map = {int(k): v for k, v in state.get('sample_map', {}).items()}
                self.loop_status = {int(k): v for k, v in state.get('loop_status', {}).items()}

                # Validate loaded state
                if len(self.sample_map) != 4 or not all(k in self.sample_map for k in range(4)):
                    print(f"WARNING: Invalid sample_map in state file, using defaults")
                    self._initialize_default_state()
                    return

                if len(self.loop_status) != 32 or not all(k in self.loop_status for k in range(32)):
                    print(f"WARNING: Invalid loop_status in state file, using defaults")
                    self._initialize_default_state()
                    return

                timestamp = state.get('timestamp', 0)
                print(f"Loaded state from {self.state_path}")
                print(f"  State timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}")
                return

            except Exception as e:
                print(f"WARNING: Failed to load state: {e}")
                print(f"         Using defaults")

        # Initialize defaults if file doesn't exist or failed to load
        self._initialize_default_state()

    def _initialize_default_state(self):
        """Initialize default state values."""
        # All PPG sensors start at column 0
        self.sample_map = {0: 0, 1: 0, 2: 0, 3: 0}

        # All loops start inactive
        self.loop_status = {loop_id: False for loop_id in range(32)}

    def save_state(self):
        """Persist current state to disk.

        Writes state atomically using temp file + rename to avoid corruption.
        Logs warning if write fails but continues operation.
        """
        state_path = Path(self.state_path)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            'version': STATE_VERSION,
            'sample_map': self.sample_map,
            'loop_status': self.loop_status,
            'timestamp': time.time()
        }

        try:
            # Atomic write: write to temp file, then rename
            temp_path = state_path.with_suffix('.json.tmp')
            with open(temp_path, 'w') as f:
                json.dump(state, f, indent=2)
            temp_path.replace(state_path)
        except Exception as e:
            print(f"WARNING: Failed to save state: {e}")

    def broadcast_full_state(self):
        """Broadcast complete state to all components (routing + LEDs).

        Called when components send /status/ready signal after restart.
        Sends all routing updates and LED updates.
        """
        print("Broadcasting full state to all components...")

        # Send routing to audio
        for ppg_id in range(4):
            sample_id = self.sample_map[ppg_id]
            self.audio_client.send_message(f"/route/{ppg_id}", sample_id)

        # Send all LED updates
        for row in range(4):
            self.update_ppg_row_leds(row)

        for loop_id in range(32):
            self.update_loop_led(loop_id)

        self.stats.increment('reconnections')
        print("  Full state broadcast complete")

    def handle_status_ready(self, address: str, *args):
        """Handle component ready signals.

        When components restart, they send /status/ready/{component} to signal
        they're ready to receive state. Sequencer responds with full state broadcast.

        Args:
            address: OSC address (e.g., "/status/ready/launchpad")
            *args: Message arguments (none expected)
        """
        self.stats.increment('total_messages')

        # Parse address: /status/ready/{component}
        parts = address.split('/')
        if len(parts) == 4 and parts[1] == 'status' and parts[2] == 'ready':
            component = parts[3]
            print(f"Component ready: {component}")
            self.broadcast_full_state()
        else:
            self.stats.increment('invalid_messages')
            print(f"WARNING: Invalid /status/ready address: {address}")

    def send_initial_routing(self):
        """Send initial routing state to audio engine.

        Sends /route/{ppg_id} [0] for all 4 PPG sensors to set
        initial sample selection (column 0 for all).
        """
        print("Sending initial routing to audio engine...")
        for ppg_id in range(4):
            sample_id = self.sample_map[ppg_id]
            address = f"/route/{ppg_id}"
            self.audio_client.send_message(address, sample_id)
            print(f"  {address} {sample_id}")

    def send_initial_leds(self):
        """Send initial LED state to Launchpad Bridge.

        Sets LEDs for PPG rows (column 0 selected with pulse mode, others unselected with flash mode)
        and all loop rows (all off with static mode).
        """
        print("Sending initial LED state to Launchpad Bridge...")

        # PPG rows (0-3): column 0 selected (pulse), others unselected (flash)
        for row in range(4):
            for col in range(8):
                if col == 0:
                    color = LED_COLOR_SELECTED
                    mode = LED_MODE_PULSE  # Selected button pulses brighter on beat
                else:
                    color = LED_COLOR_UNSELECTED
                    mode = LED_MODE_FLASH  # Unselected buttons flash on beat
                self.led_client.send_message(f"/led/{row}/{col}", [color, mode])

        # Loop rows (4-7): all off, static (no beat pulse)
        for row in range(4, 8):
            for col in range(8):
                self.led_client.send_message(f"/led/{row}/{col}", [LED_COLOR_LOOP_OFF, LED_MODE_STATIC])

        print("  Initial LED state sent")

    def update_ppg_row_leds(self, ppg_id: int):
        """Update LED state for a PPG row after selection change.

        Args:
            ppg_id: PPG sensor ID (0-3)
        """
        row = ppg_id
        selected_col = self.sample_map[ppg_id]

        for col in range(8):
            if col == selected_col:
                color = LED_COLOR_SELECTED
                mode = LED_MODE_PULSE  # Selected button pulses brighter on beat
            else:
                color = LED_COLOR_UNSELECTED
                mode = LED_MODE_FLASH  # Unselected buttons flash on beat
            self.led_client.send_message(f"/led/{row}/{col}", [color, mode])

    def update_loop_led(self, loop_id: int):
        """Update LED state for a loop button.

        Args:
            loop_id: Loop ID (0-31)
        """
        row, col = loop_id_to_row_col(loop_id)
        is_active = self.loop_status[loop_id]

        # Determine color based on loop type and state
        if is_active:
            # Rows 4-5 are latching (green), rows 6-7 are momentary (yellow)
            if row < 6:
                color = LED_COLOR_LOOP_LATCHING
            else:
                color = LED_COLOR_LOOP_MOMENTARY
        else:
            color = LED_COLOR_LOOP_OFF

        self.led_client.send_message(f"/led/{row}/{col}", [color, LED_MODE_STATIC])

    def handle_select(self, address: str, *args):
        """Handle /select/{ppg_id} [column] message.

        Updates sample selection for specified PPG sensor, sends routing
        update to audio engine, and updates LED state.

        Args:
            address: OSC address (e.g., "/select/0")
            *args: Message arguments [column]
        """
        self.stats.increment('total_messages')

        # Validate address
        is_valid, ppg_id, error_msg = validate_select_address(address)
        if not is_valid:
            self.stats.increment('invalid_messages')
            print(f"WARNING: {error_msg}")
            return

        # Validate arguments
        if len(args) != 1:
            self.stats.increment('invalid_messages')
            print(f"WARNING: /select expects 1 argument, got {len(args)}")
            return

        try:
            column = int(args[0])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            print(f"WARNING: Invalid column value: {args[0]} ({e})")
            return

        is_valid, error_msg = validate_column(column)
        if not is_valid:
            self.stats.increment('invalid_messages')
            print(f"WARNING: {error_msg}")
            return

        # Update state
        old_column = self.sample_map[ppg_id]
        self.sample_map[ppg_id] = column

        # Persist state
        self.save_state()

        # Send routing update to audio engine
        self.audio_client.send_message(f"/route/{ppg_id}", column)

        # Update LEDs
        self.update_ppg_row_leds(ppg_id)

        self.stats.increment('select_messages')
        print(f"SELECT: PPG {ppg_id}, column {old_column} → {column}")

    def handle_loop_toggle(self, address: str, *args):
        """Handle /loop/toggle [loop_id] message.

        Toggles loop state, sends start/stop command to audio engine,
        and updates LED state.

        Args:
            address: OSC address ("/loop/toggle")
            *args: Message arguments [loop_id]
        """
        self.stats.increment('total_messages')

        # Validate arguments
        if len(args) != 1:
            self.stats.increment('invalid_messages')
            print(f"WARNING: /loop/toggle expects 1 argument, got {len(args)}")
            return

        try:
            loop_id = int(args[0])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            print(f"WARNING: Invalid loop_id value: {args[0]} ({e})")
            return

        is_valid, error_msg = validate_loop_id(loop_id)
        if not is_valid:
            self.stats.increment('invalid_messages')
            print(f"WARNING: {error_msg}")
            return

        # Toggle state
        old_state = self.loop_status[loop_id]
        new_state = not old_state
        self.loop_status[loop_id] = new_state

        # Persist state
        self.save_state()

        # Send command to audio engine
        if new_state:
            self.audio_client.send_message("/loop/start", loop_id)
            action = "START"
        else:
            self.audio_client.send_message("/loop/stop", loop_id)
            action = "STOP"

        # Update LED
        self.update_loop_led(loop_id)

        self.stats.increment('loop_toggle_messages')
        print(f"LOOP TOGGLE: Loop {loop_id} → {action}")

    def handle_loop_momentary(self, address: str, *args):
        """Handle /loop/momentary [loop_id] [state] message.

        Starts/stops loop based on button press/release, sends command
        to audio engine, and updates LED state.

        Args:
            address: OSC address ("/loop/momentary")
            *args: Message arguments [loop_id, state]
        """
        self.stats.increment('total_messages')

        # Validate arguments
        if len(args) != 2:
            self.stats.increment('invalid_messages')
            print(f"WARNING: /loop/momentary expects 2 arguments, got {len(args)}")
            return

        try:
            loop_id = int(args[0])
            state = int(args[1])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            print(f"WARNING: Invalid loop_id or state value: {args[0]}, {args[1]} ({e})")
            return

        is_valid, error_msg = validate_loop_id(loop_id)
        if not is_valid:
            self.stats.increment('invalid_messages')
            print(f"WARNING: {error_msg}")
            return

        is_valid, error_msg = validate_momentary_state(state)
        if not is_valid:
            self.stats.increment('invalid_messages')
            print(f"WARNING: {error_msg}")
            return

        # Update state
        is_pressed = (state == 1)
        self.loop_status[loop_id] = is_pressed

        # Persist state
        self.save_state()

        # Send command to audio engine
        if is_pressed:
            self.audio_client.send_message("/loop/start", loop_id)
            action = "START (pressed)"
        else:
            self.audio_client.send_message("/loop/stop", loop_id)
            action = "STOP (released)"

        # Update LED
        self.update_loop_led(loop_id)

        self.stats.increment('loop_momentary_messages')
        print(f"LOOP MOMENTARY: Loop {loop_id} → {action}")

    def run(self):
        """Start the OSC server and process control messages.

        Blocks indefinitely, listening for control messages from
        Launchpad Bridge on control_port.

        Message flow:
            1. Send initial routing and LED state
            2. Listen for control messages
            3. Update state and send commands
            4. Handle Ctrl+C gracefully with statistics

        Side effects:
            - Sends initial routing to audio engine
            - Sends initial LED state to Launchpad Bridge
            - Prints status messages to console
            - Handles KeyboardInterrupt
            - Prints final statistics on shutdown
        """
        # Send initial state
        self.send_initial_routing()
        self.send_initial_leds()

        # Create dispatcher and bind handlers
        disp = dispatcher.Dispatcher()
        disp.map("/select/*", self.handle_select)
        disp.map("/loop/toggle", self.handle_loop_toggle)
        disp.map("/loop/momentary", self.handle_loop_momentary)
        disp.map("/status/ready/*", self.handle_status_ready)

        # Create OSC server
        server = osc.ReusePortBlockingOSCUDPServer(
            ("0.0.0.0", self.control_port),
            disp
        )

        print(f"\nSequencer listening on port {self.control_port}")
        print(f"Expecting control messages from Launchpad Bridge:")
        print(f"  /select/{{0-3}} [column]")
        print(f"  /loop/toggle [loop_id]")
        print(f"  /loop/momentary [loop_id] [state]")
        print(f"Waiting for messages... (Ctrl+C to stop)\n")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        except Exception as e:
            print(f"\nERROR: Server crashed: {e}", file=sys.stderr)
        finally:
            server.shutdown()
            self.stats.print_stats("SEQUENCER STATISTICS")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point with command-line argument parsing.

    Parses arguments for port configuration and config file path,
    creates Sequencer instance, and handles runtime errors.

    Command-line arguments:
        --control-port N    Port for control input (default: 8003)
        --audio-port N      Port for audio output (default: 8004)
        --led-port N        Port for LED output (default: 8005)
        --config PATH       Path to samples.yaml (default: amor/config/samples.yaml)

    Example usage:
        python3 -m amor.sequencer
        python3 -m amor.sequencer --control-port 8003
        python3 -m amor.sequencer --config /path/to/samples.yaml

    Validation:
        - All ports must be in range 1-65535
        - Config file must exist and be valid YAML
        - Exits with error code 1 if validation fails
    """
    parser = argparse.ArgumentParser(
        description="Sequencer - Launchpad sample selection state manager"
    )
    parser.add_argument(
        "--control-port",
        type=int,
        default=8003,
        help="Port for control input from Launchpad Bridge (default: 8003)",
    )
    parser.add_argument(
        "--audio-port",
        type=int,
        default=8004,
        help="Port for audio routing output to Audio Engine (default: 8004)",
    )
    parser.add_argument(
        "--led-port",
        type=int,
        default=8005,
        help="Port for LED output to Launchpad Bridge (default: 8005)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="amor/config/samples.yaml",
        help="Path to samples.yaml config (default: amor/config/samples.yaml)",
    )
    parser.add_argument(
        "--state-path",
        type=str,
        default="amor/state/sequencer_state.json",
        help="Path to state file (default: amor/state/sequencer_state.json)",
    )

    args = parser.parse_args()

    # Create and run sequencer
    try:
        sequencer = Sequencer(
            config_path=args.config,
            control_port=args.control_port,
            audio_port=args.audio_port,
            led_port=args.led_port,
            state_path=args.state_path
        )
        sequencer.run()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: Port {args.control_port} already in use", file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
