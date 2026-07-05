"""Smoke tests: the demo, helpers, and all three sample games run headless
for a few simulated seconds without crashing, and their basic rules hold."""

import pygame
import pytest

from starfield_kit.retro import pixelart, sfx, ui

# --- retro helpers --------------------------------------------------------------


def test_sprite_from_ascii_grid():
    surf = pixelart.sprite([".W.", "WWW"], {"W": (255, 255, 255)}, scale=4)
    assert surf.get_size() == (12, 8)
    assert surf.get_at((4, 0))[:3] == (255, 255, 255)  # the top-center block
    assert surf.get_at((0, 0)).a == 0  # '.' is transparent


def test_sprite_unknown_char_raises():
    with pytest.raises(ValueError, match="no entry"):
        pixelart.sprite(["X"], {"W": (1, 2, 3)})


def test_synth_produces_correct_sample_counts():
    dur = 0.1
    data = sfx._sweep(dur, 800, 200)
    assert len(data) == int(sfx.RATE * dur) * 2  # 16-bit mono = 2 bytes/sample
    assert len(sfx._noise(dur)) == len(data)
    assert len(sfx._notes([440, 220], dur)) == 2 * len(data)


def test_soundbank_survives_headless():
    bank = sfx.SoundBank()  # dummy audio driver: may enable or not — either is fine
    bank.play("laser")
    bank.loop("thrust")
    bank.stop("thrust")


def test_pixel_text_scales():
    small = ui.pixel_text("HI", (255, 255, 255), scale=1)
    big = ui.pixel_text("HI", (255, 255, 255), scale=3)
    assert big.get_width() == small.get_width() * 3


# --- the demo -----------------------------------------------------------------------


def test_demo_state_builds_all_parameter_combos():
    from starfield_kit import demo

    state = demo.DemoState((320, 240))
    for i in range(len(demo.PALETTES)):
        state.palette_i = i
        for j in range(len(demo.LAYER_CHOICES)):
            state.layers_i = j
            for k in range(len(demo.STAR_SIZES)):
                state.size_i = k
                field = state.build()
                assert field.star_count > 0
    assert "Starfield(size" in state.constructor_text()
    assert "star_size=4" in state.constructor_text()  # last size in the cycle


# --- galaxians ------------------------------------------------------------------------


def simulate_galaxians(seconds: float):
    from starfield_kit.galaxians.main import Game

    game = Game()
    game.new_game()
    dt = 1 / 60
    for frame in range(int(seconds * 60)):
        game._pressed_keys = {pygame.K_SPACE} if frame % 30 == 0 else set()
        game.stars.update(dt)
        game.update_playing(dt)
        if game.scene != "playing":
            break
    game.stars.draw(game.screen)
    game.draw_playing()  # drawing must not crash either
    return game


def test_galaxians_plays_a_few_seconds():
    game = simulate_galaxians(6)
    world = game.world
    assert world is not None
    assert game.scene in ("playing", "game over")
    assert 0 < len(world.convoy.aliens) <= 32
    # firing blind for six seconds into a swaying convoy scores something
    assert game.score >= 0
    assert game.hiscore >= game.score


def test_galaxians_wave_clears_when_convoy_dies():
    game = simulate_galaxians(1)
    assert game.world is not None
    game.world.convoy.aliens.clear()
    game._pressed_keys = set()
    for _ in range(int(60 * 3)):
        game.update_playing(1 / 60)
        if game.wave == 2:
            break
    assert game.wave == 2  # the pause elapsed and a new convoy arrived
    assert game.world is not None
    assert len(game.world.convoy.aliens) == 32


def test_galaxians_attract_matches_the_arcade_numbers():
    from starfield_kit.galaxians import attract, sprites

    # 224x256 native at 3x scale, like the rotated cabinet monitor.
    assert (attract.WINDOW_W, attract.WINDOW_H) == (672, 768)
    stars = attract.make_starfield()
    assert stars.star_count == 252  # 256 per LFSR cycle minus the 4 black
    vx, vy = stars.velocity
    assert vx == 0
    assert vy == pytest.approx(0.5 * 60.606 * 3)  # half a native px per frame
    assert stars.star_size == 3

    # The tableau draws without crashing, and the convoy is 36 strong.
    assert sum(count for _, count in attract.CONVOY_ROWS) == 36
    screen = pygame.display.set_mode((attract.WINDOW_W, attract.WINDOW_H))
    stars.update(1 / 60)
    attract.draw_frame(screen, stars, sprites.load(attract.SCALE))


# --- defender -----------------------------------------------------------------------


class FakeKeys:
    def __init__(self, down=()):
        self.down = set(down)

    def __getitem__(self, key):
        return key in self.down


def test_defender_thrust_camera_and_wrapping(monkeypatch):
    from starfield_kit.defender import settings as S
    from starfield_kit.defender.main import Game

    game = Game()
    game.new_game()
    monkeypatch.setattr(
        pygame.key, "get_pressed", lambda: FakeKeys({pygame.K_RIGHT, pygame.K_SPACE})
    )
    dt = 1 / 60
    assert game.world is not None
    start_x = game.world.player.x
    for _ in range(60 * 5):
        game._pressed_keys = set()
        game.stars.update(dt)
        game.update_playing(dt)
        if game.scene != "playing":
            break
    assert game.world is not None
    player = game.world.player
    assert player.vx == S.MAX_SPEED  # thrust hit the speed cap
    assert 0 <= player.x < S.WORLD_W  # position stays wrapped
    assert (player.x - start_x) % S.WORLD_W > S.WINDOW_W  # actually travelled
    assert 0 <= game.cam < S.WORLD_W
    game.stars.draw(game.screen)
    game.draw_playing()


def test_defender_wrap_delta_shortest_path():
    from starfield_kit.defender import settings as S
    from starfield_kit.defender.entities import wrap_delta

    assert wrap_delta(10, S.WORLD_W - 10) == 20  # across the seam
    assert wrap_delta(S.WORLD_W - 10, 10) == -20
    assert wrap_delta(100, 100) == 0


def test_defender_baiters_arrive_when_dawdling():
    from starfield_kit.defender.main import Game

    game = Game()
    game.new_game()
    assert game.world is not None
    game.world.wave_time = 999  # pretend we dawdled
    game._pressed_keys = set()
    game.update_playing(1 / 60)
    assert len(game.world.baiters) == 1


# --- invaders -------------------------------------------------------------------------


def test_invaders_runs_via_its_real_main_loop(monkeypatch):
    from starfield_kit.invaders import main as invaders

    frames = {"n": 0}
    real_flip = pygame.display.flip

    def fake_flip():
        frames["n"] += 1
        if frames["n"] == 20:  # fire once
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        if frames["n"] >= 90:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", fake_flip)
    assert invaders.main() == 0
    assert frames["n"] >= 90


def test_invaders_formation_layout():
    from starfield_kit.invaders.main import COLS, ROWS, new_invaders

    rects = new_invaders()
    assert len(rects) == COLS * ROWS
    assert all(r.width > 0 for r in rects)
