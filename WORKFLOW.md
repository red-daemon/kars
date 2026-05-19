# KARS Development Workflow

Guía de uso del workflow automatizado.

## Quick Start: Do Commit

Automatiza commit + push + sync en un comando:

### Manual (desde terminal)
```powershell
.\.claude\do-commit.ps1 "Tu mensaje de commit"
```

### Desde Claude
```
/do-commit "Tu mensaje de commit"
```

**Ejemplo**:
```powershell
.\.claude\do-commit.ps1 "Implementar MOBIL model para lane-change"
```

## Flujo Recomendado

```
1. Implement feature
   ↓
2. Crear tests/unit/test_*.py
   ↓
3. Crear tests/integration/test_*.py
   ↓
4. python run_tests.py (debe pasar)
   ↓
5. .\.claude\do-commit.ps1 "Tu mensaje"
   ├─ Limpia cache
   ├─ Stage cambios
   ├─ Commit (pre-commit hook valida)
   ├─ Push
   └─ Sync
   ↓
6. ¡Completado! Cambios en remote
```

## Componentes del Workflow

| Script | Propósito | Ubicación |
|--------|-----------|-----------|
| `do-commit.ps1` | Todo en uno: commit → push → sync | `.\.claude\` |
| `push-and-sync.ps1` | Solo push + sync (sin nuevo commit) | `.\.claude\` |
| `run_tests.py` | Unitarios + integración | Root |
| Pre-commit hook | Validación automática | `.\.claude\hooks\pre-commit` |

## Testing Requirements

**OBLIGATORIO antes de cada commit**:

1. ✅ Crear tests unitarios (`tests/unit/test_*.py`)
2. ✅ Crear tests integración (`tests/integration/test_*.py`)
3. ✅ `python run_tests.py` pasa
4. ✅ Código documentado en español

Ver `DEVELOPMENT.md` para plan detallado.

## Documentación

- **CLAUDE.md** - Arquitectura, comandos, patrones
- **DEVELOPMENT.md** - Plan atómico por fase con testing requirements
- **.claude/DO_COMMIT_GUIDE.md** - Guía detallada del do-commit script
- **.claude/skills/README.md** - Skills disponibles
- **tests/README.md** - Estructura y uso de tests

## Skills Disponibles

### do-commit
Ejecuta commit + push + sync automático.

```
/do-commit "Mensaje de commit"
```

Ver `.claude/skills/do-commit.md` para detalles.

## Troubleshooting

### Pre-commit hook bloquea
```
[ERROR] Error en commit (pre-commit hook bloqueo)
```
**Solución**: Lee el mensaje del hook, arregla, y ejecuta script nuevamente.

### Tests fallan
```
FAILED: X test(s) fallaron
```
**Solución**: 
- Ejecuta test individualmente para debuggear
- Arregla el problema
- Vuelve a ejecutar script

### Push falla
```
[ERROR] Error en push
```
**Solución**: Verifica conexión a internet y permisos en repo.

## Pro Tips

- ✅ Usa `do-commit` solo cuando hayas completado TODOS los tests
- ✅ Mensajes de commit claros y concisos
- ✅ Un commit por tarea atómica (ver DEVELOPMENT.md)
- ✅ Valida con `python run_tests.py` antes de `do-commit`

## Próximas Mejoras

- [ ] Crear skill `/run-tests` para ejecutar tests desde Claude
- [ ] Crear skill `/validate-feature` para tests de validación
- [ ] Agregar pre-push checks automáticos
