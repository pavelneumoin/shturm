"""Static level data — themes and 3 stages.
Level renderer/Camera live in level.py and consume LevelDef."""
from dataclasses import dataclass, field


@dataclass
class Theme:
    sky_top: tuple = (40, 60, 120)
    sky_bot: tuple = (90, 130, 180)
    ground: tuple = (60, 40, 20)
    ground_top: tuple = (90, 60, 30)
    mountain_far: tuple = (50, 70, 100)
    mountain_near: tuple = (40, 50, 70)
    has_ceiling: bool = False
    ceiling_color: tuple = (40, 25, 25)
    ceiling_top: tuple = (70, 50, 45)
    fog: bool = False
    has_stars: bool = False
    # Ambient particle style: "leaves" (jungle), "fireflies" (caves),
    # "sparks" (base) or None.
    ambient: str = None
    # Tile sprite filenames (in assets/sprites/). When set, level.draw will
    # tile them instead of drawing flat coloured rectangles.
    tile_top: str = "tile_grass_top.png"
    tile_mid: str = "tile_dirt.png"
    # Foreground weather overlay (v0.13): "rain" (+lightning) / "drip" /
    # "alarm" (red pulse) / "clouds" / None. Purely cosmetic.
    weather: str = None


@dataclass
class LevelDef:
    stage: int
    name: str
    theme: Theme
    width: int
    floor_strips: list = field(default_factory=list)        # list of (x0, x1) ground strips
    floats: list = field(default_factory=list)              # list of (x, y, w) static floating platforms
    movables: list = field(default_factory=list)            # list of dicts {x,y,w,h, axis, range, speed}
    ceiling_strips: list = field(default_factory=list)      # for caves: top strips
    enemy_spawns: list = field(default_factory=list)        # list of (kind, x, y) tuples
    pickup_spawns: list = field(default_factory=list)       # list of (x, y, kind)
    checkpoints: list = field(default_factory=list)         # list of (x, y) flag positions
    boss_spawn: tuple = None                                # (x, y, kind)


THEME_JUNGLE = Theme(
    sky_top=(40, 60, 120),
    sky_bot=(90, 130, 180),
    ground=(60, 40, 20),
    ground_top=(90, 60, 30),
    mountain_far=(50, 70, 100),
    mountain_near=(40, 50, 70),
    ambient="leaves",
    weather="rain",
    tile_top="tile_grass_top.png",
    tile_mid="tile_dirt.png",
)

THEME_CAVES = Theme(
    sky_top=(15, 8, 25),
    sky_bot=(35, 18, 45),
    ground=(55, 35, 35),
    ground_top=(95, 65, 50),
    mountain_far=(30, 18, 30),
    mountain_near=(50, 28, 38),
    has_ceiling=True,
    ceiling_color=(48, 28, 28),
    ceiling_top=(85, 55, 45),
    fog=True,
    ambient="fireflies",
    weather="drip",
    tile_top="tile_stone_top.png",
    tile_mid="tile_stone.png",
)

THEME_BASE = Theme(
    sky_top=(20, 22, 35),
    sky_bot=(50, 55, 80),
    ground=(60, 60, 75),
    ground_top=(110, 110, 130),
    mountain_far=(40, 40, 55),
    mountain_near=(60, 60, 80),
    ambient="sparks",
    weather="alarm",
    tile_top="tile_metal_top.png",
    tile_mid="tile_metal.png",
)

THEME_SKY = Theme(
    sky_top=(45, 30, 80),     # twilight purple at top
    sky_bot=(220, 110, 90),   # warm sunset at horizon
    ground=(70, 60, 110),     # cloud-platform body
    ground_top=(180, 150, 220),  # bright cloud top
    mountain_far=(80, 60, 130),
    mountain_near=(120, 80, 160),
    has_stars=True,
    ambient="leaves",   # repurposed as feather-drift; tint via palette later
    weather="clouds",
    tile_top="tile_ice_top.png",
    tile_mid="tile_ice.png",
)


