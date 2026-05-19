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

    # Crea entorno (carril único de 1000m)
    print("\n[Setup] Creando entorno...")
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

    # Crea World
    world = World(network)

    # Agrega obstáculo fijo a 2/3 del carril (simula accidente o señal de alto)
    obstacle_s = 1000 * (2.0 / 3.0)
    obstacle_id = world.add_permanent_obstacle("lane_0", obstacle_s)
    print(f"\n[Setup] Obstáculo fijo agregado a s={obstacle_s:.0f}m (2/3 del carril)")
    print(f"[Setup] Tráfico se genera automáticamente según zona 'urban'")

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
    frame_count = 0
    try:
        while renderer.running:
            frame_count += 1
            try:
                if not renderer.run_frame(world):
                    break
            except Exception as frame_error:
                print(f"\n[Frame Error] Frame #{frame_count}: {frame_error}")
                import traceback
                traceback.print_exc()
                break
    except KeyboardInterrupt:
        print("\n[Interrupted] Simulación detenida por usuario")
    except Exception as e:
        print(f"\n[Error] {e}")
        import traceback
        traceback.print_exc()
    finally:
        renderer.close()
        print(f"\n[Stats] Total frames rendered: {frame_count}")

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
