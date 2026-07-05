# Starfield — the full reference

Everything `Starfield` can do, with recipes. The class lives in one
self-contained file, [`src/starfield_kit/starfield.py`](../src/starfield_kit/starfield.py) —
copy it into any pygame-ce project and `from starfield import Starfield`.

The fastest way to *see* every option below: `uv run starfield-demo`.

## The three lines

```python
field = Starfield(screen.get_size())    # once, after pygame.init()

# then, every frame:
field.update(dt)                        # dt = seconds since last frame
field.draw(screen)                      # before drawing anything else
```

`update()` animates (scroll + twinkle) in a frame-rate-independent way;
`draw()` paints the background color and the stars. That's the entire
integration.

## Constructor parameters

```python
Starfield(
    size,                    # required: (width, height) in pixels
    velocity=(0.0, 30.0),    # px/sec the STARS move; (0, 0) = static
    density=1.0,             # 1.0 ≈ one star per 2000 px² of screen
    count=None,              # exact star count (overrides density)
    twinkle_speed=1.0,       # blink rate; 0 disables twinkling
    layers=1,                # parallax depth planes (1 = classic flat)
    palette="galaxian",      # "galaxian", "white", or [(r,g,b), ...]
    star_size=None,          # px size of the biggest stars (None = auto)
    background=(0, 0, 0),    # fill color; None = draw stars only
    seed=None,               # int for a reproducible sky
)
```

### `size`

The area the field fills, usually your window: `Starfield(screen.get_size())`.
Any size works — the field wraps its stars around these bounds as they
scroll. If the window changes, call `resize()` (see below).

### `velocity` — direction and speed in one pair

Pixels per second that the **stars** move on screen. The mental model:
stars move opposite to your imaginary flight.

| you want                          | velocity        |
| --------------------------------- | --------------- |
| a still, twinkling backdrop       | `(0, 0)`        |
| Galaxian's gentle downward drift  | `(0, 30)`       |
| flying up fast                    | `(0, 400)`      |
| flying right (side-scroller)      | `(-150, 0)`     |
| drifting diagonally               | `(-40, 25)`     |

It's a live property — assign it whenever you like:

```python
field.velocity = (0, 0)           # slam the brakes
field.velocity = (-player_vx, 0)  # mirror the player's speed (see recipes)
```

### `density` and `count`

`density=1.0` gives about one star per 2000 pixels of area (a 640×480
window → ~150 stars) — a comfortable arcade look at any resolution.
`2.0` doubles it, `0.5` halves it. If you'd rather say exactly how many:
`count=200` wins over density. Read back the result with
`field.star_count`.

### `twinkle_speed`

Stars blink on and off, each with its own rhythm, like the arcade
hardware's gating did. `1.0` matches that feel; `0.3` is a slow calm
shimmer; `3.0` is frantic; `0` turns twinkling off (all stars always lit).
Also a live attribute: `field.twinkle_speed = 0.5`.

### `layers` — parallax

With `layers=1` (default) you get the classic flat field. With more, stars
are split across depth planes; far planes scroll slower and their stars
are smaller and fainter. `3` is the sweet spot for side-scrollers. There
is no visual cost to leaving it at 1 for static or slow fields.

### `palette`

* `"galaxian"` (default) — the 63 visible star colors the 1979 Galaxian
  board's DAC could produce. Subtle rainbow; looks *right*.
* `"white"` — white/grey mix, subtler and more modern.
* Your own: any list of `(r, g, b)` tuples, e.g.
  `palette=[(255, 190, 120), (255, 120, 60)]` for embers, or a single
  color like `[(120, 180, 255)]` for an ice world.

### `star_size` — match your game's pixel scale

Pixel size of the biggest (nearest) stars. Leave it `None` and the field
picks sensibly for the resolution (1 px below 600-tall windows, scaling up
from there).

For blocky retro games, set it explicitly to the scale your art is drawn
at, so one star = one "virtual pixel" of your world. All three sample
games draw their sprites at 3× and pass `star_size=3` for exactly this
reason — it is also about how chunky the 1979 original's stars looked at
a 3× window scale:

```python
PIXEL_SCALE = 3                       # your sprites are 3x3 blocks per pixel
field = Starfield(size, star_size=PIXEL_SCALE)
```

With parallax (`layers=3`), `star_size` sets the *nearest* plane; farther
planes shrink automatically (3 → 2 → 1 px), which deepens the effect.

It is a live property too — `field.star_size = 4` restyles the field
mid-game, and `field.star_size = None` returns it to automatic.

### `background`

