#!/usr/bin/env python3
"""
Sequencer - Amor Launchpad Integration State Manager

Manages sample selection and loop control state for Launchpad Mini MK3 integration.
Translates button presses from Launchpad Bridge to routing updates for audio engine.

ARCHITECTURE:
- OSC server listening on PORT_CONTROL (8003) for control messages
- OSC broadcast client sending all messages to PORT_CONTROL (8003)
- Broadcast bus allows Audio, Launchpad, and Sequencer to communicate
- All components filter messages by OSC address pattern
- Stateful sample selection (4 PPG sensors × 8 samples each)
- Stateful loop management (32 loops: 16 latching + 16 momentary)

STATE:
- sample_map: dict[int, int]      # PPG ID (0-3) → selected column (0-7)
- loop_status: dict[int, bool]    # Loop ID (0-31) → active/inactive

RESPONSIBILITIES:
On control message (from Launchpad Bridge via PORT_CONTROL):
1. Update state (sample_map or loop_status)
2. Broadcast routing update /route/{ppg_id} [sample_id] to PORT_CONTROL
3. Broadcast loop start/stop commands to PORT_CONTROL
4. Broadcast LED state updates to PORT_CONTROL

On startup:
1. Load YAML config (amor/config/samples.yaml)
2. Initialize state (all PPGs → column 0, all loops off)
3. Broadcast initial routing to PORT_CONTROL: /route/{0-3} [0]
4. Start OSC server on PORT_CONTROL (8003)

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

    /scene [scene_id] [state]
      scene_id: 0-7 (right side scene buttons), state: 1 (pressed) or 0 (released)
      Action: Sampler control (scene 0-3: recording, scene 4-7: virtual channels)

    /control [control_id] [state]
      control_id: 0-7 (top side control buttons), state: 1 (pressed) or 0 (released)
      Action: Currently logs event. Future: tempo, volume, effects, etc.

Output on PORT_CONTROL (broadcast to Audio, Launchpad, Sampler):
    /route/{ppg_id} [sample_id]
      ppg_id: 0-3
      sample_id: 0-7 (column index)
      Sent only when selection changes
      Received by: Audio Engine

    /loop/start [loop_id]
      loop_id: 0-31
      Received by: Audio Engine

    /loop/stop [loop_id]
      loop_id: 0-31
      Received by: Audio Engine

    /sampler/record/toggle [source_ppg]
      source_ppg: 0-3
      Received by: Sampler

    /sampler/assign [dest_channel]
      dest_channel: 4-7
      Received by: Sampler

    /sampler/toggle [dest_channel]
      dest_channel: 4-7
      Received by: Sampler

    /led/{row}/{col} [color, mode]
      row: 0-7, col: 0-7
      color: 0-127 (Launchpad palette index)
      mode: 0 (static), 1 (pulse), 2 (flash)
      Received by: Launchpad Bridge

    /led/scene/{scene_id} [color, mode]
      scene_id: 0-7
      color: 0-127 (Launchpad palette index)
      mode: 0 (static), 1 (pulse), 2 (flash)
      Received by: Launchpad Bridge

Input from Sampler on PORT_CONTROL:
    /sampler/status/recording [source_ppg] [active]
      source_ppg: 0-3, active: 0 or 1

    /sampler/status/assignment [active]
      active: 0 or 1

    /sampler/status/playback [dest_channel] [active]
      dest_channel: 4-7, active: 0 or 1

USAGE:
    # Start with default settings
    python3 -m amor.sequencer

    # Custom control port
    python3 -m amor.sequencer --control-port 8003

    # Custom config
    python3 -m amor.sequencer --config amor/config/samples.yaml

Reference: docs/amor-sequencer-design.md
"""

import argparse
import os
import sys
import re
import json
import time
from pathlib import Path
from typing import Optional, Tuple, Set
import yaml
from pythonosc import dispatcher, udp_client

from amor import osc
from amor.log import get_logger

logger = get_logger(__name__)


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

# Sampler scene button colors
LED_COLOR_RECORDING = 5        # Red
LED_COLOR_ASSIGNMENT = 21      # Green (blinking)
LED_COLOR_PLAYING = 21         # Green (solid)
LED_COLOR_SCENE_OFF = 0        # Off

# LED modes
LED_MODE_STATIC = 0
LED_MODE_PULSE = 1
LED_MODE_FLASH = 2

# Control mode LED colors
LED_COLOR_CONTROL_ACTIVE = 21  # Green - control mode active
LED_COLOR_CONTROL_INACTIVE = 0  # Off - control mode inactive

# Grid LED colors for control modes
LED_COLOR_MODE_AVAILABLE = 45  # Dim blue - available option
LED_COLOR_MODE_SELECTED = 37   # Bright cyan - selected option

# Lighting program ID to name mapping
LIGHTING_PROGRAMS = {
    0: 'soft_pulse',
    1: 'rotating_gradient',
    2: 'breathing_sync',
    3: 'convergence',
    4: 'wave_chase',
    5: 'intensity_reactive'
}

# BPM multiplier values (mapped to columns 0-6)
BPM_MULTIPLIERS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

