"""Configuración global y constantes físicas (unidades SI en todo el código)."""

# ============================================================================
# TIEMPO DE SIMULACIÓN
# ============================================================================
# Cada tick avanza 50ms simulados (20 ticks por segundo)
TICK_DT_S = 0.05
RENDER_TARGET_FPS = 30
RENDER_SKIP_FRAMES = 1  # Renderiza cada N ticks

# ============================================================================
# ESCALA FÍSICA: metros ↔ píxeles (ESCALA 2x: 40px por carro)
# ============================================================================
# Dimensiones reales y del sprite para calibración
CAR_LENGTH_M = 4.5
CAR_WIDTH_M = 1.8
CAR_SPRITE_LENGTH_PX = 40  # Duplicado (fue 20)
CAR_SPRITE_WIDTH_PX = 20   # Duplicado (fue 10)

# Escala uniforme: 40px / 4.5m ≈ 8.89 px/m (el doble)
SCALE_PX_PER_M = CAR_SPRITE_LENGTH_PX / CAR_LENGTH_M

# Ancho del carril (gris de carretera): 3.48m (348cm)
# Medido de centro de franja a centro de franja = 3.6m, menos las medias franjas
LANE_WIDTH_M = 3.48

# Franja blanca: 12cm (0.12m)
LANE_MARKING_WIDTH_M = 0.12

# Margen verde exterior: 100cm (1.0m) a cada lado
ROAD_MARGIN_WIDTH_M = 1.0

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
COLOR_CAR_FAST = (255, 200, 0)       # Amarillo: agente a velocidad alta
COLOR_CAR_SLOW = (100, 100, 200)     # Azul: agente lento/frenando
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