The color `draw()` fills behind the stars — default black, like space.
Two useful alternatives: a very dark blue `(8, 8, 24)` for a softer mood,
or `None`, which fills nothing so you can draw the stars **over** your own
sky (a gradient, a nebula image, ...). With `None`, remember you are
responsible for clearing the screen each frame.

### `seed`

Any integer makes the sky identical every run (useful for tests, or when
you just like a particular sky). `None` = random each run.

## Methods and properties

| member                    | what it does |
| ------------------------- | ------------ |
| `update(dt)`              | Advance animation by `dt` seconds. Call once per frame. |
| `draw(surface, dest=(0, 0))` | Paint background + stars onto `surface`, top-left at `dest`. |
| `scroll(dx, dy)`          | Shift stars by pixels *right now* — for camera-driven games (see recipe). Adds on top of `velocity`. |
| `resize(size)`            | Refit to a new window size, preserving the layout and density. |
| `velocity`                | Live `(vx, vy)` property. |
| `twinkle_speed`           | Live attribute; `0` stops twinkling. |
| `star_size`               | Live property; a pixel size, or `None` for automatic. |
| `background`              | Live attribute; color or `None`. |
| `size`                    | Current `(width, height)`. |
| `star_count`              | Actual number of stars. |

## Recipes

### 1. Static twinkling backdrop (Space Invaders, menus, puzzles)

```python
field = Starfield(screen.get_size(), velocity=(0, 0), twinkle_speed=0.7, star_size=3)
```

Still call `update(dt)` — that's what animates the twinkle. This is the
setup the [tutorial](tutorial.md) uses (`star_size=3` because its sprites
are drawn at 3× — see the parameter above).

### 2. The Galaxian look

```python
field = Starfield(screen.get_size())          # velocity=(0, 30) is the default
```

Colored stars falling gently, blinking at the arcade rate. (For the
cycle-exact 1979 hardware simulation — the actual shift-register star
generator — see the companion repo
[galaxian-starfield](https://github.com/pmirvine/galaxian-starfield).)

### 3. Horizontal scroller where the player accelerates

If your game scrolls at the player's speed, mirror that speed into the
starfield every frame — one line keeps them perfectly in sync:

```python
player_vx += thrust * dt                       # your movement code
field.velocity = (-player_vx * 0.5, 0)         # stars stream the other way
```

The `0.5` makes the stars move at half the world's speed, which reads as
"the stars are far away". Add `layers=3` and the depth illusion gets
dramatically better.

### 4. Camera-driven world (Defender, or any scrolling level)

When entities live in *world* coordinates and a camera pans over them,
drive the field by how far the camera moved instead of setting a velocity:

```python
field = Starfield(screen.get_size(), velocity=(0, 0), layers=3)

# each frame:
camera_moved = camera_x - old_camera_x
field.scroll(-camera_moved, 0)
```

This is exactly what the Defender sample does — search its
[`main.py`](../src/starfield_kit/defender/main.py) for `STARFIELD`.
Works vertically too (`field.scroll(0, -camera_moved_y)`) for climbers.

### 5. A sky over your own art

```python
field = Starfield(screen.get_size(), background=None, palette="white")

# each frame:
screen.blit(my_gradient, (0, 0))    # your sky
field.draw(screen)                  # stars on top of it
```

### 6. Warp speed

```python
field.velocity = (0, 1200)
field.twinkle_speed = 0             # twinkle reads as flicker at this speed
```

Snap back to `(0, 30)` when the hyperdrive spools down. Because `velocity`
is live, you can ease it with any curve you like.

### 7. Handling window resize

```python
elif event.type == pygame.VIDEORESIZE:
    field.resize((event.w, event.h))
```

Star positions scale with the window and, when you used `density`, the
star count adjusts to keep the same look.

## Performance notes

Stars are pre-rendered once per color and blitted in a single batched
`Surface.fblits()` call — a few thousand stars cost well under a
millisecond on anything modern. If you go wild (`density=20` on a 4K
window), the cost is in Python building the blit list; drop `density`,
or raise `star_size` and lower `count` for the same visual weight.

## How it works (two paragraphs, for the curious)

Each star stores its position as a *fraction* of the field (so resizing
keeps the layout), a color from the palette, and a personal blink period
and phase. Scrolling never moves stars individually: each layer keeps one
scroll offset, and drawing adds it modulo the field size — that's the
wraparound. Twinkling is a comparison against a clock: a star is lit for
55% of its period, dark for the rest, matching the on/off character (and
roughly the tempo) of the original hardware's V1⊕H8 gating.

The default palette really is Galaxian's: two bits per color gun through a
100Ω/150Ω resistor DAC gives four levels — 0, 194, 214, 255 — per gun, and
the 63 visible combinations are computed the same way the board wired it.
