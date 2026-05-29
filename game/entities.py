import math
import random
import pygame
from . import sprites
from .constants import (
    BULLET_W, BULLET_H, BULLET_SPEED, BULLET_COLOR, ENEMY_BULLET_COLOR,
    SCREEN_W, SCREEN_H,
    SOLDIER_HP, SOLDIER_SPEED, SOLDIER_SHOOT_COOLDOWN,
    TURRET_HP, TURRET_SHOOT_COOLDOWN,
    BOSS_HP,
    DRONE_HP, DRONE_SHOOT_COOLDOWN,
    JUMPER_HP, JUMPER_SPEED, JUMPER_JUMP_INTERVAL, JUMPER_JUMP_VY,
    MORTAR_HP, MORTAR_SHOOT_COOLDOWN, MORTAR_SHELL_GRAVITY,
    SNIPER_HP, SNIPER_AIM_FRAMES, SNIPER_COOLDOWN,
    CHARGER_HP, CHARGER_VISION, CHARGER_SPEED,
    BURROWER_HP, BURROWER_SPEED, BURROWER_UNDER_FRAMES, BURROWER_UP_FRAMES,
    CRATE_HP, BARREL_HP,
    KAMIKAZE_HP, KAMIKAZE_TRIGGER, KAMIKAZE_LOCK_FRAMES, KAMIKAZE_DIVE_SPEED,
    KAMIKAZE_HOVER_SPEED,
    BOMBER_HP, BOMBER_SHOOT_COOLDOWN, GRENADE_FUSE, GRENADE_GRAVITY,
    LASER_COLOR, LASER_TRAIL,
    SOLDIER_COLOR, SOLDIER_DARK, TURRET_COLOR, TURRET_DARK, BOSS_COLOR,
    PICKUP_COLOR, GRAVITY, PLAYER_W, PLAYER_H,
    WEAPON_SPREAD, WEAPON_MACHINE, WEAPON_LASER, PICKUP_LIFE, PICKUP_GEM,
    CHECKPOINT_COLOR, CHECKPOINT_ACTIVE,
)


