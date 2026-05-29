"""Render representative frames to screenshots/ for the README / showcase.
Headless (dummy SDL), so it runs anywhere. Captures menu, jungle gameplay,
caves, and a SKY frame featuring the v0.15 Kamikaze in its lock-on telegraph."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import game.persistence as _persistence
_persistence.set_int = lambda key, value: None
_persistence.set_str = lambda key, value: None
_persistence.commit_hi_table = lambda table: None

import pygame
from main import Game
from game.entities import Kamikaze
from game.constants import SCREEN_W, GROUND_Y, PLAYER_H

OUT = os.path.join(os.path.dirname(__file__), "..", "screenshots")
os.makedirs(OUT, exist_ok=True)


class FK:
    def __init__(self, *keys):
        self.pressed = set(keys)
    def __getitem__(self, k):
        return k in self.pressed


def save(game, name):
    game._draw()
    path = os.path.join(OUT, name)
    pygame.image.save(game.screen, path)
    print("saved", os.path.relpath(path))


def main():
    pygame.init()
    pygame.display.set_mode((SCREEN_W, 480))
    game = Game()

    # --- menu ---
    game.state = "menu"
    game.hi_score = 12345
    save(game, "01_menu.png")

    # --- jungle gameplay ---
    game._start_new_run()
    game.state = "play"
    for _ in range(8):
        game._update_play(FK())
    for _ in range(70):
        game._update_play(FK(pygame.K_RIGHT, pygame.K_d))
    save(game, "02_jungle.png")

    # --- caves ---
    game._load_stage(1)
    game.state = "play"
    for _ in range(70):
        game._update_play(FK(pygame.K_RIGHT, pygame.K_d))
    save(game, "03_caves.png")

    # --- SKY + Kamikaze locked on (v0.15 showcase) ---
    game._load_stage(3)
    game.state = "play"
    game.player.x = 950
    game.player.y = GROUND_Y - PLAYER_H
    game.level.camera.x = max(0, min(game.level.width - SCREEN_W,
                                     game.player.x - SCREEN_W / 2))
    # drop a kamikaze just above/ahead, frozen in its lock-on telegraph
    k = Kamikaze(int(game.player.x + 70), 130)
    k.state = "lock"
    k.lock_timer = 12
    game.enemies.insert(0, k)
    for _ in range(2):
        game._update_play(FK(pygame.K_RIGHT, pygame.K_d, pygame.K_x))
    save(game, "04_sky_kamikaze.png")

    pygame.quit()


if __name__ == "__main__":
    main()
