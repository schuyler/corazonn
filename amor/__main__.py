#!/usr/bin/env python3
"""
Entry point for running amor.osc as a module.

Usage:
    python -m amor.osc <address> [arg1] [arg2] ...
"""

import sys

# When running as module, sys.argv[0] is the module path
# Check if we're running the osc submodule
if 'osc' in sys.argv[0] or len(sys.argv) > 1:
    # Import only when needed to avoid circular import warnings
    from amor.osc import main
    main()
else:
    print("Usage: python -m amor.osc <address> [arg1] [arg2] ...")
    sys.exit(1)
