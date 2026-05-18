"""Cargador de escenarios desde YAML."""

from typing import Dict, List, Any
from pathlib import Path

from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.physics.models import Waypoint, Vector2
import kars.config as config


class ScenarioLoader:
    """Carga escenarios desde archivos YAML."""

    @staticmethod
    def load_scenario(yaml_path: str) -> Dict[str, Any]:
        """Carga escenario desde archivo YAML.

        Args:
            yaml_path: Ruta al archivo YAML

        Returns:
            Dict con configuracion del escenario
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML no esta instalado. Instala con: pip install pyyaml")

        with open(yaml_path, 'r') as f:
            scenario = yaml.safe_load(f)

        return scenario

    @staticmethod
    def create_network_from_scenario(scenario: Dict[str, Any]) -> RoadNetwork:
        """Crea RoadNetwork a partir de configuracion de escenario.

        Args:
            scenario: Dict con configuracion

        Returns:
            RoadNetwork poblado
        """
        network = RoadNetwork()

        # Lee lane del escenario
        lane_config = scenario.get('lane', {})
        lane_id = lane_config.get('lane_id', 'lane_0')

        # Crea waypoints
        waypoints_config = lane_config.get('waypoints', [])
        waypoints = []
        for wp_dict in waypoints_config:
            wp = Waypoint(
                position=Vector2(wp_dict['x'], wp_dict['y']),
                heading=wp_dict.get('heading', 0),
            )
            waypoints.append(wp)

        # Crea lane
        lane = Lane(
            lane_id=lane_id,
            waypoints=waypoints,
            width_m=lane_config.get('width_m', config.LANE_WIDTH_M),
            speed_limit_kmh=lane_config.get('speed_limit_kmh', config.MAX_SPEED_KMH),
            direction=lane_config.get('direction', 'forward'),
        )

        # Crea segmento
        start_pos = Vector2(waypoints[0].position.x, waypoints[0].position.y)
        end_pos = Vector2(waypoints[-1].position.x, waypoints[-1].position.y)

        segment = RoadSegment(
            segment_id='seg_0',
            lanes=[lane],
            start_pos_m=start_pos,
            end_pos_m=end_pos,
        )

        # Agrega a network
        network.add_segment(segment)

        return network

    @staticmethod
    def create_agents_from_scenario(scenario: Dict[str, Any], network: RoadNetwork) -> List[CarAgent]:
        """Crea agentes a partir de configuracion de escenario.

        Args:
            scenario: Dict con configuracion
            network: RoadNetwork para validar carriles

        Returns:
            Lista de CarAgent creados
        """
        agents = []

        agents_config = scenario.get('agents', {})
        initial_count = agents_config.get('initial_count', 0)
        spawn_region = agents_config.get('spawn_region', {})
        min_s = spawn_region.get('min_s', 0)
        max_s = spawn_region.get('max_s', 500)

        idm_defaults = scenario.get('idm_defaults', {})
        speed_tolerance = idm_defaults.get('speed_tolerance_kmh', 2.0)

        # Obtiene el primer carril (MVP: solo 1 carril)
        lane_id = None
        for lane in network.get_all_lanes():
            lane_id = lane.lane_id
            break

        if lane_id is None:
            return agents

        # Crea agentes
        import random
        for i in range(initial_count):
            agent_id = config.AGENT_ID_COUNTER_START + i

            # Posicion aleatoria en spawn region
            s = random.uniform(min_s, max_s)

            agent = CarAgent(
                agent_id=agent_id,
                current_lane_id=lane_id,
                position_along_lane_s=s,
                lateral_offset=0.0,
                speed_tolerance_kmh=random.uniform(-speed_tolerance, speed_tolerance),
            )

            # Sincroniza posicion mundo
            lane = network.get_lane(lane_id)
            world_pos = lane.world_position_at(s, 0.0)
            agent.set_position_world(world_pos, heading=0)

            agents.append(agent)

        return agents
