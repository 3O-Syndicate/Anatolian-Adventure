"""
ui.py

Module Description:
    Manages the User Interface (HUD) and post-processing effects.
    Displays health status, ammo count, wave info, and renders the
    atmospheric vignette (flashlight/fog) effect.
"""
import pygame
import globals as G
from settings import *

class UI:
    def __init__(self, font):
        self.current_health = 100
        self.maximum_health = 100
        self.health_bar_length = 100
        self.health_ratio = self.maximum_health / self.health_bar_length
        self.current_colour = None
        self.font = font

        # --- VIGNETTE / LIGHTING SYSTEM ---
        self.fog_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        # Darkness Opacity (RGBA)
        self.darkness_color = (10, 10, 25, 150)

        # Pre-render light texture for optimization
        self.flashlight_surf = pygame.Surface((1200, 1200), pygame.SRCALPHA)

        # 1. Outer Gradient (Soft Light)
        pygame.draw.circle(self.flashlight_surf, (0,0,0,100), (600, 600), 550)

        # 2. Inner Circle (Brightest)
        pygame.draw.circle(self.flashlight_surf, (0,0,0,100), (600, 600), 300)


    def display_coin(self):
        if getattr(G, "coin_icon", None):
            coin_image = G.coin_icon
        elif getattr(G, "coin_imgs", None):
            coin_image = pygame.transform.scale(G.coin_imgs[0], (G.coin_imgs[0].get_width()*3, G.coin_imgs[0].get_height()*3))
        else:
            coin_image = pygame.Surface((32,32)); coin_image.fill((255,223,91))
        coin_image_rect = coin_image.get_rect(center=(1162, 30))
        coin_text = self.font.render(f"x {game_stats['coins']}", True, (255, 223, 91))
        G.screen.blit(coin_text, (1200, 20))
        G.screen.blit(coin_image, coin_image_rect)

    def display_level(self):
        level_text = self.font.render("LEVEL: "+ str(G.level_num), True, WHITE)
        level_rect = level_text.get_rect(bottomright=(200, 32))
        G.screen.blit(level_text, level_rect)

    def display_vignette(self):
        """
        Renders the lighting effect using subtractive blending.
        This creates a 'flashlight' look by removing darkness around the player.
        """
        self.fog_surf.fill(self.darkness_color)
        player_screen_pos = G.player.rect.center - G.game_level.offset

        # Position light texture over player
        light_rect = self.flashlight_surf.get_rect(center=player_screen_pos)

        # Blend mode SUB removes alpha from the fog surface
        self.fog_surf.blit(self.flashlight_surf, light_rect, special_flags=pygame.BLEND_RGBA_SUB)
        G.screen.blit(self.fog_surf, (0,0))

    def update(self):
        # self.display_vignette()
        self.display_level()
        self.display_coin()


