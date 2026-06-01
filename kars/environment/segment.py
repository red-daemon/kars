"""Segmento de vía: tramo con múltiples carriles paralelos."""

from dataclasses import dataclass
from typing import List, Dict
from kars.environment.lane import Lane
from kars.physics.models import Vector2


@dataclass
class RoadSegment:
    """Un tramo de vía con múltiples carriles paralelos.

    Ejemplos:
    - MVP: 1 segmento con 1 carril (línea recta)
    - Fase 2: 1 segmento con 3 carriles (Avenida con 3 carriles por dirección)
    - Fase 3: N segmentos conectados en grafo (intersecciones)
    """

    segment_id: str
    lanes: List[Lane]
    start_pos_m: Vector2
    end_pos_m: Vector2

    def __post_init__(self):
        """Valida que haya al menos 1 carril y que estén ordenados por lane_index."""
        if not self.lanes:
            raise ValueError(f"RoadSegment {self.segment_id}: necesita al menos 1 carril")

        # Verifica que lanes estén ordenadas por lane_index de forma secuencial
        lane_indices = [lane.lane_index for lane in self.lanes]
        if lane_indices != list(range(len(self.lanes))):
            raise ValueError(
                f"RoadSegment {self.segment_id}: lanes no están ordenadas secuencialmente. "
                f"Indices encontrados: {lane_indices}, esperado: {list(range(len(self.lanes)))}"
            )

    def get_lane(self, lane_index: int) -> Lane:
        """Retorna el lane en índice dado.

        Args:
            lane_index: Índice (0 = primer carril)

        Returns:
            Lane

        Raises:
            IndexError si índice está fuera de rango
        """
        return self.lanes[lane_index]

    def get_lane_by_id(self, lane_id: str) -> Lane:
        """Retorna el lane por ID.

        Args:
            lane_id: ID del carril

        Returns:
            Lane

        Raises:
            ValueError si no existe
        """
        for lane in self.lanes:
            if lane.lane_id == lane_id:
                return lane
        raise ValueError(f"Lane {lane_id} no encontrado en segmento {self.segment_id}")

    def num_lanes(self) -> int:
        """Número de carriles en este segmento."""
        return len(self.lanes)

    def total_width_m(self) -> float:
        """Ancho total del segmento (suma de anchos de todos los carriles).

        Returns:
            float: Ancho total en metros
        """
        return sum(lane.width_m for lane in self.lanes)

    def get_speed_limit_kmh(self) -> float:
        """Límite de velocidad del segmento (del primer carril).

        Todos los carriles de un segment deben tener el mismo límite.

        Returns:
            float: Límite de velocidad en km/h
        """
        return self.lanes[0].speed_limit_kmh if self.lanes else 0.0
