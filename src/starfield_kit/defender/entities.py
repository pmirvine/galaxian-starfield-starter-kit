"""The moving parts of Defender: an inertial ship in a wrapping world,
landers that stalk you, and baiters that punish you for taking too long.

The world is a loop WORLD_W pixels around. The one tricky idea in this
file is ``wrap_delta(a, b)``: the shortest signed distance from b to a
around that loop. Every "which way is the player?" question uses it, so
enemies correctly chase you across the seam of the world.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from ..retro.particles import Particle
from . import settings as S


def wrap_delta(a: float, b: float) -> float:
    """Shortest signed distance from b to a in the wrapping world:
    positive means a is to the right of b (going the short way)."""
    d = (a - b) % S.WORLD_W
    if d > S.WORLD_W / 2:
        d -= S.WORLD_W
    return d


def make_terrain(rng: random.Random) -> list[int]:
    """Jagged mountain heights, one per TERRAIN_STEP of world, as a random
    walk that is nudged back to its start so the seam doesn't show."""
    n = S.WORLD_W // S.TERRAIN_STEP
    heights = [0] * n
    h = rng.randint(S.TERRAIN_MIN, S.TERRAIN_MAX)
    start = h
    for i in range(n):
        h += rng.randint(-26, 26)
        h = max(S.TERRAIN_MIN, min(S.TERRAIN_MAX, h))
        # In the last stretch, blend toward the starting height to close the loop.
        remaining = n - i
        if remaining < 12:
            h += (start - h) // remaining
        heights[i] = h
    return heights


