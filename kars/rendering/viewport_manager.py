"""ViewportManager: Cámara extendida con follow mode y controles interactivos."""

from typing import Optional
from kars.physics.models import Vector2
from kars.rendering.camera import Camera
from kars.simulation.world import RenderSnapshot


class ViewportManager:
    """Gestiona la cámara con capacidades extendidas: follow mode, zoom, pan."""

    def __init__(self, camera: Camera):
        """Inicializa el gestor de viewport.

        Args:
            camera: Camera instance a controlar
        """
        self.camera = camera
        self.follow_agent_id: Optional[int] = None

    def update(self, snapshot: RenderSnapshot, agents_dict: dict) -> None:
        """Actualiza viewport cada frame (sigue al agente si está activo).

        Args:
            snapshot: RenderSnapshot con datos de renderizado
            agents_dict: Dict de agentes para buscar el agent_id
        """
        if self.follow_agent_id is not None and self.follow_agent_id in agents_dict:
            agent = agents_dict[self.follow_agent_id]
            # Centra cámara en la posición del agente seguido
            self.camera.center_on(agent.kinematic_state.position)

    def handle_mouse_wheel(self, delta: int) -> None:
        """Maneja zoom con rueda del mouse.

        Args:
            delta: >0 para zoom in, <0 para zoom out
        """
        zoom_factor = 1.2 if delta > 0 else 1.0 / 1.2
        self.camera.set_zoom(self.camera.zoom * zoom_factor)

    def handle_mouse_drag(self, dx: float, dy: float) -> None:
        """Maneja pan con mouse (middle button).

        Args:
            dx: Desplazamiento en x (píxeles → metros)
            dy: Desplazamiento en y (píxeles → metros)
        """
        # Convierte píxeles a metros usando escala actual
        delta_x_m = -dx / self.camera.scale_px_per_m
        delta_y_m = -dy / self.camera.scale_px_per_m
        self.camera.pan(delta_x_m, delta_y_m)

    def zoom_to_fit(self, min_x: float, min_y: float, max_x: float, max_y: float) -> None:
        """Ajusta zoom para encajar el área especificada en la pantalla.

        Args:
            min_x, min_y, max_x, max_y: Bounds del mundo (metros) a encajar
        """
        world_width = max_x - min_x
        world_height = max_y - min_y

        window_w = self.camera.window_width_px
        window_h = self.camera.window_height_px

        # Calcula zoom necesario en ambos ejes
        zoom_x = window_w / (world_width * self.camera.base_scale)
        zoom_y = window_h / (world_height * self.camera.base_scale)

        # Usa el menor zoom para encajar todo
        new_zoom = min(zoom_x, zoom_y) * 0.95  # 5% margen
        self.camera.set_zoom(max(0.1, new_zoom))

        # Centra en el medio del área
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        self.camera.center_on(Vector2(center_x, center_y))

    def start_follow(self, agent_id: int) -> None:
        """Comienza a seguir un agente.

        Args:
            agent_id: ID del agente a seguir
        """
        self.follow_agent_id = agent_id

    def stop_follow(self) -> None:
        """Detiene el seguimiento de agente."""
        self.follow_agent_id = None

    def world_to_screen(self, world_pos: Vector2) -> tuple:
        """Convierte coordenadas del mundo a pantalla.

        Args:
            world_pos: Posición en metros (mundo)

        Returns:
            (screen_x, screen_y) en píxeles
        """
        return self.camera.world_to_screen(world_pos)

    def screen_to_world(self, screen_pos: tuple) -> Vector2:
        """Convierte coordenadas de pantalla a mundo.

        Args:
            screen_pos: (screen_x, screen_y) en píxeles

        Returns:
            Vector2 posición en metros
        """
        return self.camera.screen_to_world(screen_pos)
