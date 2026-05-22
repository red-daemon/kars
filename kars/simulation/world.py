"""World: orquestador central del simulador."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict
import random
import math

from kars.physics.models import Vector2, Waypoint, KinematicState
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
    obstacles: List[tuple] = field(default_factory=list)  # (world_pos, lane_id, s) para obstáculos permanentes

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

    def __init__(self, network: RoadNetwork, allow_spawning: bool = False, on_tick_callback=None):
        """Inicializa World.

        Args:
            network: RoadNetwork con la topologia de calles
            allow_spawning: Si True, auto-spawn de vehículos. Si False, solo manual via mouse.
            on_tick_callback: Callback(world, tick_number) para eventos customizados cada tick.
        """
        self.network = network
        self.agents: Dict[int, CarAgent] = {}
        self._agent_id_counter = config.AGENT_ID_COUNTER_START
        self.allow_spawning = allow_spawning
        self.on_tick_callback = on_tick_callback

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

    def _try_spawn_at_lane_start(self, lane: Lane, zone_params: dict) -> None:
        """Intenta crear un nuevo agente al inicio del carril.

        Args:
            lane: Lane donde hacer spawn
            zone_params: Dict con parámetros de tráfico de la zona
        """
        min_headway = zone_params['min_spawn_headway_m']

        # Verifica si hay agente dentro del headway mínimo
        for agent in self.agents.values():
            if agent.current_lane_id == lane.lane_id and agent.position_along_lane_s < min_headway:
                return

        # Elige velocidad inicial según distribución normal
        speed_mean_kmh = zone_params['speed_mean_kmh']
        speed_std_kmh = zone_params['speed_std_kmh']
        speed_kmh = random.gauss(speed_mean_kmh, speed_std_kmh)
        speed_kmh = max(0.0, min(config.MAX_SPEED_KMH, speed_kmh))
        speed_ms = speed_kmh / 3.6

        # Crea agente al inicio (s ≈ 0)
        agent = CarAgent(
            agent_id=self.get_next_agent_id(),
            current_lane_id=lane.lane_id,
            position_along_lane_s=0.1,
            lateral_offset=0.0,
            speed_tolerance_kmh=0.0,
        )

        # Pone velocidad inicial
        initial_pos = lane.world_position_at(0.1, 0.0)
        initial_heading = lane.heading_at(0.1)
        agent.set_position_world(initial_pos, heading=initial_heading)
        agent.set_velocity_world(Vector2(
            speed_ms * math.cos(initial_heading),
            speed_ms * math.sin(initial_heading),
        ))

        self.add_agent(agent)

    def _disable_agent(self, agent: CarAgent) -> None:
        """Deshabilita un agente por colisión.

        Args:
            agent: CarAgent a deshabilitar
        """
        agent.is_disabled = True
        agent.disable_ticks_remaining = config.COLLISION_DISABLE_TICKS

    def add_permanent_obstacle(self, lane_id: str, position_s: float) -> int:
        """Agrega un obstáculo permanente (señal de alto, accidente, etc).

        Args:
            lane_id: ID del carril
            position_s: Posición a lo largo del carril (metros)

        Returns:
            ID del agente obstáculo (para referencia)
        """
        agent = CarAgent(
            agent_id=self.get_next_agent_id(),
            current_lane_id=lane_id,
            position_along_lane_s=position_s,
            lateral_offset=0.0,
        )

        # Posiciona el obstáculo
        try:
            lane = self.network.get_lane(lane_id)
            world_pos = lane.world_position_at(position_s, 0.0)
            heading = lane.heading_at(position_s)
            agent.set_position_world(world_pos, heading=heading)
        except ValueError:
            return -1

        # Lo pone en estado permanente deshabilitado
        agent.is_disabled = True
        agent.disable_ticks_remaining = -1  # -1 = nunca se elimina

        self.add_agent(agent)
        return agent.agent_id

    def _phase_perception(self) -> None:
        """FASE 1: Calcula percepcion de todos los agentes (read-only estado N)."""
        # Prepara dict de otros agentes para PerceptionModule
        # Incluye flag de deshabilitación para filtrar colisiones
        other_agents_data = {
            agent_id: (agent.current_lane_id, agent.position_along_lane_s,
                      agent.kinematic_state.speed_ms(), agent.is_disabled)
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
            # Agentes deshabilitados no deciden
            if agent.is_disabled:
                agent._desired_accel = 0.0
                continue

            perception = getattr(agent, '_last_perception', None)
            if perception is not None:
                # Agente decide aceleracion basada en percepcion
                agent._desired_accel = agent.decide(perception, self.tick_number)
            else:
                agent._desired_accel = 0.0

    def _phase_physics(self) -> None:
        """FASE 3: Integra fisica (escribe en buffer N+1)."""
        for agent in self.agents.values():
            # Agentes deshabilitados se detienen
            if agent.is_disabled:
                agent.kinematic_state = KinematicState(
                    position=agent.kinematic_state.position,
                    velocity=Vector2(0, 0),
                    acceleration=Vector2(0, 0),
                    heading=agent.kinematic_state.heading,
                )
                continue

            # Agentes esperando en señal de alto se detienen
            if agent.stop_sign_wait_time_remaining_s > 0:
                agent.kinematic_state = KinematicState(
                    position=agent.kinematic_state.position,
                    velocity=Vector2(0, 0),
                    acceleration=Vector2(0, 0),
                    heading=agent.kinematic_state.heading,
                )
                continue

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
        """FASE 4: Actualiza entorno (generador de tráfico, animación orilla, etc)."""
        # Ejecuta callback de escena si existe
        if self.on_tick_callback:
            self.on_tick_callback(self, self.tick_number)

        # Generador de tráfico probabilístico - solo si allow_spawning está habilitado
        if self.allow_spawning:
            for lane in self.network.get_all_lanes():
                zone_params = config.ZONE_TRAFFIC.get(lane.zone, config.ZONE_TRAFFIC['urban'])
                rate = zone_params['arrival_rate_veh_per_min'] / 60.0
                prob = rate * config.TICK_DT_S * self.sim_speed_factor
                if random.random() < prob:
                    self._try_spawn_at_lane_start(lane, zone_params)

        # Animación de agentes en orilla (deshabilitados)
        for agent in list(self.agents.values()):
            if agent.is_disabled:
                # No decrementa si es obstáculo permanente (-1)
                if agent.disable_ticks_remaining > 0:
                    agent.disable_ticks_remaining -= 1

                if agent.shoulder_offset < config.SHOULDER_OFFSET_M:
                    agent.shoulder_offset = min(
                        agent.shoulder_offset + config.SHOULDER_ANIM_SPEED_M_PER_TICK,
                        config.SHOULDER_OFFSET_M
                    )

                # Solo elimina si no es permanente (disable_ticks_remaining >= 0)
                if agent.disable_ticks_remaining == 0:
                    self.remove_agent(agent.agent_id)

        # Decrementa contador de espera en señal de alto
        for agent in list(self.agents.values()):
            if agent.stop_sign_wait_time_remaining_s > 0:
                agent.stop_sign_wait_time_remaining_s -= config.TICK_DT_S * self.sim_speed_factor

    def _phase_spatial_index(self) -> None:
        """FASE 5: Sincroniza posiciones, detecta colisiones, limpia fin de carril."""
        self.spatial_grid.clear()
        agents_to_remove = []

        # SINCRONIZA POSICIONES DE AGENTES ACTIVOS
        for agent in self.agents.values():
            # Agentes deshabilitados no se sincronizan: mantienen su posición del accidente
            if agent.is_disabled:
                # Solo inserta en grid para geometría, pero mantiene s/offset del accidente
                try:
                    self.spatial_grid.insert(agent.agent_id, agent.kinematic_state.position)
                except ValueError:
                    pass
                continue

            # Sincroniza posicion en carril basada en (x, y) actual
            try:
                lane = self.network.get_lane(agent.current_lane_id)

                new_s = lane.find_closest_s(agent.kinematic_state.position)
                new_offset = lane.get_lateral_offset_at(agent.kinematic_state.position, new_s)

                # Comprueba fin de carril
                if new_s >= lane.length_m():
                    agents_to_remove.append(agent.agent_id)
                    continue

                agent.set_position_lane(agent.current_lane_id, new_s, new_offset)

                # Inserta en grid
                self.spatial_grid.insert(agent.agent_id, agent.kinematic_state.position)
            except ValueError:
                # Carril no existe, ignorar
                pass

        # Elimina agentes que llegaron al final
        for agent_id in agents_to_remove:
            self.remove_agent(agent_id)

        # DETECCIÓN DE COLISIONES (después de sincronizar, con datos frescos)
        by_lane: Dict[str, List[CarAgent]] = defaultdict(list)
        for agent in self.agents.values():
            by_lane[agent.current_lane_id].append(agent)

        for lane_id, lane_agents in by_lane.items():
            lane_agents.sort(key=lambda a: a.position_along_lane_s)

            # Detecta solapamientos basado en componente forward del carril
            try:
                lane = self.network.get_lane(lane_id)

                # Calcula dirección forward del carril (desde primer waypoint al último)
                if len(lane.waypoints) >= 2:
                    lane_start = lane.waypoints[0].position
                    lane_end = lane.waypoints[-1].position
                    lane_forward = (lane_end - lane_start).normalize()
                else:
                    # Fallback: usar heading del primer waypoint
                    heading = lane.waypoints[0].heading if lane.waypoints else 0.0
                    lane_forward = Vector2(math.cos(heading), math.sin(heading))

                lane_origin = lane.waypoints[0].position if lane.waypoints else Vector2(0, 0)

                for i in range(len(lane_agents) - 1):
                    rear = lane_agents[i]
                    front = lane_agents[i + 1]

                    # Calcula posiciones world del frente y trasero de cada carro
                    rear_rear_pos = lane.world_position_at(rear.position_along_lane_s - config.CAR_LENGTH_M / 2.0, rear.lateral_offset)
                    rear_front_pos = lane.world_position_at(rear.position_along_lane_s + config.CAR_LENGTH_M / 2.0, rear.lateral_offset)
                    front_rear_pos = lane.world_position_at(front.position_along_lane_s - config.CAR_LENGTH_M / 2.0, front.lateral_offset)
                    front_front_pos = lane.world_position_at(front.position_along_lane_s + config.CAR_LENGTH_M / 2.0, front.lateral_offset)

                    # Proyecta en dirección forward
                    rear_front_proj = (rear_front_pos - lane_origin).dot(lane_forward)
                    front_rear_proj = (front_rear_pos - lane_origin).dot(lane_forward)

                    # Colisión si front_rear_proj < rear_front_proj (hay solapamiento)
                    if front_rear_proj < rear_front_proj:
                        if not rear.is_disabled:
                            self._disable_agent(rear)
                        if not front.is_disabled:
                            self._disable_agent(front)
            except ValueError:
                # Carril no existe
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

        # Obstáculos permanentes (agentes con is_disabled=True y disable_ticks_remaining=-1)
        obstacle_data = []
        for agent in self.agents.values():
            if agent.is_disabled and agent.disable_ticks_remaining == -1:
                obstacle_data.append((
                    agent.kinematic_state.position,
                    agent.current_lane_id,
                    agent.position_along_lane_s,
                ))

        # Stats para HUD
        last_stats = self.stats_collector.get_last_tick()
        avg_speed = last_stats.avg_speed_kmh if last_stats else 0.0

        snapshot = RenderSnapshot(
            agents=agent_data,
            lanes=lane_data,
            obstacles=obstacle_data,
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
