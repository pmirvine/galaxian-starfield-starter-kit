"""LUNAR LANDER — gravity, fuel, and the gentlest touchdown you can manage.

Run it: ``uv run lander``

Controls: UP (or SPACE) fires the main engine, LEFT/RIGHT nudge sideways,
P pauses, ESC quits, SPACE restarts after game over. Land on a flat pad
with vertical speed under 45 and drift under 25 — narrower pads pay more.

Two things this demo shows:

*   **Stars over your own art.** The starfield is created with
    ``background=None`` and drawn *on top of* a dusk-gradient sky the game
    paints first — the overlay mode from the docs. The gradient is built
    once at startup (it never changes), which is the standard trick for
    any static background you compute rather than load.
*   **Real(ish) physics in eight lines.** Gravity adds to ``vy`` every
    frame; the engine subtracts from it while fuel lasts; nothing else.
    The whole game is those two accelerations plus a landing test — and
    the instrument panel that turns red when your numbers would kill you.
"""

from __future__ import annotations

import random

import pygame

from ..retro.particles import explosion
from ..retro.pixelart import sprite
from ..retro.sfx import SoundBank
from ..retro.ui import blink_on, draw_text
from ..starfield import Starfield

WIDTH, HEIGHT = 800, 500

GRAVITY = 55.0  # px/s^2, ever downward
MAIN_THRUST = 130.0  # px/s^2 upward while burning
SIDE_THRUST = 70.0
FUEL_START = 400.0
FUEL_MAIN_BURN = 22.0  # per second
FUEL_SIDE_BURN = 8.0
SAFE_VY = 45.0  # touch down harder than this and you are a crater
SAFE_VX = 25.0
START_SHIPS = 3

TERRAIN_STEP = 20  # px between terrain vertices
# Three pads: (width in terrain segments, score multiplier) — narrow pays.
PADS = [(5, 1), (4, 2), (2, 4)]

LANDER_ART = [
    "...WWW...",
    "..WWWWW..",
    ".WWCCCWW.",
    ".WWWWWWW.",
    "..GGGGG..",
    ".G.....G.",
    "G.......G",
]
FLAME_ART = [
    ".oo.",
    ".yy.",
    "oyyo",
    ".oo.",
    "..o.",
]
COLORS = {
    "W": (200, 205, 220),
    "C": (90, 220, 255),
    "G": (150, 160, 190),
    "o": (255, 150, 60),
    "y": (255, 220, 80),
}


def make_sky() -> pygame.Surface:
    """A vertical gradient from near-black space to a dim violet horizon,
    computed once. The starfield draws OVER this (background=None)."""
    sky = pygame.Surface((WIDTH, HEIGHT))
    top, bottom = (4, 4, 16), (52, 24, 58)
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom, strict=True))
        sky.fill(color, (0, y, WIDTH, 1))
    return sky


