"""Configuración global y constantes físicas (unidades SI en todo el código)."""

import sys
import os

# ============================================================================
# PYTHON PATH - Para encontrar python fácilmente
# ============================================================================
# Ruta a Python (instalado vía uv)
PYTHON_EXECUTABLE = r"C:\Users\bgaxiola\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe"
# Si no existe, usa sys.executable como fallback
if not os.path.exists(PYTHON_EXECUTABLE):
    PYTHON_EXECUTABLE = sys.executable

# ============================================================================
# TIEMPO DE SIMULACIÓN
# ============================================================================
# Cada tick avanza 25ms simulados (40 ticks por segundo) - más suave y lento
TICK_DT_S = 0.025
RENDER_TARGET_FPS = 30
RENDER_SKIP_FRAMES = 1  # Renderiza cada N ticks

# ============================================================================
# ESCALA FÍSICA: metros ↔ píxeles
# ============================================================================
# 10 px/m → 1px = 10cm = 0.1m → 10px = 1m → 100px = 10m (zoom neutro ideal para calibración)
SCALE_PX_PER_M = 10.0

# Dimensiones reales del carro
CAR_LENGTH_M = 4.5
CAR_WIDTH_M = 1.8

# Tamaño del sprite basado en dimensiones reales y escala
# El carro se dibuja proporcionalmente al carril (1.8m de ancho)
# Mantiene aspect ratio 2:1 (largo:ancho)
CAR_SPRITE_WIDTH_PX = int(CAR_WIDTH_M * SCALE_PX_PER_M)    # 1.8m * 3.0 = 5.4 ≈ 5px
CAR_SPRITE_LENGTH_PX = CAR_SPRITE_WIDTH_PX * 2              # Mantiene proporción 2:1 = 10px

# Ancho del carril: 3.6m
# Carro: 1.8m, carril: 3.6m, diferencia: 1.8m a cada lado
LANE_WIDTH_M = 3.6

# Franja blanca: 0.2m para simetría
# 0.2m * 3.0 px/m = 0.6px (visible en pantalla)
LANE_MARKING_WIDTH_M = 0.2

# Margen gris exterior (parte de la calle): 0.8m a cada lado
# Los márgenes son GRISES, no verdes. El fondo verde está fuera de la calle.
ROAD_MARGIN_WIDTH_M = 0.8

# ============================================================================
# DINÁMICAS DEL VEHÍCULO
# ============================================================================
# Límite MVP: 20 km/h en calle local urbana
MAX_SPEED_KMH = 20.0
MAX_SPEED_MS = MAX_SPEED_KMH / 3.6

# Aceleración y frenado realistas
MAX_ACCEL_MS2 = 2.0
COMFORTABLE_DECEL_MS2 = 2.0
MAX_DECEL_MS2 = 4.0

IDM_DESIRED_SPEED_MS = 5.56
# Tiempo de separación (segundos adelante que quiere mantener)
# Aumentado de 1.5s a 3.0s para mayor distancia de seguridad
# A 5.56 m/s, 3.0s = ~16.7m de brecha deseada
IDM_TIME_HEADWAY_S = 3.0
# Brecha mínima al detenerse (metros)
# 0.5 * CAR_LENGTH_M = 0.5 * 4.5 = 2.25m (distancia reglamentaria)
IDM_MIN_GAP_M = 2.25
# Exponente en la fórmula IDM
IDM_DELTA = 4

# ============================================================================
# INDEXADO ESPACIAL
# ============================================================================
# Tamaño de celda para búsqueda rápida de vecinos
SPATIAL_GRID_CELL_SIZE_M = 30.0
PERCEPTION_RADIUS_M = 100.0

# ============================================================================
# ENTORNO (MVP: carril único)
# ============================================================================
ROAD_SEGMENT_LENGTH_M = 500.0
INITIAL_NUM_AGENTS = 20
AGENT_SPAWN_MARGIN_M = 50.0

# ============================================================================
# SISTEMA DE RESPAWN: Mantenimiento de población de carros
# ============================================================================
RESPAWN_WAIT_MIN_S = 3.0                 # Tiempo mínimo entre spawns de deficit
RESPAWN_WAIT_MAX_S = 7.0                 # Tiempo máximo entre spawns de deficit

# ============================================================================
# SISTEMA DE TRÁFICO: Generación de vehículos por zona
# ============================================================================
ZONE_TRAFFIC = {
    'urban': {
        'arrival_rate_veh_per_min': 1.5,   # ~90 veh/hora
        'speed_mean_kmh': 18.0,
        'speed_std_kmh': 2.5,
        'min_spawn_headway_m': 25.0,       # Brecha mínima para poder hacer spawn (aumentado de 15m)
    }
}

# ============================================================================
# SISTEMA DE COLISIONES
# ============================================================================
COLLISION_OVERLAP_RATIO = 0.5          # Colisión si gap < CAR_LENGTH_M * overlap_ratio
COLLISION_DISABLE_TICKS = 400          # ~20s antes de que desaparezca (400 * 50ms = 20s)
# Justificación: tiempo suficiente para que agentes de atrás frenen completamente
# Velocidad máxima 5.56 m/s, decel máxima 4 m/s² → distancia de frenado ≈ 3.9m
# Con headway de 1.5s a 5.56 m/s ≈ 8.3m de distancia nominal
# 20s permite que múltiples agentes en cadena se detengan sin chocar
SHOULDER_OFFSET_M = 2.5                # Desplazamiento lateral hacia la orilla
SHOULDER_ANIM_SPEED_M_PER_TICK = 0.05  # Qué tan rápido se mueve a la orilla

# ============================================================================
# RENDERIZADO
# ============================================================================
WINDOW_WIDTH_PX = 1200
WINDOW_HEIGHT_PX = 800
BACKGROUND_COLOR = (34, 139, 34)  # Verde pasto oscuro (ForestGreen)
FPS_DISPLAY = True
DEBUG_OVERLAY_ENABLED = True

# HUD layout dimensions
HUD_CHART_W = 200
HUD_CHART_H = 80
HUD_BAR_HEIGHT = 55  # Altura de la barra de controles (bottom)

COLOR_CAR_DEFAULT = (200, 50, 50)    # Rojo oscuro
COLOR_CAR_LEADER = (200, 100, 100)
COLOR_CAR_FAST = (255, 200, 0)       # Amarillo: agente a velocidad alta (>15 km/h)
COLOR_CAR_SLOW = (100, 100, 200)     # Azul: agente lento (2-15 km/h)
COLOR_CAR_STOPPED = (0, 0, 0)        # Negro: agente detenido (<0.1 km/h)
COLOR_CAR_SELECTED = (255, 255, 0)   # Amarillo brillante: agente en follow mode
COLOR_LANE_BORDER = (255, 255, 255)  # Blanco: franjas de demarcación
COLOR_LANE_ROAD = (140, 140, 140)    # Gris claro: superficie de la carretera
COLOR_ROAD_MARGIN = (140, 140, 140)  # Gris: margen alrededor del carril (mismo que carretera)
COLOR_GRID = (50, 50, 50)
COLOR_TEXT = (200, 200, 200)
COLOR_HUD_BG = (15, 15, 15)          # Fondo de panels HUD
COLOR_CHART_LINE = (100, 200, 100)   # Línea del speed chart
COLOR_CHART_BG = (30, 30, 30)        # Fondo del chart

# ============================================================================
# MISCELÁNEA
# ============================================================================
AGENT_ID_COUNTER_START = 1000
RANDOM_SEED = None
