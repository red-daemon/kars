"""Configuración global y constantes físicas (unidades SI en todo el código)."""

# ============================================================================
# TIEMPO DE SIMULACIÓN
# ============================================================================
# Cada tick avanza 50ms simulados (20 ticks por segundo)
TICK_DT_S = 0.05
RENDER_TARGET_FPS = 30
RENDER_SKIP_FRAMES = 1  # Renderiza cada N ticks

# ============================================================================
# ESCALA FÍSICA: metros ↔ píxeles
# ============================================================================
# Dimensiones reales y del sprite para calibración
CAR_LENGTH_M = 4.5
CAR_WIDTH_M = 1.8
CAR_SPRITE_LENGTH_PX = 20
CAR_SPRITE_WIDTH_PX = 10

# Escala uniforme: 20px / 4.5m ≈ 4.44 px/m
SCALE_PX_PER_M = CAR_SPRITE_LENGTH_PX / CAR_LENGTH_M

LANE_WIDTH_PX = 12
LANE_WIDTH_M = LANE_WIDTH_PX / SCALE_PX_PER_M

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

# ============================================================================
# MODELO DE CONDUCTOR INTELIGENTE (IDM)
# ============================================================================
# Parámetros que definen el comportamiento emergente de los carros

# Velocidad deseada: 20 km/h = 5.56 m/s
IDM_DESIRED_SPEED_MS = 5.56
# Tiempo de separación (segundos adelante que quiere mantener)
IDM_TIME_HEADWAY_S = 1.5
# Brecha mínima al detenerse (metros)
IDM_MIN_GAP_M = 2.0
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
# RENDERIZADO
# ============================================================================
WINDOW_WIDTH_PX = 1200
WINDOW_HEIGHT_PX = 600
BACKGROUND_COLOR = (25, 25, 25)
FPS_DISPLAY = True
DEBUG_OVERLAY_ENABLED = True

# HUD layout dimensions
HUD_CHART_W = 200
HUD_CHART_H = 80
HUD_BAR_HEIGHT = 55  # Altura de la barra de controles (bottom)

COLOR_CAR_DEFAULT = (100, 200, 100)
COLOR_CAR_LEADER = (200, 100, 100)
COLOR_CAR_FAST = (255, 200, 0)       # Amarillo: agente a velocidad alta
COLOR_CAR_SLOW = (200, 80, 80)       # Rojo: agente frenando
COLOR_CAR_SELECTED = (100, 150, 255) # Azul: agente en follow mode
COLOR_LANE_BORDER = (100, 100, 100)
COLOR_LANE_ROAD = (60, 60, 60)       # Fill de carretera
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
