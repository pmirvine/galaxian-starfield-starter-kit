"""The moving parts of Galaxians: the player, shots, particles, and the
alien convoy with its diving attacks.

Everything here is plain game logic — positions, timers, and states.
Drawing happens in main.py, which keeps "what things do" separate from
"how things look" (a habit worth copying into your own games).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from ..retro.particles import Particle
from . import settings as S


class Player:
    """The fighter at the bottom of the screen."""

    def __init__(self, size: tuple[int, int]) -> None:
        self.w, self.h = size
        self.x = S.WINDOW_W / 2  # center of the ship
        self.y = S.WINDOW_H - S.PLAYER_Y_MARGIN
        self.alive = True
        self.respawn_timer = 0.0  # counts down while we wait to respawn
        self.safe_timer = 0.0  # blink-and-invulnerable time after respawn

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        if not self.alive:
            self.respawn_timer -= dt
            return
        self.safe_timer = max(0.0, self.safe_timer - dt)
        direction = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        self.x += direction * S.PLAYER_SPEED * dt
        half = self.w / 2
        self.x = max(half, min(S.WINDOW_W - half, self.x))

    def explode(self) -> None:
        self.alive = False
        self.respawn_timer = S.RESPAWN_DELAY

    def respawn(self) -> None:
        self.alive = True
        self.x = S.WINDOW_W / 2
        self.safe_timer = S.INVULNERABLE_TIME

    @property
    def rect(self) -> pygame.Rect:
        r = pygame.Rect(0, 0, self.w, self.h)
        r.center = (int(self.x), int(self.y))
        return r


@dataclass
class Shot:
    """A bullet. The player's fly up (negative vy); the aliens' fly down,
    possibly angled toward where the player was when they fired."""

    x: float
    y: float
    vx: float
    vy: float

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def gone(self) -> bool:
        return self.y < -20 or self.y > S.WINDOW_H + 20 or not -20 < self.x < S.WINDOW_W + 20

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 2, int(self.y) - 6, 4, 12)


# --- the alien convoy ---------------------------------------------------------

FORMATION = "formation"
DIVING = "diving"
RETURNING = "returning"


@dataclass
class Alien:
    kind: str  # "drone", "escort", or "flagship" — picks sprite and score
    row: int
    col: int
    points: tuple[int, int]  # (in formation, while diving)
    x: float = 0.0
    y: float = 0.0
    state: str = FORMATION
    dive_t: float = 0.0  # seconds since this dive began
    dive_x: float = 0.0  # the dive's drifting centerline
    target_x: float = 0.0  # where the player was when the dive started
    fire_cooldown: float = 0.0

    @property
    def score(self) -> int:
        return self.points[1] if self.state == DIVING else self.points[0]

    def rect(self, size: tuple[int, int]) -> pygame.Rect:
        r = pygame.Rect(0, 0, *size)
        r.center = (int(self.x), int(self.y))
        return r.inflate(-size[0] // 4, -size[1] // 4)  # forgiving hitbox


class Convoy:
    """The formation: it sways side to side as one body, and every so often
    sends an alien screaming down at the player."""

    def __init__(self, wave: int, rng: random.Random) -> None:
        self.wave = wave
        self.rng = rng
        self.time = 0.0
        self.aliens: list[Alien] = []
        for row, (kind, count, points) in enumerate(S.FORMATION_ROWS):
            for col in range(count):
                self.aliens.append(Alien(kind, row, col, points))
        self.dive_timer = self.dive_interval() * 1.5  # a moment of calm at wave start
        self.just_launched = False  # True for the one frame a dive begins
        self.place_all()

    def dive_interval(self) -> float:
        """Later waves send divers more often."""
        interval = S.DIVE_INTERVAL - (self.wave - 1) * S.DIVE_INTERVAL_STEP
        return max(S.DIVE_INTERVAL_MIN, interval)

    def sway(self) -> float:
        return S.SWAY_AMPLITUDE * math.sin(math.tau * self.time / S.SWAY_PERIOD)

    def slot_pos(self, alien: Alien) -> tuple[float, float]:
        """Where this alien's formation slot currently is (it sways)."""
        count = S.FORMATION_ROWS[alien.row][1]
        x = S.WINDOW_W / 2 + (alien.col - (count - 1) / 2) * S.FORMATION_H_SPACING
        y = S.FORMATION_TOP + alien.row * S.FORMATION_V_SPACING
        return x + self.sway(), y

    def place_all(self) -> None:
        for alien in self.aliens:
            alien.x, alien.y = self.slot_pos(alien)

    def update(self, dt: float, player_x: float, player_alive: bool) -> list[Shot]:
        """Advance the whole convoy. Returns any shots fired by divers."""
        self.time += dt
        self.just_launched = False
        shots: list[Shot] = []

        # Maybe launch a new dive.
        self.dive_timer -= dt
        if self.dive_timer <= 0 and player_alive:
            self.dive_timer = self.dive_interval() * self.rng.uniform(0.75, 1.25)
            candidates = [a for a in self.aliens if a.state == FORMATION]
            if candidates:
                diver = self.rng.choice(candidates)
                diver.state = DIVING
                diver.dive_t = 0.0
                diver.dive_x = diver.x
                diver.target_x = player_x
                self.just_launched = True

        for alien in self.aliens:
            if alien.state == FORMATION:
                alien.x, alien.y = self.slot_pos(alien)

            elif alien.state == DIVING:
                alien.dive_t += dt
                # The dive: accelerate downward while the centerline chases
                # the player's position and the alien swoops around it.
                alien.y += S.DIVE_SPEED * (1 + alien.dive_t * 0.5) * dt
                alien.dive_x += (alien.target_x - alien.dive_x) * min(1.0, 0.9 * dt)
                alien.x = alien.dive_x + S.DIVE_SWERVE * math.sin(alien.dive_t * 3.0)
                # Divers shoot while they are above the player.
                alien.fire_cooldown -= dt
                if (
                    player_alive
                    and alien.fire_cooldown <= 0
                    and alien.y < S.WINDOW_H - 160
                    and self.rng.random() < S.DIVER_FIRE_CHANCE * dt
                ):
                    alien.fire_cooldown = 0.35
                    aim = (player_x - alien.x) * S.ENEMY_SHOT_AIM
                    vx = max(-150.0, min(150.0, aim))
                    shots.append(Shot(alien.x, alien.y + 10, vx, S.ENEMY_SHOT_SPEED))
                # Off the bottom: reappear above the screen and glide home.
                if alien.y > S.WINDOW_H + 40:
                    alien.state = RETURNING
                    alien.y = -30

            elif alien.state == RETURNING:
                home_x, home_y = self.slot_pos(alien)
                dx, dy = home_x - alien.x, home_y - alien.y
                dist = math.hypot(dx, dy)
                step = S.RETURN_SPEED * dt
                if dist <= step:
                    alien.x, alien.y = home_x, home_y
                    alien.state = FORMATION
                else:
                    alien.x += dx / dist * step
                    alien.y += dy / dist * step

        return shots

    @property
    def defeated(self) -> bool:
        return not self.aliens


@dataclass
class World:
    """Everything alive in one wave, bundled for easy resetting."""

    player: Player
    convoy: Convoy
    player_shots: list[Shot] = field(default_factory=list)
    enemy_shots: list[Shot] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
