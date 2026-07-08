"""Interactive Starfield playground: `uv run starfield-demo`.

Every Starfield parameter, live on keys — the fastest way to find the
settings you want for your own game. The HUD shows the exact constructor
call for what you are currently looking at, ready to copy.

Controls (also drawn in the window; `h` hides them):

    arrows     push the star velocity around (hold to steer)
    space      stop scrolling (velocity back to zero)
    d          cycle density         t  cycle twinkle speed
    l          cycle layer count     p  cycle palette
    s          cycle star size       r  reseed — a brand new sky
    1 / 2 / 3  presets: Galaxian drift / side-scroller / static backdrop
    h          show or hide the help lines
    esc or q   quit (the window is resizable, too)
"""

from __future__ import annotations

import random

import pygame

from .retro.ui import draw_text
from .starfield import Starfield

SIZE = (960, 540)  # TWEAK: starting window size in pixels (you can also just resize the window)
# Each key steps through one of these lists, one press at a time. TWEAK: reorder
# or add values freely — every parameter is explained in docs/starfield-api.md.
DENSITIES = [0.25, 0.5, 1.0, 2.0, 4.0]  # 1.0 ≈ one star per 2000 px of screen area
TWINKLES = [0.0, 0.3, 1.0, 2.0, 4.0]  # 0 = steady stars, 1.0 = arcade blink, 4.0 = frantic
LAYER_CHOICES = [1, 2, 3, 5]  # parallax planes; far ones are smaller, fainter, slower
STAR_SIZES: list[int | None] = [None, 1, 2, 3, 4]  # None = pick automatically
# A palette is a preset name or any list of RGB tuples. TWEAK: swap the embers
# colors for your own — a few related shades usually look best.
PALETTES: list[str | list[tuple[int, int, int]]] = [
    "galaxian",
    "white",
    [(255, 190, 120), (255, 120, 60), (255, 230, 180)],  # a custom "embers" palette
]
PALETTE_NAMES = ["galaxian", "white", "custom embers"]  # HUD labels; keep in step with PALETTES

# The in-window cheat sheet (`h` toggles it). If you rebind a key below, update it here too.
HELP_LINES = [
    "arrows  push star velocity      space  stop scrolling",
    "d density   t twinkle   l layers   p palette   s star size   r new sky",
    "presets:  1 galaxian   2 side-scroller   3 static backdrop",
    "h hide help    esc quit    (window is resizable)",
]


