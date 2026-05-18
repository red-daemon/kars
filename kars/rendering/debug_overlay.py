"""Debug overlay: HUD con informacion de la simulacion."""

from typing import Tuple
import math


class DebugOverlay:
    """Renderiza HUD de debug sobre la pantalla."""

    def __init__(self, enabled: bool = True):
        """Inicializa overlay.

        Args:
            enabled: Si esta habilitado
        """
        self.enabled = enabled

    def render_text_lines(self) -> list:
        """Retorna lineas de texto a mostrar en HUD.

        Retorna lista de (texto, x, y, color) para que el renderer dibuje.
        """
        return []  # Implementacion en renderer

    def format_stats(self, snapshot) -> str:
        """Formatea estadisticas para mostrar."""
        lines = []
        lines.append(f"Tick: {snapshot.tick_number}")
        lines.append(f"Time: {snapshot.sim_time_s:.2f}s")
        lines.append(f"Agents: {len(snapshot.agents)}")
        lines.append(f"Avg Speed: {snapshot.avg_speed_kmh:.1f} km/h")
        lines.append(f"FPS: {snapshot.fps:.1f}")

        return "\n".join(lines)

    def format_agent_info(self, agent_id: int, speed_kmh: float, s: float, lane_id: str) -> str:
        """Formatea informacion de un agente."""
        return f"A{agent_id}: {speed_kmh:.1f}km/h @ {s:.0f}m"
