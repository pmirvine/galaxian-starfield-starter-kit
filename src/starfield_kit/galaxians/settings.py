"""Every tunable number in the Galaxians sample, in one place.

Tweak these! Making the game your own is the whole point of a starter kit.
All speeds are pixels per second; all times are seconds.
"""

# Harder or easier? Start with these dials: DIVE_INTERVAL, DIVE_INTERVAL_MIN
# and DIVE_INTERVAL_STEP set how often divers come and how fast that ramps up
# per wave; DIVER_FIRE_CHANCE and ENEMY_SHOT_AIM set how much aimed fire is
# in the air; START_LIVES is your safety margin. Nudge one dial at a time.

# Portrait window, like the arcade cabinet's monitor.
WINDOW_W, WINDOW_H = 480, 640
FPS = 60
TITLE = "GALAXIANS — a starfield_kit sample"

PIXEL_SCALE = 3  # sprite ASCII art is blown up by this factor

# --- starfield ---------------------------------------------------------------
STAR_VELOCITY = (0, 40)  # TWEAK: gentle downward drift (px/sec), like the arcade — try (0, 160)
STAR_DENSITY = 1.2
STAR_SIZE = PIXEL_SCALE  # stars one retro-pixel big, same 3x scale as the sprites
STAR_SEED = 1979  # fixed layout so the game always opens the same sky

# --- player ------------------------------------------------------------------
# TWEAK: ship speed, px/sec — more makes dodging easier, hence the game easier.
PLAYER_SPEED = 260
PLAYER_Y_MARGIN = 56  # distance of the ship above the bottom edge
# TWEAK: your bullet speed, px/sec — snappier shots make sniping divers easier.
PLAYER_SHOT_SPEED = 540
# Raising the cap turns arcade-faithful discipline into a modern bullet hose.
PLAYER_MAX_SHOTS = 1  # TWEAK: one shot on screen at a time, the Galaxian way — try 3
# TWEAK: the classic 3 — more ships = a friendlier game.
START_LIVES = 3
EXTRA_LIFE_AT = 7000  # one bonus ship, once
# Seconds of empty screen after you die, before the next ship flies in.
RESPAWN_DELAY = 1.6
INVULNERABLE_TIME = 2.2  # blink time after respawning — nothing can hit you while it runs

# --- the alien convoy ----------------------------------------------------------
# The formation grid: (sprite name, points in formation, points while diving)
# Row 0 is the top (flagships). Column count per row centers itself.
# TWEAK: edit this table to reshape the armada — fewer rows = an easier wave.
FORMATION_ROWS = [
    ("flagship", 2, (60, 150)),
    ("escort", 6, (50, 100)),
    ("drone", 8, (30, 60)),
    ("drone", 8, (30, 60)),
    ("drone", 8, (30, 60)),
]
# Where the grid hangs and how tightly it packs (all pixels).
FORMATION_TOP = 84
FORMATION_H_SPACING = 44
FORMATION_V_SPACING = 38
SWAY_AMPLITUDE = 34  # how far the convoy drifts side to side, in px
SWAY_PERIOD = 5.0  # seconds for one full left-right-left cycle
FLAP_RATE = 2.4  # wing-flap animation, frames per second

# --- diving attacks ------------------------------------------------------------
DIVE_INTERVAL = 2.6  # TWEAK: seconds between dives on wave 1... (lower = busier, harder)
DIVE_INTERVAL_MIN = 0.9  # ...tightening to this on later waves
DIVE_INTERVAL_STEP = 0.35  # how much faster each wave gets — the difficulty ramp itself
DIVE_SPEED = 170  # TWEAK: downward speed of a diving alien, px/sec — raise for a harder game
DIVE_SWERVE = 90  # TWEAK: sideways swoop amplitude, px — 0 dives dead straight
RETURN_SPEED = 150  # speed while gliding back into formation, px/sec
DIVER_FIRE_CHANCE = 1.1  # TWEAK: shots per second while diving — the main bullet-pressure dial
# TWEAK: how fast enemy bullets fall, px/sec — lower gives you more dodge room.
ENEMY_SHOT_SPEED = 240
ENEMY_SHOT_AIM = 0.6  # TWEAK: 0 = drop straight down, 1 = aim hard at the player

# --- presentation ----------------------------------------------------------------
HUD_COLOR = (120, 255, 160)
SCORE_COLOR = (255, 255, 255)
GAMEOVER_COLOR = (255, 80, 80)
# Seconds of "WAVE CLEAR!" breathing room before the next, faster wave arrives.
WAVE_CLEAR_PAUSE = 2.0
