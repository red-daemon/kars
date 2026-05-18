"""Índice espacial: grid para búsqueda O(1) de agentes cercanos."""

from typing import Dict, List, Set, Tuple
from kars.physics.models import Vector2
import kars.config as config


class SpatialGrid:
    """Grid espacial para búsqueda rápida de agentes.

    Divide el mundo en celdas de tamaño fijo. Cada celda contiene
    una lista de agent_ids dentro de ella.

    Operaciones:
    - insert(agent_id, pos): O(1)
    - query_neighbors(pos, radius): O(1) amortizado
    - clear(): O(N)
    """

    def __init__(self, cell_size_m: float = config.SPATIAL_GRID_CELL_SIZE_M):
        """Inicializa grid.

        Args:
            cell_size_m: Tamaño de cada celda en metros
        """
        self.cell_size_m = cell_size_m
        # (grid_x, grid_y) -> Set[agent_id]
        self.cells: Dict[Tuple[int, int], Set[int]] = {}

    def _get_cell_key(self, pos: Vector2) -> Tuple[int, int]:
        """Convierte posición mundo a clave de celda.

        Args:
            pos: Vector2 en metros

        Returns:
            Tupla (grid_x, grid_y)
        """
        grid_x = int(pos.x // self.cell_size_m)
        grid_y = int(pos.y // self.cell_size_m)
        return (grid_x, grid_y)

    def insert(self, agent_id: int, pos: Vector2) -> None:
        """Inserta un agente en el grid.

        Args:
            agent_id: ID del agente
            pos: Vector2 posición en metros
        """
        cell_key = self._get_cell_key(pos)

        if cell_key not in self.cells:
            self.cells[cell_key] = set()

        self.cells[cell_key].add(agent_id)

    def query_neighbors(self, pos: Vector2, radius_m: float) -> Set[int]:
        """Retorna agentes dentro de radio de una posición.

        Busca en todas las celdas que solapan con el círculo de búsqueda.

        Args:
            pos: Vector2 posición central
            radius_m: Radio de búsqueda en metros

        Returns:
            Set de agent_ids cercanos (aproximado, puede incluir más)
        """
        neighbors = set()

        # Calcula rango de celdas a buscar
        cell_radius = int(radius_m / self.cell_size_m) + 1
        center_cell_x, center_cell_y = self._get_cell_key(pos)

        # Itera celdas en un cuadrado alrededor del centro
        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cell_key = (center_cell_x + dx, center_cell_y + dy)

                if cell_key in self.cells:
                    neighbors.update(self.cells[cell_key])

        return neighbors

    def query_cell_neighbors(self, pos: Vector2) -> Set[int]:
        """Retorna agentes en la misma celda que la posición.

        Más rápido que query_neighbors si solo necesitas la celda actual.

        Args:
            pos: Vector2 posición

        Returns:
            Set de agent_ids en la misma celda
        """
        cell_key = self._get_cell_key(pos)
        return self.cells.get(cell_key, set())

    def clear(self) -> None:
        """Limpia el grid."""
        self.cells.clear()

    def get_all_agents(self) -> Set[int]:
        """Retorna todos los agentes en el grid."""
        all_agents = set()
        for cell_agents in self.cells.values():
            all_agents.update(cell_agents)
        return all_agents

    def get_stats(self) -> Dict:
        """Retorna estadísticas del grid (para debug)."""
        total_agents = sum(len(agents) for agents in self.cells.values())
        total_cells = len(self.cells)
        avg_agents_per_cell = total_agents / total_cells if total_cells > 0 else 0

        return {
            "total_cells": total_cells,
            "total_agents": total_agents,
            "avg_agents_per_cell": avg_agents_per_cell,
        }