# ============= STAGE 1: JUNGLE =============
STAGE_1 = LevelDef(
    stage=1,
    name="STAGE 1: JUNGLE",
    theme=THEME_JUNGLE,
    width=4000,
    floor_strips=[(0, 720), (840, 1500), (1620, 2360),
                  (2480, 3300), (3380, 4000)],
    floats=[
        (300, 300, 120), (480, 220, 110), (640, 290, 90),
        (920, 260, 100), (1100, 200, 110), (1280, 280, 100),
        (1700, 290, 100), (1880, 220, 110), (2060, 300, 90),
        (2240, 250, 100), (2580, 270, 110), (2780, 200, 100),
        (2980, 280, 110), (3180, 220, 90),
    ],
    enemy_spawns=[
        ("soldier", 380, 348), ("soldier", 600, 348),
        ("soldier", 540, 188),
        ("turret", 920, 352),
        ("jumper", 1050, 358),
        ("soldier", 1100, 348), ("soldier", 1200, 168),
        ("turret", 1400, 352),
        ("soldier", 1700, 348), ("soldier", 1900, 348),
        ("jumper", 2000, 358),
        ("soldier", 2100, 348),
        ("turret", 2280, 352),
        ("soldier", 2600, 348),
        ("mortar", 2750, 356),
        ("turret", 2820, 352),
        ("soldier", 3000, 348),
        ("jumper", 3100, 358),
        ("soldier", 3200, 348),
        # destructibles (v0.12): crates spill guaranteed loot, barrels chain-blast
        ("crate", 660, 352),
        ("barrel", 1150, 348),
        ("crate", 1950, 352),
        ("barrel", 2700, 348),
        ("crate", 3150, 352),
    ],
    pickup_spawns=[
        (1320, 330, "S"),
        (2620, 330, "M"),
    ],
    checkpoints=[(1500, 320), (2700, 320)],
    boss_spawn=(3700, 260, "boss"),
)


# ============= STAGE 2: CAVES =============
STAGE_2 = LevelDef(
    stage=2,
    name="STAGE 2: CAVES",
    theme=THEME_CAVES,
    width=4500,
    floor_strips=[(0, 600), (720, 1300), (1420, 2200),
                  (2320, 3000), (3120, 3800), (3900, 4500)],
    floats=[
        (200, 280, 90),
        (380, 220, 90),
        (560, 300, 80),
        (760, 260, 100),
        (920, 200, 110),
        (1100, 290, 90),
        (1500, 270, 110),
        (1700, 200, 100),
        (1880, 280, 90),
        (2400, 260, 110),
        (2580, 200, 90),
        (2750, 290, 100),
        (3200, 250, 100),
        (3380, 200, 90),
        (3550, 290, 100),
        (3950, 230, 110),
        (4150, 280, 100),
    ],
    movables=[
        {"x": 1300, "y_min": 200, "y_max": 360, "w": 80, "h": 14,
         "axis": "y", "speed": 1.2, "phase": 0},
        {"x": 2050, "y_min": 180, "y_max": 360, "w": 80, "h": 14,
         "axis": "y", "speed": 1.4, "phase": 0.5},
        {"x": 3700, "y_min": 200, "y_max": 360, "w": 80, "h": 14,
         "axis": "y", "speed": 1.3, "phase": 0.25},
    ],
    ceiling_strips=[
        (0, 4500),  # full ceiling at top
    ],
    enemy_spawns=[
        ("soldier", 350, 348),
        ("drone", 500, 200),
        ("turret", 760, 232),
        ("drone", 900, 150),
        ("jumper", 1100, 358),
        ("soldier", 1180, 348),
        ("drone", 1450, 180),
        ("soldier", 1600, 348),
        ("mortar", 1750, 356),
        ("soldier", 1900, 348),
        ("turret", 2050, 352),
        ("drone", 2200, 150),
        ("jumper", 2350, 358),
        ("soldier", 2400, 232),
        ("turret", 2700, 352),
        ("drone", 2900, 180),
        ("jumper", 3200, 358),
        ("soldier", 3300, 348), ("soldier", 3500, 348),
        ("drone", 3700, 150),
        ("mortar", 3800, 356),
        ("turret", 3950, 202),
        ("drone", 4100, 180),
        ("burrower", 1300, 356),
        ("burrower", 3050, 356),
        # destructibles (v0.12)
        ("crate", 450, 352),
        ("barrel", 1150, 348),
        ("crate", 1650, 352),
        ("barrel", 2600, 348),
        ("crate", 3350, 352),
    ],
    pickup_spawns=[
        (820, 330, "1UP"),
        (1900, 330, "S"),
        (2900, 330, "L"),
        (3700, 330, "1UP"),
    ],
    checkpoints=[(1300, 320), (2300, 320), (3100, 320)],
    boss_spawn=(4250, 260, "boss"),
)


