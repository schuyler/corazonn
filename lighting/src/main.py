#!/usr/bin/env python3
"""
Main entry point for Heartbeat Lighting Bridge MVP v2.0.

This module loads configuration, validates it, sets up logging, creates the
backend, and starts the OSC server. It's the executable entry point for the
lighting bridge system.

TRD References:
- R7-R14: Config validation requirements
- R12: Zone validation (0-3, unique)
- R5: Authentication failure must prevent startup (SystemExit)
"""

import yaml
import logging
import logging.handlers
import errno
from pathlib import Path
from backends import create_backend
from osc_receiver import start_osc_server


# =============================================================================
# Task 8.1-8.2: Config Loading
# =============================================================================

def load_config(path: str) -> dict:
    """
    Load and validate configuration from YAML file.

    Args:
        path: Path to configuration YAML file

    Returns:
        Validated configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML syntax is invalid
        ValueError: If configuration is invalid (via validate_config)
    """
    config_path = Path(path)

    # Check file exists
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}\n"
            f"Please create a config.yaml file in the project root.\n"
            f"See config.yaml.example for a template."
        )

    # Load YAML
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Validate configuration
    validate_config(config)

    return config


# =============================================================================
# Task 8.3-8.10: Config Validation (R7-R12)
# =============================================================================

def validate_config(config: dict) -> None:
    """
    Validate configuration against TRD requirements.

    Validates:
    - R7: Backend selection ('kasa' only for now)
    - R13: Kasa section existence
    - R8: OSC port range (1-65535)
    - R9: Brightness/saturation ranges (0-100)
    - R10: Hue range (0-360, optional)
    - R11: Time parameters (> 0)
    - R12: Zone validation (0-3, unique)

    Args:
        config: Configuration dictionary to validate

    Raises:
        ValueError: If any validation fails
    """
    # R7: Check backend exists and is 'kasa'
    backend = config.get('lighting', {}).get('backend')
    if not backend:
        raise ValueError(
            "Configuration missing 'lighting.backend'\n"
            "Must specify: lighting.backend: 'kasa'"
        )

    if backend != 'kasa':
        raise ValueError(
            f"Unsupported backend: '{backend}'\n"
            f"Currently only 'kasa' is supported."
        )

    # R13: Check 'kasa' section exists
    if 'kasa' not in config:
        raise ValueError(
            "Configuration missing 'kasa' section\n"
            "Backend configuration not found."
        )

    # R8: Validate OSC port
    osc_config = config.get('osc', {})
    listen_port = osc_config.get('listen_port')
    if listen_port is None:
        raise ValueError(
            "Configuration missing 'osc.listen_port'\n"
            "Must specify: osc.listen_port: (1-65535)"
        )

    if not isinstance(listen_port, int) or not (1 <= listen_port <= 65535):
        raise ValueError(
            f"Invalid OSC port: {listen_port}\n"
            f"Port must be in range 1-65535"
        )

    # R9: Validate brightness and saturation ranges
    effects = config.get('effects', {})

    baseline_bri = effects.get('baseline_brightness')
    if baseline_bri is not None and not (0 <= baseline_bri <= 100):
        raise ValueError(
            f"Invalid baseline_brightness: {baseline_bri}\n"
            f"Must be in range 0-100"
        )

    pulse_max = effects.get('pulse_max')
    if pulse_max is not None and not (0 <= pulse_max <= 100):
        raise ValueError(
            f"Invalid pulse_max: {pulse_max}\n"
            f"Must be in range 0-100"
        )

    baseline_sat = effects.get('baseline_saturation')
    if baseline_sat is not None and not (0 <= baseline_sat <= 100):
        raise ValueError(
            f"Invalid baseline_saturation: {baseline_sat}\n"
            f"Must be in range 0-100"
        )

    # R10: Validate hue range (if present)
    baseline_hue = effects.get('baseline_hue')
    if baseline_hue is not None and not (0 <= baseline_hue <= 360):
        raise ValueError(
            f"Invalid baseline_hue: {baseline_hue}\n"
            f"Must be in range 0-360"
        )

    # R11: Validate time parameters > 0
    for param in ['fade_time_ms', 'attack_time_ms', 'sustain_time_ms']:
        time_val = effects.get(param)
        if time_val is not None and time_val <= 0:
            raise ValueError(
                f"Invalid {param}: {time_val}\n"
                f"Must be greater than 0"
            )

    # R12: Zone validation - 0-3 and unique
    kasa_config = config.get('kasa', {})
    bulbs = kasa_config.get('bulbs', [])
    zones = [bulb.get('zone') for bulb in bulbs]

    # Validate range 0-3
    for zone in zones:
        if zone is not None and not (0 <= zone <= 3):
            raise ValueError(
                f"Invalid zone: {zone}\n"
                f"Zones must be in range 0-3"
            )

    # Validate uniqueness
    if len(zones) != len(set(zones)):
        raise ValueError(
            f"Duplicate zones found in kasa configuration\n"
            f"All zones must be unique (0-3)"
        )


