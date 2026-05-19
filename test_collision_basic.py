#!/usr/bin/env python3
"""Test: colisión forzada entre dos carros."""

import sys
sys.path.insert(0, '/c/Users/bgaxiola/OneDrive - Capgemini/Projects/Kars')

from kars.physics.models import Vector2, Waypoint
from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.world import World
import kars.config as config
import math

def test_basic_collision():
    """Test: dos carros en colision frontal."""
    print("\n" + "="*70)
    print("TEST: Colision Frontal Basica")
    print("="*70)

    lane = Lane(
        lane_id="lane_0",
        waypoints=[
            Waypoint(Vector2(0, 0), heading=0),
            Waypoint(Vector2(1000, 0), heading=0)
        ],
        width_m=2.7,
        speed_limit_kmh=20.0,
        zone="urban",
    )

    segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(1000, 0))
    network = RoadNetwork()
    network.add_segment(segment)

    world = World(network)
    world.allow_spawning = False
    world.sim_speed_factor = 5.0

    print(f"\nConfiguracion:")
    print(f"  Carro 1 (adelante): posicion=100m, velocidad=0.0m/s (detenido)")
    print(f"  Carro 2 (atras):    posicion=98.5m, velocidad=3.0m/s (avanzando)")
    print(f"  Distancia inicial: 1.5m < threshold de colision (2.25m)")
    print(f"  --> COLISION DEBE DETECTARSE EN TICK 0")

    # Carro 1: detenido (adelante)
    agent_1 = CarAgent(
        agent_id=world.get_next_agent_id(),
        current_lane_id="lane_0",
        position_along_lane_s=100.0,
        lateral_offset=0.0,
    )
    world_pos_1 = lane.world_position_at(100.0, 0.0)
    agent_1.set_position_world(world_pos_1, heading=0)
    agent_1.set_position_lane("lane_0", 100.0, 0.0)  # Asegura sync
    agent_1.set_velocity_world(Vector2(0.0, 0.0))
    world.add_agent(agent_1)

    # Carro 2: muy cerca, velocidad moderada
    agent_2 = CarAgent(
        agent_id=world.get_next_agent_id(),
        current_lane_id="lane_0",
        position_along_lane_s=98.5,
        lateral_offset=0.0,
    )
    world_pos_2 = lane.world_position_at(98.5, 0.0)
    agent_2.set_position_world(world_pos_2, heading=0)
    agent_2.set_position_lane("lane_0", 98.5, 0.0)  # Asegura sync
    agent_2.set_velocity_world(Vector2(3.0, 0.0))  # 3 m/s
    world.add_agent(agent_2)

    print(f"\nSimulando 200 ticks (hasta colision)...")
    collision_detected = False
    collision_tick = None

    try:
        for tick in range(200):
            world.tick()

            agents_list = list(world.agents.values())
            if len(agents_list) >= 2:
                a1, a2 = agents_list[0], agents_list[1]
                # Determina cuál está adelante
                if a1.position_along_lane_s > a2.position_along_lane_s:
                    a1, a2 = a2, a1  # Swap para que a2 sea el adelante
                gap = a2.position_along_lane_s - a1.position_along_lane_s - config.CAR_LENGTH_M
            else:
                continue
            disabled_a1 = a1.is_disabled
            disabled_a2 = a2.is_disabled

            # Detecta colision
            if not collision_detected:
                if disabled_a1 or disabled_a2:
                    collision_detected = True
                    collision_tick = tick

            if tick % 20 == 0 or (collision_detected and tick <= collision_tick + 5):
                disabled = sum(1 for a in world.agents.values() if a.is_disabled)
                print(f"  Tick {tick:3d}: gap={gap:6.2f}m, "
                      f"v1={a1.kinematic_state.velocity.magnitude():.2f}m/s, "
                      f"v2={a2.kinematic_state.velocity.magnitude():.2f}m/s, "
                      f"disabled={disabled}, a1_dis={disabled_a1}, a2_dis={disabled_a2}")

                if collision_detected and tick == collision_tick:
                    print(f"           >>> COLISION DETECTADA en Tick {collision_tick} <<<)")

        if collision_detected:
            print(f"\n[OK] COLISION DETECTADA en tick {collision_tick}")
            print(f"     Sistema de colisiones funciona correctamente")
        else:
            print(f"\n[WARN] No se detecto colision despues de 200 ticks")
            print(f"      Gap final: {a2.position_along_lane_s - a1.position_along_lane_s:.2f}m")

    except Exception as e:
        print(f"\n[ERROR] Error en tick {tick}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_basic_collision()
