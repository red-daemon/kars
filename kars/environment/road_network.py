"""Red de vías: grafo de segmentos y carriles."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from kars.environment.segment import RoadSegment
from kars.environment.lane import Lane
from kars.physics.models import Vector2


@dataclass
class RoadNetwork:
    """Red de segmentos viales (grafo).

    En MVP: 1 segmento con 1 carril (trivial)
    En Fase 3+: grafo con múltiples segmentos conectados
    """

    segments: Dict[str, RoadSegment] = field(default_factory=dict)
    lanes: Dict[str, Lane] = field(default_factory=dict)

    def add_segment(self, segment: RoadSegment) -> None:
        """Agrega un segmento y sus carriles al network.

        Args:
            segment: RoadSegment a agregar

        Raises:
            ValueError si segment_id ya existe
        """
        if segment.segment_id in self.segments:
            raise ValueError(f"Segmento {segment.segment_id} ya existe")

        self.segments[segment.segment_id] = segment

        # Registra todos los carriles del segmento
        for lane in segment.lanes:
            if lane.lane_id in self.lanes:
                raise ValueError(f"Lane {lane.lane_id} ya existe")
            self.lanes[lane.lane_id] = lane

    def get_lane(self, lane_id: str) -> Lane:
        """Busca un lane por ID.

        Args:
            lane_id: ID del carril

        Returns:
            Lane

        Raises:
            ValueError si no existe
        """
        if lane_id not in self.lanes:
            raise ValueError(f"Lane {lane_id} no encontrado en red")
        return self.lanes[lane_id]

    def get_segment(self, segment_id: str) -> RoadSegment:
        """Busca un segmento por ID.

        Args:
            segment_id: ID del segmento

        Returns:
            RoadSegment

        Raises:
            ValueError si no existe
        """
        if segment_id not in self.segments:
            raise ValueError(f"Segmento {segment_id} no encontrado en red")
        return self.segments[segment_id]

    def get_segments_by_position(
        self, pos: Vector2, radius_m: float
    ) -> List[RoadSegment]:
        """Retorna segmentos cercanos a una posición (para percepciones futuras).

        Args:
            pos: Vector2 posición mundo
            radius_m: Radio de búsqueda en metros

        Returns:
            Lista de segmentos dentro del radio
        """
        nearby = []
        for segment in self.segments.values():
            # Distancia al inicio o fin del segmento
            dist_to_start = pos.distance_to(segment.start_pos_m)
            dist_to_end = pos.distance_to(segment.end_pos_m)

            if dist_to_start <= radius_m or dist_to_end <= radius_m:
                nearby.append(segment)

        return nearby

    def get_all_lanes(self) -> List[Lane]:
        """Retorna todos los carriles en la red."""
        return list(self.lanes.values())

    def get_all_segments(self) -> List[RoadSegment]:
        """Retorna todos los segmentos en la red."""
        return list(self.segments.values())

    def num_lanes(self) -> int:
        """Número total de carriles en la red."""
        return len(self.lanes)

    def num_segments(self) -> int:
        """Número total de segmentos en la red."""
        return len(self.segments)