# ============= STAGE 3: BASE =============
STAGE_3 = LevelDef(
    stage=3,
    name="STAGE 3: BASE",
    theme=THEME_BASE,
    width=4400,
    floor_strips=[(0, 500), (620, 1100), (1220, 1700),
                  (1820, 2400), (2520, 3000), (3120, 3800), (3900, 4400)],
    floats=[
        (200, 280, 80),
        (700, 270, 90),
        (900, 200, 100),
        (1300, 280, 90),
        (1500, 200, 100),
        (1900, 290, 90),
        (2100, 220, 100),
        (2300, 280, 90),
        (2700, 250, 100),
        (3300, 280, 100),
        (3500, 200, 100),
        (4000, 250, 110),
    ],
    movables=[
        {"x": 540, "y_min": 200, "y_max": 360, "w": 70, "h": 14,
         "axis": "y", "speed": 1.5, "phase": 0},
        {"x": 1140, "y_min": 180, "y_max": 360, "w": 70, "h": 14,
         "axis": "y", "speed": 1.6, "phase": 0.5},
        {"x": 1750, "y_min": 200, "y_max": 360, "w": 70, "h": 14,
         "axis": "y", "speed": 1.7, "phase": 0.25},
        {"x": 2440, "y_min": 200, "y_max": 360, "w": 70, "h": 14,
         "axis": "y", "speed": 1.4, "phase": 0.75},
        {"x": 3040, "y_min": 180, "y_max": 360, "w": 70, "h": 14,
         "axis": "y", "speed": 1.5, "phase": 0.4},
        {"x": 3830, "y_min": 200, "y_max": 360, "w": 70, "h": 14,
         "axis": "y", "speed": 1.6, "phase": 0.6},
    ],
    enemy_spawns=[
        ("soldier", 280, 348),
        ("turret", 720, 352),
        ("drone", 850, 150),
        ("mortar", 1000, 356),
        ("soldier", 1300, 348),
        ("drone", 1500, 180),
        ("turret", 1600, 352),
        ("jumper", 1850, 358),
        ("soldier", 1900, 348),
        ("soldier", 2200, 348),
        ("drone", 2300, 150),
        ("turret", 2350, 352),
        ("mortar", 2600, 356),
        ("drone", 2700, 180),
        ("soldier", 2800, 348),
        ("jumper", 2900, 358),
        ("kamikaze", 2950, 130),   # introduces the dive-bomber before the SKY stage
        ("shield", 3050, 348),
        ("drone", 3000, 150),
        ("turret", 3150, 352),
        ("soldier", 3300, 348),
        ("jumper", 3400, 358),
        ("shield", 3450, 348),
        ("drone", 3500, 180),
        ("kamikaze", 3520, 125),
        ("mortar", 3550, 356),
        ("sniper", 3600, 352),
        ("turret", 3700, 352),
        ("charger", 3800, 358),
        ("soldier", 3900, 348),
        ("drone", 4050, 150),
        ("burrower", 1450, 356),
        ("burrower", 2750, 356),
        ("burrower", 3650, 356),
        # destructibles (v0.12): barrel at 3680 sits in the dense final cluster
        ("crate", 350, 352),
        ("barrel", 950, 348),
        ("crate", 1400, 352),
        ("barrel", 2850, 348),
        ("crate", 3300, 352),
        ("barrel", 3680, 348),
    ],
    pickup_spawns=[
        (450, 330, "M"),
        (1500, 330, "1UP"),
        (2300, 330, "L"),
        (3500, 330, "M"),
        (4000, 330, "1UP"),
    ],
    checkpoints=[(1200, 320), (2500, 320), (3700, 320)],
    boss_spawn=(4150, 240, "mech"),
)


