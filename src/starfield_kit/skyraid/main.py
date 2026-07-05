"""SKY RAID — a vertical shooter where your throttle drives the sky.

Run it: ``uv run skyraid``

Controls: LEFT/RIGHT steer, UP/DOWN throttle, SPACE fires, P pauses,
ESC quits, SPACE restarts after game over.

This demo exists to show the starfield's **live ``velocity`` property**
doing real gameplay work — the two tricks no other sample uses:

*   **Throttle-linked scrolling.** Every frame the game writes
    ``stars.velocity = (0, throttle)``. Push the throttle and the three
    parallax layers pour past faster — and so do the raiders, because
    their dive speed is derived from the same number. Your speed is a
    weapon and a risk, which is the whole design in one line of code.
*   **Warp bursts.** Clearing a wave slams the velocity toward
    ~1500 px/s with the twinkle switched off (at that speed blinking
    reads as flicker), then eases it back down: the "warp speed" recipe
    from the docs, in context. Search for ``# STARFIELD`` to find both.
"""

from __future__ import annotations

import math
import random

import pygame

from ..retro.particles import explosion
from ..retro.pixelart import sprite
from ..retro.sfx import SoundBank
from ..retro.ui import blink_on, draw_text
from ..starfield import Starfield

WIDTH, HEIGHT = 480, 640

THROTTLE_MIN, THROTTLE_MAX = 120.0, 520.0  # the sky's scroll range, px/s
THROTTLE_RATE = 420.0  # how fast UP/DOWN move the throttle
PLAYER_SPEED = 300
SHOT_SPEED = 620
SHOT_MAX = 3
START_LIVES = 3

RAIDERS_PER_WAVE = 10  # plus 4 more each wave
RAIDER_FIRE_CHANCE = 0.5  # shots per second per raider
BOMB_SPEED = 240

WARP_TIME = 2.2  # seconds of hyperdrive between waves
WARP_SPEED = 1500.0

PLAYER_ART = [
    "....W....",
    "....W....",
    "...WWW...",
    "..WWRWW..",
    ".WWWRWWW.",
    "WW.WRW.WW",
    "W..WWW..W",
]
RAIDER_ART = [
    "o.......o",
    ".o..r..o.",
    ".ooorooo.",
    "oorrrrroo",
    ".o.rrr.o.",
    "...r.r...",
]
COLORS = {"W": (230, 230, 255), "R": (255, 60, 60), "o": (255, 150, 60), "r": (255, 60, 60)}


