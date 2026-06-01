"""Red de vías: grafo de segmentos y carriles."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING
from kars.environment.segment import RoadSegment
from kars.environment.lane import Lane
from kars.physics.models import Vector2

if TYPE_CHECKING:
    from kars.environment.road import Road


@dataclass
class RoadNetwork:
    """Red de vías (calles): grafo de segmentos y carriles.

    Estructura:
    - roads: Dict de calles (Road)
    - segments: Dict de segmentos (RoadSegment)
    - lanes: Dict de carriles (Lane)

    En MVP: 1 road con 1 segment con 1 carril (trivial)
    En Fase 3+: múltiples roads y segmentos conectados
    """

    roads: Dict[str, 'Road'] = field(default_factory=dict)  # road_id -> Road
    segments: Dict[str, RoadSegment] = field(default_factory=dict)
    lanes: Dict[str, Lane] = field(default_factory=dict)

    def add_road(self, road: 'Road') -> None:
        """Agrega una calle (road) y todos sus segmentos a la red.

        Args:
            road: Road a agregar

        Raises:
            ValueError si road_id ya existe
        """
        if road.road_id in self.roads:
            raise ValueError(f"Road {road.road_id} ya existe")

        self.roads[road.road_id] = road

        # Agrega todos los segmentos de la calle
        for segment in road.segments:
            self.add_segment(segment)

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

    def num_roads(self) -> int:
        """Número total de calles en la red."""
        return len(self.roads)

    def get_road(self, road_id: str) -> 'Road':
        """Busca una calle por ID.

        Args:
            road_id: ID de la calle

        Returns:
            Road

        Raises:
            ValueError si no existe
        """
        if road_id not in self.roads:
            raise ValueError(f"Road {road_id} no encontrada en red")
        return self.roads[road_id]

    def get_all_roads(self) -> List['Road']:
        """Retorna todas las calles en la red."""
        return list(self.roads.values())
