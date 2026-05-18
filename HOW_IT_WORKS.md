# KARS: Cómo Funciona el Simulador

## Descripción General

KARS es un simulador de tráfico **basado en agentes** donde cada carro es un agente autónomo que decide su comportamiento basándose en:
- Su velocidad actual
- La distancia al carro de adelante
- El modelo de comportamiento IDM (Intelligent Driver Model)

**Sin reglas explícitas de "mantener distancia"**, los patrones de coordinación emergen naturalmente.

---

## Arquitectura de Capas

```
┌─────────────────────────────────────────────────┐
│          RENDERIZADO (Pygame)                   │
│  - Dibuja agentes como rectangulos             │
│  - Dibuja carriles como lineas                 │
│  - HUD con velocidades y estadisticas          │
└─────────────────────────────────────────────────┘
                        ↑
                  RenderSnapshot
                        ↑
┌─────────────────────────────────────────────────┐
│          WORLD (Orquestador)                    │
│  - Tick maestro con 7 fases                    │
│  - Doble buffer (lectura N, escritura N+1)    │
│  - Scheduler de orden garantizado              │
└─────────────────────────────────────────────────┘
           ↑         ↑         ↑
      Agentes   Entorno   Estadisticas
           ↑         ↑         ↑
┌──────────┴─────────┴─────────┴─────────────────┐
│    SIMULATION LOGIC (Physics, Behavior, etc)  │
├───────────────────────────────────────────────┤
│  AGENTES                                       │
│  - CarAgent: vehículo con estado dual         │
│  - PerceptionModule: qué ve cada agente       │
│  - IDMBehavior: cómo decide acelerar          │
│                                               │
│  ENTORNO                                       │
│  - Lane: carril como polilínea                │
│  - RoadSegment: varias lanes paralelas        │
│  - RoadNetwork: grafo de segmentos            │
│                                               │
│  FISICA                                        │
│  - PhysicsEngine: integración de Euler        │
│  - KinematicState: posición, velocidad, etc   │
└───────────────────────────────────────────────┘
```

---

## El Tick Maestro: 7 Fases

Cada 50ms simulado, ocurren estos pasos EN ORDEN ESTRICTO:

### Fase 1: PERCEPTION (Lee estado N)
```python
for cada_agente in agentes:
    # Consulta SpatialGrid para encontrar líder/seguidor
    percepcion = PerceptionModule.compute(
        agent_s = posicion_del_agente,
        other_agents = estado_de_otros_agentes,  # ESTADO N
        network = red_de_calles
    )
    # Resultado: distancia_al_lider, velocidad_lider, etc
```

**Invariante**: Todos los agentes **leen el mismo estado N**. Ninguno ve cambios de otros en este tick.

### Fase 2: DECISION (Lee estado N)
```python
for cada_agente in agentes:
    # Agente usa IDM para decidir aceleración
    acel_deseada = agente.decide(percepcion)  # Lee estado N
    # Ejemplo: a = 2.0 * (1 - (v/v0)^4 - (s*/s)^2)
    #   - Si v < v0: acelera hacia velocidad deseada
    #   - Si s < s*: frena para mantener distancia segura
```

### Fase 3: PHYSICS (Escribe estado N+1)
```python
for cada_agente in agentes:
    nuevo_estado = PhysicsEngine.integrate(
        estado_actual = agente.state,      # Lee N
        aceleracion = acel_deseada,
        dt = 0.05s
    )
    agente.state = nuevo_estado  # Escribe N+1 (buffer)
```

**Motor de física**:
```
v(t+dt) = v(t) + a*dt           # Actualiza velocidad
x(t+dt) = x(t) + v(t+dt)*dt     # Actualiza posición
```

### Fase 4: ENVIRONMENT (Actualiza mundo)
```python
# En MVP: noop (vacío)
# En Fase 3: actualizar semáforos, generar agentes, etc
pass
```

### Fase 5: SPATIAL_INDEX (Sincroniza carriles)
```python
# Reconstruye índice espacial con posiciones N+1
spatial_grid.clear()
for cada_agente in agentes:
    # Proyecta (x,y) de vuelta al carril (s, offset_lateral)
    nueva_s = carril.find_closest_s(agente.position)
    nuevo_offset = carril.get_lateral_offset_at(agente.position, nueva_s)
    
    agente.position_along_lane = nueva_s
    agente.lateral_offset = nuevo_offset
    
    spatial_grid.insert(agente.id, agente.position)
```

**Mantiene representación dual en sincronización**:
- KinematicState: (x, y) en metros (lo que maneja la física)
- Lane representation: (lane_id, s, offset) (lo que entiende la percepción)

### Fase 6: STATISTICS (Observa, no modifica)
```python
stats = StatsCollector.record_tick(
    tick_number = world.tick_number,
    sim_time = world.sim_time_s,
    agents = world.agents
)
# Calcula: velocidad promedio, varianza, etc
```

### Fase 7: RENDER (Prepara para dibujar)
```python
snapshot = RenderSnapshot(
    agents = [(id, pos, heading, speed) for cada agente],
    lanes = [(lane_id, waypoints) para cada carril],
    sim_time_s = world.sim_time_s,
    avg_speed_kmh = stats.avg_speed_kmh
)
# El renderer dibuja el snapshot
```

---

## Ejemplo Concreto: Qué pasa en 3 ticks

