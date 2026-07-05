"""The Galaxians cast, drawn as ASCII pixel art.

Each sprite is a list of strings (one character per pixel) with a legend
mapping characters to colors. Aliens get two frames so their wings flap.
Edit the art right here — add a row, change a color, give the flagship a
hat. The `load()` function turns the art into pygame Surfaces.
"""

from __future__ import annotations

import pygame

from ..retro.pixelart import sprite

# Legend characters shared by all the art below.
WHITE = (230, 230, 255)
RED = (255, 60, 60)
BLUE = (80, 120, 255)
CYAN = (90, 220, 255)
PURPLE = (200, 90, 255)
YELLOW = (255, 220, 80)
GREEN = (110, 255, 130)
ORANGE = (255, 150, 60)

# --- the player's fighter -----------------------------------------------------

PLAYER = [
    "......W......",
    "......W......",
    ".....WWW.....",
    ".....WRW.....",
    "....WWRWW....",
    "....WWRWW....",
    "B...WWRWW...B",
    "BB.WWWRWWW.BB",
    "BWWWWWRWWWWWB",
    "BWWW.WRW.WWWB",
    "BW...WWW...WB",
]

# --- the convoy ---------------------------------------------------------------
# Two frames each: A = wings spread, B = wings tucked.

DRONE_A = [
    ".r.......r.",
    "..r.....r..",
    "...ccccc...",
    "..ccWcWcc..",
    ".ccccccccc.",
    "cc.ccccc.cc",
    "c..c...c..c",
    "...c...c...",
]

DRONE_B = [
    ".r.......r.",
    "..r.....r..",
    "...ccccc...",
    "..ccWcWcc..",
    "..ccccccc..",
    ".c.ccccc.c.",
    ".c.c...c.c.",
    "..cc...cc..",
]

ESCORT_A = [
    ".y.......y.",
    "..y.....y..",
    "...ppppp...",
    "..ppWpWpp..",
    ".ppppppppp.",
    "pp.ppppp.pp",
    "p..p...p..p",
    "...p...p...",
]

ESCORT_B = [
    ".y.......y.",
    "..y.....y..",
    "...ppppp...",
    "..ppWpWpp..",
    "..ppppppp..",
    ".p.ppppp.p.",
    ".p.p...p.p.",
    "..pp...pp..",
]

FLAGSHIP_A = [
    "..g.....g..",
    ".y.y...y.y.",
    "..yyyyyyy..",
    ".yygWyWgyy.",
    "yyyyyyyyyyy",
    "yy.yyyyy.yy",
    "y..gyyyg..y",
    "...y...y...",
]

FLAGSHIP_B = [
    "..g.....g..",
    ".y.y...y.y.",
    "..yyyyyyy..",
    ".yygWyWgyy.",
    ".yyyyyyyyy.",
    ".y.yyyyy.y.",
    "..gyyyyg...",
    "..y.....y..",
]

LEGEND = {
    "W": WHITE,
    "R": RED,
    "B": BLUE,
    "c": CYAN,
    "r": RED,
    "p": PURPLE,
    "y": YELLOW,
    "g": GREEN,
    "o": ORANGE,
}


def load(scale: int) -> dict[str, list[pygame.Surface]]:
    """Build every sprite at the given pixel scale. Returns a mapping of
    name -> animation frames (a one-frame list for the player)."""
    return {
        "player": [sprite(PLAYER, LEGEND, scale)],
        "drone": [sprite(DRONE_A, LEGEND, scale), sprite(DRONE_B, LEGEND, scale)],
        "escort": [sprite(ESCORT_A, LEGEND, scale), sprite(ESCORT_B, LEGEND, scale)],
        "flagship": [sprite(FLAGSHIP_A, LEGEND, scale), sprite(FLAGSHIP_B, LEGEND, scale)],
    }
