"""Cámara: convierte coordenadas del mundo (metros) a pantalla (píxeles)."""

from kars.physics.models import Vector2
import kars.config as config


class Camera:
    """Gestiona viewport y transformación de coordenadas."""

    def __init__(
        self,
        window_width_px: int = config.WINDOW_WIDTH_PX,
        window_height_px: int = config.WINDOW_HEIGHT_PX,
        scale_px_per_m: float = config.SCALE_PX_PER_M,
    ):
        """Inicializa cámara."""
        self.window_width_px = window_width_px
        self.window_height_px = window_height_px
        self.base_scale = scale_px_per_m

        # Estado del viewport
        self.zoom = 1.0
        self.offset_x_m = 0.0
        self.offset_y_m = 0.0

    @property
    def scale_px_per_m(self) -> float:
        """Escala actual incluyendo zoom."""
        return self.base_scale * self.zoom

    def world_to_screen(self, world_pos_m: Vector2) -> tuple:
        """Convierte posición del mundo (metros) a pantalla (píxeles)."""
        rel_x = world_pos_m.x - self.offset_x_m
        rel_y = world_pos_m.y - self.offset_y_m

        screen_x = rel_x * self.scale_px_per_m + self.window_width_px / 2.0
        screen_y = rel_y * self.scale_px_per_m + self.window_height_px / 2.0

        return (screen_x, screen_y)

    def screen_to_world(self, screen_pos_px: tuple) -> Vector2:
        """Convierte coordenadas de pantalla (píxeles) a mundo (metros)."""
        screen_x, screen_y = screen_pos_px

        rel_x = (screen_x - self.window_width_px / 2.0) / self.scale_px_per_m
        rel_y = (screen_y - self.window_height_px / 2.0) / self.scale_px_per_m

        world_x = rel_x + self.offset_x_m
        world_y = rel_y + self.offset_y_m

        return Vector2(world_x, world_y)

    def set_zoom(self, zoom_level: float):
        """Establece nivel de zoom (1.0 = sin zoom, > 1.0 = acercado)."""
        self.zoom = max(0.1, zoom_level)

    def pan(self, delta_x_m: float, delta_y_m: float):
        """Desplaza cámara por metros del mundo."""
        self.offset_x_m += delta_x_m
        self.offset_y_m += delta_y_m

    def center_on(self, world_pos_m: Vector2):
        """Centra cámara en una posición del mundo."""
        self.offset_x_m = world_pos_m.x
        self.offset_y_m = world_pos_m.y

    def get_visible_world_bounds(self) -> tuple:
        """Obtiene límites (min_x, min_y, max_x, max_y) visibles en el mundo."""
        top_left = self.screen_to_world((0, 0))
        bottom_right = self.screen_to_world((self.window_width_px, self.window_height_px))

        return (top_left.x, top_left.y, bottom_right.x, bottom_right.y)
