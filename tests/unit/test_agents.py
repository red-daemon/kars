"""Tests unitarios para Perception, CarAgent, SpatialGrid."""

import math
from kars.physics.models import Vector2, KinematicState, PhysicsBody, Waypoint
from kars.agents.perception import PerceptionData, PerceptionModule
from kars.agents.car_agent import CarAgent
from kars.agents.behaviors.idm import IDMBehavior
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.utils.spatial_index import SpatialGrid
import kars.config as config


class TestPerceptionData:
    """Tests de PerceptionData."""

    def test_perception_data_creation(self):
        """Crea PerceptionData valida."""
        perc = PerceptionData(
            leader_distance_m=50.0,
            leader_speed_ms=5.0,
            follower_distance_m=30.0,
            follower_speed_ms=4.0,
            speed_limit_kmh=20.0,
            current_lane_id="lane_0",
        )

        assert perc.leader_distance_m == 50.0
        assert perc.leader_speed_ms == 5.0

    def test_perception_data_validates_negative_distance(self):
        """PerceptionData rechaza distancia negativa."""
        try:
            PerceptionData(
                leader_distance_m=-10.0,
                leader_speed_ms=5.0,
                follower_distance_m=30.0,
                follower_speed_ms=4.0,
                speed_limit_kmh=20.0,
                current_lane_id="lane_0",
            )
            assert False, "Deberia haber lanzado ValueError"
        except ValueError:
            pass


class TestPerceptionModule:
    """Tests del modulo de percepcion."""

    def test_perception_no_other_agents(self):
        """Percepcion con ningun otro agente visible."""
        # Crea red simple
        lane = Lane(
            lane_id="lane_0",
            waypoints=[Waypoint(Vector2(0, 0), heading=0), Waypoint(Vector2(500, 0), heading=0)],
        )
        network = RoadNetwork()
        segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(500, 0))
        network.add_segment(segment)

        # Percepcion del agente 1 (sin otros agentes)
        perception = PerceptionModule.compute(
            agent_id=1,
            agent_s=100.0,
            agent_lane_id="lane_0",
            agent_speed_ms=5.0,
            other_agents={},  # Vacio
            network=network,
        )

        assert perception.leader_distance_m == float("inf")
        assert perception.follower_distance_m == float("inf")
        assert abs(perception.speed_limit_kmh - 20.0) < 1e-6

    def test_perception_leader_ahead(self):
        """Percibe un carro adelante en el mismo carril."""
        lane = Lane(
            lane_id="lane_0",
            waypoints=[Waypoint(Vector2(0, 0), heading=0), Waypoint(Vector2(500, 0), heading=0)],
        )
        network = RoadNetwork()
        segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(500, 0))
        network.add_segment(segment)

        other_agents = {
            2: ("lane_0", 150.0, 5.0),  # Agente 2 adelante a 150m
        }

        perception = PerceptionModule.compute(
            agent_id=1,
            agent_s=100.0,
            agent_lane_id="lane_0",
            agent_speed_ms=4.0,
            other_agents=other_agents,
            network=network,
        )

        # Brecha = 150 - 100 = 50m
        assert abs(perception.leader_distance_m - 50.0) < 1e-6
        assert abs(perception.leader_speed_ms - 5.0) < 1e-6

    def test_perception_follower_behind(self):
        """Percibe un carro atras en el mismo carril."""
        lane = Lane(
            lane_id="lane_0",
            waypoints=[Waypoint(Vector2(0, 0), heading=0), Waypoint(Vector2(500, 0), heading=0)],
        )
        network = RoadNetwork()
        segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(500, 0))
        network.add_segment(segment)

        other_agents = {
            2: ("lane_0", 50.0, 4.0),  # Agente 2 atras a 50m
        }

        perception = PerceptionModule.compute(
            agent_id=1,
            agent_s=100.0,
            agent_lane_id="lane_0",
            agent_speed_ms=5.0,
            other_agents=other_agents,
            network=network,
        )

        # Brecha = 100 - 50 = 50m
        assert abs(perception.follower_distance_m - 50.0) < 1e-6
        assert abs(perception.follower_speed_ms - 4.0) < 1e-6

    def test_perception_ignores_different_lane(self):
        """No percibe carros en carril diferente (MVP)."""
        lane0 = Lane(
            lane_id="lane_0",
            waypoints=[Waypoint(Vector2(0, 0), heading=0), Waypoint(Vector2(500, 0), heading=0)],
        )
        lane1 = Lane(
            lane_id="lane_1",
            waypoints=[Waypoint(Vector2(0, 5), heading=0), Waypoint(Vector2(500, 5), heading=0)],
        )
        network = RoadNetwork()
        segment = RoadSegment("seg_0", [lane0, lane1], Vector2(0, 0), Vector2(500, 0))
        network.add_segment(segment)

        other_agents = {
            2: ("lane_1", 150.0, 5.0),  # En carril diferente
        }

        perception = PerceptionModule.compute(
            agent_id=1,
            agent_s=100.0,
            agent_lane_id="lane_0",
            agent_speed_ms=4.0,
            other_agents=other_agents,
            network=network,
        )

        # No debe percibir el carro en carril diferente
        assert perception.leader_distance_m == float("inf")


