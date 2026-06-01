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
                 height_px: int = config.WINDOW_HEIGHT_PX,
                 scene_filepath: str = None,
                 camera_config: dict = None):
        """Inicializa renderer.

        Args:
            width_px: Ancho de ventana
            height_px: Alto de ventana
            scene_filepath: Ruta al archivo JSON de la escena (para resetear)
            camera_config: Configuración de cámara {'viewport_x_min_m': ..., 'viewport_x_max_m': ...}
        """
        pygame.init()

        self.width_px = width_px
        self.height_px = height_px
        self.screen = pygame.display.set_mode((width_px, height_px))

        # Espacio dibujable real (excluyendo banners del HUD)
        self.drawable_top_y = config.HUD_TOP_HEIGHT
        self.drawable_height_px = height_px - config.HUD_TOP_HEIGHT - config.HUD_BAR_HEIGHT
        self.drawable_center_y_px = self.drawable_top_y + self.drawable_height_px / 2.0
        pygame.display.set_caption("KARS: Interactive Traffic Simulator")

        self.clock = pygame.time.Clock()

        # Viewport manager
        from kars.rendering.camera import Camera
        camera = Camera(
            width_px,
            height_px,
            config.SCALE_PX_PER_M,
            drawable_top_y_px=config.HUD_TOP_HEIGHT,
            drawable_height_px=height_px - config.HUD_TOP_HEIGHT - config.HUD_BAR_HEIGHT
        )
        self.viewport = ViewportManager(camera)

        # HUD
        self.hud = HUD(width_px, height_px)

        # FPS tracking
        self.frame_times = []
        self.last_frame_time = time.time()
        self.current_fps = 0.0

        # Cache de lanes (se dibuja una sola vez)
        self.lanes_cache_surface: Optional[pygame.Surface] = None
        self.lanes_cache_valid = False

        self.running = True
        self.initial_zoom_done = False
        self.scene_filepath = scene_filepath
        self.reset_requested = False
        self.camera_config = camera_config or {}

        # Bounds explícitos del viewport (si se especifican en la configuración)
        self.explicit_viewport_x_min = None
        self.explicit_viewport_x_max = None
        self.explicit_viewport_y_min = None
        self.explicit_viewport_y_max = None

    def _build_segments_cache(self, snapshot: RenderSnapshot) -> pygame.Surface:
        """Construye una surface con todos los segmentos dibujados como calles unificadas.

        Estructura visual: una calle es una polilínea con ancho. Se dibuja como:
        ┌────────────────────────────────────┐
        │ GREEN (fondo)                      │
        │ ┌──────────────────────────────────┐
        │ │ GRAY (carpeta asfáltica)         │ ← márgenes + carriles en una tira
        │ │ WHITE │ [dashed] │ WHITE         │ ← franjas de demarcación encima
        │ └──────────────────────────────────┘
        │ GREEN (fondo)                      │
        └────────────────────────────────────┘

        Para cada segmento, dibuja:
        1. Un rectángulo gris unificado (borde a borde: márgenes + carriles)
        2. Franjas blancas sólidas en los bordes externos
        3. Franjas punteadas entre carriles (si hay múltiples) — TODO

        Args:
            snapshot: RenderSnapshot con información de segmentos

        Returns:
            pygame.Surface con segmentos pre-renderizados
        """
        surface = pygame.Surface((self.width_px, self.height_px))
        surface.fill(config.BACKGROUND_COLOR)  # Fondo verde pasto

        # Dibuja cada segmento como una calle unificada
        for segment in snapshot.segments:
            segment_id = segment['segment_id']
            waypoints = segment['waypoints']
            total_width_m = segment['total_width_m']
            speed_limit_kmh = segment['speed_limit_kmh']
            lane_ids = segment['lane_ids']

            if len(waypoints) < 2:
                continue

            # Convierte waypoints a pantalla
            screen_points = []
            for wx, wy in waypoints:
                px, py = self.viewport.world_to_screen(Vector2(wx, wy))
                screen_points.append((int(px), int(py)))

            # Calcula el ancho total en metros: carriles + márgenes
            half_total_width = total_width_m / 2.0
            total_half_width_with_margins = half_total_width + config.ROAD_MARGIN_WIDTH_M

            # Borde exterior del segmento (márgenes)
            offset_street_left = []
            offset_street_right = []

            # Borde interior del segmento (límite del concreto)
            offset_road_left = []
            offset_road_right = []

            for i, (wx, wy) in enumerate(waypoints):
                # Calcula normal (perpendicular a la dirección)
                if i < len(waypoints) - 1:
                    next_wx, next_wy = waypoints[i + 1]
                    dx = next_wx - wx
                    dy = next_wy - wy
                else:
                    prev_wx, prev_wy = waypoints[i - 1]
                    dx = wx - prev_wx
                    dy = wy - prev_wy

                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    nx = -dy / length
                    ny = dx / length
                else:
                    nx, ny = 0, 0

                # Borde exterior (márgenes incluidos)
                street_left_x = wx + nx * total_half_width_with_margins
                street_left_y = wy + ny * total_half_width_with_margins
                street_right_x = wx - nx * total_half_width_with_margins
                street_right_y = wy - ny * total_half_width_with_margins

                # Borde interior (donde empieza la carretera)
                road_left_x = wx + nx * half_total_width
                road_left_y = wy + ny * half_total_width
                road_right_x = wx - nx * half_total_width
                road_right_y = wy - ny * half_total_width

                offset_street_left.append(self.viewport.world_to_screen(Vector2(street_left_x, street_left_y)))
                offset_street_right.append(self.viewport.world_to_screen(Vector2(street_right_x, street_right_y)))
                offset_road_left.append(self.viewport.world_to_screen(Vector2(road_left_x, road_left_y)))
                offset_road_right.append(self.viewport.world_to_screen(Vector2(road_right_x, road_right_y)))

            # Helper: dibuja un strip entre dos líneas paralelas
            def draw_strip(surface, color, left_line, right_line, min_width_px=2):
                if len(left_line) < 2 or len(right_line) < 2:
                    return
                for i in range(len(left_line) - 1):
                    p1 = (int(left_line[i][0]), int(left_line[i][1]))
                    p2 = (int(left_line[i+1][0]), int(left_line[i+1][1]))
                    p3 = (int(right_line[i+1][0]), int(right_line[i+1][1]))
                    p4 = (int(right_line[i][0]), int(right_line[i][1]))

                    width_px = abs(p1[0] - p4[0]) + abs(p1[1] - p4[1])
                    if width_px < min_width_px:
                        pygame.draw.line(surface, color, p1, p2, max(min_width_px, 2))
                        pygame.draw.line(surface, color, p4, p3, max(min_width_px, 2))
                    else:
                        quad = [p1, p2, p3, p4]
                        pygame.draw.polygon(surface, color, quad)

            # Dibuja la carpeta asfáltica completa (márgenes + carriles) como un único rectángulo
            draw_strip(surface, config.COLOR_LANE_ROAD, offset_street_left, offset_street_right)

            # 2. FRANJAS BLANCAS en los bordes de la carpeta asfáltica
            marking_width_m = config.LANE_MARKING_WIDTH_M

            # Franja blanca izquierda (borde izquierdo del carril)
            outer_left_edge = []
            inner_left_edge = []
            for i, (wx, wy) in enumerate(waypoints):
                if i < len(waypoints) - 1:
                    next_wx, next_wy = waypoints[i + 1]
                    dx = next_wx - wx
                    dy = next_wy - wy
                else:
                    prev_wx, prev_wy = waypoints[i - 1]
                    dx = wx - prev_wx
                    dy = wy - prev_wy

                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    nx = -dy / length
                    ny = dx / length
                else:
                    nx, ny = 0, 0

                # Franja: desde borde del carril (half_total_width) hacia el margen
                outer_x = wx + nx * half_total_width
                outer_y = wy + ny * half_total_width
                inner_x = wx + nx * (half_total_width - marking_width_m)
                inner_y = wy + ny * (half_total_width - marking_width_m)

                outer_left_edge.append(self.viewport.world_to_screen(Vector2(outer_x, outer_y)))
                inner_left_edge.append(self.viewport.world_to_screen(Vector2(inner_x, inner_y)))

            draw_strip(surface, config.COLOR_LANE_BORDER, outer_left_edge, inner_left_edge, min_width_px=2)

            # Franja blanca derecha (borde derecho del carril)
            outer_right_edge = []
            inner_right_edge = []
            for i, (wx, wy) in enumerate(waypoints):
                if i < len(waypoints) - 1:
                    next_wx, next_wy = waypoints[i + 1]
                    dx = next_wx - wx
                    dy = next_wy - wy
                else:
                    prev_wx, prev_wy = waypoints[i - 1]
                    dx = wx - prev_wx
                    dy = wy - prev_wy

                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    nx = -dy / length
                    ny = dx / length
                else:
                    nx, ny = 0, 0

                # Franja: desde borde del carril (-half_total_width) hacia el margen
                outer_x = wx - nx * half_total_width
                outer_y = wy - ny * half_total_width
                inner_x = wx - nx * (half_total_width - marking_width_m)
                inner_y = wy - ny * (half_total_width - marking_width_m)

                outer_right_edge.append(self.viewport.world_to_screen(Vector2(outer_x, outer_y)))
                inner_right_edge.append(self.viewport.world_to_screen(Vector2(inner_x, inner_y)))

            draw_strip(surface, config.COLOR_LANE_BORDER, inner_right_edge, outer_right_edge, min_width_px=2)

            # 4. FRANJAS PUNTEADAS entre carriles (solo si hay más de 1 carril)
            if len(lane_ids) > 1:
                # Obtén el ancho de un carril (asumir que todos tienen el mismo)
                try:
                    first_lane = self.world.network.get_lane(lane_ids[0])
                    lane_width_m = first_lane.width_m
                except:
                    lane_width_m = config.LANE_WIDTH_M

                # Dibuja línea divisoria entre cada par de carriles adyacentes
                # La línea divisoria entre carril i y carril i+1 está en: (i+1) * lane_width_m desde el borde izq
                for divider_index in range(1, len(lane_ids)):
                    # Posición perpendicular desde el borde izquierdo de la carpeta
                    divider_offset_m = half_total_width - divider_index * lane_width_m

                    # Calcula puntos de la línea punteada
                    divider_edge = []
                    for i, (wx, wy) in enumerate(waypoints):
                        if i < len(waypoints) - 1:
                            next_wx, next_wy = waypoints[i + 1]
                            dx = next_wx - wx
                            dy = next_wy - wy
                        else:
                            prev_wx, prev_wy = waypoints[i - 1]
                            dx = wx - prev_wx
                            dy = wy - prev_wy

                        length = math.sqrt(dx*dx + dy*dy)
                        if length > 0:
                            nx = -dy / length
                            ny = dx / length
                        else:
                            nx, ny = 0, 0

                        # Posición de la línea divisoria
                        div_x = wx + nx * divider_offset_m
                        div_y = wy + ny * divider_offset_m
                        divider_edge.append(self.viewport.world_to_screen(Vector2(div_x, div_y)))

                    # Dibuja como línea punteada blanca
                    self._draw_dashed_line(surface, config.COLOR_LANE_BORDER, divider_edge, dash_length_px=8, gap_length_px=8)

        return surface

    def _draw_dashed_line(self, surface: pygame.Surface, color: Tuple, points: list, dash_length_px: int = 8, gap_length_px: int = 8) -> None:
        """Dibuja una línea punteada entre puntos.

        Params:
            surface: Surface donde dibujar
            color: Color RGB
            points: Lista de tuplas (x, y) en píxeles pantalla
            dash_length_px: Longitud del trazo en píxeles
            gap_length_px: Longitud del hueco en píxeles
        """
        if len(points) < 2:
            return

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]

            # Distancia total entre puntos
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dist = math.sqrt(dx*dx + dy*dy)

            if dist < 0.1:
                continue

            # Número de dashes que caben en este segmento
            dash_cycle = dash_length_px + gap_length_px
            num_dashes = int(dist / dash_cycle)

            # Dibuja dashes
            for d in range(num_dashes + 1):
                start_ratio = (d * dash_cycle) / dist
                end_ratio = (d * dash_cycle + dash_length_px) / dist

                if start_ratio >= 1.0:
                    break

                end_ratio = min(end_ratio, 1.0)

                dash_start_x = int(p1[0] + dx * start_ratio)
                dash_start_y = int(p1[1] + dy * start_ratio)
                dash_end_x = int(p1[0] + dx * end_ratio)
                dash_end_y = int(p1[1] + dy * end_ratio)

                pygame.draw.line(surface, color, (dash_start_x, dash_start_y), (dash_end_x, dash_end_y), 2)

    def _build_lanes_cache(self, snapshot: RenderSnapshot) -> pygame.Surface:
        """Construye una surface con todos los lanes dibujados.

        Dibuja: margen verde → carretera gris → bordes blancos

        Args:
            snapshot: RenderSnapshot con información de lanes

        Returns:
            pygame.Surface con lanes pre-renderizados
        """
        surface = pygame.Surface((self.width_px, self.height_px))
        surface.fill(config.BACKGROUND_COLOR)  # Fondo verde pasto

        # Estructura de la calle urbana real:
        # 100cm margen verde + 12cm franja blanca + 348cm gris carretera + 12cm franja blanca + 100cm margen verde
        # Total: 5.72m de ancho

        # Dibuja cada lane
        for lane_id, waypoints, width_m in snapshot.lanes:
            if len(waypoints) < 2:
                continue

            # Convierte waypoints a pantalla
            screen_points = []
            for wx, wy in waypoints:
                px, py = self.viewport.world_to_screen(Vector2(wx, wy))
                screen_points.append((int(px), int(py)))

            # Estructura de la calle (desde center outward):
            # margen_verde (1.0m) | franja_blanca (0.12m) | carretera_gris (3.48m) | franja_blanca (0.12m) | margen_verde (1.0m)

            half_road = config.LANE_WIDTH_M / 2.0  # 2.0m (borde del carril)
            half_marking = config.LANE_MARKING_WIDTH_M / 2.0  # 0.1m

            # Ancho total de la calle (márgenes + carril)
            total_half_width = config.ROAD_MARGIN_WIDTH_M + half_road  # 0.8 + 2.0 = 2.8m

            # Franjas: centradas en los bordes del carril
            franja_inner_left = half_road - half_marking  # 2.0 - 0.1 = 1.9m
            franja_outer_left = half_road + half_marking  # 2.0 + 0.1 = 2.1m
            franja_inner_right = half_road - half_marking  # 2.0 - 0.1 = 1.9m
            franja_outer_right = half_road + half_marking  # 2.0 + 0.1 = 2.1m

            offset_street_left = []   # Borde izquierdo de la calle (gris)
            offset_street_right = []  # Borde derecho de la calle (gris)
            offset_stripe_left_inner = []  # Franja blanca izquierda, lado interior
            offset_stripe_left_outer = []  # Franja blanca izquierda, lado exterior
            offset_stripe_right_inner = []  # Franja blanca derecha, lado interior
            offset_stripe_right_outer = []  # Franja blanca derecha, lado exterior

            for i, (wx, wy) in enumerate(waypoints):
                # Calcula normal (perpendicular a la dirección)
                if i < len(waypoints) - 1:
                    next_wx, next_wy = waypoints[i + 1]
                    dx = next_wx - wx
                    dy = next_wy - wy
                else:
                    prev_wx, prev_wy = waypoints[i - 1]
                    dx = wx - prev_wx
                    dy = wy - prev_wy

                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    nx = -dy / length
                    ny = dx / length
                else:
                    nx, ny = 0, 0

                # CALLE COMPLETA (gris, incluye márgenes)
                street_left_x = wx + nx * total_half_width
                street_left_y = wy + ny * total_half_width
                street_right_x = wx - nx * total_half_width
                street_right_y = wy - ny * total_half_width

                # FRANJAS BLANCAS (centradas en bordes del carril)
                stripe_left_outer_x = wx + nx * franja_outer_left
                stripe_left_outer_y = wy + ny * franja_outer_left
                stripe_left_inner_x = wx + nx * franja_inner_left
                stripe_left_inner_y = wy + ny * franja_inner_left

                stripe_right_inner_x = wx - nx * franja_inner_right
                stripe_right_inner_y = wy - ny * franja_inner_right
                stripe_right_outer_x = wx - nx * franja_outer_right
                stripe_right_outer_y = wy - ny * franja_outer_right

                # Convierte a pantalla
                offset_street_left.append(self.viewport.world_to_screen(Vector2(street_left_x, street_left_y)))
                offset_street_right.append(self.viewport.world_to_screen(Vector2(street_right_x, street_right_y)))
                offset_stripe_left_outer.append(self.viewport.world_to_screen(Vector2(stripe_left_outer_x, stripe_left_outer_y)))
                offset_stripe_left_inner.append(self.viewport.world_to_screen(Vector2(stripe_left_inner_x, stripe_left_inner_y)))
                offset_stripe_right_inner.append(self.viewport.world_to_screen(Vector2(stripe_right_inner_x, stripe_right_inner_y)))
                offset_stripe_right_outer.append(self.viewport.world_to_screen(Vector2(stripe_right_outer_x, stripe_right_outer_y)))

            # Dibuja polígonos rellenos (strips) de cada sección de la calle
            # Estructura: verde margen | blanco borde | gris carretera | blanco borde | verde margen

            # Helper: crea un strip (quad) entre dos líneas paralelas
            def draw_strip(surface, color, left_line, right_line, min_width_px=2):
                """Dibuja un polígono entre dos líneas paralelas.

                min_width_px: ancho mínimo en píxeles para asegurar visibilidad
                """
                if len(left_line) < 2 or len(right_line) < 2:
                    return
                for i in range(len(left_line) - 1):
                    p1 = (int(left_line[i][0]), int(left_line[i][1]))
                    p2 = (int(left_line[i+1][0]), int(left_line[i+1][1]))
                    p3 = (int(right_line[i+1][0]), int(right_line[i+1][1]))
                    p4 = (int(right_line[i][0]), int(right_line[i][1]))

                    # Si el ancho es muy pequeño, usa líneas gruesas en su lugar
                    width_px = abs(p1[0] - p4[0]) + abs(p1[1] - p4[1])
                    if width_px < min_width_px:
                        pygame.draw.line(surface, color, p1, p2, max(min_width_px, 2))
                        pygame.draw.line(surface, color, p4, p3, max(min_width_px, 2))
                    else:
                        quad = [p1, p2, p3, p4]
                        pygame.draw.polygon(surface, color, quad)

            # Dibuja en orden:
            # 1. CALLE COMPLETA (gris: márgenes + carril)
            draw_strip(surface, config.COLOR_LANE_ROAD, offset_street_left, offset_street_right)

            # 2. FRANJA BLANCA IZQUIERDA (encima)
            draw_strip(surface, config.COLOR_LANE_BORDER, offset_stripe_left_outer, offset_stripe_left_inner, min_width_px=2)

            # 3. FRANJA BLANCA DERECHA (encima)
            draw_strip(surface, config.COLOR_LANE_BORDER, offset_stripe_right_inner, offset_stripe_right_outer, min_width_px=2)

        return surface

    def draw_stopping_line(self, snapshot: RenderSnapshot) -> None:
        """Dibuja línea blanca vertical donde deberían detenerse los vehículos.

        Posición: centro del carro a (CAR_LENGTH_M + min_gap) antes del obstáculo
        - Parte trasera del obstáculo: s - CAR_LENGTH_M/2
        - Gap mínimo: min_gap
        - Parte delantera del carro debe estar en: (s - CAR_LENGTH_M/2) - min_gap
        - Centro del carro: parte_delantera - CAR_LENGTH_M/2

        Args:
            snapshot: RenderSnapshot con obstáculos
        """
        import kars.config as config
        MIN_GAP_M = config.IDM_MIN_GAP_M  # 2.25m = 0.5 * CAR_LENGTH_M
        CAR_LENGTH_M = config.CAR_LENGTH_M  # 4.5m

        for world_pos, lane_id, s in snapshot.obstacles:
            # Centro del carro debe estar a: CAR_LENGTH_M + MIN_GAP_M antes del obstáculo
            stop_s = s - CAR_LENGTH_M - MIN_GAP_M
            if stop_s >= 0:
                try:
                    # Calcula posición en mundo donde deberían detenerse
                    stop_world_pos = Vector2(world_pos.x - (s - stop_s), world_pos.y)
                    screen_x, screen_y = self.viewport.world_to_screen(stop_world_pos)

                    # Dibuja una línea blanca vertical donde deberían detenerse
                    line_color = (200, 200, 200)  # Blanco (línea de parada)
                    line_width = 3

                    # Línea vertical en pantalla
                    pygame.draw.line(self.screen, line_color,
                                   (int(screen_x), int(screen_y) - 100),
                                   (int(screen_x), int(screen_y) + 100), line_width)

                    # Etiqueta
                    font = pygame.font.Font(None, 12)
                    text = font.render("STOP HERE", True, line_color)
                    self.screen.blit(text, (int(screen_x) - 30, int(screen_y) - 110))
                except Exception:
                    pass

    def draw_obstacles(self, snapshot: RenderSnapshot) -> None:
        """Dibuja símbolos para obstáculos permanentes.

        Args:
            snapshot: RenderSnapshot con obstáculos
        """
        for world_pos, lane_id, s in snapshot.obstacles:
            screen_x, screen_y = self.viewport.world_to_screen(world_pos)

            # Dibuja un símbolo X grande en rojo
            size = 15
            line_color = (255, 0, 0)  # Rojo puro
            line_width = 3

            # Línea diagonal /
            pygame.draw.line(self.screen, line_color,
                           (int(screen_x) - size, int(screen_y) - size),
                           (int(screen_x) + size, int(screen_y) + size), line_width)
            # Línea diagonal \
            pygame.draw.line(self.screen, line_color,
                           (int(screen_x) + size, int(screen_y) - size),
                           (int(screen_x) - size, int(screen_y) + size), line_width)

            # Etiqueta "STOP"
            font = pygame.font.Font(None, 14)
            text = font.render("STOP", True, line_color)
            self.screen.blit(text, (int(screen_x) - 15, int(screen_y) + size + 5))

    def draw_viewport_bounds(self) -> None:
        """Dibuja un rectángulo en los bordes del viewport visible (coordenadas mundo).

        Útil para debug: muestra exactamente dónde empieza y termina el área visible.
        Con zoom=1.0 y SCALE_PX_PER_M=10, los bordes deben estar en (0,0) a (1200,800).
        """
        vis_x_min, vis_y_min, vis_x_max, vis_y_max = self.viewport.camera.get_visible_world_bounds()

        top_left = self.viewport.world_to_screen(Vector2(vis_x_min, vis_y_min))
        top_right = self.viewport.world_to_screen(Vector2(vis_x_max, vis_y_min))
        bottom_left = self.viewport.world_to_screen(Vector2(vis_x_min, vis_y_max))
        bottom_right = self.viewport.world_to_screen(Vector2(vis_x_max, vis_y_max))

        # Dibuja rectángulo magenta (3px grosor) en los bordes
        # Expande ligeramente para asegurar que las líneas horizontales sean visibles
        color = (255, 0, 255)
        x = int(top_left[0])
        y = int(top_left[1]) - 70  # Sube un poco la de arriba
        width = int(top_right[0]) - int(top_left[0])
        height = int(bottom_left[1]) - int(top_left[1]) + 100  # Expande abajo también
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, color, rect, 1)

        # Etiquetas en las 4 esquinas (mostrando coordenadas mundo)
        # Las etiquetas se dibujan con fondo oscuro para que sean visibles
        font = pygame.font.Font(None, 12)
        bg_color = (0, 0, 0)
        text_color = (255, 0, 255)

        label_tl = font.render(f"({vis_x_min:.0f}, {vis_y_min:.0f})", True, text_color, bg_color)
        label_tr = font.render(f"({vis_x_max:.0f}, {vis_y_min:.0f})", True, text_color, bg_color)
        label_bl = font.render(f"({vis_x_min:.0f}, {vis_y_max:.0f})", True, text_color, bg_color)
        label_br = font.render(f"({vis_x_max:.0f}, {vis_y_max:.0f})", True, text_color, bg_color)

        # Posiciona adentro del rect para que siempre sean visibles
        self.screen.blit(label_tl, (int(top_left[0]) + 3, int(top_left[1]) + 3))
        self.screen.blit(label_tr, (int(top_right[0]) - label_tr.get_width() - 3, int(top_right[1]) + 3))
        self.screen.blit(label_bl, (int(bottom_left[0]) + 3, int(bottom_left[1]) - label_bl.get_height() - 3))
        self.screen.blit(label_br, (int(bottom_right[0]) - label_br.get_width() - 3, int(bottom_right[1]) - label_br.get_height() - 3))

    def draw_grid(self) -> None:
        """Dibuja malla de calibración cada 10m con etiquetas de coordenadas mundo.

        Usado para verificación visual de coordenadas mundo. Con SCALE_PX_PER_M=10
        y zoom=1.0, cada celda de la malla mide 100x100px = 10m.
        """
        grid_m = 10.0
        vis_x_min, vis_y_min, vis_x_max, vis_y_max = self.viewport.camera.get_visible_world_bounds()
        font = pygame.font.Font(None, 16)

        # Obtén posición del eje Y=0 en pantalla (para etiquetar coordenadas X sobre el eje)
        _, sy_axis = self.viewport.world_to_screen(Vector2(0, 0))
        sy_axis_int = int(sy_axis)

        # Obtén posición del eje X=0 en pantalla (para etiquetar coordenadas Y sobre el eje)
        sx_axis, _ = self.viewport.world_to_screen(Vector2(0, 0))
        sx_axis_int = int(sx_axis)

        # Líneas verticales (cada 10m en X)
        x = math.floor(vis_x_min / grid_m) * grid_m
        while x <= vis_x_max + 0.01:
            sx, _ = self.viewport.world_to_screen(Vector2(x, 0))
            sx_int = int(sx)
            # Origen (0m) en rojo, otras en blanco
            color = (255, 0, 0) if abs(x) < 0.01 else (255, 255, 255)
            pygame.draw.line(self.screen, color, (sx_int, 0), (sx_int, self.height_px), 1)
            # Etiqueta sobre el eje Y=0 (eje horizontal)
            if 0 <= sx_int < self.width_px and 0 <= sy_axis_int < self.height_px:
                label = font.render(f"{int(x)}m", True, (255, 255, 100))
                self.screen.blit(label, (sx_int - 12, sy_axis_int + 2))
            x += grid_m

        # Líneas horizontales (cada 10m en Y)
        y = math.floor(vis_y_min / grid_m) * grid_m
        while y <= vis_y_max + 0.01:
            _, sy = self.viewport.world_to_screen(Vector2(0, y))
            sy_int = int(sy)
            # Origen (0m) en rojo, otras en blanco
            color = (255, 0, 0) if abs(y) < 0.01 else (255, 255, 255)
            pygame.draw.line(self.screen, color, (0, sy_int), (self.width_px, sy_int), 1)
            # Etiqueta sobre el eje X=0 (eje vertical)
            if 0 <= sx_axis_int < self.width_px and 0 <= sy_int < self.height_px:
                label = font.render(f"{int(y)}m", True, (255, 255, 100))
                self.screen.blit(label, (sx_axis_int + 2, sy_int - 8))
            y += grid_m

    def draw_distance_markers(self, snapshot: RenderSnapshot) -> None:
        """Dibuja marcadores cada 100 metros a lo largo del carril.

        Solo dibuja marcadores dentro del viewport visible (camera.get_viewport_world_bounds()).

        Args:
            snapshot: RenderSnapshot con información de lanes
        """
        if not snapshot.segments:
            return

        segment = snapshot.segments[0]
        waypoints = segment['waypoints']

        if len(waypoints) < 2:
            return

        # Obtén rango visible actual de la cámara (solo X nos interesa para los marcadores)
        visible_x_min, _, visible_x_max, _ = self.viewport.camera.get_visible_world_bounds()

        # Calcula distancias cumulativas para saber dónde está cada 100m
        cumulative_distances = [0.0]
        for i in range(len(waypoints) - 1):
            dx = waypoints[i+1][0] - waypoints[i][0]
            dy = waypoints[i+1][1] - waypoints[i][1]
            distance = math.sqrt(dx*dx + dy*dy)
            cumulative_distances.append(cumulative_distances[-1] + distance)

        total_length = cumulative_distances[-1]

        # Dibuja marcadores cada 100m SOLO en el rango visible
        marker_interval = 100.0
        distance_m = 0
        line_color = (180, 180, 180)  # Gris claro
        line_height = 20
        font = pygame.font.Font(None, 10)

        while distance_m <= total_length:
            # Encuentra el índice en waypoints más cercano a esta distancia
            idx = 0
            for i, cum_dist in enumerate(cumulative_distances):
                if cum_dist <= distance_m:
                    idx = i
                else:
                    break

            if idx >= len(waypoints) - 1:
                distance_m += marker_interval
                continue

            # Interpola posición entre waypoints
            dist_in_segment = distance_m - cumulative_distances[idx]
            segment_length = cumulative_distances[idx + 1] - cumulative_distances[idx]

            if segment_length > 0:
                t = dist_in_segment / segment_length
                marker_x = waypoints[idx][0] + t * (waypoints[idx+1][0] - waypoints[idx][0])
                marker_y = waypoints[idx][1] + t * (waypoints[idx+1][1] - waypoints[idx][1])
            else:
                marker_x, marker_y = waypoints[idx]

            # Solo dibuja si el marcador está dentro del viewport visible
            if visible_x_min <= marker_x <= visible_x_max:
                # Convierte a pantalla
                screen_pos = self.viewport.world_to_screen(Vector2(marker_x, marker_y))

                # Dibuja pequeña línea vertical
                pygame.draw.line(self.screen, line_color,
                               (int(screen_pos[0]), int(screen_pos[1]) - line_height),
                               (int(screen_pos[0]), int(screen_pos[1]) + line_height), 1)

                # Etiqueta con distancia
                text = font.render(f"{int(distance_m)}m", True, line_color)
                self.screen.blit(text, (int(screen_pos[0]) - 8, int(screen_pos[1]) - line_height - 12))

            distance_m += marker_interval

    def draw_speed_limit_sign(self, snapshot: RenderSnapshot) -> None:
        """Dibuja indicador de límite de velocidad UNA VEZ por segmento.

        Cuadrado blanco fijo de 32×32 píxeles con número negro indicando velocidad en km/h.
        Posicionado 1.0m hacia afuera del borde exterior de la calle (perpendicular).
        El tamaño no cambia con zoom ni con el número de carriles, pero su posición
        siempre sigue la geometría de la calle.

        Args:
            snapshot: RenderSnapshot con información de segmentos
        """
        if not snapshot.segments:
            # Fallback si no hay segmentos (usar lanes antiguos)
            if snapshot.lanes:
                for lane_id, waypoints, width_m in snapshot.lanes:
                    if len(waypoints) < 2:
                        continue
                    sign_position_s = 10.0
                    sign_world_pos = Vector2(waypoints[0][0] + sign_position_s, waypoints[0][1])
                    sign_screen = self.viewport.world_to_screen(sign_world_pos)
                    try:
                        lane = self.world.network.get_lane(lane_id)
                        speed_limit_kmh = int(lane.speed_limit_kmh)
                    except:
                        speed_limit_kmh = 60
                    sign_size = 20
                    offset_y = -40
                    rect = pygame.Rect(
                        int(sign_screen[0]) - sign_size // 2,
                        int(sign_screen[1]) + offset_y - sign_size // 2,
                        sign_size,
                        sign_size
                    )
                    pygame.draw.rect(self.screen, (255, 255, 255), rect)
                    pygame.draw.rect(self.screen, (0, 0, 0), rect, 2)
                    font = pygame.font.Font(None, 16)
                    text = font.render(str(speed_limit_kmh), True, (0, 0, 0))
                    text_rect = text.get_rect(center=(int(sign_screen[0]), int(sign_screen[1]) + offset_y))
                    self.screen.blit(text, text_rect)
            return

        # Dibuja UNO por segmento
        for segment in snapshot.segments:
            waypoints = segment['waypoints']
            speed_limit_kmh = int(segment['speed_limit_kmh'])
            total_width_m = segment['total_width_m']

            if len(waypoints) < 2:
                continue

            # Interpola posición a 16m desde el inicio del segmento
            target_distance_m = 16.0
            accumulated_distance = 0.0
            wx, wy = waypoints[0]

            for i in range(len(waypoints) - 1):
                w1 = waypoints[i]
                w2 = waypoints[i + 1]
                segment_length = math.sqrt((w2[0] - w1[0])**2 + (w2[1] - w1[1])**2)

                if accumulated_distance + segment_length >= target_distance_m:
                    # La posición objetivo está en este segmento
                    ratio = (target_distance_m - accumulated_distance) / segment_length if segment_length > 0 else 0
                    wx = w1[0] + ratio * (w2[0] - w1[0])
                    wy = w1[1] + ratio * (w2[1] - w1[1])
                    break
                accumulated_distance += segment_length
            else:
                # Si no alcanza 20m, usa el último waypoint
                wx, wy = waypoints[-1]

            # Calcula vector normal en el siguiente punto
            next_idx = min(1, len(waypoints) - 1)
            next_wx, next_wy = waypoints[next_idx]
            dx = next_wx - waypoints[0][0]
            dy = next_wy - waypoints[0][1]
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                nx = -dy / length
                ny = dx / length
            else:
                continue

            # Posición en mundo: borde exterior del asfalto + 20 píxeles adicionales
            half_total_width = total_width_m / 2.0
            scale = config.SCALE_PX_PER_M * self.viewport.camera.zoom
            # Convierte 20 píxeles a metros en mundo
            additional_offset_m = 20.0 / scale
            offset_m = half_total_width + config.ROAD_MARGIN_WIDTH_M + additional_offset_m

            sign_world_x = wx + nx * offset_m
            sign_world_y = wy + ny * offset_m
            sign_world_pos = Vector2(sign_world_x, sign_world_y)

            # Convierte a pantalla
            sign_screen = self.viewport.world_to_screen(sign_world_pos)

            # Tamaño fijo del signo en píxeles: mitad del anterior (16)
            sign_size = 22

            # Dibuja cuadrado blanco fuera de la calle
            rect = pygame.Rect(
                int(sign_screen[0]) - sign_size // 2,
                int(sign_screen[1]) - sign_size // 2,
                sign_size,
                sign_size
            )
            pygame.draw.rect(self.screen, (255, 255, 255), rect)  # Blanco
            pygame.draw.rect(self.screen, (0, 0, 0), rect, 2)    # Borde negro

            # Dibuja número en negro
            font_size = max(16, sign_size // 2.5)
            font = pygame.font.Font(None, font_size)
            text = font.render(str(speed_limit_kmh), True, (0, 0, 0))
            text_rect = text.get_rect(center=(int(sign_screen[0]), int(sign_screen[1])))
            self.screen.blit(text, text_rect)

    def draw_stop_signs(self, snapshot: RenderSnapshot) -> None:
        """Dibuja señales de alto en cada carril.

        Octágono rojo + franja blanca de parada.

        Args:
            snapshot: RenderSnapshot con información de lanes
        """
        if not snapshot.lanes:
            return

        for lane_id, waypoints, width_m in snapshot.lanes:
            if len(waypoints) < 2:
                continue

            try:
                lane = self.world.network.get_lane(lane_id)
                if not hasattr(lane, 'stop_signs') or not lane.stop_signs:
                    continue

                for stop_sign in lane.stop_signs:
                    if not stop_sign.is_active:
                        continue

                    # Posición de la señal en el mundo
                    stop_world_pos = Vector2(waypoints[0][0] + stop_sign.position_s, waypoints[0][1])
                    stop_screen = self.viewport.world_to_screen(stop_world_pos)

                    # Franja blanca en el suelo (mismo grosor que las franjas de carril)
                    # Dibuja línea blanca perpendicular al carril
                    half_width = config.LANE_WIDTH_M / 2.0

                    # Calcula normal (perpendicular al carril en ese punto)
                    # Usa dirección entre primer y último waypoint
                    lane_start = Vector2(waypoints[0][0], waypoints[0][1])
                    lane_end = Vector2(waypoints[-1][0], waypoints[-1][1])
                    lane_dir = (lane_end - lane_start).normalize()
                    lane_normal = Vector2(-lane_dir.y, lane_dir.x)

                    left_pos = stop_world_pos + lane_normal * half_width
                    right_pos = stop_world_pos - lane_normal * half_width

                    left_screen = self.viewport.world_to_screen(left_pos)
                    right_screen = self.viewport.world_to_screen(right_pos)

                    pygame.draw.line(self.screen, (255, 255, 255),
                                   (int(left_screen[0]), int(left_screen[1])),
                                   (int(right_screen[0]), int(right_screen[1])), 3)

                    # Octágono rojo (señal de alto) encima de la calle
                    offset_y = -35
                    sign_size = 20
                    sign_radius = sign_size // 2

                    # Crea puntos del octágono (8 puntos)
                    import math
                    octagon_points = []
                    for i in range(8):
                        angle = i * math.pi / 4  # 45 grados entre puntos
                        x = int(stop_screen[0]) + int(sign_radius * math.cos(angle))
                        y = int(stop_screen[1]) + offset_y + int(sign_radius * math.sin(angle))
                        octagon_points.append((x, y))

                    # Dibuja octágono rojo
                    pygame.draw.polygon(self.screen, (200, 0, 0), octagon_points)  # Rojo oscuro
                    pygame.draw.polygon(self.screen, (255, 0, 0), octagon_points, 2)  # Borde rojo brillante

                    # Dibuja "STOP" en blanco
                    font = pygame.font.Font(None, 14)
                    text = font.render("STOP", True, (255, 255, 255))
                    text_rect = text.get_rect(center=(int(stop_screen[0]), int(stop_screen[1]) + offset_y))
                    self.screen.blit(text, text_rect)

            except Exception:
                continue

    def draw_lane_cached(self, snapshot: RenderSnapshot) -> None:
        """Dibuja segmentos usando cache estático.

        El clipping ya está aplicado en run_frame(), así que solo dibujamos.

        Args:
            snapshot: RenderSnapshot con información de segmentos
        """
        # Si no hay segmentos ni lanes, no dibuja nada (ej: escenarios de calibración)
        if not snapshot.segments and not snapshot.lanes:
            return

        if not self.lanes_cache_valid or self.lanes_cache_surface is None:
            # Usa segmentos (multi-carril) si están disponibles, si no usa lanes
            if snapshot.segments:
                self.lanes_cache_surface = self._build_segments_cache(snapshot)
            else:
                self.lanes_cache_surface = self._build_lanes_cache(snapshot)
            self.lanes_cache_valid = True

        if self.lanes_cache_surface is not None:
            self.screen.blit(self.lanes_cache_surface, (0, 0))

    def draw_agent(self, agent_id: int, world_pos: Vector2, heading: float,
                   speed_kmh: float, selected: bool = False, lane_s: float = None) -> None:
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
        elif speed_kmh == 0.0:
            color = config.COLOR_CAR_STOPPED
        elif speed_kmh < 2.0:
            color = config.COLOR_CAR_SLOW
        elif speed_kmh > 15.0:
            color = config.COLOR_CAR_FAST
        else:
            color = config.COLOR_CAR_DEFAULT

        # Crea rectángulo centrado con píxeles enteros
        # Una mitad redondea hacia abajo, la otra hacia arriba para centrado perfecto
        half_length_lower = car_length_px // 2
        half_length_upper = car_length_px - half_length_lower
        half_height_lower = car_width_px // 2
        half_height_upper = car_width_px - half_height_lower

        left = int(screen_x - half_length_lower)
        top = int(screen_y - half_height_lower)
        rect = pygame.Rect(left, top, car_length_px, car_width_px)


        # Dibuja rectángulo (sin rotación por ahora para performance)
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, config.COLOR_TEXT, rect, 1)

        # Dibuja ID del agente con color de contraste automático
        if config.DEBUG_OVERLAY_ENABLED:
            # Calcula luminancia del color del carro
            r, g, b = color
            luminance = 0.299 * r + 0.587 * g + 0.114 * b

            # Si el fondo es claro (luminancia > 127), usa texto negro; si es oscuro, usa blanco
            text_color = (0, 0, 0) if luminance > 127 else (255, 255, 255)

            font_speed = pygame.font.Font(None, 12)
            text = font_speed.render(f"{speed_kmh:.1f}", True, text_color)
            self.screen.blit(text, (screen_x - 10, screen_y - 5))

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
                if event.key == pygame.K_r:
                    # Reset del escenario
                    self.reset_requested = True
                    return False  # Sale del loop para resetear


            # Left click: spawn agente
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                world_pos = self.viewport.screen_to_world(event.pos)
                lane, s = self._find_nearest_lane_s(world.network, world_pos)

                if lane is not None:
                    # Spawn nuevo agente con velocidad inicial
                    import random
                    from kars.physics.models import Vector2, KinematicState

                    agent_id = world.get_next_agent_id()
                    agent = CarAgent(
                        agent_id=agent_id,
                        current_lane_id=lane.lane_id,
                        position_along_lane_s=s,
                        lateral_offset=0.0,
                    )

                    # Muestrea multiplicador de velocidad
                    speed_multiplier = random.gauss(1.0, 0.2)
                    speed_multiplier = max(0.5, min(1.5, speed_multiplier))
                    object.__setattr__(agent, 'speed_multiplier', speed_multiplier)

                    # Configura velocidad deseada basada en límite de calle
                    lane_speed_limit_kmh = lane.speed_limit_kmh
                    desired_speed_ms = (lane_speed_limit_kmh * speed_multiplier) / 3.6
                    object.__setattr__(agent.idm_behavior, 'desired_speed', desired_speed_ms)

                    world_pos_snapped = lane.world_position_at(s, 0.0)
                    agent.set_position_world(world_pos_snapped, heading=0.0)

                    # Establece velocidad inicial = velocidad deseada del carril
                    # Así el carro avanza con precaución respetando obstáculos
                    initial_velocity_ms = desired_speed_ms
                    new_kinematic_state = KinematicState(
                        position=world_pos_snapped,
                        velocity=Vector2(initial_velocity_ms, 0.0),
                        acceleration=Vector2(0, 0),
                        heading=0.0,
                    )
                    object.__setattr__(agent, 'kinematic_state', new_kinematic_state)

                    world.add_agent(agent)

            # Right click: remove agente (o click en agente para seguir)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                # Primero intenta encontrar agente en esta posición
                # Si no, se consume para no disparar pan
                pass

            # Propagar eventos al HUD
            self.hud.handle_event(event, world)

        return True

    def update_fps(self) -> None:
        """Actualiza cálculo de FPS."""
        now = time.time()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        self.frame_times.append(dt)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)

        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.current_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0

    def run_frame(self, world: World) -> bool:
        """Ejecuta un frame del simulador.

        Args:
            world: World a simular

        Returns:
            True si debe continuar, False para salir
        """
        self.world = world  # Guarda referencia para acceso en draw_agent

        # Maneja eventos
        if not self.handle_events(world):
            return False

        # Simula un tick si no está pausado
        if not self.hud.is_paused:
            world.tick()

        # Actualiza viewport (follow mode)
        snapshot = world.build_render_snapshot()
        self.viewport.update(snapshot, world.agents)

        # DESHABILITADO: Cámara fija (no sigue agentes)
        # Si no hay follow mode, centra en promedio de posiciones de agentes
        # if self.viewport.follow_agent_id is None and snapshot.agents:
        #     avg_s = sum(s for _, _, _, _, _, s in snapshot.agents) / len(snapshot.agents)
        #     lane = world.network.get_lane(snapshot.agents[0][4])
        #     avg_world_pos = lane.world_position_at(avg_s, 0.0)
        #     self.viewport.camera.center_on(avg_world_pos)

        # Configuración inicial: centra en todas las calles (solo una vez)
        if not self.initial_zoom_done and len(snapshot.lanes) > 0:
            # Determina viewport: visible_length_m o viewport_x_min/max
            x_min = None
            x_max = None
            explicit_viewport_x = False  # Marca si el viewport X fue explícitamente configurado

            if 'visible_length_m' in self.camera_config:
                # Nueva estructura: visible_length_m define cuánto ver en pantalla (0 a visible_length)
                # Márgenes existen en el mundo (-20 a 0, visible_length a visible_length+20) pero no se ven
                visible_length = self.camera_config['visible_length_m']
                x_min = 0  # La pantalla muestra desde 0m
                x_max = visible_length  # Hasta visible_length_m
                explicit_viewport_x = True
            elif 'viewport_x_min_m' in self.camera_config and 'viewport_x_max_m' in self.camera_config:
                # Formato antiguo: viewport_x_min/max (compatibilidad)
                x_min = self.camera_config['viewport_x_min_m']
                x_max = self.camera_config['viewport_x_max_m']
                explicit_viewport_x = True

            # Si se definió viewport, úsalo
            if x_min is not None and x_max is not None:
                # Usa Y explícito si se proporciona, si no calcula desde lanes
                explicit_viewport_y = False
                if 'viewport_y_min_m' in self.camera_config and 'viewport_y_max_m' in self.camera_config:
                    min_y = self.camera_config['viewport_y_min_m']
                    max_y = self.camera_config['viewport_y_max_m']
                    explicit_viewport_y = True
                else:
                    # Obtén altura máxima de los carriles para centrar verticalmente
                    min_y, max_y = float('inf'), float('-inf')
                    for lane_id, waypoints, width_m in snapshot.lanes:
                        for wx, wy in waypoints:
                            min_y = min(min_y, wy - width_m/2)
                            max_y = max(max_y, wy + width_m/2)

                viewport_width_m = x_max - x_min
                viewport_height_m = max_y - min_y if max_y != float('-inf') else 10.0

                # Si Y fue explícitamente configurado, ajustarlo para que la relación de aspecto coincida
                # con el drawable area, manteniendo el centro en Y
                if explicit_viewport_y:
                    # Calcula la altura necesaria para mantener la relación de aspecto del drawable area
                    desired_height_m = viewport_width_m * self.drawable_height_px / self.width_px
                    center_y = (min_y + max_y) / 2.0
                    min_y = center_y - desired_height_m / 2.0
                    max_y = center_y + desired_height_m / 2.0
                    viewport_height_m = desired_height_m

                # Calcula zoom para que el viewport quepa bien en pantalla
                scale_px_per_m = config.SCALE_PX_PER_M

                # Usa zoom_x directamente ya que el Y ha sido ajustado para coincidir con la relación de aspecto
                zoom_x = self.width_px / (viewport_width_m * scale_px_per_m)
                final_zoom = zoom_x
                self.viewport.camera.set_zoom(final_zoom)
                self.lanes_cache_valid = False  # Invalida cache cuando cambia el zoom

                # Centra en el viewport configurado
                # El centro X es en coordenadas mundo, el centro Y también (la cámara maneja la traducción a pantalla)
                center_x = (x_min + x_max) / 2.0
                center_y = (min_y + max_y) / 2.0 if max_y != float('-inf') else 0.0
                self.viewport.camera.center_on(Vector2(center_x, center_y))

                # Guarda los bounds explícitos del viewport para usar en clipping
                self.explicit_viewport_x_min = x_min if explicit_viewport_x else None
                self.explicit_viewport_x_max = x_max if explicit_viewport_x else None
                self.explicit_viewport_y_min = min_y if explicit_viewport_y else None
                self.explicit_viewport_y_max = max_y if explicit_viewport_y else None

            else:
                # Auto-fit: calcula bounding box de todas las calles
                min_x, max_x = float('inf'), float('-inf')
                min_y, max_y = float('inf'), float('-inf')

                for lane_id, waypoints, width_m in snapshot.lanes:
                    for wx, wy in waypoints:
                        min_x = min(min_x, wx)
                        max_x = max(max_x, wx)
                        min_y = min(min_y, wy - width_m/2)
                        max_y = max(max_y, wy + width_m/2)

                lane_length_m = max_x - min_x
                lane_height_m = max_y - min_y

                # Calcula zoom para que todo quepa en el espacio dibujable (sin banners del HUD)
                scale_px_per_m = config.SCALE_PX_PER_M
                zoom_x = self.width_px / (lane_length_m * scale_px_per_m)
                zoom_y = self.drawable_height_px / (lane_height_m * scale_px_per_m)
                required_zoom = min(zoom_x, zoom_y)
                self.viewport.camera.set_zoom(required_zoom)
                self.lanes_cache_valid = False  # Invalida cache cuando cambia el zoom

                # Centra en el medio del bounding box
                center_x = (min_x + max_x) / 2.0
                center_y = (min_y + max_y) / 2.0
                self.viewport.camera.center_on(Vector2(center_x, center_y))

            self.initial_zoom_done = True

        # Actualiza HUD
        self.hud.update(snapshot, world)

        # Aplica clipping al viewport visible ANTES de dibujar
        # Usa los bounds explícitos si están disponibles, si no usa los de la cámara
        if self.explicit_viewport_x_min is not None and self.explicit_viewport_x_max is not None:
            visible_x_min = self.explicit_viewport_x_min
            visible_x_max = self.explicit_viewport_x_max
        else:
            visible_x_min, _, visible_x_max, _ = self.viewport.camera.get_visible_world_bounds()

        if self.explicit_viewport_y_min is not None and self.explicit_viewport_y_max is not None:
            visible_y_min = self.explicit_viewport_y_min
            visible_y_max = self.explicit_viewport_y_max
        else:
            _, visible_y_min, _, visible_y_max = self.viewport.camera.get_visible_world_bounds()

        top_left_screen = self.viewport.world_to_screen(Vector2(visible_x_min, visible_y_min))
        bottom_right_screen = self.viewport.world_to_screen(Vector2(visible_x_max, visible_y_max))

        clip_rect = pygame.Rect(
            min(int(top_left_screen[0]), int(bottom_right_screen[0])),
            min(int(top_left_screen[1]), int(bottom_right_screen[1])),
            abs(int(bottom_right_screen[0]) - int(top_left_screen[0])),
            abs(int(bottom_right_screen[1]) - int(top_left_screen[1]))
        )
        self.screen.set_clip(clip_rect)

        # Dibuja escena (ya con clipping aplicado)
        self.screen.fill(config.BACKGROUND_COLOR)

        # Dibuja lanes (cache)
        self.draw_lane_cached(snapshot)

        # Dibuja malla de calibración si está configurada en camera_config (después de lanes para que sea visible)
        if self.camera_config.get('show_grid', False):
            self.draw_grid()

        # Dibuja agentes
        for agent_id, world_pos, heading, speed_kmh, lane_id, s in snapshot.agents:
            is_selected = (agent_id == self.viewport.follow_agent_id)

            # Recalcula posición desde carril para asegurar alineación perfecta
            # Siempre usa offset=0 (centro del carril) para evitar desalineación
            try:
                lane = self.world.network.get_lane(lane_id)
                corrected_world_pos = lane.world_position_at(s, 0.0)
                corrected_heading = lane.heading_at(s)
                self.draw_agent(agent_id, corrected_world_pos, corrected_heading, speed_kmh, is_selected, lane_s=s)
            except Exception as e:
                # Si hay error, usa la posición original
                self.draw_agent(agent_id, world_pos, heading, speed_kmh, is_selected, lane_s=s)

        # Dibuja marcadores de distancia cada 100 metros (solo si está habilitado)
        if self.camera_config.get('show_distance_markers', False):
            self.draw_distance_markers(snapshot)

        # Dibuja indicador de límite de velocidad
        self.draw_speed_limit_sign(snapshot)

        # Dibuja señales de alto
        self.draw_stop_signs(snapshot)

        # Dibuja obstáculos permanentes
        self.draw_obstacles(snapshot)

        # Dibuja línea de parada (blanca) donde deberían detenerse los vehículos (solo si hay obstáculos)
        if snapshot.obstacles:
            self.draw_stopping_line(snapshot)

        # Dibuja límites del viewport visible (para debug, se dibuja al final para no taparse)
        if self.camera_config.get('show_grid', False):
            self.draw_viewport_bounds()

        # Remueve clipping para que el HUD se dibuje sin restricciones
        self.screen.set_clip(None)


        # Actualiza FPS
        self.update_fps()

        # Dibuja HUD overlay (pasa FPS actual)
        self.hud.draw(self.screen, fps=self.current_fps)

        # Actualiza pantalla
        pygame.display.flip()

        # Limita FPS
        self.clock.tick(60)

        return True

    def close(self) -> None:
        """Cierra el renderer."""
        pygame.quit()
