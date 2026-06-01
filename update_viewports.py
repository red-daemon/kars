#!/usr/bin/env python3
"""
Actualiza todos los scenarios para usar visible_length_m en lugar de viewport_x_min/max.
Estructura: visible_length_m define cuánta calle queremos ver.
El renderer agrega 20m de margen antes y después automáticamente.
"""

import json
from pathlib import Path

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
MARGIN_M = 20.0  # Margen antes y después


def update_scenario_viewport(scenario_data):
    """Convierte viewport_x_min/max a visible_length_m."""

    if "camera" not in scenario_data:
        scenario_data["camera"] = {}

    camera = scenario_data["camera"]

    # Si ya tiene visible_length_m, OK
    if "visible_length_m" in camera:
        return scenario_data

    # Si tiene viewport_x_min/max, convierte
    if "viewport_x_min_m" in camera and "viewport_x_max_m" in camera:
        x_min = camera["viewport_x_min_m"]
        x_max = camera["viewport_x_max_m"]
        visible_length = x_max - x_min

        # Reemplaza con visible_length_m
        camera["visible_length_m"] = visible_length
        del camera["viewport_x_min_m"]
        del camera["viewport_x_max_m"]
    else:
        # Default: 150m visible
        camera["visible_length_m"] = 150.0

    return scenario_data


def update_all():
    """Actualiza todos los scenarios."""
    scenarios = sorted(SCENARIOS_DIR.glob("*.json"))

    for scenario_file in scenarios:
        print(f"Actualizando: {scenario_file.name}")

        with open(scenario_file) as f:
            data = json.load(f)

        data = update_scenario_viewport(data)

        with open(scenario_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"  -> visible_length_m: {data['camera']['visible_length_m']}")


if __name__ == "__main__":
    update_all()
    print(f"\n[DONE] Todos los scenarios usan visible_length_m")
    print(f"[INFO] Margen automático: {MARGIN_M}m antes y {MARGIN_M}m después")
