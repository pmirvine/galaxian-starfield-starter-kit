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

Along the way you get the classic physics chain (acceleration changes
velocity, velocity changes position, everything scaled by ``dt``),
procedural terrain (a random walk of heights with flat pads carved in),
and win/lose rules that are just two speed checks. Every dial worth
turning is marked with a ``TWEAK`` comment — grep for it, then start
with GRAVITY, FUEL_START, and the SAFE_ limits.
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

# --- the dials: gravity, engines, fuel, lives ---------------------------------
GRAVITY = 55.0  # TWEAK: px/s^2, ever downward — lower for a moon, higher for a brute
MAIN_THRUST = 130.0  # TWEAK: px/s^2 upward while burning — must beat GRAVITY or you only sink
# TWEAK: sideways push in px/s^2 — higher makes drift easier to catch and to cause.
SIDE_THRUST = 70.0
# TWEAK: units of fuel at launch — the single biggest difficulty dial (lower = harder).
FUEL_START = 400.0
FUEL_MAIN_BURN = 22.0  # TWEAK: fuel units per second while the main engine burns
# TWEAK: fuel units per second while nudging sideways.
FUEL_SIDE_BURN = 8.0
SAFE_VY = 45.0  # TWEAK: max survivable fall in px/s — touch down harder and you are a crater
# TWEAK: max sideways drift in px/s at touchdown — raise both SAFE_ limits to forgive.
SAFE_VX = 25.0
# TWEAK: how many landers you get per game.
START_SHIPS = 3

TERRAIN_STEP = 20  # TWEAK: px between terrain vertices — smaller = craggier, busier ground
# Three pads: (width in terrain segments, score multiplier) — narrow pays.
# TWEAK: widen a pad or add a fourth — wider targets are far easier to hit.
PADS = [(5, 1), (4, 2), (2, 4)]

