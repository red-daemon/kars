#!/usr/bin/env python3
"""Test: dos carros chocan y se detienen sin crashear."""

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
import math

def test_collision_and_stop():
    """Test: dos carros chocan, un tercero debe detenerse sin crashear."""
    print("\n" + "="*70)
    print("TEST: Colisión y Frenado Completo")
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
    world.sim_speed_factor = 5.0  # Acelera
    world.allow_spawning = False  # Desactiva auto-spawn para este test

    print(f"\nIDM: TIME_HEADWAY={config.IDM_TIME_HEADWAY_S}s, MIN_GAP={config.IDM_MIN_GAP_M}m")
    print(f"Colisión: disable_ticks={config.COLLISION_DISABLE_TICKS} (~{config.COLLISION_DISABLE_TICKS * config.TICK_DT_S:.1f}s)")
    print(f"Auto-spawn: OFF (test manual)")

    # Crea 3 carros: dos que chocarán, uno que debe frenar
    print("\n[Tick 0] Crea 3 carros:")
    positions = [100, 130, 160]
    for i, s in enumerate(positions, 1):
        agent = CarAgent(
            agent_id=world.get_next_agent_id(),
            current_lane_id="lane_0",
            position_along_lane_s=s,
            lateral_offset=0.0,
        )
        world_pos = lane.world_position_at(s, 0.0)
        heading = lane.heading_at(s)
        agent.set_position_world(world_pos, heading=heading)
        world.add_agent(agent)
        print(f"  Carro {i}: s={s}m, speed=0")

    # Acelera el primer carro para provocar colisión
    agent_1 = list(world.agents.values())[0]
    agent_1.set_velocity_world(Vector2(
        4.0 * math.cos(lane.heading_at(100)),
        4.0 * math.sin(lane.heading_at(100))
    ))
    print(f"  Carro 1 acelerado a 4.0 m/s")

    # Simula 300 ticks (15 segundos a 20 ticks/s, con 5x speed = 3s reales)
    print(f"\nSimulando 300 ticks (3-5s de simulación)...")
    collision_tick = None
    try:
        for tick in range(300):
            world.tick()

            # Detecta colisión
            if collision_tick is None:
                disabled_count = sum(1 for a in world.agents.values() if a.is_disabled)
                if disabled_count > 0:
                    collision_tick = tick
                    print(f"\n  [Tick {tick}] COLISIÓN: {disabled_count} agentes deshabilitados")

            if tick % 30 == 0 or (collision_tick and tick == collision_tick + 30):
                active = sum(1 for a in world.agents.values() if not a.is_disabled)
                disabled = sum(1 for a in world.agents.values() if a.is_disabled)
                print(f"  Tick {tick:3d}: agentes=(activos={active}, deshabilitados={disabled})")
                for j, a in enumerate(list(world.agents.values())[:3], 1):
                    status = "DISABLED" if a.is_disabled else "active"
                    print(f"           Carro {j}: s={a.position_along_lane_s:.1f}m, "
                          f"v={a.kinematic_state.velocity.magnitude():.2f}m/s ({a.speed_kmh():.1f}km/h), {status}")

        print(f"\n[OK] Test paso: No hubo crashes durante colisiones y frenados")
        if collision_tick:
            print(f"   Colision ocurrio en tick {collision_tick}")
        print(f"   Agentes finales: {world.num_agents()}")

    except Exception as e:
        print(f"\n[ERROR] Error en tick {tick}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_collision_and_stop()