# =============================================================================
# Task 8.11-8.14: Logging Setup
# =============================================================================

def setup_logging(config: dict) -> None:
    """
    Configure logging with file and console handlers.

    Creates a rotating file handler and console handler with separate
    log levels. Uses the formatter specified in TRD.

    Args:
        config: Configuration dict with logging settings

    Returns:
        None
    """
    logging_config = config.get('logging', {})

    # Create logs directory if needed
    log_file = logging_config.get('file', 'logs/lighting.log')
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure formatter
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler (rotating)
    max_bytes = logging_config.get('max_bytes', 10485760)  # 10MB default
    backup_count = logging_config.get('backup_count', 5)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_level_str = logging_config.get('file_level', 'DEBUG')
    file_level = getattr(logging, file_level_str, logging.DEBUG)
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_level_str = logging_config.get('console_level', 'INFO')
    console_level = getattr(logging, console_level_str, logging.INFO)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


# =============================================================================
# Task 8.15-8.22: Main Function
# =============================================================================

def main() -> int:
    """
    Main entry point for the lighting bridge.

    Orchestrates:
    1. Configuration loading and validation
    2. Logging setup
    3. Backend creation and authentication
    4. Baseline bulb initialization
    5. OSC server startup

    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        # Load configuration
        config = load_config('config.yaml')

        # Setup logging
        setup_logging(config)
        logger = logging.getLogger(__name__)

        # Print startup banner
        print("=" * 60)
        print("Heartbeat Lighting Bridge MVP v2.0 (Multi-Backend)")
        print("=" * 60)

        logger.info("Starting Heartbeat Lighting Bridge MVP v2.0")

        # Create backend
        backend = create_backend(config)
        logger.info(f"Backend: {backend.__class__.__name__}")

        # Log latency estimate
        latency = backend.get_latency_estimate()
        logger.info(f"Estimated command latency: {latency}ms")

        # Authenticate backend
        logger.info("Authenticating backend...")
        backend.authenticate()
        logger.info("Backend authentication successful")

        # Set all bulbs to baseline
        logger.info("Setting all bulbs to baseline...")
        backend.set_all_baseline()
        logger.info("Baseline initialization complete")

        # Start OSC server (blocks indefinitely)
        try:
            logger.info("Starting OSC server...")
            start_osc_server(config, backend)
        except OSError as e:
            # Handle port conflicts
            if e.errno == errno.EADDRINUSE or "Address already in use" in str(e):
                port = config['osc']['listen_port']
                logger.error(f"Port {port} already in use. Is bridge already running?")
                print(f"Error: Port {port} already in use")
                return 1
            else:
                raise

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    except ValueError as e:
        print(f"Invalid config: {e}")
        return 1

    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Shutdown requested (Ctrl+C)")
        backend.print_stats()
        print("\nBridge shutdown complete")
        return 0

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        return 1


# Entry point
if __name__ == '__main__':
    exit(main())
