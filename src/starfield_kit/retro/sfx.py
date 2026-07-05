"""Bleepy arcade sound effects, synthesized from scratch at startup.

There are no audio files in this kit. Every effect is a few thousand
16-bit samples computed with plain Python (square waves for tones, random
values for noise) and handed to ``pygame.mixer.Sound(buffer=...)``. That
keeps the repository free of binary assets and shows how simple retro
audio really is: a laser is just a square wave whose pitch falls quickly.

Usage in a game::

    sounds = SoundBank()          # after pygame.init()
    sounds.play("laser")
    sounds.loop("thrust")         # loops until...
    sounds.stop("thrust")

If the machine has no audio device (CI, some containers), SoundBank
quietly disables itself and every call becomes a harmless no-op.
"""

from __future__ import annotations

import math
import random
from array import array

import pygame

RATE = 22050  # samples per second; plenty for chip-style effects

# ---------------------------------------------------------------------------
# Tiny synthesizer: each helper returns raw signed-16-bit mono sample bytes.
# ---------------------------------------------------------------------------


def _sweep(
    duration: float,
    start_hz: float,
    end_hz: float,
    *,
    volume: float = 0.5,
    fade: bool = True,
    vibrato_hz: float = 0.0,
    vibrato_depth: float = 0.0,
) -> bytes:
    """A square wave that glides from start_hz to end_hz. With vibrato it
    warbles around that glide — instant 1979. Phase is accumulated sample
    by sample so the sweep stays click-free."""
    n = int(RATE * duration)
    out = array("h")
    phase = 0.0
    for i in range(n):
        progress = i / n
        hz = start_hz + (end_hz - start_hz) * progress
        if vibrato_hz:
            hz += vibrato_depth * math.sin(2 * math.pi * vibrato_hz * i / RATE)
        phase += hz / RATE
        sample = 1.0 if phase % 1.0 < 0.5 else -1.0
        level = volume * (1.0 - progress if fade else 1.0)
        out.append(int(sample * level * 32767))
    return out.tobytes()


def _noise(duration: float, *, volume: float = 0.5, smooth: float = 0.0) -> bytes:
    """A burst of white noise fading to silence — the universal explosion.
    ``smooth`` (0..1) low-pass filters it: higher sounds deeper/boomier."""
    rng = random.Random(0)  # fixed seed: the same explosion every run
    n = int(RATE * duration)
    out = array("h")
    value = 0.0
    for i in range(n):
        target = rng.uniform(-1.0, 1.0)
        value += (target - value) * (1.0 - smooth)
        level = volume * (1.0 - i / n) ** 2
        out.append(int(value * level * 32767))
    return out.tobytes()


def _notes(frequencies: list[float], note_duration: float, *, volume: float = 0.4) -> bytes:
    """A little tune: square-wave notes played back to back."""
    chunks = [_sweep(note_duration, hz, hz, volume=volume, fade=False) for hz in frequencies]
    return b"".join(chunks)


# ---------------------------------------------------------------------------
# The bank of named effects the sample games share.
# ---------------------------------------------------------------------------


def _build_effects() -> dict[str, bytes]:
    return {
        # pew: a fast falling square sweep
        "laser": _sweep(0.12, 1400, 250, volume=0.35),
        # a longer, meaner zap for the Defender ship
        "zap": _sweep(0.18, 2400, 120, volume=0.35),
        # enemy shot: a soft short blip
        "blip": _sweep(0.06, 700, 500, volume=0.25),
        # small and large explosions: filtered noise bursts
        "boom": _noise(0.3, volume=0.6, smooth=0.55),
        "big_boom": _noise(0.8, volume=0.7, smooth=0.8),
        # the Galaxian dive scream: a falling sweep with heavy vibrato
        "dive": _sweep(0.7, 1900, 500, volume=0.22, vibrato_hz=28, vibrato_depth=300),
        # engine rumble, meant to be looped while thrusting
        "thrust": _noise(0.4, volume=0.16, smooth=0.92),
        # rising arpeggio: wave cleared / bonus
        "fanfare": _notes([262, 330, 392, 523, 659, 784], 0.09),
        # the sad trombone of arcade death
        "game_over": _notes([392, 330, 262, 196], 0.22),
        # four-step invader march (played one note per formation step)
        "march0": _notes([180], 0.09),
        "march1": _notes([160], 0.09),
        "march2": _notes([143], 0.09),
        "march3": _notes([127], 0.09),
    }


class SoundBank:
    """All the kit's sound effects, ready to play by name.

    Create one after ``pygame.init()``. If audio can't be initialized the
    bank disables itself instead of crashing — games still run silently.
    """

    def __init__(self) -> None:
        self.enabled = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._looping: dict[str, pygame.mixer.Channel] = {}
        try:
            # Our sample buffers are 22050 Hz signed 16-bit mono, so the
            # mixer must match; reopen it if pygame.init() chose otherwise.
            if pygame.mixer.get_init() != (RATE, -16, 1):
                pygame.mixer.quit()
                pygame.mixer.init(RATE, -16, 1, buffer=512)
            pygame.mixer.set_num_channels(16)
        except pygame.error:
            return  # no audio device — stay disabled
        self._sounds = {
            name: pygame.mixer.Sound(buffer=data) for name, data in _build_effects().items()
        }
        self.enabled = True

    def play(self, name: str, volume: float = 1.0) -> None:
        """Fire and forget one effect (does nothing if audio is disabled)."""
        if self.enabled:
            sound = self._sounds[name]
            sound.set_volume(volume)
            sound.play()

    def loop(self, name: str) -> None:
        """Start an effect looping (e.g. engine thrust); no-op if already going."""
        if self.enabled and name not in self._looping:
            channel = self._sounds[name].play(loops=-1)
            if channel is not None:
                self._looping[name] = channel

    def stop(self, name: str) -> None:
        """Stop a looping effect started with ``loop()``."""
        channel = self._looping.pop(name, None)
        if channel is not None:
            channel.stop()
