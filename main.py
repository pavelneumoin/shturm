import asyncio
import math
import os
import random
import pygame

from game.constants import (
    SCREEN_W, SCREEN_H, FPS, GROUND_Y, PLAYER_W, PLAYER_H,
    DARK,
    WEAPON_NORMAL, WEAPON_SPREAD, WEAPON_MACHINE, WEAPON_LASER, PICKUP_LIFE,
    PICKUP_GEM, GEM_SCORE,
    BARREL_EXPLOSION_RADIUS, BARREL_EXPLOSION_DAMAGE,
    KAMIKAZE_EXPLOSION_RADIUS,
    STAGE_INTRO_FRAMES, STAGE_CLEAR_FRAMES,
)
from game.player import Player
from game.entities import (
    Bullet, MortarShell, Soldier, Turret, Drone, Jumper, Mortar,
    Sniper, Charger, Bomber, Grenade, ShieldTrooper, Burrower,
    Crate, Barrel, Kamikaze,
    Boss, MechBoss, Pickup, Particle, Checkpoint, ScorePopup,
)
from game.level import Level
from game.leveldef import ALL_LEVELS
from game.sounds import SoundBank
from game.music import MusicPlayer
from game.controls import TouchControls, CombinedKeys
from game import persistence as _persist
from game.persistence import (
    get_int, set_int,
    get_hi_table, qualifies_for_table,
    HI_SCORE_KEY, MUTED_KEY, CRT_KEY, DIFFICULTY_KEY,
)
from game.difficulty import ALL as DIFFICULTIES, by_index as diff_by_index
from game import vk_bridge


STAGE_MUSIC = ["jungle", "caves", "base", "sky"]


WEAPON_NAMES = {
    WEAPON_NORMAL: "RIFLE",
    WEAPON_SPREAD: "SPREAD",
    WEAPON_MACHINE: "MACHINE",
    WEAPON_LASER: "LASER",
}
WEAPON_COLORS = {
    WEAPON_NORMAL: (255, 240, 100),
    WEAPON_SPREAD: (100, 220, 255),
    WEAPON_MACHINE: (255, 220, 80),
    WEAPON_LASER: (255, 100, 100),
}


