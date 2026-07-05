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
"""

from __future__ import annotations

import random

import pygame

from ..retro.pixelart import sprite
from ..retro.sfx import SoundBank
from ..retro.ui import blink_on, draw_text
from ..starfield import Starfield

WIDTH, HEIGHT = 800, 520
GROUND_Y = HEIGHT - 36

INTERCEPTOR_SPEED = 460.0
AMMO_PER_WAVE = 15
ENEMY_BASE_SPEED = 55.0  # +10 per wave
ENEMIES_PER_WAVE = 8  # +3 per wave
SPAWN_GAP = 0.9  # seconds between incoming launches

BLAST_MAX_R = 55.0
BLAST_GROW, BLAST_HOLD, BLAST_SHRINK = 0.45, 0.35, 0.4

CITY_XS = [90, 205, 320, 480, 595, 710]  # the battery guards the center gap
BATTERY_X = WIDTH // 2

CITY_ART = [
    "..y.....y..",
    ".yby...yby.",
    "bbbbb.bbbbb",
    "bbbbbbbbbbb",
]
COLORS = {"b": (80, 120, 255), "y": (255, 220, 80)}

SKY_BLUE = (90, 220, 255)
RED = (255, 60, 60)


class Interceptor:
    """Our shot: flies from the battery to the clicked point, then blooms."""

    def __init__(self, target: tuple[int, int]) -> None:
        self.origin = pygame.Vector2(BATTERY_X, GROUND_Y - 14)
        self.pos = pygame.Vector2(self.origin)
        self.target = pygame.Vector2(target)
        self.arrived = False

    def update(self, dt: float) -> None:
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
        self.origin = pygame.Vector2(rng.uniform(20, WIDTH - 20), -6)
        self.target = pygame.Vector2(rng.choice(targets), GROUND_Y)
        self.pos = pygame.Vector2(self.origin)
        self.speed = ENEMY_BASE_SPEED + 10 * (wave - 1)
        self.arrived = False

    def update(self, dt: float) -> None:
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
        t = (self.age - BLAST_GROW - BLAST_HOLD) / BLAST_SHRINK
        return self.max_r * max(0.0, 1.0 - t)

    @property
    def gone(self) -> bool:
        return self.age >= BLAST_GROW + BLAST_HOLD + BLAST_SHRINK


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
        self.score = 0
        self.wave = 0
        self.cities = [True] * len(CITY_XS)
        self.interceptors: list[Interceptor] = []
        self.enemies: list[Enemy] = []
        self.blasts: list[Blast] = []
        self.game_over = False
        self.next_wave()

    def next_wave(self) -> None:
        self.wave += 1
        self.ammo = AMMO_PER_WAVE
        self.to_spawn = ENEMIES_PER_WAVE + 3 * (self.wave - 1)
        self.spawn_timer = 1.5

    def launch(self, target: tuple[int, int]) -> None:
        """Fire an interceptor at a point — wired to the mouse in run()."""
        if self.ammo > 0 and not self.game_over and target[1] < GROUND_Y - 20:
            self.ammo -= 1
            self.interceptors.append(Interceptor(target))
            self.sounds.play("zap")

    def living_targets(self) -> list[int]:
        alive = [x for x, ok in zip(CITY_XS, self.cities, strict=True) if ok]
        return alive or [BATTERY_X]  # nothing left? they come for the battery

    def update(self, dt: float) -> None:
        if self.paused or self.game_over:
            return

        # Feed the wave in a missile at a time.
        if self.to_spawn > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_timer = SPAWN_GAP * self.rng.uniform(0.6, 1.4)
                self.to_spawn -= 1
                self.enemies.append(Enemy(self.wave, self.living_targets(), self.rng))

        for thing in (*self.interceptors, *self.enemies, *self.blasts):
            thing.update(dt)

        # Interceptors that reach their mark become blasts.
        for shot in list(self.interceptors):
            if shot.arrived:
                self.interceptors.remove(shot)
                self.blasts.append(Blast(shot.pos))
                self.sounds.play("boom")

        # Any enemy head inside any blast dies — into a blast of its own,
        # which is what makes chain reactions possible.
        for enemy in list(self.enemies):
            if any(b.pos.distance_to(enemy.pos) <= b.radius for b in self.blasts):
                self.enemies.remove(enemy)
                self.blasts.append(Blast(enemy.pos, max_r=40))
                self.score += 25
                self.sounds.play("boom", volume=0.6)

        # Enemies that get through level a city.
        for enemy in list(self.enemies):
            if enemy.arrived:
                self.enemies.remove(enemy)
                self.blasts.append(Blast(enemy.pos, max_r=48))
                for i, x in enumerate(CITY_XS):
                    if self.cities[i] and abs(x - enemy.target.x) < 3:
                        self.cities[i] = False
                        self.sounds.play("big_boom")

        self.blasts = [b for b in self.blasts if not b.gone]

        if not any(self.cities):
            self.game_over = True
            self.sounds.play("game_over")
        elif self.to_spawn == 0 and not self.enemies and not self.blasts:
            # Wave survived: bonus for thrift and for what still stands.
            self.score += 5 * self.ammo + 100 * sum(self.cities)
            self.sounds.play("fanfare")
            self.next_wave()

    def draw(self) -> None:
        self.stars.draw(self.screen)

        # Trails first (behind the bright heads): one line each.
        for enemy in self.enemies:
            pygame.draw.line(self.screen, (120, 40, 40), enemy.origin, enemy.pos, 2)
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
        pygame.draw.polygon(
            self.screen,
            (150, 120, 40),
            [(BATTERY_X - 30, GROUND_Y), (BATTERY_X, GROUND_Y - 22), (BATTERY_X + 30, GROUND_Y)],
        )

        # The crosshair is wherever the mouse is.
        mx, my = pygame.mouse.get_pos()
        pygame.draw.line(self.screen, (255, 255, 255), (mx - 7, my), (mx + 7, my))
        pygame.draw.line(self.screen, (255, 255, 255), (mx, my - 7), (mx, my + 7))

        draw_text(self.screen, f"SCORE {self.score:06d}", (12, 10))
        draw_text(
            self.screen,
            f"WAVE {self.wave}",
            (WIDTH - 12, 10),
            anchor="topright",
            color=(120, 255, 160),
        )
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
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000, 0.05)
            self.time += dt

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

            self.stars.update(dt)
            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()
        return 0


def main() -> int:
    return Game().run()


if __name__ == "__main__":
    raise SystemExit(main())
