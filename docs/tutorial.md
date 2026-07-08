# Build your first game: INVADERS

In this tutorial you will build a small Space-Invaders-style game from an
empty file, on top of the kit's starfield. No prior game-programming
experience is assumed — just basic Python (variables, lists, loops,
functions).

The finished game ships with the kit, so you can see where you are headed
right now:

```sh
uv run invaders
```

A grid of invaders marches over a **static, twinkling starfield** — the sky
doesn't scroll, it just quietly shimmers, which is exactly what a
fixed-screen game like this wants. You will build that whole game, step by
step. Whenever you get stuck, the finished code is in
[`src/starfield_kit/invaders/main.py`](../src/starfield_kit/invaders/main.py),
and its comments are numbered to match the steps below.

## Step 0 — a place to work

Work inside this repository so the kit is importable. Create a file called
`mygame.py` in the repository root (next to `README.md`), and run it with:

```sh
uv run python mygame.py
```

(`uv run` makes sure the project's virtualenv — with pygame-ce installed —
is used. If you prefer plain pip, `pip install -e .` once, then
`python mygame.py`.)

## Step 1 — a window and the loop

Every pygame game is the same skeleton: open a window, then repeat forever —
*handle input, update the world, draw everything* — sixty times a second.
Put this in `mygame.py`:

```python
import random

import pygame

from starfield_kit import Starfield
from starfield_kit.retro.pixelart import sprite
from starfield_kit.retro.sfx import SoundBank
from starfield_kit.retro.ui import draw_text

WIDTH, HEIGHT = 640, 480

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("INVADERS")
clock = pygame.time.Clock()

running = True
while running:
    # dt is the time the last frame took, in seconds. Multiply every
    # speed by it and your game runs the same on fast and slow machines.
    dt = min(clock.tick(60) / 1000, 0.05)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    screen.fill((0, 0, 0))
    pygame.display.flip()

pygame.quit()
```

Run it. A black window that closes with Esc — congratulations, that's the
heart of every game ever made. Two lines deserve attention:

* `clock.tick(60)` waits just long enough to cap the game at 60 frames per
  second, and returns how many milliseconds the frame actually took. We
  convert to seconds and call it `dt` ("delta time"). **Every** movement in
  this tutorial will be `speed * dt`, so nothing depends on the frame rate.
* The `min(..., 0.05)` cap means that if the window is dragged or the
  computer hiccups for a second, the world advances at most 0.05 s — no
  bullet teleports through an invader.

## Step 2 — the starfield

Three lines. After `clock = ...`, create the field:

```python
stars = Starfield((WIDTH, HEIGHT), velocity=(0, 0), twinkle_speed=0.7, star_size=3, seed=7)
```

Inside the loop, *before* the drawing, animate it; and replace the
`screen.fill(...)` with drawing the field (it paints the black for you):

```python
    stars.update(dt)   # with the other updates

    stars.draw(screen)  # instead of screen.fill(...) — the sky goes first
    pygame.display.flip()
```

Run it. A night sky, gently twinkling. The parameters we picked:

* `velocity=(0, 0)` — the stars don't move. Invaders is a fixed screen, so
  a scrolling sky would look wrong. (Try `(0, 30)` for a moment to see the
  difference — then put it back.)
* `twinkle_speed=0.7` — a little calmer than the arcade default of 1.0.
* `star_size=3` — every star is a 3×3 block. That is no accident: in
  Step 3 we will draw our sprites at 3× scale, and giving the stars the
  same "virtual pixel" size makes the whole screen feel like one chunky
  low-resolution machine (it is also about how fat the 1979 arcade's
  stars looked at this window scale). Leave it out and the field picks a
  subtler size automatically.
* `seed=7` — the same sky every run. Any number works; each gives its own
  layout. Delete the argument for a fresh sky per run.

Everything else (star colors, density, sizes) is a sensible default. The
full menu of options is in [starfield-api.md](starfield-api.md).

## Step 3 — the player

Sprites in this kit are ASCII art: one string per row, one character per
pixel, and a legend mapping characters to colors — `.` means transparent.
Add this above the loop:

```python
PLAYER_ART = [
    "....W....",
    "...WWW...",
    "...WWW...",
    "GGWWWWWGG",
    "GGGGGGGGG",
]
COLORS = {"W": (230, 230, 255), "G": (110, 255, 130), "g": (110, 255, 130)}

player_img = sprite(PLAYER_ART, COLORS, scale=3)
player = player_img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 16))
```

`sprite()` turns the art into an image; `scale=3` blows each character up
into a 3×3 block — that chunky look is a feature. `get_rect()` gives us a
`pygame.Rect`: a rectangle that knows its position and size. Rects are the
workhorse of 2D games — they move, they clamp, they collide.