class Game:
    def __init__(self):
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption("SHTURM - run-and-gun")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        # Pixel font (Press Start 2P, SIL OFL). Fallback to default if missing.
        font_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "assets", "fonts", "PressStart2P-Regular.ttf",
        )
        if os.path.isfile(font_path):
            self.font = pygame.font.Font(font_path, 10)
            self.font_bold = pygame.font.Font(font_path, 12)
            self.bigfont = pygame.font.Font(font_path, 32)
            self.medfont = pygame.font.Font(font_path, 20)
            self.smallfont = pygame.font.Font(font_path, 8)
        else:
            self.font = pygame.font.Font(None, 22)
            self.font_bold = pygame.font.Font(None, 26)
            self.bigfont = pygame.font.Font(None, 64)
            self.medfont = pygame.font.Font(None, 44)
            self.smallfont = pygame.font.Font(None, 18)
        self.sounds = SoundBank()
        self.music = MusicPlayer()
        self.touch = TouchControls()
        self.state = "menu"
        self._music_state = None
        self._boss_engaged = False
        # persistent across stages
        self.score = 0
        self.lives = 3
        self.persistent_weapon = WEAPON_NORMAL
        self.persistent_ammo = 0
        self.current_level_idx = 0
        self.level = None
        self.player = None
        self.boss = None
        self.intro_timer = 0
        self.clear_timer = 0
        self.bonus_score = 0
        # ephemeral
        self.bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.pickups = []
        self.particles = []
        self.checkpoints = []
        self.last_checkpoint_x = None
        self.popups = []
        self.next_milestone = 20000
        self.combo = 0
        self.combo_timer = 0  # frames until combo resets
        self.combo_best = 0
        self.achievement_text = ""
        self.achievement_timer = 0
        self.first_blood = False
        self.tutorial_timer = 0
        self.tutorial_shot = False
        self.tutorial_moved = False
        self.tutorial_jumped = False
        self.tutorial_dashed = False
        self.shake = 0
        self.combo_flash = 0
        self.combo_flash_color = (255, 220, 80)
        self.boss_warning_timer = 0
        # persistent across runs
        self.hi_score = get_int(HI_SCORE_KEY, 0)
        self._hi_committed_to = self.hi_score
        self.muted = bool(get_int(MUTED_KEY, 0))
        self._apply_mute()
        self.crt = bool(get_int(CRT_KEY, 0))
        self._scanlines_cache = None
        self.diff_idx = max(0, min(len(DIFFICULTIES) - 1, get_int(DIFFICULTY_KEY, 1)))
        self.difficulty = diff_by_index(self.diff_idx)
        # hi-score table
        self.hi_table = get_hi_table()
        self.name_entry = ["A", "A", "A"]
        self.name_pos = 0

    def _start_new_run(self):
        self.score = 0
        self.lives = self.difficulty.starting_lives
        self.persistent_weapon = WEAPON_NORMAL
        self.persistent_ammo = 0
        self.current_level_idx = 0
        self.next_milestone = 20000
        self.combo = 0
        self.combo_timer = 0
        self.combo_best = 0
        self.achievement_text = ""
        self.achievement_timer = 0
        self.first_blood = False
        self.tutorial_timer = 360  # ~6 seconds at 60 FPS
        self.tutorial_shot = False
        self.tutorial_moved = False
        self.tutorial_jumped = False
        self.tutorial_dashed = False
        self.combo_flash = 0
        self.combo_flash_color = (255, 220, 80)
        self._load_stage(0)
        self.state = "stage_intro"
        self.intro_timer = STAGE_INTRO_FRAMES

    def _load_stage(self, level_idx):
        self.current_level_idx = level_idx
        level_def = ALL_LEVELS[level_idx]
        self.level = Level(level_def)
        self.player = Player(60, GROUND_Y - PLAYER_H)
        self.player.weapon = self.persistent_weapon
        self.player.ammo = self.persistent_ammo
        self.bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.pickups = []
        self.particles = []
        self.popups = []
        self.boss = None
        self.shake = 0
        self._boss_engaged = False
        self.boss_warning_timer = 0
        for kind, x, y in level_def.enemy_spawns:
            e = None
            if kind == "soldier":
                e = Soldier(x, y)
            elif kind == "turret":
                e = Turret(x, y)
            elif kind == "drone":
                e = Drone(x, y)
            elif kind == "jumper":
                e = Jumper(x, y)
            elif kind == "mortar":
                e = Mortar(x, y)
            elif kind == "sniper":
                e = Sniper(x, y)
            elif kind == "charger":
                e = Charger(x, y)
            elif kind == "bomber":
                e = Bomber(x, y)
            elif kind == "shield":
                e = ShieldTrooper(x, y)
            elif kind == "burrower":
                e = Burrower(x, y)
            elif kind == "crate":
                e = Crate(x, y)
            elif kind == "barrel":
                e = Barrel(x, y)
            elif kind == "kamikaze":
                e = Kamikaze(x, y)
            if e is not None:
                # apply difficulty HP scaling (destructibles always break in 1 hit)
                if not isinstance(e, (Crate, Barrel)):
                    e.hp = max(1, int(round(e.hp * self.difficulty.enemy_hp_mult)))
                    e.max_hp = e.hp
                self.enemies.append(e)
        if level_def.boss_spawn:
            bx, by, btype = level_def.boss_spawn
            if btype == "mech":
                self.boss = MechBoss(bx, by)
            else:
                self.boss = Boss(bx, by)
            self.enemies.append(self.boss)
        for x, y, kind in level_def.pickup_spawns:
            self.pickups.append(Pickup(x, y, kind))
        self.checkpoints = [Checkpoint(x, y) for (x, y) in level_def.checkpoints]
        self.last_checkpoint_x = None
        self.respawn_y = GROUND_Y - PLAYER_H

    def _advance_stage(self):
        # carry over weapon and remaining ammo
        self.persistent_weapon = self.player.weapon
        self.persistent_ammo = self.player.ammo
        next_idx = self.current_level_idx + 1
        if next_idx >= len(ALL_LEVELS):
            self._commit_hi_score()
            self._maybe_enter_name_or_end("win")
        else:
            self._load_stage(next_idx)
            self.state = "stage_intro"
            self.intro_timer = STAGE_INTRO_FRAMES

    def _combo_multiplier(self):
        if self.combo >= 15:
            return 3
        if self.combo >= 5:
            return 2
        return 1

    def _register_kill(self, enemy, x, y):
        """Bump combo, multiply points, push popup."""
        self.combo += 1
        self.combo_timer = 180  # 3 seconds at 60 FPS
        if self.combo > self.combo_best:
            self.combo_best = self.combo
        mult = self._combo_multiplier()
        gained = enemy.points * mult
        self.score += gained
        # Achievement popups for combo milestones
        if self.combo == 5:
            self._flash_achievement("5x COMBO!")
        elif self.combo == 10:
            self._flash_achievement("10x COMBO!")
        elif self.combo == 15:
            self._flash_achievement("15x COMBO!")
        elif self.combo == 25:
            self._flash_achievement("RAMPAGE!")
        return gained

    def _maybe_drop_loot(self, enemy):
        """Small chance a slain enemy drops a pickup (gem / heart / weapon).
        Tougher enemies (max_hp >= 2) drop a little more often."""
        drop_chance = 0.18 if getattr(enemy, "max_hp", 1) >= 2 else 0.10
        if random.random() > drop_chance:
            return
        cx = enemy.x + enemy.w / 2 - 11
        cy = enemy.y + enemy.h / 2 - 11
        r = random.random()
        if r < 0.62:
            kind = PICKUP_GEM           # gems are the common reward
        elif r < 0.74:
            kind = PICKUP_LIFE          # extra life is rare
        else:
            kind = random.choice([WEAPON_SPREAD, WEAPON_MACHINE, WEAPON_LASER])
        self.pickups.append(Pickup(cx, cy, kind))

    def _drop_crate_loot(self, crate):
        """Crates ALWAYS reward the player — weapons are the most common find,
        with the occasional gem or extra life."""
        cx = crate.x + crate.w / 2 - 11
        cy = crate.y + crate.h / 2 - 11
        r = random.random()
        if r < 0.42:
            kind = PICKUP_GEM
        elif r < 0.55:
            kind = PICKUP_LIFE
        else:
            kind = random.choice([WEAPON_SPREAD, WEAPON_MACHINE, WEAPON_LASER])
        self.pickups.append(Pickup(cx, cy, kind))

    def _break_crate(self, crate):
        """Splinter a destroyed crate and spill its guaranteed loot."""
        cx = crate.x + crate.w / 2
        cy = crate.y + crate.h / 2
        self._spawn_explosion(cx, cy, (160, 110, 60), count=10)
        self._spawn_explosion(cx, cy, (210, 170, 100), count=6)
        self.sounds.play('kill')
        self._drop_crate_loot(crate)

    def _explode_barrel(self, barrel):
        """Detonate a barrel: a radial blast damages every enemy in range (and
        chains into other barrels), singeing the player if they're too close."""
        cx = barrel.x + barrel.w / 2
        cy = barrel.y + barrel.h / 2
        self._spawn_explosion(cx, cy, (255, 170, 50), count=26)
        self._spawn_explosion(cx, cy, (255, 90, 30), count=16)
        self._spawn_explosion(cx, cy - 6, (90, 90, 95), count=8)  # smoke puff
        self.shake = max(self.shake, 22)
        self.sounds.play('boss')  # deep boom
        r2 = BARREL_EXPLOSION_RADIUS * BARREL_EXPLOSION_RADIUS
        for e in self.enemies:
            if not e.alive or e is barrel:
                continue
            ex = e.x + e.w / 2
            ey = e.y + e.h / 2
            if (ex - cx) ** 2 + (ey - cy) ** 2 > r2:
                continue
            if isinstance(e, (Boss, MechBoss)):
                e.hit(BARREL_EXPLOSION_DAMAGE)  # chip the boss, no instakill
                continue
            if not e.hit(BARREL_EXPLOSION_DAMAGE):
                continue
            if isinstance(e, Barrel):
                self._explode_barrel(e)          # chain reaction!
            elif isinstance(e, Crate):
                self._break_crate(e)
            else:
                gained = self._register_kill(e, ex, e.y)
                self._spawn_explosion(ex, ey, (255, 200, 80), count=10)
                self.popups.append(ScorePopup(ex, e.y, gained))
                self._maybe_drop_loot(e)
        # Player caught in the blast — smaller lethal radius leaves a safe gap
        if self.player.invincible <= 0 and not self.player.dead:
            px = self.player.x + PLAYER_W / 2
            py = self.player.y + PLAYER_H / 2
            pr = BARREL_EXPLOSION_RADIUS * 0.66
            if (px - cx) ** 2 + (py - cy) ** 2 <= pr * pr:
                self.player.hit()
                self.shake = max(self.shake, 18)
                self.sounds.play('hit')
                self.combo = 0

    def _explode_kamikaze(self, k):
        """Detonate a kamikaze drone: fiery burst + AoE that hurts a nearby
        player. A dashing/invincible player passes through unharmed because
        player.hit() guards on dash i-frames and invincibility."""
        cx = k.x + k.w / 2
        cy = k.y + k.h / 2
        self._spawn_explosion(cx, cy, (255, 150, 50), count=20)
        self._spawn_explosion(cx, cy, (255, 90, 30), count=12)
        self.shake = max(self.shake, 16)
        self.sounds.play('kill')
        if self.player.invincible <= 0 and not self.player.dead:
            px = self.player.x + PLAYER_W / 2
            py = self.player.y + PLAYER_H / 2
            r = KAMIKAZE_EXPLOSION_RADIUS
            if (px - cx) ** 2 + (py - cy) ** 2 <= r * r:
                if self.player.hit():
                    self.shake = max(self.shake, 16)
                    self.sounds.play('hit')
                    self.combo = 0

    def _flash_achievement(self, text):
        self.achievement_text = text
        self.achievement_timer = 90
        # brief screen flash for combo milestones
        if "COMBO" in text or text == "RAMPAGE!":
            if self.combo >= 25 or text == "RAMPAGE!":
                self.combo_flash = 10
                self.combo_flash_color = (255, 60, 60)
            elif self.combo >= 15:
                self.combo_flash = 8
                self.combo_flash_color = (255, 110, 40)
            elif self.combo >= 10:
                self.combo_flash = 6
                self.combo_flash_color = (255, 180, 60)
            else:
                self.combo_flash = 5
                self.combo_flash_color = (255, 220, 80)
        elif text in ("BOSS DOWN!", "MISSION COMPLETE"):
            self.combo_flash = 12
            self.combo_flash_color = (255, 200, 80)

    def _spawn_explosion(self, x, y, color, count=10):
        for _ in range(count):
            vx = random.uniform(-3.2, 3.2)
            vy = random.uniform(-5.5, -1.0)
            life = random.randint(20, 40)
            self.particles.append(Particle(x, y, vx, vy, color, life))

    def _spawn_death_burst(self, x, y):
        """Shatter the hero into a cloud of body-coloured pixel chunks."""
        palette = [
            (60, 220, 80),     # body
            (30, 100, 40),     # helmet
            (220, 180, 140),   # face
            (35, 35, 50),      # boots
            (180, 140, 60),    # ammo belt
            (255, 240, 100),   # muzzle yellow accent
        ]
        # main shatter — 28 chunks
        for _ in range(28):
            vx = random.uniform(-5, 5)
            vy = random.uniform(-7, -2)
            life = random.randint(34, 60)
            col = random.choice(palette)
            self.particles.append(Particle(
                x + random.uniform(-8, 8),
                y + random.uniform(-10, 10),
                vx, vy, col, life))
        # outer ring of warm explosion
        for _ in range(10):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(2.5, 5.5)
            self.particles.append(Particle(
                x, y,
                math.cos(ang) * sp, math.sin(ang) * sp - 1,
                (255, 200, 80), random.randint(22, 36)))
        self.shake = max(self.shake, 18)

    def _commit_hi_score(self):
        adjusted = int(round(self.score * self.difficulty.score_mult))
        if adjusted > self.hi_score:
            self.hi_score = adjusted
        if self.hi_score != self._hi_committed_to:
            set_int(HI_SCORE_KEY, self.hi_score)
            self._hi_committed_to = self.hi_score

    def _apply_mute(self):
        self.sounds.set_muted(self.muted)
        self.music.set_muted(self.muted)

    def _toggle_mute(self):
        self.muted = not self.muted
        self._apply_mute()
        set_int(MUTED_KEY, 1 if self.muted else 0)

    def _toggle_crt(self):
        self.crt = not self.crt
        set_int(CRT_KEY, 1 if self.crt else 0)

    def _maybe_enter_name_or_end(self, end_state):
        """If score qualifies for top-5, enter name-entry; else go to end_state."""
        adjusted = int(round(self.score * self.difficulty.score_mult))
        if qualifies_for_table(self.hi_table, adjusted):
            self.state = "enter_name"
            self.name_entry = ["A", "A", "A"]
            self.name_pos = 0
            self._end_state_after_name = end_state
        else:
            self.state = end_state

    def _commit_name_entry(self):
        name = "".join(self.name_entry)
        adjusted = int(round(self.score * self.difficulty.score_mult))
        self.hi_table.append({
            "name": name,
            "score": adjusted,
            "diff": self.difficulty.name,
        })
        self.hi_table.sort(key=lambda r: r["score"], reverse=True)
        self.hi_table = self.hi_table[:5]
        _persist.commit_hi_table(self.hi_table)
        self.state = self._end_state_after_name

    def _cycle_difficulty(self, delta):
        self.diff_idx = (self.diff_idx + delta) % len(DIFFICULTIES)
        self.difficulty = diff_by_index(self.diff_idx)
        set_int(DIFFICULTY_KEY, self.diff_idx)
        self.sounds.play('select')

    def _draw_crt_overlay(self):
        if not self.crt:
            return
        if self._scanlines_cache is None:
            surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            for y in range(0, SCREEN_H, 3):
                pygame.draw.line(surf, (0, 0, 0, 60), (0, y), (SCREEN_W, y))
            # subtle vertical vignette
            for x in range(0, 30):
                a = int(80 * (1 - x / 30))
                pygame.draw.line(surf, (0, 0, 0, a), (x, 0), (x, SCREEN_H))
                pygame.draw.line(surf, (0, 0, 0, a),
                                 (SCREEN_W - 1 - x, 0),
                                 (SCREEN_W - 1 - x, SCREEN_H))
            self._scanlines_cache = surf
        self.screen.blit(self._scanlines_cache, (0, 0))

    async def run(self):
        running = True
        MOUSE_FID = -1
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._on_keydown(event)
                    if event.key in (pygame.K_ESCAPE, pygame.K_p) and \
                            self.state == "play":
                        self.state = "pause"
                        self.touch.clear()
                        self.music.set_paused(True)
                    elif event.key in (pygame.K_ESCAPE, pygame.K_p) and \
                            self.state == "pause":
                        self.state = "play"
                        self.music.set_paused(False)
                    elif event.key == pygame.K_ESCAPE and self.state == "menu":
                        running = False
                    elif event.key == pygame.K_m:
                        self._toggle_mute()
                    elif event.key == pygame.K_f:
                        self._toggle_crt()
                    elif event.key in (pygame.K_LEFT, pygame.K_LEFTBRACKET) \
                            and self.state == "menu":
                        self._cycle_difficulty(-1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_RIGHTBRACKET) \
                            and self.state == "menu":
                        self._cycle_difficulty(+1)
                elif event.type == pygame.FINGERDOWN:
                    fx = event.x * SCREEN_W
                    fy = event.y * SCREEN_H
                    self._handle_touch_down(event.finger_id, fx, fy)
                elif event.type == pygame.FINGERUP:
                    self.touch.end(event.finger_id)
                elif event.type == pygame.FINGERMOTION:
                    self.touch.move(event.finger_id,
                                    event.x * SCREEN_W, event.y * SCREEN_H)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_touch_down(MOUSE_FID, event.pos[0], event.pos[1])
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.touch.end(MOUSE_FID)
                elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
                    self.touch.move(MOUSE_FID, event.pos[0], event.pos[1])

            real_keys = pygame.key.get_pressed()
            keys = CombinedKeys(real_keys, self.touch)
            self._update_music()
            # handle touch-pause tap
            if self.touch.consume_pause_tap():
                if self.state == "play":
                    self.state = "pause"
                    self.touch.clear()
                    self.music.set_paused(True)
                elif self.state == "pause":
                    self.state = "play"
                    self.music.set_paused(False)
            if self.state == "play":
                self._update_play(keys)
            elif self.state == "stage_intro":
                self._update_intro()
            elif self.state == "stage_clear":
                self._update_clear()

            self._draw()
            pygame.display.flip()
            await asyncio.sleep(0)
            self.clock.tick(FPS)
        pygame.quit()

    def _on_keydown(self, event):
        if self.state == "menu" and event.key in (
            pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_z, pygame.K_x, pygame.K_SPACE
        ):
            self._start_new_run()
            self.sounds.play('select')
        elif self.state in ("gameover", "win") and event.key in (
            pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_z, pygame.K_x, pygame.K_SPACE
        ):
            self.state = "menu"
            self.sounds.play('select')
        elif self.state == "pause" and event.key in (
            pygame.K_RETURN, pygame.K_q
        ):
            # quit to menu from pause
            self.state = "menu"
            self.touch.clear()
            self.music.set_paused(False)
            self.sounds.play('select')
        elif self.state == "enter_name":
            self._on_keydown_name_entry(event)
        elif self.state == "stage_intro" and event.key in (
            pygame.K_RETURN, pygame.K_z, pygame.K_x, pygame.K_SPACE
        ):
            self.state = "play"
        elif self.state == "stage_clear" and event.key in (
            pygame.K_RETURN, pygame.K_z, pygame.K_x, pygame.K_SPACE
        ):
            self._advance_stage()

    def _on_keydown_name_entry(self, event):
        key = event.key
        ch = self.name_entry[self.name_pos]
        idx = ord(ch) - ord('A')
        if key in (pygame.K_UP, pygame.K_w):
            idx = (idx - 1) % 26
            self.name_entry[self.name_pos] = chr(ord('A') + idx)
        elif key in (pygame.K_DOWN, pygame.K_s):
            idx = (idx + 1) % 26
            self.name_entry[self.name_pos] = chr(ord('A') + idx)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.name_pos = (self.name_pos - 1) % 3
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.name_pos = (self.name_pos + 1) % 3
        elif key in (pygame.K_z, pygame.K_x, pygame.K_RETURN, pygame.K_SPACE):
            if self.name_pos < 2:
                self.name_pos += 1
            else:
                self._commit_name_entry()
                self.sounds.play('select')
        elif pygame.K_a <= key <= pygame.K_z:
            self.name_entry[self.name_pos] = chr(key).upper()
            if self.name_pos < 2:
                self.name_pos += 1

    def _handle_touch_down(self, fid, x, y):
        if self.state == "menu":
            self._start_new_run()
            self.sounds.play('select')
            return
        if self.state in ("gameover", "win"):
            self.state = "menu"
            self.sounds.play('select')
            self.touch.clear()
            return
        if self.state == "stage_intro":
            self.state = "play"
            return
        if self.state == "stage_clear":
            self._advance_stage()
            return
        self.touch.begin(fid, x, y)

    def _update_music(self):
        """Pick the right looping track for the current state."""
        if self.state == "menu":
            target = "menu"
        elif self.state == "win":
            target = "victory"
        elif self.state in ("play", "stage_intro", "stage_clear"):
            if self.state == "play" and self.boss is not None and \
                    self.boss.alive and self._boss_in_view():
                target = "boss"
            elif 0 <= self.current_level_idx < len(STAGE_MUSIC):
                target = STAGE_MUSIC[self.current_level_idx]
            else:
                target = "menu"
        elif self.state == "gameover":
            target = None
        else:
            target = None
        if target != self._music_state:
            self._music_state = target
            if target is None:
                self.music.stop()
            else:
                self.music.play(target)

    def _boss_in_view(self):
        if self.boss is None or not self.boss.alive or self.level is None:
            return False
        cam_x = self.level.camera.x
        return -100 < (self.boss.x - cam_x) < SCREEN_W + 100

    def _update_intro(self):
        self.intro_timer -= 1
        if self.intro_timer <= 0:
            self.state = "play"

    def _update_clear(self):
        self.clear_timer -= 1
        if self.clear_timer <= 0:
            self._advance_stage()

    def _update_play(self, keys):
        self.level.update()
        self.player.update(keys, self.level)
        if self.player.just_jumped:
            self.sounds.play('jump')
            self.tutorial_jumped = True
        if self.player.just_dashed:
            self.sounds.play('dash')
            self.tutorial_dashed = True
            # kick up a puff of dust behind the dash for a sense of speed
            dx = self.player.x + PLAYER_W / 2 - self.player.dash_dir * 10
            dy = self.player.y + PLAYER_H - 6
            self._spawn_explosion(dx, dy, (200, 230, 255), count=8)
        if abs(self.player.vx) > 0.1:
            self.tutorial_moved = True
        if keys[pygame.K_x] or keys[pygame.K_j]:
            new_shots = self.player.try_shoot()
            if new_shots:
                self.sounds.play('shoot')
                self.bullets.extend(new_shots)
                self.tutorial_shot = True

        if self.tutorial_timer > 0:
            self.tutorial_timer -= 1
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0
        if self.achievement_timer > 0:
            self.achievement_timer -= 1

        for b in self.bullets:
            b.update(self.level)
        for b in self.enemy_bullets:
            b.update(self.level)
            if getattr(b, 'exploded', False):
                self._spawn_explosion(b.x, b.y, (255, 140, 40), count=14)
                self._spawn_explosion(b.x, b.y, (255, 200, 80), count=8)
                self.shake = max(self.shake, 6)
                self.sounds.play('kill')
                b.exploded = False  # one-shot

        any_enemy_shot = False
        bs_mult = self.difficulty.enemy_bullet_speed_mult
        for e in self.enemies:
            new_b = e.update(self.player, self.level)
            # Kamikaze self-detonation on ground hit during its dive
            if getattr(e, 'exploded', False):
                e.exploded = False
                self._explode_kamikaze(e)
            if new_b:
                if bs_mult != 1.0:
                    for nb in new_b:
                        nb.vx *= bs_mult
                        nb.vy *= bs_mult
                self.enemy_bullets.extend(new_b)
                any_enemy_shot = True
        if any_enemy_shot:
            self.sounds.play('enemy')

        for p in self.pickups:
            p.update()
        for pt in self.particles:
            pt.update()
        for pop in self.popups:
            pop.update()

        for b in self.bullets:
            if not b.alive:
                continue
            for e in self.enemies:
                if not e.alive:
                    continue
                if b.already_hit(e):
                    continue
                if b.rect.colliderect(e.rect):
                    # Shield Trooper: check if frontal block absorbs the bullet
                    if hasattr(e, 'is_blocked') and e.is_blocked(b.x) and not b.piercing:
                        b.alive = False
                        self._spawn_explosion(b.x, b.y, (160, 180, 255), count=3)
                        break
                    dmg = 2 if b.piercing else 1
                    # round so 1.3 * 1 = 1 floor, 1.3 * 2 = 2 (avoid being too easy)
                    dmg = max(1, int(round(dmg * self.difficulty.player_dmg_mult)))
                    killed = e.hit(dmg)
                    if b.piercing:
                        b.mark_hit(e)
                    else:
                        b.alive = False
                    if killed:
                        if isinstance(e, Barrel):
                            self._explode_barrel(e)
                        elif isinstance(e, Crate):
                            self._break_crate(e)
                        else:
                            gained = self._register_kill(e, e.x + e.w / 2, e.y)
                            if not self.first_blood:
                                self.first_blood = True
                                self._flash_achievement("FIRST BLOOD!")
                            if isinstance(e, (Boss, MechBoss)):
                                self._spawn_explosion(e.x + e.w / 2, e.y + e.h / 2,
                                                      (255, 200, 80), count=60)
                                self.shake = 40
                                self.sounds.play('boss')
                                self.popups.append(ScorePopup(
                                    e.x + e.w / 2, e.y, gained,
                                    color=(255, 120, 120)))
                                self._flash_achievement("BOSS DOWN!")
                            else:
                                self._spawn_explosion(e.x + e.w / 2, e.y + e.h / 2,
                                                      (255, 200, 80), count=12)
                                self.sounds.play('kill')
                                self.popups.append(ScorePopup(
                                    e.x + e.w / 2, e.y, gained))
                                self._maybe_drop_loot(e)
                    else:
                        self._spawn_explosion(b.x, b.y, (255, 240, 100), count=4)
                    if not b.piercing:
                        break

        if self.player.invincible <= 0 and not self.player.dead:
            for b in self.enemy_bullets:
                if not b.alive:
                    continue
                if b.rect.colliderect(self.player.rect):
                    self.player.hit()
                    b.alive = False
                    self.shake = 12
                    self.sounds.play('hit')
                    self.combo = 0  # reset combo on hit
                    break

        if self.player.invincible <= 0 and not self.player.dead:
            for e in self.enemies:
                if not e.alive:
                    continue
                if isinstance(e, (Crate, Barrel)):
                    continue  # destructibles are scenery — no contact damage
                if self.player.rect.colliderect(e.rect):
                    self.player.hit()
                    self.shake = 12
                    self.sounds.play('hit')
                    self.combo = 0
                    # Charger explodes on contact
                    if isinstance(e, Charger):
                        e.hp = 0
                        e.alive = False
                        self._spawn_explosion(e.x + e.w / 2, e.y + e.h / 2,
                                              (255, 120, 40), count=20)
                    # Kamikaze detonates on contact (player already hit above)
                    elif isinstance(e, Kamikaze):
                        e.exploded = False
                        self._explode_kamikaze(e)
                    break

        for p in self.pickups:
            if p.alive and self.player.rect.colliderect(p.rect):
                burst_color = (100, 220, 255)
                if p.kind == PICKUP_LIFE:
                    self.lives += 1
                    burst_color = (120, 240, 120)
                elif p.kind == PICKUP_GEM:
                    self.score += GEM_SCORE
                    burst_color = (200, 140, 255)
                    self.popups.append(ScorePopup(
                        p.x + p.w / 2, p.y, GEM_SCORE, color=(210, 150, 255)))
                else:
                    from game.player import WEAPON_AMMO
                    refill = WEAPON_AMMO.get(p.kind, 0)
                    if self.player.weapon == p.kind:
                        # top up
                        self.player.ammo += refill
                    else:
                        self.player.weapon = p.kind
                        self.player.ammo = refill
                p.alive = False
                self._spawn_explosion(p.x + p.w / 2, p.y + p.h / 2,
                                      burst_color, count=8)
                self.sounds.play('powerup')

        for cp in self.checkpoints:
            cp.update()
            if not cp.active and self.player.rect.colliderect(cp.rect):
                cp.active = True
                self.last_checkpoint_x = cp.x
                self.sounds.play('powerup')
                self._spawn_explosion(cp.x + cp.W / 2, cp.y + 10,
                                      (120, 240, 120), count=14)

        self.bullets = [b for b in self.bullets if b.alive]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.alive]
        self.pickups = [p for p in self.pickups if p.alive]
        self.particles = [p for p in self.particles if p.alive]
        self.popups = [p for p in self.popups if p.alive]

        # milestone 1UP every 20000 points
        while self.score >= self.next_milestone:
            self.lives += 1
            self.next_milestone += 20000
            self.sounds.play('powerup')
            self.popups.append(ScorePopup(
                self.player.x + 12, self.player.y - 10, "1UP",
                color=(120, 240, 120)))

        self.level.camera.follow(self.player)

        # Boss WARNING banner — fires once when the boss first scrolls on-screen
        if (not self._boss_engaged and self.boss is not None
                and self.boss.alive and self._boss_in_view()):
            self._boss_engaged = True
            self.boss_warning_timer = 110
            self.shake = max(self.shake, 16)
            self.sounds.play('boss')
        if self.boss_warning_timer > 0:
            self.boss_warning_timer -= 1

        if self.shake > 0:
            self.shake -= 1

        if self.player.dead:
            self.lives -= 1
            # rich pixel-shatter death: multiple coloured chunks
            self._spawn_death_burst(self.player.x + 12, self.player.y + 18)
            self.sounds.play('death')
            if self.lives < 0:
                self._commit_hi_score()
                self._maybe_enter_name_or_end("gameover")
            else:
                if self.last_checkpoint_x is not None:
                    respawn_x = self.last_checkpoint_x
                else:
                    respawn_x = max(60, self.level.camera.x + 80)
                self.player.respawn(respawn_x, self.respawn_y)
                # apply difficulty's invincibility scaling
                self.player.invincible = int(
                    round(self.player.invincible *
                          self.difficulty.invincible_frames_mult))

        if self.boss is not None and not self.boss.alive:
            self.bonus_score = (self.current_level_idx + 1) * 5000
            self.score += self.bonus_score
            self.state = "stage_clear"
            self.clear_timer = STAGE_CLEAR_FRAMES

    def _draw(self):
        if self.state == "menu":
            self._draw_menu()
            self._draw_crt_overlay()
            return
        self._draw_play()
        if self.state == "stage_intro":
            self._draw_intro_overlay()
        elif self.state == "stage_clear":
            self._draw_clear_overlay()
        elif self.state == "pause":
            self._draw_pause_overlay()
        elif self.state == "gameover":
            self._draw_overlay("GAME OVER",
                               "ENTER / TAP - menu")
        elif self.state == "win":
            self._draw_overlay("MISSION COMPLETE",
                               "ENTER / TAP - menu")
        elif self.state == "enter_name":
            self._draw_name_entry_overlay()
        self._draw_crt_overlay()

    def _draw_play(self):
        ox = oy = 0
        if self.shake > 0:
            ox = random.randint(-3, 3)
            oy = random.randint(-3, 3)

        if ox or oy:
            target = pygame.Surface((SCREEN_W, SCREEN_H))
        else:
            target = self.screen

        self.level.draw(target, self.level.camera)
        for cp in self.checkpoints:
            cp.draw(target, self.level.camera)
        for p in self.pickups:
            p.draw(target, self.level.camera, self.font_bold)
        for e in self.enemies:
            e.draw(target, self.level.camera)
            e.draw_flash(target, self.level.camera)
            if not isinstance(e, (Boss, MechBoss)):
                e.draw_hp_bar(target, self.level.camera)
        for b in self.bullets:
            b.draw(target, self.level.camera)
        for b in self.enemy_bullets:
            b.draw(target, self.level.camera)
        for pt in self.particles:
            pt.draw(target, self.level.camera)
        for pop in self.popups:
            pop.draw(target, self.level.camera, self.font_bold)
        self.player.draw(target, self.level.camera)

        if ox or oy:
            self.screen.fill((0, 0, 0))
            self.screen.blit(target, (ox, oy))

        # foreground weather overlay (rain/lightning/drips/clouds/alarm) —
        # drawn on the final surface so it never leaves shake-edge artifacts
        self.level.draw_weather(self.screen, self.level.camera)

        # brief combo/event screen flash
        if self.combo_flash > 0:
            ratio = self.combo_flash / 10.0
            cf_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            cf_surf.fill((*self.combo_flash_color, int(70 * ratio)))
            self.screen.blit(cf_surf, (0, 0))
            self.combo_flash -= 1

        self._draw_hud()
        if self.current_level_idx == 0 and self.tutorial_timer > 0:
            self._draw_tutorial_hints()
        self._draw_achievement_flash()
        self.touch.draw(self.screen)
        # pause button is always visible during play
        self.touch.draw_pause_button(self.screen)
        self._draw_mute_indicator()

    def _draw_hud(self):
        hud_h = 32
        hud = pygame.Surface((SCREEN_W, hud_h), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 170))
        self.screen.blit(hud, (0, 0))

        # hearts (max display)
        hearts_x = self._draw_hearts(10, 8)
        score_t = self.font_bold.render(
            f"{self.score:06d}", True, (255, 240, 120))
        self.screen.blit(score_t, (max(110, hearts_x + 6), 8))
        hi_col = (255, 120, 180) if self.score > self.hi_score else (180, 180, 200)
        hi_t = self.smallfont.render(
            f"HI {max(self.hi_score, self.score):06d}", True, hi_col)
        self.screen.blit(hi_t, (260, 12))
        wname = WEAPON_NAMES.get(self.player.weapon, "RIFLE")
        wcol = WEAPON_COLORS.get(self.player.weapon, (255, 240, 100))
        if self.player.weapon != WEAPON_NORMAL:
            w_t = self.font_bold.render(
                f"{wname[0]}:{self.player.ammo}", True, wcol)
        else:
            w_t = self.font_bold.render(wname[0], True, wcol)
        self.screen.blit(w_t, (430, 8))
        # stage indicator
        stage_t = self.smallfont.render(
            f"ST {self.current_level_idx + 1}/{len(ALL_LEVELS)}",
            True, (200, 200, 220))
        self.screen.blit(stage_t, (SCREEN_W - 110, 12))

        # combo (only when > 1)
        if self.combo >= 2:
            mult = self._combo_multiplier()
            pulse = (math.sin(pygame.time.get_ticks() / 100) + 1) / 2
            base = (255, 240, 120) if mult == 1 else (
                (255, 180, 80) if mult == 2 else (255, 100, 80))
            col = (base[0],
                   int(base[1] * (0.8 + 0.2 * pulse)),
                   int(base[2] * (0.8 + 0.2 * pulse)))
            t = self.font_bold.render(
                f"COMBO x{self.combo}  ({mult}x)", True, col)
            self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 36))
            # combo timer bar
            bar_w = 80
            ratio = self.combo_timer / 180
            pygame.draw.rect(self.screen, (60, 30, 30),
                             (SCREEN_W // 2 - bar_w // 2, 56, bar_w, 3))
            pygame.draw.rect(self.screen, col,
                             (SCREEN_W // 2 - bar_w // 2, 56,
                              int(bar_w * ratio), 3))

        progress = min(1.0, self.player.x / max(1, self.level.width - 100))
        pygame.draw.rect(self.screen, (40, 40, 40),
                         (SCREEN_W - 160, 22, 140, 6))
        pygame.draw.rect(self.screen, (200, 200, 220),
                         (SCREEN_W - 160, 22, int(140 * progress), 6))

        if self.boss is not None and self.boss.alive:
            cam_x = self.level.camera.x
            if -120 < self.boss.x - cam_x < SCREEN_W + 120:
                bar_w = SCREEN_W - 240
                bar_x = 120
                bar_y = SCREEN_H - 28
                max_hp = getattr(self.boss, 'max_hp', 30)
                pygame.draw.rect(self.screen, (40, 0, 0),
                                 (bar_x, bar_y, bar_w, 14))
                ratio = max(0.0, self.boss.hp / max_hp)
                pygame.draw.rect(self.screen, (240, 40, 40),
                                 (bar_x, bar_y, int(bar_w * ratio), 14))
                pygame.draw.rect(self.screen, (255, 255, 255),
                                 (bar_x, bar_y, bar_w, 14), 1)
                boss_label = "FINAL BOSS" if isinstance(self.boss, MechBoss) else "BOSS"
                t = self.smallfont.render(boss_label, True, (255, 255, 255))
                self.screen.blit(t, (bar_x + bar_w // 2 - t.get_width() // 2,
                                     bar_y - 16))

        # Boss WARNING banner — blinks across screen centre when boss appears
        if self.boss_warning_timer > 0 and (self.boss_warning_timer // 6) % 2 == 0:
            band_h = 56
            band_y = SCREEN_H // 2 - band_h // 2
            band = pygame.Surface((SCREEN_W, band_h), pygame.SRCALPHA)
            band.fill((140, 0, 0, 150))
            self.screen.blit(band, (0, band_y))
            pygame.draw.rect(self.screen, (255, 60, 60),
                             (0, band_y, SCREEN_W, band_h), 2)
            wt = self.bigfont.render("! WARNING !", True, (255, 230, 80))
            self.screen.blit(wt, (SCREEN_W // 2 - wt.get_width() // 2,
                                  band_y + 6))
            boss_kind = "FINAL BOSS" if isinstance(self.boss, MechBoss) else "BOSS"
            st = self.smallfont.render(f"{boss_kind} APPROACHING", True,
                                       (255, 255, 255))
            self.screen.blit(st, (SCREEN_W // 2 - st.get_width() // 2,
                                  band_y + band_h - 16))

    def _draw_menu(self):
        self.screen.fill(DARK)
        for i in range(0, SCREEN_H, 4):
            pygame.draw.line(self.screen, (30, 30, 50),
                             (0, i), (SCREEN_W, i))
        title = self.bigfont.render("S H T U R M", True, (250, 80, 80))
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 40))
        sub = self.font.render("Pixel run-and-gun arcade  -  4 stages",
                               True, (180, 180, 180))
        self.screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 105))
        if self.hi_score > 0:
            hi_t = self.font_bold.render(
                f"HI-SCORE: {self.hi_score}", True, (255, 200, 80))
            self.screen.blit(hi_t,
                             (SCREEN_W // 2 - hi_t.get_width() // 2, 128))
        # difficulty selector
        diff_label = f"< {self.difficulty.label} >"
        dt = self.font_bold.render(diff_label, True, self.difficulty.color)
        self.screen.blit(dt, (SCREEN_W // 2 - dt.get_width() // 2,
                              SCREEN_H - 70))
        hint = self.smallfont.render(
            "ARROWS - CHANGE DIFFICULTY",
            True, (180, 180, 200))
        self.screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2,
                                SCREEN_H - 52))
        # hi-score top-5 panel (top-right)
        if self.hi_table:
            panel_x = SCREEN_W - 200
            panel_y = 50
            ht = self.font_bold.render("TOP 5", True, (255, 200, 80))
            self.screen.blit(ht, (panel_x, panel_y))
            for i, row in enumerate(self.hi_table):
                y = panel_y + 28 + i * 18
                line = f"{i+1}. {row['name']}  {row['score']}"
                col = (220, 220, 220) if i > 0 else (255, 240, 120)
                t = self.smallfont.render(line, True, col)
                self.screen.blit(t, (panel_x, y))
                # difficulty letter
                d = row['diff'][0].upper() if row.get('diff') else ' '
                dt = self.smallfont.render(d, True, (180, 180, 220))
                self.screen.blit(dt, (panel_x + 150, y))

        lines = [
            ("CONTROLS", (255, 255, 120)),
            ("ARROWS / AD - RUN    DOWN - DUCK", (220, 220, 220)),
            ("Z - JUMP    X - FIRE    C - DASH", (220, 220, 220)),
            ("P - PAUSE    (DASH = dodge with i-frames)", (170, 200, 230)),
            ("", (0, 0, 0)),
            ("PICKUPS", (255, 255, 120)),
            ("S SPREAD  M MACHINE  L LASER  1UP", (200, 220, 255)),
            ("", (0, 0, 0)),
            ("JUNGLE -> CAVES -> BASE -> SKY",
             (255, 200, 100)),
            ("", (0, 0, 0)),
            ("M MUTE   F CRT SCANLINES", (160, 200, 240)),
        ]
        y = 165
        for text, col in lines:
            t = self.font.render(text, True, col)
            self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, y))
            y += 24

        prompt = self.font_bold.render(
            "PRESS KEY / TAP TO START",
            True, (255, 240, 120))
        # blink
        if (pygame.time.get_ticks() // 400) % 2 == 0:
            self.screen.blit(prompt, (SCREEN_W // 2 - prompt.get_width() // 2,
                                      SCREEN_H - 30))

    def _draw_overlay(self, title, sub):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        t = self.bigfont.render(title, True, (250, 80, 80))
        self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2,
                             SCREEN_H // 2 - 80))
        sc = self.font_bold.render(f"FINAL SCORE: {self.score}",
                                   True, (255, 240, 120))
        self.screen.blit(sc, (SCREEN_W // 2 - sc.get_width() // 2,
                              SCREEN_H // 2 - 20))
        hi_t = self.font.render(f"HI-SCORE: {self.hi_score}",
                                True, (255, 200, 80))
        self.screen.blit(hi_t, (SCREEN_W // 2 - hi_t.get_width() // 2,
                                SCREEN_H // 2 + 10))
        if self.score >= self.hi_score and self.score > 0:
            # blink "NEW RECORD" when current run set the hi-score
            if (pygame.time.get_ticks() // 250) % 2 == 0:
                nr = self.font_bold.render("NEW RECORD!", True, (120, 255, 120))
                self.screen.blit(nr, (SCREEN_W // 2 - nr.get_width() // 2,
                                      SCREEN_H // 2 + 36))
        s = self.font.render(sub, True, (220, 220, 220))
        self.screen.blit(s, (SCREEN_W // 2 - s.get_width() // 2,
                             SCREEN_H // 2 + 70))

    def _draw_intro_overlay(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        level_def = ALL_LEVELS[self.current_level_idx]
        title = self.medfont.render(level_def.name, True, (250, 80, 80))
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2,
                                 SCREEN_H // 2 - 50))
        sub = self.font.render(
            "Get ready!", True, (255, 240, 120))
        self.screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2,
                               SCREEN_H // 2 + 10))
        prompt = self.smallfont.render(
            "(press any key / tap to skip)", True, (180, 180, 180))
        self.screen.blit(prompt, (SCREEN_W // 2 - prompt.get_width() // 2,
                                  SCREEN_H - 40))

    def _draw_achievement_flash(self):
        if self.achievement_timer <= 0 or not self.achievement_text:
            return
        # life ratio (1 → fresh, 0 → expired)
        ratio = self.achievement_timer / 90
        # rise from y=70 to y=50 over its life, fade out at the very end
        y = 70 - int((1 - ratio) * 20)
        alpha = int(255 * min(1.0, ratio * 2.5))
        # glowing background pill
        text_surf = self.medfont.render(self.achievement_text, True,
                                        (255, 220, 80))
        text_surf = text_surf.convert_alpha()
        text_surf.set_alpha(alpha)
        bg_w = text_surf.get_width() + 30
        bg_h = text_surf.get_height() + 12
        bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        bg.fill((40, 20, 0, min(180, alpha)))
        pygame.draw.rect(bg, (255, 220, 80, min(220, alpha)),
                         (0, 0, bg_w, bg_h), 2)
        bg_x = SCREEN_W // 2 - bg_w // 2
        self.screen.blit(bg, (bg_x, y))
        self.screen.blit(text_surf,
                         (SCREEN_W // 2 - text_surf.get_width() // 2,
                          y + 6))

    def _draw_hearts(self, x0, y0):
        """Pixel hearts representing remaining lives. lives counts spares
        (display = lives+1, since dying when lives==0 means no spare). Caps
        at 6 hearts; remainder shown as 'x N' text."""
        total = max(0, self.lives + 1)
        cap = 6
        shown = min(total, cap)
        size = 14
        gap = 3
        cx = x0
        for i in range(shown):
            self._draw_pixel_heart(cx, y0, size, filled=True)
            cx += size + gap
        if total > cap:
            t = self.smallfont.render(f"x{total}", True, (255, 150, 180))
            self.screen.blit(t, (cx + 2, y0 + 2))
            cx += t.get_width() + 4
        return cx

    def _draw_pixel_heart(self, x, y, size, filled=True):
        """Tiny pixel heart in size×size area."""
        col = (255, 80, 110) if filled else (60, 30, 40)
        outline = (180, 30, 50) if filled else (40, 20, 30)
        s = size
        # heart shape via two top circles + bottom triangle
        r = s // 4
        cx1 = x + r + 1
        cx2 = x + s - r - 1
        cy = y + r + 1
        pygame.draw.circle(self.screen, col, (cx1, cy), r)
        pygame.draw.circle(self.screen, col, (cx2, cy), r)
        pygame.draw.polygon(self.screen, col, [
            (x + 1, cy),
            (x + s - 1, cy),
            (x + s // 2, y + s - 1),
        ])
        # outline
        pygame.draw.circle(self.screen, outline, (cx1, cy), r, 1)
        pygame.draw.circle(self.screen, outline, (cx2, cy), r, 1)
        # subtle highlight (small white dot)
        if filled:
            pygame.draw.rect(self.screen, (255, 200, 220),
                             (cx1 - 1, cy - r // 2 - 1, 2, 2))

    def _draw_tutorial_hints(self):
        """Three soft hints next to the player at start of stage 1."""
        # fade-out near the end of the timer
        alpha = min(220, int(self.tutorial_timer * 1.2))
        if alpha <= 0:
            return
        player_screen_x = int(self.player.x - self.level.camera.x)
        player_screen_y = int(self.player.y)
        hints = []
        if not self.tutorial_moved:
            hints.append(("ARROWS / A-D - MOVE", -10, -60))
        if not self.tutorial_jumped:
            hints.append(("Z - JUMP", 50, -34))
        if not self.tutorial_shot:
            hints.append(("X - SHOOT", 50, -8))
        if self.tutorial_shot and not self.tutorial_dashed:
            hints.append(("C - DASH (dodge!)", 40, -52))
        for text, dx, dy in hints:
            t = self.font.render(text, True, (255, 240, 120))
            t = t.convert_alpha()
            t.set_alpha(alpha)
            tx = player_screen_x + dx
            ty = player_screen_y + dy
            # background pill for legibility
            bg = pygame.Surface((t.get_width() + 8, t.get_height() + 4),
                                pygame.SRCALPHA)
            bg.fill((0, 0, 0, min(160, alpha)))
            self.screen.blit(bg, (tx - 4, ty - 2))
            self.screen.blit(t, (tx, ty))

    def _draw_mute_indicator(self):
        """Tiny speaker icon to the left of the pause button."""
        if not self.muted:
            return
        cx = SCREEN_W - 60
        cy = 16
        surf = pygame.Surface((28, 22), pygame.SRCALPHA)
        # speaker body
        pygame.draw.rect(surf, (255, 255, 255, 180), (4, 7, 4, 8))
        pygame.draw.polygon(surf, (255, 255, 255, 180),
                            [(8, 6), (16, 2), (16, 20), (8, 16)])
        # diagonal red bar
        pygame.draw.line(surf, (255, 80, 80, 220), (2, 4), (24, 18), 3)
        self.screen.blit(surf, (cx - 14, cy - 11))

    def _draw_name_entry_overlay(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        title = self.medfont.render("NEW HIGH SCORE!", True, (255, 220, 80))
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2,
                                 SCREEN_H // 2 - 110))
        adjusted = int(round(self.score * self.difficulty.score_mult))
        sub = self.font_bold.render(
            f"SCORE: {adjusted}  ({self.difficulty.name.upper()})",
            True, (255, 240, 120))
        self.screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2,
                               SCREEN_H // 2 - 65))
        # 3 big letters
        slot_w = 64
        total_w = slot_w * 3
        x0 = SCREEN_W // 2 - total_w // 2
        for i, ch in enumerate(self.name_entry):
            cx = x0 + i * slot_w
            selected = (i == self.name_pos)
            bg_col = (60, 60, 100) if selected else (30, 30, 50)
            pygame.draw.rect(self.screen, bg_col,
                             (cx + 4, SCREEN_H // 2 - 20, slot_w - 8, 56))
            pygame.draw.rect(self.screen, (200, 200, 240),
                             (cx + 4, SCREEN_H // 2 - 20, slot_w - 8, 56), 2)
            col = (255, 240, 120) if selected else (220, 220, 220)
            t = self.bigfont.render(ch, True, col)
            self.screen.blit(t, (cx + slot_w // 2 - t.get_width() // 2,
                                 SCREEN_H // 2 - 16))
            if selected and (pygame.time.get_ticks() // 300) % 2 == 0:
                # blinking arrows
                pygame.draw.polygon(self.screen, (255, 240, 120),
                                    [(cx + slot_w // 2 - 6, SCREEN_H // 2 - 32),
                                     (cx + slot_w // 2 + 6, SCREEN_H // 2 - 32),
                                     (cx + slot_w // 2, SCREEN_H // 2 - 24)])
                pygame.draw.polygon(self.screen, (255, 240, 120),
                                    [(cx + slot_w // 2 - 6, SCREEN_H // 2 + 44),
                                     (cx + slot_w // 2 + 6, SCREEN_H // 2 + 44),
                                     (cx + slot_w // 2, SCREEN_H // 2 + 52)])
        hint = self.smallfont.render(
            "UP/DOWN - letter   LEFT/RIGHT - slot   Z/ENTER - confirm",
            True, (180, 180, 200))
        self.screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2,
                                SCREEN_H // 2 + 80))

    def _draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        title = self.bigfont.render("PAUSED", True, (255, 240, 120))
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2,
                                 SCREEN_H // 2 - 70))
        line1 = self.font_bold.render(
            "ESC / P / TAP - resume", True, (220, 220, 220))
        self.screen.blit(line1, (SCREEN_W // 2 - line1.get_width() // 2,
                                 SCREEN_H // 2 - 10))
        line2 = self.font.render(
            "ENTER / Q - quit to menu", True, (180, 180, 200))
        self.screen.blit(line2, (SCREEN_W // 2 - line2.get_width() // 2,
                                 SCREEN_H // 2 + 22))
        # mute hint
        mute_t = self.smallfont.render(
            f"M - {'unmute' if self.muted else 'mute'}",
            True, (160, 200, 240))
        self.screen.blit(mute_t, (SCREEN_W // 2 - mute_t.get_width() // 2,
                                  SCREEN_H // 2 + 50))

    def _draw_clear_overlay(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        title = self.medfont.render(
            f"STAGE {self.current_level_idx + 1} CLEAR!",
            True, (120, 240, 120))
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2,
                                 SCREEN_H // 2 - 70))
        bonus = self.font_bold.render(
            f"BONUS: +{self.bonus_score}", True, (255, 240, 120))
        self.screen.blit(bonus, (SCREEN_W // 2 - bonus.get_width() // 2,
                                 SCREEN_H // 2 - 20))
        sc = self.font_bold.render(
            f"SCORE: {self.score}", True, (255, 240, 120))
        self.screen.blit(sc, (SCREEN_W // 2 - sc.get_width() // 2,
                              SCREEN_H // 2 + 10))
        if self.current_level_idx + 1 < len(ALL_LEVELS):
            nxt = ALL_LEVELS[self.current_level_idx + 1].name
            sub = self.font.render(f"Next: {nxt}", True, (200, 220, 255))
            self.screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2,
                                   SCREEN_H // 2 + 50))


async def main():
    game = Game()
    # Best-effort VK Mini App init — no-op on desktop / outside VK
    try:
        await vk_bridge.init()
    except Exception:
        pass
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
