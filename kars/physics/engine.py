"""Motor físico: integración numérica y restricciones."""

from kars.physics.models import KinematicState, PhysicsBody, Vector2


class PhysicsEngine:
    """Integra ecuaciones cinemáticas usando método de Euler."""

    @staticmethod
    def integrate(
        state: KinematicState,
        desired_accel_ms2: float,
        physics_body: PhysicsBody,
        dt_s: float,
    ) -> KinematicState:
        """Integra estado cinemático hacia adelante en tiempo."""
        # Limita aceleración deseada dentro de límites físicos
        clamped_accel = PhysicsEngine.clamp_acceleration(
            desired_accel_ms2, state, physics_body
        )

        # Construye vector de aceleración en dirección del movimiento
        current_speed = state.speed_ms()
        if current_speed > 1e-6:
            accel_direction = state.velocity.normalize()
        else:
            import math
            accel_direction = Vector2(math.cos(state.heading), math.sin(state.heading))

        accel_vec = accel_direction * clamped_accel

        # Integración de Euler: v(t+dt) = v(t) + a*dt
        new_velocity = state.velocity + accel_vec * dt_s

        new_velocity_mag = new_velocity.magnitude()
        if new_velocity_mag < 0:
            new_velocity = Vector2(0, 0)

        # Actualiza posición: x(t+dt) = x(t) + v(t+dt)*dt
        new_position = state.position + new_velocity * dt_s

        # Actualiza rumbo según dirección de velocidad
        if new_velocity.magnitude() > 1e-6:
            import math
            new_heading = math.atan2(new_velocity.y, new_velocity.x)
        else:
            new_heading = state.heading

        return KinematicState(
            position=new_position,
            velocity=new_velocity,
            acceleration=accel_vec,
            heading=new_heading,
        )

    @staticmethod
    def clamp_acceleration(
        desired_accel_ms2: float, state: KinematicState, physics_body: PhysicsBody
    ) -> float:
        """Limita aceleración deseada dentro de restricciones físicas."""
        current_speed = state.speed_ms()

        if current_speed < 0:
            return max(desired_accel_ms2, physics_body.max_decel_ms2)

        if desired_accel_ms2 > 0:
            return min(desired_accel_ms2, physics_body.max_accel_ms2)
        else:
            return max(desired_accel_ms2, -physics_body.max_decel_ms2)
