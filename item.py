"""
item.py

Module Description:
    Manages interactable items (drops) in the game world.
    Handles item spawning, animated coin rotation, floating animations,
    and effects applied to the player upon collection.
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
        self.anim_timer = 0.0
        self.frames = []
        self.start_y = pos[1]

        # --- Asset Loading ---
        item_info = items.get(type, None)
        loaded = False

        if type == "coin" and getattr(G, "coin_imgs", None) and len(G.coin_imgs) > 0:
            self.frames = [pygame.transform.rotozoom(img, 0, 1.2) for img in G.coin_imgs]
            self.image = self.frames[0]
            loaded = True
        elif item_info and item_info.get("image_path"):
            path = item_info["image_path"]
            try:
                self.image = pygame.image.load(path).convert_alpha()
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
        # Coin frame rotation animation
        if self.type == "coin" and self.frames:
            self.anim_timer += 0.25
            idx = int(self.anim_timer) % len(self.frames)
            current_center = self.rect.center
            self.image = self.frames[idx]
            self.rect = self.image.get_rect(center=current_center)

        # Floating Animation
        self.timer += 0.1
        offset = math.sin(self.timer) * 5
        self.rect.centery = int(self.start_y + offset)

        # Player Interaction
        if G.player and self.rect.colliderect(G.player.base_player_rect):
            if self.type == "health potion":
                if G.player.health < 100:
                    if G.health_potion_sound: G.health_potion_sound.play()
                    heal_amt = game_stats.get("health_potion_heal", 20)
                    G.player.increase_health(heal_amt)
                    if getattr(G, "create_floating_text", None):
                        G.create_floating_text(f"+{heal_amt} HP", self.rect.center, (100, 255, 100))
                    self.kill()

            elif self.type == "coin":
                if G.coin_sound: G.coin_sound.play()
                game_stats["coins"] += 1
                game_stats["score"] += 10
                if getattr(G, "create_floating_text", None):
                    G.create_floating_text("+10", self.rect.center, (255, 223, 91))
                self.kill()

            elif self.type == "ammo":
                if G.coin_sound: G.coin_sound.play()
                G.player.total_ammo += 30
                if getattr(G, "create_floating_text", None):
                    G.create_floating_text("+30 AMMO", self.rect.center, (100, 200, 255))
                self.kill()
