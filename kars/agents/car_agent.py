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

    # Velocidad media deseada del carro (fija desde spawn, no cambia)
    # Se calcula como: speed_limit_kmh * speed_multiplier
    desired_speed_mean_ms: float = config.IDM_DESIRED_SPEED_MS

    # Rango de oscilación de velocidad alrededor de desired_speed_mean (metros/segundo)
    # Cada tick, la velocidad deseada varía: desired_speed_mean ± random(-speed_oscillation_range, +speed_oscillation_range)
    # E.g., 1.0 m/s = oscilación de ±1.0 m/s (±3.6 km/h)
    speed_oscillation_range_ms: float = 0.0

    # Gap crítico: distancia umbral en la que comienza frenado máximo (metros)
    # Conductores precavidos: 10m (frenan temprano)
    # Conductores normales: 5m
    # Conductores agresivos: 2m (casi chocan antes de frenar)
    critical_gap_m: float = 5.0

    # Parámetros de comportamiento en señales de alto
    # Media de tiempo de espera en segundos
    stop_sign_wait_mean_s: float = 1.0
    # Desviación estándar del tiempo de espera en segundos
    stop_sign_wait_stddev_s: float = 0.3
    # Buffer adicional de parada antes de la línea (metros)
    # Se suma a 1m base: precavido 1.0m, normal 0.5m, agresivo 0.0m
    stop_sign_buffer_m: float = 0.5

    # Estado de colisión
    is_disabled: bool = False          # True si está en estado de colisión
    disable_ticks_remaining: int = 0   # Countdown para remoción
    shoulder_offset: float = 0.0       # Offset actual hacia la orilla (m)

    # Estado de espera en señal de alto
    stop_sign_wait_time_remaining_s: float = 0.0  # Contador de espera
    _stop_sign_wait_initialized: bool = False      # Si ya se sorteó el tiempo
    processed_stop_signs: list = field(default_factory=list)  # IDs de señales ya procesadas

    # Estado de cambio de carril
    target_lane_id: Optional[str] = None           # Carril objetivo durante cambio de carril
    lane_change_duration_s: float = 1.5            # Duración total de la animación (segundos)
    lane_change_elapsed_s: float = 0.0             # Tiempo transcurrido en la transición
    lane_change_start_offset: float = 0.0          # Offset inicial antes de empezar cambio
    lane_change_target_offset: float = 0.0         # Offset objetivo al llegar al carril destino
    target_lane_at_position_s: Optional[float] = None  # Posición en la que cambiar de carril
    target_lane_id_on_signal: Optional[str] = None     # Carril objetivo cuando se cumple la condición
    _lane_change_triggered: bool = False           # Si ya se triggeró el cambio programado

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

    def initiate_lane_change(self, target_lane_id: str, target_offset: float, duration_s: float = 1.5) -> None:
        """Inicia transición suave a otro carril.

        Args:
            target_lane_id: ID del carril destino
            target_offset: Offset objetivo (desplazamiento perpendicular al carril destino)
            duration_s: Duración de la transición en segundos
        """
        object.__setattr__(self, 'target_lane_id', target_lane_id)
        object.__setattr__(self, 'lane_change_duration_s', duration_s)
        object.__setattr__(self, 'lane_change_elapsed_s', 0.0)
        object.__setattr__(self, 'lane_change_start_offset', self.lateral_offset)
        object.__setattr__(self, 'lane_change_target_offset', target_offset)

    def update_lane_change(self) -> None:
        """Actualiza la transición de carril cada tick.

        Incrementa el offset hacia el objetivo en pasos pequeños.
        Cuando llega, cambia de carril.
        """
        if self.target_lane_id is None:
            return

        # Incremento direccional: 0.05m/tick, en la dirección del target
        direction = 1 if self.lane_change_target_offset > 0 else -1
        increment = 0.05 * direction
        new_offset = self.lateral_offset + increment

        object.__setattr__(self, 'lateral_offset', new_offset)
        object.__setattr__(self, 'lane_change_elapsed_s', self.lane_change_elapsed_s + config.TICK_DT_S)

        # Si alcanzó o pasó el objetivo, completa la transición
        if direction > 0:
            # Cambio hacia derecha: detente cuando new_offset >= target
            if new_offset >= self.lane_change_target_offset:
                object.__setattr__(self, 'current_lane_id', self.target_lane_id)
                object.__setattr__(self, 'lateral_offset', 0.0)
                object.__setattr__(self, 'target_lane_id', None)
                object.__setattr__(self, 'lane_change_elapsed_s', 0.0)
        else:
            # Cambio hacia izquierda: detente cuando new_offset <= target
            if new_offset <= self.lane_change_target_offset:
                object.__setattr__(self, 'current_lane_id', self.target_lane_id)
                object.__setattr__(self, 'lateral_offset', 0.0)
                object.__setattr__(self, 'target_lane_id', None)
                object.__setattr__(self, 'lane_change_elapsed_s', 0.0)

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
        import random

        current_speed = self.kinematic_state.speed_ms()
        current_braking_mode = "none"

        # Distancia umbral para comenzar frenado suave (metros)
        # Calculada dinámicamente: distancia de frenado = v² / (2*a)
        # Usa velocidad deseada y frenado cómodo
        desired_speed = self.idm_behavior.desired_speed
        comfortable_decel = self.idm_behavior.comfortable_decel
        BRAKING_DISTANCE_M = max(30.0, (desired_speed ** 2) / (2.0 * comfortable_decel)) if comfortable_decel > 0 else 30.0

        # Manejo de señales de alto
        # Solo aplica si no hay carro más cerca adelante
        if perception.nearby_stop_signs and perception.leader_distance_m > perception.nearby_stop_signs[0]['distance_m']:
            nearest_stop_sign = perception.nearby_stop_signs[0]
            stop_sign_distance = nearest_stop_sign['distance_m']
            stop_sign_position_s = nearest_stop_sign['position_s']
            stop_sign_id = nearest_stop_sign['stop_sign_id']

            # Si no fue procesada aún, aplicar lógica
            if stop_sign_id not in self.processed_stop_signs:
                if tick_number % 50 == 0:
                    print(f"[STOP SIGN DEBUG] Agent {self.agent_id}: distance={stop_sign_distance:.1f}m, "
                          f"position_s={stop_sign_position_s:.1f}m, speed={current_speed:.2f}m/s, "
                          f"wait_remaining={self.stop_sign_wait_time_remaining_s:.2f}s")

                # Si terminó la espera, marcar como procesada
                if self._stop_sign_wait_initialized and self.stop_sign_wait_time_remaining_s <= 0:
                    object.__setattr__(self, '_stop_sign_wait_initialized', False)
                    self.processed_stop_signs.append(stop_sign_id)
                    # Dejar que IDM normal continúe
                # Si aún está esperando o debe frenar para llegar
                elif stop_sign_distance < BRAKING_DISTANCE_M:
                    # Decrementa timer si está esperando (ocurre aquí en DECISION, no en ENVIRONMENT)
                    if self._stop_sign_wait_initialized and self.stop_sign_wait_time_remaining_s > 0:
                        object.__setattr__(self, 'stop_sign_wait_time_remaining_s',
                                         self.stop_sign_wait_time_remaining_s - config.TICK_DT_S)

                    # Si está casi detenido (v < 0.05 m/s) e inicializa espera
                    if current_speed < 0.05 and not self._stop_sign_wait_initialized:
                        # Sortea tiempo aleatorio
                        wait_time = random.gauss(self.stop_sign_wait_mean_s, self.stop_sign_wait_stddev_s)
                        wait_time = max(0.0, wait_time)  # No puede ser negativo
                        object.__setattr__(self, 'stop_sign_wait_time_remaining_s', wait_time)
                        object.__setattr__(self, '_stop_sign_wait_initialized', True)

                    # Si está esperando o debe frenar hasta detenerse completamente, mantén velocidad = 0
                    if self.stop_sign_wait_time_remaining_s > 0 or (self._stop_sign_wait_initialized and current_speed > 0):
                        return 0.0

                    # Si debe frenar para llegar a la señal
                    if current_speed > 0:
                        agent_front_s = self.position_along_lane_s + config.CAR_LENGTH_M / 2.0

                        # Calcula posición efectiva de parada: 1m base + buffer del carro
                        stop_buffer_base_m = 1.0
                        effective_stop_position = stop_sign_position_s - stop_buffer_base_m - self.stop_sign_buffer_m
                        gap_to_stop = effective_stop_position - agent_front_s

                        if current_speed < 0.5:
                            accel = -current_speed / config.TICK_DT_S if current_speed > 0 else 0.0
                        elif gap_to_stop > 2.0:
                            accel = -current_speed * current_speed / (2.0 * gap_to_stop)
                            accel = max(accel, -self.idm_behavior.comfortable_decel)
                        else:
                            accel = -self.idm_behavior.comfortable_decel

                        return accel

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

                print(f"[Tick {tick_number}] Agent {self.agent_id}: {old_mode} -> {current_braking_mode} | "
                      f"Modo duro {time_in_mode_s:.3f}s, a_prom={avg_accel:.2f}m/s2 | "
                      f"gap_rear={perception.leader_distance_m:.2f}m, center-to-center={gap_center_to_center:.2f}m, "
                      f"speed={current_speed*3.6:.1f}km/h, a_actual={accel:.2f}m/s2 | "
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

                pass  # print(f"[Tick {tick_number}] Agent exited braking mode")

        # Caso normal: usar IDM
        # Aplica oscilación de velocidad alrededor de la velocidad media deseada
        desired_speed_mean_ms = self.desired_speed_mean_ms
        speed_oscillation_range_ms = self.speed_oscillation_range_ms

        # Ruido uniforme: random entre -range y +range
        speed_noise = random.uniform(-speed_oscillation_range_ms, speed_oscillation_range_ms)
        desired_speed_ms = desired_speed_mean_ms + speed_noise

        # Actualiza IDM con velocidad deseada del agente (con oscilación aplicada)
        idm_with_tolerance = IDMBehavior(
            desired_speed_ms=desired_speed_ms,
            time_headway_s=self.idm_behavior.time_headway,
            min_gap_m=self.idm_behavior.min_gap,
            max_accel_ms2=self.idm_behavior.max_accel,
            comfortable_decel_ms2=self.idm_behavior.comfortable_decel,
            delta=self.idm_behavior.delta,
        )

        # Resetea estado de stop sign si se aleja
        if not perception.nearby_stop_signs and self._stop_sign_wait_initialized:
            object.__setattr__(self, '_stop_sign_wait_initialized', False)
            object.__setattr__(self, 'stop_sign_wait_time_remaining_s', 0.0)

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
