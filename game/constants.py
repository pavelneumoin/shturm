SCREEN_W = 800
SCREEN_H = 480
FPS = 60

PLAYER_W = 24
PLAYER_H = 36
PLAYER_DUCK_VISUAL_H = 22
PLAYER_SPEED = 4
JUMP_VELOCITY = -13
GRAVITY = 0.55
MAX_FALL = 14
INVINCIBLE_FRAMES = 90
SHOOT_COOLDOWN = 8

BULLET_SPEED = 9
BULLET_W = 8
BULLET_H = 4

SOLDIER_HP = 1
SOLDIER_SPEED = 2
SOLDIER_SHOOT_COOLDOWN = 110
TURRET_HP = 3
TURRET_SHOOT_COOLDOWN = 70
BOSS_HP = 30

LEVEL_W = 4000
GROUND_Y = 380

SKY_TOP = (40, 60, 120)
SKY_BOT = (90, 130, 180)
GROUND = (60, 40, 20)
GROUND_TOP = (90, 60, 30)
MOUNTAIN_FAR = (50, 70, 100)
MOUNTAIN_NEAR = (40, 50, 70)

PLAYER_COLOR = (60, 220, 80)
PLAYER_HELMET = (30, 100, 40)
PLAYER_GUN = (240, 240, 240)

BULLET_COLOR = (255, 240, 100)
ENEMY_BULLET_COLOR = (255, 80, 80)

SOLDIER_COLOR = (200, 60, 60)
SOLDIER_DARK = (120, 30, 30)
TURRET_COLOR = (140, 140, 160)
TURRET_DARK = (60, 60, 80)
BOSS_COLOR = (200, 50, 200)

PICKUP_COLOR = (100, 220, 255)
HUD_TEXT = (255, 255, 255)
DARK = (20, 20, 30)

WEAPON_NORMAL = "N"
WEAPON_SPREAD = "S"
WEAPON_MACHINE = "M"
WEAPON_LASER = "L"

PICKUP_LIFE = "1UP"
PICKUP_GEM = "GEM"
GEM_SCORE = 500
DRONE_HP = 1
DRONE_SHOOT_COOLDOWN = 80

SHOOT_COOLDOWN_MACHINE = 4
SHOOT_COOLDOWN_LASER = 12

JUMPER_HP = 1
JUMPER_SPEED = 1.6
JUMPER_JUMP_INTERVAL = 75
JUMPER_JUMP_VY = -10.0

MORTAR_HP = 2
MORTAR_SHOOT_COOLDOWN = 130
MORTAR_SHELL_GRAVITY = 0.22

SNIPER_HP = 2
SNIPER_AIM_FRAMES = 60      # how long the laser sight is shown before firing
SNIPER_COOLDOWN = 180

CHARGER_HP = 2
CHARGER_VISION = 280
CHARGER_SPEED = 3.6

BOMBER_HP = 2
BOMBER_SHOOT_COOLDOWN = 110
GRENADE_FUSE = 50
GRENADE_GRAVITY = 0.28

LASER_BULLET_SPEED = 12
LASER_COLOR = (255, 110, 180)
LASER_TRAIL = (255, 60, 130)

STAGE_INTRO_FRAMES = 120
STAGE_CLEAR_FRAMES = 150

CHECKPOINT_COLOR = (255, 240, 120)
CHECKPOINT_ACTIVE = (120, 240, 120)

SHIELD_TROOPER_HP = 2

BURROWER_HP = 2
BURROWER_SPEED = 1.8          # underground tracking speed
BURROWER_UNDER_FRAMES = 95    # time spent submerged (invulnerable)
BURROWER_UP_FRAMES = 80       # time spent surfaced (vulnerable, shoots)

# --- Destructibles (v0.12) ---
CRATE_HP = 1                  # wooden supply crate — one shot, guaranteed loot
BARREL_HP = 1                 # explosive barrel — one shot to detonate
BARREL_EXPLOSION_RADIUS = 96  # AoE radius that damages enemies (chain reaction)
BARREL_EXPLOSION_DAMAGE = 3   # damage dealt to every enemy caught in the blast

# --- Player dash / dodge-roll (v0.14) ---
DASH_SPEED = 10.0   # horizontal burst speed during a dash (vs PLAYER_SPEED=4)
DASH_DURATION = 11  # frames the dash lasts — also the i-frame (invulnerability) window
DASH_COOLDOWN = 40  # frames before the player can dash again

# --- Kamikaze flyer (v0.15) ---
KAMIKAZE_HP = 1               # fragile — shoot it down before it reaches you
KAMIKAZE_TRIGGER = 240        # horizontal range at which it locks on and commits to a dive
KAMIKAZE_LOCK_FRAMES = 28     # telegraph time before the dive (dodge / shoot window)
KAMIKAZE_DIVE_SPEED = 7.5     # dive velocity once committed
KAMIKAZE_HOVER_SPEED = 1.1    # slow drift toward the player while hovering
KAMIKAZE_EXPLOSION_RADIUS = 66  # AoE that damages the player on detonation
