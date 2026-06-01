#!/usr/bin/env python3
"""
Script para convertir todos los escenarios al nuevo formato multi-lane.
"""

import json
import os
from pathlib import Path

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
LANE_WIDTH_M = 3.6  # Nuevo ancho de carril


def convert_flat_lanes_to_multi_lane(scenario_data):
    """Convierte formato antiguo (flat lanes) a nuevo (roads → segments → lanes)."""

    if "road" not in scenario_data:
        return scenario_data

    road_config = scenario_data["road"]

    # Si ya está en formato nuevo (tiene "roads"), retorna sin cambios
    if "roads" in road_config:
        return scenario_data

    # Si está en formato antiguo (tiene "lanes"), convierte
    if "lanes" in road_config:
        old_lanes = road_config["lanes"]

        # Crea un segmento por cada carril antiguo
        new_roads = []
        for i, old_lane in enumerate(old_lanes):
            lane_id = old_lane.get("id", f"lane_{i}")

            # Crea estructura de road → segment → lane
            road = {
                "id": f"road_{i}",
                "name": f"Road {i}",
                "speed_limit_kmh": old_lane.get("speed_limit_kmh", 60.0),
                "segments": [
                    {
                        "id": f"segment_{i}",
                        "start": old_lane.get("start", [0, 0]),
                        "end": old_lane.get("end", [100, 0]),
                        "lanes": [
                            {
                                "id": lane_id,
                                "width_m": LANE_WIDTH_M,  # Usa el nuevo ancho
                                "zone": old_lane.get("zone", "urban"),
                                "lane_type": "normal",
                                "direction": "forward"
                            }
                        ]
                    }
                ]
            }
            new_roads.append(road)

        # Reemplaza la estructura antigua
        road_config["roads"] = new_roads
        del road_config["lanes"]

    return scenario_data


def update_agent_lanes(scenario_data):
    """Actualiza referencias a carriles en agentes."""
    if "agents" not in scenario_data:
        return scenario_data

    for agent in scenario_data["agents"]:
        # Si referencia una lane antigua, mantén el ID (será mappeable)
        # El scene loader se encargará de encontrar la lane correcta
        pass

    return scenario_data


def convert_all_scenarios():
    """Convierte todos los escenarios."""
    scenarios = sorted(SCENARIOS_DIR.glob("*.json"))

    for scenario_file in scenarios:
        print(f"\nConvirtiendo: {scenario_file.name}")

        with open(scenario_file) as f:
            data = json.load(f)

        # Convierte a nuevo formato
        data = convert_flat_lanes_to_multi_lane(data)
        data = update_agent_lanes(data)

        # Guarda con indentación
        with open(scenario_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"[OK] Actualizado: {scenario_file.name}")


if __name__ == "__main__":
    convert_all_scenarios()
    print("\n[DONE] Todos los escenarios convertidos al nuevo formato multi-lane")
    print(f"[INFO] Ancho de carril: {LANE_WIDTH_M}m")
