"""Generate a 256x256 ШТУРМ icon programmatically.

Run from project root:
    python tools/make_icon.py

Produces `build/web/icon-256.png` and `assets/icon-256.png`. Designed to look
good in VK Mini Apps store listing — bold, high-contrast, pixel art.
"""
import os
import sys
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def make_icon(size=256):
    pygame.init()
    surf = pygame.Surface((size, size))

    # 1) Background: vertical gradient (sunset/dusk feel)
    for y in range(size):
        t = y / size
        r = int(40 + (180 - 40) * t)
        g = int(20 + (60 - 20) * t)
        b = int(60 + (90 - 60) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (size, y))

    # 2) Skyline / mountains
    pygame.draw.polygon(surf, (60, 30, 70),
                        [(0, 180), (50, 130), (110, 160),
                         (160, 110), (220, 150), (256, 130),
                         (256, 256), (0, 256)])
    pygame.draw.polygon(surf, (40, 20, 50),
                        [(0, 210), (40, 180), (90, 200),
                         (140, 170), (200, 200), (256, 180),
                         (256, 256), (0, 256)])

    # 3) Ground band
    pygame.draw.rect(surf, (60, 40, 30), (0, 220, size, 36))
    pygame.draw.rect(surf, (90, 60, 40), (0, 220, size, 6))

    # 4) Pixel soldier silhouette (centred, larger)
    cx = size // 2
    body_top = 110
    # legs
    pygame.draw.rect(surf, (35, 35, 50), (cx - 14, body_top + 70, 10, 28))
    pygame.draw.rect(surf, (35, 35, 50), (cx + 4, body_top + 70, 10, 28))
    pygame.draw.rect(surf, (15, 15, 25), (cx - 16, body_top + 95, 14, 6))
    pygame.draw.rect(surf, (15, 15, 25), (cx + 2, body_top + 95, 14, 6))
    # body
    pygame.draw.rect(surf, (60, 220, 80), (cx - 18, body_top + 24, 36, 50))
    pygame.draw.rect(surf, (180, 140, 60),
                     (cx - 17, body_top + 50, 34, 4))  # belt
    # head
    pygame.draw.rect(surf, (220, 180, 140),
                     (cx - 12, body_top + 8, 24, 18))
    # helmet
    pygame.draw.rect(surf, (30, 100, 40), (cx - 14, body_top, 28, 12))
    pygame.draw.rect(surf, (60, 220, 80), (cx - 10, body_top - 2, 20, 2))
    # eye
    pygame.draw.rect(surf, (30, 30, 30), (cx + 4, body_top + 12, 4, 4))
    # gun + arm extended right
    pygame.draw.line(surf, (60, 220, 80),
                     (cx + 14, body_top + 36),
                     (cx + 36, body_top + 36), 8)
    pygame.draw.line(surf, (50, 50, 60),
                     (cx + 36, body_top + 36),
                     (cx + 64, body_top + 36), 8)
    pygame.draw.line(surf, (110, 110, 120),
                     (cx + 36, body_top + 34),
                     (cx + 64, body_top + 34), 3)
    # muzzle flash
    pygame.draw.circle(surf, (255, 240, 120),
                       (cx + 70, body_top + 36), 10)
    pygame.draw.circle(surf, (255, 200, 60),
                       (cx + 70, body_top + 36), 6)
    pygame.draw.circle(surf, (255, 80, 30),
                       (cx + 70, body_top + 36), 3)

    # 5) Title
    pygame.font.init()
    font = pygame.font.Font(None, 48)
    title = font.render("SHTURM", True, (250, 80, 80))
    # white shadow
    sh = font.render("SHTURM", True, (10, 10, 20))
    surf.blit(sh, (cx - title.get_width() // 2 + 2, 30 + 2))
    surf.blit(title, (cx - title.get_width() // 2, 30))

    # 6) Border frame
    pygame.draw.rect(surf, (250, 80, 80), (0, 0, size, size), 4)
    pygame.draw.rect(surf, (40, 10, 10), (4, 4, size - 8, size - 8), 1)
    return surf


def main():
    surf = make_icon(256)
    out_dirs = [
        os.path.join(ROOT, "assets"),
        os.path.join(ROOT, "build", "web"),
    ]
    for d in out_dirs:
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "icon-256.png")
        pygame.image.save(surf, path)
        print(f"wrote {path}")
    pygame.quit()


if __name__ == "__main__":
    main()
