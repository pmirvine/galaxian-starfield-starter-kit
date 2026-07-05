"""GALAXIAN 1979 — a non-interactive tableau at true arcade geometry.

Run it: ``uv run galaxians-demo``   (Esc or Q quits; nothing else responds)

This is not a game — it is a still life. A static convoy, score header,
and player ship are arranged the way Galaxian's screen laid them out, and
then *only the starfield moves*. The point is to show the "pure" starfield
as it appeared in the 1979 cabinet, isolated from gameplay, using the
generic library dialed to the original's real numbers:

* **Geometry** — the cabinet's rotated monitor showed 224x256 native
  pixels; this window is exactly that at 3x scale (672x768), with 3-pixel
  stars to match (``star_size=SCALE``).
* **Drift** — the hardware's star pattern slipped half a native pixel per
  16.5 ms frame: 0.5 x 60.606 fps x 3 ≈ 91 window-pixels/second, straight
  down.
* **Population** — the board's shift register fires 256 stars per cycle,
  4 of them black, so 252 visible: ``count=252``.
* **Color** — the default "galaxian" palette *is* the board's DAC output.

(For the cycle-exact emulation of the star circuit itself, see the
companion repo: https://github.com/pmirvine/galaxian-starfield — and
``docs/arcade-accurate.md`` is a step-by-step guide to swapping it into
this very file. Three small edits and the model becomes the machine.)

This file is also a deliberately clean starting point for your own game:
everything on screen is already drawn at arcade proportions, so wiring in
a keyboard-controlled ship and moving the convoy is exactly the road the
full sample (``uv run galaxians``) already walked. Steal from both.
"""

from __future__ import annotations

import pygame

from ..retro.ui import draw_text
from ..starfield import Starfield
from . import sprites

# --- the 1979 numbers ---------------------------------------------------------

NATIVE_W, NATIVE_H = 224, 256  # the rotated arcade monitor, in native pixels
SCALE = 3  # one native pixel = a 3x3 block here
WINDOW_W, WINDOW_H = NATIVE_W * SCALE, NATIVE_H * SCALE  # 672 x 768

ARCADE_FPS = 60.606  # 6.144 MHz pixel clock / (384 x 264 raster)
DRIFT_PX_PER_S = 0.5 * ARCADE_FPS * SCALE  # half a native pixel per frame ~ 91
STAR_COUNT = 252  # 256 stars per LFSR cycle, minus the 4 black ones

# The convoy, top row first: Galaxian flew 2 flagships, 6 escorts, and
# ranks of drones beneath them. Grid pitch is 16 native pixels (48 here).
CONVOY_ROWS = [
    ("flagship", 2),
    ("escort", 6),
    ("drone", 8),
    ("drone", 10),
    ("drone", 10),
]
CONVOY_TOP = 150
H_SPACING = 16 * SCALE
V_SPACING = 13 * SCALE

SHIP_Y = 700  # the fighter waits near the bottom, as ever
RED = (255, 60, 60)
WHITE = (230, 230, 255)


def make_starfield() -> Starfield:
    """The library configured to the cabinet's numbers (see module docs)."""
    return Starfield(
        (WINDOW_W, WINDOW_H),
        velocity=(0, DRIFT_PX_PER_S),
        count=STAR_COUNT,
        star_size=SCALE,
        palette="galaxian",
        seed=1979,
    )


def draw_frame(
    screen: pygame.Surface,
    stars: Starfield,
    art: dict[str, list[pygame.Surface]],
) -> None:
    """One complete frame: moving sky, then the frozen 1979 tableau."""
    stars.draw(screen)

    # The score header, laid out like the arcade's top rows.
    draw_text(screen, "1UP", (110, 14), color=RED, anchor="midtop")
    draw_text(screen, "HIGH SCORE", (WINDOW_W // 2, 14), color=RED, anchor="midtop")
    draw_text(screen, "00000", (110, 40), color=WHITE, anchor="midtop")
    draw_text(screen, "20000", (WINDOW_W // 2, 40), color=WHITE, anchor="midtop")

    # The convoy at rest (in play it sways and peels off divers — that part
    # is yours to add; the galaxians sample shows how).
    for row, (kind, count) in enumerate(CONVOY_ROWS):
        frame = art[kind][0]
        y = CONVOY_TOP + row * V_SPACING
        for col in range(count):
            x = WINDOW_W // 2 + (col - (count - 1) / 2) * H_SPACING
            screen.blit(frame, frame.get_rect(center=(int(x), y)))

    # The fighter, plus two spares in the corner where the cabinet kept them.
    ship = art["player"][0]
    screen.blit(ship, ship.get_rect(center=(WINDOW_W // 2, SHIP_Y)))
    spare = pygame.transform.scale_by(ship, 0.7)
    for i in range(2):
        screen.blit(spare, (12 + i * (spare.get_width() + 8), WINDOW_H - 40))


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("GALAXIAN 1979 — the starfield, at arcade geometry")
    clock = pygame.time.Clock()
    stars = make_starfield()
    art = sprites.load(SCALE)

    running = True
    while running:
        # Ticking at the cabinet's own 60.606 Hz is a nicety, not a need:
        # the starfield is dt-based, so any frame rate scrolls correctly.
        dt = clock.tick(ARCADE_FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q)
            ):
                running = False

        stars.update(dt)
        draw_frame(screen, stars, art)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
