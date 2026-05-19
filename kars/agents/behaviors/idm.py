"""Modelo de Conductor Inteligente (IDM): comportamiento de seguimiento de vehículos."""

import math


class IDMBehavior:
    """Ecuaciones IDM para comportamiento de seguimiento vehicular.

    El modelo produce aceleración basada en:
    - Velocidad actual vs velocidad deseada (aceleración en flujo libre)
    - Brecha al líder y velocidad relativa (evitar colisiones)
    """

    def __init__(
        self,
        desired_speed_ms: float,
        time_headway_s: float = 1.5,
        min_gap_m: float = 2.0,
        max_accel_ms2: float = 2.0,
        comfortable_decel_ms2: float = 2.0,
        delta: float = 4.0,
    ):
        """Inicializa parámetros IDM."""
        self.desired_speed = desired_speed_ms
        self.time_headway = time_headway_s
        self.min_gap = min_gap_m
        self.max_accel = max_accel_ms2
        self.comfortable_decel = comfortable_decel_ms2
        self.delta = delta

    def compute_acceleration(
        self,
        current_speed_ms: float,
        leader_distance_m: float,
        leader_speed_ms: float,
    ) -> float:
        """Calcula aceleración deseada usando IDM."""
        v = current_speed_ms
        v0 = self.desired_speed
        d = leader_distance_m
        dv = v - leader_speed_ms  # Positivo si se acerca más rápido que el líder

        # Término de flujo libre: (v / v0)^delta
        free_flow_term = (v / v0) ** self.delta if v0 > 0 else 0.0

        # Brecha deseada dinámica: s* = s0 + v*T + v*dv / (2*sqrt(a*b))
        interaction_term = (
            v * dv / (2.0 * math.sqrt(self.max_accel * self.comfortable_decel))
            if self.max_accel > 0 and self.comfortable_decel > 0
            else 0.0
        )
        desired_gap = self.min_gap + v * self.time_headway + interaction_term

        # Término de evitar colisión: (s* / s)^2
        # Si gap es muy pequeño (< 0.1m), fuerza máxima desaceleración
        if d <= 0.1:
            collision_avoidance_term = 100.0  # Frenado máximo
        elif d > 0:
            collision_avoidance_term = (desired_gap / d) ** 2
        else:
            collision_avoidance_term = 1.0

        # Ecuación IDM: a = amax * [1 - (v/v0)^delta - (s*/s)^2]
        accel = self.max_accel * (1.0 - free_flow_term - collision_avoidance_term)

        return accel
