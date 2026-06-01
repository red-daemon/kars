"""Validate that grid calibration shows correct world coordinates with HUD banners."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import unittest
from kars.rendering.camera import Camera
from kars.physics.models import Vector2
import kars.config as config


class TestViewportGridCalibration(unittest.TestCase):
    """Test viewport coordinate transformation accounting for HUD banners."""

    def setUp(self):
        """Set up camera with drawable area."""
        self.camera = Camera(
            window_width_px=config.WINDOW_WIDTH_PX,
            window_height_px=config.WINDOW_HEIGHT_PX,
            scale_px_per_m=config.SCALE_PX_PER_M,
            drawable_top_y_px=config.HUD_TOP_HEIGHT,
            drawable_height_px=config.WINDOW_HEIGHT_PX - config.HUD_TOP_HEIGHT - config.HUD_BAR_HEIGHT
        )

    def test_grid_calibration_zoom_1_centered_at_origin(self):
        """At zoom 1.0, centered at (0,0), viewport should show correct bounds."""
        self.camera.set_zoom(1.0)
        self.camera.center_on(Vector2(0.0, 0.0))

        x_min, y_min, x_max, y_max = self.camera.get_visible_world_bounds()

        # X range should be ±60m (1200px / 10px/m = 120m width, ±60m from center)
        self.assertAlmostEqual(x_min, -60.0, places=1)
        self.assertAlmostEqual(x_max, 60.0, places=1)

        # Y range should be ±31.25m (625px / 10px/m = 62.5m height, ±31.25m from center)
        # Note: 625px = 800px total - 120px top banner - 55px bottom banner
        self.assertAlmostEqual(y_min, -31.25, places=1)
        self.assertAlmostEqual(y_max, 31.25, places=1)

    def test_screen_to_world_center_maps_to_origin(self):
        """Screen center should map to world origin (0, 0)."""
        self.camera.set_zoom(1.0)
        self.camera.center_on(Vector2(0.0, 0.0))

        screen_center_x = config.WINDOW_WIDTH_PX / 2.0
        screen_center_y = self.camera.drawable_center_y_px

        world_pos = self.camera.screen_to_world((screen_center_x, screen_center_y))

        self.assertAlmostEqual(world_pos.x, 0.0, places=2)
        self.assertAlmostEqual(world_pos.y, 0.0, places=2)

    def test_world_corners_map_to_screen_edges(self):
        """World corners should map to drawable screen edges."""
        self.camera.set_zoom(1.0)
        self.camera.center_on(Vector2(0.0, 0.0))

        # Note: In world coords, +Y is UP. In screen coords, +Y is DOWN.
        # Visible world range at zoom 1.0 centered at (0,0): X: [-60, 60], Y: [-31.25, 31.25]
        # World y = -31.25 is visually at the TOP of the viewport
        # World y = +31.25 is visually at the BOTTOM of the viewport

        # Top of viewport (world y = -31.25, screen should be at drawable top)
        screen_at_world_top = self.camera.world_to_screen(Vector2(-60, -31.25))
        self.assertAlmostEqual(screen_at_world_top[0], 0.0, places=0)
        self.assertAlmostEqual(screen_at_world_top[1], config.HUD_TOP_HEIGHT, places=0)

        # Bottom of viewport (world y = +31.25, screen should be at drawable bottom)
        screen_at_world_bottom = self.camera.world_to_screen(Vector2(60, 31.25))
        drawable_bottom = config.HUD_TOP_HEIGHT + (config.WINDOW_HEIGHT_PX - config.HUD_TOP_HEIGHT - config.HUD_BAR_HEIGHT)
        self.assertAlmostEqual(screen_at_world_bottom[0], config.WINDOW_WIDTH_PX, places=0)
        self.assertAlmostEqual(screen_at_world_bottom[1], drawable_bottom, places=0)

    def test_drawable_area_calculations(self):
        """Verify drawable area accounting."""
        expected_top = config.HUD_TOP_HEIGHT
        expected_height = config.WINDOW_HEIGHT_PX - config.HUD_TOP_HEIGHT - config.HUD_BAR_HEIGHT
        expected_center = expected_top + expected_height / 2.0

        self.assertEqual(self.camera.drawable_top_y_px, expected_top)
        self.assertEqual(self.camera.drawable_height_px, expected_height)
        self.assertAlmostEqual(self.camera.drawable_center_y_px, expected_center, places=1)


if __name__ == '__main__':
    unittest.main()
