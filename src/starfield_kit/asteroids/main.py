"""ASTEROIDS — rotation, thrust, and drifting rocks.

Run it: ``uv run asteroids``

Controls: LEFT/RIGHT rotate, UP thrusts (you keep drifting — that's the
game), SPACE fires, P pauses, ESC quits, SPACE restarts after game over.

What this demo teaches that the other games don't:

*   **Vectors and rotation.** The ship is not a sprite: it is three points
    rotated by an angle and drawn as lines, like the 1979 vector monitor.
    `pygame.math.Vector2` does the trigonometry (`from_polar`), thrust
    *adds* to a velocity vector, and everything wraps around the screen.
*   **Circle collisions.** Rocks are lumpy polygons, but they collide as
    circles — distance between centers vs. radius. Cheaper and smoother
    than rectangles for round things.

The starfield here is the *quiet* configuration: static, sparse
(``count=90``), plain white, barely twinkling — a restrained backdrop
that suits the stark vector look instead of stealing attention from it.

Like every demo in this kit, movement is frame-rate independent: speeds
are in px/sec and get multiplied by ``dt`` each frame. Any number you can
safely tune is marked ``TWEAK`` — grep for it; the constants just below
are the best place to start making the game your own.
"""

from __future__ import annotations

import random

import pygame

from ..retro.particles import explosion
from ..retro.sfx import SoundBank
from ..retro.ui import blink_on, draw_text
from ..starfield import Starfield

WIDTH, HEIGHT = 800, 600
WHITE = (230, 230, 255)

# The knobs. Units are pixels and seconds; every TWEAK says how a change feels.
SHIP_TURN = 230  # TWEAK: turn rate (degrees/sec) — higher = twitchier handling
SHIP_THRUST = 300  # TWEAK: px/s^2 gained while holding UP — higher = punchier ship
SHIP_DRAG = 0.3  # TWEAK: speed bleed per second — 0 is the true drifty arcade (harder)
SHIP_MAX_SPEED = 460  # TWEAK: speed cap (px/sec) — keeps a runaway drift recoverable
BULLET_SPEED = 540  # TWEAK: shot speed (px/sec), added on top of the ship's own drift
BULLET_LIFE = 1.1  # TWEAK: seconds before a shot fizzles — longer = more range
BULLET_MAX = 4  # TWEAK: shots alive at once, as in the arcade — raise for a looser feel
FIRE_COOLDOWN = 0.18  # TWEAK: seconds between shots — lower = a faster trigger

# tier -> (radius in px, score for shooting it) — small rocks are worth the most
ROCK_TIERS = {3: (52, 20), 2: (30, 50), 1: (16, 100)}  # TWEAK: rock sizes and scores
START_LIVES = 3  # TWEAK: spare ships — more = an easier game


def wrap(v: pygame.Vector2) -> pygame.Vector2:
    """Everything in Asteroids lives on a torus: off one edge, in the other."""
    return pygame.Vector2(v.x % WIDTH, v.y % HEIGHT)  # modulo folds 810 -> 10 and -5 -> 795


def polar(length: float, degrees: float) -> pygame.Vector2:
    """A vector of the given length pointing at `degrees` — the bridge
    between "an angle and a speed" and "an x and a y"."""
    v = pygame.Vector2()
    v.from_polar((length, degrees))  # pygame does the cos/sin so we don't have to
    return v


