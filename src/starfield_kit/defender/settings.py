"""Every tunable number in the Defender sample.

All speeds are pixels per second, accelerations pixels per second squared,
times in seconds. The world is WORLD_W pixels around and wraps: fly right
long enough and you arrive back where you started.

Make the game yours: change a number, run ``uv run defender``, feel the
difference. The most rewarding dials are marked ``TWEAK:``. Difficulty in
one place — EASIER: lower LANDERS_PER_WAVE, LANDER_SPEED, BAITER_SPEED and
the two *_FIRE_CHANCE values, or raise START_LIVES, LASER_MAX and
BAITER_AFTER. HARDER: push the same knobs the other way.
"""

WINDOW_W, WINDOW_H = 800, 450
FPS = 60
TITLE = "DEFENDER — a starfield_kit sample"

# Art scale: every pixel in sprites.py becomes a PIXEL_SCALE x PIXEL_SCALE block.
PIXEL_SCALE = 3

WORLD_W = WINDOW_W * 4  # TWEAK: four screens of wrapping world — more screens = a longer patrol

# --- starfield ---------------------------------------------------------------
# The Defender sky shows off parallax: three depths of stars that slide at
# different rates as the camera moves. The starfield itself has NO velocity;
# the game pushes it around with field.scroll() as the camera travels.
# TWEAK: more layers = deeper parallax; higher density = a busier sky.
STAR_LAYERS = 3
STAR_DENSITY = 1.1
STAR_SIZE = PIXEL_SCALE  # nearest stars one retro-pixel big; far layers shrink
STAR_SEED = 1981  # the year Defender conquered the arcades — any int gives a different fixed sky

# --- the ship ------------------------------------------------------------------
THRUST = 900  # TWEAK: acceleration while holding left/right (px/sec^2) — higher = snappier
DRAG = 1.1  # how quickly you coast to a stop (bigger = sooner)
# TWEAK: top speed (px/sec) — thrust builds toward this; higher = slipperier flying.
MAX_SPEED = 620
VERTICAL_SPEED = 260  # up/down movement is direct, not inertial (like the arcade)
CAMERA_LOOKAHEAD = 0.28  # ship sits this fraction from the screen edge behind it (0.5 = centered)
CAMERA_SNAP = 4.0  # how eagerly the camera slides to its target position (higher = stiffer)
# TWEAK: lives — raise START_LIVES or lower EXTRA_LIFE_AT for a kinder game.
START_LIVES = 3
EXTRA_LIFE_AT = 8000
# Seconds dead before respawning, then seconds of blinking invulnerability.
RESPAWN_DELAY = 1.6
INVULNERABLE_TIME = 2.5

# --- weapons ---------------------------------------------------------------------
# TWEAK: bolt speed (px/sec) and drawn length (px) — long and fast is the Defender feel.
LASER_SPEED = 1100
LASER_LENGTH = 26
LASER_MAX = 4  # TWEAK: bolts allowed on screen at once — try 1 for strict, 8 for generous
# TWEAK: seconds between shots — lower = a faster trigger finger.
LASER_COOLDOWN = 0.14
# TWEAK: enemy bullet speed (px/sec) — slower bullets are easier to dodge.
ENEMY_SHOT_SPEED = 210

# --- enemies ------------------------------------------------------------------
LANDERS_PER_WAVE = 8  # TWEAK: plus LANDERS_WAVE_STEP more each wave — fewer = a gentler game
LANDERS_WAVE_STEP = 2
LANDER_SPEED = 70  # TWEAK: base drift speed toward the player (px/sec) — raise for a harder game
LANDER_BOB = 40  # amplitude of their up/down bobbing
LANDER_FIRE_CHANCE = 0.5  # TWEAK: shots per second per lander (when on screen) — lower = kinder
LANDER_POINTS = 150

BAITER_AFTER = 30.0  # TWEAK: dawdle this long (sec) and a baiter comes for you — raise for mercy
BAITER_INTERVAL = 12.0  # ...then another, and another
# TWEAK: baiter chase speed (px/sec) — higher = a deadlier hunter.
BAITER_SPEED = 420
# TWEAK: baiter shots per second — and baiters aim true, unlike landers.
BAITER_FIRE_CHANCE = 1.2
BAITER_POINTS = 200

# --- terrain -------------------------------------------------------------------
TERRAIN_STEP = 40  # horizontal distance between mountain vertices
TERRAIN_MIN, TERRAIN_MAX = 330, 430  # mountain height range (screen y)
TERRAIN_COLOR = (170, 90, 40)

# --- radar ---------------------------------------------------------------------
# The strip at the top squeezes the whole WORLD_W loop into RADAR_W pixels.
RADAR_W, RADAR_H = 260, 44
RADAR_BORDER = (110, 110, 140)

HUD_COLOR = (120, 255, 160)
GAMEOVER_COLOR = (255, 80, 80)
# Seconds of "WAVE CLEAR!" celebration before the next, bigger wave starts.
WAVE_CLEAR_PAUSE = 2.0
