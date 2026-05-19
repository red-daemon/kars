"""Módulo de percepción: qué "ve" cada agente."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PerceptionData:
    """Información que un agente percibe del mundo.

    Todo en unidades SI (metros, m/s, etc).
    """

    # Distancia al carro de adelante (metros)
    # Infinito si no hay carro de adelante visible
    leader_distance_m: float

    # Velocidad del carro de adelante (m/s)
    leader_speed_ms: float

    # Distancia al carro de atrás (metros)
    # Infinito si no hay carro de atrás visible
    follower_distance_m: float

    # Velocidad del carro de atrás (m/s)
    follower_speed_ms: float

    # Límite de velocidad del carril actual (km/h)
    speed_limit_kmh: float

    # ID del carril actual
    current_lane_id: str

    def __post_init__(self):
        """Valida que distancias sean positivas."""
        if self.leader_distance_m < 0:
            raise ValueError("leader_distance_m no puede ser negativo")
        if self.follower_distance_m < 0:
            raise ValueError("follower_distance_m no puede ser negativo")


class PerceptionModule:
    """Calcula la percepción de un agente basada en el estado del mundo.

    En MVP: solo percibe carril actual (sin carriles adyacentes).
    En Fase 2: expande a carriles adyacentes para cambio de carril.
    """

    PERCEPTION_HORIZON = 1000.0  # Mirar hasta 1000m adelante/atrás
    PERCEPTION_TOLERANCE = 1e-6

    @staticmethod
    def compute(
        agent_id: int,
        agent_s: float,
        agent_lane_id: str,
        agent_speed_ms: float,
        other_agents: dict,  # {agent_id -> (lane_id, s, speed, is_disabled)}
        network,  # RoadNetwork
    ) -> PerceptionData:
        """Calcula percepción del agente.

        Incluye agentes deshabilitados (colisionados) como obstáculos.
        El IDM verá agentes parados (speed=0) con distancia > 0 y frenarán.

        Args:
            agent_id: ID del agente que percibe
            agent_s: Posición a lo largo del carril (metros)
            agent_lane_id: ID del carril del agente
            agent_speed_ms: Velocidad actual del agente (m/s)
            other_agents: Dict {agent_id -> (lane_id, s, speed, is_disabled)} de otros agentes
            network: RoadNetwork para búsqueda de carriles

        Returns:
            PerceptionData con información del mundo
        """
        # Obtén carril del agente
        try:
            lane = network.get_lane(agent_lane_id)
        except ValueError:
            # Si el carril no existe, retorna percepción "vacía"
            return PerceptionData(
                leader_distance_m=float("inf"),
                leader_speed_ms=0.0,
                follower_distance_m=float("inf"),
                follower_speed_ms=0.0,
                speed_limit_kmh=20.0,
                current_lane_id=agent_lane_id,
            )

        # Busca el carro más cercano adelante y atrás en el mismo carril
        leader_distance = float("inf")
        leader_speed = 0.0
        follower_distance = float("inf")
        follower_speed = 0.0

        for other_id, other_data in other_agents.items():
            if other_id == agent_id:
                continue  # Ignora al agente mismo

            # Desempaca datos (lane_id, s, speed, is_disabled)
            other_lane_id, other_s, other_speed = other_data[:3]

            if other_lane_id != agent_lane_id:
                continue  # Solo considera agentes en el mismo carril (MVP)

            # Calcula brecha (distancia a lo largo del carril)
            gap = other_s - agent_s

            # Si está adelante y es el más cercano
            if gap > PerceptionModule.PERCEPTION_TOLERANCE:
                if gap < leader_distance:
                    leader_distance = gap
                    leader_speed = other_speed

            # Si está atrás y es el más cercano
            elif gap < -PerceptionModule.PERCEPTION_TOLERANCE:
                if -gap < follower_distance:
                    follower_distance = -gap
                    follower_speed = other_speed

        return PerceptionData(
            leader_distance_m=leader_distance,
            leader_speed_ms=leader_speed,
            follower_distance_m=follower_distance,
            follower_speed_ms=follower_speed,
            speed_limit_kmh=lane.speed_limit_kmh,
            current_lane_id=agent_lane_id,
        )
