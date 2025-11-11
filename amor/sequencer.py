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
from pathlib import Path
from typing import Optional, Tuple
import yaml
from pythonosc import dispatcher, udp_client

from amor import osc


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

    # Voice limit (optional, default 3)
    config.setdefault('voice_limit', 3)

    print(f"Loaded config from {config_path}")
    print(f"  PPG samples: 4 banks × 8 samples = 32 total")
    print(f"  Ambient loops: 16 latching + 16 momentary = 32 total")
    print(f"  Voice limit: {config['voice_limit']}")

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

    Attributes:
        control_port (int): Port for receiving control messages (default 8003)
        audio_port (int): Port for sending audio routing (default 8004)
        led_port (int): Port for sending LED updates (default 8005)
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
        led_port: int = 8005
    ):
        """Initialize sequencer and load configuration.

        Args:
            config_path: Path to samples.yaml (default: amor/config/samples.yaml)
            control_port: Port for receiving control messages (default: 8003)
            audio_port: Port for sending audio routing (default: 8004)
            led_port: Port for sending LED updates (default: 8005)

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

        # Load config
        self.config = load_config(config_path)

        # Initialize state
        # All PPG sensors start at column 0
        self.sample_map = {0: 0, 1: 0, 2: 0, 3: 0}

        # All loops start inactive
        self.loop_status = {loop_id: False for loop_id in range(32)}

        # Create OSC clients for output
        self.audio_client = udp_client.SimpleUDPClient("127.0.0.1", audio_port)
        self.led_client = udp_client.SimpleUDPClient("127.0.0.1", led_port)

        # Statistics
        self.stats = osc.MessageStatistics()

        print(f"Sequencer initialized")
        print(f"  Control input: port {control_port}")
        print(f"  Audio output: port {audio_port}")
        print(f"  LED output: port {led_port}")

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

        Sets LEDs for PPG rows (column 0 selected, others unselected)
        and all loop rows (all off).
        """
        print("Sending initial LED state to Launchpad Bridge...")

        # PPG rows (0-3): column 0 selected, others unselected
        for row in range(4):
            for col in range(8):
                if col == 0:
                    color = LED_COLOR_SELECTED
                else:
                    color = LED_COLOR_UNSELECTED
                self.led_client.send_message(f"/led/{row}/{col}", [color, LED_MODE_STATIC])

        # Loop rows (4-7): all off
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
            else:
                color = LED_COLOR_UNSELECTED
            self.led_client.send_message(f"/led/{row}/{col}", [color, LED_MODE_STATIC])

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

        column = int(args[0])
        is_valid, error_msg = validate_column(column)
        if not is_valid:
            self.stats.increment('invalid_messages')
            print(f"WARNING: {error_msg}")
            return

        # Update state
        old_column = self.sample_map[ppg_id]
        self.sample_map[ppg_id] = column

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

        loop_id = int(args[0])
        is_valid, error_msg = validate_loop_id(loop_id)
        if not is_valid:
            self.stats.increment('invalid_messages')
            print(f"WARNING: {error_msg}")
            return

        # Toggle state
        old_state = self.loop_status[loop_id]
        new_state = not old_state
        self.loop_status[loop_id] = new_state

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

        loop_id = int(args[0])
        state = int(args[1])

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

    args = parser.parse_args()

    # Create and run sequencer
    try:
        sequencer = Sequencer(
            config_path=args.config,
            control_port=args.control_port,
            audio_port=args.audio_port,
            led_port=args.led_port
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
