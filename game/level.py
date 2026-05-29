import math
import random
import pygame
from . import sprites
from .constants import (
    SCREEN_W, SCREEN_H, GROUND_Y,
    PLAYER_W,
)
from .leveldef import LevelDef, Theme


TILE = 18  # Kenney pixel-platformer tile size; scaled 2x for rendering


class Camera:
    def __init__(self, level_width):
        self.x = 0.0
        self.level_width = level_width

    def reset(self, level_width):
        self.x = 0.0
        self.level_width = level_width

    def follow(self, player):
        target = player.x + PLAYER_W / 2 - SCREEN_W / 2
        target = max(0.0, min(self.level_width - SCREEN_W, target))
        self.x += (target - self.x) * 0.18
        if abs(target - self.x) < 0.5:
            self.x = target


class MovablePlatform:
    def __init__(self, cfg):
        self.x = float(cfg["x"])
        self.y_min = cfg["y_min"]
        self.y_max = cfg["y_max"]
        self.w = cfg["w"]
        self.h = cfg["h"]
        self.axis = cfg.get("axis", "y")
        self.speed = cfg.get("speed", 1.0)
        self.t = float(cfg.get("phase", 0.0)) * 2 * math.pi
        self._y = (self.y_min + self.y_max) / 2

    def update(self):
        self.t += 0.018 * self.speed
        if self.axis == "y":
            mid = (self.y_min + self.y_max) / 2
            amp = (self.y_max - self.y_min) / 2
            self._y = mid + math.sin(self.t) * amp

    @property
    def y(self):
        return self._y

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self._y), self.w, self.h)

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self._y)
        if sx + self.w < 0 or sx > SCREEN_W:
            return
        # cable up
        pygame.draw.line(screen, (60, 60, 75),
                         (sx + self.w // 2, 0), (sx + self.w // 2, sy), 1)
        # platform body
        pygame.draw.rect(screen, (90, 90, 110), (sx, sy, self.w, self.h))
        pygame.draw.rect(screen, (160, 160, 180), (sx, sy, self.w, 4))
        pygame.draw.rect(screen, (50, 50, 65), (sx, sy + self.h - 2, self.w, 2))
        # rivets
        for rx in (sx + 4, sx + self.w - 6):
            pygame.draw.rect(screen, (30, 30, 40), (rx, sy + self.h - 5, 2, 2))
        # warning stripes
        for i in range(0, self.w, 8):
            pygame.draw.rect(screen, (220, 200, 60), (sx + i, sy + 5, 4, 2))


class AmbientParticle:
    __slots__ = ("x", "y", "vx", "vy", "t", "kind", "color", "size", "phase")

    def __init__(self, x, y, kind):
        self.x = float(x)
        self.y = float(y)
        self.kind = kind
        self.t = random.uniform(0, math.pi * 2)
        self.phase = random.uniform(0, math.pi * 2)
        if kind == "leaves":
            self.vx = random.uniform(-0.3, -0.05)
            self.vy = random.uniform(0.3, 0.7)
            self.color = random.choice([
                (140, 200, 80), (180, 220, 80),
                (220, 160, 60), (220, 110, 50),
            ])
            self.size = random.randint(2, 4)
        elif kind == "fireflies":
            self.vx = random.uniform(-0.4, 0.4)
            self.vy = random.uniform(-0.2, 0.2)
            self.color = (255, 230, 120)
            self.size = random.randint(1, 2)
        elif kind == "sparks":
            self.vx = random.uniform(-0.3, 0.3)
            self.vy = random.uniform(0.6, 1.4)
            self.color = random.choice([
                (255, 200, 80), (255, 150, 60), (255, 100, 40),
            ])
            self.size = random.randint(1, 2)
        else:
            self.vx = self.vy = 0
            self.color = (255, 255, 255)
            self.size = 1

    def update(self):
        self.t += 0.06
        self.x += self.vx
        self.y += self.vy
        if self.kind == "leaves":
            # gentle sway
            self.x += math.sin(self.t) * 0.4
        elif self.kind == "fireflies":
            self.x += math.sin(self.t + self.phase) * 0.6
            self.y += math.cos(self.t * 1.3 + self.phase) * 0.4


class Weather:
    """Theme-driven atmospheric overlay drawn in FRONT of the action — purely
    cosmetic, no gameplay effect. Each kind keeps a tiny list of [x,y,a,b]
    records so the whole system stays allocation-light:
      rain   — diagonal streaks + occasional lightning flash (jungle)
      drip   — water drops falling from the cave ceiling, splashing on the floor
      clouds — soft cloud puffs drifting across the sunset sky
      alarm  — slow pulsing red vignette (base under assault)
    """

    def __init__(self, kind):
        self.kind = kind
        self.t = 0
        self.flash = 0.0                      # lightning brightness (decays)
        self.flash_cooldown = random.randint(180, 480)
        self.parts = []
        self._seed()

    def _seed(self):
        if self.kind == "rain":
            for _ in range(70):
                self.parts.append([
                    random.uniform(0, SCREEN_W),
                    random.uniform(0, SCREEN_H),
                    random.uniform(7.0, 11.0),     # fall speed
                    random.randint(6, 11),         # streak length
                ])
        elif self.kind == "clouds":
            for _ in range(6):
                w = random.randint(70, 130)
                self.parts.append([
                    random.uniform(-120, SCREEN_W),
                    random.uniform(18, 150),
                    random.uniform(0.25, 0.7),     # drift speed
                    w,                             # width
                ])
        # "drip" spawns dynamically; "alarm" needs no particles

    def update(self):
        self.t += 1
        if self.kind == "rain":
            for d in self.parts:
                d[1] += d[2]
                d[0] -= 1.5                        # wind slant
                if d[1] > SCREEN_H:
                    d[0] = random.uniform(0, SCREEN_W)
                    d[1] = random.uniform(-20, -2)
            if self.flash > 0:
                self.flash *= 0.80
                if self.flash < 0.03:
                    self.flash = 0.0
            else:
                self.flash_cooldown -= 1
                if self.flash_cooldown <= 0:
                    self.flash = 1.0
                    self.flash_cooldown = random.randint(240, 600)
        elif self.kind == "clouds":
            for c in self.parts:
                c[0] += c[2]
                if c[0] > SCREEN_W + 130:
                    c[0] = -c[3] - random.uniform(0, 80)
                    c[1] = random.uniform(18, 150)
        elif self.kind == "drip":
            # d[3] == -1 → still falling; >= 0 → splashing with N frames left
            if random.random() < 0.05 and len(self.parts) < 40:
                self.parts.append([random.uniform(0, SCREEN_W), 60.0,
                                   random.uniform(1.6, 2.6), -1.0])
            for d in self.parts:
                if d[3] >= 0:
                    d[3] -= 1
                else:
                    d[2] += 0.18                   # gravity
                    d[1] += d[2]
                    if d[1] >= GROUND_Y - 2:
                        d[1] = GROUND_Y - 2
                        d[3] = 7                   # begin splash
            self.parts = [d for d in self.parts if d[3] != 0]

    def draw(self, screen, camera):
        if self.kind == "rain":
            for d in self.parts:
                x, y = int(d[0]), int(d[1])
                pygame.draw.line(screen, (150, 170, 210),
                                 (x, y), (x - 2, y + d[3]), 1)
            if self.flash > 0:
                ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                ov.fill((205, 215, 255, int(150 * self.flash)))
                screen.blit(ov, (0, 0))
        elif self.kind == "clouds":
            for c in self.parts:
                self._draw_cloud(screen, int(c[0]), int(c[1]), int(c[3]))
        elif self.kind == "drip":
            for d in self.parts:
                x, y, splash = int(d[0]), int(d[1]), d[3]
                if splash >= 0:
                    r = 2 + (7 - int(splash))
                    pygame.draw.arc(screen, (150, 185, 215),
                                    (x - r, y - 2, r * 2, 5), 3.5, 5.9, 1)
                else:
                    pygame.draw.line(screen, (165, 195, 225),
                                     (x, y), (x, y + 4), 1)
        elif self.kind == "alarm":
            pulse = (math.sin(self.t * 0.05) + 1) / 2
            if pulse > 0.55:
                ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                a = int(55 * (pulse - 0.55) / 0.45)
                ov.fill((185, 30, 22, a))
                screen.blit(ov, (0, 0))

    def _draw_cloud(self, screen, x, y, w):
        h = max(16, w // 4)
        surf = pygame.Surface((w + 24, h + 16), pygame.SRCALPHA)
        col = (236, 234, 245, 165)
        for ex, ey, ew, eh in (
            (0, h // 2, w // 2, h // 2),
            (w // 4, 0, w // 2, h),
            (w // 2, h // 3, w // 2 + 8, h // 2 + 4),
        ):
            pygame.draw.ellipse(surf, col, (ex, ey, ew, eh))
        screen.blit(surf, (x, y))


class Level:
    def __init__(self, level_def: LevelDef):
        self.def_ = level_def
        self.width = level_def.width
        self.theme = level_def.theme
        self.static_platforms = []
        self.movables = []
        self.platforms = []
        self.enemy_spawns = list(level_def.enemy_spawns)
        self.pickup_spawns = list(level_def.pickup_spawns)
        self.boss_spawn = level_def.boss_spawn
        self.camera = Camera(self.width)
        self._sky_cache = None
        self._stars = []
        self.ambient_particles = []
        self._seed_ambient()
        weather_kind = getattr(self.theme, 'weather', None)
        self.weather = Weather(weather_kind) if weather_kind else None
        if getattr(self.theme, 'has_stars', False):
            self._seed_stars()
        self._build()
        self._refresh_platforms()

    def _seed_ambient(self):
        kind = self.theme.ambient
        if kind is None:
            return
        count = 24 if kind != "fireflies" else 18
        for _ in range(count):
            x = random.uniform(0, SCREEN_W)
            if kind == "leaves":
                y = random.uniform(0, SCREEN_H - 100)
            elif kind == "fireflies":
                y = random.uniform(60, SCREEN_H - 100)
            elif kind == "sparks":
                y = random.uniform(0, 80)
            else:
                y = random.uniform(0, SCREEN_H)
            self.ambient_particles.append(AmbientParticle(x, y, kind))

    def _seed_stars(self):
        """Seed a parallax starfield for the SKY stage."""
        for _ in range(90):
            self._stars.append({
                'x': random.uniform(0, max(SCREEN_W, self.width * 0.12)),
                'y': random.uniform(10, SCREEN_H - 120),
                'parallax': random.uniform(0.04, 0.14),
                'size': random.choice([1, 1, 1, 2, 2]),
                'twinkle': random.uniform(0, math.pi * 2),
                'speed': random.uniform(1.5, 3.5),
            })

    def _build(self):
        floor_h = SCREEN_H - GROUND_Y
        for x0, x1 in self.def_.floor_strips:
            self.static_platforms.append(
                pygame.Rect(x0, GROUND_Y, x1 - x0, floor_h))
        for fx, fy, fw in self.def_.floats:
            self.static_platforms.append(pygame.Rect(fx, fy, fw, 16))
        if self.theme.has_ceiling:
            for cx0, cx1 in self.def_.ceiling_strips:
                self.static_platforms.append(
                    pygame.Rect(cx0, 0, cx1 - cx0, 60))
        for cfg in self.def_.movables:
            self.movables.append(MovablePlatform(cfg))

    def _refresh_platforms(self):
        self.platforms = self.static_platforms + [m.rect for m in self.movables]

    def update(self):
        for m in self.movables:
            m.update()
        self._refresh_platforms()
        self._update_ambient()
        if self.weather is not None:
            self.weather.update()

    def draw_weather(self, screen, camera):
        """Foreground atmospheric overlay (rain/lightning/drips/clouds/alarm).
        Drawn by main.py after the world + entities so it sits on top."""
        if self.weather is not None:
            self.weather.draw(screen, camera)

    def _update_ambient(self):
        kind = self.theme.ambient
        if kind is None:
            return
        for p in self.ambient_particles:
            p.update()
        # Re-spawn particles that drift off-screen (ambient is screen-local, not world)
        for i, p in enumerate(self.ambient_particles):
            wrap = False
            if kind == "leaves":
                if p.y > SCREEN_H - 60 or p.x < -10:
                    wrap = True
            elif kind == "fireflies":
                if not (-20 < p.x < SCREEN_W + 20 and 40 < p.y < SCREEN_H - 80):
                    wrap = True
            elif kind == "sparks":
                if p.y > SCREEN_H - 40:
                    wrap = True
            if wrap:
                self.ambient_particles[i] = self._respawn_ambient(kind)

    def _respawn_ambient(self, kind):
        if kind == "leaves":
            return AmbientParticle(random.uniform(0, SCREEN_W) + 30,
                                   random.uniform(-20, 20), kind)
        if kind == "fireflies":
            return AmbientParticle(random.uniform(0, SCREEN_W),
                                   random.uniform(60, SCREEN_H - 100), kind)
        if kind == "sparks":
            return AmbientParticle(random.uniform(0, SCREEN_W),
                                   random.uniform(-10, 30), kind)
        return AmbientParticle(0, 0, kind)

    def _make_sky(self):
        s = pygame.Surface((SCREEN_W, SCREEN_H))
        t_top = self.theme.sky_top
        t_bot = self.theme.sky_bot
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            c = (
                int(t_top[0] + (t_bot[0] - t_top[0]) * t),
                int(t_top[1] + (t_bot[1] - t_top[1]) * t),
                int(t_top[2] + (t_bot[2] - t_top[2]) * t),
            )
            pygame.draw.line(s, c, (0, y), (SCREEN_W, y))
        return s

    def draw(self, screen, camera):
        if self._sky_cache is None:
            self._sky_cache = self._make_sky()
        screen.blit(self._sky_cache, (0, 0))

        # parallax star layer (SKY stage only)
        if self._stars:
            t = pygame.time.get_ticks() / 1000.0
            for star in self._stars:
                sx = int((star['x'] - camera.x * star['parallax']) % SCREEN_W)
                sy = int(star['y'])
                twinkle = (math.sin(t * star['speed'] + star['twinkle']) + 1) / 2
                brightness = int(150 + twinkle * 105)
                # warm star tint (slightly orange/pink for sunset sky)
                col = (brightness,
                       int(brightness * 0.85),
                       int(brightness * 0.7 + 30))
                pygame.draw.rect(screen, col, (sx, sy, star['size'], star['size']))
                if star['size'] >= 2 and twinkle > 0.75:
                    # bright stars get a tiny cross glow
                    pygame.draw.rect(screen, col, (sx - 1, sy, 1, star['size']))
                    pygame.draw.rect(screen, col, (sx + star['size'], sy, 1, star['size']))

        # parallax mountains
        far_off = -int(camera.x * 0.25) % 320
        for i in range(-1, SCREEN_W // 320 + 2):
            mx = i * 320 - far_off
            pygame.draw.polygon(screen, self.theme.mountain_far, [
                (mx, GROUND_Y),
                (mx + 80, 220),
                (mx + 160, 260),
                (mx + 240, 200),
                (mx + 320, GROUND_Y),
            ])
        near_off = -int(camera.x * 0.5) % 240
        for i in range(-1, SCREEN_W // 240 + 2):
            mx = i * 240 - near_off
            pygame.draw.polygon(screen, self.theme.mountain_near, [
                (mx, GROUND_Y),
                (mx + 60, 280),
                (mx + 180, 250),
                (mx + 240, GROUND_Y),
            ])

        # ceiling decorations (stalactites) for caves
        if self.theme.has_ceiling:
            self._draw_stalactites(screen, camera)

        # ambient particles (mostly background layer)
        self._draw_ambient(screen)

        # platforms — tile-based if sprites available, else flat rectangle
        tile_top_spr = sprites.get(self.theme.tile_top, scale=2) \
            if self.theme.tile_top else None
        tile_mid_spr = sprites.get(self.theme.tile_mid, scale=2) \
            if self.theme.tile_mid else None
        ts = tile_top_spr.get_width() if tile_top_spr else 36  # 18*2
        for p in self.static_platforms:
            sx = p.x - int(camera.x)
            if sx + p.width < 0 or sx > SCREEN_W:
                continue
            # ceiling rectangle?
            if p.y == 0 and self.theme.has_ceiling:
                pygame.draw.rect(screen, self.theme.ceiling_color,
                                 (sx, 0, p.width, p.height))
                pygame.draw.rect(screen, self.theme.ceiling_top,
                                 (sx, p.height - 4, p.width, 4))
                continue
            if tile_top_spr is not None and tile_mid_spr is not None:
                self._draw_tiled_platform(screen, p, sx,
                                          tile_top_spr, tile_mid_spr, ts)
            else:
                pygame.draw.rect(screen, self.theme.ground,
                                 (sx, p.y, p.width, p.height))
                pygame.draw.rect(screen, self.theme.ground_top,
                                 (sx, p.y, p.width, 6))
                for tx in range(0, p.width, 28):
                    pygame.draw.line(screen, (40, 25, 10),
                                     (sx + tx, p.y + 6),
                                     (sx + tx, p.y + p.height), 1)

        # movable platforms (with their cables) drawn after static
        for m in self.movables:
            m.draw(screen, camera)

        # fog overlay for caves
        if self.theme.fog:
            fog = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            fog.fill((0, 0, 0, 50))
            screen.blit(fog, (0, 0))

    def _draw_ambient(self, screen):
        kind = self.theme.ambient
        if kind is None:
            return
        for p in self.ambient_particles:
            sx = int(p.x)
            sy = int(p.y)
            if kind == "fireflies":
                # pulsing glow
                pulse = (math.sin(p.t) + 1) / 2
                r = max(2, int(p.size + pulse * 2))
                surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(surf,
                                   (p.color[0], p.color[1], p.color[2], 120),
                                   (r + 1, r + 1), r)
                screen.blit(surf, (sx - r, sy - r))
                pygame.draw.rect(screen, p.color, (sx, sy, 1, 1))
            elif kind == "leaves":
                # tiny rotating square
                tilt = int(math.sin(p.t * 0.7) * 2)
                pygame.draw.rect(screen, p.color,
                                 (sx + tilt, sy, p.size, p.size))
            elif kind == "sparks":
                pygame.draw.rect(screen, p.color,
                                 (sx, sy, p.size, p.size))
                # short tail
                tail_col = (max(40, p.color[0] - 80),
                            max(20, p.color[1] - 80),
                            max(10, p.color[2] - 80))
                pygame.draw.rect(screen, tail_col,
                                 (sx, sy - 2, p.size, 2))

    def _draw_tiled_platform(self, screen, p, sx, top_spr, mid_spr, ts):
        """Tile a Kenney sprite across a platform rect. Top row uses tile_top,
        rows below use tile_mid. Sprites are 18×18 → drawn at 36×36 (2x)."""
        # how many columns of tiles cover this platform
        cols = (p.width + ts - 1) // ts
        # how many rows we need: 1 top row + enough mid to cover height
        rows = max(1, (p.height + ts - 1) // ts)
        for col in range(cols):
            x = sx + col * ts
            if x + ts < 0 or x > SCREEN_W:
                continue
            for row in range(rows):
                y = p.y + row * ts
                spr = top_spr if row == 0 else mid_spr
                screen.blit(spr, (x, y))

    def _draw_stalactites(self, screen, camera):
        # Static positions across the level so they appear at consistent spots
        spacing = 80
        offset = -int(camera.x) % spacing
        ceiling_h = 60
        for i in range(-1, SCREEN_W // spacing + 2):
            sx = i * spacing - offset
            tip_h = 12 + ((i * 7 + 13) % 14)
            base_w = 14 + ((i * 5) % 6)
            color = self.theme.ceiling_top
            pygame.draw.polygon(screen, color, [
                (sx, ceiling_h),
                (sx + base_w, ceiling_h),
                (sx + base_w // 2, ceiling_h + tip_h),
            ])
            pygame.draw.polygon(screen, self.theme.ceiling_color, [
                (sx + 2, ceiling_h),
                (sx + base_w - 2, ceiling_h),
                (sx + base_w // 2, ceiling_h + tip_h - 3),
            ])
