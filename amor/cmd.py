#!/usr/bin/env python3
"""
Cmd - English-language REPL for Amor system control

Interactive REPL and one-shot command execution using Claude Haiku
for natural language → structured OSC command translation.

Usage:
    Interactive REPL:
        python -m amor.cmd

    One-shot command:
        python -m amor.cmd "start the sequencer"
        python -m amor.cmd "switch to soft pulse lighting"

Architecture:
- Claude Haiku function calling for NL → structured commands
- Lightweight conversation context (last N messages)
- Cost-optimized (Haiku API calls)
- Extensible function definitions

Functions execute via:
- amor.osc.send_osc_message() for OSC commands
- PyYAML for config queries
"""

import anthropic
import yaml
import json
import os
import sys
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from amor import osc
from amor.lighting_programs import PROGRAMS
from amor.log import get_logger

logger = get_logger("cmd")


# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# Absolute paths to config files (relative to repo root)
AMOR_ROOT = Path(__file__).parent.parent
DEFAULT_LIGHTING_CONFIG = AMOR_ROOT / "amor" / "config" / "lighting.yaml"
DEFAULT_SAMPLES_CONFIG = AMOR_ROOT / "amor" / "config" / "samples.yaml"
DEFAULT_CMD_CONFIG = AMOR_ROOT / "amor" / "config" / "cmd.yaml"


# ============================================================================
# TOOL DEFINITIONS FOR CLAUDE HAIKU
# ============================================================================

TOOLS = [
    {
        "name": "send_osc",
        "description": "Send an OSC message to amor components (lighting, sequencer, audio, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "OSC address path (e.g., '/program', '/select/0', '/loop/toggle')"
                },
                "args": {
                    "type": "array",
                    "items": {"anyOf": [{"type": "string"}, {"type": "number"}]},
                    "description": "OSC message arguments (strings or numbers)"
                }
            },
            "required": ["address", "args"]
        }
    },
    {
        "name": "query_lighting_programs",
        "description": "List available lighting programs and currently active program",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "query_lighting_config",
        "description": "Get current lighting configuration (zones, effects settings)",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "query_samples",
        "description": "List available audio samples and loops from sequencer configuration",
        "input_schema": {
            "type": "object",
            "properties": {
                "ppg_id": {
                    "type": "integer",
                    "description": "PPG ID (0-3) to query samples for, or omit for all",
                    "minimum": 0,
                    "maximum": 3
                }
            }
        }
    },
    {
        "name": "query_sample_banks",
        "description": "List available sample banks for each PPG sensor",
        "input_schema": {
            "type": "object",
            "properties": {
                "ppg_id": {
                    "type": "integer",
                    "description": "PPG ID (0-3) to query banks for, or omit for all",
                    "minimum": 0,
                    "maximum": 3
                }
            }
        }
    },
    {
        "name": "switch_sample_bank",
        "description": "Switch active sample bank for a PPG sensor",
        "input_schema": {
            "type": "object",
            "properties": {
                "ppg_id": {
                    "type": "integer",
                    "description": "PPG ID (0-3) to switch bank for",
                    "minimum": 0,
                    "maximum": 3
                },
                "bank_name": {
                    "type": "string",
                    "description": "Name of the bank to switch to (e.g., 'default', 'techno', 'ambient')"
                }
            },
            "required": ["ppg_id", "bank_name"]
        }
    },
]


# ============================================================================
# FUNCTION IMPLEMENTATIONS
# ============================================================================

