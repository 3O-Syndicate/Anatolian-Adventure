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

    def display_health_bar(self):
        pygame.draw.rect(G.screen, BLACK, (10, 15, self.health_bar_length * 3, 20))
        if self.current_health >= 75:
            pygame.draw.rect(G.screen, GREEN, (10, 15, self.current_health * 3, 20))
            self.current_colour = GREEN
        elif self.current_health >= 25:
            pygame.draw.rect(G.screen, YELLOW, (10, 15, self.current_health * 3, 20))
            self.current_colour = YELLOW
        elif self.current_health >= 0:
            pygame.draw.rect(G.screen, RED, (10, 15, self.current_health * 3, 20))
            self.current_colour = RED
        pygame.draw.rect(G.screen, WHITE, (10, 15, self.health_bar_length * 3, 20), 4)

    def display_health_text(self):
        #health_surface = self.font.render(f"{G.player.health} / {self.maximum_health}", False, self.current_colour)
        health_dict = {100: "AA", 90: "BA", 80: "BB", 70: "CB", 60: "CC", 50: "DC", 40: "DD", 30: "DF", 20: "FF",
                       10: "FFF", 0: "DEAD"}
        health_surface = self.font.render(f"{health_dict[G.player.health]}", False, self.current_colour)
        health_rect = health_surface.get_rect(center=(410, 25))
        G.screen.blit(health_surface, health_rect)

    def display_stamina_bar(self):
        pygame.draw.rect(G.screen, BLACK, (10, 40, 200, 10))
        stamina_width = int((G.player.stamina / 200) * 200)
        pygame.draw.rect(G.screen, BLUE, (10, 40, stamina_width, 10))
        pygame.draw.rect(G.screen, WHITE, (10, 40, 200, 10), 2)

    def display_wave_text(self):
        wave_surface = self.font.render(f"Wave: {game_stats['current_wave']}", False, GREEN)
        wave_rect = wave_surface.get_rect(center=(745, 28))
        G.screen.blit(wave_surface, wave_rect)

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

    def display_countdown(self, time):
        text_1 = self.font.render(f"Enemies spawning in {int(time/1000)} seconds!", True, RED)
        G.screen.blit(text_1, (400, 100))

    def display_enemy_count(self):
        text_1 = self.font.render(f"Enemies: {game_stats['number_of_enemies'][game_stats['current_wave'] - 1] - game_stats['enemies_killed_or_removed']}", True, GREEN)
        G.screen.blit(text_1, (855, 18))

    def display_ammo(self):
        """Displays current magazine count and total reserves."""
        player = G.player
        if player.is_reloading:
            if pygame.time.get_ticks() % 500 < 250:
                reload_text = self.font.render("RELOADING...", True, RED)
                screen_pos = player.rect.center - G.game_level.offset
                rect = reload_text.get_rect(center=(screen_pos.x, screen_pos.y - 50))
                G.screen.blit(reload_text, rect)
            ammo_surf = self.font.render("-- / --", True, RED)
        else:
            color = WHITE
            if player.current_ammo <= 5: color = RED
            elif player.total_ammo <= 30: color = YELLOW
            ammo_surf = self.font.render(f"{player.current_ammo} / {player.total_ammo}", True, color)

        ammo_rect = ammo_surf.get_rect(bottomright=(WIDTH - 20, HEIGHT - 20))
        G.screen.blit(ammo_surf, ammo_rect)

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
        self.display_vignette()
        self.display_health_bar()
        self.display_health_text()
        self.display_stamina_bar()
        self.display_coin()
        self.display_wave_text()
        self.display_enemy_count()
        self.display_ammo()


