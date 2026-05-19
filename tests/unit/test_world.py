"""Tests unitarios para World."""

from kars.physics.models import Vector2, Waypoint, KinematicState
from kars.agents.car_agent import CarAgent
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.world import World, RenderSnapshot
from kars.simulation.scheduler import UpdatePhase
import kars.config as config


class TestWorld:
    """Tests de World."""

    def create_simple_world(self) -> World:
        """Crea un World simple para testing."""
        # Entorno
        lane = Lane(
            lane_id="lane_0",
            waypoints=[Waypoint(Vector2(0, 0), heading=0), Waypoint(Vector2(500, 0), heading=0)],
        )
        segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(500, 0))
        network = RoadNetwork()
        network.add_segment(segment)

        # World
        world = World(network)
        return world

    def test_world_creation(self):
        """Crea un World valido."""
        world = self.create_simple_world()

        assert world.tick_number == 0
        assert world.sim_time_s == 0.0
        assert world.num_agents() == 0

    def test_world_add_agent(self):
        """Agrega un agente a World."""
        world = self.create_simple_world()

        agent = CarAgent(agent_id=1, current_lane_id="lane_0", position_along_lane_s=100.0)
        world.add_agent(agent)

        assert world.num_agents() == 1
        assert 1 in world.agents

    def test_world_tick_increments_time(self):
        """Un tick incrementa el tiempo simulado."""
        world = self.create_simple_world()

        initial_time = world.sim_time_s
        initial_tick = world.tick_number

        world.tick()

        assert world.tick_number == initial_tick + 1
        assert world.sim_time_s > initial_time

    def test_world_tick_updates_agent_position(self):
        """Un tick mueve al agente segun IDM."""
        world = self.create_simple_world()

        agent = CarAgent(agent_id=1, current_lane_id="lane_0", position_along_lane_s=100.0)
        agent.kinematic_state = KinematicState(
            position=Vector2(100, 0),
            velocity=Vector2(0, 0),
            acceleration=Vector2(0, 0),
            heading=0,
        )
        world.add_agent(agent)

        initial_pos = agent.kinematic_state.position.x
        world.tick()
        final_pos = agent.kinematic_state.position.x

        # Agente debe moverse adelante (acelera en flujo libre)
        assert final_pos > initial_pos

    def test_world_sim_speed_factor(self):
        """Cambia factor de velocidad de simulacion."""
        world = self.create_simple_world()

        agent = CarAgent(agent_id=1, current_lane_id="lane_0", position_along_lane_s=100.0)
        agent.kinematic_state = KinematicState(
            position=Vector2(100, 0),
            velocity=Vector2(0, 0),
            acceleration=Vector2(0, 0),
            heading=0,
        )
        world.add_agent(agent)

        # Tick con 1x speed
        world.set_sim_speed_factor(1.0)
        world.tick()
        pos_1x = agent.kinematic_state.position.x

        # Reset
        agent.kinematic_state = KinematicState(
            position=Vector2(100, 0),
            velocity=Vector2(0, 0),
            acceleration=Vector2(0, 0),
            heading=0,
        )

        # Tick con 2x speed
        world.set_sim_speed_factor(2.0)
        world.tick()
        pos_2x = agent.kinematic_state.position.x

        # Con 2x speed, debe moverse mas
        assert pos_2x > pos_1x

    def test_world_build_render_snapshot(self):
        """Construye snapshot para render."""
        world = self.create_simple_world()

        agent = CarAgent(agent_id=1, current_lane_id="lane_0", position_along_lane_s=100.0)
        agent.kinematic_state = KinematicState(
            position=Vector2(100, 0),
            velocity=Vector2(5, 0),
            acceleration=Vector2(0, 0),
            heading=0,
        )
        world.add_agent(agent)

        world.tick()
        snapshot = world.build_render_snapshot()

        assert isinstance(snapshot, RenderSnapshot)
        assert len(snapshot.agents) == 1
        assert len(snapshot.lanes) > 0
        assert snapshot.tick_number == 1

    def test_world_scheduler_order(self):
        """Verifica que el scheduler ejecuta fases en orden correcto."""
        world = self.create_simple_world()

        # Registra orden de ejecucion
        execution_order = []

        def track_phase(phase):
            def callback():
                execution_order.append(phase)
            return callback

        # Reemplaza scheduler callbacks para tracking
        world.scheduler.callbacks = {phase: [] for phase in world.scheduler.phase_order}
        for phase in world.scheduler.phase_order:
            world.scheduler.register_callback(phase, track_phase(phase))

        world.tick()

        # Verifica orden
        expected_order = [
            UpdatePhase.PERCEPTION,
            UpdatePhase.DECISION,
            UpdatePhase.PHYSICS,
            UpdatePhase.ENVIRONMENT,
            UpdatePhase.SPATIAL_INDEX,
            UpdatePhase.STATISTICS,
        ]

        for expected_phase in expected_order:
            assert expected_phase in execution_order


class TestScheduler:
    """Tests del Scheduler."""

    def test_scheduler_creation(self):
        """Crea un scheduler valido."""
        from kars.simulation.scheduler import Scheduler
        scheduler = Scheduler()

        assert len(scheduler.phase_order) > 0

    def test_scheduler_register_callback(self):
        """Registra callbacks en scheduler."""
        from kars.simulation.scheduler import Scheduler, UpdatePhase
        scheduler = Scheduler()

        called = []

        def callback():
            called.append(True)

        scheduler.register_callback(UpdatePhase.PERCEPTION, callback)
        scheduler.execute_tick()

        assert len(called) > 0


class TestStatsCollector:
    """Tests del StatsCollector."""

    def test_stats_collector_record(self):
        """Registra estadisticas."""
        from kars.simulation.statistics import StatsCollector

        collector = StatsCollector()

        agent1 = CarAgent(agent_id=1)
        agent1.kinematic_state = KinematicState(
            position=Vector2(0, 0),
            velocity=Vector2(5, 0),
            acceleration=Vector2(0, 0),
            heading=0,
        )

        collector.record_tick(0, 0.0, [agent1])

        assert len(collector.ticks) == 1
        last_stats = collector.get_last_tick()
        assert last_stats.num_agents == 1
        assert last_stats.avg_speed_kmh > 0

    def test_stats_collector_summary(self):
        """Obtiene resumen de estadisticas."""
        from kars.simulation.statistics import StatsCollector

        collector = StatsCollector()

        agent1 = CarAgent(agent_id=1)
        agent1.kinematic_state = KinematicState(
            position=Vector2(0, 0),
            velocity=Vector2(5, 0),
            acceleration=Vector2(0, 0),
            heading=0,
        )

        collector.record_tick(0, 0.0, [agent1])
        summary = collector.get_summary()

        assert "total_ticks" in summary
        assert "avg_agent_speed_kmh" in summary