def execute_send_osc(address: str, args: List[Any]) -> Dict[str, Any]:
    """Execute OSC message send."""
    try:
        # Validate address format
        if not address.startswith('/'):
            return {"success": False, "error": "OSC address must start with '/'"}

        # Send OSC message using amor.osc infrastructure
        port = osc.infer_port(address)
        osc.send_osc_message(address, args, port=port)

        return {
            "success": True,
            "message": f"Sent OSC to port {port}: {address} {args}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_query_lighting_programs(config_path: Path = DEFAULT_LIGHTING_CONFIG) -> Dict[str, Any]:
    """Query available lighting programs from configuration."""
    try:
        # Read lighting config
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Get available programs from lighting_programs.PROGRAMS registry
        available_programs = list(PROGRAMS.keys())

        active_program = config.get("program", {}).get("active", "unknown")

        return {
            "success": True,
            "available_programs": available_programs,
            "active_program": active_program,
            "message": f"Active: {active_program}. Available: {', '.join(available_programs)}"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Lighting config not found at {config_path}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_query_lighting_config(config_path: Path = DEFAULT_LIGHTING_CONFIG) -> Dict[str, Any]:
    """Query lighting configuration details."""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Extract key configuration
        zones = config.get("zones", {})
        effects = config.get("effects", {})
        program_config = config.get("program", {})

        zone_summary = {
            zone_id: {
                "name": zone_data.get("name", f"Zone {zone_id}"),
                "hue": zone_data.get("hue", 0)
            }
            for zone_id, zone_data in zones.items()
        }

        return {
            "success": True,
            "program": program_config,
            "zones": zone_summary,
            "effects": effects,
            "message": f"{len(zones)} zones configured with {program_config.get('active', 'unknown')} program"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_query_samples(ppg_id: Optional[int] = None, config_path: Path = DEFAULT_SAMPLES_CONFIG) -> Dict[str, Any]:
    """Query available audio samples from sequencer configuration."""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        ppg_samples = config.get("ppg_samples", {})
        ambient_loops = config.get("ambient_loops", {})

        if ppg_id is not None:
            # Query specific PPG
            if ppg_id not in ppg_samples:
                return {
                    "success": False,
                    "error": f"PPG {ppg_id} not found in configuration"
                }

            samples = ppg_samples[ppg_id]
            # Extract just filenames for readability
            sample_names = [Path(s).stem for s in samples]

            return {
                "success": True,
                "ppg_id": ppg_id,
                "samples": sample_names,
                "count": len(sample_names),
                "message": f"PPG {ppg_id} has {len(sample_names)} samples: {', '.join(sample_names[:3])}{'...' if len(sample_names) > 3 else ''}"
            }
        else:
            # Query all PPGs
            all_samples = {}
            for pid, samples in ppg_samples.items():
                sample_names = [Path(s).stem for s in samples]
                all_samples[f"ppg_{pid}"] = sample_names

            latching_loops = [Path(l).stem for l in ambient_loops.get("latching", [])]
            momentary_loops = [Path(l).stem for l in ambient_loops.get("momentary", [])]

            return {
                "success": True,
                "ppg_samples": all_samples,
                "latching_loops": latching_loops,
                "momentary_loops": momentary_loops,
                "message": f"{len(ppg_samples)} PPG banks, {len(latching_loops)} latching loops, {len(momentary_loops)} momentary loops"
            }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Samples config not found at {config_path}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_query_sample_banks(ppg_id: Optional[int] = None, config_path: Path = DEFAULT_SAMPLES_CONFIG) -> Dict[str, Any]:
    """Query available sample banks for PPG sensors."""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        ppg_samples = config.get("ppg_samples", {})

        if ppg_id is not None:
            # Query specific PPG
            if ppg_id not in ppg_samples:
                return {
                    "success": False,
                    "error": f"PPG {ppg_id} not found in configuration"
                }

            banks = ppg_samples[ppg_id]
            if not isinstance(banks, dict):
                return {
                    "success": False,
                    "error": f"PPG {ppg_id} does not use multi-bank format"
                }

            bank_names = list(banks.keys())
            return {
                "success": True,
                "ppg_id": ppg_id,
                "banks": bank_names,
                "count": len(bank_names),
                "message": f"PPG {ppg_id} has {len(bank_names)} banks: {', '.join(bank_names)}"
            }
        else:
            # Query all PPGs
            all_banks = {}
            for pid, banks in ppg_samples.items():
                if isinstance(banks, dict):
                    all_banks[f"ppg_{pid}"] = list(banks.keys())
                else:
                    all_banks[f"ppg_{pid}"] = ["(legacy format - no banks)"]

            total_banks = sum(len(b) for b in all_banks.values() if isinstance(b, list))
            return {
                "success": True,
                "banks": all_banks,
                "message": f"{len(ppg_samples)} PPGs with {total_banks} total banks"
            }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Samples config not found at {config_path}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_switch_sample_bank(ppg_id: int, bank_name: str) -> Dict[str, Any]:
    """Switch active sample bank for a PPG sensor via OSC."""
    try:
        # Validate PPG ID
        if not 0 <= ppg_id <= 3:
            return {
                "success": False,
                "error": f"PPG ID must be 0-3, got {ppg_id}"
            }

        # Send /bank OSC message to sequencer
        port = osc.infer_port("/bank")
        osc.send_osc_message("/bank", [ppg_id, bank_name], port=port)

        return {
            "success": True,
            "ppg_id": ppg_id,
            "bank_name": bank_name,
            "message": f"Switched PPG {ppg_id} to bank '{bank_name}'"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Tool dispatch mapping
TOOL_FUNCTIONS = {
    "send_osc": execute_send_osc,
    "query_lighting_programs": execute_query_lighting_programs,
    "query_lighting_config": execute_query_lighting_config,
    "query_samples": execute_query_samples,
    "query_sample_banks": execute_query_sample_banks,
    "switch_sample_bank": execute_switch_sample_bank,
}


# ============================================================================
# CONTROL SESSION
# ============================================================================

class ControlSession:
    """Interactive control session with Claude Haiku."""

    def __init__(
        self,
        api_key: str,
        max_context: int = 10,
        rate_limit: int = 60
    ):
        """Initialize control session.

        Args:
            api_key: Anthropic API key
            max_context: Maximum conversation messages to keep for context
            rate_limit: Maximum commands per minute
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.max_context = max_context
        self.rate_limit = rate_limit
        self.conversation_history: List[Dict] = []
        self.command_timestamps: List[float] = []

        # System message to guide Haiku
        self.system_message = """You are an intelligent control interface for the Amor system, a heartbeat-responsive audio/visual art installation.

Your role is to translate natural language commands into OSC messages and configuration queries.

Available components:
- Lighting: Smart bulbs with 6 programs (soft_pulse, rotating_gradient, breathing_sync, convergence, wave_chase, intensity_reactive)
- Sequencer: 4 PPG sensors (0-3), each with 8 sample columns, plus latching/momentary loops
- Audio: Real-time audio playback with effects

Common OSC paths:
- /program [name] - Switch lighting program
- /select/{ppg_id} [column] - Select sample for PPG (0-7)
- /loop/toggle [loop_id] - Toggle latching loop (0-31)

Be concise and helpful. When executing commands, confirm what you did."""

    def _check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded."""
        now = time.time()
        # Remove timestamps older than 1 minute
        self.command_timestamps = [
            ts for ts in self.command_timestamps
            if now - ts < 60
        ]
        return len(self.command_timestamps) < self.rate_limit

    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool function and return result."""
        if tool_name not in TOOL_FUNCTIONS:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        func = TOOL_FUNCTIONS[tool_name]
        try:
            return func(**tool_input)
        except TypeError as e:
            return {"success": False, "error": f"Invalid arguments for {tool_name}: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Tool execution error: {e}"}

    def send_command(self, user_message: str) -> str:
        """Send command to Claude Haiku and execute resulting tool calls.

        Args:
            user_message: Natural language command from user

        Returns:
            Assistant's response message
        """
        # Check rate limit
        if not self._check_rate_limit():
            return "ERROR: Rate limit exceeded (60 commands/minute). Please wait."

        self.command_timestamps.append(time.time())

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Keep only recent context (cost optimization)
        context = self.conversation_history[-self.max_context:]

        try:
            # Call Claude Haiku with function calling
            response = self.client.messages.create(
                model="claude-haiku-4-20250514",
                max_tokens=1024,
                system=self.system_message,
                tools=TOOLS,
                messages=context
            )

            # Process tool calls
            tool_results = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    result = self.execute_tool(
                        content_block.name,
                        content_block.input
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": json.dumps(result)  # Proper JSON serialization
                    })

            # If tools were called, get final response
            if tool_results:
                # Add assistant's tool_use response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                # Add tool results as user message
                self.conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })

                # Trim context before final API call
                trimmed_context = self.conversation_history[-self.max_context:]

                final_response = self.client.messages.create(
                    model="claude-haiku-4-20250514",
                    max_tokens=512,
                    system=self.system_message,
                    messages=trimmed_context
                )

                # Safely extract text from response
                text_blocks = [block for block in final_response.content if hasattr(block, 'text')]
                assistant_message = text_blocks[0].text if text_blocks else "[No response]"

                # Add final response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
            else:
                # No tools called, extract text directly
                text_blocks = [block for block in response.content if hasattr(block, 'text')]
                assistant_message = text_blocks[0].text if text_blocks else "[No response]"

                # Add response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

            return assistant_message

        except anthropic.APIError as e:
            return f"ERROR: Claude API error: {e}"
        except anthropic.RateLimitError:
            return "ERROR: Claude API rate limit. Please wait and try again."
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"

    def run_repl(self):
        """Run interactive REPL."""
        logger.info("Amor Cmd REPL")
        logger.info("Natural language control for amor system")
        logger.info("Type 'exit' or 'quit' to exit")

        while True:
            try:
                user_input = input("> ").strip()

                if user_input.lower() in ["exit", "quit"]:
                    logger.info("Exiting...")
                    break

                if not user_input:
                    continue

                response = self.send_command(user_input)
                logger.info(f"{response}")

            except KeyboardInterrupt:
                logger.info("Exiting...")
                break
            except Exception as e:
                logger.error(f"Error: {e}")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def load_config(config_path: str) -> Dict[str, Any]:
    """Load control configuration."""
    if not Path(config_path).exists():
        # Return defaults if config doesn't exist
        return {
            "anthropic_api_key_env": "ANTHROPIC_API_KEY",
            "max_context_messages": 10,
            "rate_limit_per_minute": 60
        }

    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Amor Cmd - English-language REPL for amor system control"
    )
    parser.add_argument(
        "command",
        nargs="*",
        help="One-shot command (omit for interactive REPL)"
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CMD_CONFIG),
        help=f"Path to cmd config (default: {DEFAULT_CMD_CONFIG})"
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key (overrides config and environment)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Configure logger with specified log level
    logger.setLevel(getattr(logging, args.log_level))

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"ERROR loading config: {e}")
        logger.warning(f"Using default configuration")
        config = {
            "anthropic_api_key_env": "ANTHROPIC_API_KEY",
            "max_context_messages": 10,
            "rate_limit_per_minute": 60
        }

    # Get API key
    api_key = (
        args.api_key or
        os.getenv(config.get("anthropic_api_key_env", "ANTHROPIC_API_KEY"))
    )

    if not api_key:
        logger.error("No API key provided.")
        logger.error("Set ANTHROPIC_API_KEY environment variable or use --api-key")
        sys.exit(1)

    # Create session
    session = ControlSession(
        api_key=api_key,
        max_context=config.get("max_context_messages", 10),
        rate_limit=config.get("rate_limit_per_minute", 60)
    )

    # One-shot or interactive mode
    if args.command:
        # One-shot mode
        command_str = " ".join(args.command)
        response = session.send_command(command_str)
        logger.info(response)
    else:
        # Interactive REPL
        session.run_repl()


if __name__ == "__main__":
    main()
