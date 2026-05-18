"""HUD: Ensamblador del overlay de interfaz (estadísticas, controles, gráfica)."""

import pygame
from kars.rendering.chart import SpeedChart
from kars.rendering.ui_layer import UILayer, Button, Slider, Label
from kars.simulation.world import RenderSnapshot, World
import kars.config as config


class HUD:
    """Assembler del HUD overlay que contiene stats, controls y gráfica."""

    def __init__(self, window_width: int, window_height: int):
        """Inicializa el HUD.

        Args:
            window_width: Ancho de ventana en píxeles
            window_height: Alto de ventana en píxeles
        """
        self.window_width = window_width
        self.window_height = window_height
        self.font_small = pygame.font.Font(None, 14)
        self.font_normal = pygame.font.Font(None, 16)
        self.font_large = pygame.font.Font(None, 20)

        # Crear chart de velocidad (esquina inferior derecha)
        chart_rect = pygame.Rect(
            window_width - config.HUD_CHART_W - 10,
            window_height - config.HUD_CHART_H - 70,
            config.HUD_CHART_W,
            config.HUD_CHART_H
        )
        self.speed_chart = SpeedChart(chart_rect, max_speed_kmh=25.0)

        # Crear UI layer con controles
        self.ui_layer = UILayer()

        # Callbacks para botones/sliders
        self.is_paused = False
        self.sim_speed = 1.0
        self.spawn_goal = 5

        # Botón Play/Pause (esquina inferior izquierda)
        pause_btn_rect = pygame.Rect(10, window_height - 50, 80, 40)
        self.btn_pause = Button(pause_btn_rect, "P: Pause", self._on_pause_click)
        self.ui_layer.add(self.btn_pause)

        # Slider de velocidad de simulación
        speed_slider_rect = pygame.Rect(100, window_height - 50, 150, 40)
        self.slider_speed = Slider(
            speed_slider_rect, min_val=0.1, max_val=5.0, current_val=1.0,
            label="Sim Speed", callback=self._on_speed_change
        )
        self.ui_layer.add(self.slider_speed)

        # Slider de número de agentes a mantener
        agents_slider_rect = pygame.Rect(260, window_height - 50, 150, 40)
        self.slider_agents = Slider(
            agents_slider_rect, min_val=1, max_val=50, current_val=5,
            label="Target Agents", callback=self._on_agents_change
        )
        self.ui_layer.add(self.slider_agents)

        # Labels para estadísticas (esquina superior izquierda)
        self.label_tick = Label((10, 10), "", font_size=12)
        self.label_time = Label((10, 25), "", font_size=12)
        self.label_agents = Label((10, 40), "", font_size=12)
        self.label_fps = Label((10, 55), "", font_size=12)
        self.label_speed = Label((10, 70), "", font_size=12)
        self.label_variance = Label((10, 85), "", font_size=12)

        # Hints de controles (esquina superior derecha)
        self.label_hints = Label(
            (window_width - 300, 10),
            "Click: spawn | RClick: remove | Click agent: follow | Scroll: zoom",
            font_size=11
        )

    def _on_pause_click(self) -> None:
        """Callback cuando se presiona el botón de pausa."""
        self.is_paused = not self.is_paused
        self.btn_pause.label = "Resume" if self.is_paused else "Pause"

    def _on_speed_change(self, value: float) -> None:
        """Callback cuando cambia el slider de velocidad."""
        self.sim_speed = value

    def _on_agents_change(self, value: float) -> None:
        """Callback cuando cambia el slider de agentes."""
        self.spawn_goal = int(value)

    def handle_event(self, event: pygame.event.EventType, world: World) -> bool:
        """Maneja eventos del HUD.

        Args:
            event: pygame.event
            world: World para modificar si es necesario

        Returns:
            True si el evento fue consumido
        """
        # Propagar a UI layer (buttons, sliders)
        if self.ui_layer.handle_event(event):
            # Aplicar cambios de sliders a world
            if not self.is_paused:
                world.set_sim_speed_factor(self.sim_speed)
            return True

        # Teclas de atajos
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._on_pause_click()
                if not self.is_paused:
                    world.set_sim_speed_factor(self.sim_speed)
                return True

        return False

    def update(self, snapshot: RenderSnapshot, world: World) -> None:
        """Actualiza el HUD con datos nuevos.

        Args:
            snapshot: RenderSnapshot con datos de simulación
            world: World para obtener estadísticas
        """
        # Actualizar gráfica
        self.speed_chart.update(snapshot.avg_speed_kmh)

        # Actualizar labels de estadísticas
        self.label_tick.set_text(f"Tick: {snapshot.tick_number}")
        self.label_time.set_text(f"Time: {snapshot.sim_time_s:.2f}s")
        self.label_agents.set_text(f"Agents: {len(world.agents)}")
        self.label_fps.set_text(f"FPS: {snapshot.fps:.1f}")
        self.label_speed.set_text(f"Avg Speed: {snapshot.avg_speed_kmh:.2f} km/h")

        # Obtener varianza si está disponible
        stats = world.stats_collector.get_last_tick()
        if stats:
            self.label_variance.set_text(f"Variance: {stats.avg_speed_variance:.4f}")

    def draw(self, surface: pygame.Surface) -> None:
        """Dibuja todo el HUD.

        Args:
            surface: pygame.Surface donde dibujar
        """
        # Fondo semi-transparente para HUD (top section)
        hud_top_rect = pygame.Rect(0, 0, self.window_width, 120)
        pygame.draw.rect(surface, config.COLOR_HUD_BG, hud_top_rect)

        # Separador
        pygame.draw.line(surface, config.COLOR_TEXT,
                        (0, 110), (self.window_width, 110), 1)

        # Dibujar labels de estadísticas
        self.label_tick.draw(surface)
        self.label_time.draw(surface)
        self.label_agents.draw(surface)
        self.label_fps.draw(surface)
        self.label_speed.draw(surface)
        self.label_variance.draw(surface)

        # Dibujar hints
        self.label_hints.draw(surface)

        # Fondo semi-transparente para control bar (bottom)
        control_bar_rect = pygame.Rect(0, self.window_height - config.HUD_BAR_HEIGHT,
                                       self.window_width, config.HUD_BAR_HEIGHT)
        pygame.draw.rect(surface, config.COLOR_HUD_BG, control_bar_rect)

        # Separador
        pygame.draw.line(surface, config.COLOR_TEXT,
                        (0, self.window_height - config.HUD_BAR_HEIGHT),
                        (self.window_width, self.window_height - config.HUD_BAR_HEIGHT), 1)

        # Dibujar UI widgets (buttons, sliders)
        self.ui_layer.draw(surface)

        # Dibujar chart
        self.speed_chart.draw(surface)
