"""Estructuras de datos física: estado cinemático inmutable."""

from dataclasses import dataclass
from typing import Tuple
import math


@dataclass(frozen=True)
class Waypoint:
    """Punto en una polilínea (metros)."""
    position: "Vector2"
    heading: float  # Radianes


@dataclass(frozen=True)
class Vector2:
    """Vector 2D inmutable en metros."""
    x: float
    y: float

    def __add__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2":
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vector2":
        return Vector2(scalar * self.x, scalar * self.y)

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self) -> "Vector2":
        mag = self.magnitude()
        if mag < 1e-10:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)

    def dot(self, other: "Vector2") -> float:
        return self.x * other.x + self.y * other.y

    def distance_to(self, other: "Vector2") -> float:
        """Distancia Euclidiana a otro punto."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True)
class KinematicState:
    """Estado cinemático inmutable de un vehículo (unidades SI)."""
    position: Vector2  # Metros desde origen del mundo
    velocity: Vector2  # Metros/segundo
    acceleration: Vector2  # Metros/segundo²
    heading: float  # Radianes (0 = derecha/este)

    def speed_ms(self) -> float:
        """Magnitud actual de velocidad (m/s)."""
        return self.velocity.magnitude()

    def speed_kmh(self) -> float:
        """Velocidad actual en km/h."""
        return self.speed_ms() * 3.6


@dataclass(frozen=True)
class PhysicsBody:
    """Propiedades físicas constantes de un vehículo."""
    length_m: float
    width_m: float
    mass_kg: float = 1500.0

    max_accel_ms2: float = 2.0
    max_decel_ms2: float = 4.0
    comfortable_decel_ms2: float = 2.0
