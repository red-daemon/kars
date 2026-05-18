"""World: orquestador central del simulador."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random

from kars.physics.models import Vector2, Waypoint
from kars.agents.car_agent import CarAgent
from kars.agents.perception import PerceptionModule
from kars.physics.engine import PhysicsEngine
from kars.environment.road_network import RoadNetwork
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.utils.spatial_index import SpatialGrid
from kars.simulation.scheduler import Scheduler, UpdatePhase
from kars.simulation.statistics import StatsCollector
import kars.config as config


@dataclass
class RenderSnapshot:
    """Snapshot de lo que se debe renderizar en un frame.

    DTO que contiene todo lo necesario para dibujar sin acceder a World.
    """
    # Estado de agentes
    agents: List[tuple] = field(default_factory=list)  # (id, world_pos, heading, speed_kmh, lane_id, s)

    # Entorno
    lanes: List[tuple] = field(default_factory=list)  # (lane_id, waypoints)

    # Tiempo simulado
    sim_time_s: float = 0.0
    tick_number: int = 0

    # Estadisticas para HUD
    avg_speed_kmh: float = 0.0
    fps: float = 0.0


class World:
    """Orquestador central del simulador.

    Responsabilidades:
    - Mantiene estado global (agentes, entorno, tiempo)
    - Ejecuta tick maestro en orden estricto
    - Doble buffer para actualizar simultaneamente
    - Produce snapshots para render
    """

    def __init__(self, network: RoadNetwork):
        """Inicializa World.

        Args:
            network: RoadNetwork con la topologia de calles
        """
        self.network = network
        self.agents: Dict[int, CarAgent] = {}
        self._agent_id_counter = config.AGENT_ID_COUNTER_START

        # Estado temporalizado
        self.tick_number = 0
        self.sim_time_s = 0.0
        self.sim_speed_factor = 1.0  # 1x, 10x, etc

        # Motor de fisica
        self.physics_engine = PhysicsEngine()

        # Indexado espacial
        self.spatial_grid = SpatialGrid(cell_size_m=config.SPATIAL_GRID_CELL_SIZE_M)

        # Scheduler
        self.scheduler = Scheduler()

        # Estadisticas
        self.stats_collector = StatsCollector()

        # Registra callbacks en scheduler
        self._setup_scheduler()

        # Random
        if config.RANDOM_SEED is not None:
            random.seed(config.RANDOM_SEED)

    def _setup_scheduler(self) -> None:
        """Registra callbacks en el scheduler."""
        self.scheduler.register_callback(UpdatePhase.PERCEPTION, self._phase_perception)
        self.scheduler.register_callback(UpdatePhase.DECISION, self._phase_decision)
        self.scheduler.register_callback(UpdatePhase.PHYSICS, self._phase_physics)
        self.scheduler.register_callback(UpdatePhase.ENVIRONMENT, self._phase_environment)
        self.scheduler.register_callback(UpdatePhase.SPATIAL_INDEX, self._phase_spatial_index)
        self.scheduler.register_callback(UpdatePhase.STATISTICS, self._phase_statistics)

    def add_agent(self, agent: CarAgent) -> None:
        """Agrega un agente a la simulacion.

        Args:
            agent: CarAgent a agregar
        """
        self.agents[agent.agent_id] = agent

    def remove_agent(self, agent_id: int) -> bool:
        """Elimina un agente de la simulacion.

        Args:
            agent_id: ID del agente a eliminar

        Returns:
            True si el agente fue eliminado, False si no existía
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    def get_next_agent_id(self) -> int:
        """Obtiene el siguiente ID disponible para un agente.

        Returns:
            Nuevo ID único
        """
        agent_id = self._agent_id_counter
        self._agent_id_counter += 1
        return agent_id

    def _phase_perception(self) -> None:
        """FASE 1: Calcula percepcion de todos los agentes (read-only estado N)."""
        # Prepara dict de otros agentes para PerceptionModule
        other_agents_data = {
            agent_id: (agent.current_lane_id, agent.position_along_lane_s, agent.kinematic_state.speed_ms())
            for agent_id, agent in self.agents.items()
        }

        # Cada agente calcula su percepcion
        for agent in self.agents.values():
            perception = PerceptionModule.compute(
                agent_id=agent.agent_id,
                agent_s=agent.position_along_lane_s,
                agent_lane_id=agent.current_lane_id,
                agent_speed_ms=agent.kinematic_state.speed_ms(),
                other_agents=other_agents_data,
                network=self.network,
            )

            # Almacena en agente para fase de decision
            agent._last_perception = perception

    def _phase_decision(self) -> None:
        """FASE 2: Agentes toman decisiones (read-only estado N)."""
        for agent in self.agents.values():
            perception = getattr(agent, '_last_perception', None)
            if perception is not None:
                # Agente decide aceleracion basada en percepcion
                agent._desired_accel = agent.decide(perception)
            else:
                agent._desired_accel = 0.0

    def _phase_physics(self) -> None:
        """FASE 3: Integra fisica (escribe en buffer N+1)."""
        for agent in self.agents.values():
            desired_accel = getattr(agent, '_desired_accel', 0.0)

            # Integra
            new_state = self.physics_engine.integrate(
                agent.kinematic_state,
                desired_accel,
                agent.physics_body,
                config.TICK_DT_S * self.sim_speed_factor,
            )

            agent.kinematic_state = new_state

    def _phase_environment(self) -> None:
        """FASE 4: Actualiza entorno (semaforos, spawns, etc).

        En MVP: noop. En Fase 3+ agrega semaforos y generacion dinamica.
        """
        pass

    def _phase_spatial_index(self) -> None:
        """FASE 5: Reconstruye indice espacial con posiciones N+1."""
        self.spatial_grid.clear()

        for agent in self.agents.values():
            # Sincroniza posicion en carril basada en (x, y) actual
            try:
                lane = self.network.get_lane(agent.current_lane_id)

                new_s = lane.find_closest_s(agent.kinematic_state.position)
                new_offset = lane.get_lateral_offset_at(agent.kinematic_state.position, new_s)

                agent.set_position_lane(agent.current_lane_id, new_s, new_offset)

                # Inserta en grid
                self.spatial_grid.insert(agent.agent_id, agent.kinematic_state.position)
            except ValueError:
                # Carril no existe, ignorar
                pass

    def _phase_statistics(self) -> None:
        """FASE 6: Recolecta estadisticas (observador puro)."""
        self.stats_collector.record_tick(
            self.tick_number,
            self.sim_time_s,
            list(self.agents.values()),
        )

    def tick(self) -> None:
        """Ejecuta un tick completo (todas las fases)."""
        # Ejecuta scheduler (todas las fases)
        self.scheduler.execute_tick()

        # Actualiza tiempo
        self.sim_time_s += config.TICK_DT_S * self.sim_speed_factor
        self.tick_number += 1

    def build_render_snapshot(self) -> RenderSnapshot:
        """Construye snapshot para que el renderer dibuje."""
        # Posiciones de agentes
        agent_data = []
        for agent in self.agents.values():
            agent_data.append((
                agent.agent_id,
                agent.kinematic_state.position,
                agent.kinematic_state.heading,
                agent.speed_kmh(),
                agent.current_lane_id,
                agent.position_along_lane_s,
            ))

        # Carriles (solo los waypoints para dibujar)
        lane_data = []
        for lane in self.network.get_all_lanes():
            waypoints_list = [(wp.position.x, wp.position.y) for wp in lane.waypoints]
            lane_data.append((lane.lane_id, waypoints_list, lane.width_m))

        # Stats para HUD
        last_stats = self.stats_collector.get_last_tick()
        avg_speed = last_stats.avg_speed_kmh if last_stats else 0.0

        snapshot = RenderSnapshot(
            agents=agent_data,
            lanes=lane_data,
            sim_time_s=self.sim_time_s,
            tick_number=self.tick_number,
            avg_speed_kmh=avg_speed,
            fps=0.0,  # Se actualiza en renderer
        )

        return snapshot

    def get_agents(self) -> List[CarAgent]:
        """Retorna lista de agentes."""
        return list(self.agents.values())

    def num_agents(self) -> int:
        """Numero de agentes."""
        return len(self.agents)

    def set_sim_speed_factor(self, factor: float) -> None:
        """Cambia la velocidad de simulacion (1x, 10x, etc).

        Args:
            factor: Multiplicador de tiempo (1.0 = tiempo real)
        """
        self.sim_speed_factor = max(0.1, factor)
