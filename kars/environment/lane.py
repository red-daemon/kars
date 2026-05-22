"""Carril: representado como polilínea (waypoints)."""

from dataclasses import dataclass, field
from typing import List
import math
from kars.physics.models import Vector2, Waypoint
import kars.config as config


@dataclass
class StopSign:
    """Señal de alto en un carril.

    Representa una línea de parada donde los vehículos deben detenerse.
    """

    position_s: float  # Distancia a lo largo del carril (metros)
    is_active: bool = True  # Si está en efecto
    stop_sign_id: int = field(default_factory=lambda: id(object()))  # ID único de la señal


@dataclass
class Lane:
    """Un carril individual representado como polilínea.

    Posición de agente: (current_lane_id, position_along_lane_s, lateral_offset)
    - position_along_lane_s: distancia a lo largo del carril desde inicio
    - lateral_offset: desplazamiento perpendicular (0 = centro)
    """

    lane_id: str
    waypoints: List[Waypoint]
    width_m: float = None
    speed_limit_kmh: float = None
    direction: str = "forward"  # "forward" o "backward"
    zone: str = "urban"  # Tipo de zona para parámetros de tráfico
    stop_signs: List[StopSign] = field(default_factory=list)  # Señales de alto en este carril

    # Campos computados
    _cumulative_distances: List[float] = field(default_factory=list, init=False, repr=False)
    _total_length_m: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self):
        """Precalcula distancias cumulativas para búsqueda O(log N)."""
        if len(self.waypoints) < 2:
            raise ValueError(f"Lane {self.lane_id}: necesita al menos 2 waypoints")

        # Usar defaults de config si no se especificaron
        if self.width_m is None:
            object.__setattr__(self, 'width_m', config.LANE_WIDTH_M)
        if self.speed_limit_kmh is None:
            object.__setattr__(self, 'speed_limit_kmh', config.MAX_SPEED_KMH)

        # Precalcula distancias cumulativas
        cumulative = [0.0]
        for i in range(len(self.waypoints) - 1):
            segment_length = self.waypoints[i].position.distance_to(self.waypoints[i + 1].position)
            cumulative.append(cumulative[-1] + segment_length)

        object.__setattr__(self, '_cumulative_distances', cumulative)
        object.__setattr__(self, '_total_length_m', cumulative[-1])

    def length_m(self) -> float:
        """Longitud total del carril en metros."""
        return self._total_length_m

    def position_at(self, s: float) -> Vector2:
        """Posición (x,y) a distancia s a lo largo del carril.

        Args:
            s: Distancia a lo largo del carril (metros)

        Returns:
            Vector2 en coordenadas mundo (metros)
        """
        # Asegura que s está en rango [0, length]
        s = max(0.0, min(s, self._total_length_m))

        # Busca el segmento de waypoint que contiene s
        for i in range(len(self._cumulative_distances) - 1):
            if s <= self._cumulative_distances[i + 1]:
                # s está entre waypoint[i] y waypoint[i+1]
                segment_start_s = self._cumulative_distances[i]
                segment_end_s = self._cumulative_distances[i + 1]

                # Parámetro de interpolación: 0 en waypoint[i], 1 en waypoint[i+1]
                segment_length = segment_end_s - segment_start_s
                if segment_length < 1e-9:
                    return self.waypoints[i].position

                t = (s - segment_start_s) / segment_length

                # Interpolación lineal
                p0 = self.waypoints[i].position
                p1 = self.waypoints[i + 1].position

                return Vector2(
                    p0.x + t * (p1.x - p0.x),
                    p0.y + t * (p1.y - p0.y),
                )

        # Si llegamos aquí, algo salió mal
        return self.waypoints[-1].position

    def heading_at(self, s: float) -> float:
        """Rumbo (radianes) a distancia s a lo largo del carril."""
        s = max(0.0, min(s, self._total_length_m))

        # Encuentra el segmento
        for i in range(len(self._cumulative_distances) - 1):
            if s <= self._cumulative_distances[i + 1]:
                # Rumbo del segmento: direcci贸n de waypoint[i] a waypoint[i+1]
                p0 = self.waypoints[i].position
                p1 = self.waypoints[i + 1].position

                dx = p1.x - p0.x
                dy = p1.y - p0.y

                return math.atan2(dy, dx)

        return self.waypoints[-1].heading

    def normal_direction_at(self, s: float) -> Vector2:
        """Vector normal perpendicular al carril a distancia s.

        Usado para calcular posici贸n lateral de agentes.
        Returns: vector unitario perpendicular (rotaci贸n 90掳 contraria a heading)
        """
        heading = self.heading_at(s)
        # Normal perpendicular: rotaci贸n 90掳 en sentido contrario
        normal_heading = heading + math.pi / 2.0
        return Vector2(math.cos(normal_heading), math.sin(normal_heading))

    def clamp_lateral_offset(self, offset: float) -> float:
        """Asegura que offset lateral no salga del carril.

        Args:
            offset: Desplazamiento lateral en metros (0 = centro)

        Returns:
            offset ajustado dentro de [-width/2, width/2]
        """
        max_offset = self.width_m / 2.0
        return max(-max_offset, min(offset, max_offset))

    def world_position_at(self, s: float, lateral_offset: float = 0.0) -> Vector2:
        """Posici贸n mundo 2D de un agente en (s, lateral_offset).

        Args:
            s: Distancia a lo largo del carril
            lateral_offset: Desplazamiento perpendicular al carril

        Returns:
            Vector2 en coordenadas mundo
        """
        # Posici贸n a lo largo del carril
        pos_along = self.position_at(s)

        # Si hay offset lateral, a帽ade la componente perpendicular
        if abs(lateral_offset) > 1e-9:
            normal = self.normal_direction_at(s)
            return pos_along + (normal * lateral_offset)

        return pos_along

    def find_closest_s(self, world_pos: Vector2) -> float:
        """Encuentra la distancia s mas cercana en el carril a una posicion mundo."""
        closest_s = 0.0
        closest_dist = float("inf")

        num_samples = max(100, int(self.length_m() / 1.0))
        for i in range(num_samples):
            s = (i / num_samples) * self.length_m()
            pos_on_lane = self.position_at(s)
            dist = world_pos.distance_to(pos_on_lane)

            if dist < closest_dist:
                closest_dist = dist
                closest_s = s

        return closest_s

    def get_lateral_offset_at(self, world_pos: Vector2, s: float) -> float:
        """Calcula offset lateral de una posicion mundo respecto al carril."""
        pos_on_lane = self.position_at(s)
        displacement = world_pos - pos_on_lane
        normal = self.normal_direction_at(s)
        offset = displacement.dot(normal)
        return offset
