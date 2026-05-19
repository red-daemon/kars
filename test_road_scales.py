#!/usr/bin/env python3
"""Test: muestra 5 escalas diferentes de la calle para elegir."""

import sys
sys.path.insert(0, '/c/Users/bgaxiola/OneDrive - Capgemini/Projects/Kars')

import pygame
import math
from kars.physics.models import Vector2, Waypoint
from kars.environment.lane import Lane
from kars.environment.segment import RoadSegment
from kars.environment.road_network import RoadNetwork
from kars.simulation.world import World
from kars.rendering.camera import Camera
import kars.config as config

def draw_road_section(surface, camera, lane, rect):
    """Dibuja una sección de carretera dentro de un rectángulo."""
    # Crea surface temporal para esta sección
    temp_surface = pygame.Surface((rect.width, rect.height))
    temp_surface.fill((20, 20, 20))

    waypoints = lane.waypoints

    # Estructura de la calle (en metros)
    half_road = config.LANE_WIDTH_M / 2.0
    margin_outer = config.ROAD_MARGIN_WIDTH_M + config.LANE_MARKING_WIDTH_M + half_road
    border_outer = half_road
    border_inner = half_road + config.LANE_MARKING_WIDTH_M

    # Crea offsets para las líneas paralelas
    offset_margin_left = []
    offset_border_left_outer = []
    offset_border_left_inner = []
    offset_border_right_inner = []
    offset_border_right_outer = []
    offset_margin_right = []

    for idx, wp in enumerate(waypoints):
        wx, wy = wp.position.x, wp.position.y

        # Calcula normal perpendicular
        if idx < len(waypoints) - 1:
            next_wp = waypoints[idx + 1]
            next_wx, next_wy = next_wp.position.x, next_wp.position.y
            dx = next_wx - wx
            dy = next_wy - wy
        else:
            prev_wp = waypoints[idx - 1]
            prev_wx, prev_wy = prev_wp.position.x, prev_wp.position.y
            dx = wx - prev_wx
            dy = wy - prev_wy

        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            nx = -dy / length
            ny = dx / length
        else:
            nx, ny = 0, 0

        # Calcula puntos
        margin_left_x = wx + nx * margin_outer
        margin_left_y = wy + ny * margin_outer
        border_left_outer_x = wx + nx * border_outer
        border_left_outer_y = wy + ny * border_outer
        border_left_inner_x = wx + nx * border_inner
        border_left_inner_y = wy + ny * border_inner
        border_right_inner_x = wx - nx * border_inner
        border_right_inner_y = wy - ny * border_inner
        border_right_outer_x = wx - nx * border_outer
        border_right_outer_y = wy - ny * border_outer
        margin_right_x = wx - nx * margin_outer
        margin_right_y = wy - ny * margin_outer

        offset_margin_left.append(camera.world_to_screen(Vector2(margin_left_x, margin_left_y)))
        offset_border_left_outer.append(camera.world_to_screen(Vector2(border_left_outer_x, border_left_outer_y)))
        offset_border_left_inner.append(camera.world_to_screen(Vector2(border_left_inner_x, border_left_inner_y)))
        offset_border_right_inner.append(camera.world_to_screen(Vector2(border_right_inner_x, border_right_inner_y)))
        offset_border_right_outer.append(camera.world_to_screen(Vector2(border_right_outer_x, border_right_outer_y)))
        offset_margin_right.append(camera.world_to_screen(Vector2(margin_right_x, margin_right_y)))

    def draw_strip(color, left_line, right_line):
        """Dibuja un polígono entre dos líneas."""
        for i in range(len(left_line) - 1):
            p1 = (int(left_line[i][0]), int(left_line[i][1]))
            p2 = (int(left_line[i+1][0]), int(left_line[i+1][1]))
            p3 = (int(right_line[i+1][0]), int(right_line[i+1][1]))
            p4 = (int(right_line[i][0]), int(right_line[i][1]))

            quad = [p1, p2, p3, p4]
            pygame.draw.polygon(temp_surface, color, quad)

    # Dibuja en orden
    draw_strip(config.COLOR_ROAD_MARGIN, offset_margin_left, offset_border_left_outer)
    draw_strip(config.COLOR_LANE_BORDER, offset_border_left_outer, offset_border_left_inner)
    draw_strip(config.COLOR_LANE_ROAD, offset_border_left_inner, offset_border_right_inner)
    draw_strip(config.COLOR_LANE_BORDER, offset_border_right_inner, offset_border_right_outer)
    draw_strip(config.COLOR_ROAD_MARGIN, offset_border_right_outer, offset_margin_right)

    # Blitea la superficie temporal al rectángulo en la pantalla principal
    surface.blit(temp_surface, (rect.x, rect.y))

def main():
    """Muestra 5 escalas de calle diferentes."""
    pygame.init()

    width_px = 1200
    height_px = 900
    screen = pygame.display.set_mode((width_px, height_px))
    pygame.display.set_caption("Elige la escala de la calle - Presiona una tecla para salir")

    # Crea carril (1000m de largo, horizontal)
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

    # 5 escalas diferentes (px/m)
    scales = [
        ("Escala 1: 1.2 px/m (vista amplia)", 1.2),
        ("Escala 2: 3.0 px/m", 3.0),
        ("Escala 3: 5.0 px/m", 5.0),
        ("Escala 4: 8.0 px/m (actual)", 8.0),
        ("Escala 5: 12.0 px/m (zoom in)", 12.0),
    ]

    clock = pygame.time.Clock()
    running = True

    print("\nMostrando 5 escalas de carretera...")
    print("Presiona cualquier tecla para salir\n")

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                running = False

        # Fondo
        screen.fill((30, 30, 30))

        # Dibuja 5 secciones: cada una ocupa 1/5 de la pantalla
        section_height = height_px // 5
        margin_top = 40

        for i, (label, scale) in enumerate(scales):
            # Rectángulo para esta sección (con márgen)
            rect_x = 15
            rect_y = margin_top + i * section_height + 10
            rect_w = width_px - 30
            rect_h = section_height - 20

            # Crea cámara: calcula qué parte del mundo cabe en el rectángulo
            # con la escala deseada
            camera = Camera(rect_w, rect_h)

            # Calcular cuánto del mundo se ve en esta escala
            visible_width_m = rect_w / scale
            visible_height_m = rect_h / scale

            # Establece la escala base directamente (sin zoom)
            camera.base_scale = scale
            camera.zoom = 1.0

            # Centra en la carretera, mostrando ±(visible_width/2) de ancho
            camera.center_on(Vector2(500, 0))

            # Dibuja etiqueta
            font_label = pygame.font.Font(None, 18)
            text = font_label.render(label, True, (255, 255, 255))
            screen.blit(text, (30, rect_y - 25))

            # Dibuja la carretera dentro del rectángulo
            draw_road_section(screen, camera, lane, pygame.Rect(rect_x, rect_y, rect_w, rect_h))

            # Borde del rectángulo
            pygame.draw.rect(screen, (80, 80, 80), (rect_x, rect_y, rect_w, rect_h), 1)

        # Instrucciones
        font_small = pygame.font.Font(None, 14)
        instr = font_small.render("Presiona cualquier tecla para salir | Elige el tamaño que prefieres", True, (180, 180, 180))
        screen.blit(instr, (20, height_px - 25))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    print("\nCierre la ventana o presionó una tecla.")
    print("\nDime cuál escala te gusta más (1-5):")

if __name__ == "__main__":
    main()
