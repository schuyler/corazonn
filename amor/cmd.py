#!/usr/bin/env python3
"""
Cmd - English-language REPL for Amor system control

Interactive REPL and one-shot command execution using Claude Haiku
for natural language → structured OSC command translation + Freesound discovery.

Usage:
    Interactive REPL:
        python -m amor.cmd

    One-shot command:
        python -m amor.cmd "start the sequencer"
        python -m amor.cmd "switch to soft pulse lighting"
        python -m amor.cmd "find me a deep metallic gong sound"

Architecture:
- Claude Haiku function calling for NL → structured commands
- Freesound search with NL → query translation
- Automatic sample download and processing (48kHz mono WAV)
- Lightweight conversation context (last N messages)
- Cost-optimized (Haiku API calls)
- Extensible function definitions

Functions execute via:
- amor.osc.send_osc_message() for OSC commands
- PyYAML for config queries
- Freesound API for sound discovery
- Sox for audio processing
"""

import anthropic
import yaml
import json
import os
import sys
import argparse
import logging
import time
import subprocess
import tempfile
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
    {
        "name": "search_freesound",
        "description": "Search Freesound.org using natural language, download, process, and optionally assign to a PPG slot. Translates descriptions like 'deep metallic gong' into Freesound queries with filters. Can directly assign to sequencer slots.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Natural language description of desired sound (e.g., 'dark ambient drone', 'short metallic bell hit')"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to download (default: 1)",
                    "minimum": 1,
                    "maximum": 10
                },
                "ppg_id": {
                    "type": "integer",
                    "description": "PPG sensor ID (0-3) to assign sound to. If provided, slot must also be specified.",
                    "minimum": 0,
                    "maximum": 3
                },
                "slot": {
                    "type": "integer",
                    "description": "Sample slot/column (0-7) within the PPG's default bank. Required if ppg_id is provided.",
                    "minimum": 0,
                    "maximum": 7
                }
            },
            "required": ["description"]
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


