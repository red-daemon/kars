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

    # Debug: track de estado anterior para imprimir cambios
    _last_braking_mode: str = "none"   # "none", "cruise", "soft_brake", "hard_brake", "stopped"
    _last_mode_tick: int = 0           # Tick en que cambió el modo
    _last_mode_speed_ms: float = 0.0   # Velocidad cuando cambió el modo

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

    def decide(self, perception: PerceptionData, tick_number: int = 0) -> float:
        """Calcula aceleración deseada basada en percepción.

        Usa el modelo IDM de seguimiento vehicular, pero con frenado especial
        cuando el obstáculo está completamente detenido y cerca.

        Frenado inteligente: mantiene velocidad hasta distancia umbral,
        luego frena suavemente para detenerse exactamente en min_gap.

        Args:
            perception: PerceptionData del mundo
            tick_number: Número de tick actual (para debug)

        Returns:
            Aceleración deseada en m/s²
        """
        current_speed = self.kinematic_state.speed_ms()
        current_braking_mode = "none"

        # Distancia umbral para comenzar frenado suave (metros)
        BRAKING_DISTANCE_M = 30.0

        # Obstáculo parado cerca: usar frenado cinemático
        if perception.leader_speed_ms == 0.0 and perception.leader_distance_m < BRAKING_DISTANCE_M:
            current_braking_mode = "stopped" if current_speed < 0.1 else "braking"

            # Calcula posición de la línea imaginaria (a un carro completo antes del obstáculo)
            # Se apunta a esta línea; si se pasa ~medio carro, terminará en min_gap correcto
            agent_front_s = self.position_along_lane_s + config.CAR_LENGTH_M / 2.0
            obstacle_rear_s = agent_front_s + perception.leader_distance_m
            stop_line_s = obstacle_rear_s - config.CAR_LENGTH_M

            # Gap desde frente del carro hasta la línea imaginaria
            gap_to_target = stop_line_s - agent_front_s

            # Debug: muestra cálculo de posiciones
            if tick_number % 50 == 0:  # Cada 50 ticks
                print(f"[BRAKING CALC TICK {tick_number}] Agent {self.agent_id}: "
                      f"agent_center={self.position_along_lane_s:.2f}m, "
                      f"agent_front={agent_front_s:.2f}m, "
                      f"gap_rear_to_obstacle={perception.leader_distance_m:.2f}m, "
                      f"obstacle_rear={obstacle_rear_s:.2f}m, "
                      f"min_gap={self.idm_behavior.min_gap:.2f}m, "
                      f"stop_line={stop_line_s:.2f}m, "
                      f"gap_to_target={gap_to_target:.2f}m")

            if current_speed < 0.5:
                # Velocidad baja: fuerza a exactamente 0 en el siguiente frame
                accel = -current_speed / config.TICK_DT_S if current_speed > 0 else 0.0
            elif gap_to_target > 2.0:
                # Frenado cinemático puro: a = -v²/(2*gap)
                accel = -current_speed * current_speed / (2.0 * gap_to_target)
                # Limita a máximo frenado confortable
                accel = max(accel, -self.idm_behavior.comfortable_decel)
            elif gap_to_target > 0.0:
                # Muy cerca (< 2m): máximo frenado para evitar paradoja de Zenón
                accel = -self.idm_behavior.comfortable_decel
            else:
                # Ya pasó/está en la línea: máximo frenado de emergencia
                accel = -self.idm_behavior.comfortable_decel

            # Debug: imprime solo cuando cambia de modo
            if current_braking_mode != self._last_braking_mode:
                old_mode = self._last_braking_mode
                ticks_in_mode = tick_number - self._last_mode_tick
                time_in_mode_s = ticks_in_mode * config.TICK_DT_S
                avg_accel = (current_speed - self._last_mode_speed_ms) / time_in_mode_s if time_in_mode_s > 0 else 0.0
                gap_center_to_center = perception.leader_distance_m + config.CAR_LENGTH_M

                object.__setattr__(self, '_last_braking_mode', current_braking_mode)
                object.__setattr__(self, '_last_mode_tick', tick_number)
                object.__setattr__(self, '_last_mode_speed_ms', current_speed)

                # Comparación con línea de STOP HERE
                agent_front_s = self.position_along_lane_s + config.CAR_LENGTH_M / 2.0
                obstacle_rear_s = agent_front_s + perception.leader_distance_m
                stop_line_s = obstacle_rear_s - config.IDM_MIN_GAP_M
                agent_center_s = self.position_along_lane_s
                overshoot = agent_center_s - stop_line_s

                print(f"[Tick {tick_number}] Agent {self.agent_id}: {old_mode} → {current_braking_mode} | "
                      f"Modo duró {time_in_mode_s:.3f}s, a_prom={avg_accel:.2f}m/s² | "
                      f"gap_rear={perception.leader_distance_m:.2f}m, center-to-center={gap_center_to_center:.2f}m, "
                      f"speed={current_speed*3.6:.1f}km/h, a_actual={accel:.2f}m/s² | "
                      f"STOP LINE at {stop_line_s:.2f}m, agent center at {agent_center_s:.2f}m, overshoot={overshoot:+.2f}m")

            return accel
        else:
            # Fuera de zona de frenado especial
            if self._last_braking_mode != "none":
                old_mode = self._last_braking_mode
                ticks_in_mode = tick_number - self._last_mode_tick
                time_in_mode_s = ticks_in_mode * config.TICK_DT_S
                avg_accel = (current_speed - self._last_mode_speed_ms) / time_in_mode_s if time_in_mode_s > 0 else 0.0
                gap_center_to_center = perception.leader_distance_m + config.CAR_LENGTH_M

                object.__setattr__(self, '_last_braking_mode', "none")
                object.__setattr__(self, '_last_mode_tick', tick_number)
                object.__setattr__(self, '_last_mode_speed_ms', current_speed)

                print(f"[Tick {tick_number}] Agent {self.agent_id}: {old_mode} → none | "
                      f"Modo duró {time_in_mode_s:.3f}s, a_prom={avg_accel:.2f}m/s² | "
                      f"gap_rear={perception.leader_distance_m:.2f}m, center-to-center={gap_center_to_center:.2f}m, "
                      f"speed={current_speed*3.6:.1f}km/h")

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
