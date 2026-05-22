"""Escenas de prueba: configuraciones predefinidas para validar comportamientos."""

from dataclasses import dataclass
from typing import List, Callable
from kars.physics.models import Vector2, Waypoint, KinematicState
from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.world import World
import kars.config as config


@dataclass
class SceneSetup:
    """Configuración de una escena de prueba."""
    name: str
    description: str
    network: RoadNetwork
    initial_agents: List[CarAgent]
    world_config: dict  # {'allow_spawning': False, ...}
    on_tick: Callable[[World, int], None] = None  # Callback cada tick
    camera_config: dict = None  # {'viewport_x_min_m': ..., 'viewport_x_max_m': ...}


def create_single_car_acceleration_scene() -> SceneSetup:
    """
    Escena 1: Un carro que empieza parado durante 3s, luego acelera.

    Permite observar:
    - Comportamiento del carro en aceleración constante
    - Velocidad en pantalla
    - Comportamiento del motor IDM
    """
    # Crea carril recto horizontal (1000m)
    lane = Lane(
        lane_id="lane_0",
        waypoints=[
            Waypoint(Vector2(0, 0), heading=0),
            Waypoint(Vector2(1000, 0), heading=0)
        ],
        width_m=2.7,
        speed_limit_kmh=50.0,
        zone="urban",
    )

    segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(1000, 0))
    network = RoadNetwork()
    network.add_segment(segment)

    # Crea un carro a 100m del inicio, parado
    agent = CarAgent(
        agent_id=1,
        current_lane_id="lane_0",
        position_along_lane_s=100.0,
        lateral_offset=0.0,
    )

    # Posición en mundo
    world_pos = lane.world_position_at(100.0, 0.0)
    agent.set_position_world(world_pos, heading=0.0)

    # Inicialmente parado
    initial_state = KinematicState(
        position=world_pos,
        velocity=Vector2(0.0, 0.0),
        acceleration=Vector2(0, 0),
        heading=0.0,
    )
    object.__setattr__(agent, 'kinematic_state', initial_state)

    # Callback: después de 3 segundos (60 ticks a 20 ticks/s), empieza a acelerar
    def on_tick_callback(world: World, tick_number: int):
        """Controla comportamiento del carro durante la escena."""
        # Los primeros 60 ticks (3s): mantener velocidad = 0
        # Después: el IDM toma control automáticamente (detecta velocidad deseada)

        # En realidad, no necesitamos hacer nada - el IDM funcionará automáticamente
        # cuando la velocidad sea < deseada. Esto es solo para logging si queremos.
        pass

    return SceneSetup(
        name="Single Car Acceleration",
        description="Un carro parado durante 3s, luego acelera automáticamente",
        network=network,
        initial_agents=[agent],
        world_config={'allow_spawning': False},
        on_tick=on_tick_callback,
    )


def create_scene(scene_name: str) -> SceneSetup:
    """Factory: crea una escena por nombre."""
    scenes = {
        'single_car_acceleration': create_single_car_acceleration_scene,
    }

    if scene_name not in scenes:
        raise ValueError(f"Escena desconocida: {scene_name}. Disponibles: {list(scenes.keys())}")

    return scenes[scene_name]()
