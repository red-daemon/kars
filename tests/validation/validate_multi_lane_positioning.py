#!/usr/bin/env python3
"""Validar posicionamiento multi-carril: agentes en carriles paralelos."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pathlib import Path
from kars.simulation.scene_loader import SceneLoader
from kars.simulation.world import World
from kars.physics.models import Vector2


def validate_multi_lane_positioning():
    """Carga escena multi-carril y valida posicionamiento de agentes."""

    print("\n" + "="*70)
    print("VALIDACION: Posicionamiento Multi-Carril")
    print("="*70)

    # Carga escena
    scenario_file = Path("scenarios/test_multi_lane_basic.json")
    print(f"\nCargando: {scenario_file}")

    scene = SceneLoader.load_scene(str(scenario_file))
    print(f"Escena: {scene.name}")
    print(f"Descripcion: {scene.description}")

    # Crea mundo
    world = World(scene.network, on_tick_callback=scene.on_tick, **scene.world_config)

    # Agrega agentes
    for agent in scene.initial_agents:
        world.add_agent(agent)

    print(f"\nAgentes iniciales: {len(scene.initial_agents)}")

    # Obtiene las lanes
    lanes = {}
    for segment_id, segment in scene.network.segments.items():
        for lane in segment.lanes:
            lanes[lane.lane_id] = lane
            print(f"  Lane: {lane.lane_id} (index={lane.lane_index}, width={lane.width_m}m)")

    # Valida posicionamiento inicial
    print("\n" + "-"*70)
    print("POSICIONAMIENTO INICIAL")
    print("-"*70)

    agent_positions = {}
    for agent_id, agent in world.agents.items():
        lane = lanes[agent.current_lane_id]
        world_pos = agent.kinematic_state.position

        # Posicion esperada
        expected_pos = lane.world_position_at(agent.position_along_lane_s, 0.0)

        agent_positions[agent_id] = {
            'lane_id': agent.current_lane_id,
            'lane_index': lane.lane_index,
            'world_pos': world_pos,
            'expected_pos': expected_pos,
            'pos_error': world_pos.distance_to(expected_pos)
        }

        print(f"\nAgente {agent_id}:")
        print(f"  Lane: {agent.current_lane_id} (index={lane.lane_index})")
        print(f"  Position s: {agent.position_along_lane_s:.1f}m")
        print(f"  World pos: ({world_pos.x:.1f}, {world_pos.y:.1f})")
        print(f"  Expected:  ({expected_pos.x:.1f}, {expected_pos.y:.1f})")
        print(f"  Error: {agent_positions[agent_id]['pos_error']:.4f}m")

    # Valida separacion entre carriles
    print("\n" + "-"*70)
    print("SEPARACION ENTRE CARRILES")
    print("-"*70)

    agents_by_lane = {}
    for agent_id, info in agent_positions.items():
        lane_id = info['lane_id']
        if lane_id not in agents_by_lane:
            agents_by_lane[lane_id] = []
        agents_by_lane[lane_id].append((agent_id, info))

    expected_lane_separation = 4.0  # width_m

    for lane_id in sorted(agents_by_lane.keys()):
        agents = agents_by_lane[lane_id]
        if agents:
            agent_id, info = agents[0]
            print(f"\n{lane_id}: (1 agente)")
            print(f"  Y coordinate: {info['world_pos'].y:.2f}")

    # Valida que agentes esten separados por ancho del carril
    all_agents = list(agent_positions.items())
    if len(all_agents) >= 2:
        agent1_id, info1 = all_agents[0]
        agent2_id, info2 = all_agents[1]

        y_diff = abs(info2['world_pos'].y - info1['world_pos'].y)
        print(f"\nSeparacion Y (agente {agent1_id} vs {agent2_id}): {y_diff:.2f}m")
        print(f"Esperado: {expected_lane_separation:.2f}m")

        if abs(y_diff - expected_lane_separation) < 0.1:
            print("[OK] Separacion correcta")
        else:
            print("[WARN] Separacion no es la esperada")

    # Simula algunos ticks para validar que agentes se mueven correctamente
    print("\n" + "-"*70)
    print("SIMULACION: 5 TICKS")
    print("-"*70)

    for tick in range(5):
        world.tick()

    print("\nPosiciones despues de 5 ticks:")
    for agent_id, agent in world.agents.items():
        lane = lanes[agent.current_lane_id]
        world_pos = agent.kinematic_state.position
        expected_pos = lane.world_position_at(agent.position_along_lane_s, 0.0)
        error = world_pos.distance_to(expected_pos)

        print(f"\nAgente {agent_id}:")
        print(f"  Lane: {agent.current_lane_id}")
        print(f"  Position s: {agent.position_along_lane_s:.1f}m")
        print(f"  World pos: ({world_pos.x:.1f}, {world_pos.y:.1f})")
        print(f"  Expected:  ({expected_pos.x:.1f}, {expected_pos.y:.1f})")
        print(f"  Error: {error:.4f}m")
        print(f"  Velocity: {agent.kinematic_state.speed_ms():.2f} m/s")

        if error > 0.1:
            print(f"  [ERROR] Posicion: {error:.4f}m")
        else:
            print(f"  [OK] Posicion correcta")

    print("\n" + "="*70)
    print("VALIDACION COMPLETADA")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        validate_multi_lane_positioning()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