def make_terrain(rng: random.Random) -> tuple[list[int], list[tuple[int, int, int]]]:
    """Jagged ground plus flat landing pads. Returns (heights, pads) where
    heights has one entry per TERRAIN_STEP and each pad is (i0, i1, mult)."""
    n = WIDTH // TERRAIN_STEP + 1
    heights = [0] * n
    h = rng.randint(360, 450)
    for i in range(n):
        h += rng.randint(-22, 22)
        h = max(330, min(470, h))
        heights[i] = h
    pads = []
    zone = (n - 4) // len(PADS)  # spread the pads across thirds of the world
    for k, (width, mult) in enumerate(PADS):
        i0 = rng.randint(2 + k * zone, (k + 1) * zone - width)
        for i in range(i0, i0 + width + 1):
            heights[i] = heights[i0]  # flatten
        pads.append((i0, i0 + width, mult))
    return heights, pads


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("LUNAR LANDER — a starfield_kit demo")
        self.clock = pygame.time.Clock()
        self.sounds = SoundBank()
        self.rng = random.Random()
        self.ship_img = sprite(LANDER_ART, COLORS, scale=3)
        self.flame_img = sprite(FLAME_ART, COLORS, scale=3)
        self.sky = make_sky()

        # STARFIELD: background=None means "no fill — just stars", so the
        # gradient sky underneath shows through. Calm, white, sparse.
        self.stars = Starfield(
            (WIDTH, HEIGHT),
            velocity=(0, 0),
            background=None,
            palette="white",
            count=70,
            twinkle_speed=0.3,
            star_size=2,
            seed=1969,
        )

        self.time = 0.0
        self.paused = False
        self._pressed: set[int] = set()
        self.new_game()

    def new_game(self) -> None:
        self.score = 0
        self.ships = START_SHIPS
        self.fuel = FUEL_START
        self.game_over = False
        self.terrain, self.pads = make_terrain(self.rng)
        self.particles = []
        self.message = ""
        self.message_timer = 0.0
        self.reset_ship()

    def reset_ship(self) -> None:
        self.x, self.y = WIDTH * 0.15, 60.0
        self.vx, self.vy = 42.0, 0.0  # you always arrive drifting
        self.burning = False
        self.landed = False
        self.dead_timer = 0.0

    def ground_at(self, x: float) -> float:
        """Terrain height under x, linearly interpolated between vertices."""
        i = int(x // TERRAIN_STEP)
        i = max(0, min(len(self.terrain) - 2, i))
        t = (x - i * TERRAIN_STEP) / TERRAIN_STEP
        return self.terrain[i] + (self.terrain[i + 1] - self.terrain[i]) * t

    def pad_under(self, x: float) -> int:
        """Score multiplier of the pad below x, or 0 if that's bare rock."""
        half = self.ship_img.get_width() / 2
        for i0, i1, mult in self.pads:
            if i0 * TERRAIN_STEP <= x - half and x + half <= i1 * TERRAIN_STEP:
                return mult
        return 0

    def update(self, dt: float) -> None:
        if pygame.K_p in self._pressed:
            self.paused = not self.paused
        if self.paused or self.game_over:
            return
        self.message_timer = max(0.0, self.message_timer - dt)

        if self.dead_timer > 0:  # smoldering pause after a crash
            self.dead_timer -= dt
            for p in self.particles:
                p.update(dt)
            self.particles = [p for p in self.particles if not p.gone]
            if self.dead_timer <= 0:
                if self.ships > 0:
                    self.reset_ship()
                else:
                    self.game_over = True
                    self.sounds.play("game_over")
            return
        if self.landed:  # celebrate, then a fresh approach
            if self.message_timer <= 0:
                self.terrain, self.pads = make_terrain(self.rng)
                self.fuel = min(FUEL_START, self.fuel + 250)  # partial refuel
                self.reset_ship()
            return

        keys = pygame.key.get_pressed()
        # The physics. Gravity always; engines only while there is fuel.
        self.vy += GRAVITY * dt
        self.burning = False
        if self.fuel > 0:
            if keys[pygame.K_UP] or keys[pygame.K_SPACE]:
                self.vy -= (GRAVITY + MAIN_THRUST) * dt
                self.fuel -= FUEL_MAIN_BURN * dt
                self.burning = True
            side = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
            if side:
                self.vx += side * SIDE_THRUST * dt
                self.fuel -= FUEL_SIDE_BURN * dt
        self.fuel = max(0.0, self.fuel)
        if self.burning:
            self.sounds.loop("thrust")
        else:
            self.sounds.stop("thrust")
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x = max(15.0, min(WIDTH - 15.0, self.x))

        # Touchdown or impact?
        bottom = self.y + self.ship_img.get_height() / 2
        if bottom >= self.ground_at(self.x):
            self.sounds.stop("thrust")
            mult = self.pad_under(self.x)
            if mult and abs(self.vx) <= SAFE_VX and self.vy <= SAFE_VY:
                self.landed = True
                bonus = 50 * mult + int(self.fuel / 4)
                self.score += bonus
                self.message = f"THE EAGLE HAS LANDED  +{bonus}"
                self.message_timer = 2.5
                self.sounds.play("fanfare")
            else:
                self.ships -= 1
                self.dead_timer = 2.0
                self.message = "CRASHED" if mult == 0 else "TOO FAST"
                self.message_timer = 2.0
                self.particles += explosion(self.x, self.y, (255, 150, 60), big=True)
                self.sounds.play("big_boom")

    # -- drawing -------------------------------------------------------------

    def draw_terrain(self) -> None:
        points = [(i * TERRAIN_STEP, h) for i, h in enumerate(self.terrain)]
        pygame.draw.polygon(self.screen, (26, 26, 38), [*points, (WIDTH, HEIGHT), (0, HEIGHT)])
        pygame.draw.lines(self.screen, (150, 160, 190), False, points, 2)
        for i0, i1, mult in self.pads:
            x0, x1, y = i0 * TERRAIN_STEP, i1 * TERRAIN_STEP, self.terrain[i0]
            pygame.draw.line(self.screen, (120, 255, 160), (x0, y), (x1, y), 4)
            draw_text(
                self.screen,
                f"x{mult}",
                ((x0 + x1) // 2, y + 8),
                scale=1,
                anchor="midtop",
                color=(120, 255, 160),
            )

    def draw_instruments(self) -> None:
        altitude = max(0, int(self.ground_at(self.x) - self.y - self.ship_img.get_height() / 2))
        rows = [
            ("ALTITUDE", f"{altitude:4d}", (230, 230, 255)),
            ("H-SPEED", f"{self.vx:+5.0f}", self.gauge_color(abs(self.vx), SAFE_VX)),
            ("V-SPEED", f"{self.vy:+5.0f}", self.gauge_color(self.vy, SAFE_VY)),
            ("FUEL", f"{self.fuel:4.0f}", (255, 80, 80) if self.fuel < 80 else (230, 230, 255)),
        ]
        for i, (label, value, color) in enumerate(rows):
            y = 10 + i * 22
            draw_text(self.screen, label, (WIDTH - 150, y), scale=1, color=(110, 110, 140))
            draw_text(self.screen, value, (WIDTH - 12, y), scale=1, anchor="topright", color=color)

    @staticmethod
    def gauge_color(value: float, limit: float) -> tuple[int, int, int]:
        """Green while a touchdown at this reading would survive, red past it."""
        return (120, 255, 160) if value <= limit else (255, 80, 80)

    def draw(self) -> None:
        self.screen.blit(self.sky, (0, 0))  # our own background art first...
        self.stars.draw(self.screen)  # STARFIELD: ...then stars over it
        self.draw_terrain()

        if self.dead_timer <= 0 and not self.game_over:
            rect = self.ship_img.get_rect(center=(int(self.x), int(self.y)))
            self.screen.blit(self.ship_img, rect)
            if self.burning:
                flame = self.flame_img
                self.screen.blit(flame, flame.get_rect(midtop=(rect.centerx, rect.bottom - 6)))
        for p in self.particles:
            self.screen.fill(p.color, (int(p.x), int(p.y), 3, 3))

        draw_text(self.screen, f"SCORE {self.score:05d}", (12, 10))
        draw_text(self.screen, f"SHIPS {max(0, self.ships)}", (12, 34), color=(110, 110, 140))
        self.draw_instruments()

        if self.message_timer > 0:
            draw_text(
                self.screen,
                self.message,
                (WIDTH // 2, 150),
                scale=3,
                anchor="center",
                color=(120, 255, 160) if self.landed else (255, 80, 80),
            )
        if self.paused:
            draw_text(self.screen, "PAUSED", (WIDTH // 2, 200), scale=4, anchor="center")
        if self.game_over:
            draw_text(
                self.screen,
                "GAME OVER",
                (WIDTH // 2, 180),
                color=(255, 80, 80),
                scale=5,
                anchor="center",
            )
            if blink_on(self.time):
                draw_text(self.screen, "PRESS SPACE", (WIDTH // 2, 240), anchor="center")

    def run(self) -> int:
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000, 0.05)
            self.time += dt

            self._pressed = set()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    self._pressed.add(event.key)

            if self.game_over and pygame.K_SPACE in self._pressed:
                self.new_game()

            self.stars.update(dt)  # STARFIELD: just the twinkle here
            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()
        return 0


def main() -> int:
    return Game().run()


if __name__ == "__main__":
    raise SystemExit(main())
