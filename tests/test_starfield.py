"""Behavioral tests for the Starfield library — all headless."""

import pygame
import pytest

from starfield_kit import GALAXIAN_PALETTE, Starfield


def render(field: Starfield) -> bytes:
    surf = pygame.Surface(field.size)
    field.draw(surf)
    return pygame.image.tobytes(surf, "RGB")


def lit_pixels(field: Starfield) -> list[tuple[int, int, tuple[int, int, int]]]:
    surf = pygame.Surface(field.size)
    field.draw(surf)
    w, h = field.size
    out: list[tuple[int, int, tuple[int, int, int]]] = []
    for y in range(h):
        for x in range(w):
            r, g, b = surf.get_at((x, y))[:3]
            if (r, g, b) != (0, 0, 0):
                out.append((x, y, (r, g, b)))
    return out


# --- construction -------------------------------------------------------------


def test_density_scales_with_area():
    small = Starfield((200, 100), seed=1)
    big = Starfield((400, 200), seed=1)  # 4x the area
    assert small.star_count == round(200 * 100 / 2000)
    assert big.star_count == 4 * small.star_count


def test_explicit_count_wins_over_density():
    field = Starfield((300, 300), count=42, density=99, seed=1)
    assert field.star_count == 42


def test_seed_reproduces_the_same_sky():
    a = Starfield((320, 240), seed=7, twinkle_speed=0)
    b = Starfield((320, 240), seed=7, twinkle_speed=0)
    assert render(a) == render(b)
    c = Starfield((320, 240), seed=8, twinkle_speed=0)
    assert render(a) != render(c)


def test_bad_arguments_raise():
    with pytest.raises(ValueError):
        Starfield((100, 100), layers=0)
    with pytest.raises(ValueError):
        Starfield((100, 100), palette="nope")
    with pytest.raises(ValueError):
        Starfield((100, 100), palette=[])


def test_galaxian_palette_is_the_hardware_dac():
    # 63 visible colors (64 minus black), from levels 0/194/214/255 per gun.
    assert len(GALAXIAN_PALETTE) == 63
    assert (0, 0, 0) not in GALAXIAN_PALETTE
    assert (255, 255, 255) in GALAXIAN_PALETTE
    levels = {0, 194, 214, 255}
    assert all(set(c) <= levels for c in GALAXIAN_PALETTE)


# --- drawing ---------------------------------------------------------------------


def test_stars_actually_draw_and_use_the_palette():
    field = Starfield((320, 240), twinkle_speed=0, seed=3)
    pixels = lit_pixels(field)
    assert len(pixels) > 0.8 * field.star_count  # a few may overlap
    assert all(color in GALAXIAN_PALETTE for _, _, color in pixels)


def test_custom_palette_is_respected():
    field = Starfield((200, 200), palette=[(10, 200, 30)], twinkle_speed=0, seed=3)
    assert {c for _, _, c in lit_pixels(field)} == {(10, 200, 30)}


def test_background_none_overlays_instead_of_clearing():
    field = Starfield((100, 100), background=None, twinkle_speed=0, seed=3, count=5)
    surf = pygame.Surface((100, 100))
    surf.fill((40, 0, 60))
    field.draw(surf)
    colors = {surf.get_at((x, y))[:3] for x in range(100) for y in range(100)}
    assert (40, 0, 60) in colors  # our fill survived
    assert len(colors) > 1  # and stars were drawn over it


def test_draw_at_dest_offsets_the_field():
    field = Starfield((60, 60), twinkle_speed=0, seed=5, count=8)
    surf = pygame.Surface((200, 200))
    surf.fill((1, 2, 3))
    field.draw(surf, dest=(100, 100))
    # nothing outside the 60x60 box at (100, 100) may be touched
    for x in range(200):
        for y in range(200):
            inside = 100 <= x < 160 and 100 <= y < 160
            if not inside:
                assert surf.get_at((x, y))[:3] == (1, 2, 3)


# --- motion ----------------------------------------------------------------------


