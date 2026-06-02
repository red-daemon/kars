"""Scheduler: determina el orden de ejecucion en cada tick."""

from enum import Enum
from typing import List, Callable


class UpdatePhase(Enum):
    """Fases de actualizacion en el tick maestro."""
    PERCEPTION = 1
    DECISION = 2
    LANE_CHANGE = 2.5
    PHYSICS = 3
    ENVIRONMENT = 4
    SPATIAL_INDEX = 5
    STATISTICS = 6
    RENDER = 7


class Scheduler:
    """Determina el orden estricto de actualizacion en cada tick.

    Garantiza que todos los agentes leen estado N antes de escribir N+1.
    """

    def __init__(self):
        """Inicializa scheduler con orden por defecto."""
        self.phase_order = [
            UpdatePhase.PERCEPTION,
            UpdatePhase.DECISION,
            UpdatePhase.LANE_CHANGE,
            UpdatePhase.PHYSICS,
            UpdatePhase.ENVIRONMENT,
            UpdatePhase.SPATIAL_INDEX,
            UpdatePhase.STATISTICS,
            UpdatePhase.RENDER,
        ]

        # Callbacks ejecutables en cada fase
        self.callbacks: dict = {phase: [] for phase in UpdatePhase}

    def register_callback(self, phase: UpdatePhase, callback: Callable) -> None:
        """Registra un callback para ejecutarse en una fase.

        Args:
            phase: UpdatePhase en la que ejecutar
            callback: Funcion() sin argumentos que se ejecuta en esa fase
        """
        self.callbacks[phase].append(callback)

    def execute_tick(self) -> None:
        """Ejecuta un tick completo (todas las fases en orden)."""
        for phase in self.phase_order:
            for callback in self.callbacks[phase]:
                callback()

    def get_phase_order(self) -> List[UpdatePhase]:
        """Retorna el orden de fases para debug."""
        return self.phase_order.copy()
