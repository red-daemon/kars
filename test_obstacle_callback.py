#!/usr/bin/env python3
"""Test que verifica que el callback de obstáculo se ejecuta correctamente."""

import sys
sys.path.insert(0, 'c:\\Users\\bgaxiola\\OneDrive - Capgemini\\Projects\\Kars')

from pathlib import Path
from kars.simulation.scene_loader import SceneLoader
from kars.simulation.world import World

def test_obstacle_avoidance_callback():
    """Verifica que el callback crea el obstáculo en tick 0."""
    print("Cargando escena test_obstacle_avoidance...")
    scenario_file = Path("scenarios") / "test_obstacle_avoidance.json"

    scene = SceneLoader.load_scene(str(scenario_file))
    print(f"Escena: {scene.name}")

    # Crea world con callback
    world = World(scene.network, on_tick_callback=scene.on_tick, **scene.world_config)

    # Agrega agentes iniciales
    for agent in scene.initial_agents:
        world.add_agent(agent)

    print(f"Agentes iniciales: {len(world.agents)}")

    # Ejecuta tick 0
    print("\nEjecutando tick 0...")
    world.tick()

    # Verifica que se creó obstáculo
    print(f"Agentes después de tick 0: {len(world.agents)}")

    obstacles = []
    for agent_id, agent in world.agents.items():
        if agent.is_disabled and agent.disable_ticks_remaining == -1:
            obstacles.append((agent_id, agent.position_along_lane_s))
            print(f"  Obstáculo encontrado: agent_id={agent_id}, s={agent.position_along_lane_s:.1f}m")

    if obstacles:
        print(f"\n[OK] Callback funcionó: {len(obstacles)} obstáculo(s) creado(s)")

        # Verifica que aparece en snapshot
        snapshot = world.build_render_snapshot()
        print(f"Obstáculos en snapshot: {len(snapshot.obstacles)}")
        for world_pos, lane_id, s in snapshot.obstacles:
            print(f"  En pantalla: lane={lane_id}, s={s:.1f}m, pos={world_pos}")

        return True
    else:
        print(f"\n[ERROR] Callback NO funcionó: no se encontraron obstáculos")
        return False

if __name__ == "__main__":
    success = test_obstacle_avoidance_callback()
    sys.exit(0 if success else 1)
