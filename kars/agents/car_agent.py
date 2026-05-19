"""Agente Car: vehículo controlado por comportamiento IDM."""

from dataclasses import dataclass, field
from typing import Optional
import uuid

from kars.physics.models import Vector2, KinematicState, PhysicsBody
from kars.agents.behaviors.idm import IDMBehavior
from kars.agents.perception import PerceptionData
import kars.config as config


@dataclass
class CarAgent:
    """Un carro individual en la simulación.

    Mantiene representación dual:
    - Física: KinematicState en (x, y) metros
    - Carril: (lane_id, position_along_lane_s, lateral_offset)
    """

    # Identificación
    agent_id: int = field(default_factory=lambda: config.AGENT_ID_COUNTER_START + hash(uuid.uuid4()) % 1000000)

    # Propiedades físicas
    physics_body: PhysicsBody = field(default_factory=lambda: PhysicsBody(
        length_m=config.CAR_LENGTH_M,
        width_m=config.CAR_WIDTH_M,
    ))

    # Estado cinemático en mundo (x, y)
    kinematic_state: KinematicState = field(default_factory=lambda: KinematicState(
        position=Vector2(0, 0),
        velocity=Vector2(0, 0),
        acceleration=Vector2(0, 0),
        heading=0,
    ))

    # Posición en carril (representación lógica)
    current_lane_id: str = ""
    position_along_lane_s: float = 0.0
    lateral_offset: float = 0.0

    # Comportamiento
    idm_behavior: IDMBehavior = field(default_factory=lambda: IDMBehavior(
        desired_speed_ms=config.IDM_DESIRED_SPEED_MS,
        time_headway_s=config.IDM_TIME_HEADWAY_S,
        min_gap_m=config.IDM_MIN_GAP_M,
        max_accel_ms2=config.MAX_ACCEL_MS2,
        comfortable_decel_ms2=config.COMFORTABLE_DECEL_MS2,
    ))

    # Tolerancia individual: +/- variación respecto a velocidad deseada
    speed_tolerance_kmh: float = 0.0

    # Estado de colisión
    is_disabled: bool = False          # True si está en estado de colisión
    disable_ticks_remaining: int = 0   # Countdown para remoción
    shoulder_offset: float = 0.0       # Offset actual hacia la orilla (m)

    def get_desired_speed_ms(self) -> float:
        """Velocidad deseada del agente incluyendo tolerancia.

        La tolerancia individual permite que cada agente tenga una
        velocidad deseada ligeramente diferente, generando heterogeneidad.
        """
        base_speed = self.idm_behavior.desired_speed

        # Convierte tolerancia de km/h a m/s
        tolerance_ms = self.speed_tolerance_kmh / 3.6

        return base_speed + tolerance_ms

    def set_position_world(self, pos: Vector2, heading: float = 0.0):
        """Actualiza posición en coordenadas mundo (x, y).

        Args:
            pos: Vector2 en metros
            heading: Rumbo en radianes
        """
        new_state = KinematicState(
            position=pos,
            velocity=self.kinematic_state.velocity,
            acceleration=self.kinematic_state.acceleration,
            heading=heading,
        )
        object.__setattr__(self, 'kinematic_state', new_state)

    def set_position_lane(self, lane_id: str, s: float, lateral_offset: float = 0.0):
        """Actualiza posición en representación de carril.

        Args:
            lane_id: ID del carril
            s: Distancia a lo largo del carril (metros)
            lateral_offset: Offset perpendicular al carril (metros)
        """
        object.__setattr__(self, 'current_lane_id', lane_id)
        object.__setattr__(self, 'position_along_lane_s', s)
        object.__setattr__(self, 'lateral_offset', lateral_offset)

    def set_velocity_world(self, velocity: Vector2):
        """Establece velocidad en coordenadas mundo (x, y).

        Args:
            velocity: Vector2 en m/s
        """
        new_state = KinematicState(
            position=self.kinematic_state.position,
            velocity=velocity,
            acceleration=self.kinematic_state.acceleration,
            heading=self.kinematic_state.heading,
        )
        object.__setattr__(self, 'kinematic_state', new_state)

    def decide(self, perception: PerceptionData) -> float:
        """Calcula aceleración deseada basada en percepción.

        Usa el modelo IDM de seguimiento vehicular.

        Args:
            perception: PerceptionData del mundo

        Returns:
            Aceleración deseada en m/s²
        """
        # Velocidad deseada incluyendo tolerancia individual
        desired_speed_ms = self.get_desired_speed_ms()

        # Actualiza IDM con velocidad deseada del agente
        # (puede ser diferente a la del carril por tolerancia)
        idm_with_tolerance = IDMBehavior(
            desired_speed_ms=desired_speed_ms,
            time_headway_s=self.idm_behavior.time_headway,
            min_gap_m=self.idm_behavior.min_gap,
            max_accel_ms2=self.idm_behavior.max_accel,
            comfortable_decel_ms2=self.idm_behavior.comfortable_decel,
            delta=self.idm_behavior.delta,
        )

        # Calcula aceleración usando IDM
        desired_accel = idm_with_tolerance.compute_acceleration(
            current_speed_ms=self.kinematic_state.speed_ms(),
            leader_distance_m=perception.leader_distance_m,
            leader_speed_ms=perception.leader_speed_ms,
        )

        return desired_accel

    def speed_kmh(self) -> float:
        """Velocidad actual en km/h."""
        return self.kinematic_state.speed_kmh()

    def __repr__(self) -> str:
        """Representación de debug."""
        return (
            f"CarAgent(id={self.agent_id}, "
            f"lane={self.current_lane_id}, "
            f"s={self.position_along_lane_s:.1f}m, "
            f"speed={self.speed_kmh():.1f}km/h)"
        )
