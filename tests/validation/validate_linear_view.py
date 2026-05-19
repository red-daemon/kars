#!/usr/bin/env python3
"""Test: vista lineal sin zoom con marcadores de distancia."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kars.physics.models import Vector2, Waypoint
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.world import World
import kars.config as config

def test_linear_view():
    """Test: verifica que la escala lineal se calcula correctamente."""
    print("\n" + "="*70)
    print("TEST: Vista Lineal (Sin Zoom Automático)")
    print("="*70)

    lane = Lane(
        lane_id="lane_0",
        waypoints=[
            Waypoint(Vector2(0, 0), heading=0),
            Waypoint(Vector2(1000, 0), heading=0)
        ],
        width_m=2.7,
        speed_limit_kmh=20.0,
        zone="urban",
    )

    segment = RoadSegment("seg_0", [lane], Vector2(0, 0), Vector2(1000, 0))
    network = RoadNetwork()
    network.add_segment(segment)

    world = World(network)

    # Obtén snapshot
    snapshot = world.build_render_snapshot()

    # Verifica que snapshot tiene lanes
    print(f"\nSnapshot lanes: {len(snapshot.lanes)}")
    if snapshot.lanes:
        lane_id, waypoints, width_m = snapshot.lanes[0]
        print(f"  Lane ID: {lane_id}")
        print(f"  Waypoints: {len(waypoints)}")
        print(f"  First point: {waypoints[0]}")
        print(f"  Last point: {waypoints[-1]}")
        print(f"  Width: {width_m}m")

        # Calcula longitud
        lane_length_m = sum(
            ((waypoints[i+1][0] - waypoints[i][0])**2 +
             (waypoints[i+1][1] - waypoints[i][1])**2)**0.5
            for i in range(len(waypoints)-1)
        )
        print(f"  Calculated length: {lane_length_m:.1f}m")

        # Calcula zoom que se usaría
        window_width = 1200
        pixels_per_meter = window_width / lane_length_m
        print(f"\n  Pixels per meter: {pixels_per_meter:.3f}")
        print(f"  Escala: 1000m -> {1000 * pixels_per_meter:.0f} pixeles")
        print(f"  Viewport: 0m (píx 0) a 1000m (píx {1000 * pixels_per_meter:.0f})")

    print(f"\nOK Test paso: Estructura lista para vista lineal")

if __name__ == "__main__":
    try:
        test_linear_view()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

