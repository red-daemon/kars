# Tests - KARS Project

Estructura organizada de tests por tipo de funcionalidad.

## Estructura de Carpetas

```
tests/
├── validation/        # Tests de validacion y prototipado
│   ├── validate_*.py  # Prefijo validate_ para distinguir
│   └── ...
├── unit/             # Tests unitarios
│   ├── test_*.py     # Tests de componentes individuales
│   └── ...
├── integration/      # Tests de integracion
│   ├── test_*.py     # Tests multi-componentes
│   └── ...
└── README.md
```

## Tipos de Tests

### 1. Validación (`tests/validation/validate_*.py`)

Tests creados durante desarrollo para validar nuevas funcionalidades o cambios.

- **Prefijo especial**: `validate_` (no `test_`) para diferenciar de tests unitarios/integración
- **Ubicación**: Carpeta `tests/validation/`
- **Ejemplos**:
  - `validate_collision_basic.py` - Detecta colisión frontal
  - `validate_collisions.py` - Cadena de colisiones
  - `validate_road_scales.py` - Calibración visual (interactivo)

**Uso**:
```bash
python tests/validation/validate_collision_basic.py
```

### 2. Unitarios (`tests/unit/test_*.py`)

Tests que prueban componentes individuales en aislamiento.

- **Prefijo**: `test_`
- **Ubicación**: Carpeta `tests/unit/`
- **Dependencias**: Mínimas, sin acceso a mundo completo
- **Ejemplos**:
  - `test_lane.py` - Geometría de carriles
  - `test_agents.py` - Comportamiento de agentes
  - `test_world.py` - Orquestación del mundo

### 3. Integración (`tests/integration/test_*.py`)

Tests que validan interacción entre múltiples componentes.

- **Prefijo**: `test_`
- **Ubicación**: Carpeta `tests/integration/`
- **Uso**: Para testing de workflows completos

## Ejecutar Tests

### Tests estándar (unitarios + integración)
```bash
python run_tests.py
```

Muestra:
- Cantidad de tests por categoría
- Nombre de cada test que se ejecuta
- Resumen final (PASSED/FAILED)

### Tests de validación (manualmente)
```bash
# Validación: se ejecutan UNO A UNO, nunca automáticamente
python tests/validation/validate_collision_basic.py
python tests/validation/validate_collisions.py
python tests/validation/validate_collision_stop.py
```

### Otros tests individuales
```bash
# Unitario
python tests/unit/test_lane.py

# Integración
python tests/integration/test_world.py
```

## Pre-commit Hook

El pre-commit hook ejecuta `run_tests.py` antes de cada commit:
- Ejecuta solo tests unitarios e integración
- Omite tests de validación (se ejecutan manualmente)
- Impide commit si algún test falla

## Nombrado de Tests

**Validación** (durante desarrollo):
```python
# Carpeta: tests/validation/
# Prefijo: validate_
validate_collision_basic.py
validate_collisions.py
validate_road_scales.py
```

**Unitarios** (componentes):
```python
# Carpeta: tests/unit/
# Prefijo: test_
test_lane.py
test_agents.py
test_world.py
```

**Integración** (workflows):
```python
# Carpeta: tests/integration/
# Prefijo: test_
test_full_simulation.py
```

## Notas

- Los tests de validación pueden ser interactivos (GUI)
- Los tests unitarios e integración deben ser automáticos
- Todos los tests deben tener docstrings en español
- Ver CLAUDE.md para estándares de documentación
