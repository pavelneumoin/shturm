"""On-screen virtual controls for touch devices (VK Mini App on phone).

Maps multi-finger touches in three regions to virtual key presses:
    - left half  : virtual D-pad (sets K_LEFT/K_RIGHT/K_UP/K_DOWN)
    - jump pad   : sets K_z
    - shoot pad  : sets K_x

Also accepts mouse clicks as a single-finger touch for desktop testing.
"""
import math
import pygame
from .constants import SCREEN_W, SCREEN_H


class TouchControls:
    DPAD_CX = 90
    DPAD_CY = SCREEN_H - 80
    DPAD_R = 60
    DPAD_DEAD = 16

    JUMP_CX = SCREEN_W - 170
    JUMP_CY = SCREEN_H - 80
    JUMP_R = 38

    SHOOT_CX = SCREEN_W - 75
    SHOOT_CY = SCREEN_H - 80
    SHOOT_R = 42

    DASH_CX = SCREEN_W - 132
    DASH_CY = SCREEN_H - 156
    DASH_R = 30

    PAUSE_CX = SCREEN_W - 26
    PAUSE_CY = 16
    PAUSE_R = 14

    def __init__(self):
        self.fingers = {}
        self.virtual = set()
        self.touch_seen = False
        # one-shot flag for pause button: outer code reads + clears
        self.pause_tapped = False

    def begin(self, fid, x, y):
        self.touch_seen = True
        # check for pause-button hit on touchdown
        if math.hypot(x - self.PAUSE_CX, y - self.PAUSE_CY) < self.PAUSE_R + 6:
            self.pause_tapped = True
            return
        self.fingers[fid] = (x, y)
        self._recompute()

    def consume_pause_tap(self):
        v = self.pause_tapped
        self.pause_tapped = False
        return v

    def end(self, fid):
        self.fingers.pop(fid, None)
        self._recompute()

    def move(self, fid, x, y):
        if fid in self.fingers:
            self.fingers[fid] = (x, y)
            self._recompute()

    def clear(self):
        self.fingers.clear()
        self.virtual.clear()

    def _recompute(self):
        self.virtual.clear()
        for x, y in self.fingers.values():
            dx = x - self.DPAD_CX
            dy = y - self.DPAD_CY
            if math.hypot(dx, dy) < self.DPAD_R + 30:
                if dx < -self.DPAD_DEAD:
                    self.virtual.add(pygame.K_LEFT)
                if dx > self.DPAD_DEAD:
                    self.virtual.add(pygame.K_RIGHT)
                if dy < -self.DPAD_DEAD:
                    self.virtual.add(pygame.K_UP)
                if dy > self.DPAD_DEAD:
                    self.virtual.add(pygame.K_DOWN)
                continue
            if math.hypot(x - self.JUMP_CX, y - self.JUMP_CY) < self.JUMP_R + 12:
                self.virtual.add(pygame.K_z)
                continue
            if math.hypot(x - self.SHOOT_CX, y - self.SHOOT_CY) < self.SHOOT_R + 12:
                self.virtual.add(pygame.K_x)
                continue
            if math.hypot(x - self.DASH_CX, y - self.DASH_CY) < self.DASH_R + 10:
                self.virtual.add(pygame.K_c)
                continue

    def is_pressed(self, key):
        return key in self.virtual

    def draw_pause_button(self, screen):
        """Draw the pause icon in the top-right corner (always visible)."""
        cx, cy, r = self.PAUSE_CX, self.PAUSE_CY, self.PAUSE_R
        overlay = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (0, 0, 0, 140), (r + 2, r + 2), r)
        pygame.draw.circle(overlay, (255, 255, 255, 170), (r + 2, r + 2), r, 2)
        # two vertical bars (pause symbol)
        bar_w = 3
        bar_h = r
        pygame.draw.rect(overlay, (255, 255, 255, 220),
                         (r + 2 - 5, r + 2 - bar_h // 2, bar_w, bar_h))
        pygame.draw.rect(overlay, (255, 255, 255, 220),
                         (r + 2 + 2, r + 2 - bar_h // 2, bar_w, bar_h))
        screen.blit(overlay, (cx - r - 2, cy - r - 2))

    def draw(self, screen):
        if not self.touch_seen:
            return
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        # D-pad ring
        self._dot(overlay, self.DPAD_CX, self.DPAD_CY, self.DPAD_R,
                  outline=(255, 255, 255, 110), thickness=3)
        self._dot(overlay, self.DPAD_CX, self.DPAD_CY, self.DPAD_R // 3,
                  fill=(255, 255, 255, 50))
        # arrows
        for ang, key in (
            (math.pi, pygame.K_LEFT),
            (0, pygame.K_RIGHT),
            (-math.pi / 2, pygame.K_UP),
            (math.pi / 2, pygame.K_DOWN),
        ):
            x = self.DPAD_CX + int(math.cos(ang) * (self.DPAD_R - 10))
            y = self.DPAD_CY + int(math.sin(ang) * (self.DPAD_R - 10))
            col = (255, 240, 120, 220) if self.is_pressed(key) else (255, 255, 255, 170)
            pygame.draw.circle(overlay, col, (x, y), 6)

        # Jump pad
        jcol_outline = (140, 240, 255, 140)
        jcol_fill = (140, 240, 255, 90) if self.is_pressed(pygame.K_z) else (140, 240, 255, 30)
        self._dot(overlay, self.JUMP_CX, self.JUMP_CY, self.JUMP_R,
                  fill=jcol_fill, outline=jcol_outline, thickness=3)

        # Shoot pad
        scol_outline = (255, 120, 120, 140)
        scol_fill = (255, 120, 120, 90) if self.is_pressed(pygame.K_x) else (255, 120, 120, 30)
        self._dot(overlay, self.SHOOT_CX, self.SHOOT_CY, self.SHOOT_R,
                  fill=scol_fill, outline=scol_outline, thickness=3)

        # Dash pad (cyan, smaller, up between jump & fire)
        dcol_outline = (140, 225, 255, 140)
        dcol_fill = (140, 225, 255, 95) if self.is_pressed(pygame.K_c) else (140, 225, 255, 28)
        self._dot(overlay, self.DASH_CX, self.DASH_CY, self.DASH_R,
                  fill=dcol_fill, outline=dcol_outline, thickness=3)

        screen.blit(overlay, (0, 0))

        f = pygame.font.Font(None, 22)
        fd = pygame.font.Font(None, 18)
        td = fd.render("DASH", True, (255, 255, 255))
        screen.blit(td, (self.DASH_CX - td.get_width() // 2,
                         self.DASH_CY - td.get_height() // 2))
        for cx, cy, label, col in (
            (self.JUMP_CX, self.JUMP_CY, "JUMP", (255, 255, 255)),
            (self.SHOOT_CX, self.SHOOT_CY, "FIRE", (255, 255, 255)),
        ):
            t = f.render(label, True, col)
            screen.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))

    @staticmethod
    def _dot(surf, cx, cy, r, fill=None, outline=None, thickness=2):
        if fill is not None:
            pygame.draw.circle(surf, fill, (cx, cy), r)
        if outline is not None:
            pygame.draw.circle(surf, outline, (cx, cy), r, thickness)


class CombinedKeys:
    """Wrap pygame.key.get_pressed() AND TouchControls so player.update sees both."""
    def __init__(self, real, touch):
        self.real = real
        self.touch = touch

    def __getitem__(self, k):
        try:
            r = bool(self.real[k])
        except (IndexError, KeyError):
            r = False
        return r or self.touch.is_pressed(k)
