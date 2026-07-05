"""A drop-in, arcade-style starfield background for pygame-ce.

This is the whole library — one file, no dependencies beyond pygame-ce.
Copy it into your own project and you have a starfield that works at any
window size, scrolls in any direction (or stays still), twinkles like the
1979 arcade games, and optionally fakes depth with parallax layers.

Minimal use — three lines on top of a normal pygame loop::

    field = Starfield(screen.get_size())        # 1. create
    ...
    field.update(dt)                            # 2. each frame: animate
    field.draw(screen)                          # 3. each frame: draw first

By default the stars drift slowly downward, the way Galaxian's did. Common
setups:

    Starfield(size, velocity=(0, 0))            # static, twinkling backdrop
    Starfield(size, velocity=(0, 60))           # flying up (stars fall down)
    Starfield(size, velocity=(-120, 0))         # flying right (stars stream left)
    Starfield(size, layers=3)                   # parallax depth (side-scrollers!)

The one rule to remember: **velocity is the direction the STARS move on
screen**, in pixels per second. If your ship flies right, the stars should
stream left, so use a negative x velocity. For games where the player
controls a camera (Defender-style), leave velocity at (0, 0) and call
``scroll()`` with how far the camera moved — see that method's docstring.

The default star colors are the actual 63 visible star colors produced by
the Galaxian arcade board's color DAC, so the field looks like the real
thing out of the box. Run this file directly to see it::

    python starfield.py
"""

from __future__ import annotations

import random
from collections.abc import Sequence

import pygame

__all__ = ["Starfield", "GALAXIAN_PALETTE", "WHITE_PALETTE"]

Color = tuple[int, int, int]

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------

# The Galaxian arcade board drove each color gun (red, green, blue) with two
# bits through a 100/150 ohm resistor DAC, giving four levels per gun:
_DAC_LEVELS = (0, 194, 214, 255)


def _galaxian_palette() -> tuple[Color, ...]:
    """The 63 visible star colors of the real Galaxian hardware.

    Each of the 64 possible 6-bit star colors uses two bits per gun (the
    hardware wires the 100-ohm bit as the high bit). Color 0 is black —
    invisible on a black sky — so we leave it out.
    """
    colors = []
    for i in range(64):
        r = _DAC_LEVELS[((i >> 4) & 1) << 1 | ((i >> 5) & 1)]
        g = _DAC_LEVELS[((i >> 2) & 1) << 1 | ((i >> 3) & 1)]
        b = _DAC_LEVELS[((i >> 0) & 1) << 1 | ((i >> 1) & 1)]
        if (r, g, b) != (0, 0, 0):
            colors.append((r, g, b))
    return tuple(colors)


GALAXIAN_PALETTE: tuple[Color, ...] = _galaxian_palette()

# A plain white-to-grey mix, for a subtler modern look.
WHITE_PALETTE: tuple[Color, ...] = (
    (255, 255, 255),
    (255, 255, 255),
    (214, 214, 214),
    (170, 170, 170),
)

_PALETTE_PRESETS: dict[str, tuple[Color, ...]] = {
    "galaxian": GALAXIAN_PALETTE,
    "white": WHITE_PALETTE,
}

# ---------------------------------------------------------------------------
# Tuning constants (module-level so curious readers can find them)
# ---------------------------------------------------------------------------

# density=1.0 means one star per this many pixels of screen area.
_PIXELS_PER_STAR = 2000

# Each star blinks on/off with its own period in this range (seconds) at
# twinkle_speed=1.0. Centered near the ~0.53 s blink of the arcade original.
_TWINKLE_PERIOD_RANGE = (0.35, 0.9)

# Fraction of each blink period that the star is visible.
_TWINKLE_DUTY = 0.55

# With layers > 1, layer depth factors run from _FAR to 1.0. A factor scales
# a layer's scroll speed; brightness and star size shrink with it too.
_FAR_FACTOR = 0.3


class _Layer:
    """One depth plane of stars. With layers=1 there is a single plane
    with factor 1.0 (full speed, full brightness)."""

    __slots__ = ("factor", "stars", "offset_x", "offset_y", "size", "alpha", "surfaces")

    def __init__(self, factor: float) -> None:
        self.factor = factor
        # Each star is (nx, ny, color, period, phase): position as a 0..1
        # fraction of the field (so resizing keeps the layout), its color,
        # and its personal twinkle period/phase in seconds.
        self.stars: list[tuple[float, float, Color, float, float]] = []
        self.offset_x = 0.0  # how far this layer has scrolled, in pixels
        self.offset_y = 0.0
        self.size = 1  # star square size in pixels, set by _rebuild_surfaces
        self.alpha = 255  # star opacity (far layers are fainter)
        self.surfaces: dict[Color, pygame.Surface] = {}  # color -> prerendered star


