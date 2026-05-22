"""Chart: Gráfica en tiempo real de velocidad promedio."""

import pygame
from collections import deque
import kars.config as config


class SpeedChart:
    """Mini gráfica que muestra los últimos 60 ticks de velocidad promedio.

    Renderiza como polyline en Pygame, mostrando la convergencia de velocidad
    durante la simulación. Útil para observar comportamiento emergente en vivo.
    """

    def __init__(self, rect: pygame.Rect, max_speed_kmh: float = 25.0):
        """Inicializa el chart.

        Args:
            rect: pygame.Rect define posición (x,y) y tamaño (w,h) en pantalla
            max_speed_kmh: Escala inicial del eje Y (escala dinámicamente según datos)
        """
        self.rect = rect
        self.initial_max_speed = max_speed_kmh
        self.max_speed_kmh = max_speed_kmh
        self.history = deque(maxlen=60)  # últimos 60 valores
        self.font_small = pygame.font.Font(None, 14)

    def update(self, avg_speed_kmh: float) -> None:
        """Agrega nuevo valor a la historia y escala dinámicamente.

        Args:
            avg_speed_kmh: Velocidad promedio del último tick
        """
        speed = max(0.0, avg_speed_kmh)
        self.history.append(speed)

        # Escala dinámica: si la velocidad supera el máximo actual, aumenta la escala
        if speed > self.max_speed_kmh:
            # Redondea hacia arriba al múltiplo de 5 km/h más cercano
            self.max_speed_kmh = ((speed // 5) + 1) * 5
        # Si no hay datos cercanos al máximo, reduce la escala
        elif len(self.history) > 30:
            max_in_history = max(self.history)
            min_scale = self.initial_max_speed
            # Solo reduce si todos los valores están muy por debajo
            if max_in_history < self.max_speed_kmh / 2 and self.max_speed_kmh > min_scale:
                self.max_speed_kmh = max(min_scale, ((max_in_history * 1.2) // 5 + 1) * 5)

    def draw(self, surface: pygame.Surface) -> None:
        """Dibuja el chart en la superficie.

        Args:
            surface: pygame.Surface donde dibujar
        """
        # Fondo del chart
        pygame.draw.rect(surface, config.COLOR_CHART_BG, self.rect)
        pygame.draw.rect(surface, config.COLOR_TEXT, self.rect, 1)

        if len(self.history) < 2:
            return

        # Convierte historia a puntos en pantalla
        points = []
        for i, speed in enumerate(self.history):
            # Mapea índice (0..59) a x en el rect
            x = self.rect.x + (i / (len(self.history) - 1)) * self.rect.width
            # Mapea velocidad (0..max) a y invertida (top = max)
            norm_speed = speed / self.max_speed_kmh
            y = self.rect.y + self.rect.height - (norm_speed * self.rect.height)
            points.append((x, y))

        # Dibuja línea de datos
        if len(points) >= 2:
            for i in range(len(points) - 1):
                pygame.draw.line(surface, config.COLOR_CHART_LINE,
                               (int(points[i][0]), int(points[i][1])),
                               (int(points[i+1][0]), int(points[i+1][1])), 2)

        # Dibuja ejes
        # Eje horizontal (bottom)
        pygame.draw.line(surface, config.COLOR_TEXT,
                        (self.rect.x, self.rect.y + self.rect.height),
                        (self.rect.x + self.rect.width, self.rect.y + self.rect.height), 1)

        # Etiquetas de velocidad (0, max/2, max)
        for label_speed in [0, self.max_speed_kmh / 2, self.max_speed_kmh]:
            norm_speed = label_speed / self.max_speed_kmh
            y = self.rect.y + self.rect.height - (norm_speed * self.rect.height)
            # Dibuja marca
            pygame.draw.line(surface, config.COLOR_TEXT,
                            (self.rect.x - 3, y),
                            (self.rect.x, y), 1)
            # Etiqueta
            text = self.font_small.render(f"{label_speed:.0f}", True, config.COLOR_TEXT)
            surface.blit(text, (self.rect.x - 25, y - 5))
