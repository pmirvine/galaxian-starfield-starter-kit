"""Explosion particles, shared by the sample games.

An "explosion" is just 14-26 colored squares flung outward at random
angles that fade after a fraction of a second. It is astonishing how much
game-feel this cheap trick buys.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

Color = tuple[int, int, int]


@dataclass
class Particle:
    """One fleck of an explosion."""

    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: Color
    age: float = 0.0

    def update(self, dt: float) -> None:
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 60 * dt  # a touch of gravity looks nicer than straight lines

    @property
    def gone(self) -> bool:
        return self.age >= self.life


def explosion(x: float, y: float, color: Color, big: bool = False) -> list[Particle]:
    """A burst of particles for a destroyed ship or alien."""
    rng = random.Random()
    count = 26 if big else 14
    out = []
    for _ in range(count):
        angle = rng.uniform(0, math.tau)
        speed = rng.uniform(40, 260 if big else 180)
        out.append(
            Particle(
                x,
                y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life=rng.uniform(0.25, 0.7 if big else 0.5),
                color=rng.choice([color, (255, 255, 255), (255, 180, 60)]),
            )
        )
    return out
