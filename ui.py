"""Display the platformer level and coin HUD."""
import pygame
import globals as G
from settings import *

class UI:
    def __init__(self, font):
        self.current_health = 100
        self.maximum_health = 100
        self.font = font

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
        level_text = self.font.render("LEVEL: "+ str(game_stats["current_level"] + 1), True, WHITE)
        level_rect = level_text.get_rect(bottomright=(200, 32))
        G.screen.blit(level_text, level_rect)

    def update(self):
        self.display_level()
        self.display_coin()
