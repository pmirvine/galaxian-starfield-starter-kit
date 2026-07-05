"""Shared helpers for the sample games: pixel-art sprites drawn from ASCII
grids (`pixelart`), bleepy sound effects synthesized at startup (`sfx`),
and chunky retro text (`ui`). No binary assets anywhere — everything the
games show and play is built from code you can read.
"""

from .pixelart import flipped, sprite
from .sfx import SoundBank
from .ui import blink_on, draw_text, pixel_font, pixel_text

__all__ = [
    "sprite",
    "flipped",
    "SoundBank",
    "draw_text",
    "pixel_text",
    "pixel_font",
    "blink_on",
]
