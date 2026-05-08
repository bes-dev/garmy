#!/usr/bin/env python3
"""Entry point for running localdb as a module: python -m garmy.localdb"""

from .cli import main

if __name__ == "__main__":
    exit(main())