class DemoState:
    """The current parameter choices, and the Starfield built from them."""

    def __init__(self, size: tuple[int, int]) -> None:
        self.size = size
        self.density_i = 2  # index into DENSITIES -> 1.0
        self.twinkle_i = 2  # -> 1.0
        self.layers_i = 0  # -> 1
        self.palette_i = 0  # -> "galaxian"
        self.size_i = 0  # index into STAR_SIZES -> None (automatic)
        self.seed = 2026  # any integer = repeatable sky; `r` swaps in a random one
        self.velocity = (0.0, 30.0)  # TWEAK: starting drift in px/s; +y moves stars downward
        self.field = self.build()

    def build(self) -> Starfield:
        """(Re)build the field. Cheap enough to do on any parameter change."""
        field = Starfield(
            self.size,
            velocity=self.velocity,
            density=DENSITIES[self.density_i],
            twinkle_speed=TWINKLES[self.twinkle_i],
            layers=LAYER_CHOICES[self.layers_i],
            palette=PALETTES[self.palette_i],
            star_size=STAR_SIZES[self.size_i],
            seed=self.seed,
        )
        self.field = field
        return field

    def constructor_text(self) -> str:
        """The code for the field being shown, for copying into your game."""
        vx, vy = self.field.velocity
        # Mention only what differs from the defaults, so the line stays short and pasteable.
        parts = [f"velocity=({vx:.0f}, {vy:.0f})"]
        if DENSITIES[self.density_i] != 1.0:
            parts.append(f"density={DENSITIES[self.density_i]}")
        if TWINKLES[self.twinkle_i] != 1.0:
            parts.append(f"twinkle_speed={TWINKLES[self.twinkle_i]}")
        if LAYER_CHOICES[self.layers_i] != 1:
            parts.append(f"layers={LAYER_CHOICES[self.layers_i]}")
        if self.palette_i == 1:
            parts.append("palette='white'")
        elif self.palette_i == 2:
            parts.append("palette=[...]")
        if STAR_SIZES[self.size_i] is not None:
            parts.append(f"star_size={STAR_SIZES[self.size_i]}")
        return f"Starfield(size, {', '.join(parts)})"


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode(SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("starfield playground")
    clock = pygame.time.Clock()
    state = DemoState(screen.get_size())
    show_help = True

    running = True
    while running:
        # dt = seconds since last frame; multiply every speed by it. tick(60)
        # also sleeps as needed to cap the loop at 60 frames per second.
        dt = clock.tick(60) / 1000

        # --- input: hotkeys arrive as one-shot events.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                # resize() keeps the layout and tops up stars to hold the same density.
                state.size = (event.w, event.h)
                state.field.resize(state.size)
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif key == pygame.K_h:
                    show_help = not show_help
                elif key == pygame.K_SPACE:
                    state.field.velocity = (0, 0)
                elif key == pygame.K_d:
                    state.density_i = (state.density_i + 1) % len(DENSITIES)
                    # Keep the current drift across the rebuild (same below for l/p/r).
                    state.velocity = state.field.velocity
                    state.build()
                elif key == pygame.K_t:
                    # twinkle_speed is live too — assign it, no rebuild needed.
                    state.twinkle_i = (state.twinkle_i + 1) % len(TWINKLES)
                    state.field.twinkle_speed = TWINKLES[state.twinkle_i]
                elif key == pygame.K_l:
                    state.layers_i = (state.layers_i + 1) % len(LAYER_CHOICES)
                    state.velocity = state.field.velocity
                    state.build()
                elif key == pygame.K_p:
                    state.palette_i = (state.palette_i + 1) % len(PALETTES)
                    state.velocity = state.field.velocity
                    state.build()
                elif key == pygame.K_s:
                    # star_size is a live property — no rebuild needed
                    state.size_i = (state.size_i + 1) % len(STAR_SIZES)
                    state.field.star_size = STAR_SIZES[state.size_i]
                elif key == pygame.K_r:
                    state.seed = random.randrange(1_000_000)
                    state.velocity = state.field.velocity
                    state.build()
                elif key == pygame.K_1:  # classic Galaxian: gentle downward drift
                    state.layers_i, state.palette_i, state.twinkle_i = 0, 0, 2
                    state.velocity = (0, 30)
                    state.build()
                elif key == pygame.K_2:  # side-scroller: streaming left, deep parallax
                    state.layers_i, state.twinkle_i = 2, 2
                    state.velocity = (-180, 0)
                    state.build()
                elif key == pygame.K_3:  # static twinkling backdrop (Space Invaders)
                    state.layers_i, state.twinkle_i = 0, 2
                    state.velocity = (0, 0)
                    state.build()

        # Held arrow keys push the velocity around, like steering a camera.
        keys = pygame.key.get_pressed()
        vx, vy = state.field.velocity
        push = 240 * dt  # TWEAK: arrow strength — px/s of extra velocity per second held
        # Bools subtract to -1, 0, or +1, so each axis reads in one line.
        vx += push * (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT])
        vy += push * (keys[pygame.K_DOWN] - keys[pygame.K_UP])
        state.field.velocity = (vx, vy)

        # --- update: scroll and twinkle the stars.
        state.field.update(dt)
        # --- draw: the sky first, then the HUD text over it.
        state.field.draw(screen)

        draw_text(screen, state.constructor_text(), (12, 10), color=(120, 255, 160))
        info = (
            f"{state.field.star_count} stars   "
            f"palette: {PALETTE_NAMES[state.palette_i]}   "
            f"{clock.get_fps():.0f} fps"
        )
        draw_text(screen, info, (12, 34), color=(150, 150, 170))
        if show_help:
            for i, line in enumerate(HELP_LINES):
                # Stack the help lines upward from the bottom edge, 22 px apart.
                y = screen.get_height() - 14 - (len(HELP_LINES) - i) * 22
                draw_text(screen, line, (12, y), color=(110, 110, 140))

        pygame.display.flip()  # put the finished frame on screen

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
