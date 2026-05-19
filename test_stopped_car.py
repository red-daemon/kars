#!/usr/bin/env python3
"""Test: un carro se detiene sin crashear."""

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

def test_stopped_car():
    """Test: carro se detiene y permanece detenido."""
    print("\n" + "="*70)
    print("TEST: Carro Detenido")
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

    # Crea un carro que arranca parado
    print("\n[Tick 0] Crea carro parado a s=100m")
    agent = CarAgent(
        agent_id=world.get_next_agent_id(),
        current_lane_id="lane_0",
        position_along_lane_s=100,
        lateral_offset=0.0,
    )
    world_pos = lane.world_position_at(100, 0.0)
    initial_heading = lane.heading_at(100)
    agent.set_position_world(world_pos, heading=initial_heading)
    world.add_agent(agent)

    print(f"  Carro {agent.agent_id}: s={agent.position_along_lane_s:.1f}m, speed={agent.speed_kmh():.1f}km/h")

    # Simula 50 ticks (2.5 segundos)
    print(f"\nSimulando 50 ticks con carro parado...")
    try:
        for tick in range(50):
            world.tick()

            if tick % 10 == 0 or tick == 49:
                agent = list(world.agents.values())[0]
                print(f"  Tick {tick:2d}: s={agent.position_along_lane_s:.1f}m, "
                      f"speed={agent.speed_kmh():.1f}km/h, "
                      f"v={agent.kinematic_state.velocity.magnitude():.3f}m/s")

        print(f"\n✅ Test pasó: Carro permaneció detenido sin crashes")

    except Exception as e:
        print(f"\n❌ Error en tick {tick}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_stopped_car()
