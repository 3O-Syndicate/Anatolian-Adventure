"""
settings.py

Pure data + helper functions only. No image or sound loading here.
Store file paths (strings) for assets so assets.py can load them after pygame.init().

Constants: screen size, tile size, colours, and game data (monster/item metadata).
"""
import os

# game setup
WIDTH = 1280    # 1280 x 720 - full is 1600x900
HEIGHT = 720
FPS = 60
TILESIZE = 32

# colours
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

def extract_number(filename):
    """Helper to sort filenames like '0.png','1.png' numerically."""
    return int(os.path.splitext(filename)[0])

def import_folder(path):
    """
    Convenience helper: returns a list of pygame Surfaces for all images in `path`.
    NOTE: This function uses pygame.image.load and must be called only after pygame.init().
    Kept here so other modules (like assets.py) can import and use it.
    """
    import pygame  # local import to avoid requiring pygame at module import time
    surface_list = []

    for root, dirs, img_files in os.walk(path):
        sorted_file_names = sorted(img_files, key=extract_number)

        for img_name in sorted_file_names:
            full_path = os.path.join(path, img_name)
            image_surf = pygame.image.load(full_path).convert_alpha()
            surface_list.append(image_surf)

    return surface_list

# NOTE: image and sound loading removed from settings. We store paths (strings)
# so assets.py can load them after pygame.init().

monster_data = {
    "necromancer": {
        "health": 100,
        "attack_damage": 20,
        "roaming_speed": 2,
        "hunting_speed": [4, 4, 7, 7, 7],
        "image_path": "necromancer/roam/0.png",
        "image_scale": 1.5,
        "hitbox_rect": ("rect", 0, 0, 75, 100),
        "animation_speed": 0.2,
        "roam_animation_speed": 0.05,
        "death_animation_speed": 0.12,
        "notice_radius": 500
    },
    "nightborne": {
        "health": 100,
        "attack_damage": 40,
        "roaming_speed": 4,
        "hunting_speed": [4, 4, 6, 6, 6],
        "image_path": "nightborne/hunt/1.png",
        "image_scale": 1.9,
        "hitbox_rect": ("rect", 0, 0, 75, 90),
        "animation_speed": 0.1,
        "roam_animation_speed": 0.12,
        "death_animation_speed": 0.2,
        "notice_radius": 400
    },
}

game_stats = {
    "coins": 0,
    "health_potion_heal": 20,
    "score": 0,
    "current_level" : 0 
}

items = {
    "health potion": {"image_path": "items/health.png", "has_animation": False},
    "coin": {"image_path": "items/coin/0.png", "has_animation": True, "anim_folder": "items/coin"},

    "ammo": {"image_path": "items/ammo.png", "has_animation": False}
}