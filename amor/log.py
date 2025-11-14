"""Logging utilities for amor system."""
import logging
import sys
import os
import threading
from typing import Optional


# Thread-safe lock for logger initialization
_logger_init_lock = threading.Lock()


class AmorFormatter(logging.Formatter):
    """Custom formatter for amor logs.

    Format: [{level[0]} {time} {module_basename[:9]}] {message}
    Example: [I 14:23:45.123 audio    ] Audio engine started
    """

    def format(self, record):
        # Get first character of level name
        level_char = record.levelname[0]

        # Get module basename (last part after dot)
        module_name = record.name.split('.')[-1]
        # Truncate to 9 chars and right-pad
        module_padded = module_name[:9].ljust(9)

        # Format timestamp with milliseconds
        timestamp = self.formatTime(record, "%H:%M:%S")
        msecs = f"{record.msecs:03.0f}"

        # Build the log line
        prefix = f"[{level_char} {timestamp}.{msecs} {module_padded}]"
        message = record.getMessage()

        return f"{prefix} {message}"


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get logger for amor component.

    Args:
        name: Component name (usually __name__)
        level: Optional level (DEBUG/INFO/WARNING/ERROR)
               Falls back to AMOR_LOG_LEVEL env var, then INFO

    Returns:
        Configured logger instance

    Example:
        >>> from amor.log import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Audio engine started")
        [I 14:23:45.123 audio    ] Audio engine started
    """
    logger = logging.getLogger(name)

    # Set level from: parameter > env var > INFO default
    if level is None:
        level = os.getenv("AMOR_LOG_LEVEL", "INFO")

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Add handler if not already configured (thread-safe)
    with _logger_init_lock:
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(AmorFormatter())
            logger.addHandler(handler)

    return logger