# ============= STAGE 4: SKY =============
STAGE_4 = LevelDef(
    stage=4,
    name="STAGE 4: SKY",
    theme=THEME_SKY,
    width=4600,
    # cloud-platforms hovering with gaps — fewer wide floors, more floats
    floor_strips=[(0, 400), (520, 900), (1040, 1500), (1640, 2100),
                  (2240, 2700), (2840, 3300), (3440, 3900), (4040, 4600)],
    floats=[
        (450, 270, 90),
        (700, 220, 100),
        (950, 280, 90),
        (1180, 230, 100),
        (1400, 200, 90),
        (1700, 260, 100),
        (1950, 220, 90),
        (2200, 290, 100),
        (2450, 240, 90),
        (2700, 200, 100),
        (2950, 270, 90),
        (3180, 220, 100),
        (3450, 240, 90),
        (3700, 200, 100),
        (3950, 270, 100),
        (4250, 230, 110),
    ],
    movables=[
        {"x": 400, "y_min": 200, "y_max": 360, "w": 80, "h": 14,
         "axis": "y", "speed": 1.4, "phase": 0.0},
        {"x": 1500, "y_min": 200, "y_max": 360, "w": 80, "h": 14,
         "axis": "y", "speed": 1.5, "phase": 0.3},
        {"x": 2750, "y_min": 200, "y_max": 360, "w": 80, "h": 14,
         "axis": "y", "speed": 1.6, "phase": 0.6},
        {"x": 3900, "y_min": 180, "y_max": 360, "w": 80, "h": 14,
         "axis": "y", "speed": 1.5, "phase": 0.9},
    ],
    enemy_spawns=[
        ("soldier", 260, 348),
        ("sniper", 600, 352),      # introduces sniper
        ("drone", 800, 150),
        ("kamikaze", 1000, 120),   # SKY = aerial-threat showcase for the dive-bomber
        ("charger", 1100, 358),
        ("bomber", 1400, 130),
        ("turret", 1700, 352),
        ("shield", 1600, 348),
        ("kamikaze", 1800, 110),
        ("jumper", 1900, 358),
        ("sniper", 2000, 352),
        ("drone", 2300, 150),
        ("charger", 2500, 358),
        ("kamikaze", 2650, 130),
        ("bomber", 2800, 130),
        ("mortar", 3000, 356),
        ("shield", 3200, 348),
        ("soldier", 3300, 348),
        ("kamikaze", 3500, 115),
        ("sniper", 3600, 352),
        ("drone", 3700, 180),
        ("charger", 3900, 358),
        ("bomber", 4150, 130),
        ("kamikaze", 4250, 120),
        ("turret", 4350, 352),
        # destructibles (v0.12)
        ("crate", 300, 352),
        ("barrel", 1150, 348),
        ("crate", 1750, 352),
        ("barrel", 2550, 348),
        ("crate", 3200, 352),
    ],
    pickup_spawns=[
        (500, 330, "S"),
        (1500, 330, "L"),
        (2700, 330, "M"),
        (3500, 330, "L"),
        (4200, 330, "1UP"),
    ],
    checkpoints=[(1200, 320), (2400, 320), (3500, 320)],
    boss_spawn=(4400, 240, "mech"),  # reuse final mech boss design here too
)


ALL_LEVELS = [STAGE_1, STAGE_2, STAGE_3, STAGE_4]