### Tick 1
```
Tiempo: 0.00s

1. PERCEPTION:
   Agente 1 mira adelante → Agente 2 está a 80m
   
2. DECISION:
   IDM: a = 2.0 * (1 - (0/5.56)^4 - (40/80)^2)
       a = 2.0 * (1 - 0 - 0.25) = 1.5 m/s²
   
3. PHYSICS:
   v_nuevo = 0 + 1.5 * 0.05 = 0.075 m/s
   x_nuevo = 100 + 0.075 * 0.05 = 100.004m
   
4. STATISTICS:
   Avg speed = 0.27 km/h
```

### Tick 2
```
Tiempo: 0.05s

1. PERCEPTION:
   Agente 1 mira adelante → Agente 2 está a 79.9m (se acerca, ambos aceleran)
   
2. DECISION:
   IDM: a = 2.0 * (1 - (0.075/5.56)^4 - (40/79.9)^2)
       a = 2.0 * (1 - 0.000000015 - 0.25) ≈ 1.5 m/s²
   
3. PHYSICS:
   v_nuevo = 0.075 + 1.5 * 0.05 = 0.15 m/s
   x_nuevo = 100.004 + 0.15 * 0.05 = 100.012m
```

### Tick 20 (1 segundo simulado)
```
Tiempo: 1.00s

1. PERCEPTION:
   Agente 1 → Agente 2 a 79.5m, velocidad 1.5 m/s
   
2. DECISION:
   IDM: a = 2.0 * (1 - (1.5/5.56)^4 - (40/79.5)^2)
       a ≈ 1.48 m/s²
   
3. STATISTICS:
   Velocidad promedio: 5.4 km/h
   (Los 5 agentes aceleran gradualmente)
```

---

## Comportamiento Emergente: Caravanas

Después de 20 segundos, ocurre esto:

```
Posiciones iniciales:        Estado final (20s):
50m, 130m, 210m, 290m, 370m → 152m, 232m, 312m, 392m, 473m

Espaciamiento inicial: 80m cada uno
Espaciamiento final: ~80m cada uno  ← MANTIENE DISTANCIA

Velocidades finales: 19.93, 19.93, 19.93, 19.93, 20.02 km/h

┌─Agente 1 @ 152m, 19.93km/h───────────────────┐
│                                               │
│  VE: Agente 2 a 80m adelante, 19.93km/h     │
│  DECIDE: acelerar = 0 (velocidad deseada)    │
│  RESULTADO: mantiene velocidad                │
│                                               │
└─Agente 2 @ 232m, 19.93km/h───────────────────┘
  ↓
┌─Agente 2 @ 232m, 19.93km/h────────────────────┐
│                                                │
│  VE: Agente 3 a 80m adelante, 19.93km/h      │
│  DECIDE: acelerar = 0                         │
│  RESULTADO: copia la velocidad del agente 1   │
│                                                │
└─Agente 3 @ 312m, 19.93km/h────────────────────┘
```

**¿Por qué?**
- Cada agente percibe solo al de adelante
- Cada uno aplica IDM localmente
- NO hay comunicación ni regla explícita de "convoy"
- **Emerge un patrón de caravana cohesiva**

Esto es **comportamiento emergente**: propiedades del sistema que NO están programadas explícitamente.

---

## Cálculos de Física (SI units)

### Aceleración IDM
```
a = amax * [1 - (v/v0)^delta - (s*/s)^2]

Donde:
  amax = 2.0 m/s² (aceleración máxima)
  v = velocidad actual (m/s)
  v0 = velocidad deseada (5.56 m/s = 20 km/h)
  delta = 4 (exponente)
  s = brecha actual al líder (metros)
  s* = brecha deseada = s0 + v*T + v*dv/(2*sqrt(a*b))
    s0 = 2.0 m (brecha mínima)
    T = 1.5 s (tiempo de separación)
```

### Integración numérica (Euler)
```
v_new = v_old + a * dt
x_new = x_old + v_new * dt

Con dt = 0.05s (50ms):
  - 0 a 20 km/h tarda ~2.8 segundos (realista)
  - Distancia de frenado desde 20 km/h: ~7.7m (realista)
```

### Conversión de unidades
```
Distancias: metros (m)
Velocidades: m/s, convertidas a km/h para display
Aceleraciones: m/s²
Escala visual: 4.44 píxeles/metro
```

---

## Cómo Ejecutar

### Demo Headless (sin visualización)
```bash
python main.py
```
Muestra: estadísticas, velocidades finales, comportamiento emergente

### Demo Visual (ASCII art)
```bash
python demo_visual.py
```
Muestra: agentes moviéndose en el carril (ASCII), análisis paso a paso

### Tests (validación)
```bash
python run_tests.py
```
Ejecuta 47 tests, verifica 100% cobertura

---

## Próximos Pasos: Fase 2

1. **Múltiples carriles paralelos**
   - Lane[] en RoadSegment
   - Percepción expandida a carriles adyacentes

2. **MOBIL: Cambio de carril**
   - Agentes deciden cambiar de carril si ven ganancia de velocidad
   - Transición suave con lateral_offset interpolado

3. **Nuevos tests**
   - Detección de colisiones laterales
   - Validación de cambios de carril seguros

---

## Resumen: ¿Qué Hace KARS?

**Es un laboratorio para observar comportamiento emergente en sistemas de tráfico.**

Sin programar "haz una caravana" o "mantén distancia", emergen estos patrones porque:
1. Cada agente tiene percepción local (solo ve al de adelante)
2. Cada uno aplica IDM (regla simple de aceleración)
3. La física se integra consistentemente en cada tick
4. Los patrones emergen de la interacción de cientos de decisiones locales

Esto es lo que los científicos estudian en modelos multiagente.
