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
        self.initial_zoom_done = False

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

    def draw_distance_markers(self, snapshot: RenderSnapshot) -> None:
        """Dibuja marcadores de distancia (inicio y final de pista).

        Args:
            snapshot: RenderSnapshot con información de lanes
        """
        if not snapshot.lanes:
            return

        lane_id, waypoints, width_m = snapshot.lanes[0]

        # Calcula longitud total del carril
        lane_length_m = sum(
            math.sqrt((waypoints[i+1][0] - waypoints[i][0])**2 +
                     (waypoints[i+1][1] - waypoints[i][1])**2)
            for i in range(len(waypoints)-1)
        )

        # Puntos de inicio y final
        start_pos = Vector2(waypoints[0][0], waypoints[0][1])
        end_pos = Vector2(waypoints[-1][0], waypoints[-1][1])

        # Convierte a pantalla
        start_screen = self.viewport.world_to_screen(start_pos)
        end_screen = self.viewport.world_to_screen(end_pos)

        # Dibuja líneas verticales en inicio y final
        line_color = (255, 100, 100)  # Rojo claro
        line_height = 50

        # Línea en inicio (0m)
        pygame.draw.line(self.screen, line_color,
                        (int(start_screen[0]), int(start_screen[1]) - line_height),
                        (int(start_screen[0]), int(start_screen[1]) + line_height), 3)

        # Línea en final (1000m)
        pygame.draw.line(self.screen, line_color,
                        (int(end_screen[0]), int(end_screen[1]) - line_height),
                        (int(end_screen[0]), int(end_screen[1]) + line_height), 3)

        # Etiquetas de distancia
        font = pygame.font.Font(None, 18)

        # "0m" en inicio
        text_0 = font.render("0m", True, line_color)
        self.screen.blit(text_0, (int(start_screen[0]) - 15, int(start_screen[1]) + line_height + 5))

        # "1000m" en final
        text_end = font.render(f"{lane_length_m:.0f}m", True, line_color)
        self.screen.blit(text_end, (int(end_screen[0]) - 35, int(end_screen[1]) + line_height + 5))

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
        elif speed_kmh > 15.0:
            color = config.COLOR_CAR_FAST
        elif speed_kmh < 2.0:
            color = config.COLOR_CAR_SLOW
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

            font_id = pygame.font.Font(None, 12)
            text = font_id.render(f"{agent_id}", True, text_color)
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

        # Configuración inicial: centra en el carril (solo una vez)
        if not self.initial_zoom_done and len(snapshot.lanes) > 0:
            lane_id, waypoints, width_m = snapshot.lanes[0]
            lane_length_m = sum(
                math.sqrt((waypoints[i+1][0] - waypoints[i][0])**2 +
                         (waypoints[i+1][1] - waypoints[i][1])**2)
                for i in range(len(waypoints)-1)
            )

            # Aplica factor de escala para que la visualización sea correcta
            # El viewport en el test mostraba bien con 3.0 px/m
            # Aquí necesitamos ajustar según el tamaño de la ventana
            self.viewport.camera.set_zoom(2.5)

            # Centra en el inicio (primeros 300m del carril)
            # El carril es horizontal en Y=0, no en Y=width/2
            center_x = 150.0
            center_y = 0.0
            self.viewport.camera.center_on(Vector2(center_x, center_y))

            self.initial_zoom_done = True

        # Actualiza HUD
        self.hud.update(snapshot, world)

        # Dibuja escena
        self.screen.fill(config.BACKGROUND_COLOR)

        # Dibuja lanes (cache)
        self.draw_lane_cached(snapshot)

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

        # Dibuja marcadores de distancia (inicio y final de pista)
        self.draw_distance_markers(snapshot)

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
