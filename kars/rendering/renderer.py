"""Renderer: dibuja la simulación usando Pygame con optimizaciones."""

import pygame
import math
import time
from typing import Optional, Tuple

from kars.physics.models import Vector2
from kars.rendering.viewport_manager import ViewportManager
from kars.rendering.hud import HUD
from kars.simulation.world import World, RenderSnapshot
from kars.agents.car_agent import CarAgent
import kars.config as config


class Renderer:
    """Renderiza la simulación con viewport manager y HUD interactivo.

    Características:
    - Cache de lanes para render rápido
    - Culling de agentes fuera de viewport
    - Interacción con mouse: spawn, remove, follow
    - HUD overlay con controles interactivos
    """

    def __init__(self, width_px: int = config.WINDOW_WIDTH_PX,
                 height_px: int = config.WINDOW_HEIGHT_PX):
        """Inicializa renderer.

        Args:
            width_px: Ancho de ventana
            height_px: Alto de ventana
        """
        pygame.init()

        self.width_px = width_px
        self.height_px = height_px
        self.screen = pygame.display.set_mode((width_px, height_px))
        pygame.display.set_caption("KARS: Interactive Traffic Simulator")

        self.clock = pygame.time.Clock()

        # Viewport manager
        from kars.rendering.camera import Camera
        camera = Camera(width_px, height_px)
        self.viewport = ViewportManager(camera)

        # HUD
        self.hud = HUD(width_px, height_px)

        # FPS tracking
        self.frame_times = []
        self.last_frame_time = time.time()

        # Cache de lanes (se dibuja una sola vez)
        self.lanes_cache_surface: Optional[pygame.Surface] = None
        self.lanes_cache_valid = False

        self.running = True

    def _build_lanes_cache(self, snapshot: RenderSnapshot) -> pygame.Surface:
        """Construye una surface con todos los lanes dibujados.

        Args:
            snapshot: RenderSnapshot con información de lanes

        Returns:
            pygame.Surface con lanes pre-renderizados
        """
        # Crea surface del tamaño de la ventana
        surface = pygame.Surface((self.width_px, self.height_px))
        surface.fill(config.BACKGROUND_COLOR)

        # Dibuja cada lane
        for lane_id, waypoints, width_m in snapshot.lanes:
            if len(waypoints) < 2:
                continue

            # Convierte waypoints a pantalla
            screen_points = []
            for wx, wy in waypoints:
                px, py = self.viewport.world_to_screen(Vector2(wx, wy))
                screen_points.append((int(px), int(py)))

            # Dibuja línea central del carril
            if len(screen_points) >= 2:
                for i in range(len(screen_points) - 1):
                    pygame.draw.line(surface, config.COLOR_LANE_BORDER,
                                   screen_points[i], screen_points[i+1], 2)

            # Dibuja bordes paralelos del carril (offsets laterales)
            # Esto se hace calculando normales a la polyline
            offset_points_left = []
            offset_points_right = []
            offset_m = width_m / 2.0

            for i, (wx, wy) in enumerate(waypoints):
                # Calcula normal (perpendicular a la dirección)
                if i < len(waypoints) - 1:
                    next_wx, next_wy = waypoints[i + 1]
                    dx = next_wx - wx
                    dy = next_wy - wy
                else:
                    # Último punto: usa dirección del segmento anterior
                    prev_wx, prev_wy = waypoints[i - 1]
                    dx = wx - prev_wx
                    dy = wy - prev_wy

                # Normal (perpendicular)
                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    nx = -dy / length
                    ny = dx / length
                else:
                    nx, ny = 0, 0

                # Puntos offset
                left_x = wx + nx * offset_m
                left_y = wy + ny * offset_m
                right_x = wx - nx * offset_m
                right_y = wy - ny * offset_m

                left_screen = self.viewport.world_to_screen(Vector2(left_x, left_y))
                right_screen = self.viewport.world_to_screen(Vector2(right_x, right_y))
                offset_points_left.append((int(left_screen[0]), int(left_screen[1])))
                offset_points_right.append((int(right_screen[0]), int(right_screen[1])))

            # Dibuja bordes
            if len(offset_points_left) >= 2:
                for i in range(len(offset_points_left) - 1):
                    pygame.draw.line(surface, config.COLOR_LANE_BORDER,
                                   offset_points_left[i], offset_points_left[i+1], 1)
            if len(offset_points_right) >= 2:
                for i in range(len(offset_points_right) - 1):
                    pygame.draw.line(surface, config.COLOR_LANE_BORDER,
                                   offset_points_right[i], offset_points_right[i+1], 1)

        return surface

    def draw_lane_cached(self, snapshot: RenderSnapshot) -> None:
        """Dibuja lanes usando cache estático.

        Args:
            snapshot: RenderSnapshot con información de lanes
        """
        if not self.lanes_cache_valid or self.lanes_cache_surface is None:
            self.lanes_cache_surface = self._build_lanes_cache(snapshot)
            self.lanes_cache_valid = True

        self.screen.blit(self.lanes_cache_surface, (0, 0))

    def draw_agent(self, agent_id: int, world_pos: Vector2, heading: float,
                   speed_kmh: float, selected: bool = False) -> None:
        """Dibuja un agente (carro).

        Args:
            agent_id: ID del agente
            world_pos: Posición en metros
            heading: Rumbo en radianes
            speed_kmh: Velocidad en km/h
            selected: True si el agente está siendo seguido
        """
        screen_x, screen_y = self.viewport.world_to_screen(world_pos)

        # Culling: no dibujar si está fuera de pantalla
        if not (-20 < screen_x < self.width_px + 20 or -20 < screen_y < self.height_px + 20):
            return

        car_length_px = config.CAR_SPRITE_LENGTH_PX
        car_width_px = config.CAR_SPRITE_WIDTH_PX

        # Escala según zoom
        zoom = self.viewport.camera.zoom
        car_length_px = int(car_length_px * zoom)
        car_width_px = int(car_width_px * zoom)

        # Elige color según velocidad y estado
        if selected:
            color = config.COLOR_CAR_SELECTED
        elif speed_kmh > 15.0:
            color = config.COLOR_CAR_FAST
        elif speed_kmh < 2.0:
            color = config.COLOR_CAR_SLOW
        else:
            color = config.COLOR_CAR_DEFAULT

        # Crea rectángulo y lo rota
        rect = pygame.Rect(screen_x - car_length_px / 2, screen_y - car_width_px / 2,
                          car_length_px, car_width_px)

        # Dibuja rectángulo (sin rotación por ahora para performance)
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, config.COLOR_TEXT, rect, 1)

        # Dibuja ID del agente
        if config.DEBUG_OVERLAY_ENABLED:
            font_id = pygame.font.Font(None, 12)
            text = font_id.render(f"{agent_id}", True, config.COLOR_TEXT)
            self.screen.blit(text, (screen_x - 5, screen_y - 5))

    def _find_agent_at_screen(self, snapshot: RenderSnapshot, mouse_pos: Tuple[int, int],
                              threshold_px: int = 20) -> Optional[Tuple[int, Vector2]]:
        """Encuentra el agente más cercano a una posición de pantalla.

        Args:
            snapshot: RenderSnapshot con agentes
            mouse_pos: (screen_x, screen_y)
            threshold_px: Distancia máxima de click (píxeles)

        Returns:
            (agent_id, world_pos) o None
        """
        best_agent = None
        best_dist = threshold_px

        for agent_id, world_pos, heading, speed_kmh, lane_id, s in snapshot.agents:
            screen_x, screen_y = self.viewport.world_to_screen(world_pos)
            dx = screen_x - mouse_pos[0]
            dy = screen_y - mouse_pos[1]
            dist = math.sqrt(dx*dx + dy*dy)

            if dist < best_dist:
                best_dist = dist
                best_agent = (agent_id, world_pos)

        return best_agent

    def _find_nearest_lane_s(self, network, world_pos: Vector2) -> Tuple:
        """Encuentra el carril más cercano y la posición s.

        Args:
            network: RoadNetwork
            world_pos: Posición en mundo (metros)

        Returns:
            (lane, s_value) o (None, None)
        """
        closest_lane = None
        closest_s = None
        best_dist = float('inf')

        for lane in network.get_all_lanes():
            try:
                s = lane.find_closest_s(world_pos)
                closest_world = lane.world_position_at(s, 0.0)
                dist = world_pos.distance_to(closest_world)

                if dist < best_dist:
                    best_dist = dist
                    closest_lane = lane
                    closest_s = s
            except ValueError:
                continue

        return closest_lane, closest_s

    def handle_events(self, world: World) -> bool:
        """Maneja eventos de Pygame.

        Args:
            world: World para modificar si es necesario

        Returns:
            True si debe continuar, False para salir
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    return False

            # Scroll del mouse para zoom
            if event.type == pygame.MOUSEWHEEL:
                self.viewport.handle_mouse_wheel(event.y)

            # Middle mouse pan
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self.middle_mouse_start = event.pos
            elif event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[2]:
                if hasattr(self, 'middle_mouse_start'):
                    dx = event.pos[0] - self.middle_mouse_start[0]
                    dy = event.pos[1] - self.middle_mouse_start[1]
                    self.viewport.handle_mouse_drag(dx, dy)
                    self.middle_mouse_start = event.pos

            # Left click: spawn agente
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                world_pos = self.viewport.screen_to_world(event.pos)
                lane, s = self._find_nearest_lane_s(world.network, world_pos)

                if lane is not None:
                    # Spawn nuevo agente
                    agent_id = world.get_next_agent_id()
                    agent = CarAgent(
                        agent_id=agent_id,
                        current_lane_id=lane.lane_id,
                        position_along_lane_s=s,
                        lateral_offset=0.0,
                    )
                    world_pos_snapped = lane.world_position_at(s, 0.0)
                    agent.set_position_world(world_pos_snapped, heading=0.0)
                    world.add_agent(agent)

            # Right click: remove agente (o click en agente para seguir)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                # Primero intenta encontrar agente en esta posición
                # Si no, se consume para no disparar pan
                pass

            # Propagar eventos al HUD
            self.hud.handle_event(event, world)

        return True

    def update_fps(self, snapshot: RenderSnapshot) -> None:
        """Actualiza cálculo de FPS."""
        now = time.time()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        self.frame_times.append(dt)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)

        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
            snapshot.fps = fps

    def run_frame(self, world: World) -> bool:
        """Ejecuta un frame del simulador.

        Args:
            world: World a simular

        Returns:
            True si debe continuar, False para salir
        """
        # Maneja eventos
        if not self.handle_events(world):
            return False

        # Simula un tick si no está pausado
        if not self.hud.is_paused:
            world.tick()

        # Actualiza viewport (follow mode)
        snapshot = world.build_render_snapshot()
        self.viewport.update(snapshot, world.agents)

        # Actualiza HUD
        self.hud.update(snapshot, world)

        # Dibuja escena
        self.screen.fill(config.BACKGROUND_COLOR)

        # Dibuja lanes (cache)
        self.draw_lane_cached(snapshot)

        # Dibuja agentes
        for agent_id, world_pos, heading, speed_kmh, lane_id, s in snapshot.agents:
            is_selected = (agent_id == self.viewport.follow_agent_id)
            self.draw_agent(agent_id, world_pos, heading, speed_kmh, is_selected)

        # Actualiza FPS
        self.update_fps(snapshot)

        # Dibuja HUD overlay
        self.hud.draw(self.screen)

        # Actualiza pantalla
        pygame.display.flip()

        # Limita FPS
        self.clock.tick(60)

        return True

    def close(self) -> None:
        """Cierra el renderer."""
        pygame.quit()
