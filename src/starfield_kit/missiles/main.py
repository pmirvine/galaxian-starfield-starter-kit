"""MISSILE DEFENSE — click the sky, save the cities.

Run it: ``uv run missiles``

Controls: point with the MOUSE, CLICK to fire an interceptor at the
crosshair, P pauses, ESC quits, CLICK restarts after game over.

This is the kit's mouse-input demo — everything else plays on the
keyboard. The ideas worth stealing:

*   **Aim where the player points.** The crosshair is just the mouse
    position (with the real cursor hidden); a click sends an interceptor
    from the battery to that exact point, where it blooms into a blast.
*   **Trails are two points.** Each missile only remembers where it
    started and where it is; the classic smoke trail is a single line
    between them, redrawn every frame.
*   **Expanding-circle collisions.** A blast is a circle whose radius
    follows a grow-hold-shrink timeline; anything whose head falls inside
    it dies — and enemy missiles die into blasts of their own, so one good
    shot can chain across half the sky.

The starfield is a static night sky in the arcade palette, twinkling
calmly over the doomed cities.

Every number worth a first experiment is marked ``TWEAK`` — grep for it
to speed up the warheads, widen the blasts, or tighten the ammo.
"""

from __future__ import annotations

import random

import pygame

from ..retro.pixelart import sprite
from ..retro.sfx import SoundBank
from ..retro.ui import blink_on, draw_text
from ..starfield import Starfield

# --- the dials ---------------------------------------------------------------
WIDTH, HEIGHT = 800, 520
# Everything below this y is ground; the cities and the battery stand on it.
GROUND_Y = HEIGHT - 36

# TWEAK: our shots' flight speed (px/sec) — lower means leading targets by more, a harder game.
INTERCEPTOR_SPEED = 460.0
# TWEAK: shots per wave — the whole ammo economy; lower = every click has to count.
AMMO_PER_WAVE = 15
ENEMY_BASE_SPEED = 55.0  # TWEAK: enemy descent (px/sec), +10 per wave — raise for a harder game
ENEMIES_PER_WAVE = 8  # TWEAK: warheads in wave 1, +3 per wave — more incoming = harder
SPAWN_GAP = 0.9  # TWEAK: seconds between incoming launches — lower = a denser, meaner sky

# TWEAK: full blast radius (px) — bigger blasts forgive rough aim and chain more easily.
BLAST_MAX_R = 55.0
# TWEAK: the blast's life in seconds — a longer HOLD keeps it lethal and helps chains.
BLAST_GROW, BLAST_HOLD, BLAST_SHRINK = 0.45, 0.35, 0.4

# TWEAK: one x per city — remove entries for a harder game; lose them all and it's over.
CITY_XS = [90, 205, 320, 480, 595, 710]  # the battery guards the center gap
BATTERY_X = WIDTH // 2

# Each string is one row of pixels; the letters index into COLORS (see retro/pixelart.py).
CITY_ART = [
    "..y.....y..",
    ".yby...yby.",
    "bbbbb.bbbbb",
    "bbbbbbbbbbb",
]
COLORS = {"b": (80, 120, 255), "y": (255, 220, 80)}

SKY_BLUE = (90, 220, 255)
RED = (255, 60, 60)


# --- the actors --------------------------------------------------------------
class Interceptor:
    """Our shot: flies from the battery to the clicked point, then blooms."""

    def __init__(self, target: tuple[int, int]) -> None:
        # origin never moves — it is the fixed end of the smoke-trail line.
        self.origin = pygame.Vector2(BATTERY_X, GROUND_Y - 14)
        self.pos = pygame.Vector2(self.origin)
        self.target = pygame.Vector2(target)
        self.arrived = False

    def update(self, dt: float) -> None:
        # Glide straight at the target; once we are within one frame's step,
        # snap onto it — otherwise we could overshoot and sail past forever.
        step = INTERCEPTOR_SPEED * dt
        if self.pos.distance_to(self.target) <= step:
            self.pos = pygame.Vector2(self.target)
            self.arrived = True
        else:
            self.pos += (self.target - self.pos).normalize() * step


