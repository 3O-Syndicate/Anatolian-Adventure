"""Display the platformer HUD (health, ammo, score, level, coins, beads) and floating text."""
import pygame
import globals as G
from settings import *


class FloatingText(pygame.sprite.Sprite):
    """Short-lived floating text for pickups, scores, and notifications."""

    def __init__(self, text, pos, color=(255, 255, 255), font=None, duration=45):
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
        self.timer = duration  # game ticks; longer for texts worth reading

    def update(self):
        self.timer -= 1
        self.y -= 0.8
        self.rect.centery = int(self.y)
        if self.timer < 15:
            alpha = max(0, int(255 * (self.timer / 15)))
            self.image.set_alpha(alpha)
        if self.timer <= 0:
            self.kill()


def spawn_floating_text(text, pos, color=(255, 255, 255), duration=45):
    return FloatingText(text, pos, color, duration=duration)


G.create_floating_text = spawn_floating_text


def level_name(level):
    return "Eğitim" if level == 0 else f"Bölüm {level}"  # level 0 is the tutorial


# Turkish texts use sentence case: the pixel font draws Ç Ğ İ Ö Ş Ü as small letters,
# so all-caps words such as BÖLÜM would look broken.
class UI:
    def __init__(self, font):
        self.current_health = 100
        self.maximum_health = 100
        self.font = font
        self.small_font = pygame.font.Font("font/PublicPixel.ttf", 10)
        self.mid_font = pygame.font.Font("font/PublicPixel.ttf", 14)
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
        hp_label = self.small_font.render(f"Can {int(self.current_health)}/{self.maximum_health}", True, WHITE)
        G.screen.blit(hp_label, (bar_x + bar_width + 10, bar_y + 2))

    def display_ammo(self):
        if G.player is None or not G.player.has_gun:
            return
        ammo_y = 48
        if G.player.is_reloading:
            # Pulsing reload text
            ticks = pygame.time.get_ticks()
            color = (255, 220, 50) if (ticks // 250) % 2 == 0 else (200, 160, 20)
            text = self.small_font.render("Dolduruluyor...", True, color)
        else:
            color = WHITE if G.player.current_ammo > 5 else (231, 76, 60)
            text = self.small_font.render(f"Mermi {G.player.current_ammo} / {G.player.total_ammo}", True, color)
        G.screen.blit(text, (24, ammo_y))

    def display_items(self):
        """Nazar beads and acid next to the ammo line, only while the player has some."""
        if G.player is None:
            return
        x = 24
        beads = G.player.armor
        icon = G.nazar_imgs[1] if G.nazar_imgs and len(G.nazar_imgs) > 1 else None
        if beads > 0 and icon is not None:
            icon = pygame.transform.scale_by(icon, 2)
            for i in range(min(beads, 5)):
                G.screen.blit(icon, (x, 60))
                x += icon.get_width() + 4
            if beads > 5:
                label = self.small_font.render(f"x{beads}", True, (200, 225, 255))
                G.screen.blit(label, (x, 66))
                x += label.get_width()
            x += 14
            beads = 0
        for count, text, color in ((beads, "Nazar x{}", (200, 225, 255)),
                                   (G.player.acid, "Asit x{} [Q]", (150, 255, 90))):
            if count > 0:
                label = text.format(count)
                G.screen.blit(self.small_font.render(label, True, (20, 24, 32)), (x + 1, 67))
                surface = self.small_font.render(label, True, color)
                G.screen.blit(surface, (x, 66))
                x += surface.get_width() + 18

    def display_score(self):
        score_text = self.font.render(f"Skor {game_stats['score']}", True, WHITE)
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

    def display_beads(self):
        """Tesbih beads under the coins; the count turns green once the elder has enough."""
        beads = game_stats.get("beads", 0)
        icon = getattr(G, "bead_icon", None)
        if icon is not None:
            G.screen.blit(icon, icon.get_rect(center=(WIDTH - 110, 64)))
        color = (140, 255, 140) if beads >= BEADS_NEEDED else (255, 223, 91)
        label = self.mid_font.render(f"{beads}/{BEADS_NEEDED}", True, color)
        G.screen.blit(label, label.get_rect(midleft=(WIDTH - 90, 64)))

    def display_level(self):
        level_text = self.font.render(level_name(game_stats["current_level"]), True, WHITE)
        level_rect = level_text.get_rect(topright=(WIDTH - 160, 18))
        G.screen.blit(level_text, level_rect)

    def display_timer(self):
        """Seconds left; in the last ten each second pops in red and the screen edges pulse."""
        left = G.game_level.time_left_ms
        seconds = (left + 999) // 1000
        if not 0 < seconds <= 10:
            timer = self.mid_font.render(f"Süre {seconds}", True, WHITE)
            G.screen.blit(timer, timer.get_rect(topright=(WIDTH - 160, 52)))
            return
        beat = (left % 1000) / 1000  # 1 just after a second starts, 0 at its end
        colour = (255, 70, 60) if beat > 0.5 else (255, 190, 180)
        timer = self.mid_font.render(f"Süre {seconds}", True, colour)
        pop = 1 + 0.45 * beat ** 3
        timer = pygame.transform.scale_by(timer, pop)
        G.screen.blit(timer, timer.get_rect(midright=(WIDTH - 160, 52 + self.mid_font.get_height() // 2)))
        if getattr(self, "vignette", None) is None:
            self.vignette = self.make_vignette()
        self.vignette.set_alpha(int(40 + 110 * beat ** 2))
        G.screen.blit(self.vignette, (0, 0))

    @staticmethod
    def make_vignette():
        """Red glow along the screen edges, strongest at the border."""
        surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        depth = 48
        for i in range(depth):
            alpha = int(150 * (1 - i / depth) ** 2)
            pygame.draw.rect(surface, (220, 30, 30, alpha), (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 1)
        return surface

    def update(self):
        self.display_health()
        self.display_ammo()
        self.display_items()
        self.display_score()
        self.display_level()
        self.display_timer()
        self.display_coin()
        self.display_beads()
