"""Pick the sprites we actually use out of the Kenney packs and copy them
into `assets/sprites/` with meaningful filenames.

Run once after refreshing the Kenney packs:
    python tools/build_sprite_pack.py

This keeps the shipped bundle small — we only carry the 30-or-so sprites we
actually reference, not the full 300+ file pack."""
import os
import shutil


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Raw Kenney packs live in a sibling directory (`../contra-vk-raw/`) so they
# aren't picked up by pygbag — we only ship the curated copies in
# `assets/sprites/`.
RAW = os.path.abspath(os.path.join(ROOT, "..", "contra-vk-raw"))
PLAT = os.path.join(RAW, "kenney_platformer")
SHMUP = os.path.join(RAW, "kenney_shmup")
OUT = os.path.join(ROOT, "assets", "sprites")

# Mapping: destination name → source path relative to its pack root
PLATFORMER_MAP = {
    # Characters (24×24)
    "player_idle.png":       "Tiles/Characters/tile_0000.png",
    "player_duck.png":       "Tiles/Characters/tile_0001.png",
    "soldier_idle.png":      "Tiles/Characters/tile_0011.png",
    "soldier_walk.png":      "Tiles/Characters/tile_0012.png",
    "turret.png":            "Tiles/Characters/tile_0008.png",
    "jumper_idle.png":       "Tiles/Characters/tile_0013.png",
    "jumper_jump.png":       "Tiles/Characters/tile_0014.png",
    "mortar.png":            "Tiles/Characters/tile_0015.png",
    "sniper.png":            "Tiles/Characters/tile_0017.png",
    "charger_idle.png":      "Tiles/Characters/tile_0018.png",
    "charger_angry.png":     "Tiles/Characters/tile_0019.png",
    "boss.png":              "Tiles/Characters/tile_0021.png",
    "mechboss.png":          "Tiles/Characters/tile_0022.png",
    "drone.png":             "Tiles/Characters/tile_0024.png",

    # Tiles (18×18) — names match how level.py will reference them
    "tile_grass_top.png":    "Tiles/tile_0000.png",
    "tile_grass_mid.png":    "Tiles/tile_0020.png",
    "tile_dirt.png":         "Tiles/tile_0021.png",
    "tile_brick.png":        "Tiles/tile_0040.png",
    "tile_stone.png":        "Tiles/tile_0060.png",
    "tile_stone_top.png":    "Tiles/tile_0061.png",
    "tile_metal.png":        "Tiles/tile_0103.png",
    "tile_metal_top.png":    "Tiles/tile_0083.png",
    "tile_ice.png":          "Tiles/tile_0080.png",
    "tile_ice_top.png":      "Tiles/tile_0081.png",

    # Pickups (18×18)
    "pickup_heart.png":      "Tiles/tile_0044.png",
    "pickup_key.png":        "Tiles/tile_0027.png",
    "pickup_gem.png":        "Tiles/tile_0067.png",

    # Backgrounds
    "bg_clouds.png":         "Tilemap/tilemap-backgrounds_packed.png",
}

SHMUP_MAP = {
    # Pulled top-down planes — pixel "drones" / "bombers"
    "ship_blue.png":         "Tiles/tile_0004.png",
    "ship_red.png":          "Tiles/tile_0005.png",
    "ship_green.png":        "Tiles/tile_0006.png",
    "ship_yellow.png":       "Tiles/tile_0007.png",
    "ship_big_blue.png":     "Tiles/tile_0000.png",
    "ship_big_red.png":      "Tiles/tile_0001.png",
    "ship_big_green.png":    "Tiles/tile_0002.png",
    "ship_big_yellow.png":   "Tiles/tile_0003.png",
    # Bullets / explosions / pickups (some shmup tiles are 16×16 markers)
    "shmup_bullet.png":      "Tiles/tile_0010.png",
    "shmup_bullet_alt.png":  "Tiles/tile_0011.png",
    "shmup_star.png":        "Tiles/tile_0015.png",
    "shmup_target.png":      "Tiles/tile_0013.png",
}


def main():
    os.makedirs(OUT, exist_ok=True)
    missing = []
    copied = 0
    for dest_name, src_rel in PLATFORMER_MAP.items():
        src = os.path.join(PLAT, src_rel)
        if not os.path.isfile(src):
            missing.append(src)
            continue
        shutil.copyfile(src, os.path.join(OUT, dest_name))
        copied += 1
    for dest_name, src_rel in SHMUP_MAP.items():
        src = os.path.join(SHMUP, src_rel)
        if not os.path.isfile(src):
            missing.append(src)
            continue
        shutil.copyfile(src, os.path.join(OUT, dest_name))
        copied += 1
    print(f"copied {copied} sprites into {OUT}")
    if missing:
        print("MISSING:")
        for m in missing:
            print(" ", m)
    # also copy License.txt so we credit Kenney in the shipped bundle
    for src_dir, label in [(PLAT, "kenney_platformer"), (SHMUP, "kenney_shmup")]:
        lic = os.path.join(src_dir, "License.txt")
        if os.path.isfile(lic):
            shutil.copyfile(lic, os.path.join(OUT, f"LICENSE_{label}.txt"))
    print("licenses copied")


if __name__ == "__main__":
    main()
