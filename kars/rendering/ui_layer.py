"""UILayer: widgets custom de Pygame sin overhead (botones, sliders)."""

import pygame
from typing import Callable, Optional, List
import kars.config as config


class Button:
    """Botón interactivo dibujado en Pygame."""

    def __init__(self, rect: pygame.Rect, label: str, callback: Callable[[], None],
                 fg_color: tuple = config.COLOR_TEXT, bg_color: tuple = (70, 70, 70)):
        """Inicializa el botón.

        Args:
            rect: pygame.Rect con posición y tamaño
            label: Texto del botón
            callback: Función a ejecutar al hacer click
            fg_color: Color del texto
            bg_color: Color de fondo
        """
        self.rect = rect
        self.label = label
        self.callback = callback
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.hovered = False
        self.font = pygame.font.Font(None, 16)

    def handle_event(self, event: pygame.event.EventType) -> bool:
        """Maneja eventos del mouse.

        Args:
            event: pygame.event

        Returns:
            True si el evento fue consumido
        """
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True

        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Dibuja el botón."""
        color = (100, 100, 100) if self.hovered else self.bg_color
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, self.fg_color, self.rect, 2)

        text = self.font.render(self.label, True, self.fg_color)
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(text, text_rect)


class Slider:
    """Deslizador horizontal para valores numéricos."""

    def __init__(self, rect: pygame.Rect, min_val: float, max_val: float,
                 current_val: float, label: str = "", callback: Optional[Callable[[float], None]] = None):
        """Inicializa el slider.

        Args:
            rect: pygame.Rect con posición y tamaño (incluye track y label)
            min_val: Valor mínimo
            max_val: Valor máximo
            current_val: Valor inicial
            label: Etiqueta del slider (opcional)
            callback: Función callback cuando cambia el valor
        """
        self.rect = rect
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = current_val
        self.label = label
        self.callback = callback
        self.dragging = False
        self.font_small = pygame.font.Font(None, 12)
        self.font_label = pygame.font.Font(None, 14)

        # Track del slider (rectángulo horizontal)
        self.track_rect = pygame.Rect(rect.x + 50, rect.y + 10, rect.width - 100, 8)

    def _get_thumb_x(self) -> float:
        """Calcula posición X del thumb (círculo) basado en valor actual."""
        ratio = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        return self.track_rect.x + ratio * self.track_rect.width

    def handle_event(self, event: pygame.event.EventType) -> bool:
        """Maneja eventos del mouse.

        Args:
            event: pygame.event

        Returns:
            True si el evento fue consumido
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            thumb_x = self._get_thumb_x()
            thumb_rect = pygame.Rect(thumb_x - 6, self.track_rect.y - 4, 12, 16)
            if thumb_rect.collidepoint(event.pos):
                self.dragging = True
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            # Actualiza valor según posición del mouse
            mouse_x = event.pos[0]
            # Clamp a los bordes del track
            clamped_x = max(self.track_rect.x, min(self.track_rect.x + self.track_rect.width, mouse_x))
            # Convierte x a valor
            ratio = (clamped_x - self.track_rect.x) / self.track_rect.width
            new_val = self.min_val + ratio * (self.max_val - self.min_val)
            self.current_val = new_val
            if self.callback:
                self.callback(self.current_val)
            return True

        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Dibuja el slider."""
        # Track
        pygame.draw.rect(surface, config.COLOR_CHART_BG, self.track_rect)
        pygame.draw.rect(surface, config.COLOR_TEXT, self.track_rect, 1)

        # Thumb (círculo)
        thumb_x = self._get_thumb_x()
        thumb_y = self.track_rect.y + self.track_rect.height // 2
        pygame.draw.circle(surface, config.COLOR_CHART_LINE, (int(thumb_x), int(thumb_y)), 6)

        # Etiqueta
        if self.label:
            label_text = self.font_label.render(self.label, True, config.COLOR_TEXT)
            surface.blit(label_text, (self.rect.x, self.rect.y))

        # Valor actual
        val_text = self.font_small.render(f"{self.current_val:.2f}", True, config.COLOR_TEXT)
        surface.blit(val_text, (self.track_rect.x + self.track_rect.width + 10, self.track_rect.y + 2))


class Label:
    """Etiqueta de texto simple."""

    def __init__(self, pos: tuple, text: str = "", color: tuple = config.COLOR_TEXT, font_size: int = 12):
        """Inicializa la etiqueta.

        Args:
            pos: (x, y) posición en pantalla
            text: Texto a mostrar
            color: Color del texto
            font_size: Tamaño de la fuente
        """
        self.pos = pos
        self.text = text
        self.color = color
        self.font = pygame.font.Font(None, font_size)

    def set_text(self, text: str) -> None:
        """Actualiza el texto."""
        self.text = text

    def draw(self, surface: pygame.Surface) -> None:
        """Dibuja la etiqueta."""
        if self.text:
            text_surface = self.font.render(self.text, True, self.color)
            surface.blit(text_surface, self.pos)


class UILayer:
    """Contenedor de widgets que maneja eventos y renderizado."""

    def __init__(self):
        """Inicializa la capa de UI."""
        self.widgets: List = []

    def add(self, widget) -> None:
        """Agrega un widget.

        Args:
            widget: Button, Slider, Label, etc
        """
        self.widgets.append(widget)

    def handle_event(self, event: pygame.event.EventType) -> bool:
        """Propaga eventos a los widgets.

        Args:
            event: pygame.event

        Returns:
            True si algún widget consumió el evento
        """
        for widget in self.widgets:
            if hasattr(widget, 'handle_event'):
                if widget.handle_event(event):
                    return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Dibuja todos los widgets.

        Args:
            surface: pygame.Surface donde dibujar
        """
        for widget in self.widgets:
            if hasattr(widget, 'draw'):
                widget.draw(surface)
