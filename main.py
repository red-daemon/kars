#!/usr/bin/env python3
"""Entry point del simulador KARS."""

import sys
sys.path.insert(0, '/c/Users/bgaxiola/OneDrive - Capgemini/Projects/Kars')

import math
import random

from kars.physics.models import Vector2, Waypoint
from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.world import World
from kars.utils.yaml_loader import ScenarioLoader
import kars.config as config


def demo_headless_simulation():
    """Demo: Simulacion headless (sin Pygame) del MVP."""
    print("\n" + "=" * 70)
    print("  FASE 1 PARTE 3: World + Simulation (Headless)")
    print("=" * 70)

    # Crea entorno
    lane = Lane(
        lane_id="lane_0",
        waypoints=[Waypoint(Vector2(0, 0), heading=0), Waypoint(Vector2(500, 0), heading=0)],
        width_m=2.7,
        speed_limit_kmh=20.0,
    )

    segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(500, 0))

    network = RoadNetwork()
    network.add_segment(segment)

    # Crea World
    world = World(network)

    # Crea agentes y los agrega a World
    print("\nCreando 5 agentes...")
    for i in range(5):
        agent = CarAgent(
            agent_id=i + 1,
            current_lane_id="lane_0",
            position_along_lane_s=50.0 + i * 80.0,  # Espaciados
            lateral_offset=0.0,
        )

        # Sincroniza posicion mundo
        world_pos = lane.world_position_at(agent.position_along_lane_s, 0.0)
        agent.set_position_world(world_pos, heading=0)

        world.add_agent(agent)

    print(f"Agentes: {world.num_agents()}")
    print(f"\nSimulando 20 segundos (400 ticks)...")
    print(f"  Tick    Tiempo   Avg Speed   Agentes")
    print(f"  " + "-" * 45)

    # Simula
    for _ in range(400):
        world.tick()

        # Imprime cada 50 ticks (2.5 segundos)
        if world.tick_number % 50 == 0:
            stats = world.stats_collector.get_last_tick()
            print(
                f"  {world.tick_number:4d}    {world.sim_time_s:6.2f}s   "
                f"{stats.avg_speed_kmh:6.2f}km/h   {world.num_agents()}"
            )

    print(f"  " + "-" * 45)

    # Estadisticas finales
    summary = world.stats_collector.get_summary()
    print(f"\nEstadisticas finales:")
    print(f"  Tiempo total: {summary['total_sim_time_s']:.1f}s")
    print(f"  Velocidad promedio: {summary['avg_agent_speed_kmh']:.2f} km/h")
    print(f"  Velocidad maxima: {summary['max_agent_speed_kmh']:.2f} km/h")

    # Muestra estado final de agentes
    print(f"\nEstado final de agentes:")
    print(f"  ID    Lane    Posicion(s)   Velocidad(km/h)")
    print(f"  " + "-" * 45)
    for agent in world.get_agents():
        print(
            f"  {agent.agent_id:2d}    {agent.current_lane_id:6s}   "
            f"{agent.position_along_lane_s:7.1f}m     {agent.speed_kmh():6.2f}"
        )


def demo_render_snapshot():
    """Demo: Crea un render snapshot para verificar estructura."""
    print("\n" + "=" * 70)
    print("  FASE 1 PARTE 3: RenderSnapshot")
    print("=" * 70)

    # Entorno simple
    lane = Lane(
        lane_id="lane_0",
        waypoints=[Waypoint(Vector2(0, 0), heading=0), Waypoint(Vector2(500, 0), heading=0)],
    )
    segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(500, 0))
    network = RoadNetwork()
    network.add_segment(segment)

    # World
    world = World(network)

    # Agregar agentes
    for i in range(3):
        agent = CarAgent(
            agent_id=i + 1,
            current_lane_id="lane_0",
            position_along_lane_s=100.0 + i * 100.0,
        )
        world_pos = lane.world_position_at(agent.position_along_lane_s, 0.0)
        agent.set_position_world(world_pos, heading=0)
        world.add_agent(agent)

    # Simula un tick
    world.tick()

    # Crea snapshot
    snapshot = world.build_render_snapshot()

    print(f"\nSnapshot creado:")
    print(f"  Tick: {snapshot.tick_number}")
    print(f"  Tiempo: {snapshot.sim_time_s:.2f}s")
    print(f"  Agentes renderizables: {len(snapshot.agents)}")
    print(f"  Carriles renderizables: {len(snapshot.lanes)}")
    print(f"  Avg Speed: {snapshot.avg_speed_kmh:.2f} km/h")

    print(f"\nAgentes en snapshot:")
    print(f"  ID    Pos(m)    Heading(rad)   Vel(km/h)   Lane")
    print(f"  " + "-" * 50)
    for agent_id, world_pos, heading, speed_kmh, lane_id, s in snapshot.agents:
        print(
            f"  {agent_id:2d}    {world_pos.x:7.1f}    {heading:7.3f}      "
            f"{speed_kmh:6.2f}      {lane_id}"
        )


def demo_yaml_loader():
    """Demo: Carga escenario desde YAML."""
    print("\n" + "=" * 70)
    print("  FASE 1 PARTE 3: YAML Scenario Loader")
    print("=" * 70)

    try:
        import yaml
        scenario = ScenarioLoader.load_scenario(
            '/c/Users/bgaxiola/OneDrive - Capgemini/Projects/Kars/scenarios/single_lane_mvp.yaml'
        )

        print(f"\nEscenario cargado desde YAML:")
        print(f"  Nombre: {scenario.get('simulation', {}).get('name', 'N/A')}")

        # Crea network desde escenario
        network = ScenarioLoader.create_network_from_scenario(scenario)
        print(f"  Carriles en red: {network.num_lanes()}")

        # Crea agentes desde escenario
        agents = ScenarioLoader.create_agents_from_scenario(scenario, network)
        print(f"  Agentes creados: {len(agents)}")

        if agents:
            print(f"\nPrimeros 3 agentes:")
            for agent in agents[:3]:
                print(f"  ID={agent.agent_id}, lane={agent.current_lane_id}, s={agent.position_along_lane_s:.1f}m")

    except ImportError:
        print(f"\nPyYAML no esta instalado. Instalalo con: pip install pyyaml")
    except Exception as e:
        print(f"\nError al cargar YAML: {e}")


def main():
    """Main del simulador."""
    print("\n" + "=" * 70)
    print("  KARS: Simulador de Trafico Basado en Agentes")
    print("=" * 70)

    # Demo 1: Simulacion headless
    demo_headless_simulation()

    # Demo 2: RenderSnapshot
    demo_render_snapshot()

    # Demo 3: YAML Loader
    demo_yaml_loader()

    print("\n" + "=" * 70)
    print("  ESTADO: Fase 1 Completa (Parte 1 + 2 + 3)")
    print("=" * 70)
    print("\nProximo: Integrar Pygame y agregar Fase 2 (multi-lane)")


if __name__ == "__main__":
    main()
