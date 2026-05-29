"""Sprite cache for Kenney CC0 pixel art assets.

The runtime loads each PNG once, scales it up using NEAREST (chunky pixels
preserved), and caches it. Mirrored variants are computed on demand —
Kenney's character sprites all face forward so we manually flip for direction.

Sprites live in `assets/sprites/`. The build_sprite_pack.py script seeds that
folder from the raw Kenney packs."""
import os
import pygame


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITE_DIR = os.path.join(_ROOT, "assets", "sprites")


# Each cached image is keyed by (name, scale, flip_x). The unscaled raw is
# stored under (name, 1, False); we derive scaled/flipped variants from it.
_CACHE = {}
# Some sprites might be missing on disk in a hostile environment — flag them
# once so callers can degrade gracefully (e.g. fall back to procedural draw).
_MISSING = set()


def _load_raw(name):
    if name in _MISSING:
        return None
    key = (name, 1, False)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    path = os.path.join(SPRITE_DIR, name)
    if not os.path.isfile(path):
        _MISSING.add(name)
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
    except Exception:
        _MISSING.add(name)
        return None
    _CACHE[key] = img
    return img


def get(name, scale=2, flip_x=False):
    """Return a cached pygame Surface for the given sprite. None if missing."""
    raw = _load_raw(name)
    if raw is None:
        return None
    key = (name, scale, flip_x)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    surf = raw
    if scale != 1:
        new_size = (int(raw.get_width() * scale),
                    int(raw.get_height() * scale))
        surf = pygame.transform.scale(surf, new_size)
    if flip_x:
        surf = pygame.transform.flip(surf, True, False)
    _CACHE[key] = surf
    return surf


def has(name):
    """True iff `name.png` is loadable."""
    return _load_raw(name) is not None


def blit_centered(screen, sprite_name, x, y, scale=2, flip_x=False):
    """Blit a sprite centred on (x, y). No-op if missing."""
    s = get(sprite_name, scale=scale, flip_x=flip_x)
    if s is None:
        return
    screen.blit(s,
                (int(x - s.get_width() // 2),
                 int(y - s.get_height() // 2)))


def blit_topleft(screen, sprite_name, x, y, scale=2, flip_x=False):
    """Blit a sprite by top-left coordinates."""
    s = get(sprite_name, scale=scale, flip_x=flip_x)
    if s is None:
        return
    screen.blit(s, (int(x), int(y)))


def silhouette(sprite_name, scale=2, flip_x=False,
               color=(255, 255, 255), alpha=180):
    """Return a same-shape surface filled with `color` (used for hit flash)."""
    base = get(sprite_name, scale=scale, flip_x=flip_x)
    if base is None:
        return None
    mask = pygame.mask.from_surface(base)
    surf = mask.to_surface(setcolor=color + (alpha,), unsetcolor=(0, 0, 0, 0))
    return surf