# Effect names (mapped to columns 1-5, column 0 = clear all)
EFFECT_NAMES = ['reverb', 'phaser', 'delay', 'chorus', 'lowpass']


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

    # Validate PPG samples: 4 PPG sensors with named banks of 8 samples each
    ppg_samples = config['ppg_samples']
    if len(ppg_samples) != 4:
        raise ValueError(f"Expected 4 PPG sensor configurations, got {len(ppg_samples)}")

    total_banks = 0
    for ppg_id in range(4):
        if ppg_id not in ppg_samples:
            raise ValueError(f"Missing PPG {ppg_id} configuration")

        banks = ppg_samples[ppg_id]
        if not isinstance(banks, dict):
            raise ValueError(f"PPG {ppg_id} must have named banks (dict), got {type(banks).__name__}")

        if 'default' not in banks:
            raise ValueError(f"PPG {ppg_id} must have a 'default' bank")

        if len(banks) == 0:
            raise ValueError(f"PPG {ppg_id} must have at least one bank")

        for bank_name, samples in banks.items():
            if not isinstance(samples, list):
                raise ValueError(f"PPG {ppg_id} bank '{bank_name}' must be a list of samples")
            if len(samples) != 8:
                raise ValueError(f"PPG {ppg_id} bank '{bank_name}' must have 8 samples, got {len(samples)}")
            total_banks += 1

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
    for ppg_id, banks in ppg_samples.items():
        for bank_name, samples in banks.items():
            for i, sample_path in enumerate(samples):
                if not Path(sample_path).exists():
                    missing_ppg_samples.append(f"PPG {ppg_id} bank '{bank_name}' sample {i}: {sample_path}")

    # Check loop file paths (warn if missing, don't fail)
    missing_loops = []
    for loop_type in ['latching', 'momentary']:
        for i, loop_path in enumerate(loops[loop_type]):
            if not Path(loop_path).exists():
                missing_loops.append(f"{loop_type.capitalize()} loop {i}: {loop_path}")

    logger.info(f"Loaded config from {config_path}")
    logger.info(f"  PPG samples: 4 sensors × {total_banks} banks × 8 samples = {total_banks * 8} total")
    logger.info(f"  Ambient loops: 16 latching + 16 momentary = 32 total")
    logger.info(f"  Voice limit: {config['voice_limit']}")

    if missing_ppg_samples or missing_loops:
        total_missing = len(missing_ppg_samples) + len(missing_loops)
        logger.warning(f"{total_missing} sample files not found (buttons will no-op):")
        for path in missing_ppg_samples[:5]:  # Show first 5
            logger.warning(f"  - {path}")
        if len(missing_ppg_samples) > 5:
            logger.warning(f"  ... and {len(missing_ppg_samples) - 5} more PPG samples")
        for path in missing_loops[:5]:  # Show first 5
            logger.warning(f"  - {path}")
        if len(missing_loops) > 5:
            logger.warning(f"  ... and {len(missing_loops) - 5} more loops")
        logger.warning(f"Sequencer will run normally. Audio engine handles missing files.")
    else:
        logger.info(f"  All file paths validated")

    return config


# ============================================================================
# SEQUENCER CLASS
# ============================================================================

