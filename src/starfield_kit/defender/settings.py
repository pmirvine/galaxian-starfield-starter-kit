"""Every tunable number in the Defender sample.

All speeds are pixels per second, accelerations pixels per second squared,
times in seconds. The world is WORLD_W pixels around and wraps: fly right
long enough and you arrive back where you started.
"""

WINDOW_W, WINDOW_H = 800, 450
FPS = 60
TITLE = "DEFENDER — a starfield_kit sample"

PIXEL_SCALE = 3

WORLD_W = WINDOW_W * 4  # four screens of wrapping world

# --- starfield ---------------------------------------------------------------
# The Defender sky shows off parallax: three depths of stars that slide at
# different rates as the camera moves. The starfield itself has NO velocity;
# the game pushes it around with field.scroll() as the camera travels.
STAR_LAYERS = 3
STAR_DENSITY = 1.1
STAR_SEED = 1981  # the year Defender conquered the arcades

# --- the ship ------------------------------------------------------------------
THRUST = 900  # horizontal acceleration while holding left/right
DRAG = 1.1  # how quickly you coast to a stop (bigger = sooner)
MAX_SPEED = 620
VERTICAL_SPEED = 260  # up/down movement is direct, not inertial (like the arcade)
CAMERA_LOOKAHEAD = 0.28  # ship sits this fraction from the screen edge behind it
CAMERA_SNAP = 4.0  # how eagerly the camera slides to its target position
START_LIVES = 3
EXTRA_LIFE_AT = 8000
RESPAWN_DELAY = 1.6
INVULNERABLE_TIME = 2.5

# --- weapons ---------------------------------------------------------------------
LASER_SPEED = 1100
LASER_LENGTH = 26
LASER_MAX = 4  # bolts allowed on screen at once
LASER_COOLDOWN = 0.14
ENEMY_SHOT_SPEED = 210

# --- enemies ------------------------------------------------------------------
LANDERS_PER_WAVE = 8  # plus LANDERS_WAVE_STEP more each wave
LANDERS_WAVE_STEP = 2
LANDER_SPEED = 70  # base drift speed toward the player
LANDER_BOB = 40  # amplitude of their up/down bobbing
LANDER_FIRE_CHANCE = 0.5  # shots per second per lander (when on screen)
LANDER_POINTS = 150

BAITER_AFTER = 30.0  # dawdle this long in a wave and a baiter comes for you
BAITER_INTERVAL = 12.0  # ...then another, and another
BAITER_SPEED = 420
BAITER_FIRE_CHANCE = 1.2
BAITER_POINTS = 200

# --- terrain -------------------------------------------------------------------
TERRAIN_STEP = 40  # horizontal distance between mountain vertices
TERRAIN_MIN, TERRAIN_MAX = 330, 430  # mountain height range (screen y)
TERRAIN_COLOR = (170, 90, 40)

# --- radar ---------------------------------------------------------------------
RADAR_W, RADAR_H = 260, 44
RADAR_BORDER = (110, 110, 140)

HUD_COLOR = (120, 255, 160)
GAMEOVER_COLOR = (255, 80, 80)
WAVE_CLEAR_PAUSE = 2.0
