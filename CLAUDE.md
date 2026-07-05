# galaxian-starfield-starter-kit — project guide

A **pygame-ce** starter kit managed by **uv**. Everything runs through `uv run`
so the project virtualenv is always used — never invoke a bare `python`/`pip`.

## Commands
- Interactive starfield playground: `uv run starfield-demo`
- Big samples: `uv run galaxians` · `uv run defender`
- Single-file demo games: `uv run invaders` · `uv run asteroids` ·
  `uv run skyraid` · `uv run lander` · `uv run missiles`
- Arcade-geometry tableau (non-interactive): `uv run galaxians-demo`
- Test (headless): `uv run pytest`
- Format: `uv run ruff format .`
- Lint (autofix): `uv run ruff check --fix .`
- Type check: `uv run ty check`
- Add a runtime dep: `uv add <pkg>` · dev tool: `uv add --dev <pkg>`

## Conventions
- **Library is `pygame-ce`, imported as `pygame`.** Do not `pip install pygame`;
  the two conflict. Prefer pygame-ce APIs (e.g. `Surface.fblits`).
- **Frame-rate independent movement:** multiply velocities by `dt` (seconds),
  where `dt = clock.tick(FPS) / 1000`. Don't assume a fixed step.
- `src/starfield_kit/starfield.py` is the product: keep it **self-contained**
  (stdlib + pygame only) so users can copy that one file into their game.
- Sample games live in their own subpackages; tunables go in each game's
  `settings.py`; shared game helpers (pixel art, sound synth, text) live in
  `starfield_kit/retro/`.
- Tests must stay **headless**: set `SDL_VIDEODRIVER=dummy` /
  `SDL_AUDIODRIVER=dummy` before importing pygame (see `tests/conftest.py`),
  and test logic/state rather than opening a window.
- No binary assets: sprites are ASCII pixel grids in code, sounds are
  synthesized at startup (`retro/sfx.py`). Keep it that way — it is part of
  the teaching value.

## Docs
`docs/tutorial.md` is a from-scratch beginner walkthrough that must stay in
sync with `src/starfield_kit/invaders/` — if you change one, change the other.
`docs/starfield-api.md` documents every `Starfield` parameter.
