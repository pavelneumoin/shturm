"""Procedurally synthesised 8-bit style sound effects.
No external WAV files — generates raw int16 samples at startup and wraps
them as pygame.mixer.Sound via in-memory buffer. Works in pygbag too."""
import math
import struct
import random
import pygame

SAMPLE_RATE = 22050


def _to_int16(samples):
    out = bytearray()
    for s in samples:
        v = max(-1.0, min(1.0, s))
        out += struct.pack('<h', int(v * 30000))
    return bytes(out)


def _square(freq, duration, decay=1.0, vol=0.7):
    n = int(SAMPLE_RATE * duration)
    period = max(2, int(SAMPLE_RATE / max(freq, 1)))
    return [vol * ((1 - i / n) ** decay) * (1 if (i % period) < period // 2 else -1)
            for i in range(n)]


def _slide(f0, f1, duration, decay=1.0, vol=0.7, square=True):
    n = int(SAMPLE_RATE * duration)
    out = []
    phase = 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * i / n
        amp = vol * ((1 - i / n) ** decay)
        if square:
            out.append(amp if phase < 0.5 else -amp)
        else:
            out.append(amp * math.sin(phase * 2 * math.pi))
        phase += f / SAMPLE_RATE
        phase -= int(phase)
    return out


def _noise(duration, decay=2.0, vol=0.7, lp=1.0):
    n = int(SAMPLE_RATE * duration)
    rng = random.Random(1234)
    prev = 0.0
    out = []
    for i in range(n):
        target = rng.random() * 2 - 1
        prev = prev * (1 - lp) + target * lp
        out.append(vol * ((1 - i / n) ** decay) * prev)
    return out


def _mix(*lists):
    n = max(len(s) for s in lists)
    out = [0.0] * n
    for s in lists:
        for i in range(len(s)):
            out[i] += s[i]
    peak = max((abs(x) for x in out), default=1) or 1
    return [x / peak for x in out]


class SoundBank:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            self.enabled = True
        except Exception as e:
            print(f"[sounds] mixer init failed: {e}")
            return
        try:
            recipes = {
                'shoot':   _slide(900, 600, 0.07, decay=1.4, vol=0.35),
                'enemy':   _slide(450, 280, 0.10, decay=1.4, vol=0.30),
                'jump':    _slide(330, 700, 0.18, decay=0.5, vol=0.35),
                'hit':     _noise(0.10, decay=2.5, vol=0.5, lp=0.6),
                'kill':    _mix(_noise(0.20, decay=2.0, vol=0.45, lp=0.4),
                                _slide(800, 200, 0.20, decay=1.0, vol=0.3)),
                'death':   _slide(700, 80, 0.55, decay=0.4, vol=0.55),
                'pickup':  _mix(_slide(500, 1200, 0.22, decay=0.4, vol=0.4),
                                _slide(800, 1500, 0.22, decay=0.5, vol=0.25)),
                'boss':    _mix(_noise(0.9, decay=1.3, vol=0.55, lp=0.3),
                                _slide(400, 60, 0.9, decay=0.5, vol=0.45)),
                'dash':    _mix(_noise(0.14, decay=2.2, vol=0.30, lp=0.7),
                                _slide(1200, 500, 0.12, decay=1.0, vol=0.18)),
                'select':  _slide(600, 900, 0.10, decay=0.7, vol=0.4),
                'powerup': _mix(_slide(400, 800, 0.15, decay=0.5, vol=0.35),
                                _slide(800, 1400, 0.15, decay=0.5, vol=0.25)),
            }
            for name, samples in recipes.items():
                self.sounds[name] = pygame.mixer.Sound(buffer=_to_int16(samples))
        except Exception as e:
            print(f"[sounds] generation failed: {e}")
            self.enabled = False
            self.sounds = {}

    def play(self, name):
        if not self.enabled or getattr(self, 'muted', False):
            return
        s = self.sounds.get(name)
        if s is None:
            return
        try:
            s.play()
        except Exception:
            pass

    def set_muted(self, muted):
        self.muted = bool(muted)
