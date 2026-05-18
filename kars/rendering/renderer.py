"""Renderer: dibuja la simulacion usando Pygame."""

import pygame
import math
import time
from typing import Optional

from kars.physics.models import Vector2
from kars.rendering.camera import Camera
from kars.rendering.debug_overlay import DebugOverlay
import kars.config as config


class Renderer:
    """Renderiza la simulacion usando Pygame.

    Responsabilidades:
    - Inicializa ventana Pygame
    - Dibuja carriles y agentes
    - Maneja eventos (zoom, pan, pause)
    - Calcula FPS
    """

    def __init__(self, width_px: int = config.WINDOW_WIDTH_PX, height_px: int = config.WINDOW_HEIGHT_PX):
        """Inicializa renderer.

        Args:
            width_px: Ancho de ventana
            height_px: Alto de ventana
        """
        pygame.init()

        self.width_px = width_px
        self.height_px = height_px
        self.screen = pygame.display.set_mode((width_px, height_px))
        pygame.display.set_caption("KARS: Traffic Simulator")

        self.clock = pygame.time.Clock()
        self.camera = Camera(width_px, height_px)
        self.debug_overlay = DebugOverlay(enabled=config.DEBUG_OVERLAY_ENABLED)

        # Tracking de FPS
        self.frame_times = []
        self.last_frame_time = time.time()

        # Fuente para texto
        self.font_small = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 28)

        self.running = True
        self.paused = False

    def draw_lane(self, lane_id: str, waypoints: list, width_m: float) -> None:
        """Dibuja un carril.

        Args:
            lane_id: ID del carril
            waypoints: Lista de (x, y) en metros
            width_m: Ancho del carril en metros
        """
        if len(waypoints) < 2:
            return

        # Convierte waypoints a pantalla
        screen_points = []
        for wx, wy in waypoints:
            px, py = self.camera.world_to_screen(Vector2(wx, wy))
            screen_points.append((px, py))

        # Dibuja linea central del carril
        if len(screen_points) >= 2:
            pygame.draw.lines(self.screen, config.COLOR_LANE_BORDER, screen_points, 1)

        # Dibuja borde del carril (lineas paralelas)
        # Para MVP: solo dibuja la linea central

    def draw_agent(self, agent_id: int, world_pos: Vector2, heading: float, speed_kmh: float) -> None:
        """Dibuja un agente (carro).

        Args:
            agent_id: ID del agente
            world_pos: Posicion en metros
            heading: Rumbo en radianes
            speed_kmh: Velocidad en km/h
        """
        screen_x, screen_y = self.camera.world_to_screen(world_pos)

        # Dibuja carro como rectangulo
        car_width_px = config.CAR_SPRITE_WIDTH_PX
        car_length_px = config.CAR_SPRITE_LENGTH_PX

        # Crea rectangulo y lo rota segun heading
        rect = pygame.Rect(screen_x - car_length_px / 2, screen_y - car_width_px / 2, car_length_px, car_width_px)

        # Por ahora dibuja rectangulo sin rotacion
        # Luego se puede mejorar con rotacion
        pygame.draw.rect(self.screen, config.COLOR_CAR_DEFAULT, rect)

        # Dibuja ID del agente
        if config.DEBUG_OVERLAY_ENABLED:
            text = self.font_small.render(f"{agent_id}", True, config.COLOR_TEXT)
            self.screen.blit(text, (screen_x - 10, screen_y - 10))

    def draw_grid_overlay(self) -> None:
        """Dibuja grid de metros para referencia."""
        if not config.DEBUG_OVERLAY_ENABLED:
            return

        # Dibuja lineas cada 50 metros
        grid_spacing_m = 50.0
        visible_bounds = self.camera.get_visible_world_bounds()
        min_x, min_y, max_x, max_y = visible_bounds

        # Lineas verticales
        x = int(min_x / grid_spacing_m) * grid_spacing_m
        while x <= max_x:
            px, _ = self.camera.world_to_screen(Vector2(x, 0))
            pygame.draw.line(self.screen, config.COLOR_GRID, (px, 0), (px, self.height_px), 1)
            x += grid_spacing_m

        # Lineas horizontales
        y = int(min_y / grid_spacing_m) * grid_spacing_m
        while y <= max_y:
            _, py = self.camera.world_to_screen(Vector2(0, y))
            pygame.draw.line(self.screen, config.COLOR_GRID, (0, py), (self.width_px, py), 1)
            y += grid_spacing_m

    def draw_hud(self, snapshot) -> None:
        """Dibuja HUD con estadisticas."""
        if not config.DEBUG_OVERLAY_ENABLED:
            return

        lines = [
            f"Tick: {snapshot.tick_number}",
            f"Time: {snapshot.sim_time_s:.2f}s",
            f"Agents: {len(snapshot.agents)}",
            f"Avg Speed: {snapshot.avg_speed_kmh:.1f} km/h",
            f"FPS: {snapshot.fps:.1f}",
            "Keys: +/-=speed, P=pause, Q=quit",
        ]

        y = 10
        for line in lines:
            text = self.font_small.render(line, True, config.COLOR_TEXT)
            self.screen.blit(text, (10, y))
            y += 20

    def draw_snapshot(self, snapshot) -> None:
        """Dibuja un snapshot de la simulacion."""
        # Limpia pantalla
        self.screen.fill(config.BACKGROUND_COLOR)

        # Dibuja grid
        self.draw_grid_overlay()

        # Dibuja carriles
        for lane_id, waypoints, width_m in snapshot.lanes:
            self.draw_lane(lane_id, waypoints, width_m)

        # Dibuja agentes
        for agent_id, world_pos, heading, speed_kmh, lane_id, s in snapshot.agents:
            self.draw_agent(agent_id, world_pos, heading, speed_kmh)

        # Dibuja HUD
        self.draw_hud(snapshot)

        # Actualiza pantalla
        pygame.display.flip()

    def handle_events(self, world) -> bool:
        """Maneja eventos de Pygame.

        Args:
            world: World para modificar estados

        Returns:
            True si debe continuar, False para salir
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return False

                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    # Aumenta velocidad de simulacion
                    world.set_sim_speed_factor(world.sim_speed_factor * 1.5)

                if event.key == pygame.K_MINUS:
                    # Disminuye velocidad de simulacion
                    world.set_sim_speed_factor(world.sim_speed_factor / 1.5)

                if event.key == pygame.K_p:
                    # Pausa
                    self.paused = not self.paused

                # Zoom
                if event.key == pygame.K_UP:
                    self.camera.set_zoom(self.camera.zoom * 1.2)

                if event.key == pygame.K_DOWN:
                    self.camera.set_zoom(self.camera.zoom / 1.2)

                # Pan
                if event.key == pygame.K_LEFT:
                    self.camera.pan(-50, 0)
                if event.key == pygame.K_RIGHT:
                    self.camera.pan(50, 0)

        return True

    def update_fps(self, snapshot) -> None:
        """Actualiza calculo de FPS."""
        now = time.time()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        self.frame_times.append(dt)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)

        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0

        # Actualiza snapshot con FPS
        snapshot.fps = fps

    def run_frame(self, world) -> bool:
        """Ejecuta un frame del simulador.

        Args:
            world: World a simular

        Returns:
            True si debe continuar, False para salir
        """
        # Maneja eventos
        if not self.handle_events(world):
            return False

        # Simula un tick si no esta pausado
        if not self.paused:
            world.tick()

        # Crea snapshot y dibuja
        snapshot = world.build_render_snapshot()
        self.update_fps(snapshot)
        self.draw_snapshot(snapshot)

        # Limita FPS a target
        self.clock.tick(config.RENDER_TARGET_FPS)

        return True

    def close(self) -> None:
        """Cierra el renderer."""
        pygame.quit()
