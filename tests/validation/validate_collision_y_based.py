#!/usr/bin/env python3
"""Validación interactiva: collision detection basada en Y-position."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kars.physics.models import Vector2, Waypoint
from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.world import World
import kars.config as config


def validate_y_based_collision():
    """
    Valida que la detección de colisiones usa Y-position, no S-position gap.

    Crea dos carros en la misma posición aproximada (pero con offset pequeño)
    y verifica que se detecte colisión cuando sus Y se solapan.
    """
    print("\n" + "="*70)
    print("VALIDACIÓN: Collision Detection basada en Y-Position")
    print("="*70)

    # Crea carril recto horizontal (Y = 0)
    lane = Lane(
        lane_id="lane_0",
        waypoints=[
            Waypoint(Vector2(0, 0), heading=0),
            Waypoint(Vector2(1000, 0), heading=0)
        ],
        width_m=2.7,
        speed_limit_kmh=50.0,
    )

    segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(1000, 0))
    network = RoadNetwork()
    network.add_segment(segment)

    # Crea world sin auto-spawn
    world = World(network, allow_spawning=False)

    print("\n[Setup] Creando 2 carros para prueba de colisión...")

    # Carro 1: posición s=200m, velocidad inicial 5 m/s
    agent1 = CarAgent(
        agent_id=1,
        current_lane_id="lane_0",
        position_along_lane_s=200.0,
        lateral_offset=0.0,
    )
    pos1 = lane.world_position_at(200.0, 0.0)
    agent1.set_position_world(pos1, heading=0)
    from kars.physics.models import KinematicState, Vector2
    agent1.kinematic_state = KinematicState(
        position=pos1,
        velocity=Vector2(5.0, 0.0),  # 5 m/s hacia adelante
        acceleration=Vector2(0, 0),
        heading=0,
    )
    world.add_agent(agent1)
    print(f"  Carro 1: s={agent1.position_along_lane_s:.1f}m, velocidad={5.0} m/s")

    # Carro 2: posición s=210m (10m adelante), velocidad inicial 0 m/s (parado)
    agent2 = CarAgent(
        agent_id=2,
        current_lane_id="lane_0",
        position_along_lane_s=210.0,
        lateral_offset=0.0,
    )
    pos2 = lane.world_position_at(210.0, 0.0)
    agent2.set_position_world(pos2, heading=0)
    agent2.kinematic_state = KinematicState(
        position=pos2,
        velocity=Vector2(0.0, 0.0),  # Parado
        acceleration=Vector2(0, 0),
        heading=0,
    )
    world.add_agent(agent2)
    print(f"  Carro 2: s={agent2.position_along_lane_s:.1f}m, velocidad={0.0} m/s (parado)")

    print(f"\n[Física] Carro 1 se acerca a Carro 2...")
    print(f"  GAP inicial: {agent2.position_along_lane_s - agent1.position_along_lane_s:.1f}m")
    print(f"  Esperado: colisión después de ~{10.0 / 5.0:.1f}s")

    # Simula ticks hasta colisión
    collision_tick = None
    max_ticks = 100  # ~5 segundos a 20 ticks/s

    print(f"\n[Simulación] Corriendo hasta colisión o max {max_ticks} ticks...")
    print(f"  {'Tick':<6} {'Agent1 S':<12} {'Agent1 Dis':<12} {'Agent2 S':<12} {'Gap':<10} {'Disabled':<10}")
    print(f"  " + "-"*60)

    for tick in range(max_ticks):
        world.tick()

        # Lee estado actual
        a1 = world.agents.get(1)
        a2 = world.agents.get(2)

        if a1 and a2:
            gap = a2.position_along_lane_s - a1.position_along_lane_s
            both_disabled = a1.is_disabled and a2.is_disabled

            if tick % 5 == 0 or both_disabled:
                print(f"  {tick:<6} {a1.position_along_lane_s:<12.2f} {a1.kinematic_state.position.x:<12.2f} "
                      f"{a2.position_along_lane_s:<12.2f} {gap:<10.2f} {str(both_disabled):<10}")

            if both_disabled and collision_tick is None:
                collision_tick = tick
                print(f"  >>> COLISIÓN DETECTADA en tick {tick}")
                break

    print(f"  " + "-"*60)

    # Resultados
    print(f"\n[Resultados]")
    if collision_tick is not None:
        print(f"  ✓ Colisión detectada correctamente en tick {collision_tick}")
        print(f"  ✓ Sistema Y-based funciona: agentes parados tras solapamiento")
        final_gap = agent2.position_along_lane_s - agent1.position_along_lane_s
        print(f"  ✓ Gap final: {final_gap:.2f}m (deberían estar solapados)")
    else:
        print(f"  ✗ FALLO: Colisión no detectada después de {max_ticks} ticks")
        print(f"  ✗ Verificar implementación de Y-position basada en world_position_at()")

    print("\n" + "="*70)


if __name__ == "__main__":
    validate_y_based_collision()
