#!/usr/bin/env python3
"""Run all automated tests (skip interactive tests)."""

import subprocess
import sys
from pathlib import Path

INTERACTIVE_TESTS = {"test_road_scales.py", "test_stopped_car.py"}

if __name__ == "__main__":
    tests_dir = Path(".")
    test_files = sorted(tests_dir.glob("test_*.py"))
    test_files = [f for f in test_files if f.name not in INTERACTIVE_TESTS]

    failed = []
    for test_file in test_files:
        print(f"\n{'='*60}")
        print(f"Running: {test_file.name}")
        print('='*60)
        result = subprocess.run([sys.executable, str(test_file)])
        if result.returncode != 0:
            failed.append(test_file.name)

    if failed:
        print(f"\nFAILED: {len(failed)} test(s) failed:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"\nPASSED: All {len(test_files)} tests passed!")
        sys.exit(0)