Move it with the arrow keys (inside the loop, after the event handling):

```python
    keys = pygame.key.get_pressed()
    player.x += int((keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 300 * dt)
    player.clamp_ip(screen.get_rect())
```

The `keys[...] - keys[...]` trick: each is `True`/`False`, which Python
treats as 1/0, so the subtraction gives -1, 0, or +1 — a direction. Then
`clamp_ip` keeps the rect inside the window. Draw the ship after the stars:

```python
    stars.draw(screen)
    screen.blit(player_img, player)
    pygame.display.flip()
```

Run it: a ship you can steer over a starfield. It's starting to feel like
a game already.

## Step 4 — shooting

Shots are just small rects in a list. Above the loop:

```python
shots = []
sounds = SoundBank()   # the kit's synthesized retro sound effects
```

We want one shot per key *press* (not a stream while held), so extend the
event handling:

```python
    fired = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                fired = True
```

Then, in the update section:

```python
    if fired and len(shots) < 3:
        shots.append(pygame.Rect(player.centerx - 2, player.top - 12, 4, 12))
        sounds.play("laser")
    for shot in shots:
        shot.y -= int(700 * dt)
    shots = [s for s in shots if s.bottom > 0]
```

That last line is a pattern you will use constantly: rebuild the list,
keeping only the things still worth keeping (here: shots still on screen).
Draw them as plain rectangles, after the player:

```python
    for shot in shots:
        screen.fill((255, 255, 255), shot)
```

Run it. Pew pew (the "laser" is a square wave whose pitch falls — see
`src/starfield_kit/retro/sfx.py` for how little that takes).

## Step 5 — the invaders march

The formation is, again, a list of rects. Above the loop:

```python
INVADER_ART = [
    ".g.....g.",
    "..g...g..",
    ".ggggggg.",
    "gg.ggg.gg",
    "ggggggggg",
    "g.g...g.g",
    "...g.g...",
]

COLS, ROWS = 8, 4
GRID_X, GRID_Y = 80, 60
SPACING_X, SPACING_Y = 58, 44
STEP_SIZE = 12   # pixels sideways per march step
DROP_SIZE = 18   # pixels downward at the edges

def new_invaders():
    rects = []
    for row in range(ROWS):
        for col in range(COLS):
            rects.append(pygame.Rect(GRID_X + col * SPACING_X,
                                     GRID_Y + row * SPACING_Y, 27, 21))
    return rects

invader_img = sprite(INVADER_ART, COLORS, scale=3)
invaders = new_invaders()
march_dir = 1      # 1 = right, -1 = left
march_timer = 0.0
march_note = 0     # the four-note bass line cycles as they step
```