class Bullet:
    def __init__(self, x, y, dx, dy, is_player=True, speed=None, piercing=False):
        if speed is None:
            speed = BULLET_SPEED
        mag = math.hypot(dx, dy)
        if mag == 0:
            dx, dy = 1.0, 0.0
            mag = 1.0
        self.vx = dx / mag * speed
        self.vy = dy / mag * speed
        self.x = float(x)
        self.y = float(y)
        self.is_player = is_player
        self.alive = True
        self.life = 140
        self.piercing = piercing
        self._hit_ids = set() if piercing else None
        self._trail = []

    @property
    def rect(self):
        if self.piercing:
            return pygame.Rect(
                int(self.x - BULLET_W / 2 - 2), int(self.y - BULLET_H / 2 - 1),
                BULLET_W + 4, BULLET_H + 2,
            )
        return pygame.Rect(
            int(self.x - BULLET_W / 2), int(self.y - BULLET_H / 2),
            BULLET_W, BULLET_H,
        )

    def already_hit(self, enemy):
        return self.piercing and id(enemy) in self._hit_ids

    def mark_hit(self, enemy):
        if self.piercing:
            self._hit_ids.add(id(enemy))

    def update(self, level):
        if self.piercing:
            self._trail.append((self.x, self.y))
            if len(self._trail) > 6:
                self._trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            return
        for p in level.platforms:
            if self.rect.colliderect(p):
                self.alive = False
                return
        if self.x < -50 or self.x > level.width + 50 or self.y < -50 or self.y > SCREEN_H + 50:
            self.alive = False

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        if self.piercing:
            # Long oriented streak along velocity direction
            speed = math.hypot(self.vx, self.vy)
            if speed > 0.01:
                dx = self.vx / speed
                dy = self.vy / speed
            else:
                dx, dy = 1.0, 0.0
            # tail end is 24 px behind, head is 6 px ahead
            tail_x = sx - dx * 22
            tail_y = sy - dy * 22
            head_x = sx + dx * 6
            head_y = sy + dy * 6
            # outer glow line
            pygame.draw.line(screen, LASER_TRAIL,
                             (int(tail_x), int(tail_y)),
                             (int(head_x), int(head_y)), 6)
            # core line
            pygame.draw.line(screen, LASER_COLOR,
                             (int(tail_x), int(tail_y)),
                             (int(head_x), int(head_y)), 3)
            # hot core
            pygame.draw.line(screen, (255, 230, 250),
                             (int(sx - dx * 8), int(sy - dy * 8)),
                             (int(head_x), int(head_y)), 1)
            # historical trail dots (positions over past frames)
            for i, (tx, ty) in enumerate(self._trail):
                alpha_i = (i + 1) / max(1, len(self._trail))
                tsx = int(tx - camera.x)
                tsy = int(ty)
                rad = max(1, int(3 * alpha_i))
                pygame.draw.circle(screen, LASER_TRAIL, (tsx, tsy), rad)
            # bright head dot
            pygame.draw.circle(screen, (255, 230, 250),
                               (int(head_x), int(head_y)), 3)
            return
        color = BULLET_COLOR if self.is_player else ENEMY_BULLET_COLOR
        pygame.draw.rect(screen, color,
                         (sx - BULLET_W // 2, sy - BULLET_H // 2, BULLET_W, BULLET_H))


class MortarShell:
    """Parabolic explosive shell from Mortar enemy."""
    R = 6

    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.alive = True
        self.is_player = False
        self.exploded = False
        self.piercing = False
        self.t = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.R), int(self.y - self.R),
                           self.R * 2, self.R * 2)

    def already_hit(self, enemy):
        return False

    def mark_hit(self, enemy):
        pass

    def update(self, level):
        self.t += 1
        self.x += self.vx
        self.vy += MORTAR_SHELL_GRAVITY
        self.y += self.vy
        for p in level.platforms:
            if self.rect.colliderect(p):
                self.alive = False
                self.exploded = True
                return
        if self.x < -50 or self.x > level.width + 50 or self.y > SCREEN_H + 50:
            self.alive = False

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        pygame.draw.circle(screen, (60, 60, 60), (sx, sy), self.R)
        pygame.draw.circle(screen, (180, 180, 60), (sx, sy - 1), self.R - 2)
        pygame.draw.circle(screen, (255, 240, 100),
                           (sx + 1, sy - 2), 2)
        if (self.t // 4) % 2 == 0:
            pygame.draw.circle(screen, (255, 120, 40),
                               (sx, sy - self.R - 2), 2)


class Enemy:
    points = 100

    def __init__(self, x, y, w, h, hp):
        self.x = float(x)
        self.y = float(y)
        self.w = w
        self.h = h
        self.hp = hp
        self.max_hp = hp
        self.alive = True
        self.shoot_timer = random.randint(30, 90)
        self.vy = 0.0
        self.hit_flash = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def hit(self, dmg=1):
        self.hp -= dmg
        self.hit_flash = 5
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def in_view(self, camera):
        return -100 < self.x - camera.x < SCREEN_W + 100

    def update(self, player, level):
        return []

    def draw(self, screen, camera):
        pass

    def draw_flash(self, screen, camera):
        """Overlay a translucent white box during hit_flash frames."""
        if self.hit_flash <= 0:
            return
        sx = int(self.x - camera.x)
        sy = int(self.y)
        alpha = int(80 + (self.hit_flash / 5) * 110)
        flash = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        screen.blit(flash, (sx, sy))
        self.hit_flash -= 1

    def draw_hp_bar(self, screen, camera):
        """Small HP bar above the enemy whenever they've taken damage (multi-HP only)."""
        if self.max_hp <= 1:
            return
        if self.hp >= self.max_hp:
            return  # undamaged — don't clutter screen
        sx = int(self.x - camera.x)
        sy = int(self.y)
        bar_w = max(20, self.w - 4)
        bar_h = 3
        bar_x = sx + (self.w - bar_w) // 2
        bar_y = sy - 7
        # background
        pygame.draw.rect(screen, (60, 20, 20), (bar_x, bar_y, bar_w, bar_h))
        # coloured fill: green → yellow → red
        ratio = max(0.0, self.hp / self.max_hp)
        if ratio > 0.5:
            bar_color = (80, 220, 80)
        elif ratio > 0.25:
            bar_color = (220, 180, 40)
        else:
            bar_color = (220, 60, 60)
        filled = max(1, int(bar_w * ratio))
        pygame.draw.rect(screen, bar_color, (bar_x, bar_y, filled, bar_h))
        # thin border
        pygame.draw.rect(screen, (180, 180, 180), (bar_x, bar_y, bar_w, bar_h), 1)

    def _draw_sprite_centered(self, screen, camera, sprite_name,
                              scale=2, flip_x=False, offset_y=0):
        """Helper: blit a Kenney sprite centred horizontally on the hitbox
        and aligned to its bottom (with optional vertical offset).
        Returns True iff the sprite was drawn, False if missing."""
        spr = sprites.get(sprite_name, scale=scale, flip_x=flip_x)
        if spr is None:
            return False
        sx = int(self.x - camera.x)
        sy = int(self.y)
        x = sx + self.w // 2 - spr.get_width() // 2
        y = sy + self.h - spr.get_height() + offset_y
        screen.blit(spr, (x, y))
        return True


class Soldier(Enemy):
    points = 100

    def __init__(self, x, y):
        super().__init__(x, y, 22, 32, SOLDIER_HP)
        self.dir = -1
        self.anim_frame = 0
        self.moving = False
        self.muzzle_flash = 0

    def _draw_soldier_gun(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        gun_y = sy + 18
        if self.dir == 1:
            gun_x0 = sx + self.w - 2
            gun_x1 = sx + self.w + 8
        else:
            gun_x0 = sx + 2
            gun_x1 = sx - 8
        pygame.draw.line(screen, (45, 45, 55), (gun_x0, gun_y), (gun_x1, gun_y), 3)
        pygame.draw.line(screen, (160, 160, 175),
                         (gun_x0, gun_y - 1), (gun_x1, gun_y - 1), 1)
        if self.muzzle_flash > 0:
            mfx = gun_x1 + (2 if self.dir == 1 else -2)
            pygame.draw.circle(screen, (255, 220, 100), (mfx, gun_y), 4)
            pygame.draw.circle(screen, (255, 160, 40), (mfx, gun_y), 2)

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        if player.x + PLAYER_W / 2 < self.x + self.w / 2:
            self.dir = -1
        else:
            self.dir = 1

        old_x = self.x
        self.x += self.dir * SOLDIER_SPEED * 0.4
        feet = pygame.Rect(int(self.x), int(self.y) + self.h, self.w, 4)
        on_ground_check = any(feet.colliderect(p) for p in level.platforms)
        if not on_ground_check:
            self.x = old_x
            self.moving = False
        else:
            self.moving = True

        self.vy += GRAVITY
        self.y += self.vy
        for p in level.platforms:
            if self.rect.colliderect(p):
                if self.vy > 0:
                    self.y = p.top - self.h
                    self.vy = 0
                elif self.vy < 0:
                    self.y = p.bottom
                    self.vy = 0

        bullets = []
        self.shoot_timer -= 1
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = SOLDIER_SHOOT_COOLDOWN + random.randint(-20, 20)
            tx = (player.x + PLAYER_W / 2) - (self.x + self.w / 2)
            ty = (player.y + PLAYER_H / 2) - (self.y + self.h / 2)
            bullets.append(Bullet(self.x + self.w / 2, self.y + self.h / 2,
                                  tx, ty, is_player=False, speed=4.5))
            self.muzzle_flash = 4
        self.anim_frame += 1
        return bullets

    def draw(self, screen, camera):
        # Try Kenney sprite first
        name = "soldier_walk.png" if self.moving else "soldier_idle.png"
        if self._draw_sprite_centered(screen, camera, name,
                                      scale=1.4,
                                      flip_x=(self.dir == -1)):
            # tiny gun overlay on top of the soldier sprite
            self._draw_soldier_gun(screen, camera)
            return
        sx = int(self.x - camera.x)
        sy = int(self.y)

        # legs (walk anim)
        legs_phase = (self.anim_frame // 6) % 4 if self.moving else 0
        frames = [(0, 5, 4, 1), (2, 3, 2, 3), (4, 1, 0, 5), (2, 3, 2, 3)]
        lx, lh, rx, rh = frames[legs_phase]
        if self.dir == -1:
            lx, rx = rx, lx
        feet_top = sy + 22
        leg_color = (40, 30, 30)
        boot_color = (15, 10, 10)
        pygame.draw.rect(screen, leg_color, (sx + 3 + lx, feet_top, 4, lh + 2))
        pygame.draw.rect(screen, boot_color, (sx + 2 + lx, feet_top + lh + 1, 6, 3))
        pygame.draw.rect(screen, leg_color, (sx + self.w - 7 - rx, feet_top, 4, rh + 2))
        pygame.draw.rect(screen, boot_color, (sx + self.w - 8 - rx, feet_top + rh + 1, 6, 3))

        # body
        pygame.draw.rect(screen, SOLDIER_COLOR, (sx + 2, sy + 9, self.w - 4, 14))
        pygame.draw.rect(screen, (60, 50, 30), (sx + 3, sy + 16, self.w - 6, 2))
        pygame.draw.line(screen, (140, 30, 30),
                         (sx + self.w // 2, sy + 10),
                         (sx + self.w // 2, sy + 22), 1)

        # head
        pygame.draw.rect(screen, (220, 180, 140), (sx + 5, sy + 3, self.w - 10, 6))
        # helmet
        pygame.draw.rect(screen, SOLDIER_DARK, (sx + 3, sy, self.w - 6, 4))
        pygame.draw.rect(screen, (50, 10, 10), (sx + 3, sy + 4, self.w - 6, 1))

        # eye
        eye_x = sx + (self.w - 7 if self.dir == 1 else 5)
        pygame.draw.rect(screen, (35, 35, 35), (eye_x, sy + 5, 2, 2))

        # gun
        gun_y = sy + 14
        if self.dir == 1:
            gun_x0 = sx + self.w - 4
            gun_x1 = sx + self.w + 7
        else:
            gun_x0 = sx + 4
            gun_x1 = sx - 7
        pygame.draw.line(screen, (60, 60, 70), (gun_x0, gun_y), (gun_x1, gun_y), 2)
        pygame.draw.line(screen, (140, 140, 150), (gun_x0, gun_y - 1), (gun_x1, gun_y - 1), 1)

        # muzzle flash
        if self.muzzle_flash > 0:
            mfx = gun_x1 + (2 if self.dir == 1 else -2)
            pygame.draw.circle(screen, (255, 220, 100), (mfx, gun_y), 4)
            pygame.draw.circle(screen, (255, 160, 40), (mfx, gun_y), 2)


class ShieldTrooper(Enemy):
    """Armoured soldier carrying a frontal shield.
    Bullets that arrive from the shield side are deflected — no damage.
    Players must flank or use Spread/Laser to break through."""
    points = 300

    def __init__(self, x, y):
        super().__init__(x, y, 24, 32, 2)
        self.dir = -1          # facing direction
        self.shield_side = -1  # which side (+1 right / -1 left) the shield faces
        self.muzzle_flash = 0
        self.moving = False

    def is_blocked(self, bullet_x):
        """True if a bullet at bullet_x hits the shield (frontal block)."""
        bdir = 1 if bullet_x > self.x + self.w / 2 else -1
        return bdir == self.shield_side

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        pcx = player.x + PLAYER_W / 2
        if pcx < self.x + self.w / 2:
            self.dir = -1
        else:
            self.dir = 1
        self.shield_side = self.dir  # shield always faces the player

        # slow advance
        old_x = self.x
        self.x += self.dir * SOLDIER_SPEED * 0.25
        feet = pygame.Rect(int(self.x), int(self.y) + self.h, self.w, 4)
        on_ground = any(feet.colliderect(p) for p in level.platforms)
        if not on_ground:
            self.x = old_x
            self.moving = False
        else:
            self.moving = True

        self.vy += GRAVITY
        self.y += self.vy
        for p in level.platforms:
            if self.rect.colliderect(p):
                if self.vy > 0:
                    self.y = p.top - self.h
                    self.vy = 0
                elif self.vy < 0:
                    self.y = p.bottom
                    self.vy = 0

        bullets = []
        self.shoot_timer -= 1
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = SOLDIER_SHOOT_COOLDOWN + 50 + random.randint(-20, 20)
            tx = pcx - (self.x + self.w / 2)
            ty = (player.y + PLAYER_H / 2) - (self.y + self.h / 2)
            bullets.append(Bullet(self.x + self.w / 2, self.y + self.h / 2,
                                  tx, ty, is_player=False, speed=4.5))
            self.muzzle_flash = 4
        return bullets

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        # Body — darker blue-grey to distinguish from regular Soldier
        body_col = (55, 75, 155)
        dark_col = (30, 40, 100)
        # legs
        pygame.draw.rect(screen, (30, 30, 50), (sx + 3, sy + 22, 5, 10))
        pygame.draw.rect(screen, (20, 20, 35), (sx + self.w - 8, sy + 22, 5, 10))
        # boots
        pygame.draw.rect(screen, (15, 15, 25), (sx + 2, sy + 30, 7, 3))
        pygame.draw.rect(screen, (15, 15, 25), (sx + self.w - 9, sy + 30, 7, 3))
        # torso
        pygame.draw.rect(screen, body_col, (sx + 2, sy + 9, self.w - 4, 14))
        pygame.draw.rect(screen, dark_col, (sx + 3, sy + 16, self.w - 6, 2))
        # head + helmet
        pygame.draw.rect(screen, (200, 165, 125), (sx + 5, sy + 3, self.w - 10, 6))
        pygame.draw.rect(screen, dark_col, (sx + 3, sy, self.w - 6, 4))
        # visor — blue tinted
        pygame.draw.rect(screen, (60, 100, 200), (sx + 5, sy + 4, self.w - 10, 3))
        # eye
        eye_x = sx + (self.w - 7 if self.dir == 1 else 5)
        pygame.draw.rect(screen, (180, 220, 255), (eye_x, sy + 5, 2, 2))
        # shield on shield_side
        if self.shield_side == 1:
            shx = sx + self.w - 3
        else:
            shx = sx - 7
        pygame.draw.rect(screen, (130, 155, 215), (shx, sy + 2, 7, 26))
        pygame.draw.rect(screen, (80, 100, 180), (shx, sy + 2, 7, 26), 1)
        # shield emblem (cross)
        pygame.draw.rect(screen, (200, 220, 255), (shx + 3, sy + 6, 1, 10))
        pygame.draw.rect(screen, (200, 220, 255), (shx + 1, sy + 10, 5, 1))
        # gun
        gun_y = sy + 14
        if self.dir == 1:
            gun_x0 = sx + self.w - 4
            gun_x1 = sx + self.w + 7
        else:
            gun_x0 = sx + 4
            gun_x1 = sx - 7
        pygame.draw.line(screen, (60, 60, 70), (gun_x0, gun_y), (gun_x1, gun_y), 2)
        pygame.draw.line(screen, (140, 140, 150), (gun_x0, gun_y - 1), (gun_x1, gun_y - 1), 1)
        # muzzle flash
        if self.muzzle_flash > 0:
            mfx = gun_x1 + (2 if self.dir == 1 else -2)
            pygame.draw.circle(screen, (255, 220, 100), (mfx, gun_y), 4)
            pygame.draw.circle(screen, (255, 160, 40), (mfx, gun_y), 2)


class Turret(Enemy):
    points = 200

    def __init__(self, x, y):
        super().__init__(x, y, 36, 28, TURRET_HP)
        self.aim_angle = 0.0
        self.muzzle_flash = 0

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        cx = self.x + self.w / 2
        cy = self.y + 6
        target_angle = math.atan2(
            (player.y + PLAYER_H / 2) - cy,
            (player.x + PLAYER_W / 2) - cx,
        )
        diff = target_angle - self.aim_angle
        while diff > math.pi: diff -= 2 * math.pi
        while diff < -math.pi: diff += 2 * math.pi
        self.aim_angle += max(-0.06, min(0.06, diff))

        bullets = []
        self.shoot_timer -= 1
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = TURRET_SHOOT_COOLDOWN + random.randint(-15, 15)
            dx = math.cos(self.aim_angle)
            dy = math.sin(self.aim_angle)
            bullets.append(Bullet(cx + dx * 14, cy + dy * 14,
                                  dx, dy, is_player=False, speed=5))
            self.muzzle_flash = 5
        return bullets

    def draw(self, screen, camera):
        # Try pixel sprite first (spiked sphere body)
        used_sprite = self._draw_sprite_centered(
            screen, camera, "turret.png", scale=1.5, offset_y=-2)
        sx = int(self.x - camera.x)
        sy = int(self.y)
        if used_sprite:
            # Draw rotating barrel on top of sprite, skip base/dome
            cx = sx + self.w // 2
            cy = sy + 12
            bx = cx + int(math.cos(self.aim_angle) * 16)
            by = cy + int(math.sin(self.aim_angle) * 16)
            bx2 = cx + int(math.cos(self.aim_angle) * 6)
            by2 = cy + int(math.sin(self.aim_angle) * 6)
            pygame.draw.line(screen, (45, 45, 60), (bx2, by2), (bx, by), 5)
            pygame.draw.line(screen, (160, 160, 175), (bx2, by2), (bx, by), 2)
            if self.muzzle_flash > 0:
                mfx = cx + int(math.cos(self.aim_angle) * 19)
                mfy = cy + int(math.sin(self.aim_angle) * 19)
                pygame.draw.circle(screen, (255, 220, 80), (mfx, mfy), 5)
                pygame.draw.circle(screen, (255, 160, 40), (mfx, mfy), 3)
            return
        # base
        pygame.draw.rect(screen, TURRET_COLOR, (sx, sy + 6, self.w, self.h - 6))
        pygame.draw.rect(screen, TURRET_DARK, (sx + 3, sy + 9, self.w - 6, self.h - 14))
        # ridge
        pygame.draw.rect(screen, (110, 110, 130), (sx, sy + 6, self.w, 2))
        # rivets
        for rx in (sx + 4, sx + self.w - 6):
            pygame.draw.rect(screen, (60, 60, 80), (rx, sy + self.h - 5, 2, 2))
        # dome
        cx = sx + self.w // 2
        cy = sy + 6
        pygame.draw.circle(screen, TURRET_COLOR, (cx, cy), 9)
        pygame.draw.circle(screen, TURRET_DARK, (cx, cy), 7)
        pygame.draw.circle(screen, (180, 50, 50), (cx, cy - 1), 3)
        # rotating barrel
        bx = cx + int(math.cos(self.aim_angle) * 16)
        by = cy + int(math.sin(self.aim_angle) * 16)
        bx2 = cx + int(math.cos(self.aim_angle) * 6)
        by2 = cy + int(math.sin(self.aim_angle) * 6)
        pygame.draw.line(screen, (90, 90, 100), (bx2, by2), (bx, by), 5)
        pygame.draw.line(screen, (140, 140, 150), (bx2, by2), (bx, by), 2)
        # muzzle flash
        if self.muzzle_flash > 0:
            mfx = cx + int(math.cos(self.aim_angle) * 19)
            mfy = cy + int(math.sin(self.aim_angle) * 19)
            pygame.draw.circle(screen, (255, 220, 80), (mfx, mfy), 5)
            pygame.draw.circle(screen, (255, 160, 40), (mfx, mfy), 3)


class Drone(Enemy):
    points = 250

    def __init__(self, x, y):
        super().__init__(x, y, 28, 18, DRONE_HP)
        self.spawn_x = float(x)
        self.spawn_y = float(y)
        self.t = random.uniform(0, math.pi * 2)
        self.muzzle_flash = 0

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        self.t += 0.04
        # sine wave around spawn
        self.x = self.spawn_x + math.sin(self.t) * 60
        self.y = self.spawn_y + math.sin(self.t * 1.5) * 20

        bullets = []
        self.shoot_timer -= 1
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = DRONE_SHOOT_COOLDOWN + random.randint(-15, 15)
            tx = (player.x + PLAYER_W / 2) - (self.x + self.w / 2)
            ty = (player.y + PLAYER_H / 2) - (self.y + self.h / 2)
            bullets.append(Bullet(self.x + self.w / 2, self.y + self.h, tx, ty,
                                  is_player=False, speed=4.5))
            self.muzzle_flash = 4
        return bullets

    def draw(self, screen, camera):
        # Sprite version: bat-head from Kenney + tiny rotor blur for motion
        used = self._draw_sprite_centered(
            screen, camera, "drone.png", scale=1.2, offset_y=-2)
        sx = int(self.x - camera.x)
        sy = int(self.y)
        if used:
            # subtle rotor blur for "drone" feel
            pygame.draw.line(screen, (190, 190, 220),
                             (sx - 4, sy - 2), (sx + self.w + 4, sy - 2), 1)
            if self.muzzle_flash > 0:
                mfx = sx + self.w // 2
                mfy = sy + self.h + 2
                pygame.draw.circle(screen, (255, 220, 100), (mfx, mfy), 4)
                pygame.draw.circle(screen, (255, 160, 40), (mfx, mfy), 2)
            return
        # rotor blur top
        rotor_col = (180, 180, 200)
        pygame.draw.line(screen, rotor_col, (sx - 6, sy), (sx + self.w + 6, sy), 2)
        pygame.draw.line(screen, (60, 60, 80), (sx + self.w // 2, sy), (sx + self.w // 2, sy + 4), 1)
        # body (oval-ish)
        pygame.draw.rect(screen, (180, 80, 80), (sx + 2, sy + 4, self.w - 4, self.h - 6))
        pygame.draw.rect(screen, (130, 50, 50), (sx + 2, sy + 4, self.w - 4, 3))
        # eye/sensor
        pygame.draw.rect(screen, (40, 40, 40), (sx + self.w // 2 - 4, sy + 8, 8, 4))
        pygame.draw.rect(screen, (255, 60, 60), (sx + self.w // 2 - 2, sy + 9, 4, 2))
        # legs
        pygame.draw.line(screen, (60, 60, 80),
                         (sx + 4, sy + self.h - 2), (sx + 1, sy + self.h + 2), 2)
        pygame.draw.line(screen, (60, 60, 80),
                         (sx + self.w - 4, sy + self.h - 2),
                         (sx + self.w - 1, sy + self.h + 2), 2)
        # muzzle flash from underside
        if self.muzzle_flash > 0:
            mfx = sx + self.w // 2
            mfy = sy + self.h + 3
            pygame.draw.circle(screen, (255, 220, 100), (mfx, mfy), 4)
            pygame.draw.circle(screen, (255, 160, 40), (mfx, mfy), 2)


class Kamikaze(Enemy):
    """Flying suicide drone. Hovers and drifts toward the player; once the
    player is within KAMIKAZE_TRIGGER (and below it), it locks on with a
    blinking telegraph, then dives along the locked vector and DETONATES on
    contact or when it hits the ground (AoE handled in main). HP=1 — shoot it
    down from range, or dash through the dive (i-frames). Distinct from Drone
    (which hovers and shoots) and Charger (ground rusher)."""
    points = 300

    def __init__(self, x, y):
        super().__init__(x, y, 24, 20, KAMIKAZE_HP)
        self.spawn_y = float(y)
        self.t = random.uniform(0, math.pi * 2)
        self.state = "hover"        # 'hover' | 'lock' | 'dive'
        self.lock_timer = 0
        self.dive_vx = 0.0
        self.dive_vy = 0.0
        self.face = -1
        self.exploded = False       # main reads this to spawn the AoE on ground hits

    def update(self, player, level):
        pcx = player.x + PLAYER_W / 2
        pcy = player.y + PLAYER_H / 2
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2

        if self.state == "hover":
            if not self.in_view(level.camera):
                return []
            self.t += 0.06
            self.y = self.spawn_y + math.sin(self.t) * 10
            if pcx < cx:
                self.x -= KAMIKAZE_HOVER_SPEED
                self.face = -1
            else:
                self.x += KAMIKAZE_HOVER_SPEED
                self.face = 1
            # commit to a dive when the player is close horizontally and below
            if abs(pcx - cx) < KAMIKAZE_TRIGGER and pcy > cy:
                self.state = "lock"
                self.lock_timer = KAMIKAZE_LOCK_FRAMES
            return []

        if self.state == "lock":
            if not self.in_view(level.camera):
                return []
            self.t += 0.2
            self.y = self.spawn_y + math.sin(self.t) * 4
            self.lock_timer -= 1
            if self.lock_timer <= 0:
                tx = pcx - cx
                ty = pcy - cy
                mag = math.hypot(tx, ty) or 1.0
                self.dive_vx = tx / mag * KAMIKAZE_DIVE_SPEED
                self.dive_vy = ty / mag * KAMIKAZE_DIVE_SPEED
                self.face = -1 if self.dive_vx < 0 else 1
                self.state = "dive"
            return []

        # --- dive --- (proceeds even slightly off-screen so the attack lands)
        self.x += self.dive_vx
        self.y += self.dive_vy
        for p in level.platforms:
            if self.rect.colliderect(p):
                self.alive = False
                self.exploded = True   # self-detonation on the ground
                return []
        if self.y > SCREEN_H + 60 or self.x < -60 or self.x > level.width + 60:
            self.alive = False         # flew off without hitting anything
        return []

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        cx = sx + self.w // 2
        cy = sy + self.h // 2

        # dive motion streak behind the body
        if self.state == "dive":
            tail_x = cx - int(self.dive_vx * 2.2)
            tail_y = cy - int(self.dive_vy * 2.2)
            pygame.draw.line(screen, (255, 160, 80), (cx, cy), (tail_x, tail_y), 3)
            pygame.draw.line(screen, (255, 230, 150), (cx, cy), (tail_x, tail_y), 1)

        if not self._draw_sprite_centered(screen, camera, "kamikaze.png",
                                          scale=1.2, offset_y=-2):
            # wings
            wing = (70, 75, 95)
            pygame.draw.polygon(screen, wing,
                                [(cx - 2, cy - 1), (sx - 5, cy - 7), (sx - 1, cy + 3)])
            pygame.draw.polygon(screen, wing,
                                [(cx + 2, cy - 1), (sx + self.w + 5, cy - 7),
                                 (sx + self.w + 1, cy + 3)])
            # metal body
            pygame.draw.ellipse(screen, (40, 42, 52),
                                (sx + 3, sy + 2, self.w - 6, self.h - 3))
            pygame.draw.ellipse(screen, (150, 60, 60),
                                (sx + 4, sy + 3, self.w - 8, self.h - 6))
            pygame.draw.ellipse(screen, (200, 90, 90),
                                (sx + 5, sy + 4, self.w - 10, 3))
            # warhead nose pointing down
            pygame.draw.polygon(screen, (60, 62, 72),
                                [(sx + 5, sy + self.h - 3),
                                 (sx + self.w - 5, sy + self.h - 3),
                                 (cx, sy + self.h + 4)])

        # blinking warning light: slow in hover, fast/bright during lock
        if self.state == "lock":
            on = (self.lock_timer // 3) % 2 == 0
            r = 4 if on else 2
            col = (255, 60, 40) if on else (255, 170, 120)
            pygame.draw.circle(screen, col, (cx, cy - 1), r)
            # target reticle ring telegraphing the imminent dive
            ring = pygame.Surface((40, 40), pygame.SRCALPHA)
            a = 200 if on else 90
            pygame.draw.circle(ring, (255, 50, 40, a), (20, 20), 16, 2)
            screen.blit(ring, (cx - 20, cy - 20))
        else:
            pulse = (math.sin(self.t * 2) + 1) * 0.5
            col = (255, int(80 + 120 * pulse), 40)
            pygame.draw.circle(screen, col, (cx, cy - 1), 2)


class Jumper(Enemy):
    """Frog-like enemy that hops toward the player periodically.
    No ranged attack — pure melee/jump pressure."""
    points = 150

    def __init__(self, x, y):
        super().__init__(x, y, 24, 22, JUMPER_HP)
        self.dir = -1
        self.on_ground = False
        self.jump_timer = JUMPER_JUMP_INTERVAL
        self.squash = 0  # 0..1 squash anim factor when on ground

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []

        if player.x + PLAYER_W / 2 < self.x + self.w / 2:
            self.dir = -1
        else:
            self.dir = 1

        # gravity
        self.vy += GRAVITY
        if self.vy > 14:
            self.vy = 14
        self.y += self.vy

        # vertical collision
        self.on_ground = False
        for p in level.platforms:
            if self.rect.colliderect(p):
                if self.vy > 0:
                    self.y = p.top - self.h
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.y = p.bottom
                    self.vy = 0

        # horizontal step (only when on ground we move while idle, in air keep vx of last jump)
        if self.on_ground:
            if self.squash < 1.0:
                self.squash = min(1.0, self.squash + 0.1)
            self.vx_air = 0
        else:
            self.squash = max(0.0, self.squash - 0.05)

        if not hasattr(self, "vx_air"):
            self.vx_air = 0
        self.x += self.vx_air
        # horizontal collision
        for p in level.platforms:
            if self.rect.colliderect(p):
                if self.vx_air > 0:
                    self.x = p.left - self.w
                elif self.vx_air < 0:
                    self.x = p.right
                self.vx_air = 0

        # jump timer
        if self.on_ground:
            self.jump_timer -= 1
            if self.jump_timer <= 0:
                self.jump_timer = JUMPER_JUMP_INTERVAL + random.randint(-15, 15)
                self.vy = JUMPER_JUMP_VY
                self.vx_air = self.dir * JUMPER_SPEED
                self.squash = 0.0
        return []

    def draw(self, screen, camera):
        # Sprite: 'carrot' character from Kenney. idle on ground, jump in air.
        name = "jumper_jump.png" if not self.on_ground else "jumper_idle.png"
        if self._draw_sprite_centered(screen, camera, name, scale=1.2,
                                      flip_x=(self.dir == -1), offset_y=-2):
            return
        sx = int(self.x - camera.x)
        sy = int(self.y)
        # squash when landing
        squash_h = int(2 * (1.0 - self.squash))
        body_h = self.h - 6 - squash_h
        body_top = sy + 6 + squash_h
        # body
        pygame.draw.rect(screen, (60, 140, 60),
                         (sx + 2, body_top, self.w - 4, body_h))
        pygame.draw.rect(screen, (30, 80, 30),
                         (sx + 2, body_top, self.w - 4, 3))
        # belly
        pygame.draw.rect(screen, (120, 200, 100),
                         (sx + 5, body_top + body_h - 5, self.w - 10, 4))
        # eyes (two big bulgy)
        eye_y = sy + 3 + squash_h // 2
        pygame.draw.rect(screen, (240, 240, 240), (sx + 4, eye_y, 6, 5))
        pygame.draw.rect(screen, (240, 240, 240),
                         (sx + self.w - 10, eye_y, 6, 5))
        # pupils — face the player
        px_off = 2 if self.dir == 1 else 0
        pygame.draw.rect(screen, (20, 20, 20),
                         (sx + 4 + px_off, eye_y + 1, 2, 3))
        pygame.draw.rect(screen, (20, 20, 20),
                         (sx + self.w - 10 + px_off, eye_y + 1, 2, 3))
        # mouth
        pygame.draw.rect(screen, (20, 40, 20),
                         (sx + 8, sy + body_h + 2, self.w - 16, 1))
        # legs — long when airborne, tucked when squashed
        if not self.on_ground:
            pygame.draw.line(screen, (40, 100, 40),
                             (sx + 4, sy + self.h - 4),
                             (sx + 1, sy + self.h + 4), 3)
            pygame.draw.line(screen, (40, 100, 40),
                             (sx + self.w - 4, sy + self.h - 4),
                             (sx + self.w - 1, sy + self.h + 4), 3)
        else:
            pygame.draw.rect(screen, (40, 100, 40),
                             (sx + 2, sy + self.h - 3, 6, 3))
            pygame.draw.rect(screen, (40, 100, 40),
                             (sx + self.w - 8, sy + self.h - 3, 6, 3))


class Mortar(Enemy):
    """Stationary mortar that lobs parabolic shells over walls."""
    points = 300

    def __init__(self, x, y):
        super().__init__(x, y, 30, 24, MORTAR_HP)
        self.aim_t = 0
        self.barrel_angle = -math.pi / 3  # default upward-left

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        # always aim toward player
        tx = (player.x + PLAYER_W / 2) - (self.x + self.w / 2)
        # angle limited so shell goes up & toward
        # we still set barrel visually but actually compute parabolic shot
        if tx < 0:
            self.barrel_angle = -math.pi * 0.65
        else:
            self.barrel_angle = -math.pi * 0.35
        self.aim_t += 1

        shells = []
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = MORTAR_SHOOT_COOLDOWN + random.randint(-20, 20)
            shells.append(self._lob(player))
        return shells

    def _lob(self, player):
        """Compute initial velocity to land near player using ballistic formula."""
        sx0 = self.x + self.w / 2
        sy0 = self.y + 4
        tx = player.x + PLAYER_W / 2
        ty = player.y + PLAYER_H / 2
        dx = tx - sx0
        dy = ty - sy0
        # choose a fixed apex above start: about 110 px high
        apex_h = 110
        # required vy at apex = 0 -> vy_init = -sqrt(2*g*h)
        vy = -math.sqrt(2 * MORTAR_SHELL_GRAVITY * apex_h)
        # time to reach apex
        t_up = -vy / MORTAR_SHELL_GRAVITY
        # then fall to dy from apex (dy is downward in screen coords)
        # distance to fall from apex relative to start = -vy^2/(2g) + dy
        # actually compute total t numerically: 0.5*g*t^2 + vy*t - dy = 0
        a = 0.5 * MORTAR_SHELL_GRAVITY
        b = vy
        c = -dy
        disc = b * b - 4 * a * c
        if disc < 0:
            t_total = t_up * 2
        else:
            t_total = (-b + math.sqrt(disc)) / (2 * a)
            t_total = max(t_total, t_up + 5)
        vx = dx / max(1, t_total)
        # clamp horizontal speed
        vx = max(-6.5, min(6.5, vx))
        return MortarShell(sx0, sy0, vx, vy)

    def draw(self, screen, camera):
        if self._draw_sprite_centered(screen, camera, "mortar.png",
                                      scale=1.4, offset_y=-2):
            sx = int(self.x - camera.x)
            sy = int(self.y)
            # tube overlay on top
            cx = sx + self.w // 2
            cy = sy + 12
            bx = cx + int(math.cos(self.barrel_angle) * 14)
            by = cy + int(math.sin(self.barrel_angle) * 14)
            pygame.draw.line(screen, (45, 45, 60), (cx, cy), (bx, by), 5)
            pygame.draw.line(screen, (160, 160, 175), (cx, cy), (bx, by), 2)
            pygame.draw.circle(screen, (25, 25, 30), (bx, by), 3)
            return
        sx = int(self.x - camera.x)
        sy = int(self.y)
        # base
        pygame.draw.rect(screen, (90, 90, 100),
                         (sx, sy + 10, self.w, self.h - 10))
        pygame.draw.rect(screen, (60, 60, 70),
                         (sx + 3, sy + 14, self.w - 6, self.h - 14))
        # treads / wheels
        for wx in (sx + 4, sx + self.w - 10):
            pygame.draw.rect(screen, (30, 30, 40), (wx, sy + self.h - 6, 6, 5))
            pygame.draw.rect(screen, (60, 60, 70), (wx + 1, sy + self.h - 5, 4, 3))
        # tube
        cx = sx + self.w // 2
        cy = sy + 12
        bx = cx + int(math.cos(self.barrel_angle) * 18)
        by = cy + int(math.sin(self.barrel_angle) * 18)
        pygame.draw.line(screen, (40, 40, 50), (cx, cy), (bx, by), 6)
        pygame.draw.line(screen, (110, 110, 120), (cx, cy), (bx, by), 2)
        # mouth
        pygame.draw.circle(screen, (20, 20, 25), (bx, by), 3)
        # gleam dot
        pygame.draw.rect(screen, (220, 220, 80), (cx - 2, cy - 1, 3, 2))


class Sniper(Enemy):
    """Stationary sniper: shows a red laser sight for SNIPER_AIM_FRAMES,
    then fires one fast bullet along that line. Player has time to hide."""
    points = 400

    def __init__(self, x, y):
        super().__init__(x, y, 28, 28, SNIPER_HP)
        self.aim_timer = 0
        self.locked_dx = 1.0
        self.locked_dy = 0.0
        self.cooldown = SNIPER_COOLDOWN

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        cx = self.x + self.w / 2
        cy = self.y + 6
        bullets = []
        if self.aim_timer > 0:
            self.aim_timer -= 1
            if self.aim_timer == 0:
                # fire along locked direction
                bullets.append(Bullet(cx + self.locked_dx * 14,
                                      cy + self.locked_dy * 14,
                                      self.locked_dx, self.locked_dy,
                                      is_player=False, speed=10))
                self.cooldown = SNIPER_COOLDOWN
        else:
            self.cooldown -= 1
            if self.cooldown <= 0:
                # lock current player position
                tx = (player.x + PLAYER_W / 2) - cx
                ty = (player.y + PLAYER_H / 2) - cy
                mag = math.hypot(tx, ty) or 1
                self.locked_dx = tx / mag
                self.locked_dy = ty / mag
                self.aim_timer = SNIPER_AIM_FRAMES
        return bullets

    def draw(self, screen, camera):
        used = self._draw_sprite_centered(screen, camera, "sniper.png",
                                          scale=1.4, offset_y=-2)
        sx = int(self.x - camera.x)
        sy = int(self.y)
        if used:
            # laser sight + scope dot on top of sprite
            cx = sx + self.w // 2
            cy = sy + 8
            bx = cx + int(self.locked_dx * 10)
            by = cy + int(self.locked_dy * 10)
            pygame.draw.line(screen, (160, 160, 175),
                             (cx, cy), (bx, by), 2)
            pygame.draw.circle(screen, (255, 60, 60), (bx, by), 2)
            if self.aim_timer > 0:
                life_ratio = self.aim_timer / SNIPER_AIM_FRAMES
                end_x = cx + int(self.locked_dx * 600)
                end_y = cy + int(self.locked_dy * 600)
                overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                blink = ((self.aim_timer // 4) % 2 == 0) or life_ratio < 0.25
                col = (255, 60, 60, 180) if blink else (255, 60, 60, 90)
                pygame.draw.line(overlay, col, (cx, cy), (end_x, end_y), 1)
                screen.blit(overlay, (0, 0))
            return
        # tripod legs
        pygame.draw.line(screen, (40, 40, 50),
                         (sx + 6, sy + self.h),
                         (sx + 2, sy + self.h + 4), 2)
        pygame.draw.line(screen, (40, 40, 50),
                         (sx + self.w - 6, sy + self.h),
                         (sx + self.w - 2, sy + self.h + 4), 2)
        # body
        pygame.draw.rect(screen, (60, 70, 80),
                         (sx + 4, sy + 12, self.w - 8, 12))
        pygame.draw.rect(screen, (90, 100, 115),
                         (sx + 4, sy + 12, self.w - 8, 3))
        # scope
        cx = sx + self.w // 2
        cy = sy + 10
        bx = cx + int(self.locked_dx * 10)
        by = cy + int(self.locked_dy * 10)
        pygame.draw.circle(screen, (40, 40, 50), (cx, cy), 5)
        pygame.draw.line(screen, (150, 150, 165), (cx, cy), (bx, by), 3)
        pygame.draw.circle(screen, (255, 60, 60), (bx, by), 1)
        # laser sight while aiming
        if self.aim_timer > 0:
            # pulsing alpha based on remaining time
            life_ratio = self.aim_timer / SNIPER_AIM_FRAMES
            # extend a long ray
            end_x = cx + int(self.locked_dx * 600)
            end_y = cy + int(self.locked_dy * 600)
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            blink = ((self.aim_timer // 4) % 2 == 0) or life_ratio < 0.25
            col = (255, 60, 60, 180) if blink else (255, 60, 60, 90)
            pygame.draw.line(overlay, col, (cx, cy), (end_x, end_y), 1)
            screen.blit(overlay, (0, 0))


class Charger(Enemy):
    """Sees player within CHARGER_VISION, then runs full-speed at them and
    explodes on contact (handled via player collision hit)."""
    points = 250

    def __init__(self, x, y):
        super().__init__(x, y, 28, 28, CHARGER_HP)
        self.dir = -1
        self.state = "idle"   # 'idle' | 'charging' | 'priming'
        self.prime_timer = 0
        self.flash_t = 0

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        # spot player
        pcx = player.x + PLAYER_W / 2
        pcy = player.y + PLAYER_H / 2
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        dist = math.hypot(pcx - cx, pcy - cy)
        if self.state == "idle" and dist < CHARGER_VISION:
            self.state = "priming"
            self.prime_timer = 25
        if self.state == "priming":
            self.flash_t += 1
            self.prime_timer -= 1
            if self.prime_timer <= 0:
                self.state = "charging"

        if self.state == "charging":
            self.dir = -1 if pcx < cx else 1
            old_x = self.x
            self.x += self.dir * CHARGER_SPEED
            feet = pygame.Rect(int(self.x), int(self.y) + self.h, self.w, 4)
            on_ground = any(feet.colliderect(p) for p in level.platforms)
            if not on_ground:
                self.x = old_x
            # gravity
            self.vy += GRAVITY
            self.y += self.vy
            for p in level.platforms:
                if self.rect.colliderect(p):
                    if self.vy > 0:
                        self.y = p.top - self.h
                        self.vy = 0
                    else:
                        self.y = p.bottom
                        self.vy = 0
            self.flash_t += 1
        else:
            # gravity in idle/priming too
            self.vy += GRAVITY
            self.y += self.vy
            for p in level.platforms:
                if self.rect.colliderect(p):
                    if self.vy > 0:
                        self.y = p.top - self.h
                        self.vy = 0
        return []

    def draw(self, screen, camera):
        # angry sprite when active, otherwise idle
        if self.state == "idle":
            name = "charger_idle.png"
        else:
            # blink between idle/angry for visual urgency
            blink = (self.flash_t // 4) % 2 == 0
            name = "charger_angry.png" if blink else "charger_idle.png"
        if self._draw_sprite_centered(screen, camera, name, scale=1.4,
                                      flip_x=(self.dir == -1), offset_y=-2):
            return
        sx = int(self.x - camera.x)
        sy = int(self.y)
        # flashing red body when angry
        if self.state != "idle":
            blink = (self.flash_t // 4) % 2 == 0
            body = (255, 60, 60) if blink else (200, 40, 40)
        else:
            body = (140, 50, 50)
        pygame.draw.rect(screen, body, (sx + 2, sy + 6, self.w - 4, self.h - 6))
        # spikes around the rim
        pygame.draw.polygon(screen, body,
                            [(sx + 2, sy + 6), (sx + 6, sy + 2),
                             (sx + 10, sy + 6)])
        pygame.draw.polygon(screen, body,
                            [(sx + self.w - 10, sy + 6), (sx + self.w - 6, sy + 2),
                             (sx + self.w - 2, sy + 6)])
        pygame.draw.polygon(screen, body,
                            [(sx + self.w // 2 - 4, sy + 6),
                             (sx + self.w // 2, sy + 2),
                             (sx + self.w // 2 + 4, sy + 6)])
        # eye facing dir
        eye_x = sx + self.w // 2 + (4 if self.dir == 1 else -4)
        pygame.draw.rect(screen, (255, 240, 100), (eye_x - 1, sy + 12, 3, 3))
        pygame.draw.rect(screen, (60, 0, 0), (eye_x, sy + 13, 1, 1))
        # treads
        pygame.draw.rect(screen, (30, 30, 35),
                         (sx, sy + self.h - 5, self.w, 5))
        for tx in range(4, self.w, 6):
            pygame.draw.rect(screen, (60, 60, 70),
                             (sx + tx, sy + self.h - 4, 3, 3))


class Burrower(Enemy):
    """Mole that tunnels underground (invulnerable — empty hitbox) tracking the
    player's x, then surfaces to fire one aimed shot before digging back down.
    Only vulnerable while surfaced; telegraphs each emergence with a shaking
    dirt mound."""
    points = 350

    def __init__(self, x, y):
        super().__init__(x, y, 30, 24, BURROWER_HP)
        # desync multiple burrowers so they don't pop in unison
        self.state = "under"
        self.state_timer = BURROWER_UNDER_FRAMES + random.randint(0, 40)
        self.fired = False
        self.dir = -1
        self.anim_t = 0

    @property
    def rect(self):
        # Submerged → zero-area hitbox: bullets and contact pass straight
        # through (this is what makes the Burrower invulnerable underground).
        if self.state == "under":
            return pygame.Rect(int(self.x), int(self.y), 0, 0)
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        self.anim_t += 1
        bullets = []
        pcx = player.x + PLAYER_W / 2
        cx = self.x + self.w / 2
        self.dir = -1 if pcx < cx else 1

        if self.state == "under":
            # tunnel horizontally toward the player
            if cx < pcx - 2:
                self.x += BURROWER_SPEED
            elif cx > pcx + 2:
                self.x -= BURROWER_SPEED
            self.x = max(0.0, min(level.width - self.w, self.x))
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "up"
                self.state_timer = BURROWER_UP_FRAMES
                self.fired = False
        else:  # surfaced — vulnerable, fires once mid-window
            self.state_timer -= 1
            if not self.fired and self.state_timer <= BURROWER_UP_FRAMES // 2:
                self.fired = True
                cy = self.y + 6
                tx = (player.x + PLAYER_W / 2) - cx
                ty = (player.y + PLAYER_H / 2) - cy
                mag = math.hypot(tx, ty) or 1
                dx, dy = tx / mag, ty / mag
                bullets.append(Bullet(cx + dx * 12, cy + dy * 12,
                                      dx, dy, is_player=False, speed=7))
            if self.state_timer <= 0:
                self.state = "under"
                self.state_timer = BURROWER_UNDER_FRAMES
        return bullets

    def _draw_mound(self, screen, sx, ground_y, shake=0):
        ox = random.randint(-shake, shake) if shake else 0
        base = (95, 65, 38)
        rim = (120, 85, 50)
        cxm = sx + self.w // 2 + ox
        pygame.draw.polygon(screen, base, [
            (cxm - 16, ground_y), (cxm, ground_y - 11), (cxm + 16, ground_y)])
        pygame.draw.polygon(screen, rim, [
            (cxm - 16, ground_y), (cxm, ground_y - 11), (cxm + 16, ground_y)], 1)
        for dxo in (-9, -2, 6):
            pygame.draw.rect(screen, (70, 48, 28),
                             (cxm + dxo, ground_y - 4, 3, 3))

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        ground_y = sy + self.h
        if self.state == "under":
            # telegraph: mound shakes harder the closer it is to emerging
            shake = 2 if self.state_timer < 22 else 0
            self._draw_mound(screen, sx, ground_y, shake=shake)
            return
        # surfaced mole body
        body = (96, 64, 40)
        belly = (150, 120, 92)
        pygame.draw.rect(screen, body, (sx + 3, sy + 4, self.w - 6, self.h - 4))
        pygame.draw.rect(screen, body, (sx + 1, sy + 8, self.w - 2, self.h - 8))
        pygame.draw.rect(screen, belly, (sx + 8, sy + 13, self.w - 16, self.h - 13))
        # snout toward the player
        snout_x = sx + (self.w - 7 if self.dir == 1 else 2)
        pygame.draw.rect(screen, (228, 150, 162), (snout_x, sy + 9, 6, 5))
        # eyes
        ey = sy + 8
        pygame.draw.rect(screen, (20, 16, 12), (sx + self.w // 2 - 5, ey, 2, 2))
        pygame.draw.rect(screen, (20, 16, 12), (sx + self.w // 2 + 3, ey, 2, 2))
        # digging claws
        claw = (235, 230, 210)
        cbx = snout_x + (5 if self.dir == 1 else -3)
        for i in range(3):
            pygame.draw.rect(screen, claw, (cbx, sy + self.h - 6 + i, 3, 2))
        # small dirt at the feet
        self._draw_mound(screen, sx, ground_y)


class Crate(Enemy):
    """Static wooden supply crate. Not a real enemy: it never shoots, never
    moves and does no contact damage — but it shares Enemy's rect/hit/flash so
    the existing bullet-collision loop handles it for free. Shoot it once and it
    splinters apart, dropping a guaranteed pickup (weapon / gem / life)."""
    points = 0

    def __init__(self, x, y):
        super().__init__(x, y, 28, 28, CRATE_HP)
        # tiny per-crate variety in the plank tint
        self._tint = random.randint(-12, 12)

    def update(self, player, level):
        return []

    def draw(self, screen, camera):
        if self._draw_sprite_centered(screen, camera, "crate.png", scale=2):
            return
        sx = int(self.x - camera.x)
        sy = int(self.y)
        w, h = self.w, self.h
        t = self._tint
        body = (150 + t, 100 + t, 55 + t // 2)
        light = (185 + t, 135 + t, 80 + t // 2)
        dark = (105 + t, 68 + t, 36 + t // 2)
        # main plank face + bevelled highlight / shadow
        pygame.draw.rect(screen, body, (sx, sy, w, h))
        pygame.draw.rect(screen, light, (sx, sy, w, 3))
        pygame.draw.rect(screen, light, (sx, sy, 3, h))
        pygame.draw.rect(screen, dark, (sx, sy + h - 3, w, 3))
        pygame.draw.rect(screen, dark, (sx + w - 3, sy, 3, h))
        # diagonal cross-braces (classic crate look)
        pygame.draw.line(screen, dark, (sx + 3, sy + 3),
                         (sx + w - 4, sy + h - 4), 2)
        pygame.draw.line(screen, dark, (sx + w - 4, sy + 3),
                         (sx + 3, sy + h - 4), 2)
        # metal corner brackets
        bracket = (70, 72, 80)
        for bx, by in ((sx + 1, sy + 1), (sx + w - 6, sy + 1),
                       (sx + 1, sy + h - 6), (sx + w - 6, sy + h - 6)):
            pygame.draw.rect(screen, bracket, (bx, by, 5, 5))
            pygame.draw.rect(screen, (40, 42, 48), (bx, by, 5, 5), 1)
        pygame.draw.rect(screen, (45, 28, 14), (sx, sy, w, h), 1)


class Barrel(Enemy):
    """Explosive barrel. Like the crate it shares Enemy's hitbox, but when it is
    destroyed main.py detonates it: a radial blast damages every enemy nearby
    (chaining into other barrels) and singes the player if they're too close.
    Pulses a warning glow so the player can read it as 'danger'."""
    points = 0

    def __init__(self, x, y):
        super().__init__(x, y, 24, 32, BARREL_HP)
        self.pulse = random.uniform(0, math.tau)

    def update(self, player, level):
        self.pulse += 0.14
        return []

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        w, h = self.w, self.h
        glow = (math.sin(self.pulse) + 1) * 0.5  # 0..1 hazard pulse
        body = (180, 45, 38)
        light = (228, 92, 70)
        dark = (120, 26, 24)
        # barrel body with rounded-ish top/bottom rims
        pygame.draw.rect(screen, body, (sx + 2, sy + 2, w - 4, h - 4))
        pygame.draw.ellipse(screen, light, (sx + 2, sy, w - 4, 7))
        pygame.draw.ellipse(screen, dark, (sx + 2, sy + h - 7, w - 4, 7))
        # vertical highlight band
        pygame.draw.rect(screen, light, (sx + 5, sy + 4, 3, h - 8))
        # metal hoops
        hoop = (210, 210, 220)
        for hy in (sy + 9, sy + h // 2, sy + h - 12):
            pygame.draw.rect(screen, hoop, (sx + 2, hy, w - 4, 2))
        # hazard chevrons / warning glow that pulses
        warn = (255, int(150 + 90 * glow), 40)
        cxm = sx + w // 2
        my = sy + h // 2
        pygame.draw.polygon(screen, warn, [
            (cxm, my - 6), (cxm + 5, my), (cxm, my + 6), (cxm - 5, my)])
        pygame.draw.polygon(screen, (40, 20, 0), [
            (cxm, my - 6), (cxm + 5, my), (cxm, my + 6), (cxm - 5, my)], 1)
        pygame.draw.rect(screen, (60, 14, 12), (sx + 2, sy + 1, w - 4, h - 2), 1)


class Grenade:
    """Lobbed by Bomber. Parabolic flight, then explodes after fuse expires
    OR on contact with a platform."""
    R = 6

    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.fuse = GRENADE_FUSE
        self.alive = True
        self.exploded = False
        self.is_player = False
        self.piercing = False
        self.t = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.R), int(self.y - self.R),
                           self.R * 2, self.R * 2)

    def already_hit(self, enemy):
        return False

    def mark_hit(self, enemy):
        pass

    def update(self, level):
        self.t += 1
        self.fuse -= 1
        self.x += self.vx
        self.vy += GRENADE_GRAVITY
        self.y += self.vy
        for p in level.platforms:
            if self.rect.colliderect(p):
                # bounce on top once if low vy, else stick
                if self.vy > 0:
                    self.y = p.top - self.R
                    self.vy *= -0.35
                    self.vx *= 0.6
                else:
                    self.vy = 0
        if self.fuse <= 0:
            self.alive = False
            self.exploded = True
            return
        if self.x < -50 or self.x > level.width + 50 or self.y > SCREEN_H + 50:
            self.alive = False

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        pygame.draw.circle(screen, (45, 70, 45), (sx, sy), self.R)
        pygame.draw.circle(screen, (90, 130, 90), (sx, sy - 1), self.R - 2)
        # fuse spark — pulses faster as fuse nears 0
        if (self.t // max(1, self.fuse // 6 + 1)) % 2 == 0:
            pygame.draw.circle(screen, (255, 220, 80),
                               (sx + 2, sy - self.R - 2), 2)
            pygame.draw.circle(screen, (255, 100, 40),
                               (sx + 2, sy - self.R - 3), 1)


class Bomber(Enemy):
    """Hovers like a drone but tosses parabolic grenades."""
    points = 350

    def __init__(self, x, y):
        super().__init__(x, y, 36, 24, BOMBER_HP)
        self.spawn_x = float(x)
        self.spawn_y = float(y)
        self.t = random.uniform(0, math.pi * 2)
        self.cooldown = BOMBER_SHOOT_COOLDOWN + random.randint(-20, 20)

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        self.t += 0.03
        self.x = self.spawn_x + math.sin(self.t) * 80
        self.y = self.spawn_y + math.sin(self.t * 1.7) * 10

        bullets = []
        self.cooldown -= 1
        if self.cooldown <= 0:
            self.cooldown = BOMBER_SHOOT_COOLDOWN + random.randint(-25, 25)
            # parabolic toss toward player
            sx0 = self.x + self.w / 2
            sy0 = self.y + self.h
            tx = player.x + PLAYER_W / 2
            ty = player.y + PLAYER_H / 2
            dx = tx - sx0
            apex_h = 80
            vy = -math.sqrt(2 * GRENADE_GRAVITY * apex_h)
            a = 0.5 * GRENADE_GRAVITY
            b = vy
            c = -(ty - sy0)
            disc = b * b - 4 * a * c
            if disc < 0:
                t_total = -vy / GRENADE_GRAVITY * 2
            else:
                t_total = (-b + math.sqrt(disc)) / (2 * a)
            vx = max(-6.0, min(6.0, dx / max(1, t_total)))
            bullets.append(Grenade(sx0, sy0, vx, vy))
        return bullets

    def draw(self, screen, camera):
        # Big-plane sprite from Pixel Shmup
        used = self._draw_sprite_centered(screen, camera, "ship_big_red.png",
                                          scale=1.6, offset_y=-2)
        sx = int(self.x - camera.x)
        sy = int(self.y)
        if used:
            # rotor blur for motion
            pygame.draw.line(screen, (190, 190, 220),
                             (sx - 4, sy - 1), (sx + self.w + 4, sy - 1), 1)
            return
        # rotor
        pygame.draw.line(screen, (180, 180, 200),
                         (sx - 8, sy), (sx + self.w + 8, sy), 2)
        pygame.draw.line(screen, (60, 60, 80),
                         (sx + self.w // 2, sy),
                         (sx + self.w // 2, sy + 4), 1)
        # body — slightly wider/greener than Drone
        pygame.draw.rect(screen, (90, 140, 80),
                         (sx + 2, sy + 4, self.w - 4, self.h - 6))
        pygame.draw.rect(screen, (60, 100, 60),
                         (sx + 2, sy + 4, self.w - 4, 3))
        # bomb-bay
        pygame.draw.rect(screen, (40, 40, 50),
                         (sx + self.w // 2 - 4, sy + self.h - 5, 8, 4))
        # red sensor
        pygame.draw.rect(screen, (200, 60, 60),
                         (sx + self.w // 2 - 3, sy + 8, 6, 3))
        pygame.draw.rect(screen, (255, 200, 100),
                         (sx + self.w // 2 - 2, sy + 9, 4, 1))


class Boss(Enemy):
    points = 5000

    def __init__(self, x, y):
        super().__init__(x, y, 100, 120, BOSS_HP)
        self.max_hp = BOSS_HP
        self.pattern_timer = 0
        self.player_x = 0.0
        self.player_y = 0.0
        self.muzzle_flash = 0
        self.telegraph = 0  # ticks down before next salvo

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        self.player_x = player.x + PLAYER_W / 2
        self.player_y = player.y + PLAYER_H / 2
        bullets = []
        self.pattern_timer += 1
        self.shoot_timer -= 1
        if self.telegraph > 0:
            self.telegraph -= 1
        elif self.shoot_timer <= 16 and self.shoot_timer > 0:
            # mark telegraph for the upcoming shot
            self.telegraph = self.shoot_timer
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = 28
            phase = (self.pattern_timer // 240) % 2
            cx = self.x + 10
            cy = self.y + self.h / 2
            if phase == 0:
                for ang in (-0.3, -0.1, 0.1, 0.3):
                    dx = math.cos(math.pi + ang)
                    dy = math.sin(math.pi + ang)
                    bullets.append(Bullet(cx, cy, dx, dy, is_player=False, speed=4))
            else:
                tx = self.player_x - cx
                ty = self.player_y - cy
                for spread in (-0.15, 0, 0.15):
                    base = math.atan2(ty, tx)
                    a = base + spread
                    bullets.append(Bullet(cx, cy, math.cos(a), math.sin(a),
                                          is_player=False, speed=4.5))
            self.muzzle_flash = 5
        return bullets

    def draw(self, screen, camera):
        # Pixel boss: scale the 24x24 robot up to fill 100x120 hitbox
        # (scale ~5 → 120×120 which closely matches the hitbox bottom)
        spr = sprites.get("boss.png", scale=5)
        if spr is not None:
            sx = int(self.x - camera.x)
            sy = int(self.y)
            x = sx + self.w // 2 - spr.get_width() // 2
            y = sy + self.h - spr.get_height()
            screen.blit(spr, (x, y))
            # eye telegraph flash (red ring around centre when telegraphing)
            if self.telegraph > 0 and (self.telegraph // 3) % 2 == 0:
                pygame.draw.circle(screen, (255, 80, 80),
                                   (sx + self.w // 2, sy + self.h // 2 - 6),
                                   16, 3)
            # gun-port muzzle flashes
            if self.muzzle_flash > 0:
                pygame.draw.circle(screen, (255, 220, 100),
                                   (sx - 6, sy + 66), 6)
                pygame.draw.circle(screen, (255, 160, 40),
                                   (sx - 6, sy + 66), 3)
                pygame.draw.circle(screen, (255, 220, 100),
                                   (sx - 6, sy + 86), 6)
                pygame.draw.circle(screen, (255, 160, 40),
                                   (sx - 6, sy + 86), 3)
            return
        sx = int(self.x - camera.x)
        sy = int(self.y)
        # body
        pygame.draw.rect(screen, BOSS_COLOR, (sx, sy + 8, self.w, self.h - 8))
        pygame.draw.rect(screen, (60, 20, 60), (sx, sy + 8, self.w, 8))
        pygame.draw.rect(screen, (60, 20, 60), (sx, sy + self.h - 18, self.w, 6))
        # plate seams
        for i in range(3):
            yy = sy + 26 + i * 22
            pygame.draw.rect(screen, (60, 20, 60), (sx + 4, yy, self.w - 8, 3))
        # vertical groove
        pygame.draw.line(screen, (60, 20, 60),
                         (sx + self.w // 2, sy + 16),
                         (sx + self.w // 2, sy + self.h - 18), 1)
        # eye socket
        eye_cx = sx + self.w // 2
        eye_cy = sy + 38
        pygame.draw.rect(screen, (30, 10, 30),
                         (eye_cx - 18, eye_cy - 14, 36, 28))
        pygame.draw.rect(screen, (15, 5, 15),
                         (eye_cx - 18, eye_cy - 14, 36, 4))
        # iris (tracks player) — flashes red when telegraphing next shot
        iris_dx = max(-7, min(7, (self.player_x - (self.x + self.w / 2)) / 25))
        iris_dy = max(-5, min(5, (self.player_y - (self.y + 38)) / 25))
        if self.telegraph > 0 and (self.telegraph // 3) % 2 == 0:
            outer = (255, 60, 60)
            inner = (255, 230, 80)
        else:
            outer = (255, 255, 80)
            inner = (255, 50, 50)
        pygame.draw.circle(screen, outer,
                           (eye_cx + int(iris_dx), eye_cy + int(iris_dy)), 8)
        pygame.draw.circle(screen, inner,
                           (eye_cx + int(iris_dx), eye_cy + int(iris_dy)), 4)
        pygame.draw.circle(screen, (60, 0, 0),
                           (eye_cx + int(iris_dx), eye_cy + int(iris_dy)), 1)
        # gun ports (left side - faces player)
        pygame.draw.rect(screen, (40, 10, 40), (sx - 12, sy + 60, 14, 12))
        pygame.draw.rect(screen, (40, 10, 40), (sx - 12, sy + 80, 14, 12))
        # muzzle flash from gun ports
        if self.muzzle_flash > 0:
            pygame.draw.circle(screen, (255, 220, 100), (sx - 14, sy + 66), 5)
            pygame.draw.circle(screen, (255, 220, 100), (sx - 14, sy + 86), 5)
            pygame.draw.circle(screen, (255, 160, 40), (sx - 14, sy + 66), 3)
            pygame.draw.circle(screen, (255, 160, 40), (sx - 14, sy + 86), 3)
        # antennae / spikes on top
        pygame.draw.rect(screen, (60, 20, 60), (sx + 8, sy, 4, 10))
        pygame.draw.rect(screen, (60, 20, 60), (sx + self.w - 12, sy, 4, 10))
        pygame.draw.rect(screen, (255, 50, 50), (sx + 9, sy - 2, 2, 3))
        pygame.draw.rect(screen, (255, 50, 50), (sx + self.w - 11, sy - 2, 2, 3))


PICKUP_STYLES = {
    WEAPON_SPREAD: {"color": (100, 220, 255), "outline": (40, 100, 130),
                    "letter": "S", "text_color": (20, 30, 80)},
    WEAPON_MACHINE: {"color": (255, 220, 80), "outline": (140, 110, 30),
                     "letter": "M", "text_color": (60, 40, 0)},
    WEAPON_LASER: {"color": (255, 100, 100), "outline": (140, 30, 30),
                   "letter": "L", "text_color": (60, 0, 0)},
    PICKUP_LIFE: {"color": (120, 240, 120), "outline": (40, 130, 50),
                  "letter": "1UP", "text_color": (10, 50, 10),
                  "sprite": "pickup_heart.png"},
    PICKUP_GEM: {"color": (180, 120, 255), "outline": (90, 50, 150),
                 "letter": "$", "text_color": (40, 0, 70),
                 "sprite": "pickup_gem.png"},
}


class MechBoss(Enemy):
    points = 10000

    def __init__(self, x, y):
        super().__init__(x, y, 120, 140, BOSS_HP * 2)
        self.max_hp = BOSS_HP * 2
        self.spawn_x = float(x)
        self.player_x = 0.0
        self.player_y = 0.0
        self.muzzle_flash = 0
        self.telegraph = 0
        self.t = 0

    @property
    def hp_ratio(self):
        return max(0.0, self.hp / self.max_hp)

    def update(self, player, level):
        if not self.in_view(level.camera):
            return []
        self.player_x = player.x + PLAYER_W / 2
        self.player_y = player.y + PLAYER_H / 2
        self.t += 1
        sway = 0.012 if self.hp_ratio > 0.3 else 0.025
        self.x = self.spawn_x + math.sin(self.t * sway) * 70

        bullets = []
        self.shoot_timer -= 1
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1
        if self.telegraph > 0:
            self.telegraph -= 1
        elif 0 < self.shoot_timer <= 14:
            self.telegraph = self.shoot_timer

        if self.shoot_timer <= 0:
            cx = self.x + 10
            cy = self.y + self.h / 2
            if self.hp_ratio > 0.6:
                self.shoot_timer = 32
                for ang in (-0.4, -0.2, 0, 0.2, 0.4):
                    dx = math.cos(math.pi + ang)
                    dy = math.sin(math.pi + ang)
                    bullets.append(Bullet(cx, cy, dx, dy, is_player=False, speed=4))
            elif self.hp_ratio > 0.3:
                self.shoot_timer = 22
                tx = self.player_x - cx
                ty = self.player_y - cy
                base = math.atan2(ty, tx)
                for spread in (-0.20, 0, 0.20):
                    a = base + spread
                    bullets.append(Bullet(cx, cy, math.cos(a), math.sin(a),
                                          is_player=False, speed=5))
                if self.t % 110 < 2:
                    for n in range(8):
                        a = n * math.pi / 4
                        bullets.append(Bullet(cx, cy, math.cos(a), math.sin(a),
                                              is_player=False, speed=3))
            else:
                self.shoot_timer = 12
                tx = self.player_x - cx
                ty = self.player_y - cy
                base = math.atan2(ty, tx) + random.uniform(-0.18, 0.18)
                bullets.append(Bullet(cx, cy, math.cos(base), math.sin(base),
                                      is_player=False, speed=6))
            self.muzzle_flash = 4
        return bullets

    def draw(self, screen, camera):
        # Mech boss uses the bigger Kenney robot (mechboss.png)
        spr = sprites.get("mechboss.png", scale=6)
        if spr is not None:
            sx = int(self.x - camera.x)
            sy = int(self.y)
            x = sx + self.w // 2 - spr.get_width() // 2
            y = sy + self.h - spr.get_height()
            screen.blit(spr, (x, y))
            # health LED bar overlay at top
            hp_w = self.w - 16
            pygame.draw.rect(screen, (30, 0, 0), (sx + 8, sy + 20, hp_w, 4))
            if self.hp_ratio > 0.6:
                bar_col = (255, 50, 50)
            elif self.hp_ratio > 0.3:
                bar_col = (255, 30, 30)
            else:
                bar_col = (255, 0, 0)
            pygame.draw.rect(screen, bar_col,
                             (sx + 8, sy + 20, int(hp_w * self.hp_ratio), 4))
            # telegraph eye flash
            if self.telegraph > 0 and (self.telegraph // 2) % 2 == 0:
                pygame.draw.circle(screen, (255, 240, 240),
                                   (sx + self.w // 2, sy + 50), 18, 4)
            # gun port flashes
            if self.muzzle_flash > 0:
                for fx, fy in [(sx - 8, sy + 81), (sx - 8, sy + 106)]:
                    pygame.draw.circle(screen, (255, 220, 100), (fx, fy), 6)
                    pygame.draw.circle(screen, (255, 160, 40), (fx, fy), 3)
            return
        sx = int(self.x - camera.x)
        sy = int(self.y)
        # body
        pygame.draw.rect(screen, (130, 130, 150), (sx, sy + 10, self.w, self.h - 10))
        pygame.draw.rect(screen, (60, 60, 80), (sx, sy + 10, self.w, 10))
        pygame.draw.rect(screen, (50, 50, 70), (sx, sy + self.h - 20, self.w, 8))
        for i in range(3):
            yy = sy + 28 + i * 25
            pygame.draw.rect(screen, (80, 80, 100), (sx + 6, yy, self.w - 12, 4))
        pygame.draw.line(screen, (60, 60, 80),
                         (sx + self.w // 2, sy + 24),
                         (sx + self.w // 2, sy + self.h - 22), 2)
        # eye / cockpit
        eye_cx = sx + self.w // 2
        eye_cy = sy + 42
        pygame.draw.rect(screen, (20, 20, 30),
                         (eye_cx - 22, eye_cy - 14, 44, 28))
        pygame.draw.rect(screen, (15, 15, 25),
                         (eye_cx - 22, eye_cy - 14, 44, 4))
        iris_dx = max(-9, min(9, (self.player_x - (self.x + self.w / 2)) / 22))
        iris_dy = max(-6, min(6, (self.player_y - (self.y + eye_cy - sy)) / 22))
        if self.hp_ratio > 0.6:
            iris_outer = (255, 255, 80)
            iris_inner = (255, 50, 50)
        elif self.hp_ratio > 0.3:
            iris_outer = (255, 180, 40)
            iris_inner = (255, 30, 30)
        else:
            iris_outer = (255, 100, 100)
            iris_inner = (255, 0, 0)
        # telegraph flash
        if self.telegraph > 0 and (self.telegraph // 2) % 2 == 0:
            iris_outer = (255, 240, 240)
            iris_inner = (255, 80, 80)
        pygame.draw.circle(screen, iris_outer,
                           (eye_cx + int(iris_dx), eye_cy + int(iris_dy)), 9)
        pygame.draw.circle(screen, iris_inner,
                           (eye_cx + int(iris_dx), eye_cy + int(iris_dy)), 5)
        pygame.draw.circle(screen, (40, 0, 0),
                           (eye_cx + int(iris_dx), eye_cy + int(iris_dy)), 2)
        # gun ports (left side facing player)
        pygame.draw.rect(screen, (40, 40, 55), (sx - 14, sy + 75, 16, 14))
        pygame.draw.rect(screen, (40, 40, 55), (sx - 14, sy + 100, 16, 14))
        pygame.draw.rect(screen, (40, 40, 55), (sx + self.w - 2, sy + 75, 16, 14))
        if self.muzzle_flash > 0:
            for fx, fy in [(sx - 16, sy + 81), (sx - 16, sy + 106)]:
                pygame.draw.circle(screen, (255, 220, 100), (fx, fy), 5)
                pygame.draw.circle(screen, (255, 160, 40), (fx, fy), 3)
        # antennae / spikes
        pygame.draw.rect(screen, (60, 60, 80), (sx + 12, sy, 4, 14))
        pygame.draw.rect(screen, (60, 60, 80), (sx + self.w - 16, sy, 4, 14))
        pygame.draw.rect(screen, (255, 80, 80), (sx + 13, sy - 4, 2, 5))
        pygame.draw.rect(screen, (255, 80, 80), (sx + self.w - 15, sy - 4, 2, 5))
        # chest LED bar
        hp_w = self.w - 16
        pygame.draw.rect(screen, (30, 0, 0), (sx + 8, sy + 20, hp_w, 4))
        pygame.draw.rect(screen, iris_inner,
                         (sx + 8, sy + 20, int(hp_w * self.hp_ratio), 4))


class Pickup:
    def __init__(self, x, y, kind=WEAPON_SPREAD):
        self.x = float(x)
        self.y = float(y)
        self.w = 26 if kind == PICKUP_LIFE else 22
        self.h = 22
        self.kind = kind
        self.alive = True
        self.bob = 0
        self._spin_t = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y) + int(math.sin(self.bob / 15) * 3),
                           self.w, self.h)

    def update(self):
        self.bob += 1
        self._spin_t += 0.08

    def draw(self, screen, camera, font):
        sx = int(self.x - camera.x)
        sy = int(self.y) + int(math.sin(self.bob / 15) * 3)
        style = PICKUP_STYLES.get(self.kind, PICKUP_STYLES[WEAPON_SPREAD])
        # glow
        pulse = (math.sin(self._spin_t) + 1) / 2
        glow_r = int(14 + pulse * 4)
        glow = pygame.Surface((glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA)
        gc = (*style["color"], int(60 + pulse * 40))
        pygame.draw.circle(glow, gc, (glow_r + 1, glow_r + 1), glow_r)
        screen.blit(glow,
                    (sx + self.w // 2 - glow_r - 1, sy + self.h // 2 - glow_r - 1))
        # Kenney pixel sprite (heart / gem) takes priority over the box+letter.
        spr = None
        sprite_name = style.get("sprite")
        if sprite_name:
            spr = sprites.get(sprite_name, scale=1.5)
        if spr is not None:
            screen.blit(spr,
                        (sx + self.w // 2 - spr.get_width() // 2,
                         sy + self.h // 2 - spr.get_height() // 2))
            return
        # procedural fallback: box + letter
        pygame.draw.rect(screen, style["color"], (sx, sy, self.w, self.h))
        pygame.draw.rect(screen, style["outline"], (sx, sy, self.w, self.h), 2)
        small = self.kind in (PICKUP_LIFE, PICKUP_GEM)
        f = pygame.font.Font(None, 20 if small else font.get_height() + 2)
        if small:
            t = f.render(style["letter"], True, style["text_color"])
        else:
            t = font.render(style["letter"], True, style["text_color"])
        screen.blit(t,
                    (sx + self.w // 2 - t.get_width() // 2,
                     sy + self.h // 2 - t.get_height() // 2))


class Particle:
    def __init__(self, x, y, vx, vy, color, life):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.18
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        ratio = self.life / self.max_life
        size = max(1, int(5 * ratio))
        pygame.draw.rect(screen, self.color, (sx, sy, size, size))


class ScorePopup:
    """Floating '+250' text above a killed enemy. `points` may be int (renders
    as '+250') or arbitrary string ('1UP', 'NEW WEAPON')."""
    LIFE = 50

    def __init__(self, x, y, points, color=(255, 240, 120)):
        self.x = float(x)
        self.y = float(y)
        self.vy = -1.6
        self.life = self.LIFE
        self.color = color
        if isinstance(points, str):
            self.text = points
        else:
            self.text = f"+{points}"
        self.alive = True

    def update(self):
        self.y += self.vy
        self.vy *= 0.92  # decelerate
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def draw(self, screen, camera, font):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        ratio = self.life / self.LIFE
        alpha = int(255 * min(1.0, ratio * 2))
        # render text on its own surface for alpha control
        t = font.render(self.text, True, self.color)
        t = t.convert_alpha()
        t.set_alpha(alpha)
        screen.blit(t, (sx - t.get_width() // 2, sy))


class Checkpoint:
    """Respawn flag — once player overlaps, becomes active and remembered."""
    W = 18
    H = 44

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.active = False
        self.t = 0
        self.alive = True  # never removed, just toggled

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def update(self):
        self.t += 1

    def draw(self, screen, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y)
        if sx + 40 < 0 or sx > SCREEN_W:
            return
        # pole
        pygame.draw.rect(screen, (180, 180, 200), (sx + 2, sy, 3, self.H))
        pygame.draw.rect(screen, (120, 120, 140), (sx + 2, sy, 1, self.H))
        # base
        pygame.draw.rect(screen, (90, 90, 100), (sx, sy + self.H - 4, 18, 4))
        # flag — waves slightly
        wave = math.sin(self.t / 8) * 2
        flag_color = CHECKPOINT_ACTIVE if self.active else CHECKPOINT_COLOR
        pygame.draw.polygon(screen, flag_color, [
            (sx + 5, sy + 4),
            (sx + 18 + int(wave), sy + 9),
            (sx + 5, sy + 14),
        ])
        outline = (40, 80, 30) if self.active else (130, 110, 30)
        pygame.draw.polygon(screen, outline, [
            (sx + 5, sy + 4),
            (sx + 18 + int(wave), sy + 9),
            (sx + 5, sy + 14),
        ], 1)
        # glow pulse when active
        if self.active:
            r = 8 + int((math.sin(self.t / 6) + 1) * 3)
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (120, 240, 120, 90), (r, r), r)
            screen.blit(surf, (sx + 9 - r, sy + 9 - r))