class Sequencer:
    """Stateful sequencer for Launchpad sample selection and loop control.

    Manages mapping between PPG sensors and audio samples, tracks loop states,
    and coordinates OSC communication between Launchpad Bridge and Audio Engine.

    Architecture:
        - OSC server on control_port (default: osc.PORT_CONTROL = 8003) for Launchpad input
        - OSC broadcast client to control_port for all output messages
        - Broadcast bus allows Audio, Launchpad, and Sequencer to communicate
        - All components use SO_REUSEPORT and filter by OSC address pattern
        - State persistence to state_path (default: amor/state/sequencer_state.json)
        - Graceful recovery via /status/ready handshake

    Attributes:
        control_port (int): Port for control bus (default: osc.PORT_CONTROL = 8003)
        state_path (str): Path to state file (default: amor/state/sequencer_state.json)
        config (dict): Loaded YAML configuration
        sample_map (dict): PPG ID → selected column
        loop_status (dict): Loop ID → active/inactive
        control_client (osc.BroadcastUDPClient): OSC broadcast client for control bus
        stats (osc.MessageStatistics): Message counters
    """

    def __init__(
        self,
        config_path: str = "amor/config/samples.yaml",
        control_port: int = osc.PORT_CONTROL,
        state_path: str = "amor/state/sequencer_state.json"
    ):
        """Initialize sequencer and load configuration.

        Args:
            config_path: Path to samples.yaml (default: amor/config/samples.yaml)
            control_port: Port for control bus (default: osc.PORT_CONTROL)
            state_path: Path to state file (default: amor/state/sequencer_state.json)

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config validation fails or port is invalid
        """
        # Validate port
        osc.validate_port(control_port)

        self.control_port = control_port
        self.state_path = state_path

        # Load config
        self.config = load_config(config_path)

        # Load persisted state (or initialize defaults)
        self.load_state()

        # Sampler state (not persisted - transient session state)
        self.recording_ppgs: set = set()  # PPG 0-3 currently being recorded (supports multiple)
        self.assignment_mode: bool = False  # Waiting for virtual channel assignment
        self.active_virtuals: dict = {4: False, 5: False, 6: False, 7: False}  # Virtual channels playing

        # Control mode state (not persisted - transient session state)
        self.active_control_mode: Optional[int] = None  # None, 0, 1, 2, 3
        self.current_lighting_program: int = 0  # 0-5
        self.current_bpm_multiplier: float = 1.0  # 0.25-3.0
        # PPG sample banks: PPG 0-7 → bank index 0-7
        # Virtual PPGs 4-7 use modulo-4 mapping for sample banks (share with physical 0-3)
        self.ppg_sample_banks: dict = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        # PPG effects: PPG 0-7 → set of effect names
        # Each PPG (0-7) has an independent effect chain
        self.ppg_effects: dict = {i: set() for i in range(8)}

        # Create single broadcast OSC client for all control messages (255.255.255.255:PORT_CONTROL)
        # All components (Sequencer, Audio, Launchpad) listen and filter by address pattern
        self.control_client = osc.BroadcastUDPClient("255.255.255.255", control_port)

        # Statistics
        self.stats = osc.MessageStatistics()

        logger.info(f"Sequencer initialized")
        logger.info(f"  Control port: {control_port}")
        logger.info(f"  State file: {state_path}")

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
                    logger.warning(f"State file version {version} != expected {STATE_VERSION}")
                    logger.warning(f"Using defaults. State file may need migration.")
                    self._initialize_default_state()
                    return

                # Load state with integer key conversion (JSON keys are strings)
                self.sample_map = {int(k): v for k, v in state.get('sample_map', {}).items()}
                self.bank_map = {int(k): v for k, v in state.get('bank_map', {}).items()}
                self.loop_status = {int(k): v for k, v in state.get('loop_status', {}).items()}

                # Validate loaded state
                if len(self.sample_map) != 4 or not all(k in self.sample_map for k in range(4)):
                    logger.warning(f"Invalid sample_map in state file, using defaults")
                    self._initialize_default_state()
                    return

                # Validate or initialize bank_map (backwards compatibility)
                if len(self.bank_map) != 4 or not all(k in self.bank_map for k in range(4)):
                    logger.info(f"Initializing bank_map to 'default' (backwards compatibility)")
                    self.bank_map = {0: "default", 1: "default", 2: "default", 3: "default"}

                if len(self.loop_status) != 32 or not all(k in self.loop_status for k in range(32)):
                    logger.warning(f"Invalid loop_status in state file, using defaults")
                    self._initialize_default_state()
                    return

                timestamp = state.get('timestamp', 0)
                logger.info(f"Loaded state from {self.state_path}")
                logger.info(f"  State timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}")
                return

            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
                logger.warning(f"Using defaults")

        # Initialize defaults if file doesn't exist or failed to load
        self._initialize_default_state()

    def _initialize_default_state(self):
        """Initialize default state values."""
        # All PPG sensors start at column 0
        self.sample_map = {0: 0, 1: 0, 2: 0, 3: 0}

        # All PPG sensors start with 'default' bank
        self.bank_map = {0: "default", 1: "default", 2: "default", 3: "default"}

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
            'bank_map': self.bank_map,
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
            logger.warning(f"Failed to save state: {e}")

    def broadcast_full_state(self):
        """Broadcast complete state to all components (routing + LEDs).

        Called when components send /status/ready signal after restart.
        Sends all routing updates and LED updates.
        """
        logger.info("Broadcasting full state to all components...")

        # Send bank state to audio
        for ppg_id in range(4):
            bank_name = self.bank_map[ppg_id]
            self.control_client.send_message("/load_bank", [ppg_id, bank_name])

        # Send routing to audio
        for ppg_id in range(4):
            sample_id = self.sample_map[ppg_id]
            self.control_client.send_message(f"/route/{ppg_id}", sample_id)

        # Send all LED updates
        for row in range(4):
            self.update_ppg_row_leds(row)

        for loop_id in range(32):
            self.update_loop_led(loop_id)

        self.stats.increment('reconnections')
        logger.info("  Full state broadcast complete")

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
            logger.info(f"Component ready: {component}")
            self.broadcast_full_state()
        else:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid /status/ready address: {address}")

    def send_initial_routing(self):
        """Send initial routing state to audio engine.

        Sends /route/{ppg_id} [0] for all 4 PPG sensors to set
        initial sample selection (column 0 for all).
        """
        logger.info("Sending initial routing to audio engine...")
        for ppg_id in range(4):
            sample_id = self.sample_map[ppg_id]
            address = f"/route/{ppg_id}"
            self.control_client.send_message(address, sample_id)
            logger.info(f"  {address} {sample_id}")

    def send_initial_leds(self):
        """Send initial LED state to Launchpad Bridge.

        Sets LEDs for PPG rows (column 0 selected with pulse mode, others unselected with flash mode)
        and all loop rows (all off with static mode).
        """
        logger.info("Sending initial LED state to Launchpad Bridge...")

        # PPG rows (0-3): column 0 selected (pulse), others unselected (flash)
        for row in range(4):
            for col in range(8):
                if col == 0:
                    color = LED_COLOR_SELECTED
                    mode = LED_MODE_PULSE  # Selected button pulses brighter on beat
                else:
                    color = LED_COLOR_UNSELECTED
                    mode = LED_MODE_FLASH  # Unselected buttons flash on beat
                self.control_client.send_message(f"/led/{row}/{col}", [color, mode])

        # Loop rows (4-7): all off, static (no beat pulse)
        for row in range(4, 8):
            for col in range(8):
                self.control_client.send_message(f"/led/{row}/{col}", [LED_COLOR_LOOP_OFF, LED_MODE_STATIC])

        logger.info("  Initial LED state sent")

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
            self.control_client.send_message(f"/led/{row}/{col}", [color, mode])

    def enter_control_mode(self, control_id: int):
        """Enter a control mode.

        Sets active_control_mode, lights control button LED, and updates
        all grid LEDs to show mode-specific layout.

        Args:
            control_id: Control mode to enter (0-3)
        """
        self.active_control_mode = control_id

        # Light up control button LED
        self.control_client.send_message(f"/led/control/{control_id}", [LED_COLOR_CONTROL_ACTIVE, LED_MODE_STATIC])

        # Update grid LEDs based on mode
        if control_id == 0:
            self.update_lighting_mode_leds()
        elif control_id == 1:
            self.update_bpm_mode_leds()
        elif control_id == 2:
            self.update_bank_mode_leds()
        elif control_id == 3:
            self.update_effects_mode_leds()

    def exit_control_mode(self, restore_leds: bool = True):
        """Exit current control mode.

        Clears active_control_mode, turns off control button LED, and
        optionally restores normal grid LED state.

        Args:
            restore_leds: If True, restore normal grid LEDs. Set to False when
                         switching modes to avoid LED flash.
        """
        if self.active_control_mode is None:
            return

        # Turn off control button LED
        self.control_client.send_message(f"/led/control/{self.active_control_mode}", [LED_COLOR_CONTROL_INACTIVE, LED_MODE_STATIC])

        self.active_control_mode = None

        # Restore normal grid LEDs (unless switching modes)
        if restore_leds:
            for row in range(4):
                self.update_ppg_row_leds(row)

            for loop_id in range(32):
                self.update_loop_led(loop_id)

    def update_lighting_mode_leds(self):
        """Update grid LEDs for lighting program selection mode (Control 0).

        Row 0: 6 program buttons (0-5), rest off
        Rows 1-7: All off
        """
        # Row 0: Lighting programs
        for col in range(8):
            if col < 6:
                if col == self.current_lighting_program:
                    color = LED_COLOR_MODE_SELECTED
                else:
                    color = LED_COLOR_MODE_AVAILABLE
            else:
                color = LED_COLOR_LOOP_OFF  # Unused
            self.control_client.send_message(f"/led/0/{col}", [color, LED_MODE_STATIC])

        # Rows 1-7: All off
        for row in range(1, 8):
            for col in range(8):
                self.control_client.send_message(f"/led/{row}/{col}", [LED_COLOR_LOOP_OFF, LED_MODE_STATIC])

    def update_bpm_mode_leds(self):
        """Update grid LEDs for BPM multiplier selection mode (Control 1).

        Row 0: 7 multiplier buttons (0.25x - 3x)
        Rows 1-7: All off
        """
        # Row 0: BPM multipliers (7 options)
        for col in range(len(BPM_MULTIPLIERS)):
            if BPM_MULTIPLIERS[col] == self.current_bpm_multiplier:
                color = LED_COLOR_MODE_SELECTED
            else:
                color = LED_COLOR_MODE_AVAILABLE
            self.control_client.send_message(f"/led/0/{col}", [color, LED_MODE_STATIC])

        # Row 0: Unused columns (7+)
        for col in range(len(BPM_MULTIPLIERS), 8):
            self.control_client.send_message(f"/led/0/{col}", [LED_COLOR_CONTROL_INACTIVE, LED_MODE_STATIC])

        # Rows 1-7: All off
        for row in range(1, 8):
            for col in range(8):
                self.control_client.send_message(f"/led/{row}/{col}", [LED_COLOR_LOOP_OFF, LED_MODE_STATIC])

    def update_bank_mode_leds(self):
        """Update grid LEDs for sample bank selection mode (Control 2).

        Rows 0-7: Bank selection for PPG 0-7 (8 banks per row)
        """
        for row in range(8):
            ppg_id = row
            current_bank = self.ppg_sample_banks[ppg_id]
            for col in range(8):
                if col == current_bank:
                    color = LED_COLOR_MODE_SELECTED
                else:
                    color = LED_COLOR_MODE_AVAILABLE
                self.control_client.send_message(f"/led/{row}/{col}", [color, LED_MODE_STATIC])

    def update_effects_mode_leds(self):
        """Update grid LEDs for effects assignment mode (Control 3).

        Rows 0-7: Effect toggles for PPG 0-7 (each independent)
        Column 0: Clear all effects
        Columns 1-5: reverb, phaser, delay, chorus, lowpass
        Columns 6-7: Unused
        """
        for row in range(8):
            ppg_id = row
            active_effects = self.ppg_effects[ppg_id]

            # Column 0: Clear (show as available if any effects active)
            if active_effects:
                color = LED_COLOR_MODE_AVAILABLE
            else:
                color = LED_COLOR_LOOP_OFF
            self.control_client.send_message(f"/led/{row}/0", [color, LED_MODE_STATIC])

            # Columns 1-5: Effect toggles
            for col in range(1, 6):
                effect_name = EFFECT_NAMES[col - 1]
                if effect_name in active_effects:
                    color = LED_COLOR_MODE_SELECTED
                else:
                    color = LED_COLOR_MODE_AVAILABLE
                self.control_client.send_message(f"/led/{row}/{col}", [color, LED_MODE_STATIC])

            # Columns 6-7: Unused
            for col in range(6, 8):
                self.control_client.send_message(f"/led/{row}/{col}", [LED_COLOR_LOOP_OFF, LED_MODE_STATIC])

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

        self.control_client.send_message(f"/led/{row}/{col}", [color, LED_MODE_STATIC])

    def handle_select(self, address: str, *args):
        """Handle /select/{ppg_id} [column] message.

        In normal mode: Updates sample selection for specified PPG sensor.
        In control mode: Routes to mode-specific handler based on active_control_mode.

        Args:
            address: OSC address (e.g., "/select/0")
            *args: Message arguments [column]
        """
        self.stats.increment('total_messages')

        # Validate address
        is_valid, ppg_id, error_msg = validate_select_address(address)
        if not is_valid:
            self.stats.increment('invalid_messages')
            logger.warning(f"{error_msg}")
            return

        # Validate arguments
        if len(args) != 1:
            self.stats.increment('invalid_messages')
            logger.warning(f"/select expects 1 argument, got {len(args)}")
            return

        try:
            column = int(args[0])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid column value: {args[0]} ({e})")
            return

        is_valid, error_msg = validate_column(column)
        if not is_valid:
            self.stats.increment('invalid_messages')
            logger.warning(f"{error_msg}")
            return

        # Route based on active control mode
        if self.active_control_mode == 0:
            self.handle_lighting_select(ppg_id, column)
        elif self.active_control_mode == 1:
            self.handle_bpm_select(ppg_id, column)
        elif self.active_control_mode == 2:
            self.handle_bank_select(ppg_id, column)
        elif self.active_control_mode == 3:
            self.handle_effect_select(ppg_id, column)
        else:
            # Normal mode: sample selection
            self.handle_normal_select(ppg_id, column)

    def handle_normal_select(self, ppg_id: int, column: int):
        """Handle normal mode sample selection.

        Args:
            ppg_id: PPG sensor ID (0-3)
            column: Column index (0-7)
        """
        # Update state
        old_column = self.sample_map[ppg_id]
        self.sample_map[ppg_id] = column

        # Persist state
        self.save_state()

        # Send routing update to audio engine
        self.control_client.send_message(f"/route/{ppg_id}", column)

        # Update LEDs
        self.update_ppg_row_leds(ppg_id)

        self.stats.increment('select_messages')
        logger.info(f"SELECT: PPG {ppg_id}, column {old_column} → {column}")

    def handle_lighting_select(self, row: int, col: int):
        """Handle lighting program selection in Control Mode 0.

        Only row 0, columns 0-5 are valid (6 lighting programs).

        Args:
            row: Grid row (should be 0)
            col: Grid column (0-5)
        """
        # Only row 0 is used for lighting selection
        if row != 0:
            return

        # Only columns 0-5 are valid (6 programs)
        if col > 5:
            return

        # Update state
        old_program = self.current_lighting_program
        self.current_lighting_program = col

        # Send OSC message to lighting system
        program_name = LIGHTING_PROGRAMS[col]
        self.control_client.send_message("/program", program_name)

        # Update LEDs
        self.update_lighting_mode_leds()

        logger.info(f"LIGHTING: Program {old_program} → {col} ({program_name})")

    def handle_bpm_select(self, row: int, col: int):
        """Handle BPM multiplier selection in Control Mode 1.

        Only row 0, columns 0-6 are valid (7 multipliers).

        Args:
            row: Grid row (should be 0)
            col: Grid column (0-6)
        """
        # Only row 0 is used for BPM selection
        if row != 0:
            return

        # Validate column range
        if col >= len(BPM_MULTIPLIERS):
            return

        # Update state
        old_multiplier = self.current_bpm_multiplier
        self.current_bpm_multiplier = BPM_MULTIPLIERS[col]

        # Send OSC message to audio/lighting systems
        self.control_client.send_message("/bpm/multiplier", self.current_bpm_multiplier)

        # Update LEDs
        self.update_bpm_mode_leds()

        logger.info(f"BPM MULTIPLIER: {old_multiplier}x → {self.current_bpm_multiplier}x")

    def handle_bank_select(self, row: int, col: int):
        """Handle sample bank selection in Control Mode 2.

        Rows 0-7 = PPG 0-7, columns 0-7 = bank index.

        Args:
            row: Grid row (0-7 = PPG ID)
            col: Grid column (0-7 = bank index)
        """
        ppg_id = row

        # Validate and send OSC message
        # For virtual PPGs (4-7), use modulo-4 mapping (share banks with physical 0-3)
        bank_ppg_id = ppg_id % 4

        # Get bank name from config (banks are named, not numbered)
        ppg_banks = self.config.get('ppg_samples', {}).get(bank_ppg_id, {})
        if isinstance(ppg_banks, dict):
            bank_names = list(ppg_banks.keys())
            if col < len(bank_names):
                # Update state only after validation passes
                old_bank = self.ppg_sample_banks[ppg_id]
                self.ppg_sample_banks[ppg_id] = col

                bank_name = bank_names[col]
                self.control_client.send_message("/load_bank", [bank_ppg_id, bank_name])
                logger.info(f"SAMPLE BANK: PPG {ppg_id} → bank {col} ('{bank_name}')")
            else:
                logger.warning(f"PPG {ppg_id} bank {col} out of range (has {len(bank_names)} banks)")
                return
        else:
            logger.warning(f"PPG {bank_ppg_id} config is not multi-bank format")
            return

        # Update LEDs
        self.update_bank_mode_leds()

    def handle_effect_select(self, row: int, col: int):
        """Handle effect toggle in Control Mode 3.

        Rows 0-7 = PPG 0-7 (each with independent effect chain)
        Column 0 = Clear all effects
        Columns 1-5 = Toggle effect (reverb, phaser, delay, chorus, lowpass)
        Columns 6-7 = Unused

        Args:
            row: Grid row (0-7 = PPG ID)
            col: Grid column (0 = clear, 1-5 = effect index)
        """
        ppg_id = row

        # Column 0: Clear all effects
        if col == 0:
            if self.ppg_effects[ppg_id]:
                self.ppg_effects[ppg_id].clear()
                self.control_client.send_message("/ppg/effect/clear", ppg_id)
                logger.info(f"EFFECTS: PPG {ppg_id}, cleared all effects")
            else:
                logger.info(f"EFFECTS: PPG {ppg_id}, no effects to clear")

        # Columns 1-5: Toggle effect
        elif 1 <= col <= 5:
            effect_name = EFFECT_NAMES[col - 1]

            # Toggle effect
            if effect_name in self.ppg_effects[ppg_id]:
                self.ppg_effects[ppg_id].remove(effect_name)
                action = "disabled"
            else:
                self.ppg_effects[ppg_id].add(effect_name)
                action = "enabled"

            # Send OSC message to audio system
            self.control_client.send_message("/ppg/effect/toggle", [ppg_id, effect_name])

            logger.info(f"EFFECTS: PPG {ppg_id}, {effect_name} {action}")

        # Columns 6-7: Unused
        else:
            return

        # Update LEDs
        self.update_effects_mode_leds()

    def handle_loop_toggle(self, address: str, *args):
        """Handle /loop/toggle [loop_id] message.

        Toggles loop state, sends start/stop command to audio engine,
        and updates LED state.

        Disabled when in control mode.

        Args:
            address: OSC address ("/loop/toggle")
            *args: Message arguments [loop_id]
        """
        self.stats.increment('total_messages')

        # Disable loop buttons when in control mode
        if self.active_control_mode is not None:
            return

        # Validate arguments
        if len(args) != 1:
            self.stats.increment('invalid_messages')
            logger.warning(f"/loop/toggle expects 1 argument, got {len(args)}")
            return

        try:
            loop_id = int(args[0])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid loop_id value: {args[0]} ({e})")
            return

        is_valid, error_msg = validate_loop_id(loop_id)
        if not is_valid:
            self.stats.increment('invalid_messages')
            logger.warning(f"{error_msg}")
            return

        # Toggle state
        old_state = self.loop_status[loop_id]
        new_state = not old_state
        self.loop_status[loop_id] = new_state

        # Persist state
        self.save_state()

        # Send command to audio engine
        if new_state:
            self.control_client.send_message("/loop/start", loop_id)
            action = "START"
        else:
            self.control_client.send_message("/loop/stop", loop_id)
            action = "STOP"

        # Update LED
        self.update_loop_led(loop_id)

        self.stats.increment('loop_toggle_messages')
        logger.info(f"LOOP TOGGLE: Loop {loop_id} → {action}")

    def handle_bank(self, address: str, *args):
        """Handle /bank [ppg_id] [bank_name] message.

        Switches active sample bank for specified PPG sensor, sends load_bank
        command to audio engine to reload samples, and updates state.

        Args:
            address: OSC address ("/bank")
            *args: Message arguments [ppg_id, bank_name]
        """
        self.stats.increment('total_messages')

        # Validate arguments
        if len(args) != 2:
            self.stats.increment('invalid_messages')
            logger.warning(f"/bank expects 2 arguments, got {len(args)}")
            return

        try:
            ppg_id = int(args[0])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid ppg_id value: {args[0]} ({e})")
            return

        # Validate PPG ID
        if not 0 <= ppg_id <= 3:
            self.stats.increment('invalid_messages')
            logger.warning(f"PPG ID must be 0-3, got {ppg_id}")
            return

        bank_name = str(args[1])

        # Validate bank exists in config
        ppg_banks = self.config.get('ppg_samples', {}).get(ppg_id, {})
        if not isinstance(ppg_banks, dict):
            self.stats.increment('invalid_messages')
            logger.warning(f"PPG {ppg_id} config is not multi-bank format")
            return

        if bank_name not in ppg_banks:
            available = ', '.join(ppg_banks.keys())
            self.stats.increment('invalid_messages')
            logger.warning(f"Bank '{bank_name}' not found for PPG {ppg_id}. Available: {available}")
            return

        # Update state
        old_bank = self.bank_map[ppg_id]
        self.bank_map[ppg_id] = bank_name

        # Persist state
        self.save_state()

        # Send load_bank command to audio engine
        self.control_client.send_message("/load_bank", [ppg_id, bank_name])

        self.stats.increment('bank_messages')
        logger.info(f"BANK: PPG {ppg_id}, '{old_bank}' → '{bank_name}'")

    def handle_loop_momentary(self, address: str, *args):
        """Handle /loop/momentary [loop_id] [state] message.

        Starts/stops loop based on button press/release, sends command
        to audio engine, and updates LED state.

        Disabled when in control mode.

        Args:
            address: OSC address ("/loop/momentary")
            *args: Message arguments [loop_id, state]
        """
        self.stats.increment('total_messages')

        # Disable loop buttons when in control mode
        if self.active_control_mode is not None:
            return

        # Validate arguments
        if len(args) != 2:
            self.stats.increment('invalid_messages')
            logger.warning(f"/loop/momentary expects 2 arguments, got {len(args)}")
            return

        try:
            loop_id = int(args[0])
            state = int(args[1])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid loop_id or state value: {args[0]}, {args[1]} ({e})")
            return

        is_valid, error_msg = validate_loop_id(loop_id)
        if not is_valid:
            self.stats.increment('invalid_messages')
            logger.warning(f"{error_msg}")
            return

        is_valid, error_msg = validate_momentary_state(state)
        if not is_valid:
            self.stats.increment('invalid_messages')
            logger.warning(f"{error_msg}")
            return

        # Update state
        is_pressed = (state == 1)
        self.loop_status[loop_id] = is_pressed

        # Persist state
        self.save_state()

        # Send command to audio engine
        if is_pressed:
            self.control_client.send_message("/loop/start", loop_id)
            action = "START (pressed)"
        else:
            self.control_client.send_message("/loop/stop", loop_id)
            action = "STOP (released)"

        # Update LED
        self.update_loop_led(loop_id)

        self.stats.increment('loop_momentary_messages')
        logger.info(f"LOOP MOMENTARY: Loop {loop_id} → {action}")

    def handle_scene_button(self, address: str, *args):
        """Handle /scene [scene_id] [state] message for sampler control.

        Scene 0-3: Record from PPG 0-3
            - Press: Start/stop recording → /sampler/record/toggle [source_ppg]

        Scene 4-7: Virtual channels 4-7
            - Press in assignment mode: Assign buffer → /sampler/assign [dest_channel]
            - Press when playing: Stop playback → /sampler/toggle [dest_channel]

        Disabled when in control mode.

        Args:
            address: OSC address ("/scene")
            *args: Message arguments [scene_id, state]
        """
        self.stats.increment('total_messages')

        # Disable scene buttons when in control mode
        if self.active_control_mode is not None:
            return

        # Validate arguments
        if len(args) != 2:
            self.stats.increment('invalid_messages')
            logger.warning(f"/scene expects 2 arguments, got {len(args)}")
            return

        try:
            scene_id = int(args[0])
            state = int(args[1])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid scene_id or state value: {args[0]}, {args[1]} ({e})")
            return

        # Validate scene_id (0-7)
        if not isinstance(scene_id, int) or scene_id < 0 or scene_id > 7:
            self.stats.increment('invalid_messages')
            logger.warning(f"Scene ID must be in range 0-7, got {scene_id}")
            return

        # Validate state (0 or 1)
        if state not in (0, 1):
            self.stats.increment('invalid_messages')
            logger.warning(f"State must be 0 or 1, got {state}")
            return

        # Only handle press events (state == 1), ignore release
        if state == 0:
            return

        self.stats.increment('scene_button_messages')

        # Scene 0-3: Recording control
        if 0 <= scene_id <= 3:
            source_ppg = scene_id
            self.control_client.send_message("/sampler/record/toggle", source_ppg)
            logger.info(f"SCENE: Record toggle for PPG {source_ppg}")

        # Scene 4-7: Virtual channel control
        elif 4 <= scene_id <= 7:
            dest_channel = scene_id

            if self.assignment_mode:
                # In assignment mode: assign buffer to virtual channel
                self.control_client.send_message("/sampler/assign", dest_channel)
                logger.info(f"SCENE: Assign buffer to channel {dest_channel}")
            elif self.active_virtuals.get(dest_channel, False):
                # Channel is playing: toggle to stop
                self.control_client.send_message("/sampler/toggle", dest_channel)
                logger.info(f"SCENE: Toggle playback for channel {dest_channel}")
            else:
                # Channel is not playing, not in assignment mode: no-op
                logger.info(f"SCENE: Channel {dest_channel} not playing, ignoring")

    def handle_sampler_status_recording(self, address: str, *args):
        """Handle /sampler/status/recording [source_ppg] [active] message.

        Updates recording state and scene LED for recording source.

        Args:
            address: OSC address ("/sampler/status/recording")
            *args: Message arguments [source_ppg, active]
        """
        self.stats.increment('total_messages')

        # Validate arguments
        if len(args) != 2:
            self.stats.increment('invalid_messages')
            logger.warning(f"/sampler/status/recording expects 2 arguments, got {len(args)}")
            return

        try:
            source_ppg = int(args[0])
            active = int(args[1])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid argument values: {args[0]}, {args[1]} ({e})")
            return

        # Validate source_ppg (0-3)
        if source_ppg < 0 or source_ppg > 3:
            self.stats.increment('invalid_messages')
            logger.warning(f"Source PPG must be 0-3, got {source_ppg}")
            return

        # Validate active (0 or 1)
        if active not in (0, 1):
            self.stats.increment('invalid_messages')
            logger.warning(f"Active must be 0 or 1, got {active}")
            return

        # Update state
        if active == 1:
            self.recording_ppgs.add(source_ppg)
            # Update scene LED: red for recording
            self.control_client.send_message(f"/led/scene/{source_ppg}", [LED_COLOR_RECORDING, LED_MODE_STATIC])
            logger.info(f"SAMPLER STATUS: Recording PPG {source_ppg} started")
        else:
            self.recording_ppgs.discard(source_ppg)
            # Update scene LED: off when recording stops (assignment mode will update separately)
            self.control_client.send_message(f"/led/scene/{source_ppg}", [LED_COLOR_SCENE_OFF, LED_MODE_STATIC])
            logger.info(f"SAMPLER STATUS: Recording PPG {source_ppg} stopped")

    def handle_sampler_status_assignment(self, address: str, *args):
        """Handle /sampler/status/assignment [active] message.

        Updates assignment mode state and scene LEDs for recording source.

        Args:
            address: OSC address ("/sampler/status/assignment")
            *args: Message arguments [active]
        """
        self.stats.increment('total_messages')

        # Validate arguments
        if len(args) != 1:
            self.stats.increment('invalid_messages')
            logger.warning(f"/sampler/status/assignment expects 1 argument, got {len(args)}")
            return

        try:
            active = int(args[0])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid active value: {args[0]} ({e})")
            return

        # Validate active (0 or 1)
        if active not in (0, 1):
            self.stats.increment('invalid_messages')
            logger.warning(f"Active must be 0 or 1, got {active}")
            return

        # Update state
        if active == 1:
            self.assignment_mode = True
            # Update scene 0-3 LEDs: blinking green for assignment mode
            # Skip any PPGs that are currently recording (preserve red LED)
            for scene_id in range(4):
                if scene_id not in self.recording_ppgs:
                    self.control_client.send_message(f"/led/scene/{scene_id}", [LED_COLOR_ASSIGNMENT, LED_MODE_FLASH])
            logger.info(f"SAMPLER STATUS: Assignment mode entered")
        else:
            self.assignment_mode = False
            # Update scene 0-3 LEDs: off when exiting assignment mode
            # Skip any PPGs that are currently recording (preserve red LED)
            for scene_id in range(4):
                if scene_id not in self.recording_ppgs:
                    self.control_client.send_message(f"/led/scene/{scene_id}", [LED_COLOR_SCENE_OFF, LED_MODE_STATIC])
            logger.info(f"SAMPLER STATUS: Assignment mode exited")

    def handle_sampler_status_playback(self, address: str, *args):
        """Handle /sampler/status/playback [dest_channel] [active] message.

        Updates virtual channel playback state and scene LED.

        Args:
            address: OSC address ("/sampler/status/playback")
            *args: Message arguments [dest_channel, active]
        """
        self.stats.increment('total_messages')

        # Validate arguments
        if len(args) != 2:
            self.stats.increment('invalid_messages')
            logger.warning(f"/sampler/status/playback expects 2 arguments, got {len(args)}")
            return

        try:
            dest_channel = int(args[0])
            active = int(args[1])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid argument values: {args[0]}, {args[1]} ({e})")
            return

        # Validate dest_channel (4-7)
        if dest_channel < 4 or dest_channel > 7:
            self.stats.increment('invalid_messages')
            logger.warning(f"Destination channel must be 4-7, got {dest_channel}")
            return

        # Validate active (0 or 1)
        if active not in (0, 1):
            self.stats.increment('invalid_messages')
            logger.warning(f"Active must be 0 or 1, got {active}")
            return

        # Update state
        self.active_virtuals[dest_channel] = (active == 1)

        # Update scene LED
        if active == 1:
            self.control_client.send_message(f"/led/scene/{dest_channel}", [LED_COLOR_PLAYING, LED_MODE_STATIC])
            logger.info(f"SAMPLER STATUS: Playback on channel {dest_channel} started")
        else:
            self.control_client.send_message(f"/led/scene/{dest_channel}", [LED_COLOR_SCENE_OFF, LED_MODE_STATIC])
            logger.info(f"SAMPLER STATUS: Playback on channel {dest_channel} stopped")

    def handle_control_button(self, address: str, *args):
        """Handle /control [control_id] [state] message.

        Implements modal control system. Control buttons toggle between normal mode
        and control modes (0=Lighting, 1=BPM, 2=Banks, 3=Effects).

        When control mode is active:
        - Grid buttons (rows 0-7) show mode-specific options
        - Scene buttons are disabled
        - Pressing same control button again exits mode
        - Pressing different control button switches to that mode

        Control button mapping (Launchpad Mark 1):
        - 0 (Session): Lighting Program Select
        - 1 (User 1): BPM Multiplier
        - 2 (Mixer): PPG Sample Bank Select
        - 3 (User 2): Audio Effects Assignment
        - 4-7: Currently unassigned

        Args:
            address: OSC address ("/control")
            *args: Message arguments [control_id, state]
        """
        self.stats.increment('total_messages')

        # Validate arguments
        if len(args) != 2:
            self.stats.increment('invalid_messages')
            logger.warning(f"/control expects 2 arguments, got {len(args)}")
            return

        try:
            control_id = int(args[0])
            state = int(args[1])
        except (ValueError, TypeError) as e:
            self.stats.increment('invalid_messages')
            logger.warning(f"Invalid control_id or state value: {args[0]}, {args[1]} ({e})")
            return

        # Validate control_id (0-7)
        if not isinstance(control_id, int) or control_id < 0 or control_id > 7:
            self.stats.increment('invalid_messages')
            logger.warning(f"Control ID must be in range 0-7, got {control_id}")
            return

        # Validate state (0 or 1)
        if state not in (0, 1):
            self.stats.increment('invalid_messages')
            logger.warning(f"State must be 0 or 1, got {state}")
            return

        # Only handle press events (ignore release)
        if state == 0:
            return

        self.stats.increment('control_button_messages')

        # Only controls 0-3 are assigned (4-7 unassigned)
        if control_id > 3:
            logger.info(f"CONTROL BUTTON: Control {control_id} pressed (unassigned)")
            return

        # Toggle control mode
        if self.active_control_mode == control_id:
            # Deactivate mode - return to normal operation
            self.exit_control_mode()
            logger.info(f"CONTROL MODE: Exited mode {control_id}")
        elif self.active_control_mode is None:
            # Activate mode
            self.enter_control_mode(control_id)
            logger.info(f"CONTROL MODE: Entered mode {control_id}")
        else:
            # Switch modes - skip LED restoration to avoid flash
            old_mode = self.active_control_mode
            self.exit_control_mode(restore_leds=False)
            self.enter_control_mode(control_id)
            logger.info(f"CONTROL MODE: Switched from mode {old_mode} to {control_id}")

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
        disp.map("/bank", self.handle_bank)
        disp.map("/loop/toggle", self.handle_loop_toggle)
        disp.map("/loop/momentary", self.handle_loop_momentary)
        disp.map("/scene", self.handle_scene_button)
        disp.map("/control", self.handle_control_button)
        disp.map("/status/ready/*", self.handle_status_ready)
        # Sampler status messages
        disp.map("/sampler/status/recording", self.handle_sampler_status_recording)
        disp.map("/sampler/status/assignment", self.handle_sampler_status_assignment)
        disp.map("/sampler/status/playback", self.handle_sampler_status_playback)

        # Create OSC server
        server = osc.ReusePortBlockingOSCUDPServer(
            ("0.0.0.0", self.control_port),
            disp
        )

        logger.info(f"Sequencer listening on port {self.control_port}")
        logger.info(f"Expecting control messages from Launchpad Bridge:")
        logger.info(f"  /select/{{0-3}} [column]             # PPG sample selection")
        logger.info(f"  /loop/toggle [loop_id]              # Latching loop toggle")
        logger.info(f"  /loop/momentary [loop_id] [state]   # Momentary loop press/release")
        logger.info(f"  /scene [scene_id] [state]           # Scene button press/release")
        logger.info(f"  /control [control_id] [state]       # Control button press/release")
        logger.info(f"Waiting for messages... (Ctrl+C to stop)")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Server crashed: {e}")
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
        --control-port N    Port for control bus (default: osc.PORT_CONTROL)
        --config PATH       Path to samples.yaml (default: amor/config/samples.yaml)

    Example usage:
        python3 -m amor.sequencer
        python3 -m amor.sequencer --control-port 8003
        python3 -m amor.sequencer --config /path/to/samples.yaml

    Validation:
        - Control port must be in range 1-65535
        - Config file must exist and be valid YAML
        - Exits with error code 1 if validation fails
    """
    parser = argparse.ArgumentParser(
        description="Sequencer - Launchpad sample selection state manager"
    )
    parser.add_argument(
        "--control-port",
        type=int,
        default=osc.PORT_CONTROL,
        help=f"Port for control bus (default: {osc.PORT_CONTROL})",
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
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.getenv("AMOR_LOG_LEVEL", "INFO"),
        help="Logging verbosity (default: INFO)",
    )

    args = parser.parse_args()

    # Set log level
    os.environ["AMOR_LOG_LEVEL"] = args.log_level

    # Reinitialize logger to pick up new log level
    get_logger(__name__)

    # Create and run sequencer
    try:
        sequencer = Sequencer(
            config_path=args.config,
            control_port=args.control_port,
            state_path=args.state_path
        )
        sequencer.run()
    except FileNotFoundError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {args.control_port} already in use")
        else:
            logger.error(f"{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
