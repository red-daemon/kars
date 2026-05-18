"""Recolector de estadisticas: observador puro del simulador."""

from dataclasses import dataclass, field
from typing import List, Dict
import statistics as stats_module


@dataclass
class TickStats:
    """Estadisticas de un tick."""
    tick_number: int
    sim_time_s: float
    num_agents: int
    avg_speed_kmh: float
    min_speed_kmh: float
    max_speed_kmh: float
    avg_speed_variance: float


class StatsCollector:
    """Recolecta estadisticas de la simulacion.

    Funciona como observador: recibe snapshots en cada tick,
    calcula metricas, pero NO afecta la simulacion.
    """

    def __init__(self):
        """Inicializa colector."""
        self.ticks: List[TickStats] = []
        self.enabled = True

    def record_tick(self, tick_number: int, sim_time_s: float, agents: List) -> None:
        """Registra estadisticas de un tick.

        Args:
            tick_number: Numero del tick
            sim_time_s: Tiempo simulado en segundos
            agents: Lista de CarAgent en la simulacion
        """
        if not self.enabled or not agents:
            return

        # Recolecta velocidades
        speeds_kmh = [agent.speed_kmh() for agent in agents]

        # Calcula metricas
        avg_speed = stats_module.mean(speeds_kmh) if speeds_kmh else 0.0
        min_speed = min(speeds_kmh) if speeds_kmh else 0.0
        max_speed = max(speeds_kmh) if speeds_kmh else 0.0

        # Varianza (desviacion estandar)
        variance = stats_module.stdev(speeds_kmh) if len(speeds_kmh) > 1 else 0.0

        tick_stat = TickStats(
            tick_number=tick_number,
            sim_time_s=sim_time_s,
            num_agents=len(agents),
            avg_speed_kmh=avg_speed,
            min_speed_kmh=min_speed,
            max_speed_kmh=max_speed,
            avg_speed_variance=variance,
        )

        self.ticks.append(tick_stat)

    def get_last_tick(self) -> TickStats | None:
        """Retorna estadisticas del ultimo tick registrado."""
        return self.ticks[-1] if self.ticks else None

    def get_stats_history(self) -> List[TickStats]:
        """Retorna historial completo de estadisticas."""
        return self.ticks.copy()

    def clear(self) -> None:
        """Limpia el historial."""
        self.ticks.clear()

    def get_summary(self) -> Dict:
        """Retorna resumen de estadisticas para el usuario."""
        if not self.ticks:
            return {}

        avg_speeds = [t.avg_speed_kmh for t in self.ticks]
        total_time = self.ticks[-1].sim_time_s if self.ticks else 0.0

        return {
            "total_ticks": len(self.ticks),
            "total_sim_time_s": total_time,
            "avg_agent_speed_kmh": stats_module.mean(avg_speeds) if avg_speeds else 0.0,
            "max_agent_speed_kmh": max([t.max_speed_kmh for t in self.ticks]) if self.ticks else 0.0,
        }