class Starfield:
    """An animated field of stars that you draw behind everything else.

    Args:
        size: (width, height) of the area to fill, usually your window size,
            e.g. ``Starfield(screen.get_size())``.
        velocity: (x, y) speed of the stars in pixels/second. This is the
            direction the stars move: (0, 30) drifts them downward (the
            classic Galaxian look), (-120, 0) streams them left as if you
            are flying right, (0, 0) holds them still. Change it at any
            time: ``field.velocity = (0, 80)``.
        density: how crowded the sky is. 1.0 is a comfortable arcade look
            (about one star per 2000 pixels of area); 2.0 doubles the
            stars, 0.5 halves them.
        count: exact number of stars, overriding ``density``.
        twinkle_speed: how fast stars blink. 1.0 matches the arcade feel,
            2.0 is frantic, 0.3 is a slow calm shimmer, 0 disables
            twinkling entirely (all stars stay lit).
        layers: number of parallax depth planes. 1 (default) is a flat
            classic field. 3 gives a convincing sense of depth for
            side-scrollers: far stars are smaller, fainter, and scroll
            slower than near ones.
        palette: star colors — the string "galaxian" (default, the real
            arcade colors), "white", or your own list of (r, g, b) tuples,
            e.g. ``palette=[(255, 200, 100), (150, 200, 255)]``.
        star_size: pixel size of the biggest stars. Leave as None to pick
            a sensible size for your resolution automatically.
        background: color the field paints behind the stars each frame.
            Defaults to black. Pass ``None`` to draw only the stars, over
            whatever you have already drawn (e.g. a gradient sky).
        seed: pass any integer to get the identical star layout every run;
            leave as None for a fresh sky each time.
    """

    def __init__(
        self,
        size: tuple[int, int],
        *,
        velocity: tuple[float, float] = (0.0, 30.0),
        density: float = 1.0,
        count: int | None = None,
        twinkle_speed: float = 1.0,
        layers: int = 1,
        palette: str | Sequence[Color] = "galaxian",
        star_size: int | None = None,
        background: Color | None = (0, 0, 0),
        seed: int | None = None,
    ) -> None:
        if layers < 1:
            raise ValueError("layers must be at least 1")
        self._width = int(size[0])
        self._height = int(size[1])
        self.velocity = velocity
        self.twinkle_speed = float(twinkle_speed)
        self.background = background
        self._density = float(density)
        self._explicit_count = count
        self._star_size = star_size
        self._rng = random.Random(seed)
        self._twinkle_clock = 0.0

        if isinstance(palette, str):
            try:
                self._palette: tuple[Color, ...] = _PALETTE_PRESETS[palette]
            except KeyError:
                options = ", ".join(sorted(_PALETTE_PRESETS))
                raise ValueError(f"unknown palette {palette!r}; choose {options}") from None
        else:
            self._palette = tuple((int(r), int(g), int(b)) for r, g, b in palette)
            if not self._palette:
                raise ValueError("palette must contain at least one color")

        # Depth factors from far (slow, faint, small) to near (full speed).
        if layers == 1:
            factors = [1.0]
        else:
            step = (1.0 - _FAR_FACTOR) / (layers - 1)
            factors = [_FAR_FACTOR + step * i for i in range(layers)]
        self._layers = [_Layer(f) for f in factors]

        self._populate(self._target_count())
        self._rebuild_surfaces()

    # -- properties ---------------------------------------------------------

    @property
    def size(self) -> tuple[int, int]:
        """The (width, height) of the field in pixels."""
        return (self._width, self._height)

    @property
    def star_count(self) -> int:
        """How many stars the field currently holds."""
        return sum(len(layer.stars) for layer in self._layers)

    @property
    def velocity(self) -> tuple[float, float]:
        """Star movement in pixels/second; assign a new (x, y) any time."""
        return self._velocity

    @velocity.setter
    def velocity(self, value: tuple[float, float]) -> None:
        vx, vy = value
        self._velocity = (float(vx), float(vy))

    # -- the three methods you call from a game loop -------------------------

    def update(self, dt: float) -> None:
        """Advance the animation by ``dt`` seconds (the time since the last
        frame). Call once per frame, before ``draw()``. Movement is
        frame-rate independent: pass ``dt = clock.tick(60) / 1000``.
        """
        self._twinkle_clock += dt * self.twinkle_speed
        vx, vy = self._velocity
        if vx or vy:
            for layer in self._layers:
                layer.offset_x = (layer.offset_x + vx * dt * layer.factor) % self._width
                layer.offset_y = (layer.offset_y + vy * dt * layer.factor) % self._height

    def scroll(self, dx: float, dy: float) -> None:
        """Shift the stars by (dx, dy) pixels right now.

        This is for games where the *camera* moves through a world
        (Defender, Mario, any side-scroller). Each frame, after you move
        the camera, push the stars the opposite way::

            camera_x += player_vx * dt        # camera follows the player
            field.scroll(-player_vx * dt, 0)  # so the stars stream past

        Parallax layers automatically move at their own depth-scaled rates,
        which is what sells the effect. You can combine ``scroll()`` with a
        nonzero ``velocity`` — they simply add.
        """
        for layer in self._layers:
            layer.offset_x = (layer.offset_x + dx * layer.factor) % self._width
            layer.offset_y = (layer.offset_y + dy * layer.factor) % self._height

    def draw(self, target: pygame.Surface, dest: tuple[int, int] = (0, 0)) -> None:
        """Draw the field onto ``target`` (normally your screen), with the
        field's top-left corner at ``dest``. Call this before drawing
        ships, aliens, and score so the stars sit behind everything.
        """
        left, top = dest
        if self.background is not None:
            target.fill(self.background, (left, top, self._width, self._height))
        w, h = self._width, self._height
        t = self._twinkle_clock
        twinkling = self.twinkle_speed > 0
        blits = []
        for layer in self._layers:
            ox, oy = layer.offset_x, layer.offset_y
            surfaces = layer.surfaces
            for nx, ny, color, period, phase in layer.stars:
                if twinkling and (t + phase) % period > period * _TWINKLE_DUTY:
                    continue  # this star is in the "off" part of its blink
                x = (nx * w + ox) % w
                y = (ny * h + oy) % h
                blits.append((surfaces[color], (int(x) + left, int(y) + top)))
        # fblits is pygame-ce's fast path for drawing many small surfaces.
        target.fblits(blits)

    # -- occasional operations ----------------------------------------------

    def resize(self, size: tuple[int, int]) -> None:
        """Fit the field to a new (width, height) — call from your window
        resize handler. The star layout is preserved (positions scale with
        the field) and, when using ``density``, stars are added or removed
        to keep the same crowdedness.
        """
        self._width = int(size[0])
        self._height = int(size[1])
        self._populate(self._target_count())
        self._rebuild_surfaces()

    # -- internals -----------------------------------------------------------

    def _target_count(self) -> int:
        if self._explicit_count is not None:
            return max(0, int(self._explicit_count))
        area = self._width * self._height
        return max(1, round(self._density * area / _PIXELS_PER_STAR))

    def _make_star(self) -> tuple[float, float, Color, float, float]:
        rng = self._rng
        lo, hi = _TWINKLE_PERIOD_RANGE
        return (
            rng.random(),  # x as a fraction of the width
            rng.random(),  # y as a fraction of the height
            rng.choice(self._palette),
            rng.uniform(lo, hi),  # personal blink period (s)
            rng.uniform(0.0, hi),  # personal blink phase, so stars desynchronize
        )

    def _populate(self, total: int) -> None:
        """Add or remove stars so the layers hold ``total`` between them,
        distributed evenly, without disturbing existing stars."""
        n = len(self._layers)
        for i, layer in enumerate(self._layers):
            want = total // n + (1 if i < total % n else 0)
            while len(layer.stars) < want:
                layer.stars.append(self._make_star())
            del layer.stars[want:]

    def _rebuild_surfaces(self) -> None:
        """Prerender one tiny square per star color per layer. Far layers
        get smaller, fainter squares; blitting prerendered surfaces via
        fblits() is much faster than drawing each star individually."""
        base = self._star_size
        if base is None:
            # Pick a size that reads well at this resolution: 1 px up to
            # ~600 px tall windows, 2 px up to ~1200, and so on.
            base = max(1, int(self._height / 600) + 1) if self._height >= 600 else 1
        for layer in self._layers:
            layer.size = max(1, round(base * layer.factor))
            layer.alpha = round(255 * (0.45 + 0.55 * layer.factor))
            layer.surfaces = {}
            for color in self._palette:
                surf = pygame.Surface((layer.size, layer.size), pygame.SRCALPHA)
                surf.fill((*color, layer.alpha))
                layer.surfaces[color] = surf


def _demo() -> None:  # pragma: no cover - manual demo, not part of the library
    """A tiny self-test so `python starfield.py` shows something pretty."""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("starfield.py — arrows change velocity, Esc quits")
    clock = pygame.time.Clock()
    field = Starfield(screen.get_size(), layers=3)
    while True:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                pygame.quit()
                return
        vx, vy = field.velocity
        keys = pygame.key.get_pressed()
        push = 200 * dt
        vx += push * (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT])
        vy += push * (keys[pygame.K_DOWN] - keys[pygame.K_UP])
        field.velocity = (vx, vy)
        field.update(dt)
        field.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    _demo()
