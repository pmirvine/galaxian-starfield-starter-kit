"""GALAXIANS — a complete small game built on starfield_kit.

Run it: ``uv run galaxians``

Controls: arrow keys move, SPACE fires (one shot in the air at a time,
just like 1979), P pauses, ESC quits.

The file reads top to bottom as three layers:

1.  ``Game.__init__`` — create the window, the starfield, sprites, sounds.
2.  ``update_*`` methods — one per scene (title / playing / game over):
    what changes each frame.
3.  ``draw_*`` methods — how each scene looks.

The starfield usage is exactly three lines (marked with ``# STARFIELD``):
create it once, ``update(dt)`` every frame, ``draw(screen)`` first.

The moving parts live in entities.py, the pixel art in sprites.py, and
every tunable number in settings.py — imported as ``S``, so when you see
``S.DIVE_SPEED`` below, that's the file to open to make the game yours.
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
from .entities import DIVING, Convoy, Player, Shot, World

# The scene names. self.scene holds one of these and run() picks the matching
# update_*/draw_* pair each frame — a state machine in its simplest clothes.
TITLE, PLAYING, GAME_OVER = "title", "playing", "game over"


class Game:
    """Owns the window, the scenes, and the loop that runs them."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((S.WINDOW_W, S.WINDOW_H))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.sprites = sprites.load(S.PIXEL_SCALE)
        self.sounds = SoundBank()
        self.rng = random.Random()

        # STARFIELD: one gently falling arcade sky behind everything.
        # star_size matches the sprites' pixel scale, so the stars sit in
        # the same blocky world as everything else.
        self.stars = Starfield(
            (S.WINDOW_W, S.WINDOW_H),
            velocity=S.STAR_VELOCITY,
            density=S.STAR_DENSITY,
            star_size=S.STAR_SIZE,
            seed=S.STAR_SEED,
        )

        # Scene bookkeeping. self.world (the live wave) stays None until a
        # game starts — the title screen has no aliens to run.
        self.scene = TITLE
        self.scene_time = 0.0
        self.hiscore = 0
        self.world: World | None = None
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
        self.start_wave()
        self.scene = PLAYING
        self.scene_time = 0.0

    def start_wave(self) -> None:
        """A fresh World for the current wave: new player, new convoy."""
        player_size = self.sprites["player"][0].get_size()
        self.world = World(Player(player_size), Convoy(self.wave, self.rng))
        self.wave_clear_timer = 0.0

    def add_score(self, points: int) -> None:
        """Bank points and hand out the single extra ship at S.EXTRA_LIFE_AT."""
        self.score += points
        self.hiscore = max(self.hiscore, self.score)
        if not self.extra_life_given and self.score >= S.EXTRA_LIFE_AT:
            self.extra_life_given = True
            self.lives += 1
            self.sounds.play("fanfare")

    # -- per-scene updates ------------------------------------------------------

    def update_title(self, dt: float) -> None:
        if self.pressed(pygame.K_SPACE):
            self.new_game()

    def update_playing(self, dt: float) -> None:
        world = self.world
        assert world is not None
        player, convoy = world.player, world.convoy

        # Pause gate: flip on P, and while paused skip all movement below.
        if self.pressed(pygame.K_p):
            self.paused = not self.paused
        if self.paused:
            return

        # The player: move, shoot, respawn.
        player.update(dt, pygame.key.get_pressed())
        if player.alive:
            # The bullet cap: only S.PLAYER_MAX_SHOTS in the air — tweak it in settings.py.
            if self.pressed(pygame.K_SPACE) and len(world.player_shots) < S.PLAYER_MAX_SHOTS:
                world.player_shots.append(
                    Shot(player.x, player.y - player.h / 2, 0, -S.PLAYER_SHOT_SPEED)
                )
                self.sounds.play("laser")
        # Death pause over: bring the ship back, or end the game if no lives remain.
        elif player.respawn_timer <= 0:
            if self.lives > 0:
                player.respawn()
            else:
                self.scene = GAME_OVER
                self.scene_time = 0.0
                self.sounds.play("game_over")
                return

        # The convoy: sway, dive, shoot back (its update returns any new shots).
        world.enemy_shots.extend(convoy.update(dt, player.x, player.alive))
        if convoy.just_launched:
            self.sounds.play("dive")

        # Move every bullet and particle; drop the ones that left the screen.
        for group in (world.player_shots, world.enemy_shots, world.particles):
            for thing in group:
                thing.update(dt)
        # (Rebuilding each list is the tidy way to drop items while looping.)
        world.player_shots = [s for s in world.player_shots if not s.gone]
        world.enemy_shots = [s for s in world.enemy_shots if not s.gone]
        world.particles = [p for p in world.particles if not p.gone]

        self.check_collisions()

        # Wave cleared: short pause, then a faster convoy.
        if convoy.defeated:
            # The timer doubles as a flag: 0.0 means the pause hasn't started yet.
            if self.wave_clear_timer == 0.0:
                self.wave_clear_timer = S.WAVE_CLEAR_PAUSE
                self.sounds.play("fanfare")
            self.wave_clear_timer -= dt
            if self.wave_clear_timer <= 0:
                self.wave += 1
                self.start_wave()

    def update_game_over(self, dt: float) -> None:
        # Wait a beat so a leftover SPACE press can't skip this screen instantly.
        if self.scene_time > 1.0 and self.pressed(pygame.K_SPACE):
            self.scene = TITLE
            self.scene_time = 0.0

    def check_collisions(self) -> None:
        """Everything is rectangles: shots vs aliens, then threats vs the player."""
        world = self.world
        assert world is not None
        player, convoy = world.player, world.convoy

        # Player shots vs aliens.
        # (list(...) is a copy, so removing from the real list mid-loop is safe.)
        for shot in list(world.player_shots):
            hit = None
            for alien in convoy.aliens:
                size = self.sprites[alien.kind][0].get_size()
                if alien.rect(size).colliderect(shot.rect):
                    hit = alien
                    break
            if hit is not None:
                world.player_shots.remove(shot)
                convoy.aliens.remove(hit)
                self.add_score(hit.score)
                color = (255, 220, 80) if hit.kind == "flagship" else (90, 220, 255)
                world.particles += explosion(hit.x, hit.y, color)
                self.sounds.play("boom")

        # Enemy shots and diving aliens vs the player.
        # safe_timer > 0 is the respawn grace period: blinking and untouchable.
        if player.alive and player.safe_timer <= 0:
            died = any(s.rect.colliderect(player.rect) for s in world.enemy_shots)
            for alien in [a for a in convoy.aliens if a.state == DIVING]:
                size = self.sprites[alien.kind][0].get_size()
                if alien.rect(size).colliderect(player.rect):
                    died = True  # ramming counts, for both parties
                    convoy.aliens.remove(alien)
                    self.add_score(alien.score)
            if died:
                self.lives -= 1
                player.explode()
                world.particles += explosion(player.x, player.y, (230, 230, 255), big=True)
                self.sounds.play("big_boom")
                # Clear the sky so you don't respawn into the volley that killed you.
                world.enemy_shots.clear()

    # -- drawing -----------------------------------------------------------------

    def draw_hud(self) -> None:
        draw_text(self.screen, f"SCORE {self.score:06d}", (12, 10), color=S.SCORE_COLOR)
        draw_text(
            self.screen,
            f"HI {self.hiscore:06d}",
            (S.WINDOW_W // 2, 10),
            color=S.HUD_COLOR,
            anchor="midtop",
        )
        draw_text(
            self.screen,
            f"WAVE {self.wave}",
            (S.WINDOW_W - 12, 10),
            color=S.HUD_COLOR,
            anchor="topright",
        )
        # One little ship icon per remaining life.
        icon = pygame.transform.scale_by(self.sprites["player"][0], 0.6)
        for i in range(max(0, self.lives)):
            self.screen.blit(icon, (10 + i * (icon.get_width() + 6), S.WINDOW_H - 30))

    def draw_title(self) -> None:
        cx = S.WINDOW_W // 2
        draw_text(self.screen, "GALAXIANS", (cx, 130), color=S.HUD_COLOR, scale=5, anchor="center")
        draw_text(
            self.screen, "a starfield_kit sample", (cx, 175), color=(150, 150, 170), anchor="center"
        )
        # The score table doubles as a cast introduction.
        rows = [("flagship", "150"), ("escort", "50"), ("drone", "30")]
        for i, (kind, points) in enumerate(rows):
            frame = self.sprites[kind][0]
            y = 260 + i * 56
            self.screen.blit(frame, frame.get_rect(center=(cx - 50, y)))
            draw_text(self.screen, f"{points} PTS", (cx - 10, y), anchor="midleft")
        # blink_on flips True/False on a beat — the classic attract-mode flash.
        if blink_on(self.scene_time):
            draw_text(
                self.screen,
                "PRESS SPACE",
                (cx, 480),
                color=(255, 255, 255),
                scale=3,
                anchor="center",
            )
        draw_text(
            self.screen,
            "arrows move - space fires - p pauses",
            (cx, 560),
            color=(110, 110, 140),
            anchor="center",
        )

    def draw_playing(self) -> None:
        world = self.world
        assert world is not None
        # Painter's order: later draws sit on top — aliens, then player, bullets,
        # sparks, and the HUD last (the starfield already went down in run()).
        # Wing-flap animation: all aliens share a global 2-frame beat.
        frame_i = int(world.convoy.time * S.FLAP_RATE) % 2
        for alien in world.convoy.aliens:
            frame = self.sprites[alien.kind][frame_i]
            self.screen.blit(frame, frame.get_rect(center=(int(alien.x), int(alien.y))))

        player = world.player
        # During respawn grace the ship blinks: draw it only on the "on" beats.
        if player.alive and (player.safe_timer <= 0 or blink_on(self.scene_time, hz=6)):
            sprite = self.sprites["player"][0]
            self.screen.blit(sprite, sprite.get_rect(center=(int(player.x), int(player.y))))

        # Bullets and sparks are bare filled rectangles — no sprite needed at this size.
        for shot in world.player_shots:
            self.screen.fill((255, 255, 255), (int(shot.x) - 1, int(shot.y) - 6, 3, 12))
        for shot in world.enemy_shots:
            self.screen.fill((255, 220, 80), (int(shot.x) - 1, int(shot.y) - 6, 3, 12))
        for p in world.particles:
            self.screen.fill(p.color, (int(p.x), int(p.y), 3, 3))

        self.draw_hud()
        if world.convoy.defeated:
            draw_text(
                self.screen,
                f"WAVE {self.wave} CLEAR!",
                (S.WINDOW_W // 2, 300),
                color=S.HUD_COLOR,
                scale=4,
                anchor="center",
            )
        if self.paused:
            draw_text(
                self.screen,
                "PAUSED",
                (S.WINDOW_W // 2, 300),
                color=(255, 255, 255),
                scale=4,
                anchor="center",
            )

    def draw_game_over(self) -> None:
        cx = S.WINDOW_W // 2
        draw_text(
            self.screen, "GAME OVER", (cx, 240), color=S.GAMEOVER_COLOR, scale=5, anchor="center"
        )
        draw_text(self.screen, f"FINAL SCORE {self.score}", (cx, 310), anchor="center")
        if self.score >= self.hiscore and self.score > 0:
            draw_text(self.screen, "NEW HIGH SCORE!", (cx, 345), color=S.HUD_COLOR, anchor="center")
        if self.scene_time > 1.0 and blink_on(self.scene_time):
            draw_text(self.screen, "PRESS SPACE", (cx, 420), scale=3, anchor="center")

    # -- the loop ------------------------------------------------------------------

    def pressed(self, key: int) -> bool:
        """Was this key pressed this frame? (Collected from the event queue.)"""
        return key in self._pressed_keys

    def run(self) -> int:
        """The heartbeat: events, then update, then draw — S.FPS times a second."""
        running = True
        while running:
            # dt = seconds since last frame; multiply every speed by it.
            dt = min(self.clock.tick(S.FPS) / 1000, 0.05)  # cap dt: no warp after a hiccup
            self.scene_time += dt

            # Input: collect this frame's fresh key presses (held keys are read
            # straight off the keyboard in update_playing).
            self._pressed_keys = set()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    self._pressed_keys.add(event.key)

            # STARFIELD: animate it even on menus — the sky never stops.
            self.stars.update(dt)

            # Run whichever scene is on stage: update first, then draw further down.
            if self.scene == TITLE:
                self.update_title(dt)
            elif self.scene == PLAYING:
                self.update_playing(dt)
            else:
                self.update_game_over(dt)

            # STARFIELD: draw first, so everything else sits on top of it.
            self.stars.draw(self.screen)
            if self.scene == TITLE:
                self.draw_title()
            elif self.scene == PLAYING:
                self.draw_playing()
            else:
                self.draw_game_over()

            # One flip per frame shows everything drawn above at once.
            pygame.display.flip()

        pygame.quit()
        return 0


def main() -> int:
    return Game().run()


if __name__ == "__main__":
    raise SystemExit(main())
