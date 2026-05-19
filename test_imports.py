#!/usr/bin/env python3
"""Test que los imports básicos funcionan."""

try:
    print("Importando config...")
    import kars.config as config
    print(f"  ✓ ZONE_TRAFFIC: {list(config.ZONE_TRAFFIC.keys())}")
    print(f"  ✓ COLLISION_DISABLE_TICKS: {config.COLLISION_DISABLE_TICKS}")

    print("\nImportando Lane...")
    from kars.environment.lane import Lane
    from kars.physics.models import Vector2, Waypoint
    lane = Lane(
        lane_id="test",
        waypoints=[Waypoint(Vector2(0, 0), 0), Waypoint(Vector2(100, 0), 0)],
        zone="urban"
    )
    print(f"  ✓ Lane creado con zone='{lane.zone}'")

    print("\nImportando CarAgent...")
    from kars.agents.car_agent import CarAgent
    agent = CarAgent(
        agent_id=1000,
        current_lane_id="test",
        position_along_lane_s=0,
        is_disabled=False,
        disable_ticks_remaining=0,
        shoulder_offset=0.0,
    )
    print(f"  ✓ CarAgent creado con is_disabled={agent.is_disabled}")

    print("\nImportando World...")
    from kars.environment.road_network import RoadNetwork
    from kars.environment.segment import RoadSegment
    from kars.simulation.world import World

    segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(100, 0))
    network = RoadNetwork()
    network.add_segment(segment)
    world = World(network)
    print(f"  ✓ World creado con {world.num_agents()} agentes iniciales")

    print("\n✅ Todos los imports y estructuras básicas funcionan correctamente")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
