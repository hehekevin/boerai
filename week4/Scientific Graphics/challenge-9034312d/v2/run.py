#!/usr/bin/env python3
"""Entry point for the FigForge engine.

Usage (from anywhere):
    python <skill-dir>/run.py probe --case /input/case.json --out /app/work
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