class Enemy:
    """An incoming warhead: a point gliding from its launch spot toward a
    city, dragging its tell-tale line of a trail."""

    def __init__(self, wave: int, targets: list[int], rng: random.Random) -> None:
        # Launch from a random spot just above the top edge...
        self.origin = pygame.Vector2(rng.uniform(20, WIDTH - 20), -6)
        # ...aimed at a random surviving city (or the battery, once none are left).
        self.target = pygame.Vector2(rng.choice(targets), GROUND_Y)
        self.pos = pygame.Vector2(self.origin)
        # TWEAK: the 10 is the per-wave speed-up (px/sec) — the game's main difficulty ramp.
        self.speed = ENEMY_BASE_SPEED + 10 * (wave - 1)
        self.arrived = False

    def update(self, dt: float) -> None:
        # Same move-and-snap as Interceptor — both are points on a straight line.
        step = self.speed * dt
        if self.pos.distance_to(self.target) <= step:
            self.pos = pygame.Vector2(self.target)
            self.arrived = True
        else:
            self.pos += (self.target - self.pos).normalize() * step


class Blast:
    """An expanding, lingering, fading circle of destruction."""

    def __init__(self, pos: pygame.Vector2, max_r: float = BLAST_MAX_R) -> None:
        self.pos = pygame.Vector2(pos)
        self.max_r = max_r
        self.age = 0.0

    def update(self, dt: float) -> None:
        self.age += dt

    @property
    def radius(self) -> float:
        """Grow, hold, shrink — a timeline expressed as arithmetic."""
        if self.age < BLAST_GROW:
            return self.max_r * (self.age / BLAST_GROW)
        if self.age < BLAST_GROW + BLAST_HOLD:
            return self.max_r
        # Past grow+hold: t runs 0..1 across the shrink, so the radius fades to zero.
        t = (self.age - BLAST_GROW - BLAST_HOLD) / BLAST_SHRINK
        return self.max_r * max(0.0, 1.0 - t)

    @property
    def gone(self) -> bool:
        # update() throws the blast away once the whole timeline has played out.
        return self.age >= BLAST_GROW + BLAST_HOLD + BLAST_SHRINK


