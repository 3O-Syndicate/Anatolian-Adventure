"""
item.py

Module Description:
    Manages interactable items (drops) in the game world.
    Handles item spawning, floating animations, and effects applied
    to the player upon collection.
"""
import pygame
import math
import globals as G
from settings import *

class Item(pygame.sprite.Sprite):
    def __init__(self, pos, type):
        super().__init__(G.items_group, G.all_sprites_group)
        self.type = type
        self.pos = pygame.math.Vector2(pos)
        self.timer = 0
        self.start_y = pos[1]

        # --- Asset Loading ---
        item_info = items.get(type, None)

        loaded = False
        if item_info and item_info.get("image_path"):
            path = item_info["image_path"]
            try:
                self.image = pygame.image.load(path).convert_alpha()

                # Scaling adjustments for visibility
                if type == "coin":
                    self.image = pygame.transform.rotozoom(self.image, 0, 1.2)

                elif type == "health potion":
                    self.image = pygame.transform.rotozoom(self.image, 0, 3.0)

                loaded = True
            except:
                loaded = False

        # --- Fallback Visualization ---
        if not loaded:
            self.image = pygame.Surface((40, 40))
            if type == "ammo":
                self.image.fill(BLUE)
                pygame.draw.rect(self.image, WHITE, (12, 12, 16, 16))
            elif type == "health potion":
                self.image.fill(RED)
            elif type == "coin":
                self.image.fill(YELLOW)
            else:
                self.image.fill(WHITE)

        self.rect = self.image.get_rect(center=pos)
        self.start_y = self.rect.centery

    def update(self):
        # Floating Animation
        self.timer += 0.1
        offset = math.sin(self.timer) * 5
        self.rect.centery = self.start_y + offset

        # Player Interaction
        if self.rect.colliderect(G.player.base_player_rect):

            if self.type == "health potion":
                if G.player.health < 100:
                    if G.health_potion_sound: G.health_potion_sound.play()
                    G.player.increase_health(game_stats["health_potion_heal"])
                    self.kill()

            elif self.type == "coin":
                if G.coin_sound: G.coin_sound.play()
                game_stats["coins"] += 1
                game_stats["score"] += 10
                self.kill()

            elif self.type == "ammo":
                if G.coin_sound: G.coin_sound.play()
                G.player.total_ammo += 30
                self.kill()