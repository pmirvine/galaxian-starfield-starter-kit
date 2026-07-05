"""Test setup: force SDL's dummy drivers BEFORE pygame is imported anywhere,
so the whole suite runs headless (no window, no audio device needed)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def pygame_session():
    pygame.init()
    # Some game code blits to "the screen"; give it a dummy one.
    pygame.display.set_mode((800, 600))
    yield
    pygame.quit()
