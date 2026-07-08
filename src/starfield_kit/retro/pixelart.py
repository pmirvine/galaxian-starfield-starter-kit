"""Sprites as ASCII art.

Instead of shipping image files, the sample games describe each sprite as a
list of strings — one character per pixel — plus a mapping from character to
color. It keeps every sprite readable, editable, and diff-able right in the
source code:

    SHIP = [
        "....W....",
        "....W....",
        "...WWW...",
        "R..WWW..R",
        "RWWWWWWWR",
    ]
    ship_surface = sprite(SHIP, {"W": (220, 220, 255), "R": (255, 40, 40)}, scale=3)

'.' (or a space) means transparent. ``scale`` blows each character up into
an NxN block of pixels, which is what gives the chunky arcade look.

Each game keeps its grids in its own package, so editing a game's art only
changes that game — the safest, most fun place to experiment. This module
itself is shared by every sample.
"""

from __future__ import annotations

from collections.abc import Sequence

import pygame

Color = tuple[int, int, int]


def sprite(rows: Sequence[str], colors: dict[str, Color], scale: int = 1) -> pygame.Surface:
    """Build a Surface from ASCII art. See the module docstring for the format."""
    width = max(len(row) for row in rows)  # rows may differ in length; size to the longest
    # One Surface pixel per character; SRCALPHA makes the untouched pixels transparent.
    surf = pygame.Surface((width, len(rows)), pygame.SRCALPHA)
    # y walks the rows (top to bottom), x the characters — a 1:1 grid-to-pixel map.
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char in (".", " "):
                continue
            try:
                surf.set_at((x, y), colors[char])
            except KeyError:
                # An unlisted character is almost always a typo — fail with a message
                # that names the row, instead of a bare KeyError from nowhere.
                raise ValueError(
                    f"sprite row {y} uses {char!r} but colors has no entry for it"
                ) from None
    if scale > 1:
        # Plain scale() (not smoothscale) keeps the edges hard and pixelated.
        surf = pygame.transform.scale(surf, (width * scale, len(rows) * scale))
    return surf


def flipped(surf: pygame.Surface) -> pygame.Surface:
    """A horizontally mirrored copy — handy for ships that face both ways."""
    return pygame.transform.flip(surf, True, False)
