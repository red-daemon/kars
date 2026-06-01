"""Calle (Road): colección de segmentos viales."""

from dataclasses import dataclass
from typing import List
from kars.environment.segment import RoadSegment


@dataclass
class Road:
    """Una calle compuesta por uno o más segmentos.

    Estructura:
    - road_id: Identificador único de la calle
    - name: Nombre (ej: "Avenida Principal")
    - segments: Lista ordenada de RoadSegment que forman esta calle
    - speed_limit_kmh: Límite de velocidad (pueden variar por segmento en futuro)

    Ejemplo:
        Avenida Principal (road_id="av_main"):
        - Segmento 0: (0,0) → (100,0), 2 carriles
        - Segmento 1: (100,0) → (200,0), 3 carriles (cruza intersección)
    """

    road_id: str
    name: str
    segments: List[RoadSegment]
    speed_limit_kmh: float = 50.0

    def __post_init__(self):
        """Valida que la calle tenga al menos 1 segmento."""
        if not self.segments:
            raise ValueError(f"Road {self.road_id}: necesita al menos 1 segmento")

    def num_segments(self) -> int:
        """Número de segmentos en esta calle."""
        return len(self.segments)

    def total_length_m(self) -> float:
        """Longitud total de la calle (suma de segmentos).

        Returns:
            float: Longitud en metros
        """
        total = 0.0
        for segment in self.segments:
            # Distancia del inicio al fin del segmento
            total += segment.start_pos_m.distance_to(segment.end_pos_m)
        return total
