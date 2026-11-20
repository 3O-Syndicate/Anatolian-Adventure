"""Shop artwork, doorway interaction, purchases and the modal shop GUI.

Maps opt in with a decor item {"id": "shop", "x": ..., "y": ...}.
The anchor tile is the doorway (bottom centre); the building is 3x3 tiles.
Prices and starter upgrades are defined in OFFERS below.
"""
import math
from pathlib import Path

import pygame

from settings import TILESIZE, game_stats

SHOP_IMAGE = Path(__file__).with_name("decor") / "shop.png"
NAZAR_IMAGE = Path(__file__).with_name("effects") / "nazar" / "0.png"
SIGN_AREA = pygame.Rect(9, 43, 78, 9)     # the ERDAL BAKKAL board in shop.png
SIGN_INK = (168, 28, 36)                  # its letter colour (art/props/props_sprite.py)
NAZAR_PIVOT = (56, 63)                    # on the door frame, right of the glass
SHOP_SIZE = (3 * TILESIZE, 3 * TILESIZE)
OFFERS = (
    ("heal", "İlk yardım", "40 can yeniler", 5),
    ("ammo", "Mermi paketi", "+30 yedek mermi", 3),
    ("speed", "Koşu botu", "Koşu hızını %20 artırır", 10),
    ("jump", "Zıplama botu", "Zıplama gücünü %10 artırır", 10),
)
BG = (27, 30, 43)
CARD = (44, 49, 66)
TEXT = (235, 238, 245)
DIM = (154, 164, 185)
GOLD = (255, 207, 90)


def shop_rect(item):
    """Identical building placement in the editor, world renderer and trigger."""
    return pygame.Rect((item["x"] - 1) * TILESIZE,
                       (item["y"] - 2) * TILESIZE, *SHOP_SIZE)


def load_shop_image():
    if SHOP_IMAGE.is_file():
        return pygame.transform.scale(pygame.image.load(str(SHOP_IMAGE)).convert_alpha(), SHOP_SIZE)
    image = pygame.Surface(SHOP_SIZE, pygame.SRCALPHA)
    image.fill("white")
    return image


