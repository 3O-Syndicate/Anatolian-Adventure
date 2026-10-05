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

# Loaded assets that assets.py will set
sectboundary_img = None
plain_bg = None
coin_imgs = None
coin_icon = None
bullet_img = None

# Player image
player_image = None

# Sounds (assets.py will set these)
coin_sound = None
health_potion_sound = None
hurt_sound = None
death_sound = None
gun_shot_sound = None
necromancer_death_sound = None
nightborne_death_sound = None
sound_volume = 0.5

# Screen reference (set in main)
screen = None

def hitbox_collide(sprite1, sprite2):
    """
    Helper used for groupcollide: returns True when enemy hitbox collides with the bullet rect.
    """
    return sprite1.base_zombie_rect.colliderect(sprite2.rect)