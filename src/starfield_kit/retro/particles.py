"""Explosion particles, shared by the sample games.

An "explosion" is just 14-26 colored squares flung outward at random
angles that fade after a fraction of a second. It is astonishing how much
game-feel this cheap trick buys.

Every game uses the same three-step lifecycle::

    particles += explosion(x, y, color)               # emit on a hit
    for p in particles: p.update(dt)                  # move + age, each frame
    particles = [p for p in particles if not p.gone]  # drop the dead ones

Drawing stays in the game: each particle is one small filled square,
``screen.fill(p.color, (int(p.x), int(p.y), 3, 3))``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

Color = tuple[int, int, int]


@dataclass
class Particle:
    """One fleck of an explosion."""

    x: float  # position in pixels
    y: float
    vx: float  # velocity in px/s
    vy: float
    life: float  # lifespan in seconds
    color: Color
    age: float = 0.0  # seconds lived so far; update() advances it

    def update(self, dt: float) -> None:
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 60 * dt  # a touch of gravity looks nicer than straight lines

    @property
    def gone(self) -> bool:
        """True once age passes life — the game's cue to drop this particle."""
        return self.age >= self.life


def explosion(x: float, y: float, color: Color, big: bool = False) -> list[Particle]:
    """A burst of particles for a destroyed ship or alien."""
    rng = random.Random()  # unseeded on purpose: every explosion gets a fresh shape
    count = 26 if big else 14  # more flecks reads as a bigger bang
    out = []
    for _ in range(count):
        angle = rng.uniform(0, math.tau)  # any direction — tau is a full circle
        speed = rng.uniform(40, 260 if big else 180)  # px/s; sets how wide the burst spreads
        out.append(
            Particle(
                x,
                y,
                math.cos(angle) * speed,  # cos/sin split the speed into x and y parts
                math.sin(angle) * speed,
                life=rng.uniform(0.25, 0.7 if big else 0.5),  # seconds before it fades
                # TWEAK: white/amber sparks are mixed into the caller's color — but this
                # helper is shared, so recoloring them changes every game's booms at once.
                color=rng.choice([color, (255, 255, 255), (255, 180, 60)]),
            )
        )
    return out
