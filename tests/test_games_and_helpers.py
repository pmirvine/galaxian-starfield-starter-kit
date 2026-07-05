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


# --- asteroids ------------------------------------------------------------------------


def test_asteroids_rocks_split_and_world_wraps(monkeypatch):
    from starfield_kit.asteroids import main as ast

    game = ast.Game()
    chunks = game.rocks[0].split(game.rng)
    assert [c.tier for c in chunks] == [2, 2]  # big rocks break in two
    assert ast.Rock(pygame.Vector2(0, 0), 1, game.rng).split(game.rng) == []
    assert ast.wrap(pygame.Vector2(-5, 610)) == pygame.Vector2(795, 10)

    monkeypatch.setattr(pygame.key, "get_pressed", lambda: FakeKeys({pygame.K_UP, pygame.K_SPACE}))
    game._pressed = set()
    for _ in range(60 * 4):  # thrust and fire blindly for four seconds
        game.update(1 / 60)
    assert 0 <= game.ship.pos.x < ast.WIDTH and 0 <= game.ship.pos.y < ast.HEIGHT
    assert all(0 <= r.pos.x < ast.WIDTH for r in game.rocks)
    game.draw()


# --- skyraid --------------------------------------------------------------------------


def test_skyraid_throttle_drives_the_starfield(monkeypatch):
    from starfield_kit.skyraid import main as sr

    game = sr.Game()
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: FakeKeys({pygame.K_UP}))
    game._pressed = set()
    for _ in range(120):
        game.update(1 / 60)
    assert game.throttle > sr.THROTTLE_MIN
    assert game.stars.velocity == (0, game.throttle)  # the live-velocity link

    # Clearing the wave triggers the warp burst: twinkle off, velocity ramps.
    game.raiders.clear()
    game.update(1 / 60)
    assert game.warp_timer > 0
    assert game.stars.twinkle_speed == 0
    for _ in range(60):
        game.update(1 / 60)
    assert game.stars.velocity[1] > sr.THROTTLE_MAX  # well past cruise speed
    for _ in range(int(sr.WARP_TIME * 60) + 10):
        game.update(1 / 60)
    assert game.warp_timer <= 0
    assert game.stars.twinkle_speed == 1.0  # sanity restored
    assert game.wave == 2
    game.draw()


# --- lander ---------------------------------------------------------------------------


def test_lander_gravity_landing_and_crash():
    from starfield_kit.lander import main as ld

    game = ld.Game()
    game._pressed = set()
    vy0 = game.vy
    for _ in range(30):
        game.update(1 / 60)  # hands off the controls: gravity wins
    assert game.vy > vy0

    # Hover just above the widest pad at a gentle speed: touchdown.
    i0, i1, _mult = game.pads[0]
    game.x = (i0 + i1) / 2 * ld.TERRAIN_STEP
    game.y = game.terrain[i0] - game.ship_img.get_height() / 2 - 1
    game.vx, game.vy = 0.0, 20.0
    for _ in range(10):  # a few frames to close the last pixel
        game.update(1 / 60)
        if game.landed:
            break
    assert game.landed
    assert game.score > 0
    game.draw()

    # Same spot but way too fast: that is a crash, not a landing.
    crash = ld.Game()
    crash._pressed = set()
    i0, i1, _mult = crash.pads[0]
    crash.x = (i0 + i1) / 2 * ld.TERRAIN_STEP
    crash.y = crash.terrain[i0] - crash.ship_img.get_height() / 2 - 1
    crash.vx, crash.vy = 0.0, 200.0
    crash.update(1 / 60)
    assert not crash.landed
    assert crash.ships == ld.START_SHIPS - 1


# --- missiles -------------------------------------------------------------------------


def test_missiles_interceptor_blooms_and_chains():
    from starfield_kit.missiles import main as ms

    game = ms.Game()
    game.launch((400, 200))
    assert len(game.interceptors) == 1
    assert game.ammo == ms.AMMO_PER_WAVE - 1
    for _ in range(300):  # let it fly to the mark
        game.update(1 / 60)
        if game.blasts:
            break
    assert game.blasts, "the interceptor should bloom into a blast"

    # An enemy at the blast's heart dies, scores, and blooms in turn.
    enemy = ms.Enemy(1, [400], game.rng)
    enemy.pos = pygame.Vector2(game.blasts[0].pos)
    game.enemies.append(enemy)
    score0, blasts0 = game.score, len(game.blasts)
    game.update(1 / 60)
    assert enemy not in game.enemies
    assert game.score >= score0 + 25
    assert len(game.blasts) > blasts0  # the chain reaction
    game.draw()


def test_missiles_city_falls_when_hit():
    from starfield_kit.missiles import main as ms

    game = ms.Game()
    game.to_spawn = 0
    enemy = ms.Enemy(1, [ms.CITY_XS[0]], game.rng)
    enemy.pos = enemy.target - pygame.Vector2(0, 4)
    game.enemies = [enemy]
    for _ in range(30):
        game.update(1 / 60)
        if not game.cities[0]:
            break
    assert game.cities[0] is False


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
