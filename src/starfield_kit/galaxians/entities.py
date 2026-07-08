"""The moving parts of Galaxians: the player, shots, particles, and the
alien convoy with its diving attacks.

Everything here is plain game logic — positions, timers, and states.
Drawing happens in main.py, which keeps "what things do" separate from
"how things look" (a habit worth copying into your own games).

Why classes, when the invaders sample gets by on plain lists of rects?
Because these things carry state that follows them around: the player owns
respawn and invulnerability timers, and every alien remembers its formation
slot, its dive clock, and where the player was when it pounced. A class
keeps that data next to the code that moves it, so update() reads as "one
thing, one frame" instead of a pile of parallel lists to keep in step.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from ..retro.particles import Particle
from . import settings as S


class Player:
    """The fighter at the bottom of the screen.

    Death doesn't delete it: explode() just flips ``alive`` off and starts
    a countdown, and respawn() brings it back, briefly untouchable. One
    long-lived object with timers beats creating and destroying ships.
    """

    def __init__(self, size: tuple[int, int]) -> None:
        self.w, self.h = size
        self.x = S.WINDOW_W / 2  # center of the ship
        self.y = S.WINDOW_H - S.PLAYER_Y_MARGIN
        self.alive = True
        self.respawn_timer = 0.0  # counts down while we wait to respawn
        self.safe_timer = 0.0  # blink-and-invulnerable time after respawn

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        # While dead, only the respawn countdown ticks; input is ignored.
        if not self.alive:
            self.respawn_timer -= dt
            return
        self.safe_timer = max(0.0, self.safe_timer - dt)
        # keys[...] are 0 or 1, so right minus left gives -1, 0, or +1.
        direction = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        self.x += direction * S.PLAYER_SPEED * dt
        # Clamp the center so the whole ship stays on screen.
        half = self.w / 2
        self.x = max(half, min(S.WINDOW_W - half, self.x))

    def explode(self) -> None:
        self.alive = False
        self.respawn_timer = S.RESPAWN_DELAY

    def respawn(self) -> None:
        self.alive = True
        self.x = S.WINDOW_W / 2
        self.safe_timer = S.INVULNERABLE_TIME

    # x and y stay floats (rects hold whole pixels and would round slow, smooth
    # motion away); a rect is built fresh only for collisions and drawing.
    @property
    def rect(self) -> pygame.Rect:
        r = pygame.Rect(0, 0, self.w, self.h)
        r.center = (int(self.x), int(self.y))
        return r


# @dataclass writes the boring __init__ for us — Shot(x, y, vx, vy) and done.
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
        # The 20 px margin lets a shot leave the screen fully before it is culled.
        return self.y < -20 or self.y > S.WINDOW_H + 20 or not -20 < self.x < S.WINDOW_W + 20

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 2, int(self.y) - 6, 4, 12)


# --- the alien convoy ---------------------------------------------------------

# Each alien is a tiny state machine; Convoy.update() branches on these.
# FORMATION: ride the swaying grid. DIVING: swoop at the player. RETURNING:
# glide back to your slot after the dive runs off the bottom of the screen.
FORMATION = "formation"
DIVING = "diving"
RETURNING = "returning"


@dataclass
class Alien:
    """One alien. row/col name its home slot; the dive_* fields track a dive."""

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

    # Divers are worth more — the arcade paid you extra for shooting the brave.
    @property
    def score(self) -> int:
        return self.points[1] if self.state == DIVING else self.points[0]

    def rect(self, size: tuple[int, int]) -> pygame.Rect:
        r = pygame.Rect(0, 0, *size)
        r.center = (int(self.x), int(self.y))
        return r.inflate(-size[0] // 4, -size[1] // 4)  # forgiving hitbox: near-misses miss


class Convoy:
    """The formation: it sways side to side as one body, and every so often
    sends an alien screaming down at the player."""

    def __init__(self, wave: int, rng: random.Random) -> None:
        self.wave = wave
        self.rng = rng
        self.time = 0.0
        self.aliens: list[Alien] = []
        # Build the grid from S.FORMATION_ROWS — edit that table to reshape the fleet.
        for row, (kind, count, points) in enumerate(S.FORMATION_ROWS):
            for col in range(count):
                self.aliens.append(Alien(kind, row, col, points))
        self.dive_timer = self.dive_interval() * 1.5  # a moment of calm at wave start
        self.just_launched = False  # True for the one frame a dive begins
        self.place_all()

    def dive_interval(self) -> float:
        """Later waves send divers more often."""
        # All three knobs live in settings.py — the whole difficulty ramp in one place.
        interval = S.DIVE_INTERVAL - (self.wave - 1) * S.DIVE_INTERVAL_STEP
        return max(S.DIVE_INTERVAL_MIN, interval)

    def sway(self) -> float:
        """Side-to-side drift: one smooth sine cycle every SWAY_PERIOD seconds."""
        return S.SWAY_AMPLITUDE * math.sin(math.tau * self.time / S.SWAY_PERIOD)

    def slot_pos(self, alien: Alien) -> tuple[float, float]:
        """Where this alien's formation slot currently is (it sways)."""
        count = S.FORMATION_ROWS[alien.row][1]
        # Each row centers itself: offset the column from the row's middle.
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
            # Re-arm with a little jitter so attacks never feel metronomic.
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
                # In formation, just ride the swaying slot.
                alien.x, alien.y = self.slot_pos(alien)

            elif alien.state == DIVING:
                alien.dive_t += dt
                # The dive: accelerate downward while the centerline chases
                # the player's position and the alien swoops around it.
                # TWEAK: the 0.5 makes dives gain speed as they fall — try 0 or 1.
                alien.y += S.DIVE_SPEED * (1 + alien.dive_t * 0.5) * dt
                # Easing: close a fraction of the gap each frame — quick start, soft settle.
                alien.dive_x += (alien.target_x - alien.dive_x) * min(1.0, 0.9 * dt)
                # A sine wave swings the alien around that centerline (3.0 = wiggle speed).
                alien.x = alien.dive_x + S.DIVE_SWERVE * math.sin(alien.dive_t * 3.0)
                # Divers shoot while they are above the player (never point-blank:
                # the S.WINDOW_H - 160 check holds fire near the bottom), and
                # chance * dt keeps "shots per second" true at any frame rate.
                alien.fire_cooldown -= dt
                if (
                    player_alive
                    and alien.fire_cooldown <= 0
                    and alien.y < S.WINDOW_H - 160
                    and self.rng.random() < S.DIVER_FIRE_CHANCE * dt
                ):
                    # TWEAK: 0.35 s minimum gap between one diver's shots.
                    alien.fire_cooldown = 0.35
                    aim = (player_x - alien.x) * S.ENEMY_SHOT_AIM
                    # Cap the sideways lean so every shot stays dodgeable.
                    vx = max(-150.0, min(150.0, aim))
                    shots.append(Shot(alien.x, alien.y + 10, vx, S.ENEMY_SHOT_SPEED))
                # Off the bottom: reappear above the screen and glide home.
                if alien.y > S.WINDOW_H + 40:
                    alien.state = RETURNING
                    alien.y = -30

            elif alien.state == RETURNING:
                # Fly straight home; snap in when one step would overshoot.
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
