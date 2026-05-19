#!/usr/bin/env python3
"""Wrapper para ejecutar tests desde Python directamente."""

import subprocess
import sys

if __name__ == "__main__":
    # Ejecuta el test usando el mismo interprete de Python que está corriendo esto
    result = subprocess.run([sys.executable, "test_road_scales.py"], cwd=".")
    sys.exit(result.returncode)