# --- pixel art (one character per pixel; "." is transparent) ------------------
# Edit these strings to redraw the ship — each letter looks up a color below.
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
    # Blend top -> bottom one 1px row at a time; t runs 0..1 down the screen.
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
    # Heights are y pixels from the TOP of the window, so bigger = lower ground.
    # A random walk: wander up or down a little each step, kept to a sane band.
    # TWEAK: the +/-22 is roughness in px per step — widen it for wilder mountains.
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
    """The whole game in one object: window, ship state, terrain, frame loop."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("LUNAR LANDER — a starfield_kit demo")
        self.clock = pygame.time.Clock()
        self.sounds = SoundBank()
        self.rng = random.Random()
        # Build the sprites once at startup; scale=3 turns each art pixel into 3x3.
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
            # A fixed seed = the same sky every run; change it for a new one.
            seed=1969,
        )

        self.time = 0.0
        self.paused = False
        # Keys that went down THIS frame — for one-shot actions like pause.
        # (Held keys are read separately with pygame.key.get_pressed().)
        self._pressed: set[int] = set()
        self.new_game()

    def new_game(self) -> None:
        """Fresh game: reset score, ships and fuel, and roll new terrain."""
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
        """Begin a new approach: back near the top-left, engines cold."""
        self.x, self.y = WIDTH * 0.15, 60.0
        self.vx, self.vy = 42.0, 0.0  # TWEAK: you always arrive drifting — the drift, in px/s
        self.burning = False
        self.landed = False
        self.dead_timer = 0.0

    def ground_at(self, x: float) -> float:
        """Terrain height under x, linearly interpolated between vertices."""
        # Find the segment x is over, then slide between its two endpoint
        # heights — t says how far across the segment we are (0 to 1).
        i = int(x // TERRAIN_STEP)
        i = max(0, min(len(self.terrain) - 2, i))
        t = (x - i * TERRAIN_STEP) / TERRAIN_STEP
        return self.terrain[i] + (self.terrain[i + 1] - self.terrain[i]) * t

    def pad_under(self, x: float) -> int:
        """Score multiplier of the pad below x, or 0 if that's bare rock."""
        # The whole ship must fit — both edges of the sprite inside the pad.
        half = self.ship_img.get_width() / 2
        for i0, i1, mult in self.pads:
            if i0 * TERRAIN_STEP <= x - half and x + half <= i1 * TERRAIN_STEP:
                return mult
        return 0

    def update(self, dt: float) -> None:
        """One tick of game logic: timers, physics, and the landing test."""
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
                # TWEAK: fuel units won back per landing, capped at a full tank.
                self.fuel = min(FUEL_START, self.fuel + 250)  # partial refuel
                self.reset_ship()
            return

        # get_pressed() reads keys HELD right now — perfect for continuous thrust.
        keys = pygame.key.get_pressed()
        # The physics. Gravity always; engines only while there is fuel.
        # Accelerations change velocity here; velocity moves the ship below.
        self.vy += GRAVITY * dt
        self.burning = False
        if self.fuel > 0:
            if keys[pygame.K_UP] or keys[pygame.K_SPACE]:
                # Cancel gravity, then push: net lift while burning is MAIN_THRUST.
                self.vy -= (GRAVITY + MAIN_THRUST) * dt
                self.fuel -= FUEL_MAIN_BURN * dt
                self.burning = True
            # True/False count as 1/0, so this is -1, 0 or +1 with no ifs.
            side = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
            if side:
                self.vx += side * SIDE_THRUST * dt
                self.fuel -= FUEL_SIDE_BURN * dt
        self.fuel = max(0.0, self.fuel)
        if self.burning:
            self.sounds.loop("thrust")
        else:
            self.sounds.stop("thrust")
        # Velocity moves the ship. There is no terminal velocity — clamp
        # self.vy right here if you want to cap how fast the lander falls.
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Keep the ship on screen; swap this clamp for wraparound if you like.
        self.x = max(15.0, min(WIDTH - 15.0, self.x))

        # Touchdown or impact?
        bottom = self.y + self.ship_img.get_height() / 2
        if bottom >= self.ground_at(self.x):
            self.sounds.stop("thrust")
            mult = self.pad_under(self.x)
            # Surviving needs all three: a pad underneath, gentle drift, gentle fall.
            if mult and abs(self.vx) <= SAFE_VX and self.vy <= SAFE_VY:
                self.landed = True
                # Narrow pads pay more, and leftover fuel is worth points too.
                bonus = 50 * mult + int(self.fuel / 4)
                self.score += bonus
                self.message = f"THE EAGLE HAS LANDED  +{bonus}"
                self.message_timer = 2.5
                self.sounds.play("fanfare")
            else:
                self.ships -= 1
                # Seconds of smoldering wreckage before the next ship (or game over).
                self.dead_timer = 2.0
                self.message = "CRASHED" if mult == 0 else "TOO FAST"
                self.message_timer = 2.0
                self.particles += explosion(self.x, self.y, (255, 150, 60), big=True)
                self.sounds.play("big_boom")

    # -- drawing -------------------------------------------------------------

    def draw_terrain(self) -> None:
        # One (x, y) point per vertex: the polygon is the dark fill down to the
        # bottom edge, then lines() retraces the ridge as a bright outline.
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
        # Each gauge goes red the moment that reading would wreck a landing.
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
        # Painter's algorithm: draw back to front — sky, stars, terrain, ship, HUD.
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

        # The HUD draws last so nothing in the world can cover it.
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
            # dt = seconds since last frame; multiply every speed by it. tick(60)
            # aims for 60 fps, and the min() stops a long hiccup (say, dragging
            # the window) from making the physics leap through the floor.
            dt = min(self.clock.tick(60) / 1000, 0.05)
            self.time += dt

            # Handle input: gather the keys freshly pressed this frame.
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

            # Update the world — physics, collisions and timers live in update().
            self.stars.update(dt)  # STARFIELD: just the twinkle here
            self.update(dt)
            # Draw everything back to front, then flip() shows the finished frame.
            self.draw()
            pygame.display.flip()

        pygame.quit()
        return 0


def main() -> int:
    return Game().run()


if __name__ == "__main__":
    raise SystemExit(main())