class Player:
    """The ship. Left/right THRUST (with inertia and drag), up/down direct,
    facing whichever way you last thrusted — pure 1981."""

    def __init__(self, size: tuple[int, int]) -> None:
        self.w, self.h = size
        self.x = 0.0  # world coordinate of the ship's center
        self.y = S.WINDOW_H * 0.45
        self.vx = 0.0
        self.facing = 1  # 1 = right, -1 = left
        self.thrusting = False
        self.fire_cooldown = 0.0
        self.alive = True
        self.respawn_timer = 0.0
        self.safe_timer = 0.0

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        if not self.alive:
            self.respawn_timer -= dt
            return
        self.safe_timer = max(0.0, self.safe_timer - dt)
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        direction = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        self.thrusting = direction != 0
        if direction:
            self.facing = direction  # thrusting also turns the ship
            self.vx += direction * S.THRUST * dt
        else:
            self.vx -= self.vx * min(1.0, S.DRAG * dt)  # coast down gently
        self.vx = max(-S.MAX_SPEED, min(S.MAX_SPEED, self.vx))
        self.x = (self.x + self.vx * dt) % S.WORLD_W

        dy = keys[pygame.K_DOWN] - keys[pygame.K_UP]
        self.y += dy * S.VERTICAL_SPEED * dt
        self.y = max(40.0, min(S.WINDOW_H - 40.0, self.y))

    def explode(self) -> None:
        self.alive = False
        self.thrusting = False
        self.respawn_timer = S.RESPAWN_DELAY

    def respawn(self) -> None:
        self.alive = True
        self.vx = 0.0
        self.y = S.WINDOW_H * 0.45
        self.safe_timer = S.INVULNERABLE_TIME

    def rect_at(self, sx: float) -> pygame.Rect:
        """Hitbox at screen x (the caller converts world->screen)."""
        r = pygame.Rect(0, 0, self.w, self.h)
        r.center = (int(sx), int(self.y))
        return r.inflate(-self.w // 4, -self.h // 4)


@dataclass
class Laser:
    """A fast horizontal bolt. Lives ~0.8 screens of travel."""

    x: float  # world x of the bolt's leading tip
    y: float
    direction: int  # 1 right, -1 left
    traveled: float = 0.0

    def update(self, dt: float) -> None:
        step = S.LASER_SPEED * dt
        self.x = (self.x + self.direction * step) % S.WORLD_W
        self.traveled += step

    @property
    def gone(self) -> bool:
        return self.traveled > S.WINDOW_W * 0.8

    def hits(self, x: float, y: float, radius: float) -> bool:
        """Does the bolt (tip back to its tail) overlap this world point?"""
        dx = wrap_delta(x, self.x)  # positive: target is right of the tip
        behind = -self.direction * dx  # distance from tip back along the bolt
        return abs(y - self.y) < radius and -radius < behind < S.LASER_LENGTH + radius


@dataclass
class EnemyShot:
    x: float
    y: float
    vx: float
    vy: float
    age: float = 0.0

    def update(self, dt: float) -> None:
        self.x = (self.x + self.vx * dt) % S.WORLD_W
        self.y += self.vy * dt
        self.age += dt

    @property
    def gone(self) -> bool:
        return self.age > 4.0 or not -20 < self.y < S.WINDOW_H + 20


class Lander:
    """Drifts toward the player, bobbing, taking potshots."""

    def __init__(self, rng: random.Random) -> None:
        self.x = rng.uniform(0, S.WORLD_W)
        self.base_y = rng.uniform(70, S.WINDOW_H - 160)
        self.y = self.base_y
        self.phase = rng.uniform(0, math.tau)
        self.time = 0.0
        self.speed = S.LANDER_SPEED * rng.uniform(0.8, 1.3)

    def update(self, dt: float, player_x: float, rng: random.Random) -> EnemyShot | None:
        self.time += dt
        toward = wrap_delta(player_x, self.x)
        self.x = (self.x + math.copysign(self.speed, toward) * dt) % S.WORLD_W
        self.y = self.base_y + S.LANDER_BOB * math.sin(self.time * 1.4 + self.phase)
        # Take a potshot now and then, but only from within about a screen.
        if abs(toward) < S.WINDOW_W and rng.random() < S.LANDER_FIRE_CHANCE * dt:
            return self.shot_at(player_x, rng)
        return None

    def shot_at(self, player_x: float, rng: random.Random) -> EnemyShot:
        """A shot loosely aimed at the player (enemy aim is charitably bad)."""
        angle = math.atan2(
            rng.uniform(-40, 40) - (self.y - S.WINDOW_H * 0.5),
            wrap_delta(player_x, self.x),
        )
        return EnemyShot(
            self.x,
            self.y,
            math.cos(angle) * S.ENEMY_SHOT_SPEED,
            math.sin(angle) * S.ENEMY_SHOT_SPEED,
        )


class Baiter:
    """The fast saucer that spawns when a wave drags on. It hunts you."""

    def __init__(self, player_x: float, rng: random.Random) -> None:
        # Appear just off-screen on a random side of the player.
        self.x = (player_x + rng.choice([-1, 1]) * S.WINDOW_W * 0.7) % S.WORLD_W
        self.y = rng.uniform(60, S.WINDOW_H - 120)

    def update(
        self, dt: float, player_x: float, player_y: float, rng: random.Random
    ) -> EnemyShot | None:
        toward = wrap_delta(player_x, self.x)
        chase = max(-S.BAITER_SPEED, min(S.BAITER_SPEED, toward * 1.5))
        self.x = (self.x + chase * dt) % S.WORLD_W
        self.y += max(-140.0, min(140.0, (player_y - self.y) * 1.2)) * dt
        if abs(toward) < S.WINDOW_W and rng.random() < S.BAITER_FIRE_CHANCE * dt:
            dx, dy = wrap_delta(player_x, self.x), player_y - self.y
            dist = math.hypot(dx, dy) or 1.0
            speed = S.ENEMY_SHOT_SPEED * 1.3
            return EnemyShot(self.x, self.y, dx / dist * speed, dy / dist * speed)
        return None


@dataclass
class World:
    """Everything alive in one wave."""

    player: Player
    landers: list[Lander]
    terrain: list[int]
    baiters: list[Baiter] = field(default_factory=list)
    lasers: list[Laser] = field(default_factory=list)
    enemy_shots: list[EnemyShot] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
    wave_time: float = 0.0
    next_baiter: float = S.BAITER_AFTER