class TestCarAgent:
    """Tests de CarAgent."""

    def test_car_agent_creation(self):
        """Crea un CarAgent valido."""
        agent = CarAgent(
            agent_id=100,
            current_lane_id="lane_0",
            position_along_lane_s=50.0,
            lateral_offset=0.0,
        )

        assert agent.agent_id == 100
        assert agent.current_lane_id == "lane_0"
        assert agent.position_along_lane_s == 50.0

    def test_car_agent_desired_speed_with_tolerance(self):
        """Velocidad deseada incluye tolerancia individual."""
        agent = CarAgent(
            agent_id=100,
            speed_tolerance_kmh=2.0,  # +2 km/h
        )

        # IDM tiene velocidad deseada de 20 km/h (config.IDM_DESIRED_SPEED_MS * 3.6)
        base_speed_kmh = config.IDM_DESIRED_SPEED_MS * 3.6
        expected_speed_kmh = base_speed_kmh + 2.0

        actual_speed_ms = agent.get_desired_speed_ms()
        actual_speed_kmh = actual_speed_ms * 3.6

        assert abs(actual_speed_kmh - expected_speed_kmh) < 1e-3

    def test_car_agent_decide_free_flow(self):
        """Agente acelera en flujo libre (sin lider)."""
        agent = CarAgent(agent_id=100)

        # Simulamos percepcion: sin lider
        perception = PerceptionData(
            leader_distance_m=float("inf"),
            leader_speed_ms=config.IDM_DESIRED_SPEED_MS,
            follower_distance_m=float("inf"),
            follower_speed_ms=0.0,
            speed_limit_kmh=20.0,
            current_lane_id="lane_0",
        )

        # Agente parado
        agent.kinematic_state = KinematicState(
            position=Vector2(0, 0),
            velocity=Vector2(0, 0),
            acceleration=Vector2(0, 0),
            heading=0,
        )

        accel = agent.decide(perception)

        # Debe acelerar hacia velocidad deseada
        assert accel > 0.5  # Aceleracion positiva significativa

    def test_car_agent_decide_braking(self):
        """Agente frena si hay carro muy cercano adelante."""
        agent = CarAgent(agent_id=100)

        # Simulamos percepcion: lider muy cercano (1m)
        perception = PerceptionData(
            leader_distance_m=1.0,  # Muy cercano
            leader_speed_ms=0.0,     # Estatico
            follower_distance_m=float("inf"),
            follower_speed_ms=0.0,
            speed_limit_kmh=20.0,
            current_lane_id="lane_0",
        )

        # Agente a velocidad alta
        agent.kinematic_state = KinematicState(
            position=Vector2(0, 0),
            velocity=Vector2(5.0, 0),  # 5 m/s = 18 km/h
            acceleration=Vector2(0, 0),
            heading=0,
        )

        accel = agent.decide(perception)

        # Debe frenar
        assert accel < -0.5

    def test_car_agent_repr(self):
        """Representacion de debug de CarAgent."""
        agent = CarAgent(
            agent_id=100,
            current_lane_id="lane_0",
            position_along_lane_s=50.0,
        )

        repr_str = repr(agent)
        assert "100" in repr_str
        assert "lane_0" in repr_str


