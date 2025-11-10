"""Wrapper module for discover-kasa tool to enable entry point."""

import importlib.util
from pathlib import Path

# Load the discover-kasa.py script
script_path = Path(__file__).parent / "discover-kasa.py"
spec = importlib.util.spec_from_file_location("discover_kasa_script", script_path)
discover_kasa_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discover_kasa_script)

# Export main function
main = discover_kasa_script.main

__all__ = ["main"]
