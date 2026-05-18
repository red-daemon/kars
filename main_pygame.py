#!/usr/bin/env python3
"""Entry point visual del simulador KARS con Pygame."""

import sys
sys.path.insert(0, '/c/Users/bgaxiola/OneDrive - Capgemini/Projects/Kars')

from kars.physics.models import Vector2, Waypoint
from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.world import World
from kars.rendering.renderer import Renderer


def main():
    """Demostración visual interactiva del simulador."""
    print("\n" + "=" * 70)
    print("  KARS: INTERFAZ GRÁFICA INTERACTIVA")
    print("=" * 70)

    # Crea entorno (carril único de 500m)
    print("\n[Setup] Creando entorno...")
    lane = Lane(
        lane_id="lane_0",
        waypoints=[
            Waypoint(Vector2(0, 0), heading=0),
            Waypoint(Vector2(500, 0), heading=0)
        ],
        width_m=2.7,
        speed_limit_kmh=20.0,
    )

    segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(500, 0))
    network = RoadNetwork()
    network.add_segment(segment)

    # Crea World
    world = World(network)

    # Crea 5 agentes iniciales
    print("[Setup] Agregando 5 agentes iniciales...")
    positions = [50, 130, 210, 290, 370]
    for i, initial_s in enumerate(positions, 1):
        agent = CarAgent(
            agent_id=world.get_next_agent_id(),
            current_lane_id="lane_0",
            position_along_lane_s=initial_s,
            lateral_offset=0.0,
            speed_tolerance_kmh=0.0,
        )
        world_pos = lane.world_position_at(agent.position_along_lane_s, 0.0)
        agent.set_position_world(world_pos, heading=0)
        world.add_agent(agent)
        print(f"    Agente {i}: s={initial_s}m")

    print("\n[Controls]")
    print("  Left click:  Spawn agente en la carretera")
    print("  Right click: (Próxima: remove agente)")
    print("  Click on agent: Seguir agente (follow mode)")
    print("  Scroll: Zoom in/out")
    print("  Middle mouse drag: Pan")
    print("  Bottom bar: Ajusta velocidad de simulación")
    print("  Space: Pause/Resume")
    print("  Q/Esc: Salir")

    print("\n[Renderizado] Iniciando Pygame...")
    renderer = Renderer()

    print("\n[Running] Simulación en vivo...")
    try:
        while renderer.running:
            if not renderer.run_frame(world):
                break
    except KeyboardInterrupt:
        print("\n[Interrupted] Simulación detenida por usuario")
    except Exception as e:
        print(f"\n[Error] {e}")
        import traceback
        traceback.print_exc()
    finally:
        renderer.close()

    # Estadísticas finales
    print("\n" + "=" * 70)
    print("  ESTADÍSTICAS FINALES")
    print("=" * 70)
    summary = world.stats_collector.get_summary()
    print(f"\nTiempo total: {summary.get('total_sim_time_s', 0):.1f}s")
    print(f"Velocidad promedio: {summary.get('avg_agent_speed_kmh', 0):.2f} km/h")
    print(f"Velocidad máxima: {summary.get('max_agent_speed_kmh', 0):.2f} km/h")
    print(f"Agentes finales: {world.num_agents()}")

    print("\nProximo: Phase 2 (Multi-lane) y Phase 3 (Semáforos)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
