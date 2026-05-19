# KARS Development Plan

Plan de desarrollo con tareas atómicas. Cada tarea = 1 commit.

## Fases del Proyecto

### Phase 1: Agent-Based Traffic Simulator MVP ✅ COMPLETADA
- ✅ Lanes, agents, physics, rendering

### Phase 2: Multi-Lane + Lane Changes (EN PROGRESO)

#### 2.1 - Lane-Change Decision (MOBIL Model)
- [ ] Implementar modelo MOBIL (Minimizing Overall Braking Induced by Lane-change)
- [ ] Agregar métodos de evaluación de beneficio de cambio
- [ ] Crear tests unitarios: `tests/unit/test_mobil.py`
- [ ] Crear tests integración: `tests/integration/test_lane_change.py`
- [ ] **COMMIT**: "Implementar MOBIL model para decisión de cambio de carril"

#### 2.2 - Lane-Change Physics
- [ ] Implementar transición suave entre carriles
- [ ] Agregar lateral dynamics
- [ ] Crear tests unitarios: `tests/unit/test_lateral_dynamics.py`
- [ ] Crear tests integración: `tests/integration/test_lane_change_physics.py`
- [ ] **COMMIT**: "Implementar física de cambio de carril"

#### 2.3 - Multi-Lane Road Network
- [ ] Extender RoadNetwork para multi-lane
- [ ] Actualizar Lane con información de carriles adyacentes
- [ ] Crear tests unitarios: `tests/unit/test_multi_lane_network.py`
- [ ] Crear tests integración: `tests/integration/test_multi_lane_routing.py`
- [ ] **COMMIT**: "Soporte para redes multi-carril"

#### 2.4 - Visualization Update
- [ ] Renderizar múltiples carriles
- [ ] Mostrar indicadores de cambio de carril
- [ ] Crear test de validación: `tests/validation/validate_multi_lane_visual.py`
- [ ] **COMMIT**: "Visualización de múltiples carriles"

### Phase 3: Traffic Lights + Intersections (PENDIENTE)

#### 3.1 - Traffic Light Logic
- [ ] Implementar TrafficLight entity
- [ ] Agregar fases de semáforo
- [ ] Crear tests unitarios: `tests/unit/test_traffic_light.py`
- [ ] Crear tests integración: `tests/integration/test_traffic_light_timing.py`
- [ ] **COMMIT**: "Implementar lógica de semáforos"

#### 3.2 - Intersection Handling
- [ ] Detectar intersecciones en RoadNetwork
- [ ] Implementar reglas de cruce
- [ ] Crear tests unitarios: `tests/unit/test_intersection.py`
- [ ] Crear tests integración: `tests/integration/test_intersection_crossing.py`
- [ ] **COMMIT**: "Implementar lógica de intersecciones"

#### 3.3 - Agent Behavior at Intersections
- [ ] Actualizar IDM para semáforos
- [ ] Agregar decisión de giro
- [ ] Crear tests unitarios: `tests/unit/test_agent_at_intersection.py`
- [ ] Crear tests integración: `tests/integration/test_intersection_behavior.py`
- [ ] **COMMIT**: "Comportamiento de agentes en intersecciones"

### Phase 4: OpenStreetMap Import (PENDIENTE)

#### 4.1 - OSM Parser
- [ ] Implementar parser de archivos OSM
- [ ] Convertir OSM a RoadNetwork
- [ ] Crear tests unitarios: `tests/unit/test_osm_parser.py`
- [ ] Crear tests integración: `tests/integration/test_osm_import.py`
- [ ] **COMMIT**: "Parser de OpenStreetMap"

#### 4.2 - Real Map Loading
- [ ] Cargar mapas reales
- [ ] Validar geometría
- [ ] Crear test de validación: `tests/validation/validate_osm_load.py`
- [ ] **COMMIT**: "Carga de mapas reales desde OSM"

### Phase 5: Multi-Resolution (PENDIENTE)

#### 5.1 - Zoning System
- [ ] Implementar zonas de detalle
- [ ] Crear tests unitarios: `tests/unit/test_zoning.py`
- [ ] Crear tests integración: `tests/integration/test_zone_switching.py`
- [ ] **COMMIT**: "Sistema de zonas con diferentes resoluciones"

#### 5.2 - Statistical Zones
- [ ] Implementar zonas estadísticas (flow-based)
- [ ] Crear tests unitarios: `tests/unit/test_statistical_zone.py`
- [ ] Crear tests integración: `tests/integration/test_statistical_behavior.py`
- [ ] **COMMIT**: "Zonas estadísticas para simulación macroscópica"

## Testing Requirements

**ANTES de pasar a la siguiente tarea, DEBES crear:**

1. **Tests Unitarios** (`tests/unit/test_*.py`)
   - Prueben componentes individuales en aislamiento
   - Cobertura mínima del 80% de la lógica nueva
   
2. **Tests de Integración** (`tests/integration/test_*.py`)
   - Prueben interacción con componentes existentes
   - Validen que no rompan el sistema completo

3. **(Opcional) Tests de Validación** (`tests/validation/validate_*.py`)
   - Para verificación visual o manual
   - Se ejecutan manualmente antes de decisiones arquitectónicas

**Checklist antes de COMMIT:**
- [ ] Código documentado en español (comentarios + docstrings)
- [ ] Tests unitarios creados y pasando
- [ ] Tests integración creados y pasando
- [ ] `python run_tests.py` pasa exitosamente
- [ ] Pre-commit hook no bloquea

## Tracking

| Tarea | Estado | Commit | Fecha |
|-------|--------|--------|-------|
| Phase 1 MVP | ✅ Completada | a3cbeed | 2026-05-19 |
| 2.1 MOBIL Model | ⏳ Pendiente | - | - |
| 2.2 Lane Physics | ⏳ Pendiente | - | - |
| 2.3 Multi-Lane Network | ⏳ Pendiente | - | - |
| 2.4 Visualization | ⏳ Pendiente | - | - |

## Notas

- Cada item con `[ ]` requiere trabajo
- Cada grupo de items termina con **UN COMMIT**
- El commit debe incluir el trabajo + tests (unitarios + integración)
- Ver CLAUDE.md para estándares de código
- Ver tests/README.md para estructura de tests
