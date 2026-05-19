#!/usr/bin/env python3
"""Ejecuta tests unitarios e integración (sin validación, que se ejecutan manualmente)."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    print("\n" + "="*70)
    print("EJECUTANDO TESTS (Unitarios + Integración)")
    print("="*70)
    print("\nNOTA: Tests de validación (validate_*) se ejecutan manualmente, uno a uno:")
    print("      python tests/validation/validate_collision_basic.py\n")

    # Busca tests unitarios
    unit_files = sorted(Path("tests/unit").glob("test_*.py")) if Path("tests/unit").exists() else []

    # Busca tests de integración
    integration_files = sorted(Path("tests/integration").glob("test_*.py")) if Path("tests/integration").exists() else []

    all_test_files = unit_files + integration_files

    if not all_test_files:
        print("No se encontraron tests unitarios ni de integración.")
        print("Pre-commit OK.")
        sys.exit(0)

    print(f"Tests encontrados:")
    print(f"  - Unitarios (tests/unit/test_*.py): {len(unit_files)}")
    print(f"  - Integración (tests/integration/test_*.py): {len(integration_files)}")
    print(f"  - Total: {len(all_test_files)}")

    failed = []
    for test_file in all_test_files:
        print(f"\n{'='*60}")
        print(f"Running: {test_file.relative_to('.')}")
        print('='*60)
        result = subprocess.run([sys.executable, str(test_file)])
        if result.returncode != 0:
            failed.append(str(test_file.relative_to('.')))

    if failed:
        print(f"\nFAILED: {len(failed)} test(s) fallaron:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"\nPASSED: Todos {len(all_test_files)} tests críticos pasaron!")
        sys.exit(0)
