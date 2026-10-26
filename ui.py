"""Display the platformer HUD (health, ammo, score, level, coins) and floating text."""
import pygame
import globals as G
from settings import *


class FloatingText(pygame.sprite.Sprite):
    """Short-lived floating text for pickups, scores, and notifications."""

    def __init__(self, text, pos, color=(255, 255, 255), font=None):
        super().__init__(G.all_sprites_group)
        if font is None:
            font = getattr(G, "small_font", None)
            if font is None:
                font = pygame.font.Font("font/PublicPixel.ttf", 9)
        text_surf = font.render(str(text), True, color)
        shadow_surf = font.render(str(text), True, (20, 20, 20))
        w, h = text_surf.get_width() + 4, text_surf.get_height() + 4
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.blit(shadow_surf, (2, 2))
        surf.blit(text_surf, (1, 1))

        self.image = surf
        self.rect = self.image.get_rect(center=pos)
        self.y = float(self.rect.centery)
        self.timer = 45

    def update(self):
        self.timer -= 1
        self.y -= 0.8
        self.rect.centery = int(self.y)
        if self.timer < 15:
            alpha = max(0, int(255 * (self.timer / 15)))
            self.image.set_alpha(alpha)
        if self.timer <= 0:
            self.kill()


def spawn_floating_text(text, pos, color=(255, 255, 255)):
    return FloatingText(text, pos, color)


G.create_floating_text = spawn_floating_text


class UI:
    def __init__(self, font):
        self.current_health = 100
        self.maximum_health = 100
        self.font = font
        self.small_font = pygame.font.Font("font/PublicPixel.ttf", 10)
        G.small_font = self.small_font

    def display_health(self):
        # Health bar box
        bar_x, bar_y = 24, 20
        bar_width, bar_height = 160, 16
        pct = max(0.0, min(1.0, self.current_health / self.maximum_health))

        # Background frame
        pygame.draw.rect(G.screen, (20, 24, 32), (bar_x - 3, bar_y - 3, bar_width + 6, bar_height + 6), border_radius=4)
        pygame.draw.rect(G.screen, (50, 20, 20), (bar_x, bar_y, bar_width, bar_height), border_radius=2)

        # Bar fill color transitions based on health
        if pct > 0.5:
            fill_color = (46, 204, 113)  # Green
        elif pct > 0.25:
            fill_color = (241, 196, 15)  # Yellow
        else:
            fill_color = (231, 76, 60)   # Red

        if pct > 0:
            fill_w = max(2, int(bar_width * pct))
            pygame.draw.rect(G.screen, fill_color, (bar_x, bar_y, fill_w, bar_height), border_radius=2)

        # HP Text label
        hp_label = self.small_font.render(f"HP {int(self.current_health)}/{self.maximum_health}", True, WHITE)
        G.screen.blit(hp_label, (bar_x + bar_width + 10, bar_y + 2))

    def display_ammo(self):
        if G.player is None:
            return
        ammo_y = 48
        if G.player.is_reloading:
            # Pulsing reload text
            ticks = pygame.time.get_ticks()
            color = (255, 220, 50) if (ticks // 250) % 2 == 0 else (200, 160, 20)
            text = self.small_font.render("RELOADING...", True, color)
        else:
            color = WHITE if G.player.current_ammo > 5 else (231, 76, 60)
            text = self.small_font.render(f"AMMO {G.player.current_ammo} / {G.player.total_ammo}", True, color)
        G.screen.blit(text, (24, ammo_y))

    def display_score(self):
        score_text = self.font.render(f"SCORE {game_stats['score']}", True, WHITE)
        score_rect = score_text.get_rect(center=(WIDTH // 2, 28))
        G.screen.blit(score_text, score_rect)

    def display_coin(self):
        if getattr(G, "coin_icon", None):
            coin_image = G.coin_icon
        elif getattr(G, "coin_imgs", None) and len(G.coin_imgs) > 0:
            coin_image = pygame.transform.scale(G.coin_imgs[0], (G.coin_imgs[0].get_width() * 2, G.coin_imgs[0].get_height() * 2))
        else:
            coin_image = pygame.Surface((24, 24))
            coin_image.fill((255, 223, 91))
        coin_image_rect = coin_image.get_rect(center=(WIDTH - 110, 28))
        coin_text = self.font.render(f"x {game_stats['coins']}", True, (255, 223, 91))
        G.screen.blit(coin_image, coin_image_rect)
        G.screen.blit(coin_text, (WIDTH - 90, 18))

    def display_level(self):
        level_text = self.font.render(f"LEVEL {game_stats['current_level'] + 1}", True, WHITE)
        level_rect = level_text.get_rect(topright=(WIDTH - 160, 18))
        G.screen.blit(level_text, level_rect)

    def update(self):
        self.display_health()
        self.display_ammo()
        self.display_score()
        self.display_level()
        self.display_coin()
