"""Render a single in-game frame with the new sprites and save it to PNG.
Used to eyeball the visual integration without launching pygbag."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Stub persistence so the test never writes a real save file.
import game.persistence as _persistence
_persistence.set_int = lambda key, value: None
_persistence.set_str = lambda key, value: None
_persistence.commit_hi_table = lambda table: None

import pygame
from main import Game


def fake_keys(left=False, right=False):
    class FK:
        def __init__(self):
            self.pressed = set()
        def __getitem__(self, k):
            return k in self.pressed
    fk = FK()
    if left: fk.pressed.update([pygame.K_LEFT])
    if right: fk.pressed.update([pygame.K_RIGHT])
    return fk


def main():
    pygame.init()
    pygame.display.set_mode((800, 480))
    game = Game()
    game._start_new_run()
    game.state = "play"
    # Settle player on the ground
    for _ in range(8):
        game._update_play(fake_keys())
    # advance camera a bit so we see soldier + turret
    for _ in range(80):
        game._update_play(fake_keys(right=True))
    game._draw()
    pygame.image.save(game.screen, "../contra-vk-raw/_screenshot.png")
    print("saved _screenshot.png")

    # stage 4 SKY screenshot
    game._load_stage(3)
    game.state = "play"
    for _ in range(60):
        game._update_play(fake_keys(right=True))
    game._draw()
    pygame.image.save(game.screen, "../contra-vk-raw/_screenshot_sky.png")
    print("saved _screenshot_sky.png")
    # menu screenshot
    game.state = "menu"
    game.hi_score = 12345
    game._draw()
    pygame.image.save(game.screen, "_screenshot_menu.png")
    print("saved _screenshot_menu.png")
    pygame.quit()


if __name__ == "__main__":
    main()