class Shop:
    def __init__(self, decor):
        self.buildings = [shop_rect(item) for item in decor if item["id"] == "shop"]
        self.is_open = False
        self.player = None
        self.selected = 0
        self.message = "Botlar sonraki bölümlere taşınır."
        self.opened_at = 0
        self.font = pygame.font.Font("font/PublicPixel.ttf", 12)
        self.title_font = pygame.font.Font("font/PublicPixel.ttf", 20)
        self.neon = self.make_neon() if self.buildings else None
        self.nazar = (pygame.image.load(str(NAZAR_IMAGE)).convert_alpha()
                      if self.buildings and NAZAR_IMAGE.is_file() else None)
        self.nudge = 0.0  # extra swing after the player walks past the door

    @staticmethod
    def make_neon():
        """The sign's letters lit up, with a warm halo, to blink over the board."""
        if not SHOP_IMAGE.is_file():
            return None
        art = pygame.transform.scale(pygame.image.load(str(SHOP_IMAGE)).convert_alpha(), SHOP_SIZE)
        neon = pygame.Surface(SHOP_SIZE, pygame.SRCALPHA)
        ink = [(x, y) for x in range(SIGN_AREA.left, SIGN_AREA.right)
               for y in range(SIGN_AREA.top, SIGN_AREA.bottom) if art.get_at((x, y))[:3] == SIGN_INK]
        for x, y in ink:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if SIGN_AREA.collidepoint(x + dx, y + dy):
                    neon.set_at((x + dx, y + dy), (255, 214, 140, 110))
        for x, y in ink:
            neon.set_at((x, y), (255, 84, 70, 255))
        return neon

    @staticmethod
    def neon_lit(ms):
        """On most of the time, with a short neon stutter every four seconds."""
        t = ms % 4000
        return not (2600 <= t < 2700 or 2800 <= t < 2950)

    def draw_world(self, screen, offset):
        """Effects on the shop art itself: the blinking sign and the swinging nazar."""
        if not self.buildings:
            return
        ms = pygame.time.get_ticks()
        import globals as G
        player = G.player
        if player is not None and self.doorway(player) is not None and abs(player.velocity_x) > 3:
            self.nudge = 18.0
        self.nudge *= 0.97
        angle = (8 + self.nudge) * math.sin(ms / 420)
        for building in self.buildings:
            top_left = pygame.Vector2(building.topleft) - offset
            if self.neon is not None and self.neon_lit(ms):
                screen.blit(self.neon, top_left)
            if self.nazar is not None:
                w, h = self.nazar.get_size()
                padded = pygame.Surface((2 * h, 2 * h), pygame.SRCALPHA)
                padded.blit(self.nazar, (h - w // 2, h))  # string top on the centre
                swung = pygame.transform.rotate(padded, angle)
                pivot = top_left + NAZAR_PIVOT
                screen.blit(swung, swung.get_rect(center=(round(pivot.x), round(pivot.y))))

    def doorway(self, player):
        if player.health <= 0 or player.is_caged or not player.on_ground:
            return None
        feet = player.base_player_rect
        for building in self.buildings:
            if (building.centerx - TILESIZE // 2 <= feet.centerx < building.centerx + TILESIZE // 2
                    and abs(feet.bottom - building.bottom) <= 8):
                return building
        return None

    def try_open(self, player):
        if self.is_open or self.doorway(player) is None:
            return False
        self.player = player
        self.is_open = True
        self.opened_at = pygame.time.get_ticks()
        self.message = "Botlar sonraki bölümlere taşınır."
        player.is_shooting = False
        return True

    def close(self):
        if not self.is_open:
            return
        # These two systems use wall-clock timers; preserve their remaining time.
        import globals as G
        elapsed = pygame.time.get_ticks() - self.opened_at
        if self.player.is_reloading:
            self.player.reload_timer += elapsed
        for bullet in G.bullet_group:
            bullet.spawn_time += elapsed
        self.is_open = False

    def unavailable(self, index):
        key = OFFERS[index][0]
        if key in game_stats.get("shop_upgrades", ()):
            return "Alındı"
        if key == "heal" and self.player.health >= 100:
            return "Can dolu"
        return ""

    def buy(self, index):
        if not self.is_open or not 0 <= index < len(OFFERS) or self.player.health <= 0:
            return False
        key, name, _, price = OFFERS[index]
        reason = self.unavailable(index)
        if reason:
            self.message = reason
            return False
        if game_stats["coins"] < price:
            self.message = "Altın yetersiz."
            return False
        player = self.player
        if key == "heal":
            player.increase_health(40)
        elif key == "ammo":
            player.total_ammo += 30
        else:
            game_stats.setdefault("shop_upgrades", []).append(key)
        game_stats["coins"] -= price
        self.message = f"Satın alındı: {name}"
        return True

    @staticmethod
    def panel_rect(screen):
        return pygame.Rect(0, 0, 820, 510).move(
            (screen.get_width() - 820) // 2, (screen.get_height() - 510) // 2)

    def offer_rect(self, screen, index):
        panel = self.panel_rect(screen)
        return pygame.Rect(panel.x + 24, panel.y + 104 + index * 78, panel.w - 48, 68)

    def handle_event(self, event, screen):
        """Called only while open; the main loop consumes all modal input."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_e):
                self.close()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(OFFERS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(OFFERS)
            elif pygame.K_1 <= event.key <= pygame.K_4:
                self.selected = event.key - pygame.K_1
                self.buy(self.selected)
            elif event.key == pygame.K_RETURN:
                self.buy(self.selected)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index in range(len(OFFERS)):
                if self.offer_rect(screen, index).collidepoint(event.pos):
                    self.selected = index
                    self.buy(index)
                    break

    def text(self, screen, text, pos, colour=TEXT, font=None):
        screen.blit((font or self.font).render(text, True, colour), pos)

    def draw_prompt(self, screen, player, offset):
        building = self.doorway(player)
        if building is None:
            return
        text = self.font.render("[E] Dükkan", True, GOLD)
        rect = text.get_rect(midbottom=(building.centerx - offset.x, building.top - offset.y - 8))
        pygame.draw.rect(screen, BG, rect.inflate(16, 12), border_radius=4)
        screen.blit(text, rect)

    def draw(self, screen):
        if not self.is_open:
            return
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        panel = self.panel_rect(screen)
        pygame.draw.rect(screen, BG, panel, border_radius=8)
        pygame.draw.rect(screen, GOLD, panel, 2, border_radius=8)
        self.text(screen, "Dükkan", (panel.x + 24, panel.y + 24), GOLD, self.title_font)
        self.text(screen, f"Altın: {game_stats['coins']}", (panel.right - 240, panel.y + 28), GOLD)
        self.text(screen, f"Can: {self.player.health}/100   Mermi: {self.player.total_ammo}",
                  (panel.x + 24, panel.y + 68), DIM)
        for index, (_, name, description, price) in enumerate(OFFERS):
            rect = self.offer_rect(screen, index)
            reason = self.unavailable(index)
            affordable = game_stats["coins"] >= price and not reason
            pygame.draw.rect(screen, CARD, rect, border_radius=4)
            if self.selected == index:
                pygame.draw.rect(screen, GOLD, rect, 2, border_radius=4)
            self.text(screen, f"{index + 1}. {name}", (rect.x + 14, rect.y + 12))
            self.text(screen, description, (rect.x + 14, rect.y + 40), DIM)
            label = reason or f"{price} altın"
            rendered = self.font.render(label, True, GOLD if affordable else DIM)
            screen.blit(rendered, rendered.get_rect(midright=(rect.right - 14, rect.y + 22)))
        self.text(screen, self.message, (panel.x + 24, panel.y + 430), GOLD)
        self.text(screen, "Tıkla / 1-4: al   Oklar + Enter: al   E / Esc: çık",
                  (panel.x + 24, panel.y + 474), DIM)
