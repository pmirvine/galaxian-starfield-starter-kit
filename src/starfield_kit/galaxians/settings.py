"""Every tunable number in the Galaxians sample, in one place.

Tweak these! Making the game your own is the whole point of a starter kit.
All speeds are pixels per second; all times are seconds.
"""

WINDOW_W, WINDOW_H = 480, 640
FPS = 60
TITLE = "GALAXIANS — a starfield_kit sample"

PIXEL_SCALE = 3  # sprite ASCII art is blown up by this factor

# --- starfield ---------------------------------------------------------------
STAR_VELOCITY = (0, 40)  # gentle downward drift, like the arcade
STAR_DENSITY = 1.2
STAR_SIZE = PIXEL_SCALE  # stars one retro-pixel big, same 3x scale as the sprites
STAR_SEED = 1979  # fixed layout so the game always opens the same sky

# --- player ------------------------------------------------------------------
PLAYER_SPEED = 260
PLAYER_Y_MARGIN = 56  # distance of the ship above the bottom edge
PLAYER_SHOT_SPEED = 540
PLAYER_MAX_SHOTS = 1  # one shot on screen at a time, the Galaxian way
START_LIVES = 3
EXTRA_LIFE_AT = 7000  # one bonus ship, once
RESPAWN_DELAY = 1.6
INVULNERABLE_TIME = 2.2  # blink time after respawning

# --- the alien convoy ----------------------------------------------------------
# The formation grid: (sprite name, points in formation, points while diving)
# Row 0 is the top (flagships). Column count per row centers itself.
FORMATION_ROWS = [
    ("flagship", 2, (60, 150)),
    ("escort", 6, (50, 100)),
    ("drone", 8, (30, 60)),
    ("drone", 8, (30, 60)),
    ("drone", 8, (30, 60)),
]
FORMATION_TOP = 84
FORMATION_H_SPACING = 44
FORMATION_V_SPACING = 38
SWAY_AMPLITUDE = 34  # how far the convoy drifts side to side
SWAY_PERIOD = 5.0  # seconds for one full left-right-left cycle
FLAP_RATE = 2.4  # wing-flap animation, frames per second

# --- diving attacks ------------------------------------------------------------
DIVE_INTERVAL = 2.6  # seconds between dives on wave 1...
DIVE_INTERVAL_MIN = 0.9  # ...tightening to this on later waves
DIVE_INTERVAL_STEP = 0.35  # how much faster each wave gets
DIVE_SPEED = 170  # downward speed of a diving alien
DIVE_SWERVE = 90  # sideways swoop amplitude
RETURN_SPEED = 150  # speed while gliding back into formation
DIVER_FIRE_CHANCE = 1.1  # shots per second while diving
ENEMY_SHOT_SPEED = 240
ENEMY_SHOT_AIM = 0.6  # 0 = drop straight down, 1 = aim hard at the player

# --- presentation ----------------------------------------------------------------
HUD_COLOR = (120, 255, 160)
SCORE_COLOR = (255, 255, 255)
GAMEOVER_COLOR = (255, 80, 80)
WAVE_CLEAR_PAUSE = 2.0