class Ship:
    """The player: an angle to steer, a velocity vector to drift on."""

    def __init__(self) -> None:
        self.pos = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        self.vel = pygame.Vector2()
        self.angle = -90.0  # degrees; -90 points straight up
        self.thrusting = False
        self.alive = True
        self.respawn_timer = 0.0  # counts down the dead-time between ships
        self.safe_timer = 3.0  # TWEAK: seconds of spawn invulnerability — higher = safer starts
        self.fire_cooldown = 0.0

    def heading(self) -> pygame.Vector2:
        """A length-1 vector pointing where the nose points."""
        return polar(1, self.angle)

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        if not self.alive:
            self.respawn_timer -= dt  # dead: just count down to the respawn
            return
        # Run the countdowns; max() pins them at zero instead of going negative.
        self.safe_timer = max(0.0, self.safe_timer - dt)
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        # keys[...] are 0 or 1, so right minus left gives -1, 0 or +1 steering.
        self.angle += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * SHIP_TURN * dt
        self.thrusting = bool(keys[pygame.K_UP])
        if self.thrusting:
            self.vel += self.heading() * SHIP_THRUST * dt  # thrust ADDS velocity
        self.vel *= max(0.0, 1.0 - SHIP_DRAG * dt)  # drag shaves off a sliver of speed
        if self.vel.length() > SHIP_MAX_SPEED:
            self.vel.scale_to_length(SHIP_MAX_SPEED)
        self.pos = wrap(self.pos + self.vel * dt)  # the heart of it: position += velocity * dt

    def points(self) -> list[pygame.Vector2]:
        """Nose, right wing, tail notch, left wing — rotated to `angle`."""
        shape = [(16, 0), (-11, 10), (-6, 0), (-11, -10)]  # px offsets, nose first
        # .rotate() turns each offset by our angle; adding pos plants it on screen.
        return [self.pos + pygame.Vector2(p).rotate(self.angle) for p in shape]

    def explode(self) -> None:
        self.alive = False
        self.thrusting = False
        self.respawn_timer = 1.6  # seconds of empty screen before the next ship

    def respawn(self) -> None:
        self.alive = True
        self.pos = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        self.vel = pygame.Vector2()
        self.angle = -90.0
        self.safe_timer = 2.5  # a fresh, slightly shorter spawn shield


class Bullet:
    """A dot that flies from the nose and dies of old age, not distance."""

    def __init__(self, ship: Ship) -> None:
        self.pos = pygame.Vector2(ship.points()[0])  # leaves from the nose
        self.vel = ship.vel + ship.heading() * BULLET_SPEED  # your drift carries into the shot
        self.age = 0.0

    def update(self, dt: float) -> None:
        self.age += dt
        self.pos = wrap(self.pos + self.vel * dt)  # bullets wrap too — mind your back

    @property
    def gone(self) -> bool:
        return self.age > BULLET_LIFE


class Rock:
    """A drifting rock. Tier 3 is big; each hit splits it toward tier 1."""

    def __init__(self, pos: pygame.Vector2, tier: int, rng: random.Random) -> None:
        self.tier = tier
        self.radius, self.score = ROCK_TIERS[tier]
        self.pos = pygame.Vector2(pos)
        # TWEAK: rock drift speed (px/sec) — raise 30, 70 for a faster, harder field.
        speed = rng.uniform(30, 70) * (4 - tier)  # smaller rocks fly faster
        self.vel = polar(speed, rng.uniform(0, 360))
        self.angle = 0.0
        self.spin = rng.uniform(-70, 70)  # tumble in degrees/sec — purely cosmetic
        # A lumpy outline: 10 spokes of slightly random length. Computed once,
        # rotated every frame — the collision circle underneath stays round.
        self.shape = [polar(self.radius * rng.uniform(0.72, 1.0), i * 36) for i in range(10)]

    def update(self, dt: float) -> None:
        self.pos = wrap(self.pos + self.vel * dt)
        self.angle += self.spin * dt

    def points(self) -> list[pygame.Vector2]:
        return [self.pos + p.rotate(self.angle) for p in self.shape]

    def split(self, rng: random.Random) -> list[Rock]:
        """Shot rocks break into two of the next tier down (tier 1 just dies)."""
        if self.tier == 1:
            return []
        # TWEAK: two chunks per split — range(3) makes waves swarm (much harder).
        return [Rock(self.pos, self.tier - 1, rng) for _ in range(2)]