def execute_search_freesound(
    description: str,
    num_results: int = 1,
    ppg_id: Optional[int] = None,
    slot: Optional[int] = None
) -> Dict[str, Any]:
    """Search Freesound using natural language, download, process, and optionally assign to PPG slot."""
    try:
        # Validate ppg_id and slot parameters
        if (ppg_id is not None and slot is None) or (slot is not None and ppg_id is None):
            return {
                "success": False,
                "error": "Both ppg_id and slot must be provided together, or neither"
            }
        # Import freesound library
        try:
            import freesound
        except ImportError:
            return {
                "success": False,
                "error": "freesound-python not installed. Install with: pip install git+https://github.com/MTG/freesound-python"
            }

        from dotenv import load_dotenv

        # Load environment
        load_dotenv(AMOR_ROOT / ".env")

        # Get Freesound credentials
        access_token = os.getenv("FREESOUND_ACCESS_TOKEN")
        if not access_token:
            return {
                "success": False,
                "error": "FREESOUND_ACCESS_TOKEN not found in .env. Run: python audio/download_freesound_library.py auth"
            }

        # Get Anthropic API key for query translation
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "ANTHROPIC_API_KEY not found in environment"
            }

        # Use Haiku to translate NL description to Freesound query parameters
        client = anthropic.Anthropic(api_key=api_key)

        translation_prompt = f"""Translate this natural language sound description into Freesound API search parameters.

Description: "{description}"

Analyze the description and extract:
1. Query string (keywords for Freesound text search)
2. Duration filter (min/max in seconds, or null if not specified)
3. Tags (relevant audio tags, or empty list)
4. Family classification (MUST be exactly one of: hit, drone, ambient, nature)

Respond with valid JSON in this exact format:
{{
  "query": "search keywords",
  "duration_min": null,
  "duration_max": null,
  "tags": ["tag1", "tag2"],
  "family": "hit"
}}

Examples:
- "short metallic bell" → {{"query": "bell metal", "duration_min": null, "duration_max": 2.0, "tags": ["bell", "metal"], "family": "hit"}}
- "deep ambient drone" → {{"query": "ambient drone deep", "duration_min": 3.0, "duration_max": null, "tags": ["ambient", "drone"], "family": "drone"}}
- "water drop sound" → {{"query": "water drop", "duration_min": null, "duration_max": 2.0, "tags": ["water"], "family": "nature"}}

Now translate: "{description}" """

        response = client.messages.create(
            model="claude-haiku-4-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": translation_prompt}]
        )

        # Extract JSON from response
        response_text = response.content[0].text.strip()
        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        search_params = json.loads(response_text)

        # Initialize Freesound client
        fs_client = freesound.FreesoundClient()
        fs_client.set_token(access_token, "oauth")

        # Build filter string
        filter_parts = []
        if search_params.get("duration_min"):
            filter_parts.append(f"duration:[{search_params['duration_min']} TO *]")
        if search_params.get("duration_max"):
            filter_parts.append(f"duration:[* TO {search_params['duration_max']}]")

        filter_str = " ".join(filter_parts) if filter_parts else None

        # Search Freesound
        results = fs_client.text_search(
            query=search_params["query"],
            filter=filter_str,
            sort="rating_desc",
            fields="id,name,username,license,duration,previews,download",
            page_size=num_results
        )

        if not results.results:
            return {
                "success": False,
                "error": f"No results found for query: {search_params['query']}"
            }

        # Create family directory
        family = search_params["family"]
        family_dir = AMOR_ROOT / "audio" / "library" / family
        family_dir.mkdir(parents=True, exist_ok=True)

        # Download and process samples
        downloaded_files = []

        for sound in results.results[:num_results]:
            # Download to temp directory
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Download original file
                sound.retrieve(str(tmpdir_path), f"{sound.id}_original")

                # Find downloaded file (extension may vary)
                downloaded = list(tmpdir_path.glob(f"{sound.id}_original.*"))
                if not downloaded:
                    logger.warning(f"Failed to download sound {sound.id}")
                    continue

                input_file = downloaded[0]

                # Process with sox (direct processing for control over filenames)
                # Sanitize filename
                safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in sound.name)
                safe_name = safe_name.replace(" ", "_")[:30]
                output_file = family_dir / f"{sound.id}_{safe_name}.wav"

                # Get duration for fade
                duration = sound.duration if hasattr(sound, 'duration') else 2.5
                fade_duration = 0.2

                # Sox processing: mono, 48kHz, normalize to -3dB, fade out
                subprocess.run([
                    "sox", str(input_file), str(output_file),
                    "remix", "1",
                    "rate", "48000",
                    "gain", "-n", "-3",
                    "fade", "t", "0", str(duration), str(fade_duration)
                ], check=True, capture_output=True)

                downloaded_files.append({
                    "id": sound.id,
                    "name": sound.name,
                    "duration": sound.duration,
                    "file": str(output_file.relative_to(AMOR_ROOT))
                })

        # If ppg_id and slot provided, update samples.yaml config
        assignment_message = ""
        if ppg_id is not None and slot is not None and downloaded_files:
            config_path = DEFAULT_SAMPLES_CONFIG

            try:
                # Load current config
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)

                # Ensure ppg_samples structure exists
                if 'ppg_samples' not in config:
                    config['ppg_samples'] = {}

                # Ensure PPG exists
                if ppg_id not in config['ppg_samples']:
                    config['ppg_samples'][ppg_id] = {}

                # Ensure default bank exists
                if 'default' not in config['ppg_samples'][ppg_id]:
                    config['ppg_samples'][ppg_id]['default'] = []

                # Get the default bank
                bank = config['ppg_samples'][ppg_id]['default']

                # Extend bank to accommodate slot if necessary
                while len(bank) <= slot:
                    bank.append(None)

                # Store old file for reference
                old_file = bank[slot]

                # Assign first downloaded file to slot
                new_file_path = downloaded_files[0]['file']
                bank[slot] = new_file_path

                # Write updated config
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                assignment_message = f" → Assigned to PPG {ppg_id} slot {slot}"
                if old_file:
                    assignment_message += f" (replaced {Path(old_file).name})"

            except Exception as e:
                assignment_message = f" (WARNING: Config update failed: {e})"

        return {
            "success": True,
            "query": search_params["query"],
            "family": family,
            "num_downloaded": len(downloaded_files),
            "files": downloaded_files,
            "assignment": {"ppg_id": ppg_id, "slot": slot} if ppg_id is not None else None,
            "message": f"Downloaded {len(downloaded_files)} sound(s) to {family} family: {', '.join(f['name'] for f in downloaded_files)}{assignment_message}"
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse Haiku response as JSON: {e}"
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"Sample processing failed: {e.stderr.decode() if e.stderr else str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {type(e).__name__}: {str(e)}"
        }


# Tool dispatch mapping
TOOL_FUNCTIONS = {
    "send_osc": execute_send_osc,
    "query_lighting_programs": execute_query_lighting_programs,
    "query_lighting_config": execute_query_lighting_config,
    "query_samples": execute_query_samples,
    "query_sample_banks": execute_query_sample_banks,
    "switch_sample_bank": execute_switch_sample_bank,
    "search_freesound": execute_search_freesound,
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

Your role is to translate natural language commands into OSC messages, configuration queries, and sound discovery.

Available components:
- Lighting: Smart bulbs with 6 programs (soft_pulse, rotating_gradient, breathing_sync, convergence, wave_chase, intensity_reactive)
- Sequencer: 4 PPG sensors (0-3), each with 8 sample columns, plus latching/momentary loops
- Audio: Real-time audio playback with effects
- Sound Search: Natural language Freesound.org search with automatic download and processing

Common OSC paths:
- /program [name] - Switch lighting program
- /select/{ppg_id} [column] - Select sample for PPG (0-7)
- /loop/toggle [loop_id] - Toggle latching loop (0-31)

Sound discovery:
- Use search_freesound for natural language sound requests (e.g., "find a deep metallic gong")
- Sounds are automatically downloaded, processed (48kHz mono WAV), and stored by family (hit/drone/ambient/nature)
- Can directly assign sounds to PPG slots (e.g., "find a deep gong and put it in PPG 2 slot 3")
- Assignments update amor/config/samples.yaml, replacing the old sample pointer (old file stays on disk)

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
