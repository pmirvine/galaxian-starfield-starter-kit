# galaxian-starfield-starter-kit

An arcade-style **starfield background for [pygame-ce](https://pyga.me/)**
that you can drop into any game — any window size, any scroll direction
and speed (or none at all), twinkle, parallax depth, adjustable density,
the real Galaxian star colors — **plus three complete sample games and a
from-scratch beginner tutorial** showing how to use it.

Built for novice game developers: every sprite is ASCII art in the source,
every sound is synthesized in ~30 lines you can read, and every game is
small enough to understand in one sitting.

| | |
| --- | --- |
| ![Galaxians](docs/screenshots/galaxians_play.png) | ![Defender](docs/screenshots/defender_play.png) |
| `uv run galaxians` — scrolling sky | `uv run defender` — parallax + camera |
| ![Invaders](docs/screenshots/invaders_play.png) | ![Playground](docs/screenshots/demo.png) |
| `uv run invaders` — static twinkling sky | `uv run starfield-demo` — the playground |

## Quick start

With [uv](https://docs.astral.sh/uv/) (it fetches Python and dependencies
for you):

```sh
git clone https://github.com/pmirvine/galaxian-starfield-starter-kit.git
cd galaxian-starfield-starter-kit
uv run starfield-demo     # the interactive playground
uv run galaxians          # dive-bombing convoy over a drifting sky
uv run defender           # inertia, a wrapping world, parallax stars
uv run invaders           # the tutorial game: static twinkling backdrop
uv run galaxians-demo     # non-interactive: the 1979 starfield at true arcade geometry
```

Or with plain pip (Python 3.10+): `pip install -e .` then `starfield-demo`.

## The starfield in three lines

```python
import pygame
from starfield_kit import Starfield

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

field = Starfield(screen.get_size())            # 1 — create

running = True
while running:
    dt = clock.tick(60) / 1000
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    field.update(dt)                            # 2 — animate
    field.draw(screen)                          # 3 — draw first
    # ... your ships, aliens and score go on top ...
    pygame.display.flip()

pygame.quit()
```

**To use it in your own project:** copy the single file
[`src/starfield_kit/starfield.py`](src/starfield_kit/starfield.py) —
it is self-contained (stdlib + pygame-ce only) on purpose.

Every use case is one constructor call:

```python
Starfield(size)                                  # Galaxian: slow downward drift
Starfield(size, velocity=(0, 0))                 # static, twinkling (Invaders)
Starfield(size, velocity=(-150, 0), layers=3)    # side-scroller with parallax
Starfield(size, star_size=3)                     # chunky stars for 3x pixel art
Starfield(size, density=3, palette="white")      # busy modern sky
Starfield(size, count=80, twinkle_speed=0)       # sparse and still
```

…and everything is adjustable live (`field.velocity = (0, 1200)` = warp).
The full parameter reference with recipes:
**[docs/starfield-api.md](docs/starfield-api.md)**.

## New to game programming? Start here

**[docs/tutorial.md](docs/tutorial.md)** builds a complete
Space-Invaders-style game from an empty file, step by step: window → loop
→ starfield → player → shooting → marching invaders → collisions → game
over. The finished game ships as `uv run invaders`, with its code
annotated by tutorial step.

Then read the two bigger samples, in order:

| game | teaches |
| --- | --- |
| [`galaxians/`](src/starfield_kit/galaxians/) | scenes (title/play/game over), sprite animation, diving enemies with curved paths, scoring, waves — under a classic scrolling sky |
| [`defender/`](src/starfield_kit/defender/) | acceleration + momentum, a wrapping world, a look-ahead camera, radar — with the starfield driven by the camera (`scroll()`) and 3 parallax layers |

Both are structured the same way (`settings.py` for every tunable number,
`sprites.py` for the ASCII art, `entities.py` for behavior, `main.py` for
the loop) so what you learn in one transfers to the other. No binary
assets anywhere: sprites are ASCII grids, sounds are synthesized square
waves and noise ([`retro/sfx.py`](src/starfield_kit/retro/sfx.py)).

## Where this comes from

The default palette, drift speed, and twinkle rhythm are modeled on the
starfield of Namco's **Galaxian (1979)**. To see that lineage plainly, run

```sh
uv run galaxians-demo
```

<img src="docs/screenshots/galaxian_1979.png" width="336" align="right" alt="The 1979 tableau: static convoy and ship over the drifting starfield">

— a deliberately **non-interactive** tableau at the cabinet's true
geometry: a 224×256 screen at 3× (672×768), 3-pixel stars, 252 of them,
drifting down at the hardware's exact ~91 px/s, behind a frozen convoy,
score header, and ship. Nothing moves but the sky — it exists purely to
show the starfield as it appeared in the original game. It is also a
tidy skeleton to build on: the screen is already laid out at arcade
proportions, so adding a keyboard-controlled ship is the natural first
step toward your own Galaxian
([`galaxians/attract.py`](src/starfield_kit/galaxians/attract.py) is a
single short file).

If you want the cycle-exact hardware simulation of that board — the
actual 17-bit LFSR star generator, half-pixel stars and all — that lives
in the companion repo
**[galaxian-starfield](https://github.com/pmirvine/galaxian-starfield)**.
This kit is the friendly, flexible cousin: same soul, any game.

## Develop

```sh
uv run pytest                 # headless test suite
uv run ruff format .          # format
uv run ruff check --fix .     # lint
uv run ty check               # type-check
```

## Layout

```
src/starfield_kit/
  starfield.py     THE library — self-contained, copy this file
  demo.py          interactive parameter playground
  invaders/        the tutorial game (simplest — start here)
  galaxians/       sample: convoy, dives, scenes, scrolling sky
  defender/        sample: momentum, wrapping world, parallax via scroll()
  retro/           shared teaching helpers: pixel art, synth sfx, chunky text
docs/
  tutorial.md      build INVADERS from an empty file
  starfield-api.md every parameter, with recipes
tests/             headless (SDL dummy) — logic, not windows
```

MIT licensed. Steal everything.
