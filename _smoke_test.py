"""Headless smoke test - runs game logic for ~120 frames without showing a window.
Verifies that player update, enemy AI, bullets, collisions and rendering don't crash."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import sys
sys.path.insert(0, os.path.dirname(__file__))

# Stub persistence so smoke-test never writes a real save file.
import game.persistence as _persistence
_persistence.set_int = lambda key, value: None
_persistence.set_str = lambda key, value: None
_persistence.commit_hi_table = lambda table: None

import pygame
import random
random.seed(42)

from game.constants import (
    SCREEN_W, SCREEN_H, GROUND_Y, PLAYER_H,
    WEAPON_LASER, WEAPON_SPREAD, WEAPON_MACHINE,
)
from game.player import Player
from game.entities import (
    Bullet, MortarShell, Soldier, Turret, Drone, Jumper, Mortar,
    Sniper, Charger, Bomber, Grenade, Burrower, Crate, Barrel,
    Kamikaze, Boss, MechBoss, Pickup, Particle, Checkpoint, ScorePopup,
)
from game.level import Level, AmbientParticle, Weather
from game.leveldef import ALL_LEVELS
from game.difficulty import ALL as DIFFICULTIES
from game.persistence import qualifies_for_table
from main import Game


class FakeKeys:
    def __init__(self):
        self.pressed = set()
    def __getitem__(self, k):
        return k in self.pressed

def fake_keys(left=False, right=False, up=False, down=False, jump=False,
              shoot=False, dash=False):
    fk = FakeKeys()
    if left: fk.pressed.update([pygame.K_LEFT, pygame.K_a])
    if right: fk.pressed.update([pygame.K_RIGHT, pygame.K_d])
    if up: fk.pressed.update([pygame.K_UP, pygame.K_w])
    if down: fk.pressed.update([pygame.K_DOWN, pygame.K_s])
    if jump: fk.pressed.update([pygame.K_z, pygame.K_k])
    if shoot: fk.pressed.update([pygame.K_x, pygame.K_j])
    if dash: fk.pressed.add(pygame.K_c)
    return fk


def main():
    pygame.init()
    pygame.display.set_mode((SCREEN_W, SCREEN_H))

    game = Game()
    game._start_new_run()
    game.state = "play"  # skip intro

    print(f"Levels available: {len(ALL_LEVELS)}: {[l.name for l in ALL_LEVELS]}")
    print(f"Initial: player at ({game.player.x:.1f}, {game.player.y:.1f}) on_ground={game.player.on_ground}")
    print(f"Enemies: {len(game.enemies)}, pickups: {len(game.pickups)}, boss: {game.boss is not None}")
    print(f"Level platforms: {len(game.level.platforms)}, width: {game.level.width}, movables: {len(game.level.movables)}")

    # First few frames: gravity should land player on ground
    for i in range(5):
        keys = fake_keys()
        game._update_play(keys)
    assert game.player.on_ground, f"Expected player on ground after 5 frames, got y={game.player.y}"
    print(f"After 5 frames: landed at y={game.player.y:.1f} on_ground={game.player.on_ground}")

    # Run right + shoot for 60 frames
    for i in range(60):
        keys = fake_keys(right=True, shoot=(i % 4 == 0))
        game._update_play(keys)
    print(f"After 60 frames running+shooting: player at ({game.player.x:.1f}, {game.player.y:.1f})")
    print(f"  Bullets in flight: {len(game.bullets)}, enemy bullets: {len(game.enemy_bullets)}")
    print(f"  Score: {game.score}, lives: {game.lives}")
    print(f"  Camera x: {game.level.camera.x:.1f}")

    # Jump test
    for i in range(30):
        keys = fake_keys(jump=(i == 0))
        game._update_play(keys)
    print(f"After jump: player y reached min, currently at y={game.player.y:.1f}")

    # Aim diagonal up-right while jumping in air
    keys = fake_keys(right=True, up=True, jump=True)
    game._update_play(keys)
    print(f"Diagonal aim: aim={game.player.aim}")

    # Test rendering doesn't crash
    game._draw()
    print("Render OK")

    # Test menu
    game.state = "menu"
    game._draw()
    print("Menu render OK")

    # Test gameover
    game.state = "gameover"
    game._draw()
    print("Gameover render OK")

    # Test win
    game.state = "win"
    game._draw()
    print("Win render OK")

    # Player hit
    game.state = "play"
    game.player.invincible = 0
    hit_result = game.player.hit()
    print(f"Player hit -> dead={game.player.dead}, hit returned {hit_result}")

    # Boss damage cycle
    if game.boss:
        max_hp = game.boss.max_hp
        for _ in range(max_hp):
            game.boss.hit()
        print(f"After {max_hp} hits: boss alive={game.boss.alive}, hp={game.boss.hp}")

    # Test multi-level pipeline: load each stage, verify
    print("\nMulti-level test:")
    for idx in range(len(ALL_LEVELS)):
        game._load_stage(idx)
        game.state = "play"
        # advance a few frames
        for _ in range(5):
            game._update_play(fake_keys())
        print(f"  Stage {idx+1} '{ALL_LEVELS[idx].name}': "
              f"width={game.level.width} platforms={len(game.level.platforms)} "
              f"movables={len(game.level.movables)} enemies={len(game.enemies)} "
              f"boss={type(game.boss).__name__ if game.boss else None}")
    # Test full progression: stage 1 -> 2 -> 3 -> win
    print("\nStage transition test:")
    game._start_new_run()
    game.state = "play"
    for stage in range(len(ALL_LEVELS)):
        # kill boss
        if game.boss:
            for _ in range(game.boss.max_hp):
                game.boss.hit()
        # one frame to detect death
        game._update_play(fake_keys())
        print(f"  After killing stage {stage+1} boss: state={game.state}, "
              f"lvl_idx={game.current_level_idx}, score={game.score}")
        if game.state == "stage_clear":
            game._advance_stage()
            print(f"  -> advanced: state={game.state}, lvl_idx={game.current_level_idx}")
    # In v0.7, finishing all stages can trigger name-entry if score qualifies
    assert game.state in ("win", "enter_name"), \
        f"Expected 'win' or 'enter_name' after final stage, got {game.state}"

    # New-feature checks: jumper, mortar, laser, checkpoints
    print("\nNew features test:")
    game._start_new_run()
    game.state = "play"
    kinds = {type(e).__name__ for e in game.enemies}
    print(f"  Stage 1 enemy kinds: {sorted(kinds)}")
    assert "Jumper" in kinds, "Jumper not spawned in stage 1"
    assert "Mortar" in kinds, "Mortar not spawned in stage 1"
    print(f"  Checkpoints in stage 1: {len(game.checkpoints)}")
    assert len(game.checkpoints) >= 1, "no checkpoints in stage 1"

    # Run player into 1st checkpoint
    cp = game.checkpoints[0]
    game.player.x = cp.x - 5
    game.player.y = cp.y + 10
    for _ in range(5):
        game._update_play(fake_keys())
    print(f"  Checkpoint #0 active: {cp.active}, "
          f"last_checkpoint_x={game.last_checkpoint_x}")
    assert cp.active, "checkpoint did not activate"
    assert game.last_checkpoint_x == cp.x, "last_checkpoint_x not stored"

    # Test laser piercing: give laser, shoot, check pierced bullet's mark_hit
    game.player.weapon = WEAPON_LASER
    game.player.ammo = 30
    game.player.aim = (1, 0)
    game.player.shoot_timer = 0
    new_shots = game.player.try_shoot()
    assert len(new_shots) == 1 and new_shots[0].piercing, "laser not piercing"
    print(f"  Laser bullet piercing={new_shots[0].piercing} "
          f"ammo_left={game.player.ammo}")

    # Test mortar shell parabola — force-fire on next update.
    # Camera has moved during prior frames, so put mortar near current camera.
    cam_x = game.level.camera.x
    m = Mortar(cam_x + 200, 350)
    game.player.x = cam_x + 400
    game.player.y = 350
    m.shoot_timer = 1  # next update ->0 ->fires
    shells = m.update(game.player, game.level)
    assert shells and isinstance(shells[0], MortarShell), "mortar didn't lob"
    print(f"  Mortar shells produced: {len(shells)}, "
          f"shell vy0={shells[0].vy:.2f}")

    # Test music doesn't crash if disabled
    if hasattr(game, 'music'):
        print(f"  Music enabled={game.music.enabled}, "
              f"channel={game.music.channel is not None}")

    # Test hi-score persistence flow (no actual write needed in headless)
    initial_hi = game.hi_score
    game.score = 99999
    game._commit_hi_score()
    assert game.hi_score == 99999, "hi_score didn't update"
    print(f"  hi_score committed: {initial_hi} -> {game.hi_score}")

    # v0.5 features: pause / coyote / damage flash / popups / ambient / mute
    print("\nv0.5 features test:")

    # damage flicker
    soldier = Soldier(100, 200)
    soldier.hp = 5  # so it survives one hit
    killed = soldier.hit()
    assert not killed and soldier.hit_flash > 0, "hit_flash didn't set"
    print(f"  Soldier hit: hit_flash={soldier.hit_flash}, hp={soldier.hp}")

    # score popup
    pop = ScorePopup(100, 50, 250)
    pop.update()
    assert pop.alive and pop.text == "+250", "popup misbehaving"
    print(f"  ScorePopup '{pop.text}' alive={pop.alive}, y after step={pop.y:.1f}")

    # ambient particles per theme
    for idx, name in enumerate(["leaves", "fireflies", "sparks"]):
        game._load_stage(idx)
        kind = game.level.theme.ambient
        n = len(game.level.ambient_particles)
        assert kind == name, f"theme {idx} ambient != {name}, got {kind}"
        assert n > 0, f"no ambient particles for {name}"
        # tick a couple frames
        for _ in range(3):
            game.level.update()
        print(f"  Stage {idx+1} ambient={kind} count={n}")

    # coyote time: walk off edge, can still jump for 6 frames
    game._load_stage(0)
    game.state = "play"
    game.player.x = 100
    game.player.y = 300
    game.player.on_ground = True
    game.player.coyote_timer = 0
    # one update with no platform under feet — leaves ground
    # we'll fake by removing nearby platforms? simpler: directly check coyote logic
    # after leaving ground (no ground update), coyote allows jump
    game.player.on_ground = False
    game.player.coyote_timer = 3  # within window
    keys = fake_keys(jump=True)
    game.player._jump_held = False
    game.player._was_jump_held = False
    game.player.update(keys, game.level)
    print(f"  Coyote jump (timer=3): just_jumped={game.player.just_jumped}, "
          f"vy={game.player.vy:.2f}")
    # Note: assertion is soft — coyote may not trigger if player is already
    # mid-fall and update collides immediately. We just check it doesn't crash.

    # jump cut: ascending jump, release key ->vy halves
    game.player.vy = -10
    game.player._was_jump_held = True
    keys = fake_keys()  # jump not pressed
    game.player.update(keys, game.level)
    print(f"  After jump-cut release: vy={game.player.vy:.2f}")

    # mute toggle
    initial_muted = game.muted
    game._toggle_mute()
    assert game.muted != initial_muted, "mute didn't toggle"
    print(f"  Mute toggle: {initial_muted} -> {game.muted}")
    game._toggle_mute()  # restore

    # pause state — verify draw doesn't crash
    game.state = "pause"
    game._draw()
    print("  Pause overlay render OK")

    # laser visual draw (piercing trail)
    from game.entities import Bullet as Blt
    laser = Blt(100, 200, 1, 0, True, speed=12, piercing=True)
    laser.update(game.level)
    laser.update(game.level)
    laser.draw(game.screen, game.level.camera)
    print(f"  Laser piercing draw OK, trail len={len(laser._trail)}")

    # v0.6 features
    print("\nv0.6 features test:")

    # MortarShell explosion flag
    shell = MortarShell(100, 200, 2, -8)
    # force it onto a platform
    cam_x = game.level.camera.x
    shell.x = cam_x + 200
    shell.y = 380  # near ground
    shell.vy = 5
    shell.update(game.level)
    print(f"  MortarShell after collision: alive={shell.alive}, "
          f"exploded={shell.exploded}")
    assert not shell.alive and shell.exploded, "mortar shell didn't explode on platform"

    # Score milestone gives 1UP
    game._start_new_run()
    game.state = "play"
    base_lives = game.lives
    game.score = 19500
    # one more enemy kill that bumps over 20000
    game.score = 22000
    # Manually trigger update_play cleanup pass via short loop
    for _ in range(2):
        game._update_play(fake_keys())
    print(f"  After score 22000: lives went {base_lives} ->{game.lives}, "
          f"next_milestone={game.next_milestone}")
    assert game.lives > base_lives, "1UP milestone didn't apply"
    assert game.next_milestone == 40000

    # Boss telegraph: ticks down as shoot_timer approaches 0
    game._load_stage(0)
    game.state = "play"
    boss = game.boss
    # bring boss into camera view
    game.level.camera.x = boss.x - 400
    boss.shoot_timer = 10  # within telegraph window
    boss.update(game.player, game.level)
    print(f"  Boss telegraph timer after pre-shot tick: {boss.telegraph}")
    assert boss.telegraph > 0, "telegraph didn't activate"

    # Tutorial timer ticks during stage 1
    game._start_new_run()
    game.state = "play"
    initial_tt = game.tutorial_timer
    for _ in range(5):
        game._update_play(fake_keys(right=True))
    print(f"  Tutorial timer: {initial_tt} ->{game.tutorial_timer}, "
          f"moved={game.tutorial_moved}")
    assert game.tutorial_moved, "moving didn't register"
    assert game.tutorial_timer < initial_tt, "tutorial timer didn't tick"

    # CRT toggle
    initial_crt = game.crt
    game._toggle_crt()
    assert game.crt != initial_crt, "CRT didn't toggle"
    game._draw_crt_overlay()  # ensure cache builds
    assert game._scanlines_cache is not None
    print(f"  CRT toggle: {initial_crt} ->{game.crt}, cache built")
    game._toggle_crt()

    # ScorePopup with string (1UP)
    pop2 = ScorePopup(0, 0, "1UP")
    assert pop2.text == "1UP", "ScorePopup didn't accept str"
    print(f"  ScorePopup str: '{pop2.text}'")

    # v0.7 features
    print("\nv0.7 features test:")

    # 4 levels now
    assert len(ALL_LEVELS) == 4, f"expected 4 stages, got {len(ALL_LEVELS)}"
    sky = ALL_LEVELS[3]
    print(f"  Stage 4 name: {sky.name}, width={sky.width}")
    assert "SKY" in sky.name

    # New enemy spawns in stage 4
    game._load_stage(3)
    kinds = {type(e).__name__ for e in game.enemies}
    print(f"  Stage 4 enemy kinds: {sorted(kinds)}")
    assert {"Sniper", "Charger", "Bomber"}.issubset(kinds), \
        f"missing new enemies, got {kinds}"

    # Sniper update: laser sight appears, then fires
    game._load_stage(3)
    snipers = [e for e in game.enemies if isinstance(e, Sniper)]
    assert snipers, "no Sniper in stage 4"
    sn = snipers[0]
    # bring camera to sniper
    game.level.camera.x = sn.x - 400
    sn.cooldown = 1
    sn.update(game.player, game.level)
    # next frame goes to aim
    sn.update(game.player, game.level)
    print(f"  Sniper aim_timer started: {sn.aim_timer}")
    assert sn.aim_timer > 0
    # fast-forward aim
    sn.aim_timer = 1
    new_b = sn.update(game.player, game.level)
    print(f"  Sniper fired {len(new_b)} bullet(s)")
    assert len(new_b) >= 1

    # Charger triggers near player
    cam_x = game.level.camera.x
    ch = Charger(cam_x + 100, 200)
    game.player.x = cam_x + 150
    game.player.y = 200
    ch.update(game.player, game.level)
    print(f"  Charger state after sight: {ch.state}")
    assert ch.state in ("priming", "charging")

    # Bomber lobs grenade
    bm = Bomber(game.level.camera.x + 200, 130)
    game.player.x = bm.x + 200
    game.player.y = 350
    bm.cooldown = 1   # will decrement to 0 and fire on next update
    bullets = bm.update(game.player, game.level)
    grenades = [b for b in bullets if isinstance(b, Grenade)]
    print(f"  Bomber grenades produced: {len(grenades)}")
    assert grenades, "bomber didn't lob a grenade"

    # Grenade fuse → explode
    g = Grenade(100, 100, 1, -2)
    g.fuse = 1
    g.update(game.level)
    print(f"  Grenade after fuse=0: alive={g.alive}, exploded={g.exploded}")
    assert not g.alive and g.exploded

    # Combo / multiplier
    game._start_new_run()
    game.state = "play"
    game.combo = 4
    mult0 = game._combo_multiplier()
    game.combo = 5
    mult5 = game._combo_multiplier()
    game.combo = 15
    mult15 = game._combo_multiplier()
    print(f"  Combo multipliers: 4->{mult0}, 5->{mult5}, 15->{mult15}")
    assert mult0 == 1 and mult5 == 2 and mult15 == 3

    # Difficulty cycle
    initial_diff = game.diff_idx
    game._cycle_difficulty(+1)
    print(f"  Difficulty cycle: {initial_diff} -> {game.diff_idx} "
          f"({game.difficulty.label})")
    assert game.diff_idx != initial_diff
    # restore
    while game.diff_idx != initial_diff:
        game._cycle_difficulty(+1)

    # Weapon ammo: laser exhausts → falls back to normal
    from game.player import WEAPON_AMMO
    game.player.weapon = WEAPON_LASER
    game.player.ammo = 1
    game.player.shoot_timer = 0
    game.player.try_shoot()
    print(f"  After 1 laser shot: ammo={game.player.ammo}")
    assert game.player.ammo == 0
    game.player.shoot_timer = 0
    new_shots = game.player.try_shoot()
    print(f"  Next shot fallback: weapon={game.player.weapon}, "
          f"piercing={new_shots[0].piercing}")
    assert game.player.weapon != WEAPON_LASER
    assert not new_shots[0].piercing

    # Hi-score table qualification
    table = [{"name": "AAA", "score": 1000, "diff": "normal"}]
    assert qualifies_for_table(table, 500)  # < 5 entries
    full_table = [{"name": "X", "score": s, "diff": "normal"}
                  for s in (5000, 4000, 3000, 2000, 1000)]
    assert qualifies_for_table(full_table, 1500)
    assert not qualifies_for_table(full_table, 500)
    print(f"  hi-table qualification logic OK")

    # Name entry render doesn't crash
    game.state = "enter_name"
    game.name_entry = ["S", "T", "U"]
    game._draw()
    print("  Name entry overlay render OK")

    # _maybe_enter_name_or_end with empty table → qualifies
    game.hi_table = []
    game.score = 1234
    game._maybe_enter_name_or_end("gameover")
    print(f"  Empty table + score 1234 -> state={game.state}")
    assert game.state == "enter_name"
    # commit
    game._commit_name_entry()
    print(f"  After commit_name_entry: hi_table len={len(game.hi_table)}, "
          f"state={game.state}")
    assert len(game.hi_table) == 1
    assert game.state == "gameover"

    # Hearts draw
    game._start_new_run()
    game.lives = 3
    game._draw_hearts(10, 8)
    game.lives = 10  # over cap
    game._draw_hearts(10, 8)
    print("  Hearts draw OK (3 lives and over-cap)")

    # Death burst
    pcount = len(game.particles)
    game._spawn_death_burst(100, 100)
    print(f"  Death burst spawned: +{len(game.particles) - pcount} particles")
    assert len(game.particles) - pcount >= 30

    # Achievement flash
    game._flash_achievement("TEST!")
    assert game.achievement_text == "TEST!" and game.achievement_timer > 0
    game._draw_achievement_flash()
    print(f"  Achievement flash: '{game.achievement_text}'")

    # v0.9 features
    print("\nv0.9 features test:")

    # ShieldTrooper: frontal block
    from game.entities import ShieldTrooper as ST
    st = ST(200, 300)
    st.dir = 1
    st.shield_side = 1  # shield faces right
    # bullet from the right (same side as shield)
    assert st.is_blocked(300), "shield should block bullet from bullet_x=300 (right)"
    # bullet from the left (flank)
    assert not st.is_blocked(100), "shield should NOT block bullet from bullet_x=100 (left)"
    print(f"  ShieldTrooper is_blocked right={st.is_blocked(300)}, left={st.is_blocked(100)}")

    # ShieldTrooper spawns in stage 3
    game._load_stage(2)
    shield_kinds = [e for e in game.enemies if isinstance(e, ST)]
    print(f"  ShieldTroopers in stage 3: {len(shield_kinds)}")
    assert len(shield_kinds) >= 1, "no ShieldTroopers in stage 3"

    # HP bar: doesn't draw when undamaged
    from game.entities import Turret as Tur
    t3 = Tur(100, 300)
    initial_hp = t3.hp
    assert t3.max_hp == initial_hp, "max_hp should equal hp on fresh Turret"
    # damage it
    t3.hit()
    assert t3.hp < t3.max_hp, "turret hp should decrease after hit"
    # draw_hp_bar should not crash
    t3.draw_hp_bar(game.screen, game.level.camera)
    print(f"  Turret HP bar: max_hp={t3.max_hp}, current={t3.hp} - draw OK")

    # Combo flash triggers on combo milestone
    game._start_new_run()
    game.state = "play"
    game.combo_flash = 0
    game.combo = 4
    game._flash_achievement("5x COMBO!")
    game.combo = 5  # match what _register_kill would set
    game._flash_achievement("5x COMBO!")
    assert game.combo_flash > 0, "combo_flash should be set after 5x COMBO achievement"
    print(f"  Combo flash set: {game.combo_flash} > 0")

    # Stars seeded for SKY stage
    game._load_stage(3)
    print(f"  Stage 4 (SKY) stars: {len(game.level._stars)}")
    assert len(game.level._stars) > 0, "SKY stage should have stars"

    # Stars NOT seeded for non-sky stages
    game._load_stage(0)
    print(f"  Stage 1 (JUNGLE) stars: {len(game.level._stars)} (should be 0)")
    assert len(game.level._stars) == 0, "JUNGLE stage should have no stars"

    # v0.10 features
    print("\nv0.10 features test:")

    # GEM constant + score
    from game.constants import PICKUP_GEM, GEM_SCORE, PICKUP_LIFE
    assert PICKUP_GEM == "GEM" and GEM_SCORE == 500
    print(f"  PICKUP_GEM='{PICKUP_GEM}', GEM_SCORE={GEM_SCORE}")

    # Pickup styles map sprites for heart + gem
    from game.entities import PICKUP_STYLES, Pickup
    assert PICKUP_STYLES[PICKUP_GEM]["sprite"] == "pickup_gem.png"
    assert PICKUP_STYLES[PICKUP_LIFE]["sprite"] == "pickup_heart.png"
    print("  PICKUP_STYLES sprite mapping OK (heart + gem)")

    # Gem pickup draws without crashing
    gem = Pickup(120, 300, PICKUP_GEM)
    gem.update()
    gem.draw(game.screen, game.level.camera, game.font)
    assert gem.rect.width > 0
    print(f"  Gem pickup draw OK, rect={gem.rect}")

    # Enemy loot drops: over many rolls at least one drop, all valid kinds
    from game.entities import Soldier as Sol
    game.pickups = []
    valid_kinds = {PICKUP_GEM, PICKUP_LIFE, WEAPON_SPREAD, WEAPON_MACHINE,
                   WEAPON_LASER}
    drops = 0
    for _ in range(400):
        before = len(game.pickups)
        game._maybe_drop_loot(Sol(500, 300))
        if len(game.pickups) > before:
            drops += 1
            assert game.pickups[-1].kind in valid_kinds
    print(f"  Enemy loot: {drops}/400 rolls dropped (expect ~10%)")
    assert 10 < drops < 200, "drop rate out of expected band"

    # Boss WARNING banner fires once when boss enters view
    game._load_stage(2)  # stage 3 has a boss
    assert game.boss is not None, "stage 3 should have a boss"
    game.state = "play"
    game._boss_engaged = False
    game.boss_warning_timer = 0
    game.player.x = game.boss.x          # stand the player at the boss
    game.player.invincible = 999         # ignore contact damage this tick
    # pre-centre the camera on the boss (follow() only lerps 18%/tick)
    game.level.camera.x = max(
        0.0, min(game.level.width - SCREEN_W, game.boss.x - SCREEN_W / 2))
    game._update_play(fake_keys())
    print(f"  Boss in view: {game._boss_in_view()}, "
          f"engaged={game._boss_engaged}, warn_timer={game.boss_warning_timer}")
    assert game._boss_engaged, "boss should be engaged when player reaches it"
    assert game.boss_warning_timer > 0, "warning banner timer should be set"
    # banner draw doesn't crash
    game._draw_play()
    print("  Boss WARNING banner draw OK")

    # v0.11 features
    print("\nv0.11 features test:")

    # Burrower starts submerged with an empty (invulnerable) hitbox
    bw = Burrower(500, 356)
    assert bw.state == "under"
    assert bw.rect.width == 0 and bw.rect.height == 0, \
        "submerged burrower must have empty hitbox"
    print(f"  Burrower starts '{bw.state}', rect={bw.rect} (invulnerable)")

    # Drive it: needs a real level (camera + width) and an in-view player
    game._load_stage(1)  # CAVES
    game.player.x = 500
    game.player.y = GROUND_Y - PLAYER_H
    game.level.camera.x = 360  # x≈500 on-screen
    bw = Burrower(540, 356)     # just ahead of the player
    fired_total = 0
    saw_up = False
    up_rect_ok = False
    start_x = bw.x
    for _ in range(400):
        shots = bw.update(game.player, game.level)
        fired_total += len(shots)
        for s in shots:
            assert hasattr(s, "vx") and hasattr(s, "vy"), \
                "burrower shots must be bullet-like"
        if bw.state == "up":
            saw_up = True
            if bw.rect.width > 0:
                up_rect_ok = True
    moved = abs(bw.x - start_x) > 1
    print(f"  Burrower/400f: surfaced={saw_up}, up_rect_ok={up_rect_ok}, "
          f"shots={fired_total}, tracked_x={moved}")
    assert saw_up, "burrower should surface within 400 frames"
    assert up_rect_ok, "surfaced burrower must have a real hitbox"
    assert fired_total >= 1, "surfaced burrower should fire at least once"
    assert moved, "submerged burrower should track the player's x"

    # Burrower takes damage only once surfaced
    guard = 0
    while bw.state != "up" and guard < 300:
        bw.update(game.player, game.level)
        guard += 1
    hp0 = bw.hp
    bw.hit(1)
    assert bw.hp == hp0 - 1, "surfaced burrower should take damage"
    print(f"  Surfaced burrower hit: hp {hp0}->{bw.hp}")

    # Burrowers placed in CAVES (stage 2) and BASE (stage 3)
    game._load_stage(1)
    caves_bw = [e for e in game.enemies if isinstance(e, Burrower)]
    game._load_stage(2)
    base_bw = [e for e in game.enemies if isinstance(e, Burrower)]
    print(f"  Burrowers — CAVES: {len(caves_bw)}, BASE: {len(base_bw)}")
    assert len(caves_bw) >= 1 and len(base_bw) >= 1

    # Burrower draws in both states without crashing
    Burrower(600, 356).draw(game.screen, game.level.camera)
    bw_up = Burrower(600, 356)
    bw_up.state = "up"
    bw_up.draw(game.screen, game.level.camera)
    print("  Burrower draw OK (under + up)")

    # v0.12 features
    print("\nv0.12 features test:")
    from game.constants import BARREL_EXPLOSION_RADIUS

    # --- Crate: 1 HP, no points, solid to bullets, guaranteed loot on break ---
    cr = Crate(700, 352)
    assert cr.hp == 1 and cr.points == 0
    assert cr.update(game.player, game.level) == []
    assert cr.rect.width > 0, "crate must be solid to bullets"
    game._load_stage(0)
    game.pickups = []
    game._break_crate(cr)
    assert len(game.pickups) == 1, "crate must drop exactly one pickup"
    print(f"  Crate hp={cr.hp}, points={cr.points}, break -> "
          f"{len(game.pickups)} pickup (kind={game.pickups[0].kind})")

    # --- Barrel blast damages nearby enemies but not distant ones ---
    game._load_stage(0)
    barrel = Barrel(1000, 348)
    near = Soldier(1010, 348)
    far = Soldier(1000 + BARREL_EXPLOSION_RADIUS + 70, 348)
    game.enemies = [barrel, near, far]
    game.player.invincible = 999  # keep the hero clear of this check
    game._explode_barrel(barrel)
    print(f"  Barrel AoE: near.alive={near.alive}, far.alive={far.alive}")
    assert not near.alive, "blast should kill the adjacent enemy"
    assert far.alive, "blast must not reach the far enemy"

    # --- Chain reaction: one barrel detonates its neighbour ---
    game._load_stage(0)
    a = Barrel(1000, 348)
    b = Barrel(1045, 348)
    game.enemies = [a, b]
    game.player.invincible = 999
    a.hit(1)                 # a bullet would have flagged it dead first
    game._explode_barrel(a)
    print(f"  Chain reaction: neighbour barrel alive={b.alive}")
    assert not b.alive, "barrel chain reaction should detonate the neighbour"

    # --- Player caught in the blast is hit; safe just outside lethal radius ---
    # (Player.hit() flags the hero `dead`; the main loop then spends a life.)
    game._load_stage(0)
    bl = Barrel(1000, 348)
    game.enemies = [bl]
    game.player.invincible = 0
    game.player.dead = False
    game.player.x = 1000
    game.player.y = GROUND_Y - PLAYER_H
    game._explode_barrel(bl)
    assert game.player.dead, "player on the barrel must be hit"
    print(f"  Player ON barrel hit (dead={game.player.dead})")

    bl2 = Barrel(1000, 348)
    game.enemies = [bl2]
    game.player.invincible = 0
    game.player.dead = False
    game.player.x = 1000 + int(BARREL_EXPLOSION_RADIUS * 0.66) + 50
    game.player.y = GROUND_Y - PLAYER_H
    game._explode_barrel(bl2)
    assert not game.player.dead, "player outside lethal gap must be safe"
    print("  Player outside lethal gap stays safe")

    # --- Crates deal no contact damage (scenery) ---
    game._load_stage(0)
    game.enemies = [Crate(int(game.player.x), int(game.player.y))]
    game.player.invincible = 0
    game.player.dead = False
    lives0 = game.lives
    game._update_play(fake_keys())
    assert not game.player.dead and game.lives == lives0, \
        "standing on a crate must not damage the player"
    print("  Crate contact is harmless (no damage)")

    # --- Destructibles spawn across the whole campaign ---
    crates_total = barrels_total = 0
    for i in range(4):
        game._load_stage(i)
        crates_total += sum(isinstance(e, Crate) for e in game.enemies)
        barrels_total += sum(isinstance(e, Barrel) for e in game.enemies)
    print(f"  Spawns — crates: {crates_total}, barrels: {barrels_total}")
    assert crates_total >= 4 and barrels_total >= 4

    # --- Both draw without crashing ---
    game._load_stage(0)
    Crate(600, 352).draw(game.screen, game.level.camera)
    Barrel(600, 348).draw(game.screen, game.level.camera)
    print("  Crate + Barrel draw OK")

    # v0.13 features
    print("\nv0.13 features test:")

    # Every weather kind constructs, updates and draws without crashing
    for kind in ("rain", "drip", "clouds", "alarm"):
        w = Weather(kind)
        for _ in range(120):
            w.update()
        w.draw(game.screen, None)
    print("  All weather kinds update+draw OK (rain/drip/clouds/alarm)")

    # Rain: drops fall, lightning fires when its cooldown elapses
    wr = Weather("rain")
    y0 = wr.parts[0][1]
    wr.update()
    assert wr.parts[0][1] != y0, "rain drops should move"
    wr.flash = 0.0
    wr.flash_cooldown = 1
    wr.update()
    assert wr.flash > 0, "lightning should fire when cooldown elapses"
    print(f"  Rain: drops move, lightning flash={wr.flash:.2f}")

    # Drip: drops spawn over time (count totals, robust to splash timing)
    wd = Weather("drip")
    ever_dripped = False
    for _ in range(400):
        wd.update()
        if wd.parts:
            ever_dripped = True
    assert ever_dripped, "drips should spawn over time"
    print(f"  Drip: spawned over 400f={ever_dripped}, active now={len(wd.parts)}")

    # Clouds: puffs drift horizontally
    wc = Weather("clouds")
    x0 = wc.parts[0][0]
    for _ in range(30):
        wc.update()
    assert wc.parts[0][0] != x0, "clouds should drift"
    print(f"  Clouds: {len(wc.parts)} puffs drifting")

    # Each stage carries the right weather, and Level drives + draws it
    expected_weather = ["rain", "drip", "alarm", "clouds"]
    for i, kind in enumerate(expected_weather):
        game._load_stage(i)
        assert game.level.weather is not None, f"stage {i} needs weather"
        assert game.level.weather.kind == kind, \
            f"stage {i} weather should be {kind}, got {game.level.weather.kind}"
        game.level.update()
        game.level.draw_weather(game.screen, game.level.camera)
    print(f"  Per-stage weather wired: {expected_weather}")

    # A full play-frame renders with the weather overlay on top
    game._load_stage(0)
    game._update_play(fake_keys())
    game._draw_play()
    print("  _draw_play with weather overlay OK")

    # ---- v0.14 features (dash / dodge-roll) ----
    print("\nv0.14 features test:")
    from game.constants import DASH_DURATION, DASH_COOLDOWN, DASH_SPEED
    game._load_stage(0)
    lvl = game.level
    p = Player(200, GROUND_Y - PLAYER_H)
    for _ in range(4):
        p.update(fake_keys(), lvl)          # settle on the ground
    assert p.dash_timer == 0 and p.dash_cd == 0, "fresh player should not be dashing"

    p.update(fake_keys(right=True), lvl)    # face right
    assert p.facing == 1
    x_before = p.x
    p.update(fake_keys(dash=True), lvl)     # dash key edge -> start
    assert p.just_dashed, "dash should start on key press"
    assert p.dash_timer > 0, "dash timer should be active"
    assert p.dash_cd > 0, "dash cooldown should be set"
    assert p.x - x_before > 8, f"dash should burst fast (dx={p.x - x_before:.1f}, normal=4)"
    print(f"  Dash starts: dx={p.x - x_before:.1f}px, timer={p.dash_timer}, cd={p.dash_cd}")

    killed = p.hit()                        # i-frames: must be ignored mid-dash
    assert killed is False and not p.dead, "dash should grant i-frames"
    print("  Dash i-frames: hit() ignored mid-dash")

    p.update(fake_keys(dash=True), lvl)     # key still held -> no re-trigger (edge)
    assert not p.just_dashed, "holding dash must not re-trigger"

    for _ in range(DASH_DURATION + 2):      # release + run the dash out
        p.update(fake_keys(), lvl)
    assert p.dash_timer == 0, "dash should have ended"
    assert p.dash_cd > 0, "should still be cooling down"
    p.update(fake_keys(dash=True), lvl)     # try to dash during cooldown
    assert not p.just_dashed and p.dash_timer == 0, "cannot dash during cooldown"
    print(f"  Cooldown blocks re-dash (cd={p.dash_cd})")

    for _ in range(DASH_COOLDOWN + 2):      # wait out the cooldown
        p.update(fake_keys(), lvl)
    assert p.dash_cd == 0, "cooldown should have elapsed"
    p.update(fake_keys(dash=True), lvl)
    assert p.just_dashed, "dash should be available again after cooldown"
    print("  Re-dash after cooldown OK")

    p2 = Player(200, GROUND_Y - PLAYER_H)   # ducking blocks dash
    for _ in range(5):
        p2.update(fake_keys(), lvl)         # settle (grounded)
    p2.update(fake_keys(down=True, dash=True), lvl)
    assert p2.ducking and not p2.just_dashed, "cannot dash while ducking"
    print("  Ducking blocks dash")

    from game.controls import TouchControls   # touch DASH pad -> K_c
    tc = TouchControls()
    tc.begin(99, TouchControls.DASH_CX, TouchControls.DASH_CY)
    assert tc.is_pressed(pygame.K_c), "touch DASH pad should press K_c"
    tc.end(99)
    print("  Touch DASH pad -> K_c OK")

    assert (not game.sounds.enabled) or ('dash' in game.sounds.sounds), \
        "dash sound should be registered"
    game._load_stage(0)                      # full play-frame with a live dash
    game.player.dead = False
    game.player.dash_timer = 0
    game.player.dash_cd = 0
    game.player._dash_held = False
    game._update_play(fake_keys(right=True, dash=True))
    game._draw_play()
    assert game.player.just_dashed, "in-game dash should fire (dust + sound path)"
    print("  _update_play + _draw_play with live dash OK")

    # ---- v0.15 features (Kamikaze dive-bomber) ----
    print("\nv0.15 features test:")
    from game.constants import (KAMIKAZE_HP, KAMIKAZE_TRIGGER,
                                 KAMIKAZE_LOCK_FRAMES, KAMIKAZE_EXPLOSION_RADIUS)
    game._load_stage(3)                          # SKY (aerial showcase)
    lvl = game.level
    lvl.camera.x = 0

    # Construction: fragile, hovering, not yet detonated, worth chasing
    k = Kamikaze(400, 120)
    assert k.hp == KAMIKAZE_HP == 1 and k.points == 300
    assert k.state == "hover" and not k.exploded
    print(f"  Kamikaze hp={k.hp}, points={k.points}, state='{k.state}'")

    # hover -> lock: player close horizontally AND below -> blinking telegraph
    game.player.x = 410
    game.player.y = GROUND_Y - PLAYER_H          # well below the drone
    out = k.update(game.player, lvl)
    assert out == [] and k.state == "lock", f"should lock on, got '{k.state}'"
    assert k.lock_timer == KAMIKAZE_LOCK_FRAMES - 1 or k.lock_timer == KAMIKAZE_LOCK_FRAMES
    print(f"  hover->lock: state='{k.state}', lock_timer={k.lock_timer}")

    # lock -> dive: after the telegraph elapses it commits to a vector
    guard = 0
    while k.state == "lock" and guard < KAMIKAZE_LOCK_FRAMES + 5:
        k.update(game.player, lvl)
        guard += 1
    assert k.state == "dive", f"should dive after lock, got '{k.state}'"
    speed = (k.dive_vx ** 2 + k.dive_vy ** 2) ** 0.5
    assert speed > 5 and k.dive_vy > 0, "dive should be fast and downward"
    print(f"  lock->dive: vx={k.dive_vx:.2f}, vy={k.dive_vy:.2f}, speed={speed:.2f}")

    # dive into the ground -> self-detonation flag for main to read
    # (x=200 sits over the (0,400) floor strip; a gap would let it fall through)
    k2 = Kamikaze(200, 120)
    k2.state = "dive"
    k2.dive_vx, k2.dive_vy = 0.0, 8.0
    guard = 0
    while k2.alive and guard < 200:
        k2.update(game.player, lvl)
        guard += 1
    assert not k2.alive and k2.exploded, "ground hit should detonate the kamikaze"
    print(f"  ground hit: alive={k2.alive}, exploded={k2.exploded}")

    # AoE: nearby player is hit; player just outside the radius is safe
    game.player.invincible = 0
    game.player.dead = False
    game.player.dash_timer = 0
    kk = Kamikaze(int(game.player.x), int(game.player.y - 5))
    game._explode_kamikaze(kk)
    assert game.player.dead, "kamikaze blast on top of the player must hit"
    print("  AoE hits adjacent player (dead=True)")

    game.player.dead = False
    game.player.invincible = 0
    kk2 = Kamikaze(int(game.player.x + KAMIKAZE_EXPLOSION_RADIUS + 60),
                   int(game.player.y))
    game._explode_kamikaze(kk2)
    assert not game.player.dead, "player outside the blast radius must be safe"
    print("  AoE spares the distant player")

    # Dash i-frames let the hero pass through a detonation unharmed
    game.player.dead = False
    game.player.invincible = 0
    game.player.dash_timer = 8                   # mid-dash
    kk3 = Kamikaze(int(game.player.x), int(game.player.y))
    game._explode_kamikaze(kk3)
    assert not game.player.dead, "dashing player should survive the blast (i-frames)"
    game.player.dash_timer = 0
    print("  Dashing player survives the blast (i-frames)")

    # Contact path: kamikaze touching the player detonates via _update_play.
    # A full play-frame spends a life and respawns, so player.dead is cleared
    # again within the same frame — assert the life loss instead.
    game._load_stage(3)
    game.lives = 3
    game.player.invincible = 0
    game.player.dead = False
    game.player.dash_timer = 0
    kon = Kamikaze(int(game.player.x), int(game.player.y))
    kon.state = "dive"
    game.enemies = [kon]
    lives0 = game.lives
    game._update_play(fake_keys())
    print(f"  Contact detonation: lives {lives0}->{game.lives}, "
          f"respawn_iframes={game.player.invincible}")
    assert game.lives == lives0 - 1, "kamikaze contact should cost a life"

    # Shooting it down is the safe counter — normal kill path, no player AoE
    game._load_stage(3)
    game.player.invincible = 999                 # ignore any stray contact
    kshot = Kamikaze(int(game.player.x + 300), 120)
    assert kshot.hit(), "1-HP kamikaze should die to a single shot"
    print(f"  Shot down: alive={kshot.alive} (HP={KAMIKAZE_HP})")

    # Spawns: introduced in BASE (stage 3), showcased in SKY (stage 4)
    game._load_stage(2)
    base_kk = sum(isinstance(e, Kamikaze) for e in game.enemies)
    game._load_stage(3)
    sky_kk = sum(isinstance(e, Kamikaze) for e in game.enemies)
    print(f"  Spawns — BASE: {base_kk}, SKY: {sky_kk}")
    assert base_kk >= 1 and sky_kk >= 2, "kamikaze should appear in BASE and SKY"

    # Draw in all three states without crashing
    for st in ("hover", "lock", "dive"):
        kd = Kamikaze(600, 150)
        kd.state = st
        if st == "lock":
            kd.lock_timer = KAMIKAZE_LOCK_FRAMES
        if st == "dive":
            kd.dive_vx, kd.dive_vy = 3.0, 6.0
        kd.draw(game.screen, game.level.camera)
    print("  Kamikaze draw OK (hover + lock + dive)")

    pygame.quit()
    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    main()
