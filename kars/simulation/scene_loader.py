"""SceneLoader: Carga escenas desde archivos JSON."""

import json
import random
from pathlib import Path
from typing import Dict, Any, List

from kars.physics.models import Vector2, Waypoint
from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.scenes import SceneSetup
import kars.config as config


class SceneLoader:
    """Carga configuraciones de escenas desde YAML."""

    @staticmethod
    def load_scene_file(filepath: str) -> Dict[str, Any]:
        """Lee archivo JSON de escena.

        Args:
            filepath: Ruta al archivo .json

        Returns:
            Diccionario con configuración de escena
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def create_network_from_config(road_config: Dict[str, Any]) -> RoadNetwork:
        """Crea RoadNetwork desde configuración.

        Args:
            road_config: Sección 'road' del YAML

        Returns:
            RoadNetwork con las lanes configuradas
        """
        network = RoadNetwork()
        lanes_config = road_config.get('lanes', [])

        for lane_cfg in lanes_config:
            lane_id = lane_cfg['id']
            start = lane_cfg['start']  # [x, y]
            end = lane_cfg['end']      # [x, y]
            width_m = lane_cfg.get('width_m', 2.7)
            speed_limit_kmh = lane_cfg.get('speed_limit_kmh', 50.0)
            zone = lane_cfg.get('zone', 'urban')

            # Crea waypoints
            waypoints = [
                Waypoint(Vector2(start[0], start[1]), heading=0),
                Waypoint(Vector2(end[0], end[1]), heading=0),
            ]

            # Crea lane
            lane = Lane(
                lane_id=lane_id,
                waypoints=waypoints,
                width_m=width_m,
                speed_limit_kmh=speed_limit_kmh,
                zone=zone,
            )

            # Crea segment y lo agrega
            segment = RoadSegment(
                f"seg_{lane_id}",
                [lane],
                Vector2(start[0], start[1]),
                Vector2(end[0], end[1])
            )
            network.add_segment(segment)

        return network

    @staticmethod
    def create_agents_from_config(
        agents_config: List[Dict[str, Any]],
        network: RoadNetwork
    ) -> List[CarAgent]:
        """Crea agentes desde configuración.

        Args:
            agents_config: Lista de configuraciones de agentes
            network: RoadNetwork para obtener lanes

        Returns:
            Lista de CarAgent inicializados
        """
        from kars.physics.models import KinematicState

        agents = []

        for agent_cfg in agents_config:
            agent_id = agent_cfg['id']
            lane_id = agent_cfg['lane']
            position_s = agent_cfg['position_s']
            initial_velocity_ms = agent_cfg.get('initial_velocity_ms', 0.0)
            time_headway_s = agent_cfg.get('time_headway_s', 1.5)
            max_accel_ms2 = agent_cfg.get('max_accel_ms2', 2.0)
            critical_gap_m = agent_cfg.get('critical_gap_m', 5.0)

            # Muestrea multiplicador de velocidad desde distribución Normal
            speed_mult_mean = agent_cfg.get('speed_multiplier_mean', 1.0)
            speed_mult_stddev = agent_cfg.get('speed_multiplier_stddev', 0.2)
            speed_multiplier = random.gauss(speed_mult_mean, speed_mult_stddev)
            # Clamp a rango razonable [0.5, 1.5]
            speed_multiplier = max(0.5, min(1.5, speed_multiplier))

            # Obtiene límite de velocidad de la calle
            lane = network.get_lane(lane_id)
            lane_speed_limit_kmh = lane.speed_limit_kmh

            # Crea agente
            agent = CarAgent(
                agent_id=agent_id,
                current_lane_id=lane_id,
                position_along_lane_s=position_s,
                lateral_offset=0.0,
            )

            # Establece multiplicador de velocidad
            object.__setattr__(agent, 'speed_multiplier', speed_multiplier)

            # Establece gap crítico (parámetro de comportamiento)
            object.__setattr__(agent, 'critical_gap_m', critical_gap_m)

            # Calcula y configura velocidad deseada basada en límite de calle
            desired_speed_ms = (lane_speed_limit_kmh * speed_multiplier) / 3.6
            object.__setattr__(
                agent.idm_behavior,
                'desired_speed',
                desired_speed_ms
            )
            object.__setattr__(
                agent.idm_behavior,
                'time_headway',
                time_headway_s
            )
            object.__setattr__(
                agent.idm_behavior,
                'max_accel',
                max_accel_ms2
            )

            # Posiciona en mundo
            world_pos = lane.world_position_at(position_s, 0.0)

            # Establece estado cinemático con velocidad inicial
            kinematic_state = KinematicState(
                position=world_pos,
                velocity=Vector2(initial_velocity_ms, 0.0),
                acceleration=Vector2(0, 0),
                heading=0.0,
            )
            object.__setattr__(agent, 'kinematic_state', kinematic_state)

            agents.append(agent)

        return agents

    @staticmethod
    def _create_obstacle_avoidance_callback():
        """Callback especial para escena de evasión de obstáculos.

        - Congela carro los primeros 3 segundos
        - Crea obstáculo permanente a 2/3 de la calle en tick 0
        """
        from kars.physics.models import Vector2, KinematicState

        freeze_ticks = 60  # 3 segundos a 40 ticks/s
        obstacle_created = [False]

        def on_tick_obstacle_avoidance(world, tick_number):
            # Congela el carro los primeros 3 segundos
            if tick_number < freeze_ticks:
                for agent in world.agents.values():
                    if not agent.is_disabled:
                        frozen_state = KinematicState(
                            position=agent.kinematic_state.position,
                            velocity=Vector2(0.0, 0.0),
                            acceleration=Vector2(0.0, 0.0),
                            heading=agent.kinematic_state.heading,
                        )
                        object.__setattr__(agent, 'kinematic_state', frozen_state)

            # Crea obstáculo permanente solo una vez en el tick 0
            if tick_number == 0 and not obstacle_created[0]:
                lane = world.network.get_lane("lane_0")
                obstacle_s = lane.length_m() * 0.9
                world.add_permanent_obstacle("lane_0", obstacle_s)
                obstacle_created[0] = True

        return on_tick_obstacle_avoidance

    @staticmethod
    def load_scene(filepath: str) -> SceneSetup:
        """Carga escena completa desde JSON.

        Args:
            filepath: Ruta al archivo .json de escena

        Returns:
            SceneSetup lista para usar
        """
        from kars.physics.models import Vector2, KinematicState

        config = SceneLoader.load_scene_file(filepath)

        name = config.get('name', 'Unknown Scene')
        description = config.get('description', '')

        # Crea network
        road_config = config.get('road', {})
        network = SceneLoader.create_network_from_config(road_config)

        # Crea agentes
        agents_config = config.get('agents', [])
        agents = SceneLoader.create_agents_from_config(agents_config, network)

        # Configuración de world
        world_config = config.get('world', {})

        # Detecta tipo de escena y aplica callback apropiado
        if "obstacle" in name.lower() or "avoidance" in description.lower():
            on_tick_callback = SceneLoader._create_obstacle_avoidance_callback()
        else:
            # Escena default - solo freeze
            freeze_ticks = 60

            def on_tick_freeze_initial(world, tick_number):
                if tick_number < freeze_ticks:
                    for agent in world.agents.values():
                        if not agent.is_disabled:
                            frozen_state = KinematicState(
                                position=agent.kinematic_state.position,
                                velocity=Vector2(0.0, 0.0),
                                acceleration=Vector2(0.0, 0.0),
                                heading=agent.kinematic_state.heading,
                            )
                            object.__setattr__(agent, 'kinematic_state', frozen_state)

            on_tick_callback = on_tick_freeze_initial

        return SceneSetup(
            name=name,
            description=description,
            network=network,
            initial_agents=agents,
            world_config=world_config,
            on_tick=on_tick_callback,
        )

    @staticmethod
    def list_available_scenarios(scenarios_dir: str = "scenarios") -> List[str]:
        """Lista escenarios disponibles.

        Args:
            scenarios_dir: Directorio de escenarios

        Returns:
            Lista de nombres de archivos .json
        """
        scenarios_path = Path(scenarios_dir)
        if not scenarios_path.exists():
            return []

        return sorted([f.stem for f in scenarios_path.glob("*.json")])
