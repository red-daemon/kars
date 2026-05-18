#!/usr/bin/env python3
"""Test runner simple sin pytest."""

import sys
import traceback
from pathlib import Path

# Agrega el proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

# Importa los tests
from tests.unit.test_lane import TestLaneGeometry, TestLaneNormal, TestLaneOffset, TestLaneValidation
from tests.unit.test_agents import TestPerceptionData, TestPerceptionModule, TestCarAgent, TestSpatialGrid
from tests.unit.test_world import TestWorld, TestScheduler, TestStatsCollector

def run_test_class(test_class):
    """Ejecuta todos los test_* methods de una clase."""
    total = 0
    passed = 0
    failed = 0

    class_name = test_class.__name__
    print(f"\n{'=' * 70}")
    print(f"  {class_name}")
    print(f"{'=' * 70}")

    instance = test_class()

    for attr_name in dir(instance):
        if attr_name.startswith("test_"):
            total += 1
            try:
                method = getattr(instance, attr_name)
                method()
                print(f"  [PASS] {attr_name}")
                passed += 1
            except AssertionError as e:
                print(f"  [FAIL] {attr_name}")
                print(f"         {e}")
                failed += 1
            except Exception as e:
                print(f"  [ERROR] {attr_name}")
                traceback.print_exc()
                failed += 1

    return total, passed, failed


def main():
    """Ejecuta todos los tests."""
    print("\n" + "=" * 70)
    print("  KARS: Lane Tests")
    print("=" * 70)

    test_classes = [
        TestLaneGeometry,
        TestLaneNormal,
        TestLaneOffset,
        TestLaneValidation,
        TestPerceptionData,
        TestPerceptionModule,
        TestCarAgent,
        TestSpatialGrid,
        TestWorld,
        TestScheduler,
        TestStatsCollector,
    ]

    total_all = 0
    passed_all = 0
    failed_all = 0

    for test_class in test_classes:
        total, passed, failed = run_test_class(test_class)
        total_all += total
        passed_all += passed
        failed_all += failed

    print(f"\n{'=' * 70}")
    print(f"  RESUMEN: {passed_all}/{total_all} tests pasados")
    if failed_all > 0:
        print(f"  ERRORES: {failed_all}")
    print(f"{'=' * 70}\n")

    return 0 if failed_all == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
