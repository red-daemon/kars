"""Tests unitarios para Lane (sin pytest)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import math
from kars.physics.models import Vector2, Waypoint
from kars.environment.lane import Lane


def approx(value, abs_tol=1e-6):
    """Retorna value (para compatibilidad con pytest style)."""
    return value


class TestLaneGeometry:
    """Tests de geometría de carriles."""

    def test_lane_creation_simple_straight(self):
        """Un carril recto horizontal."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=0)

        lane = Lane(
            lane_id="test_lane_0",
            waypoints=[wp0, wp1],
            width_m=2.7,
            speed_limit_kmh=20.0,
        )

        assert lane.lane_id == "test_lane_0"
        assert abs(lane.length_m() - 100.0) < 1e-6
        assert lane.width_m == 2.7

    def test_lane_position_at_start(self):
        """Posición en s=0 debe ser el primer waypoint."""
        wp0 = Waypoint(Vector2(10, 20), heading=0)
        wp1 = Waypoint(Vector2(50, 20), heading=0)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
        )

        pos = lane.position_at(0)
        assert abs(pos.x - 10) < 1e-6
        assert abs(pos.y - 20) < 1e-6

    def test_lane_position_at_end(self):
        """Posición en s=length debe ser el último waypoint."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=0)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
        )

        pos = lane.position_at(100.0)
        assert abs(pos.x - 100) < 1e-6
        assert abs(pos.y - 0) < 1e-6

    def test_lane_position_at_midpoint(self):
        """Posición en mitad del carril (interpolación lineal)."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=0)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
        )

        pos = lane.position_at(50.0)
        assert abs(pos.x - 50) < 1e-6
        assert abs(pos.y - 0) < 1e-6

    def test_lane_position_clamped_beyond_end(self):
        """Posición más allá del fin se clampea al fin."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=0)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
        )

        pos = lane.position_at(500.0)
        assert abs(pos.x - 100) < 1e-6
        assert abs(pos.y - 0) < 1e-6

    def test_lane_position_negative_clamped(self):
        """Posición negativa se clampea a inicio."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=0)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
        )

        pos = lane.position_at(-50.0)
        assert abs(pos.x - 0) < 1e-6
        assert abs(pos.y - 0) < 1e-6

    def test_lane_heading_at_straight(self):
        """Heading en carril recto horizontal."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=0)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
        )

        heading = lane.heading_at(50)
        assert abs(heading - 0) < 1e-6

    def test_lane_heading_at_vertical(self):
        """Heading en carril vertical."""
        wp0 = Waypoint(Vector2(0, 0), heading=math.pi / 2)
        wp1 = Waypoint(Vector2(0, 100), heading=math.pi / 2)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
        )

        heading = lane.heading_at(50)
        assert abs(heading - math.pi / 2) < 1e-6

    def test_lane_length_multiple_segments(self):
        """Longitud de carril con 3 waypoints."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=math.pi / 2)
        wp2 = Waypoint(Vector2(100, 100), heading=math.pi / 2)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1, wp2],
        )

        assert abs(lane.length_m() - 200) < 1e-6

    def test_lane_position_at_second_segment(self):
        """Posición en segundo segmento (interpolación en wp1-wp2)."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=math.pi / 2)
        wp2 = Waypoint(Vector2(100, 100), heading=math.pi / 2)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1, wp2],
        )

        pos = lane.position_at(150)
        assert abs(pos.x - 100) < 1e-6
        assert abs(pos.y - 50) < 1e-6


class TestLaneNormal:
    """Tests de dirección normal al carril."""

    def test_normal_direction_horizontal_lane(self):
        """Normal a carril horizontal apunta arriba (90 grados)."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=0)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
        )

        normal = lane.normal_direction_at(50)
        assert abs(normal.x - 0) < 1e-6
        assert abs(normal.y - 1) < 1e-6

    def test_normal_direction_vertical_lane(self):
        """Normal a carril vertical apunta derecha."""
        wp0 = Waypoint(Vector2(0, 0), heading=math.pi / 2)
        wp1 = Waypoint(Vector2(0, 100), heading=math.pi / 2)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
        )

        normal = lane.normal_direction_at(50)
        assert abs(normal.x - (-1)) < 1e-6
        assert abs(normal.y - 0) < 1e-6


