"""INVADERS — the game you build in docs/tutorial.md, finished.

Run it: ``uv run invaders``

This is deliberately the simplest game in the kit: one file, no scenes,
no classes — just a loop, some lists, and a static twinkling starfield
behind everything. If you are new to game programming, read the tutorial
and build this yourself; come back here whenever you want to peek at the
answer key. The section numbers below match the tutorial's steps.

Controls: arrows move, SPACE fires, SPACE restarts after game over.
"""

from __future__ import annotations

import random

import pygame

from starfield_kit import Starfield
from starfield_kit.retro.pixelart import sprite
from starfield_kit.retro.sfx import SoundBank
from starfield_kit.retro.ui import draw_text

# --- Step 1: a window ---------------------------------------------------------

WIDTH, HEIGHT = 640, 480

# --- Step 3: the cast, as ASCII pixel art --------------------------------------

PLAYER_ART = [
    "....W....",
    "...WWW...",
    "...WWW...",
    "GGWWWWWGG",
    "GGGGGGGGG",
]

INVADER_ART = [
    ".g.....g.",
    "..g...g..",
    ".ggggggg.",
    "gg.ggg.gg",
    "ggggggggg",
    "g.g...g.g",
    "...g.g...",
]

COLORS = {"W": (230, 230, 255), "G": (110, 255, 130), "g": (110, 255, 130)}

# --- Step 5: invader grid layout ------------------------------------------------

COLS, ROWS = 8, 4
GRID_X, GRID_Y = 80, 60  # top-left of the formation
SPACING_X, SPACING_Y = 58, 44
STEP_SIZE = 12  # pixels sideways per march step
DROP_SIZE = 18  # pixels downward when the edge is reached


def new_invaders() -> list[pygame.Rect]:
    """A fresh formation: one rect per invader (rects make collisions easy)."""
    rects = []
    for row in range(ROWS):
        for col in range(COLS):
            rects.append(pygame.Rect(GRID_X + col * SPACING_X, GRID_Y + row * SPACING_Y, 27, 21))
    return rects


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("INVADERS — a starfield_kit tutorial game")
    clock = pygame.time.Clock()

    # --- Step 2: the starfield — static (velocity zero), quietly twinkling,
    # with 3-pixel stars to match the 3x scale the sprites are drawn at.
    stars = Starfield((WIDTH, HEIGHT), velocity=(0, 0), twinkle_speed=0.7, star_size=3, seed=7)

    player_img = sprite(PLAYER_ART, COLORS, scale=3)
    invader_img = sprite(INVADER_ART, COLORS, scale=3)
    sounds = SoundBank()

    # --- Step 7: everything that changes during play, reset per game --------
    def reset() -> tuple:
        return (new_invaders(), [], [], 0)  # invaders, shots, bombs, score

    invaders, shots, bombs, score = reset()
    player = player_img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 16))
    lives = 3
    game_over = False
    march_dir = 1  # 1 = marching right, -1 = left
    march_timer = 0.0
    march_note = 0  # which of the four bass notes plays next

    running = True
    while running:
        # dt = seconds since last frame; multiply every speed by it.
        dt = min(clock.tick(60) / 1000, 0.05)

        fired = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    fired = True

        stars.update(dt)  # animates the twinkle (the field itself is static)

        if not game_over:
            # --- Step 3: move the player.
            keys = pygame.key.get_pressed()
            player.x += int((keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 300 * dt)
            player.clamp_ip(screen.get_rect())

            # --- Step 4: fire (up to three of our shots in the air at once).
            if fired and len(shots) < 3:
                shots.append(pygame.Rect(player.centerx - 2, player.top - 12, 4, 12))
                sounds.play("laser")
            for shot in shots:
                shot.y -= int(700 * dt)
            shots = [s for s in shots if s.bottom > 0]

            # --- Step 5: the invaders march on a beat that speeds up as
            # their numbers shrink (the classic Space Invaders heartbeat).
            march_timer -= dt
            if march_timer <= 0 and invaders:
                march_timer = 0.06 + 0.5 * len(invaders) / (COLS * ROWS)
                at_edge = any(
                    (r.right + STEP_SIZE * march_dir > WIDTH - 10)
                    or (r.left + STEP_SIZE * march_dir < 10)
                    for r in invaders
                )
                for r in invaders:
                    if at_edge:
                        r.y += DROP_SIZE
                    else:
                        r.x += STEP_SIZE * march_dir
                if at_edge:
                    march_dir = -march_dir
                sounds.play(f"march{march_note}")
                march_note = (march_note + 1) % 4
                # An invader may drop a bomb on each step.
                if random.random() < 0.4:
                    shooter = random.choice(invaders)
                    bombs.append(pygame.Rect(shooter.centerx - 2, shooter.bottom, 4, 10))

            for bomb in bombs:
                bomb.y += int(260 * dt)
            bombs = [b for b in bombs if b.top < HEIGHT]

            # --- Step 6: collisions. Rects make this one line each.
            for shot in list(shots):
                hit = shot.collidelist(invaders)
                if hit != -1:
                    invaders.pop(hit)
                    shots.remove(shot)
                    score += 10
                    sounds.play("boom")

            # --- Step 7: bombs (or invaders reaching the bottom) cost lives.
            for bomb in list(bombs):
                if bomb.colliderect(player):
                    bombs.remove(bomb)
                    lives -= 1
                    sounds.play("big_boom")
            if any(r.bottom >= player.top for r in invaders):
                lives = 0
            if lives <= 0:
                game_over = True
                sounds.play("game_over")
            if not invaders:  # wave cleared — send a fresh, ever-bolder wave
                invaders = new_invaders()
                bombs.clear()
                sounds.play("fanfare")

        elif fired:  # game over + SPACE = play again
            invaders, shots, bombs, score = reset()
            lives = 3
            game_over = False
            player.midbottom = (WIDTH // 2, HEIGHT - 16)

        # --- Step 8: draw everything, back to front.
        stars.draw(screen)  # the sky first, so it sits behind everything
        for r in invaders:
            screen.blit(invader_img, r)
        if not game_over:
            screen.blit(player_img, player)
        for shot in shots:
            screen.fill((255, 255, 255), shot)
        for bomb in bombs:
            screen.fill((255, 220, 80), bomb)
        draw_text(screen, f"SCORE {score:05d}", (10, 8))
        draw_text(screen, f"LIVES {max(0, lives)}", (WIDTH - 10, 8), anchor="topright")
        if game_over:
            draw_text(
                screen,
                "GAME OVER",
                (WIDTH // 2, HEIGHT // 2 - 20),
                color=(255, 80, 80),
                scale=5,
                anchor="center",
            )
            draw_text(screen, "PRESS SPACE", (WIDTH // 2, HEIGHT // 2 + 30), anchor="center")
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