def test_static_field_never_changes():
    field = Starfield((160, 120), velocity=(0, 0), twinkle_speed=0, seed=2)
    before = render(field)
    field.update(5.0)
    assert render(field) == before


def test_scrolling_moves_and_wraps_exactly():
    field = Starfield((160, 120), velocity=(0, 0), twinkle_speed=0, seed=2)
    before = render(field)
    field.scroll(7, 0)
    assert render(field) != before
    field.scroll(160 - 7, 0)  # complete one full wrap
    assert render(field) == before
    field.scroll(0, 120)  # a full vertical wrap changes nothing either
    assert render(field) == before


def test_update_is_framerate_independent():
    # 64 steps of 1/64 s must land exactly where one 1 s step lands
    # (1/64 is exact in binary floating point, so no epsilon needed).
    a = Starfield((160, 120), velocity=(32, 16), twinkle_speed=0, seed=9)
    b = Starfield((160, 120), velocity=(32, 16), twinkle_speed=0, seed=9)
    for _ in range(64):
        a.update(1 / 64)
    b.update(1.0)
    assert render(a) == render(b)


def test_velocity_is_a_live_property():
    field = Starfield((100, 100), seed=1)
    field.velocity = (-120, 4)
    assert field.velocity == (-120.0, 4.0)


def test_twinkle_animates_and_zero_disables():
    twinkly = Starfield((160, 120), velocity=(0, 0), twinkle_speed=1.0, seed=4)
    frames = set()
    for _ in range(8):
        twinkly.update(0.25)
        frames.add(render(twinkly))
    assert len(frames) > 1  # the sky visibly shimmers

    frozen = Starfield((160, 120), velocity=(0, 0), twinkle_speed=0, seed=4)
    before = render(frozen)
    frozen.update(3.33)
    assert render(frozen) == before


# --- star size -----------------------------------------------------------------------


def test_star_size_draws_square_blocks():
    field = Starfield((80, 80), count=1, star_size=3, twinkle_speed=0, seed=5)
    pixels = lit_pixels(field)
    assert len(pixels) == 9  # one star = one 3x3 block
    xs = [x for x, _, _ in pixels]
    ys = [y for _, y, _ in pixels]
    assert max(xs) - min(xs) == 2 and max(ys) - min(ys) == 2


def test_star_size_is_a_live_property():
    field = Starfield((80, 80), count=1, star_size=1, twinkle_speed=0, seed=5)
    assert field.star_size == 1
    assert len(lit_pixels(field)) == 1
    field.star_size = 4  # restyle mid-game, no rebuild required
    assert len(lit_pixels(field)) == 16
    field.star_size = None  # back to automatic (1 px at this window height)
    assert field.star_size is None
    assert len(lit_pixels(field)) == 1


def test_star_size_scales_down_across_parallax_layers():
    field = Starfield((300, 300), star_size=3, layers=3, seed=2)
    assert [layer.size for layer in field._layers] == [1, 2, 3]  # far -> near


# --- layers and resize --------------------------------------------------------------


def test_parallax_layers_move_at_different_rates():
    field = Starfield((200, 200), velocity=(0, 0), layers=3, seed=6)
    field.scroll(10, 0)
    offsets = [layer.offset_x for layer in field._layers]
    assert offsets == sorted(offsets)  # far layers moved less
    assert offsets[0] == pytest.approx(3.0)  # far factor 0.3
    assert offsets[-1] == pytest.approx(10.0)  # near factor 1.0


def test_layers_split_the_star_count():
    field = Starfield((300, 200), count=100, layers=3, seed=6)
    per_layer = [len(layer.stars) for layer in field._layers]
    assert sum(per_layer) == 100
    assert max(per_layer) - min(per_layer) <= 1


def test_resize_keeps_explicit_count_and_adjusts_density():
    fixed = Starfield((200, 100), count=30, seed=1)
    fixed.resize((400, 300))
    assert fixed.size == (400, 300)
    assert fixed.star_count == 30

    dense = Starfield((200, 100), seed=1)
    n = dense.star_count
    dense.resize((400, 200))
    assert dense.star_count == 4 * n
