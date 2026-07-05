"""galaxian-starfield-starter-kit — an arcade starfield plus sample games.

The library itself is the single file ``starfield.py``; everything else in
this package (demo, sample games, retro helpers) exists to show it off and
to teach. ``from starfield_kit import Starfield`` is all a game needs.
"""

from .starfield import GALAXIAN_PALETTE, WHITE_PALETTE, Starfield

__all__ = ["Starfield", "GALAXIAN_PALETTE", "WHITE_PALETTE"]
__version__ = "0.1.0"
