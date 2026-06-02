"""SceneLoader: Carga escenas desde archivos JSON."""

import json
import random
from pathlib import Path
from typing import Dict, Any, List

from kars.physics.models import Vector2, Waypoint
from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road import Road
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

        Soporta dos formatos:

        1. NUEVO (recomendado):
            "roads": [
              {
                "id": "road_0",
                "name": "Main Street",
                "segments": [
                  {
                    "id": "segment_0",
                    "start": [x, y],
                    "end": [x, y],
                    "lanes": [
                      {"id": "lane_0", "width_m": 4.0, ...},
                      {"id": "lane_1", "width_m": 4.0, ...}
                    ]
                  }
                ]
              }
            ]

        2. ANTIGUO (compatible):
            "lanes": [
              {"id": "lane_0", "start": [x, y], "end": [x, y], ...}
            ]

        Args:
            road_config: Sección 'road' del JSON

        Returns:
            RoadNetwork con las roads/segments/lanes configuradas
        """
        network = RoadNetwork()

        # Intenta formato nuevo (roads)
        roads_config = road_config.get('roads', [])
        if roads_config:
            for road_cfg in roads_config:
                road_id = road_cfg['id']
                road_name = road_cfg.get('name', road_id)
                speed_limit_kmh = road_cfg.get('speed_limit_kmh', 50.0)
                segments_config = road_cfg.get('segments', [])

                segments_list = []

                for seg_cfg in segments_config:
                    seg_id = seg_cfg['id']
                    start = seg_cfg['start']  # [x, y]
                    end = seg_cfg['end']      # [x, y]
                    lanes_config = seg_cfg.get('lanes', [])

                    lanes_list = []
                    num_lanes = len(lanes_config)

                    for lane_idx, lane_cfg in enumerate(lanes_config):
                        lane_id = lane_cfg['id']
                        width_m = lane_cfg.get('width_m', 4.0)
                        zone = lane_cfg.get('zone', 'urban')
                        lane_type = lane_cfg.get('lane_type', 'normal')
                        direction = lane_cfg.get('direction', 'forward')

                        # Waypoints: todas las lanes comparten la geometría del segment
                        waypoints = [
                            Waypoint(Vector2(start[0], start[1]), heading=0),
                            Waypoint(Vector2(end[0], end[1]), heading=0),
                        ]

                        # lane_index se calcula automáticamente desde posición en lista
                        lane = Lane(
                            lane_id=lane_id,
                            waypoints=waypoints,
                            width_m=width_m,
                            speed_limit_kmh=speed_limit_kmh,
                            zone=zone,
                            lane_index=lane_idx,  # Auto-calculado
                            total_lanes=num_lanes,  # Parámetro para distribución simétrica
                            lane_type=lane_type,
                            direction=direction,
                        )
                        lanes_list.append(lane)

                    # Crea segment con todas las lanes
                    segment = RoadSegment(
                        seg_id,
                        lanes_list,
                        Vector2(start[0], start[1]),
                        Vector2(end[0], end[1])
                    )
                    segments_list.append(segment)

                # Crea road con todos los segments
                road = Road(
                    road_id=road_id,
                    name=road_name,
                    segments=segments_list,
                    speed_limit_kmh=speed_limit_kmh,
                )
                network.add_road(road)
            return network

        # Fallback: formato antiguo (lanes plano)
        lanes_config = road_config.get('lanes', [])
        for lane_cfg in lanes_config:
            lane_id = lane_cfg['id']
            start = lane_cfg['start']  # [x, y]
            end = lane_cfg['end']      # [x, y]
            width_m = lane_cfg.get('width_m', 2.7)
            speed_limit_kmh = lane_cfg.get('speed_limit_kmh', 50.0)
            zone = lane_cfg.get('zone', 'urban')
            lane_type = lane_cfg.get('lane_type', 'normal')
            direction = lane_cfg.get('direction', 'forward')

            waypoints = [
                Waypoint(Vector2(start[0], start[1]), heading=0),
                Waypoint(Vector2(end[0], end[1]), heading=0),
            ]

            lane = Lane(
                lane_id=lane_id,
                waypoints=waypoints,
                width_m=width_m,
                speed_limit_kmh=speed_limit_kmh,
                zone=zone,
                lane_index=0,
                total_lanes=1,  # Single-lane segment
                lane_type=lane_type,
                direction=direction,
            )

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
            stop_sign_wait_mean_s = agent_cfg.get('stop_sign_wait_mean_s', 1.0)
            stop_sign_wait_stddev_s = agent_cfg.get('stop_sign_wait_stddev_s', 0.3)
            stop_sign_buffer_m = agent_cfg.get('stop_sign_buffer_m', 0.5)
            speed_oscillation_range_kmh = agent_cfg.get('speed_oscillation_range_kmh', 0.0)
            target_lane_at_position_s = agent_cfg.get('target_lane_at_position_s', None)
            target_lane_id_on_signal = agent_cfg.get('target_lane_id_on_signal', None)

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

            # Guarda parámetros para recalcular en respawn (distribución normal)
            object.__setattr__(agent, '_speed_multiplier_mean', speed_mult_mean)
            object.__setattr__(agent, '_speed_multiplier_stddev', speed_mult_stddev)
            object.__setattr__(agent, '_lane_speed_limit_kmh', lane_speed_limit_kmh)

            # Establece gap crítico (parámetro de comportamiento)
            object.__setattr__(agent, 'critical_gap_m', critical_gap_m)

            # Establece parámetros de stop sign
            object.__setattr__(agent, 'stop_sign_wait_mean_s', stop_sign_wait_mean_s)
            object.__setattr__(agent, 'stop_sign_wait_stddev_s', stop_sign_wait_stddev_s)
            object.__setattr__(agent, 'stop_sign_buffer_m', stop_sign_buffer_m)

            # Calcula y configura velocidad deseada basada en límite de calle
            desired_speed_ms = (lane_speed_limit_kmh * speed_multiplier) / 3.6
            desired_speed_mean_ms = desired_speed_ms
            speed_oscillation_range_ms = (speed_oscillation_range_kmh / 3.6) if speed_oscillation_range_kmh > 0 else 0.0

            object.__setattr__(agent, 'desired_speed_mean_ms', desired_speed_mean_ms)
            object.__setattr__(agent, 'speed_oscillation_range_ms', speed_oscillation_range_ms)

            # Establece parámetros de cambio de carril
            if target_lane_at_position_s is not None:
                object.__setattr__(agent, 'target_lane_at_position_s', target_lane_at_position_s)
            if target_lane_id_on_signal is not None:
                object.__setattr__(agent, 'target_lane_id_on_signal', target_lane_id_on_signal)

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
    def _create_width_calibration_callback():
        """Callback para escena de calibracion de ancho.

        - Agrega obstaculos cada 10m para verificar el ancho visualmente
        """
        obstacles_created = [False]

        def on_tick_width_calibration(world, tick_number):
            if tick_number == 0 and not obstacles_created[0]:
                try:
                    lane = world.network.get_lane("lane_0")
                    lane_length = lane.length_m()

                    # Agrega un obstáculo al final del carril (para detener carros estáticos)
                    world.add_permanent_obstacle("lane_0", lane_length)

                    obstacles_created[0] = True
                    print(f"[SCENE] Width calibration: added single obstacle at end (s={lane_length}m)")
                except Exception as e:
                    print(f"Error creating width calibration obstacles: {e}")

        return on_tick_width_calibration

    @staticmethod
    def _create_obstacle_avoidance_callback():
        """Callback especial para escena de evasión de obstáculos.

        - Crea obstáculo permanente a 90% de la calle en tick 0
        """
        obstacle_created = [False]

        def on_tick_obstacle_avoidance(world, tick_number):
            # Crea obstáculo permanente solo una vez en el tick 0
            if tick_number == 0 and not obstacle_created[0]:
                lane = world.network.get_lane("lane_0")
                obstacle_s = lane.length_m() * 0.9
                world.add_permanent_obstacle("lane_0", obstacle_s)
                obstacle_created[0] = True

        return on_tick_obstacle_avoidance

    @staticmethod
    def _create_multi_lane_callback():
        """Callback especial para escena multi-carril.

        - Crea obstáculos permanentes al 90% en cada carril
        """
        obstacles_created = [False]

        def on_tick_multi_lane(world, tick_number):
            # Crea obstáculos en todos los carriles en el tick 0
            if tick_number == 0 and not obstacles_created[0]:
                try:
                    for lane_id in ["lane_0", "lane_1", "lane_2"]:
                        lane = world.network.get_lane(lane_id)
                        obstacle_s = lane.length_m() * 0.9
                        world.add_permanent_obstacle(lane_id, obstacle_s)
                    obstacles_created[0] = True
                except Exception:
                    pass

        return on_tick_multi_lane

    @staticmethod
    def _create_stop_sign_callback():
        """Callback para escena de señal de alto.

        - Agrega una señal de alto a 3/4 de la calle
        """
        from kars.environment.lane import StopSign

        stop_sign_added = [False]

        def on_tick_stop_sign(world, tick_number):
            if tick_number == 0 and not stop_sign_added[0]:
                try:
                    lane = world.network.get_lane("lane_0")
                    # Posición: 3/4 de la longitud del carril
                    stop_sign_position_s = lane.length_m() * 0.75
                    stop_sign = StopSign(position_s=stop_sign_position_s, is_active=True)
                    lane.stop_signs.append(stop_sign)
                    stop_sign_added[0] = True
                    print(f"[SCENE] Stop sign added at s={stop_sign_position_s:.1f}m (lane length={lane.length_m():.1f}m)")
                except Exception as e:
                    print(f"Error adding stop sign: {e}")

            # Debug: print status cada 50 ticks
            if tick_number % 50 == 0:
                for agent in world.agents.values():
                    if agent.agent_id == 1001:
                        print(f"[TICK {tick_number}] Agent {agent.agent_id}: s={agent.position_along_lane_s:.1f}m, "
                              f"v={agent.kinematic_state.speed_ms():.2f}m/s, "
                              f"wait_remaining={agent.stop_sign_wait_time_remaining_s:.2f}s")

        return on_tick_stop_sign

    @staticmethod
    def _create_collision_chain_callback():
        """Callback para escena de cadena de colisiones.

        - Carro A empieza en s=50m a 60 km/h (16.67 m/s)
        - Carro C en s=0m intenta frenar a tiempo
        - En tick 120 (3s), aparece Carro B parado en s=120m
        - Carro A no tiene tiempo de frenar y colisiona
        """
        from kars.physics.models import Vector2, KinematicState

        carro_b_created = [False]

        def on_tick_collision_chain(world, tick_number):
            # Crea Carro B en tick 120 (3 segundos = 120 * 25ms = 3000ms)
            if tick_number == 120 and not carro_b_created[0]:
                try:
                    # Obtiene lane
                    lane = world.network.get_lane("lane_0")

                    # Crea Carro B parado en s=120m
                    carro_b = CarAgent(
                        agent_id=world.get_next_agent_id(),
                        current_lane_id="lane_0",
                        position_along_lane_s=120.0,
                        lateral_offset=0.0,
                    )

                    # Posiciona en mundo
                    world_pos = lane.world_position_at(120.0, 0.0)
                    heading = lane.heading_at(120.0)

                    # Estado cinemático: parado
                    kinematic_state = KinematicState(
                        position=world_pos,
                        velocity=Vector2(0.0, 0.0),
                        acceleration=Vector2(0, 0),
                        heading=heading,
                    )
                    object.__setattr__(carro_b, 'kinematic_state', kinematic_state)

                    # Agrega al mundo
                    world.add_agent(carro_b)
                    carro_b_created[0] = True
                except Exception as e:
                    print(f"Error creando Carro B: {e}")

        return on_tick_collision_chain

    @staticmethod
    def _calculate_network_bounds(network: RoadNetwork) -> tuple:
        """Calcula el bounding box (min_x, min_y, max_x, max_y) de toda la red de carreteras.

        Incluye los márgenes de las calles pero sin margen adicional de padding.

        Params:
            network: RoadNetwork con todos los segmentos

        Returns:
            (min_x, min_y, max_x, max_y) en metros mundo
        """
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for road in network.roads.values():
            for segment in road.segments:
                # Calcula ancho total del segmento (todos los carriles + márgenes)
                total_width_m = sum(lane.width_m for lane in segment.lanes)
                half_width = total_width_m / 2.0
                half_width_with_margins = half_width + config.ROAD_MARGIN_WIDTH_M

                for lane in segment.lanes:
                    for waypoint in lane.waypoints:
                        wx = waypoint.position.x
                        wy = waypoint.position.y

                        # Calcula normal perpendicular
                        # (para offset lateral, aunque sea simple lo hacemos bien)
                        min_x = min(min_x, wx)
                        max_x = max(max_x, wx)

                        # En Y, incluye margen de la calle
                        min_y = min(min_y, wy - half_width_with_margins)
                        max_y = max(max_y, wy + half_width_with_margins)

        return (min_x, min_y, max_x, max_y)

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

        # Establece número deseado de agentes (default = número inicial)
        if 'desired_num_agents' not in world_config:
            world_config['desired_num_agents'] = len(agents)

        # Configuración de cámara (convierte nombres del JSON a names esperados por renderer)
        camera_config_raw = config.get('camera', {})
        camera_config = {}

        # Calcula bounding box de la red automáticamente si no se especifica viewport
        has_explicit_viewport = (
            'viewport_x_min' in camera_config_raw or
            'viewport_x_min_m' in camera_config_raw or
            'viewport_x_max' in camera_config_raw or
            'viewport_x_max_m' in camera_config_raw or
            'visible_length_m' in camera_config_raw
        )

        if not has_explicit_viewport:
            # Calcula automáticamente desde los bounds de la red
            min_x, min_y, max_x, max_y = SceneLoader._calculate_network_bounds(network)
            # Usa los bounds exactos sin margen adicional
            camera_config['viewport_x_min_m'] = min_x
            camera_config['viewport_x_max_m'] = max_x
            camera_config['viewport_y_min_m'] = min_y
            camera_config['viewport_y_max_m'] = max_y
        else:
            # Nueva estructura: visible_length_m
            if 'visible_length_m' in camera_config_raw:
                camera_config['visible_length_m'] = camera_config_raw['visible_length_m']

            # Formato antiguo: viewport_x_min/max (compatibilidad)
            if 'viewport_x_min' in camera_config_raw:
                camera_config['viewport_x_min_m'] = camera_config_raw['viewport_x_min']
            if 'viewport_x_min_m' in camera_config_raw:
                camera_config['viewport_x_min_m'] = camera_config_raw['viewport_x_min_m']
            if 'viewport_x_max' in camera_config_raw:
                camera_config['viewport_x_max_m'] = camera_config_raw['viewport_x_max']
            if 'viewport_x_max_m' in camera_config_raw:
                camera_config['viewport_x_max_m'] = camera_config_raw['viewport_x_max_m']
            if 'viewport_y_min' in camera_config_raw:
                camera_config['viewport_y_min_m'] = camera_config_raw['viewport_y_min']
            if 'viewport_y_min_m' in camera_config_raw:
                camera_config['viewport_y_min_m'] = camera_config_raw['viewport_y_min_m']
            if 'viewport_y_max' in camera_config_raw:
                camera_config['viewport_y_max_m'] = camera_config_raw['viewport_y_max']
            if 'viewport_y_max_m' in camera_config_raw:
                camera_config['viewport_y_max_m'] = camera_config_raw['viewport_y_max_m']

        # Campos de rendering opcionales (grillas, etc.)
        if 'show_grid' in camera_config_raw:
            camera_config['show_grid'] = camera_config_raw['show_grid']

        # Si se especifica viewport_x_max explícitamente, úsalo como límite de remover
        if 'viewport_x_max_m' in camera_config:
            world_config['removal_x_max'] = camera_config['viewport_x_max_m']
        elif 'viewport_x_max' in camera_config:
            world_config['removal_x_max'] = camera_config['viewport_x_max']

        # Detecta tipo de escena y aplica callback apropiado
        if "width calibration" in name.lower():
            on_tick_callback = SceneLoader._create_width_calibration_callback()
        elif "stop sign" in name.lower():
            on_tick_callback = SceneLoader._create_stop_sign_callback()
        elif "collision chain" in name.lower():
            on_tick_callback = SceneLoader._create_collision_chain_callback()
        elif "obstacle" in name.lower() or "avoidance" in description.lower():
            on_tick_callback = SceneLoader._create_obstacle_avoidance_callback()
        else:
            # Escena default - sin congelamiento
            def on_tick_default(world, tick_number):
                pass

            on_tick_callback = on_tick_default

        return SceneSetup(
            name=name,
            description=description,
            network=network,
            initial_agents=agents,
            world_config=world_config,
            on_tick=on_tick_callback,
            camera_config=camera_config,
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
