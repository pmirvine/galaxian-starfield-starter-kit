"""DEFENDER — a complete small game built on starfield_kit.

Run it: ``uv run defender``

Controls: LEFT/RIGHT thrust (the ship keeps its momentum — that's the
game), UP/DOWN move, SPACE fires, P pauses, ESC quits. Clear the landers
before the baiters come for you.

Two things here are worth stealing for your own games:

*   **A wrapping world with a camera.** The world is a 3200-pixel loop.
    Every entity lives at a world x; ``to_screen()`` converts to screen
    space relative to the camera, which trails the ship with look-ahead.

*   **Camera-driven parallax starfield.** The starfield has zero velocity
    of its own. Each frame the game tells it how far the camera moved
    (``stars.scroll(-moved, 0)``) and the three layers slide at their own
    depths. Search for ``# STARFIELD`` to see all four relevant lines.
"""

from __future__ import annotations

import random

import pygame

from ..retro.particles import explosion
from ..retro.sfx import SoundBank
from ..retro.ui import blink_on, draw_text
from ..starfield import Starfield
from . import settings as S
from . import sprites
from .entities import Baiter, Lander, Laser, Player, World, make_terrain, wrap_delta

TITLE, PLAYING, GAME_OVER = "title", "playing", "game over"


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((S.WINDOW_W, S.WINDOW_H))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.sprites = sprites.load(S.PIXEL_SCALE)
        self.sounds = SoundBank()
        self.rng = random.Random()

        # STARFIELD: three parallax layers, no velocity of its own — the
        # camera drives it. A slow drift on the title screen shows it off.
        self.stars = Starfield(
            (S.WINDOW_W, S.WINDOW_H),
            velocity=(-40, 0),
            layers=S.STAR_LAYERS,
            density=S.STAR_DENSITY,
            seed=S.STAR_SEED,
        )

        self.scene = TITLE
        self.scene_time = 0.0
        self.hiscore = 0
        self.world: World | None = None
        self.cam = 0.0  # world x of the left edge of the screen
        self.score = 0
        self.lives = 0
        self.wave = 0
        self.extra_life_given = False
        self.wave_clear_timer = 0.0
        self.paused = False
        self._pressed_keys: set[int] = set()

    # -- game flow ------------------------------------------------------------

    def new_game(self) -> None:
        self.score = 0
        self.lives = S.START_LIVES
        self.wave = 1
        self.extra_life_given = False
        self.stars.velocity = (0, 0)  # STARFIELD: from here on, scroll() drives it
        self.start_wave()
        self.scene = PLAYING
        self.scene_time = 0.0

    def start_wave(self) -> None:
        count = S.LANDERS_PER_WAVE + (self.wave - 1) * S.LANDERS_WAVE_STEP
        self.world = World(
            player=Player(self.sprites["ship"][0].get_size()),
            landers=[Lander(self.rng) for _ in range(count)],
            terrain=make_terrain(self.rng),
        )
        self.cam = (self.world.player.x - S.WINDOW_W * S.CAMERA_LOOKAHEAD) % S.WORLD_W
        self.wave_clear_timer = 0.0

    def add_score(self, points: int) -> None:
        self.score += points
        self.hiscore = max(self.hiscore, self.score)
        if not self.extra_life_given and self.score >= S.EXTRA_LIFE_AT:
            self.extra_life_given = True
            self.lives += 1
            self.sounds.play("fanfare")

    # -- coordinate helpers ------------------------------------------------------

    def to_screen(self, world_x: float) -> float:
        """World x -> screen x, relative to the camera (wrap-aware)."""
        center = (self.cam + S.WINDOW_W / 2) % S.WORLD_W
        return wrap_delta(world_x, center) + S.WINDOW_W / 2

    def on_screen(self, sx: float, margin: float = 60) -> bool:
        return -margin < sx < S.WINDOW_W + margin

    # -- per-scene updates ---------------------------------------------------------

    def update_title(self, dt: float) -> None:
        if self.pressed(pygame.K_SPACE):
            self.new_game()

    def update_playing(self, dt: float) -> None:
        world = self.world
        assert world is not None
        player = world.player

        if self.pressed(pygame.K_p):
            self.paused = not self.paused
        if self.paused:
            self.sounds.stop("thrust")
            return

        world.wave_time += dt
        keys = pygame.key.get_pressed()

        # The ship: thrust, drag, momentum.
        player.update(dt, keys)
        if player.alive and player.thrusting:
            self.sounds.loop("thrust")
        else:
            self.sounds.stop("thrust")

        if player.alive:
            if (
                keys[pygame.K_SPACE]
                and player.fire_cooldown <= 0
                and len(world.lasers) < S.LASER_MAX
            ):
                player.fire_cooldown = S.LASER_COOLDOWN
                nose = player.x + player.facing * player.w / 2
                world.lasers.append(Laser(nose % S.WORLD_W, player.y, player.facing))
                self.sounds.play("zap")
        elif player.respawn_timer <= 0:
            if self.lives > 0:
                player.respawn()
            else:
                self.sounds.stop("thrust")
                self.scene = GAME_OVER
                self.scene_time = 0.0
                self.sounds.play("game_over")
                return

        # STARFIELD: move the camera, then push the stars the other way.
        target = player.x - S.WINDOW_W * (
            S.CAMERA_LOOKAHEAD if player.facing == 1 else 1 - S.CAMERA_LOOKAHEAD
        )
        moved = wrap_delta(target, self.cam) * min(1.0, S.CAMERA_SNAP * dt)
        self.cam = (self.cam + moved) % S.WORLD_W
        self.stars.scroll(-moved, 0)

        # Enemies think; some of them shoot.
        for lander in world.landers:
            shot = lander.update(dt, player.x, self.rng)
            if shot and player.alive:
                world.enemy_shots.append(shot)
        for baiter in world.baiters:
            shot = baiter.update(dt, player.x, player.y, self.rng)
            if shot and player.alive:
                world.enemy_shots.append(shot)

        # Dawdling summons baiters.
        if world.wave_time >= world.next_baiter and player.alive:
            world.next_baiter += S.BAITER_INTERVAL
            world.baiters.append(Baiter(player.x, self.rng))
            self.sounds.play("dive")

        for group in (world.lasers, world.enemy_shots, world.particles):
            for thing in group:
                thing.update(dt)
        world.lasers = [b for b in world.lasers if not b.gone]
        world.enemy_shots = [s for s in world.enemy_shots if not s.gone]
        world.particles = [p for p in world.particles if not p.gone]

        self.check_collisions()

        if not world.landers and not world.baiters:
            if self.wave_clear_timer == 0.0:
                self.wave_clear_timer = S.WAVE_CLEAR_PAUSE
                self.sounds.play("fanfare")
            self.wave_clear_timer -= dt
            if self.wave_clear_timer <= 0:
                self.wave += 1
                self.start_wave()

    def update_game_over(self, dt: float) -> None:
        if self.scene_time > 1.0 and self.pressed(pygame.K_SPACE):
            self.scene = TITLE
            self.scene_time = 0.0
            self.stars.velocity = (-40, 0)  # STARFIELD: title drift again

    def check_collisions(self) -> None:
        world = self.world
        assert world is not None
        player = world.player

        # Lasers vs enemies (world-space, wrap-aware).
        for laser in list(world.lasers):
            hit = None
            for lander in world.landers:
                if laser.hits(lander.x, lander.y, 16):
                    hit, points, color = lander, S.LANDER_POINTS, (110, 255, 130)
                    world.landers.remove(lander)
                    break
            if hit is None:
                for baiter in world.baiters:
                    if laser.hits(baiter.x, baiter.y, 16):
                        hit, points, color = baiter, S.BAITER_POINTS, (255, 70, 70)
                        world.baiters.remove(baiter)
                        break
            if hit is not None:
                if laser in world.lasers:
                    world.lasers.remove(laser)
                self.add_score(points)
                world.particles += explosion(self.to_screen(hit.x), hit.y, color)
                self.sounds.play("boom")

        # Enemy shots and enemy bodies vs the player.
        if player.alive and player.safe_timer <= 0:
            hit = False
            for shot in world.enemy_shots:
                if abs(wrap_delta(shot.x, player.x)) < player.w / 2 - 4 and (
                    abs(shot.y - player.y) < player.h / 2 + 4
                ):
                    hit = True
                    break
            if not hit:
                for enemy in [*world.landers, *world.baiters]:
                    if abs(wrap_delta(enemy.x, player.x)) < player.w / 2 + 8 and (
                        abs(enemy.y - player.y) < player.h / 2 + 10
                    ):
                        hit = True
                        break
            if hit:
                self.lives -= 1
                player.explode()
                self.sounds.stop("thrust")
                world.particles += explosion(
                    self.to_screen(player.x), player.y, (230, 230, 255), big=True
                )
                self.sounds.play("big_boom")
                world.enemy_shots.clear()

    # -- drawing --------------------------------------------------------------------

    def draw_terrain(self) -> None:
        world = self.world
        assert world is not None
        points = []
        for i, h in enumerate(world.terrain):
            sx = self.to_screen(i * S.TERRAIN_STEP)
            if -S.TERRAIN_STEP <= sx <= S.WINDOW_W + S.TERRAIN_STEP:
                points.append((sx, h))
        points.sort()  # left to right across the screen
        if len(points) >= 2:
            pygame.draw.lines(self.screen, S.TERRAIN_COLOR, False, points, 2)

    def draw_radar(self) -> None:
        world = self.world
        assert world is not None
        box = pygame.Rect(0, 0, S.RADAR_W, S.RADAR_H)
        box.midtop = (S.WINDOW_W // 2, 6)
        pygame.draw.rect(self.screen, (0, 0, 0), box)
        pygame.draw.rect(self.screen, S.RADAR_BORDER, box, 1)

        def plot(world_x: float, y: float, color: tuple[int, int, int], size: int) -> None:
            # The radar shows the whole wrapping world, centered on the ship.
            rel = wrap_delta(world_x, world.player.x) / S.WORLD_W  # -0.5 .. 0.5
            px = box.centerx + int(rel * (S.RADAR_W - 4))
            py = box.top + 2 + int(y / S.WINDOW_H * (S.RADAR_H - 6))
            self.screen.fill(color, (px, py, size, size))

        for lander in world.landers:
            plot(lander.x, lander.y, (110, 255, 130), 2)
        for baiter in world.baiters:
            plot(baiter.x, baiter.y, (255, 70, 70), 2)
        if world.player.alive:
            plot(world.player.x, world.player.y, (255, 255, 255), 3)

    def draw_playing(self) -> None:
        world = self.world
        assert world is not None
        player = world.player

        self.draw_terrain()

        for lander in world.landers:
            sx = self.to_screen(lander.x)
            if self.on_screen(sx):
                img = self.sprites["lander"][0]
                self.screen.blit(img, img.get_rect(center=(int(sx), int(lander.y))))
        for baiter in world.baiters:
            sx = self.to_screen(baiter.x)
            if self.on_screen(sx):
                img = self.sprites["baiter"][0]
                self.screen.blit(img, img.get_rect(center=(int(sx), int(baiter.y))))

        if player.alive and (player.safe_timer <= 0 or blink_on(self.scene_time, hz=6)):
            sx = self.to_screen(player.x)
            ship = self.sprites["ship"][0 if player.facing == 1 else 1]
            rect = ship.get_rect(center=(int(sx), int(player.y)))
            self.screen.blit(ship, rect)
            if player.thrusting:  # flickering exhaust at the tail
                frames = self.sprites["flame" if player.facing == 1 else "flame_left"]
                flame = frames[int(self.scene_time * 24) % 2]
                if player.facing == 1:
                    fr = flame.get_rect(midright=(rect.left + 2, rect.centery))
                else:
                    fr = flame.get_rect(midleft=(rect.right - 2, rect.centery))
                self.screen.blit(flame, fr)

        for laser in world.lasers:
            sx = self.to_screen(laser.x)
            tail = sx - laser.direction * S.LASER_LENGTH
            pygame.draw.line(self.screen, (255, 255, 255), (sx, laser.y), (tail, laser.y), 3)
        for shot in world.enemy_shots:
            sx = self.to_screen(shot.x)
            if self.on_screen(sx):
                self.screen.fill((255, 220, 80), (int(sx) - 2, int(shot.y) - 2, 5, 5))
        for p in world.particles:  # particles live in screen space already
            self.screen.fill(p.color, (int(p.x), int(p.y), 3, 3))

        # HUD on top of everything.
        draw_text(self.screen, f"SCORE {self.score:06d}", (12, 10))
        draw_text(
            self.screen,
            f"WAVE {self.wave}",
            (S.WINDOW_W - 12, 10),
            color=S.HUD_COLOR,
            anchor="topright",
        )
        icon = pygame.transform.scale_by(self.sprites["ship"][0], 0.5)
        for i in range(max(0, self.lives)):
            self.screen.blit(icon, (12 + i * (icon.get_width() + 6), 34))
        self.draw_radar()

        if not world.landers and not world.baiters:
            draw_text(
                self.screen,
                f"WAVE {self.wave} CLEAR!",
                (S.WINDOW_W // 2, 200),
                color=S.HUD_COLOR,
                scale=4,
                anchor="center",
            )
        if self.paused:
            draw_text(
                self.screen,
                "PAUSED",
                (S.WINDOW_W // 2, 200),
                color=(255, 255, 255),
                scale=4,
                anchor="center",
            )

    def draw_title(self) -> None:
        cx = S.WINDOW_W // 2
        draw_text(self.screen, "DEFENDER", (cx, 120), color=S.HUD_COLOR, scale=6, anchor="center")
        draw_text(
            self.screen, "a starfield_kit sample", (cx, 165), color=(150, 150, 170), anchor="center"
        )
        lines = [
            "thrust with LEFT and RIGHT - your momentum is the game",
            "UP and DOWN move - SPACE fires - watch the radar",
            "clear the landers - dawdle and the baiters come",
        ]
        for i, line in enumerate(lines):
            draw_text(self.screen, line, (cx, 230 + i * 30), color=(170, 170, 190), anchor="center")
        if blink_on(self.scene_time):
            draw_text(self.screen, "PRESS SPACE", (cx, 350), scale=3, anchor="center")

    def draw_game_over(self) -> None:
        cx = S.WINDOW_W // 2
        draw_text(
            self.screen, "GAME OVER", (cx, 160), color=S.GAMEOVER_COLOR, scale=6, anchor="center"
        )
        draw_text(self.screen, f"FINAL SCORE {self.score}", (cx, 230), anchor="center")
        if self.score >= self.hiscore and self.score > 0:
            draw_text(self.screen, "NEW HIGH SCORE!", (cx, 265), color=S.HUD_COLOR, anchor="center")
        if self.scene_time > 1.0 and blink_on(self.scene_time):
            draw_text(self.screen, "PRESS SPACE", (cx, 330), scale=3, anchor="center")

    # -- the loop ----------------------------------------------------------------------

    def pressed(self, key: int) -> bool:
        return key in self._pressed_keys

    def run(self) -> int:
        running = True
        while running:
            dt = min(self.clock.tick(S.FPS) / 1000, 0.05)
            self.scene_time += dt

            self._pressed_keys = set()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    self._pressed_keys.add(event.key)

            self.stars.update(dt)  # STARFIELD: twinkle (and title drift)

            if self.scene == TITLE:
                self.update_title(dt)
            elif self.scene == PLAYING:
                self.update_playing(dt)
            else:
                self.update_game_over(dt)

            self.stars.draw(self.screen)  # STARFIELD: always the bottom layer
            if self.scene == TITLE:
                self.draw_title()
            elif self.scene == PLAYING:
                self.draw_playing()
            else:
                self.draw_game_over()

            pygame.display.flip()

        pygame.quit()
        return 0


def main() -> int:
    return Game().run()


if __name__ == "__main__":
    raise SystemExit(main())
