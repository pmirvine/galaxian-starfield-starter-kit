"""Shared helpers for the sample games: pixel-art sprites drawn from ASCII
grids (`pixelart`), bleepy sound effects synthesized at startup (`sfx`),
and chunky retro text (`ui`). No binary assets anywhere — everything the
games show and play is built from code you can read.

Explosion particles (`particles`) live here too; the games import that
module directly: ``from ..retro.particles import explosion``.
"""

from .pixelart import flipped, sprite
from .sfx import SoundBank
from .ui import blink_on, draw_text, pixel_font, pixel_text

# Re-exported here so games can write `from ..retro import sprite, SoundBank, ...`.
__all__ = [
    "sprite",
    "flipped",
    "SoundBank",
    "draw_text",
    "pixel_text",
    "pixel_font",
    "blink_on",
]