class Game:
    """Owns the window and the world, and runs events -> update -> draw."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("ASTEROIDS — a starfield_kit demo")
        self.clock = pygame.time.Clock()
        self.sounds = SoundBank()
        self.rng = random.Random()

        # STARFIELD: static and understated — white, sparse, a slow shimmer.
        self.stars = Starfield(
            (WIDTH, HEIGHT),
            velocity=(0, 0),
            count=90,
            palette="white",
            twinkle_speed=0.4,
            star_size=2,
            seed=1979,
        )

        self.time = 0.0
        self.paused = False
        self._pressed: set[int] = set()
        self.new_game()

    def new_game(self) -> None:
        self.ship = Ship()
        self.bullets: list[Bullet] = []
        self.rocks: list[Rock] = []
        self.particles = []
        self.score = 0
        self.lives = START_LIVES
        self.wave = 0
        self.game_over = False
        self.next_wave()

    def next_wave(self) -> None:
        self.wave += 1
        # TWEAK: rocks per wave — wave 1 gets 3 big ones; raise the 2 for a harder start.
        for _ in range(2 + self.wave):
            # Spawn away from the ship: somewhere on the far half of the screen.
            offset = polar(self.rng.uniform(220, 380), self.rng.uniform(0, 360))
            self.rocks.append(Rock(wrap(self.ship.pos + offset), 3, self.rng))

    def update(self, dt: float) -> None:
        # _pressed holds keys that went down THIS frame, so P toggles once per
        # tap instead of 60 times a second while held.
        if pygame.K_p in self._pressed:
            self.paused = not self.paused
        if self.paused or self.game_over:
            return

        # get_pressed() reports HELD keys — right for steering, thrust and fire.
        keys = pygame.key.get_pressed()
        self.ship.update(dt, keys)
        if self.ship.alive and self.ship.thrusting:
            self.sounds.loop("thrust")
        else:
            self.sounds.stop("thrust")

        if self.ship.alive:
            # Fire only if the trigger has cooled AND under the BULLET_MAX cap —
            # the shot limit is what makes aiming matter.
            if (
                keys[pygame.K_SPACE]
                and self.ship.fire_cooldown <= 0
                and len(self.bullets) < BULLET_MAX
            ):
                self.ship.fire_cooldown = FIRE_COOLDOWN
                self.bullets.append(Bullet(self.ship))
                self.sounds.play("laser")
        elif self.ship.respawn_timer <= 0:
            # Death pause over: come back if a life remains, otherwise it's over.
            if self.lives > 0:
                self.ship.respawn()
            else:
                self.game_over = True
                self.sounds.stop("thrust")
                self.sounds.play("game_over")

        # Everything that drifts updates the same way, so one loop moves it all.
        for thing in (*self.bullets, *self.rocks, *self.particles):
            thing.update(dt)
        # Rebuild the lists keeping only survivors — simpler than deleting mid-loop.
        self.bullets = [b for b in self.bullets if not b.gone]
        self.particles = [p for p in self.particles if not p.gone]

        # Bullets vs rocks: circle collision — distance against radius.
        # list(...) makes throwaway copies to loop over, so removing things
        # from the real lists mid-loop is safe.
        for bullet in list(self.bullets):
            for rock in list(self.rocks):
                if bullet.pos.distance_to(rock.pos) < rock.radius:
                    self.bullets.remove(bullet)
                    self.rocks.remove(rock)
                    self.rocks += rock.split(self.rng)  # one rock becomes two smaller ones
                    self.score += rock.score
                    self.particles += explosion(rock.pos.x, rock.pos.y, WHITE)
                    self.sounds.play("boom", volume=0.4 + 0.2 * rock.tier)
                    break  # this bullet is spent — on to the next one

        # Rocks vs the ship (a slightly generous 10 px ship radius).
        if self.ship.alive and self.ship.safe_timer <= 0:  # the spawn shield blocks all hits
            for rock in list(self.rocks):
                if self.ship.pos.distance_to(rock.pos) < rock.radius + 10:
                    self.lives -= 1
                    self.ship.explode()
                    self.particles += explosion(self.ship.pos.x, self.ship.pos.y, WHITE, big=True)
                    self.sounds.play("big_boom")
                    break

        # Screen cleared? The next, slightly bigger wave rolls in immediately.
        if not self.rocks:
            self.sounds.play("fanfare")
            self.next_wave()

    def draw(self) -> None:
        # Painter's order — later draws sit on top: stars, rocks, ship, shots, HUD.
        # stars.draw also repaints the black background, erasing last frame.
        self.stars.draw(self.screen)

        for rock in self.rocks:
            pygame.draw.polygon(self.screen, WHITE, rock.points(), 2)  # outlines only

        ship = self.ship
        # While the spawn shield lasts, the ship blinks: drawn only on the on-beats.
        if ship.alive and (ship.safe_timer <= 0 or blink_on(self.time, hz=6)):
            pygame.draw.polygon(self.screen, WHITE, ship.points(), 2)
            if ship.thrusting and blink_on(self.time, hz=15):  # flickering exhaust
                tail = [
                    ship.pos + pygame.Vector2(-6, 4).rotate(ship.angle),
                    ship.pos + pygame.Vector2(-16, 0).rotate(ship.angle),
                    ship.pos + pygame.Vector2(-6, -4).rotate(ship.angle),
                ]
                pygame.draw.lines(self.screen, (255, 150, 60), False, tail, 2)

        # Bullets and sparks are tiny filled squares — cheap and period-correct.
        for bullet in self.bullets:
            self.screen.fill(WHITE, (int(bullet.pos.x) - 1, int(bullet.pos.y) - 1, 3, 3))
        for p in self.particles:
            self.screen.fill(p.color, (int(p.x), int(p.y), 3, 3))

        draw_text(self.screen, f"SCORE {self.score:06d}", (12, 10))
        draw_text(
            self.screen,
            f"WAVE {self.wave}",
            (WIDTH - 12, 10),
            anchor="topright",
            color=(120, 255, 160),
        )
        for i in range(max(0, self.lives)):  # spare ships as little outlines
            cx = 20 + i * 24
            pts = [(cx, 34), (cx - 7, 52), (cx, 47), (cx + 7, 52)]
            pygame.draw.polygon(self.screen, WHITE, pts, 1)

        if self.paused:
            draw_text(self.screen, "PAUSED", (WIDTH // 2, HEIGHT // 2), scale=4, anchor="center")
        if self.game_over:
            draw_text(
                self.screen,
                "GAME OVER",
                (WIDTH // 2, HEIGHT // 2 - 20),
                color=(255, 80, 80),
                scale=5,
                anchor="center",
            )
            if blink_on(self.time):
                draw_text(
                    self.screen, "PRESS SPACE", (WIDTH // 2, HEIGHT // 2 + 34), anchor="center"
                )

    def run(self) -> int:
        """The classic loop: read events, update the world, draw, flip. Repeat."""
        running = True
        while running:
            # tick(60) waits out the 60 fps frame budget and returns elapsed ms;
            # /1000 turns it into dt, the seconds every speed is multiplied by.
            # min() stops a hiccup (e.g. dragging the window) becoming a huge step.
            dt = min(self.clock.tick(60) / 1000, 0.05)
            self.time += dt

            self._pressed = set()  # fresh each frame: keys that went down just now
            # Handle input: window close and one-shot key taps arrive as events.
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    self._pressed.add(event.key)

            if self.game_over and pygame.K_SPACE in self._pressed:
                self.new_game()

            self.stars.update(dt)  # STARFIELD: static, but the twinkle still lives
            self.update(dt)  # update the world (movement, collisions, waves)
            self.draw()  # then draw it, back to front
            pygame.display.flip()  # show the finished frame all at once

        pygame.quit()
        return 0


def main() -> int:
    return Game().run()


if __name__ == "__main__":
    raise SystemExit(main())
