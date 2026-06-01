#!/usr/bin/env python3
"""
Test script to verify margin rendering with pixel-based width constraints.
Renders a single frame to PNG for visual inspection.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pygame
import json
from pathlib import Path
from kars.config import *
from kars.simulation.scene_loader import SceneLoader
from kars.rendering.renderer import Renderer
from kars.rendering.camera import Camera
from kars.physics.models import Vector2

# Load test scenario
scenario_path = Path(__file__).parent / "scenarios" / "test_three_roads_render.json"
print(f"Loading scenario: {scenario_path}")

with open(scenario_path) as f:
    scenario_data = json.load(f)

# Create world from scenario
from kars.simulation.world import World
loader = SceneLoader()
world = loader.load_scene(scenario_data)

print(f"Loaded world with {len(world.agents)} agents")
print(f"Roads: {world.network.num_roads()}")
print(f"Segments: {sum(r.num_segments() for r in world.network.get_all_roads())}")

# Initialize pygame for rendering
pygame.init()
pygame.display.set_mode((1200, 900))
pygame.display.set_caption("KARS - Margin Rendering Test")

# Create renderer
renderer = Renderer(1200, 900)
renderer.camera_config = {
    'viewport_x_min_m': -5,
    'viewport_x_max_m': 105,
    'viewport_y_min_m': -45,
    'viewport_y_max_m': 45,
}

# Run one tick to initialize viewport
world.tick()
snapshot = world.build_render_snapshot()

# Initialize viewport with correct camera settings
from kars.rendering.viewport_manager import ViewportManager
renderer.viewport = ViewportManager(renderer.camera_config)

# Render the frame
print("\nRendering frame...")
renderer.run_frame(world)

# Save screenshot
output_path = Path(__file__).parent / "margin_test_screenshot.png"
pygame.image.save(renderer.screen, str(output_path))
print(f"Saved screenshot to: {output_path}")

# Print rendering info
print(f"\nRendering info:")
print(f"  Screen size: {renderer.width_px}x{renderer.height_px}")
print(f"  Camera zoom: {renderer.viewport.camera.zoom:.2f}x")
print(f"  SCALE_PX_PER_M: {SCALE_PX_PER_M}")
print(f"  LANE_MARKING_WIDTH_M: {LANE_MARKING_WIDTH_M}")
print(f"  LANE_MARKING_MIN_WIDTH_PX: {LANE_MARKING_MIN_WIDTH_PX}")
print(f"  ROAD_MARGIN_WIDTH_M: {ROAD_MARGIN_WIDTH_M}")

pygame.quit()
print("\nDone!")