class Raider:
    """Dives from the top in a sine weave. Its fall speed rides on the
    throttle: fly faster and they come at you faster."""

    def __init__(self, rng: random.Random) -> None:
        self.cx = rng.uniform(40, WIDTH - 40)  # centerline of the weave
        self.y = rng.uniform(-320, -30)
        self.amp = rng.uniform(30, 90)
        self.rate = rng.uniform(1.6, 2.8)
        self.phase = rng.uniform(0, math.tau)
        self.time = 0.0
        self.x = self.cx

    def update(self, dt: float, throttle: float) -> None:
        self.time += dt
        self.y += (60 + throttle * 0.55) * dt  # most of the speed is YOUR speed
        self.x = self.cx + self.amp * math.sin(self.time * self.rate + self.phase)
        if self.y > HEIGHT + 30:  # slipped past: rejoin the attack from the top
            self.y = -30

    def rect(self, size: tuple[int, int]) -> pygame.Rect:
        r = pygame.Rect(0, 0, *size)
        r.center = (int(self.x), int(self.y))
        return r.inflate(-6, -6)


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SKY RAID — a starfield_kit demo")
        self.clock = pygame.time.Clock()
        self.sounds = SoundBank()
        self.rng = random.Random()
        self.player_img = sprite(PLAYER_ART, COLORS, scale=3)
        self.raider_img = sprite(RAIDER_ART, COLORS, scale=3)

        # STARFIELD: three vertical parallax layers. The velocity set here
        # is only the starting value — update() rewrites it every frame.
        self.stars = Starfield(
            (WIDTH, HEIGHT),
            velocity=(0, THROTTLE_MIN),
            layers=3,
            density=1.3,
            star_size=3,
            seed=1942,
        )

        self.time = 0.0
        self.paused = False
        self._pressed: set[int] = set()
        self.new_game()

    def new_game(self) -> None:
        self.player = self.player_img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 30))
        self.throttle = THROTTLE_MIN
        self.shots: list[pygame.Rect] = []
        self.bombs: list[list[float]] = []  # [x, y, vx] triples
        self.raiders: list[Raider] = []
        self.particles = []
        self.score = 0
        self.lives = START_LIVES
        self.wave = 0
        self.safe_timer = 2.0
        self.warp_timer = 0.0
        self.game_over = False
        self.next_wave()

    def next_wave(self) -> None:
        self.wave += 1
        count = RAIDERS_PER_WAVE + (self.wave - 1) * 4
        self.raiders = [Raider(self.rng) for _ in range(count)]
        self.bombs.clear()

    def update(self, dt: float) -> None:
        if pygame.K_p in self._pressed:
            self.paused = not self.paused
        if self.paused or self.game_over:
            return
        keys = pygame.key.get_pressed()

        # STARFIELD: the warp burst. Ease toward warp speed with twinkle
        # off, then hand control back to the throttle below.
        if self.warp_timer > 0:
            self.warp_timer -= dt
            vy = self.stars.velocity[1]
            if self.warp_timer > WARP_TIME * 0.35:
                vy = min(WARP_SPEED, vy + 2600 * dt)  # spool up
            else:
                vy = max(self.throttle, vy - 3400 * dt)  # spool down
            self.stars.velocity = (0, vy)
            if self.warp_timer <= 0:
                self.stars.twinkle_speed = 1.0
                self.next_wave()
            return  # the world holds its breath during warp

        # Throttle up/down, steer left/right.
        self.throttle += (keys[pygame.K_UP] - keys[pygame.K_DOWN]) * THROTTLE_RATE * dt
        self.throttle = max(THROTTLE_MIN, min(THROTTLE_MAX, self.throttle))
        self.player.x += int((keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * PLAYER_SPEED * dt)
        self.player.clamp_ip(self.screen.get_rect())

        # STARFIELD: the one line this whole demo is about.
        self.stars.velocity = (0, self.throttle)

        self.safe_timer = max(0.0, self.safe_timer - dt)
        clear_to_fire = not any(s.bottom > self.player.top - 60 for s in self.shots)
        if keys[pygame.K_SPACE] and len(self.shots) < SHOT_MAX and clear_to_fire:
            self.shots.append(pygame.Rect(self.player.centerx - 2, self.player.top - 12, 4, 14))
            self.sounds.play("laser")

        for shot in self.shots:
            shot.y -= int(SHOT_SPEED * dt)
        self.shots = [s for s in self.shots if s.bottom > 0]

        for raider in self.raiders:
            raider.update(dt, self.throttle)
            if (
                raider.y > 0
                and self.rng.random() < RAIDER_FIRE_CHANCE * dt
                and raider.y < self.player.top - 80
            ):
                aim = max(-90.0, min(90.0, (self.player.centerx - raider.x) * 0.5))
                self.bombs.append([raider.x, raider.y, aim])
                self.sounds.play("blip", volume=0.5)

        for bomb in self.bombs:
            bomb[0] += bomb[2] * dt
            bomb[1] += (BOMB_SPEED + self.throttle * 0.3) * dt
        self.bombs = [b for b in self.bombs if b[1] < HEIGHT + 20]

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if not p.gone]

        # Shots vs raiders.
        size = self.raider_img.get_size()
        for shot in list(self.shots):
            for raider in list(self.raiders):
                if raider.rect(size).colliderect(shot):
                    self.shots.remove(shot)
                    self.raiders.remove(raider)
                    self.score += 100
                    self.particles += explosion(raider.x, raider.y, (255, 150, 60))
                    self.sounds.play("boom")
                    break

        # Bombs and raider bodies vs the player.
        if self.safe_timer <= 0:
            hit = any(self.player.collidepoint(int(b[0]), int(b[1])) for b in self.bombs) or any(
                r.rect(size).colliderect(self.player) for r in self.raiders
            )
            if hit:
                self.lives -= 1
                self.particles += explosion(
                    self.player.centerx, self.player.centery, (230, 230, 255), big=True
                )
                self.sounds.play("big_boom")
                self.bombs.clear()
                self.safe_timer = 2.5
                if self.lives <= 0:
                    self.game_over = True
                    self.sounds.play("game_over")

        if not self.raiders and not self.game_over:
            # Wave cleared: hit the hyperdrive. STARFIELD: twinkle off — at
            # warp speed, blinking stars just look broken.
            self.warp_timer = WARP_TIME
            self.stars.twinkle_speed = 0
            self.score += 250
            self.sounds.play("fanfare")

    def draw(self) -> None:
        self.stars.draw(self.screen)

        for raider in self.raiders:
            self.screen.blit(
                self.raider_img, self.raider_img.get_rect(center=(int(raider.x), int(raider.y)))
            )
        if not self.game_over and (self.safe_timer <= 0 or blink_on(self.time, hz=6)):
            self.screen.blit(self.player_img, self.player)
        for shot in self.shots:
            self.screen.fill((255, 255, 255), shot)
        for bomb in self.bombs:
            self.screen.fill((255, 220, 80), (int(bomb[0]) - 2, int(bomb[1]) - 4, 4, 9))
        for p in self.particles:
            self.screen.fill(p.color, (int(p.x), int(p.y), 3, 3))

        draw_text(self.screen, f"SCORE {self.score:06d}", (10, 8))
        draw_text(
            self.screen,
            f"WAVE {self.wave}",
            (WIDTH - 10, 8),
            anchor="topright",
            color=(120, 255, 160),
        )
        draw_text(self.screen, f"LIVES {max(0, self.lives)}", (10, HEIGHT - 26))

        # The throttle gauge: a bar that fills as you speed up.
        gauge = pygame.Rect(WIDTH - 26, 60, 14, 200)
        pygame.draw.rect(self.screen, (110, 110, 140), gauge, 1)
        frac = (self.throttle - THROTTLE_MIN) / (THROTTLE_MAX - THROTTLE_MIN)
        fill = int((gauge.height - 4) * frac)
        self.screen.fill(
            (120, 255, 160), (gauge.x + 2, gauge.bottom - 2 - fill, gauge.width - 4, fill)
        )
        draw_text(
            self.screen,
            "SPD",
            (gauge.centerx, gauge.bottom + 8),
            scale=1,
            anchor="midtop",
            color=(110, 110, 140),
        )

        if self.warp_timer > 0 and blink_on(self.time, hz=3):
            draw_text(
                self.screen,
                "WARP!",
                (WIDTH // 2, 240),
                scale=5,
                anchor="center",
                color=(120, 255, 160),
            )
        if self.paused:
            draw_text(self.screen, "PAUSED", (WIDTH // 2, 300), scale=4, anchor="center")
        if self.game_over:
            draw_text(
                self.screen,
                "GAME OVER",
                (WIDTH // 2, 280),
                color=(255, 80, 80),
                scale=5,
                anchor="center",
            )
            if blink_on(self.time):
                draw_text(self.screen, "PRESS SPACE", (WIDTH // 2, 340), anchor="center")

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
                self.stars.twinkle_speed = 1.0
                self.new_game()

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
