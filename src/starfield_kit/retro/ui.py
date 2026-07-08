"""Chunky retro text.

The trick: render text small with pygame's built-in font, then enlarge it
with plain ``scale()`` (nearest-neighbor). The enlarged pixels come out
blocky, which reads as "arcade" without shipping a font file.
"""

from __future__ import annotations

from functools import lru_cache

import pygame

Color = tuple[int, int, int]


@lru_cache(maxsize=8)
def pixel_font(size: int = 16) -> pygame.font.Font:
    """pygame's bundled default font at a small base size (cached)."""
    # Font(None, size) is the font pygame ships with — nothing to install or bundle.
    # lru_cache means each size is built once, then reused every frame for free.
    return pygame.font.Font(None, size)


def pixel_text(text: str, color: Color, scale: int = 2) -> pygame.Surface:
    """Render ``text`` as a chunky pixelated Surface."""
    # Step 1: render tiny and sharp — anti-aliased gray edges would smear once enlarged.
    small = pixel_font().render(text, False, color)  # False: no anti-aliasing
    if scale > 1:
        w, h = small.get_size()
        # Step 2: nearest-neighbor scale() turns every pixel into a crisp square block.
        return pygame.transform.scale(small, (w * scale, h * scale))
    return small


def draw_text(
    target: pygame.Surface,
    text: str,
    pos: tuple[int, int],
    *,
    color: Color = (255, 255, 255),
    scale: int = 2,
    anchor: str = "topleft",
) -> pygame.Rect:
    """Draw chunky text with its ``anchor`` ("topleft", "center",
    "midtop", "topright", ...any pygame.Rect attribute) at ``pos``.
    Returns the rect it covered, in case you want to draw relative to it.
    """
    surf = pixel_text(text, color, scale)
    # The anchor name becomes a Rect keyword: get_rect(center=pos), get_rect(midtop=pos)...
    rect = surf.get_rect(**{anchor: pos})
    target.blit(surf, rect)
    return rect


def blink_on(time_s: float, hz: float = 1.5) -> bool:
    """True/False alternating ``hz`` times per second — for flashing
    "PRESS SPACE" prompts: ``if blink_on(t): draw_text(...)``."""
    # (time_s * hz) % 1.0 sweeps 0..1 once per blink; "on" for the first 60% of it.
    # Callers can pass a faster or slower ``hz``; the duty cycle is shared kit-wide.
    return (time_s * hz) % 1.0 < 0.6
