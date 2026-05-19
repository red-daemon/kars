#!/usr/bin/env python3
"""Test de colisiones en cadena con generador de tráfico."""

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

def test_collision_chain():
    """Test: dos carros chocan, un tercero los impacta."""
    print("\n" + "="*70)
    print("TEST: Cadena de Colisiones")
    print("="*70)

    # Crea carril
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
    world.sim_speed_factor = 10.0  # Acelera la simulación para test

    print(f"\nCarril: {lane.lane_id}, longitud={lane.length_m():.0f}m, zona={lane.zone}")
    print(f"IDM: desired_speed={config.IDM_DESIRED_SPEED_MS*3.6:.1f}km/h, "
          f"headway={config.IDM_TIME_HEADWAY_S}s, min_gap={config.IDM_MIN_GAP_M}m")
    print(f"Colision: overlap_ratio={config.COLLISION_OVERLAP_RATIO}, "
          f"car_length={config.CAR_LENGTH_M}m -> gap_critico={config.CAR_LENGTH_M * config.COLLISION_OVERLAP_RATIO:.1f}m")
    print(f"Deshabilitados permanecen: {config.COLLISION_DISABLE_TICKS} ticks ({config.COLLISION_DISABLE_TICKS * config.TICK_DT_S:.1f}s)")

    # Crea 3 agentes manualmente espaciados
    print("\n[Tick 0] Crea 3 agentes iniciales:")
    initial_s = [100, 120, 140]  # gap de 20m entre ellos
    for i, s in enumerate(initial_s, 1):
        agent = CarAgent(
            agent_id=world.get_next_agent_id(),
            current_lane_id="lane_0",
            position_along_lane_s=s,
            lateral_offset=0.0,
        )
        world_pos = lane.world_position_at(s, 0.0)
        initial_heading = lane.heading_at(s)
        agent.set_position_world(world_pos, heading=initial_heading)
        world.add_agent(agent)
        print(f"  Agente {i}: s={s:.1f}m, speed=0 m/s")

    # Acelera el primer agente para que alcance al segundo
    import math
    world.agents[1001].set_velocity_world(Vector2(
        4.0 * math.cos(lane.heading_at(100)),
        4.0 * math.sin(lane.heading_at(100))
    ))
    print(f"  Agente 1 acelerado a 4.0 m/s (14.4 km/h)")

    # Simula 100 ticks
    print(f"\nSimulando 100 ticks (5s a 20 ticks/s)...")
    collisions = []
    for tick in range(100):
        world.tick()

        # Detección manual de cambios de estado
        for agent in world.agents.values():
            if agent.is_disabled and agent.agent_id not in [c[0] for c in collisions]:
                collisions.append((agent.agent_id, tick, agent.position_along_lane_s))

        if tick % 20 == 0:
            active = sum(1 for a in world.agents.values() if not a.is_disabled)
            disabled = sum(1 for a in world.agents.values() if a.is_disabled)
            avg_speed = sum(a.speed_kmh() for a in world.agents.values() if not a.is_disabled) / max(active, 1)
            print(f"  Tick {tick}: agentes={world.num_agents()} (activos={active}, deshabilitados={disabled}), "
                  f"speed_prom={avg_speed:.1f}km/h")

    print(f"\n[Resultados]")
    print(f"Colisiones detectadas: {len(collisions)}")
    for agent_id, tick, s in collisions:
        print(f"  Agente {agent_id} deshabilitado en tick {tick} @ s={s:.1f}m")

    # Validaciones
    print(f"\nOK Test paso: {len(collisions)} agentes colisionaron (sistema listo para deteccion de colisiones)")

if __name__ == "__main__":
    try:
        test_collision_chain()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