(The 27×21 rect is just the sprite's size: 9×7 art × scale 3.)

Unlike our smooth shots, the invaders move in discrete *steps* on a timer —
that stomp-stomp-stomp is the personality of the whole game. In the update
section:

```python
    march_timer -= dt
    if march_timer <= 0 and invaders:
        march_timer = 0.06 + 0.5 * len(invaders) / (COLS * ROWS)
        at_edge = any((r.right + STEP_SIZE * march_dir > WIDTH - 10)
                      or (r.left + STEP_SIZE * march_dir < 10)
                      for r in invaders)
        for r in invaders:
            if at_edge:
                r.y += DROP_SIZE
            else:
                r.x += STEP_SIZE * march_dir
        if at_edge:
            march_dir = -march_dir
        sounds.play(f"march{march_note}")
        march_note = (march_note + 1) % 4
```

Read the timer line again: the delay between steps shrinks as `invaders`
shrinks. Fewer invaders → faster heartbeat → rising panic. That one line
of arithmetic is most of Space Invaders' game design.

Draw them (before the player, after the stars):

```python
    for r in invaders:
        screen.blit(invader_img, r)
```

Run it and just watch for a while. March, drop, turn, march — with the
four-note bass line speeding up. This is the moment the project starts to
feel alive.

## Step 6 — collisions and score

Because everything is a rect, collision detection is nearly free. Add
`score = 0` above the loop, then in the update section:

```python
    for shot in list(shots):
        hit = shot.collidelist(invaders)
        if hit != -1:
            invaders.pop(hit)
            shots.remove(shot)
            score += 10
            sounds.play("boom")
```

`collidelist` checks one rect against a whole list and returns the index
of the first hit (or -1). Note the `list(shots)` — we iterate over a
*copy*, because removing from a list you are looping over is a classic
bug. Show the score with the kit's chunky text helper, drawn last so it
sits on top:

```python
    draw_text(screen, f"SCORE {score:05d}", (10, 8))
```

Run it. Shoot a few invaders and watch the march speed up.

## Step 7 — bombs, lives, game over

The invaders shoot back. Add `bombs = []`, `lives = 3`,
`game_over = False` above the loop. At the end of the march step (inside
the `if march_timer <= 0` block), an invader occasionally drops one:

```python
        if random.random() < 0.4:
            shooter = random.choice(invaders)
            bombs.append(pygame.Rect(shooter.centerx - 2, shooter.bottom, 4, 10))
```

Move the bombs and handle the consequences, in the update section:

```python
    for bomb in bombs:
        bomb.y += int(260 * dt)
    bombs = [b for b in bombs if b.top < HEIGHT]

    for bomb in list(bombs):
        if bomb.colliderect(player):
            bombs.remove(bomb)
            lives -= 1
            sounds.play("big_boom")
    if any(r.bottom >= player.top for r in invaders):
        lives = 0                      # they reached you — instantly fatal
    if lives <= 0:
        game_over = True
        sounds.play("game_over")
    if not invaders:                   # cleared! send the next, bolder wave
        invaders = new_invaders()
        bombs.clear()
        sounds.play("fanfare")
```

Now wrap ALL of the update logic (player movement, shots, march, bombs,
collisions) in `if not game_over:` — when the game ends, the world
freezes but the loop (and the twinkling sky) carries on. Let SPACE
restart, as the `else` of that same `if`:

```python
    else:
        if fired:
            invaders = new_invaders()
            shots, bombs = [], []
            score, lives = 0, 3
            game_over = False
            player.midbottom = (WIDTH // 2, HEIGHT - 16)
```

Finally, in the draw section: skip the player while dead, show the state
of the world honestly, and announce the bad news:

```python
    draw_text(screen, f"LIVES {max(0, lives)}", (WIDTH - 10, 8), anchor="topright")
    for bomb in bombs:
        screen.fill((255, 220, 80), bomb)
    if game_over:
        draw_text(screen, "GAME OVER", (WIDTH // 2, HEIGHT // 2 - 20),
                  color=(255, 80, 80), scale=5, anchor="center")
        draw_text(screen, "PRESS SPACE", (WIDTH // 2, HEIGHT // 2 + 30),
                  anchor="center")
```

## Step 8 — you made a game

That's the whole thing: ~150 lines, and every one of them earns its place.
Compare your file against the shipped version
([`src/starfield_kit/invaders/main.py`](../src/starfield_kit/invaders/main.py))
— it is the same program with the steps marked in comments.

Some things worth noticing about what you built:

* **Draw order is layering.** Stars → invaders → player → shots → text.
  Painters draw backgrounds first; so do games.
* **Lists of rects are a complete entity system** for a game this size. No
  classes were needed. When entities get richer (the diving aliens in the
  Galaxians sample, say) classes start to pay for themselves — see how
  `src/starfield_kit/galaxians/entities.py` grows them naturally.
* **Everything is tunable.** Bomb speed, march step, shot limit, twinkle.
  Change numbers, rerun, feel the difference. That loop — tweak, run,
  feel — is game development. Every sample in the kit marks its dials with
  a `# TWEAK:` comment — `grep -rn "TWEAK" src/` lists them all.

## Where to go next

* **Give the sky some motion.** One line: `velocity=(0, 25)` makes it
  drift like Galaxian. Or try `layers=3, velocity=(-60, 0)` and watch
  parallax happen behind your invaders.
* **Read the two bigger samples.** `uv run galaxians` (scrolling sky,
  diving enemies, title/game-over scenes) and `uv run defender`
  (a camera moving through a wrapping world, with the starfield driven by
  `scroll()` — the technique for any side-scroller).
* **Start a game from the arcade tableau.** `uv run galaxians-demo` is a
  non-interactive screen at Galaxian's true 1979 geometry — starfield,
  convoy, ship, all laid out, nothing wired up. Adding arrow keys and a
  fire button to `src/starfield_kit/galaxians/attract.py` is a lovely
  second project after this one.
* **Explore every starfield knob** in the playground: `uv run
  starfield-demo`, and its reference: [starfield-api.md](starfield-api.md).
* **Steal this kit for your own game.** Copy
  `src/starfield_kit/starfield.py` into any pygame-ce project — it is
  self-contained on purpose. The pixel-art and sound helpers are nearly as
  small if you want them too.
* **Start a fresh project from zero.** When you want your own game in its
  own repo (not `mygame.py` inside this one), the
  [pygame-ce-starter](https://github.com/pmirvine/pygame-ce-starter) kit
  scaffolds a complete pygame-ce project — Python, dependencies, linting,
  and headless tests — with one command. Scaffold it, then drop
  `starfield.py` in and you are exactly where Step 2 started.
