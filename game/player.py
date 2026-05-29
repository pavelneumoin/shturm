import math
import pygame
from . import sprites
from .constants import (
    PLAYER_W, PLAYER_H, PLAYER_DUCK_VISUAL_H, PLAYER_SPEED, JUMP_VELOCITY,
    GRAVITY, MAX_FALL, INVINCIBLE_FRAMES, SHOOT_COOLDOWN,
    SHOOT_COOLDOWN_MACHINE, SHOOT_COOLDOWN_LASER, LASER_BULLET_SPEED,
    SCREEN_H, DASH_SPEED, DASH_DURATION, DASH_COOLDOWN,
    PLAYER_COLOR, PLAYER_HELMET, PLAYER_GUN,
    WEAPON_NORMAL, WEAPON_SPREAD, WEAPON_MACHINE, WEAPON_LASER,
)


# initial ammo per pickup of each weapon. NORMAL is infinite (not in dict).
WEAPON_AMMO = {
    WEAPON_SPREAD: 60,
    WEAPON_MACHINE: 80,
    WEAPON_LASER: 30,
}


class Player:
    COYOTE_FRAMES = 6   # can still jump this many frames after leaving ground
    JUMP_CUT_DAMP = 0.45  # if jump released during ascent, multiply vy by this

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.aim = (1, 0)
        self.on_ground = False
        self.ducking = False
        self.weapon = WEAPON_NORMAL
        self.ammo = 0  # not used for NORMAL (infinite)
        self.shoot_timer = 0
        self.invincible = 0
        self.dead = False
        self._jump_held = False
        self._was_jump_held = False
        self.anim_frame = 0
        self.just_jumped = False
        self.muzzle_timer = 0
        self.coyote_timer = 0     # frames since left ground (0 if grounded)
        self.jump_buffer = 0      # remaining frames where buffered jump can still apply
        # dash / dodge-roll (v0.14)
        self.dash_timer = 0       # >0 while dashing (also the i-frame window)
        self.dash_cd = 0          # cooldown frames before next dash allowed
        self.dash_dir = 1         # horizontal direction of the active dash
        self._dash_held = False   # edge-detect the dash key
        self.just_dashed = False  # one-shot: set the frame a dash starts
        self.dash_trail = []      # recent (x, y) ghosts for the motion blur

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), PLAYER_W, PLAYER_H)

    def update(self, keys, level):
        if self.dead:
            return

        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        up = keys[pygame.K_UP] or keys[pygame.K_w]
        down = keys[pygame.K_DOWN] or keys[pygame.K_s]
        jump = keys[pygame.K_z] or keys[pygame.K_k]
        dash = keys[pygame.K_c] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        self.ducking = down and self.on_ground

        if self.ducking:
            self.vx = 0
        elif left:
            self.vx = -PLAYER_SPEED
            self.facing = -1
        elif right:
            self.vx = PLAYER_SPEED
            self.facing = 1
        else:
            self.vx = 0

        # --- dash / dodge-roll (v0.14) ---
        # A short, fast burst in the facing direction with i-frames. Can't be
        # started while ducking; overrides normal horizontal speed while active.
        self.just_dashed = False
        dash_pressed = dash and not self._dash_held
        self._dash_held = dash
        if dash_pressed and self.dash_cd == 0 and self.dash_timer == 0 \
                and not self.ducking:
            self.dash_timer = DASH_DURATION
            self.dash_cd = DASH_COOLDOWN
            self.dash_dir = self.facing
            self.just_dashed = True
            self.dash_trail = []
        if self.dash_timer > 0:
            self.vx = DASH_SPEED * self.dash_dir
            self.facing = self.dash_dir

        self.just_jumped = False
        # jump buffering: if jump pressed but cannot yet, remember 5 frames
        jump_pressed = jump and not self._jump_held
        if jump_pressed:
            self.jump_buffer = 5

        can_jump = (self.on_ground or self.coyote_timer < self.COYOTE_FRAMES) \
            and not self.ducking
        if self.jump_buffer > 0 and can_jump:
            self.vy = JUMP_VELOCITY
            self.on_ground = False
            self.coyote_timer = self.COYOTE_FRAMES  # consume
            self.jump_buffer = 0
            self.just_jumped = True

        # jump cut: if player releases jump while ascending → shorten arc
        if self._was_jump_held and not jump and self.vy < 0:
            self.vy *= self.JUMP_CUT_DAMP

        self._was_jump_held = jump
        self._jump_held = jump
        if self.jump_buffer > 0:
            self.jump_buffer -= 1

        if not self.on_ground:
            self.vy += GRAVITY
            if self.vy > MAX_FALL:
                self.vy = MAX_FALL
        else:
            if self.vy > 0:
                self.vy = 0

        ax, ay = 0, 0
        if up and not self.ducking:
            ay = -1
        elif down and not self.on_ground:
            ay = 1
        if left:
            ax = -1
        elif right:
            ax = 1
        if ax == 0 and ay == 0:
            ax = self.facing
        self.aim = (ax, ay)

        self.x += self.vx
        for p in level.platforms:
            if self.rect.colliderect(p):
                if self.vx > 0:
                    self.x = p.left - PLAYER_W
                elif self.vx < 0:
                    self.x = p.right

        if self.x < 0:
            self.x = 0
        if self.x > level.width - PLAYER_W:
            self.x = level.width - PLAYER_W

        self.y += self.vy
        for p in level.platforms:
            if self.rect.colliderect(p):
                if self.vy > 0:
                    self.y = p.top - PLAYER_H
                    self.vy = 0
                elif self.vy < 0:
                    self.y = p.bottom
                    self.vy = 0

        feet = pygame.Rect(int(self.x), int(self.y) + PLAYER_H, PLAYER_W, 1)
        was_grounded = self.on_ground
        self.on_ground = any(feet.colliderect(p) for p in level.platforms)
        if self.on_ground:
            self.coyote_timer = 0
        else:
            self.coyote_timer = min(self.COYOTE_FRAMES + 1,
                                    self.coyote_timer + 1)

        if self.y > SCREEN_H + 100:
            self.dead = True

        if self.shoot_timer > 0:
            self.shoot_timer -= 1
        if self.muzzle_timer > 0:
            self.muzzle_timer -= 1
        if self.invincible > 0:
            self.invincible -= 1
        if self.dash_cd > 0:
            self.dash_cd -= 1
        if self.dash_timer > 0:
            self.dash_timer -= 1
            self.dash_trail.append((self.x, self.y))
            if len(self.dash_trail) > 6:
                self.dash_trail.pop(0)
        elif self.dash_trail:
            self.dash_trail.pop(0)   # fade out remaining ghosts
        self.anim_frame += 1

    def try_shoot(self):
        from .entities import Bullet
        if self.shoot_timer > 0 or self.dead:
            return []
        # if special weapon ran out of ammo, fall back to normal rifle
        if self.weapon != WEAPON_NORMAL and self.ammo <= 0:
            self.weapon = WEAPON_NORMAL
        if self.weapon == WEAPON_MACHINE:
            cooldown = SHOOT_COOLDOWN_MACHINE
        elif self.weapon == WEAPON_LASER:
            cooldown = SHOOT_COOLDOWN_LASER
        else:
            cooldown = SHOOT_COOLDOWN
        self.shoot_timer = cooldown
        self.muzzle_timer = 3
        bx = self.x + PLAYER_W / 2
        by = self.y + PLAYER_H / 2
        if self.ducking:
            by += 8
        ax, ay = self.aim
        # consume one ammo per shot for special weapons
        if self.weapon != WEAPON_NORMAL:
            self.ammo = max(0, self.ammo - 1)
        if self.weapon == WEAPON_SPREAD:
            base = math.atan2(ay, ax) if (ax or ay) else 0.0
            return [
                Bullet(bx, by, math.cos(base + off), math.sin(base + off), True)
                for off in (-0.32, -0.16, 0, 0.16, 0.32)
            ]
        if self.weapon == WEAPON_LASER:
            return [Bullet(bx, by, ax, ay, True,
                           speed=LASER_BULLET_SPEED, piercing=True)]
        return [Bullet(bx, by, ax, ay, True)]

    def hit(self):
        # dash grants i-frames: a well-timed dodge passes through danger
        if self.invincible > 0 or self.dead or self.dash_timer > 0:
            return False
        self.dead = True
        return True

    def respawn(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.dead = False
        self.invincible = INVINCIBLE_FRAMES
        self.weapon = WEAPON_NORMAL
        self.ammo = 0
        self.dash_timer = 0
        self.dash_cd = 0
        self.dash_trail = []
        self._dash_held = False
        self.just_dashed = False

    def draw(self, screen, camera):
        if self.dead:
            return
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0:
            return
        # dash motion-trail afterimages (drawn behind the player)
        if self.dash_trail:
            self._draw_dash_trail(screen, camera)
        sx = int(self.x - camera.x)
        sy = int(self.y)
        # Prefer Kenney pixel sprite. Scale 1.5 → 24×24 source becomes 36×36
        # which closely matches our 24×36 hitbox.
        sprite_name = "player_duck.png" if self.ducking else "player_idle.png"
        if sprites.has(sprite_name):
            self._draw_sprite(screen, sx, sy, sprite_name)
            return
        # Fallback to legacy procedural drawing (kept for safety)
        self._draw_procedural(screen, sx, sy)

    def _draw_dash_trail(self, screen, camera):
        """Cyan speed-streak ghosts left behind during a dash. Uses flat
        translucent silhouettes (reliable regardless of per-pixel sprite alpha)."""
        n = len(self.dash_trail)
        for i, (gx, gy) in enumerate(self.dash_trail):
            a = int(28 + 80 * (i / max(1, n)))   # newer ghosts are brighter
            ghost = pygame.Surface((PLAYER_W, PLAYER_H), pygame.SRCALPHA)
            ghost.fill((140, 225, 255, a))
            screen.blit(ghost, (int(gx - camera.x), int(gy)))

    def _draw_sprite(self, screen, sx, sy, sprite_name):
        flip = self.facing == -1
        spr = sprites.get(sprite_name, scale=1.5, flip_x=flip)
        if spr is None:
            return
        # Centre the sprite over the hitbox: sprite is 36×36, hitbox 24×36
        offset_x = (spr.get_width() - PLAYER_W) // 2
        offset_y = (spr.get_height() - PLAYER_H)
        if self.ducking:
            offset_y -= 0  # duck sprite is shorter, already aligned bottom
        screen.blit(spr, (sx - offset_x, sy + offset_y))

        # Overlay gun + muzzle flash on top of the Kenney character
        ax, ay = self.aim
        if ax or ay:
            mag = math.hypot(ax, ay)
            gx, gy = ax / mag, ay / mag
        else:
            gx, gy = self.facing, 0
        shoulder_x = sx + PLAYER_W // 2
        shoulder_y = sy + (PLAYER_H // 2 - 2)
        if self.ducking:
            shoulder_y = sy + PLAYER_H - 18
        arm_end_x = shoulder_x + int(gx * 6)
        arm_end_y = shoulder_y + int(gy * 6)
        gun_tip_x = shoulder_x + int(gx * 16)
        gun_tip_y = shoulder_y + int(gy * 16)
        pygame.draw.line(screen, (45, 45, 55),
                         (arm_end_x, arm_end_y), (gun_tip_x, gun_tip_y), 4)
        pygame.draw.line(screen, (170, 170, 185),
                         (arm_end_x, arm_end_y), (gun_tip_x, gun_tip_y), 2)
        # muzzle flash
        if self.muzzle_timer > 0:
            fx = gun_tip_x + int(gx * 3)
            fy = gun_tip_y + int(gy * 3)
            pygame.draw.circle(screen, (255, 240, 120), (fx, fy), 5)
            pygame.draw.circle(screen, (255, 200, 60), (fx, fy), 3)
            pygame.draw.circle(screen, (255, 100, 30), (fx, fy), 1)

    def _draw_procedural(self, screen, sx, sy):
        """Legacy hand-drawn version, used when sprites are missing."""
        walking = abs(self.vx) > 0.1 and self.on_ground and not self.ducking
        airborne = not self.on_ground
        legs_phase = (self.anim_frame // 5) % 4 if walking else 0

        if self.ducking:
            head_top = sy + 14
            head_h = 8
            body_top = sy + 22
            body_h = 12
            feet_top = sy + 30
        else:
            head_top = sy
            head_h = 11
            body_top = sy + 11
            body_h = 17
            feet_top = sy + 28

        # legs
        if not self.ducking:
            leg_color = (35, 35, 50)
            boot_color = (15, 15, 25)
            if airborne:
                # tucked legs
                pygame.draw.rect(screen, leg_color, (sx + 4, feet_top - 2, 5, 6))
                pygame.draw.rect(screen, leg_color, (sx + PLAYER_W - 9, feet_top - 2, 5, 6))
                pygame.draw.rect(screen, boot_color, (sx + 3, feet_top + 4, 7, 3))
                pygame.draw.rect(screen, boot_color, (sx + PLAYER_W - 10, feet_top + 4, 7, 3))
            else:
                # walk frames: (left x-offset, left height, right x-offset, right height)
                frames = [(0, 6, 4, 2), (2, 4, 2, 4), (4, 2, 0, 6), (2, 4, 2, 4)]
                lx, lh, rx, rh = frames[legs_phase]
                if self.facing == -1:
                    lx, rx = rx, lx
                pygame.draw.rect(screen, leg_color, (sx + 3 + lx, feet_top, 5, lh + 2))
                pygame.draw.rect(screen, boot_color, (sx + 2 + lx, feet_top + lh + 1, 7, 3))
                pygame.draw.rect(screen, leg_color, (sx + PLAYER_W - 8 - rx, feet_top, 5, rh + 2))
                pygame.draw.rect(screen, boot_color, (sx + PLAYER_W - 9 - rx, feet_top + rh + 1, 7, 3))
        else:
            pygame.draw.rect(screen, (35, 35, 50), (sx + 3, feet_top, 7, 4))
            pygame.draw.rect(screen, (35, 35, 50), (sx + PLAYER_W - 10, feet_top, 7, 4))
            pygame.draw.rect(screen, (15, 15, 25), (sx + 2, feet_top + 3, 9, 2))
            pygame.draw.rect(screen, (15, 15, 25), (sx + PLAYER_W - 11, feet_top + 3, 9, 2))

        # body
        pygame.draw.rect(screen, PLAYER_COLOR, (sx + 2, body_top, PLAYER_W - 4, body_h))
        # ammo belt
        pygame.draw.rect(screen, (180, 140, 60),
                         (sx + 3, body_top + body_h // 2, PLAYER_W - 6, 2))
        # body shading
        pygame.draw.line(screen, (30, 100, 40),
                         (sx + PLAYER_W // 2, body_top + 1),
                         (sx + PLAYER_W // 2, body_top + body_h - 1), 1)

        # head + helmet
        pygame.draw.rect(screen, (220, 180, 140),
                         (sx + 5, head_top + 4, PLAYER_W - 10, head_h - 4))
        pygame.draw.rect(screen, PLAYER_HELMET, (sx + 3, head_top, PLAYER_W - 6, 5))
        pygame.draw.rect(screen, (15, 60, 25), (sx + 3, head_top + 5, PLAYER_W - 6, 1))
        # helmet ridge
        pygame.draw.rect(screen, (30, 100, 40), (sx + 5, head_top - 1, PLAYER_W - 10, 1))

        # eye
        eye_x = sx + (PLAYER_W - 7 if self.facing == 1 else 5)
        pygame.draw.rect(screen, (35, 35, 35), (eye_x, head_top + 6, 2, 2))

        # gun + arm
        ax, ay = self.aim
        if ax or ay:
            mag = math.hypot(ax, ay)
            gx, gy = ax / mag, ay / mag
        else:
            gx, gy = self.facing, 0

        shoulder_x = sx + PLAYER_W // 2
        shoulder_y = body_top + 5
        if self.ducking:
            shoulder_y = body_top + 3

        arm_end_x = shoulder_x + int(gx * 8)
        arm_end_y = shoulder_y + int(gy * 8)
        gun_tip_x = shoulder_x + int(gx * 17)
        gun_tip_y = shoulder_y + int(gy * 17)

        # arm
        pygame.draw.line(screen, PLAYER_COLOR,
                         (shoulder_x, shoulder_y), (arm_end_x, arm_end_y), 4)
        # gun barrel
        pygame.draw.line(screen, (50, 50, 60),
                         (arm_end_x, arm_end_y), (gun_tip_x, gun_tip_y), 3)
        pygame.draw.line(screen, (110, 110, 120),
                         (arm_end_x, arm_end_y), (gun_tip_x, gun_tip_y), 1)

        # muzzle flash
        if self.muzzle_timer > 0:
            fx = gun_tip_x + int(gx * 3)
            fy = gun_tip_y + int(gy * 3)
            pygame.draw.circle(screen, (255, 240, 120), (fx, fy), 5)
            pygame.draw.circle(screen, (255, 200, 60), (fx, fy), 3)
            pygame.draw.circle(screen, (255, 100, 30), (fx, fy), 1)
