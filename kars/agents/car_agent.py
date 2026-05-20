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

    # Multiplicador de velocidad: personalidad del conductor respecto al límite de la calle
    # Muestreado de distribución Normal. E.g., 0.8 = 80% del límite, 1.2 = 120% del límite
    speed_multiplier: float = 1.0

    # Gap crítico: distancia umbral en la que comienza frenado máximo (metros)
    # Conductores precavidos: 10m (frenan temprano)
    # Conductores normales: 5m
    # Conductores agresivos: 2m (casi chocan antes de frenar)
    critical_gap_m: float = 5.0

    # Estado de colisión
    is_disabled: bool = False          # True si está en estado de colisión
    disable_ticks_remaining: int = 0   # Countdown para remoción
    shoulder_offset: float = 0.0       # Offset actual hacia la orilla (m)

    def set_desired_speed_from_lane(self, lane_speed_limit_kmh: float) -> None:
        """Establece velocidad deseada basada en límite de la calle y multiplicador.

        Args:
            lane_speed_limit_kmh: Límite de velocidad de la calle en km/h
        """
        desired_speed_ms = (lane_speed_limit_kmh * self.speed_multiplier) / 3.6
        object.__setattr__(self.idm_behavior, 'desired_speed', desired_speed_ms)

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

        Usa el modelo IDM de seguimiento vehicular, pero con frenado especial
        cuando el obstáculo está completamente detenido y cerca.

        Frenado inteligente: mantiene velocidad hasta distancia umbral,
        luego frena suavemente para detenerse exactamente en min_gap.

        Args:
            perception: PerceptionData del mundo

        Returns:
            Aceleración deseada en m/s²
        """
        current_speed = self.kinematic_state.speed_ms()

        # Distancia umbral para comenzar frenado suave (metros)
        # Mantiene velocidad hasta esta distancia, luego frena suavemente
        BRAKING_DISTANCE_M = 30.0

        # Detección de frenado especial: obstáculo parado y cerca
        if (perception.leader_speed_ms == 0.0 and
            perception.leader_distance_m < BRAKING_DISTANCE_M and
            current_speed > 0.05):  # Solo si estamos en movimiento

            # FASE 3: Frenado máximo si está demasiado cerca (crítico)
            if perception.leader_distance_m <= self.critical_gap_m:
                # Frenado máximo permitido por los frenos
                return -self.idm_behavior.comfortable_decel

            # FASE 2: Frenado suave calculado para detenerse en min_gap
            # Usar cinemática: v_final² = v_inicial² + 2*a*d
            # 0 = v² + 2*a*d → a = -v² / (2*d)
            gap_to_brake = perception.leader_distance_m - self.idm_behavior.min_gap

            if gap_to_brake > 0.001:  # Asegurar que hay espacio para frenar
                import math
                accel = -current_speed * current_speed / (2.0 * gap_to_brake)
                # Limita a frenado máximo cómodo (no es una emergencia aún)
                accel = max(accel, -self.idm_behavior.comfortable_decel)
                return accel

        # Caso normal: usar IDM
        desired_speed_ms = self.idm_behavior.desired_speed

        # Actualiza IDM con velocidad deseada del agente
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
            current_speed_ms=current_speed,
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
