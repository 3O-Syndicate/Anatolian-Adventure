"""
globals.py

Runtime shared objects (sprite groups, runtime instances and references to loaded assets).

assets.load_assets() assigns Surfaces/Sounds into these names so other modules can read them.
"""
import pygame

# Sprite groups used across modules (instantiate early so modules can add to them)
all_sprites_group = pygame.sprite.Group()
obstacles_group = pygame.sprite.Group()
bullet_group = pygame.sprite.Group()
enemy_group = pygame.sprite.Group()
items_group = pygame.sprite.Group()

# Runtime references (will be assigned by main.py)
player = None        # instance of Player
ui = None            # instance of UI
game_level = None    # instance of GameLevel
cage = None          # instance of Cage

# Loaded assets that assets.py will set
coin_imgs = None
coin_icon = None
bullet_img = None

# Player image
player_image = None

# Hero animations: anim.json data and {animation name: [frame Surfaces]}
hero_meta = None
hero_anims = None
muzzle_flash_imgs = None

# Enemy artwork: {"walker/walk": (frames facing right, frames facing left), ...}
enemy_frames = None

# Sounds (assets.py will set these)
coin_sound = None
health_potion_sound = None
hurt_sound = None
death_sound = None
gun_shot_sound = None
cage_break_sound = None
sound_volume = 0.5

# Screen reference (set in main)
screen = None
