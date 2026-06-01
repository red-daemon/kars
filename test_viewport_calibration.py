"""Test viewport calibration with HUD banners."""

import sys
sys.path.insert(0, '.')

from kars.rendering.camera import Camera
from kars.physics.models import Vector2
import kars.config as config

# Create camera with drawable area accounting for HUD banners
camera = Camera(
    window_width_px=config.WINDOW_WIDTH_PX,  # 1200
    window_height_px=config.WINDOW_HEIGHT_PX,  # 800
    scale_px_per_m=config.SCALE_PX_PER_M,  # 10.0
    drawable_top_y_px=config.HUD_TOP_HEIGHT,  # 120
    drawable_height_px=config.WINDOW_HEIGHT_PX - config.HUD_TOP_HEIGHT - config.HUD_BAR_HEIGHT  # 625
)

# Test 1: Center at (0, 0), zoom 1.0 should show -60 to +60 in X, -40 to +40 in Y
print("=" * 60)
print("TEST 1: Grid Calibration - Zoom 1.0, Center (0,0)")
print("=" * 60)

camera.set_zoom(1.0)
camera.center_on(Vector2(0.0, 0.0))

bounds = camera.get_visible_world_bounds()
x_min, y_min, x_max, y_max = bounds

print(f"Visible world bounds:")
print(f"  X: {x_min:.2f} to {x_max:.2f} m (expected: -60 to +60)")
print(f"  Y: {y_min:.2f} to {y_max:.2f} m (expected: -40 to +40)")

# Verify drawable area calculation
print(f"\nDrawable area:")
print(f"  Top Y: {camera.drawable_top_y_px} px")
print(f"  Height: {camera.drawable_height_px} px")
print(f"  Center Y: {camera.drawable_center_y_px} px")

print(f"\n" + "=" * 60)
print("TEST 2: Screen-to-World Conversion")
print("=" * 60)

# Screen center (accounting for drawable area offset)
screen_center_x = config.WINDOW_WIDTH_PX / 2.0  # 600
screen_center_y = camera.drawable_center_y_px  # Should be 120 + 625/2 = 432.5

world_center = camera.screen_to_world((screen_center_x, screen_center_y))
print(f"Screen center ({screen_center_x:.1f}, {screen_center_y:.1f}) → World ({world_center.x:.2f}, {world_center.y:.2f})")
print(f"Expected: (0.0, 0.0)")

# Test 3: Convert world corners to screen
print(f"\n" + "=" * 60)
print("TEST 3: World-to-Screen Conversion")
print("=" * 60)

# World corners should map to screen edges (accounting for drawable area)
world_top_left = Vector2(-60, 40)
world_bottom_right = Vector2(60, -40)

screen_tl = camera.world_to_screen(world_top_left)
screen_br = camera.world_to_screen(world_bottom_right)

print(f"World (-60, 40) → Screen ({screen_tl[0]:.1f}, {screen_tl[1]:.1f})")
print(f"Expected screen: (0, 120) [drawable top edge]")

print(f"World (60, -40) → Screen ({screen_br[0]:.1f}, {screen_br[1]:.1f})")
print(f"Expected screen: (1200, 745) [drawable bottom edge]")

print("\n✓ All calibration tests complete!")
