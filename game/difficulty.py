"""Difficulty presets that modify game balance.

Applied lazily: Game stores a Difficulty instance and queries it whenever it
needs a balance value (starting lives, enemy bullet speed multiplier, score
multiplier for hi-score, etc.). Keeps Enemy classes free of difficulty
plumbing — they use the multipliers via the level-loading code path."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Difficulty:
    name: str
    label: str           # shown in menu
    color: tuple
    starting_lives: int
    enemy_bullet_speed_mult: float
    enemy_hp_mult: float
    player_dmg_mult: float
    score_mult: float    # affects hi-score commit
    invincible_frames_mult: float


EASY = Difficulty(
    name="easy",
    label="EASY  (recruit)",
    color=(120, 240, 120),
    starting_lives=5,
    enemy_bullet_speed_mult=0.85,
    enemy_hp_mult=0.7,
    player_dmg_mult=1.3,
    score_mult=0.7,
    invincible_frames_mult=1.3,
)

NORMAL = Difficulty(
    name="normal",
    label="NORMAL  (soldier)",
    color=(255, 240, 120),
    starting_lives=3,
    enemy_bullet_speed_mult=1.0,
    enemy_hp_mult=1.0,
    player_dmg_mult=1.0,
    score_mult=1.0,
    invincible_frames_mult=1.0,
)

HARD = Difficulty(
    name="hard",
    label="HARD  (commando)",
    color=(255, 100, 100),
    starting_lives=2,
    enemy_bullet_speed_mult=1.25,
    enemy_hp_mult=1.3,
    player_dmg_mult=1.0,
    score_mult=1.5,
    invincible_frames_mult=0.7,
)

ALL = [EASY, NORMAL, HARD]


def by_name(name):
    for d in ALL:
        if d.name == name:
            return d
    return NORMAL


def by_index(idx):
    return ALL[idx % len(ALL)]
