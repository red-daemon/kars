#!/usr/bin/env python3
"""Test de cambio de carril - solo simulación numérica sin gráficos."""

from kars.simulation.scene_loader import SceneLoader
from kars.simulation.world import World

# Carga escena
setup = SceneLoader.load_scene('scenarios/test_lane_change_basic.json')

# Crea world
world = World(
    network=setup.network,
    allow_spawning=setup.world_config.get('allow_spawning', False),
    desired_num_agents=setup.world_config.get('desired_num_agents', None),
)

# Agrega agentes
for agent in setup.initial_agents:
    world.add_agent(agent)

agent = world.agents[4001]

print("=" * 70)
print(f"INICIO: Agent {agent.agent_id}")
print(f"  Lane: {agent.current_lane_id}")
print(f"  Position S: {agent.position_along_lane_s:.2f}")
print(f"  Lateral offset: {agent.lateral_offset:.2f}")
print(f"  Target lane at S: {agent.target_lane_at_position_s}")
print(f"  Target lane ID: {agent.target_lane_id_on_signal}")
print("=" * 70)
print()

last_lane = agent.current_lane_id
last_target = agent.target_lane_id

for tick in range(500):
    # Debug: imprime posición cada 10 ticks
    if tick % 20 == 0:
        print(f"Tick {tick}: s={agent.position_along_lane_s:.1f}m, offset={agent.lateral_offset:.3f}")

    world.tick()

    # Detecta cambios
    if agent.current_lane_id != last_lane:
        print(f"[CAMBIO DE CARRIL] Tick {tick}: {last_lane} -> {agent.current_lane_id}")
        last_lane = agent.current_lane_id

    if agent.target_lane_id != last_target:
        if agent.target_lane_id is not None:
            print(f"[INICIO TRANSICIÓN] Tick {tick}: target_lane_id = {agent.target_lane_id}")
        else:
            print(f"[FIN TRANSICIÓN] Tick {tick}")
        last_target = agent.target_lane_id

    # Imprime offset cada tick si está en transición
    if agent.target_lane_id is not None:
        print(f"Tick {tick}: s={agent.position_along_lane_s:.1f}m, offset={agent.lateral_offset:.3f}, lane={agent.current_lane_id}")

print()
print("=" * 70)
print(f"FINAL: Agent {agent.agent_id}")
print(f"  Lane: {agent.current_lane_id}")
print(f"  Position S: {agent.position_along_lane_s:.2f}")
print(f"  Lateral offset: {agent.lateral_offset:.2f}")
print("=" * 70)
