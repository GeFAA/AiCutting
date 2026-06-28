"""Packaging entry point for AiCutting Studio (used by pyside6-deploy).

Run the app for development with `aicutting-studio` (or `aicutting gui`); this file exists so the
deploy tool has a single windowed entry point to bundle into a standalone Windows app.
"""

import sys

from aicutting.gui.app import main_cli

if __name__ == "__main__":
    sys.exit(main_cli())
