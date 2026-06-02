#!/usr/bin/env python3
"""Entry point visual del simulador KARS con Pygame."""

import sys
sys.path.insert(0, '/c/Users/bgaxiola/OneDrive - Capgemini/Projects/Kars')

from pathlib import Path
from kars.physics.models import Vector2, Waypoint
from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.world import World
from kars.simulation.scene_loader import SceneLoader
from kars.rendering.renderer import Renderer


# Mapa de códigos cortos a nombres de escenarios (soporta números de múltiples dígitos)
SCENARIO_SHORTCUTS = {
    '1': 'test_single_car_acceleration',
    '2': 'test_simple_respawn',
    '3': 'test_collision_chain',
    '4': 'test_multi_lane_basic',
    '5': 'test_multi_lane_speeds',
    '6': 'test_obstacle_avoidance',
    '7': 'test_stop_sign',
    '8': 'test_grid_calibration',
    '9': 'test_120m_street',
    '10': 'test_three_roads_render',
    '11': 'test_width_calibration',
    '12': 'test_lane_change_basic',
    '13': 'test_five_lanes_personality',
}


def show_scenario_menu():
    """Muestra menú de escenarios y retorna el nombre seleccionado."""
    print("\n" + "=" * 70)
    print("  SELECCIONAR ESCENARIO")
    print("=" * 70)

    for code, name in SCENARIO_SHORTCUTS.items():
        display_name = name.replace('test_', '').replace('_', ' ').title()
        print(f"  [{code}] {display_name}")

    print("\nIngresa código (1-13) o nombre completo, o presiona Enter para default (1):")
    user_input = input("> ").strip()

    # Si es vacío, usa default
    if not user_input:
        return SCENARIO_SHORTCUTS['1']

    # Si es un código corto
    if user_input in SCENARIO_SHORTCUTS:
        return SCENARIO_SHORTCUTS[user_input]

    # Si es un nombre completo
    if Path("scenarios") / f"{user_input}.json" in Path("scenarios").glob("*.json"):
        return user_input

    print(f"\n[ERROR] Entrada no reconocida: {user_input}")
    return show_scenario_menu()


def main(scene_name: str = None):
    """Demostración visual interactiva del simulador."""
    print("\n" + "=" * 70)
    print("  KARS: INTERFAZ GRÁFICA INTERACTIVA")
    print("=" * 70)

    # Si no se pasa escena, muestra menú
    if not scene_name:
        scene_name = show_scenario_menu()

    # Carga escena desde JSON
    print(f"\n[Setup] Cargando escena: {scene_name}...")
    scenario_file = Path("scenarios") / f"{scene_name}.json"

    if not scenario_file.exists():
        print(f"[ERROR] Archivo de escena no encontrado: {scenario_file}")
        available = SceneLoader.list_available_scenarios("scenarios")
        print(f"Escenarios disponibles: {available}")
        return

    try:
        scene = SceneLoader.load_scene(str(scenario_file))
    except Exception as e:
        print(f"[ERROR] Error al cargar escena: {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"[Setup] Escena: {scene.name}")
    print(f"[Setup] {scene.description}")

    # Crea World desde escena, pasando el callback de escena
    world = World(scene.network, on_tick_callback=scene.on_tick, **scene.world_config)

    # Agrega agentes iniciales
    for agent in scene.initial_agents:
        world.add_agent(agent)

    print(f"[Setup] Agentes iniciales: {len(scene.initial_agents)}")

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
    renderer = Renderer(scene_filepath=str(scenario_file), camera_config=scene.camera_config)

    print("\n[Running] Simulación en vivo...")
    print("  Tecla R: Resetear escenario")
    frame_count = 0
    try:
        while renderer.running:
            frame_count += 1
            try:
                if not renderer.run_frame(world):
                    if renderer.reset_requested:
                        print("\n[Reset] Recargando escena...")
                        renderer.reset_requested = False
                        renderer.running = True
                        renderer.initial_zoom_done = False

                        # Recarga la escena
                        scene = SceneLoader.load_scene(str(scenario_file))
                        world = World(scene.network, on_tick_callback=scene.on_tick, **scene.world_config)
                        renderer.camera_config = scene.camera_config

                        for agent in scene.initial_agents:
                            world.add_agent(agent)

                        frame_count = 0
                    else:
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
    # Si se pasa argumento, úsalo como nombre de escena
    # Si se pasa un código (1-13), convierte a nombre completo
    scene_name = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        scene_name = SCENARIO_SHORTCUTS.get(arg, arg)
    main(scene_name)