# --- the game ----------------------------------------------------------------
class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("MISSILE DEFENSE — a starfield_kit demo")
        pygame.mouse.set_visible(False)  # we draw our own crosshair
        self.clock = pygame.time.Clock()
        self.sounds = SoundBank()
        self.rng = random.Random()
        self.city_img = sprite(CITY_ART, COLORS, scale=3)

        # STARFIELD: a still night sky in the arcade colors, calm twinkle.
        # (The seed pins the star layout, so the sky is identical every run.)
        self.stars = Starfield(
            (WIDTH, HEIGHT),
            velocity=(0, 0),
            density=0.8,
            twinkle_speed=0.8,
            star_size=2,
            seed=1980,
        )

        self.time = 0.0
        self.paused = False
        self.new_game()

    def new_game(self) -> None:
        # Reset everything, then roll straight into wave 1.
        self.score = 0
        self.wave = 0
        # One flag per city: True = standing, False = rubble.
        self.cities = [True] * len(CITY_XS)
        self.interceptors: list[Interceptor] = []
        self.enemies: list[Enemy] = []
        self.blasts: list[Blast] = []
        self.game_over = False
        self.next_wave()

    def next_wave(self) -> None:
        self.wave += 1
        # A fresh clip each wave — unspent shots become points, they don't carry over.
        self.ammo = AMMO_PER_WAVE
        # TWEAK: the 3 is how many extra warheads each wave adds — the other difficulty ramp.
        self.to_spawn = ENEMIES_PER_WAVE + 3 * (self.wave - 1)
        # TWEAK: seconds of quiet before a wave's first launch — a breather between rounds.
        self.spawn_timer = 1.5

    def launch(self, target: tuple[int, int]) -> None:
        """Fire an interceptor at a point — wired to the mouse in run()."""
        # Fire only with ammo in the clip and a click safely above the ground.
        # TWEAK: shots in flight are uncapped — add `and len(self.interceptors) < 3`
        # to the test below for the classic ration-your-salvos feel.
        if self.ammo > 0 and not self.game_over and target[1] < GROUND_Y - 20:
            self.ammo -= 1
            self.interceptors.append(Interceptor(target))
            self.sounds.play("zap")

    def living_targets(self) -> list[int]:
        """The x positions enemies are still allowed to aim at."""
        alive = [x for x, ok in zip(CITY_XS, self.cities, strict=True) if ok]
        return alive or [BATTERY_X]  # nothing left? they come for the battery

    def update(self, dt: float) -> None:
        # Freeze the world while paused or dead — run() keeps drawing it anyway.
        if self.paused or self.game_over:
            return

        # Feed the wave in a missile at a time.
        if self.to_spawn > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                # Random jitter (x0.6..x1.4) keeps the launches from feeling metronomic.
                self.spawn_timer = SPAWN_GAP * self.rng.uniform(0.6, 1.4)
                self.to_spawn -= 1
                self.enemies.append(Enemy(self.wave, self.living_targets(), self.rng))

        # Move everything — all three kinds share the same update(dt) shape.
        for thing in (*self.interceptors, *self.enemies, *self.blasts):
            thing.update(dt)

        # Interceptors that reach their mark become blasts.
        # (Looping over a list(...) copy lets us remove from the real list mid-loop.)
        for shot in list(self.interceptors):
            if shot.arrived:
                self.interceptors.remove(shot)
                self.blasts.append(Blast(shot.pos))
                self.sounds.play("boom")

        # Any enemy head inside any blast dies — into a blast of its own,
        # which is what makes chain reactions possible.
        for enemy in list(self.enemies):
            # Point-in-circle is one distance check — no rects needed for round blasts.
            if any(b.pos.distance_to(enemy.pos) <= b.radius for b in self.blasts):
                self.enemies.remove(enemy)
                # TWEAK: 40 is the chain-blast radius (px) — bigger = easier, showier chains.
                self.blasts.append(Blast(enemy.pos, max_r=40))
                self.score += 25
                self.sounds.play("boom", volume=0.6)

        # Enemies that get through level a city.
        for enemy in list(self.enemies):
            if enemy.arrived:
                self.enemies.remove(enemy)
                self.blasts.append(Blast(enemy.pos, max_r=48))
                for i, x in enumerate(CITY_XS):
                    # Find which city was struck: its x sits within a few px of the aim point.
                    if self.cities[i] and abs(x - enemy.target.x) < 3:
                        self.cities[i] = False
                        self.sounds.play("big_boom")

        # Rebuild the list without finished blasts — the tidy way to drop dead things.
        self.blasts = [b for b in self.blasts if not b.gone]

        # No cities left ends the game; a clear sky with cities left starts the next wave.
        if not any(self.cities):
            self.game_over = True
            self.sounds.play("game_over")
        elif self.to_spawn == 0 and not self.enemies and not self.blasts:
            # Wave survived: bonus for thrift and for what still stands.
            self.score += 5 * self.ammo + 100 * sum(self.cities)
            self.sounds.play("fanfare")
            self.next_wave()

    def draw(self) -> None:
        # Back to front: the starfield repaints the whole sky, erasing last frame.
        self.stars.draw(self.screen)

        # Trails first (behind the bright heads): one line each.
        for enemy in self.enemies:
            pygame.draw.line(self.screen, (120, 40, 40), enemy.origin, enemy.pos, 2)
            # A 4x4 fill() square is the cheapest way to paint the bright head.
            self.screen.fill((255, 255, 255), (int(enemy.pos.x) - 2, int(enemy.pos.y) - 2, 4, 4))
        for shot in self.interceptors:
            pygame.draw.line(self.screen, (40, 80, 120), shot.origin, shot.pos, 2)
            self.screen.fill(SKY_BLUE, (int(shot.pos.x) - 2, int(shot.pos.y) - 2, 4, 4))
            # the classic X marking where the blast will bloom
            x, y = int(shot.target.x), int(shot.target.y)
            pygame.draw.line(self.screen, SKY_BLUE, (x - 4, y - 4), (x + 4, y + 4))
            pygame.draw.line(self.screen, SKY_BLUE, (x - 4, y + 4), (x + 4, y - 4))
        for blast in self.blasts:
            r = int(blast.radius)
            if r > 1:
                # Flick between two fire colors ~10 times a second; width 3 keeps it a ring.
                color = (255, 220, 80) if int(blast.age * 20) % 2 else (255, 150, 60)
                pygame.draw.circle(self.screen, color, blast.pos, r, 3)

        # The ground, the cities, the battery.
        self.screen.fill((150, 120, 40), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        for x, alive in zip(CITY_XS, self.cities, strict=True):
            if alive:
                rect = self.city_img.get_rect(midbottom=(x, GROUND_Y + 2))
                self.screen.blit(self.city_img, rect)
            else:
                self.screen.fill((60, 50, 30), (x - 16, GROUND_Y - 6, 32, 6))  # rubble
        # The battery is the little pyramid in the gap between the two city banks.
        pygame.draw.polygon(
            self.screen,
            (150, 120, 40),
            [(BATTERY_X - 30, GROUND_Y), (BATTERY_X, GROUND_Y - 22), (BATTERY_X + 30, GROUND_Y)],
        )

        # The crosshair is wherever the mouse is.
        mx, my = pygame.mouse.get_pos()
        pygame.draw.line(self.screen, (255, 255, 255), (mx - 7, my), (mx + 7, my))
        pygame.draw.line(self.screen, (255, 255, 255), (mx, my - 7), (mx, my + 7))

        # HUD last, so the text sits on top of everything.
        draw_text(self.screen, f"SCORE {self.score:06d}", (12, 10))
        draw_text(
            self.screen,
            f"WAVE {self.wave}",
            (WIDTH - 12, 10),
            anchor="topright",
            color=(120, 255, 160),
        )
        # The ammo counter turns red as a running-dry warning.
        color = RED if self.ammo <= 3 else (230, 230, 255)
        draw_text(
            self.screen, f"AMMO {self.ammo:02d}", (WIDTH // 2, 10), anchor="midtop", color=color
        )

        if self.paused:
            draw_text(self.screen, "PAUSED", (WIDTH // 2, 220), scale=4, anchor="center")
        if self.game_over:
            draw_text(
                self.screen, "THE END", (WIDTH // 2, 200), color=RED, scale=6, anchor="center"
            )
            if blink_on(self.time):
                draw_text(self.screen, "CLICK TO TRY AGAIN", (WIDTH // 2, 260), anchor="center")

    def run(self) -> int:
        """The frame loop: read input, update the world, draw it, repeat."""
        running = True
        while running:
            # dt = seconds since last frame; the 0.05 cap stops a stall teleporting things.
            dt = min(self.clock.tick(60) / 1000, 0.05)
            self.time += dt

            # Handle input: quit, pause, and the click that fires (or restarts).
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.game_over:
                        self.new_game()
                    else:
                        self.launch(event.pos)  # the mouse does the aiming

            # Update the world, then draw it back to front.
            self.stars.update(dt)
            self.update(dt)
            self.draw()
            # flip() swaps the finished frame onto the monitor in one go.
            pygame.display.flip()

        pygame.quit()
        return 0


def main() -> int:
    """Entry point for ``uv run missiles`` (see [project.scripts] in pyproject.toml)."""
    return Game().run()


if __name__ == "__main__":
    raise SystemExit(main())