class TestSpatialGrid:
    """Tests del indice espacial."""

    def test_spatial_grid_creation(self):
        """Crea SpatialGrid valido."""
        grid = SpatialGrid(cell_size_m=30.0)
        assert grid.cell_size_m == 30.0

    def test_spatial_grid_insert_and_query(self):
        """Inserta agentes y consulta por posicion."""
        grid = SpatialGrid(cell_size_m=30.0)

        # Inserta agentes en posiciones conocidas
        grid.insert(1, Vector2(5.0, 5.0))      # Celda (0, 0)
        grid.insert(2, Vector2(35.0, 5.0))     # Celda (1, 0)
        grid.insert(3, Vector2(5.0, 35.0))     # Celda (0, 1)

        # Consulta agentes cerca de (10, 10) - debe encontrar el agente 1
        neighbors = grid.query_neighbors(Vector2(10.0, 10.0), radius_m=20.0)

        assert 1 in neighbors

    def test_spatial_grid_clear(self):
        """Limpia el grid."""
        grid = SpatialGrid(cell_size_m=30.0)
        grid.insert(1, Vector2(5.0, 5.0))

        assert len(grid.get_all_agents()) == 1

        grid.clear()

        assert len(grid.get_all_agents()) == 0

    def test_spatial_grid_cell_key_calculation(self):
        """Calcula correctamente las claves de celda."""
        grid = SpatialGrid(cell_size_m=30.0)

        # (0, 0) debe ir a celda (0, 0)
        cell_key = grid._get_cell_key(Vector2(0, 0))
        assert cell_key == (0, 0)

        # (5, 5) debe ir a celda (0, 0)
        cell_key = grid._get_cell_key(Vector2(5, 5))
        assert cell_key == (0, 0)

        # (35, 5) debe ir a celda (1, 0)
        cell_key = grid._get_cell_key(Vector2(35, 5))
        assert cell_key == (1, 0)

        # (-5, -5) debe ir a celda (-1, -1)
        cell_key = grid._get_cell_key(Vector2(-5, -5))
        assert cell_key == (-1, -1)

    def test_spatial_grid_query_cell_neighbors(self):
        """Consulta agentes en la misma celda."""
        grid = SpatialGrid(cell_size_m=30.0)

        grid.insert(1, Vector2(5.0, 5.0))
        grid.insert(2, Vector2(10.0, 10.0))   # Misma celda que 1
        grid.insert(3, Vector2(40.0, 40.0))   # Celda diferente

        # Consulta en celda del agente 1
        neighbors = grid.query_cell_neighbors(Vector2(7.0, 7.0))

        assert 1 in neighbors
        assert 2 in neighbors
        assert 3 not in neighbors

    def test_spatial_grid_stats(self):
        """Obtiene estadisticas del grid."""
        grid = SpatialGrid(cell_size_m=30.0)

        grid.insert(1, Vector2(5.0, 5.0))
        grid.insert(2, Vector2(10.0, 10.0))
        grid.insert(3, Vector2(40.0, 40.0))

        stats = grid.get_stats()

        assert stats["total_agents"] == 3
        assert stats["total_cells"] == 2  # Una celda con 2 agentes, otra con 1

