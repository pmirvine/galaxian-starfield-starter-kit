"""The Defender cast as ASCII pixel art.

The ship faces right in the art; `load()` also builds a mirrored copy so
it can face left. The flame frames flicker behind the ship's tail while
thrusting.
"""

from __future__ import annotations

import pygame

from ..retro.pixelart import flipped, sprite

WHITE = (230, 230, 255)
GREY = (150, 160, 190)
RED = (255, 70, 70)
GREEN = (110, 255, 130)
YELLOW = (255, 220, 80)
ORANGE = (255, 150, 60)
CYAN = (90, 220, 255)

# The player's ship, nose pointing right: a low wedge with a cockpit hump.
SHIP = [
    "......WW........",
    ".....WWWW.......",
    "..GGWWCCWWGG....",
    ".GGGGWWWWWWWWWW.",
    "GGGGGGGGGGGGGGWW",
    ".GGGGWWWWWWWWWW.",
    "..GG......GG....",
]

# Two flame frames, drawn at the ship's tail while thrusting.
FLAME_A = [
    "..oo",
    "oooo",
    "yyoo",
    "oooo",
    "..oo",
]
FLAME_B = [
    ".o..",
    "ooo.",
    "yyoo",
    "ooo.",
    ".o..",
]

# A lander: the pod-with-legs that Defender players learn to fear.
LANDER = [
    "...ggg...",
    "..gyyyg..",
    ".ggyWygg.",
    "ggggggggg",
    ".g..g..g.",
    ".g..g..g.",
    "g...g...g",
]

# A baiter: the flat, fast saucer that punishes slow play.
BAITER = [
    "....rrrr....",
    ".rrrRRRRrrr.",
    "rrrrrrrrrrrr",
    ".r..r..r..r.",
]

LEGEND = {
    "W": WHITE,
    "G": GREY,
    "C": CYAN,
    "g": GREEN,
    "y": YELLOW,
    "o": ORANGE,
    "r": RED,
    "R": (255, 160, 160),
}


def load(scale: int) -> dict[str, list[pygame.Surface]]:
    """Every sprite at the given scale. "ship" holds [facing_right,
    facing_left]; "flame" holds two flicker frames (right-facing)."""
    ship = sprite(SHIP, LEGEND, scale)
    flame_a = sprite(FLAME_A, LEGEND, scale)
    flame_b = sprite(FLAME_B, LEGEND, scale)
    return {
        "ship": [ship, flipped(ship)],
        "flame": [flame_a, flame_b],
        "flame_left": [flipped(flame_a), flipped(flame_b)],
        "lander": [sprite(LANDER, LEGEND, scale)],
        "baiter": [sprite(BAITER, LEGEND, scale)],
    }