class TestLaneOffset:
    """Tests de offset lateral (para cambio de carril Fase 2)."""

    def test_clamp_lateral_offset_center(self):
        """Offset en centro (0) se mantiene."""
        lane = Lane(
            lane_id="test_lane",
            waypoints=[
                Waypoint(Vector2(0, 0), heading=0),
                Waypoint(Vector2(100, 0), heading=0),
            ],
            width_m=2.0,
        )

        clamped = lane.clamp_lateral_offset(0)
        assert abs(clamped - 0) < 1e-9

    def test_clamp_lateral_offset_within_bounds(self):
        """Offset dentro de límites se mantiene."""
        lane = Lane(
            lane_id="test_lane",
            waypoints=[
                Waypoint(Vector2(0, 0), heading=0),
                Waypoint(Vector2(100, 0), heading=0),
            ],
            width_m=2.0,
        )

        clamped = lane.clamp_lateral_offset(0.5)
        assert abs(clamped - 0.5) < 1e-9

    def test_clamp_lateral_offset_beyond_limit(self):
        """Offset más allá de límite se clampea."""
        lane = Lane(
            lane_id="test_lane",
            waypoints=[
                Waypoint(Vector2(0, 0), heading=0),
                Waypoint(Vector2(100, 0), heading=0),
            ],
            width_m=2.0,
        )

        clamped = lane.clamp_lateral_offset(5.0)
        assert abs(clamped - 1.0) < 1e-9

    def test_world_position_with_lateral_offset(self):
        """Posición mundo con offset lateral."""
        wp0 = Waypoint(Vector2(0, 0), heading=0)
        wp1 = Waypoint(Vector2(100, 0), heading=0)

        lane = Lane(
            lane_id="test_lane",
            waypoints=[wp0, wp1],
            width_m=2.0,
        )

        world_pos = lane.world_position_at(s=50, lateral_offset=0.5)
        assert abs(world_pos.x - 50) < 1e-6
        assert abs(world_pos.y - 0.5) < 1e-6


class TestLaneValidation:
    """Tests de validación de Lane."""

    def test_lane_requires_minimum_two_waypoints(self):
        """Lane necesita al menos 2 waypoints."""
        try:
            Lane(
                lane_id="invalid",
                waypoints=[Waypoint(Vector2(0, 0), heading=0)],
            )
            assert False, "Debería haber lanzado ValueError"
        except ValueError:
            pass  # Esperado

    def test_lane_defaults_from_config(self):
        """Lane sin especificar width/speed_limit usa defaults de config."""
        lane = Lane(
            lane_id="test_lane",
            waypoints=[
                Waypoint(Vector2(0, 0), heading=0),
                Waypoint(Vector2(100, 0), heading=0),
            ],
        )

        import kars.config as config

        assert abs(lane.width_m - config.LANE_WIDTH_M) < 1e-6
        assert abs(lane.speed_limit_kmh - config.MAX_SPEED_KMH) < 1e-6

    def test_lane_custom_values_override_defaults(self):
        """Lane con valores explícitos overrridea defaults."""
        lane = Lane(
            lane_id="test_lane",
            waypoints=[
                Waypoint(Vector2(0, 0), heading=0),
                Waypoint(Vector2(100, 0), heading=0),
            ],
            width_m=3.5,
            speed_limit_kmh=50.0,
        )

        assert abs(lane.width_m - 3.5) < 1e-6
        assert abs(lane.speed_limit_kmh - 50.0) < 1e-6

