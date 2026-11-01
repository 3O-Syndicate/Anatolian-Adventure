"""Cage mechanism: Traps player at start, breaks open with debris and screen shake."""
import math
import random
import pygame
import globals as G

DARK_IRON = (38, 41, 48)
MID_IRON = (65, 70, 80)
LIGHT_IRON = (120, 126, 140)
HIGHLIGHT = (180, 185, 195)
RIVET = (210, 215, 225)
GOLD = (230, 180, 40)
DARK_GOLD = (150, 110, 20)
YELLOW = (255, 225, 50)
WHITE = (255, 255, 255)


class CagePrompt(pygame.sprite.Sprite):
    """Floating animated banner above the cage."""

    def __init__(self, cage, font):
        super().__init__(G.all_sprites_group)
        self.cage = cage
        self.font = font
        self.base_y = cage.rect.top - 36
        self.timer = 0
        self.render_prompt()
        self.rect = self.image.get_rect(center=(cage.rect.centerx, self.base_y))

    def render_prompt(self):
        line1 = self.font.render("[E] OR [SPACE]", True, YELLOW)
        line2 = self.font.render("BREAK THE CAGE!", True, WHITE)

        padding = 8
        width = max(line1.get_width(), line2.get_width()) + padding * 2
        height = line1.get_height() + line2.get_height() + padding * 2 + 4

        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        # Dark pill container with glowing outline
        pygame.draw.rect(surf, (15, 18, 25, 210), (0, 0, width, height), border_radius=6)
        pygame.draw.rect(surf, (220, 180, 50, 220), (0, 0, width, height), width=2, border_radius=6)

        surf.blit(line1, (width // 2 - line1.get_width() // 2, padding))
        surf.blit(line2, (width // 2 - line2.get_width() // 2, padding + line1.get_height() + 4))
        self.image = surf

    def update(self):
        self.timer += 0.08
        float_offset = math.sin(self.timer) * 4
        self.rect.centery = int(self.base_y + float_offset)
        self.rect.centerx = self.cage.rect.centerx


class FreedomBanner(pygame.sprite.Sprite):
    """Short-lived celebratory banner appearing when the cage breaks."""

    def __init__(self, pos, font):
        super().__init__(G.all_sprites_group)
        text = font.render("FREEDOM!", True, YELLOW)

        w, h = text.get_width() + 16, text.get_height() + 10
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (20, 20, 30, 200), (0, 0, w, h), border_radius=5)
        pygame.draw.rect(surf, YELLOW, (0, 0, w, h), width=2, border_radius=5)
        surf.blit(text, (8, 5))

        self.image = surf
        self.rect = self.image.get_rect(center=pos)
        self.y = float(self.rect.centery)
        self.timer = 60

    def update(self):
        self.timer -= 1
        self.y -= 1.0
        self.rect.centery = int(self.y)
        if self.timer < 20:
            alpha = max(0, int(255 * (self.timer / 20)))
            self.image.set_alpha(alpha)
        if self.timer <= 0:
            self.kill()


class CageDebris(pygame.sprite.Sprite):
    """Flying rotating debris fragment from broken cage."""

    def __init__(self, image, pos, x_vel, y_vel, rot_speed):
        super().__init__(G.all_sprites_group)
        self.original_image = image
        self.image = image
        self.rect = self.image.get_rect(center=pos)
        self.x = float(pos[0])
        self.y = float(pos[1])
        self.x_vel = x_vel
        self.y_vel = y_vel
        self.angle = 0
        self.rot_speed = rot_speed
        self.gravity = 0.55
        self.timer = 100

    def update(self):
        self.timer -= 1
        self.x += self.x_vel
        self.y += self.y_vel
        self.y_vel += self.gravity
        self.angle = (self.angle + self.rot_speed) % 360

        # Rotate image
        self.image = pygame.transform.rotozoom(self.original_image, self.angle, 1.0)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        if self.timer < 25:
            alpha = max(0, int(255 * (self.timer / 25)))
            self.image.set_alpha(alpha)
        if self.timer <= 0 or self.y > 1500:
            self.kill()


class CageSpark(pygame.sprite.Sprite):
    """Explosive spark/particle flying outward upon impact."""

    def __init__(self, pos, color, x_vel, y_vel, radius=3):
        super().__init__(G.all_sprites_group)
        self.color = color
        self.radius = radius
        self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (radius, radius), radius)
        self.rect = self.image.get_rect(center=pos)
        self.x = float(pos[0])
        self.y = float(pos[1])
        self.x_vel = x_vel
        self.y_vel = y_vel
        self.timer = random.randint(20, 35)

    def update(self):
        self.timer -= 1
        self.x += self.x_vel
        self.y += self.y_vel
        self.y_vel += 0.35
        self.x_vel *= 0.95
        self.rect.center = (int(self.x), int(self.y))
        if self.timer < 10:
            alpha = max(0, int(255 * (self.timer / 10)))
            self.image.set_alpha(alpha)
        if self.timer <= 0:
            self.kill()


class Cage(pygame.sprite.Sprite):
    """The starting iron cage enclosing the player."""

    def __init__(self, player, font):
        ground_y = self.floor_below(player.base_player_rect)  # before the cage joins the obstacles
        super().__init__(G.obstacles_group, G.all_sprites_group)
        self.player = player
        self.font = font
        self.width = 110
        self.height = 96
        self.is_broken = False

        # Anchor player directly to the ground inside the cage
        self.player.base_player_rect.bottom = ground_y
        self.player.rect.center = self.player.base_player_rect.center
        self.player.vec_pos = pygame.math.Vector2(self.player.base_player_rect.center)
        self.player.on_ground = True
        self.player.velocity_y = 0
        self.player.velocity_x = 0
        self.player.is_caged = True

        self.image = self.build_cage_surface()
        self.rect = self.image.get_rect(midbottom=(self.player.base_player_rect.centerx, ground_y))

        # Floating interaction prompt
        self.prompt = CagePrompt(self, font)

    @staticmethod
    def floor_below(rect):
        """Top of the first solid tile under `rect`: the floor of the level's start position."""
        tops = [tile.rect.top for tile in G.obstacles_group
                if tile.rect.left < rect.right and tile.rect.right > rect.left
                and tile.rect.top >= rect.top]
        return min(tops, default=rect.bottom)

    def build_cage_surface(self):
        w, h = self.width, self.height
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Top beam (roof)
        pygame.draw.rect(surf, DARK_IRON, (0, 0, w, 14))
        pygame.draw.rect(surf, MID_IRON, (1, 1, w - 2, 12))
        pygame.draw.line(surf, HIGHLIGHT, (2, 2), (w - 3, 2), 2)
        pygame.draw.line(surf, DARK_IRON, (1, 13), (w - 2, 13), 1)

        # Bottom beam (base)
        pygame.draw.rect(surf, DARK_IRON, (0, h - 12, w, 12))
        pygame.draw.rect(surf, MID_IRON, (1, h - 11, w - 2, 10))
        pygame.draw.line(surf, HIGHLIGHT, (2, h - 11), (w - 3, h - 11), 1)

        # Left & Right Pillars
        for x in (0, w - 12):
            pygame.draw.rect(surf, DARK_IRON, (x, 0, 12, h))
            pygame.draw.rect(surf, MID_IRON, (x + 1, 1, 10, h - 2))
            pygame.draw.line(surf, HIGHLIGHT, (x + 2, 2), (x + 2, h - 3), 1)

        # 4 Vertical Iron Bars
        bars_x = [24, 42, 60, 78]
        for bx in bars_x:
            pygame.draw.rect(surf, DARK_IRON, (bx - 4, 12, 8, h - 24))
            pygame.draw.rect(surf, MID_IRON, (bx - 3, 12, 6, h - 24))
            pygame.draw.line(surf, LIGHT_IRON, (bx - 1, 12), (bx - 1, h - 24), 2)
            pygame.draw.line(surf, HIGHLIGHT, (bx, 14), (bx, h - 26), 1)

        # Middle Reinforcing Crossbar
        mid_y = h // 2 - 4
        pygame.draw.rect(surf, DARK_IRON, (0, mid_y, w, 9))
        pygame.draw.rect(surf, MID_IRON, (1, mid_y + 1, w - 2, 7))
        pygame.draw.line(surf, HIGHLIGHT, (2, mid_y + 2), (w - 3, mid_y + 2), 1)

        # Rivets on top and bottom beams
        for rx in [6, 24, 42, 60, 78, w - 6]:
            pygame.draw.circle(surf, RIVET, (rx, 7), 2)
            pygame.draw.circle(surf, DARK_IRON, (rx, 7), 1)
            pygame.draw.circle(surf, RIVET, (rx, h - 6), 2)
            pygame.draw.circle(surf, DARK_IRON, (rx, h - 6), 1)
            pygame.draw.circle(surf, RIVET, (rx, mid_y + 4), 2)
            pygame.draw.circle(surf, DARK_IRON, (rx, mid_y + 4), 1)

        # Padlock in the center
        cx, cy = w // 2, mid_y + 4
        pygame.draw.arc(surf, LIGHT_IRON, (cx - 7, cy - 13, 14, 12), 0, math.pi, 3)
        pygame.draw.rect(surf, DARK_GOLD, (cx - 9, cy - 5, 18, 16), border_radius=3)
        pygame.draw.rect(surf, GOLD, (cx - 8, cy - 4, 16, 14), border_radius=2)
        pygame.draw.circle(surf, (30, 20, 10), (cx, cy + 1), 2)
        pygame.draw.line(surf, (30, 20, 10), (cx, cy + 2), (cx, cy + 6), 2)

        return surf

    def update(self):
        # Keep player confined while inside cage
        if not self.is_broken and self.player.is_caged:
            self.player.base_player_rect.centerx = self.rect.centerx
            self.player.rect.center = self.player.base_player_rect.center

    def break_open(self):
        if self.is_broken:
            return
        self.is_broken = True

        # Play sound
        if getattr(G, "cage_break_sound", None):
            G.cage_break_sound.play()
        elif getattr(G, "gun_shot_sound", None):
            G.gun_shot_sound.play()

        # Screen shake
        if getattr(G, "game_level", None):
            G.game_level.shake_timer = 14
            G.game_level.shake_amount = 7

        # Release player with dynamic kick
        self.player.is_caged = False
        kick_direction = 1 if self.player.direction == 1 else -1
        self.player.velocity_y = -10
        self.player.velocity_x = 7 * kick_direction
        self.player.shoot_cooldown = 20

        # Spawn debris pieces from the cage surface
        w, h = self.width, self.height
        cx, cy = self.rect.centerx, self.rect.centery

        # Top beam left & right
        top_l = self.image.subsurface((0, 0, w // 2, 14)).copy()
        CageDebris(top_l, (cx - w // 4, self.rect.top + 7), -4.5, -9.0, -8)
        top_r = self.image.subsurface((w // 2, 0, w // 2, 14)).copy()
        CageDebris(top_r, (cx + w // 4, self.rect.top + 7), 4.5, -9.0, 8)

        # Pillars
        pillar_l = self.image.subsurface((0, 0, 12, h)).copy()
        CageDebris(pillar_l, (self.rect.left + 6, cy), -6.5, -7.5, -12)
        pillar_r = self.image.subsurface((w - 12, 0, 12, h)).copy()
        CageDebris(pillar_r, (self.rect.right - 6, cy), 6.5, -7.5, 12)

        # Vertical bars
        bars_x = [24, 42, 60, 78]
        for idx, bx in enumerate(bars_x):
            bar_img = self.image.subsurface((bx - 4, 12, 8, h - 24)).copy()
            x_speed = (idx - 1.5) * 3.2
            CageDebris(bar_img, (self.rect.left + bx, cy), x_speed, random.uniform(-11, -7), random.uniform(-15, 15))

        # Padlock
        padlock_img = self.image.subsurface((w // 2 - 9, h // 2 - 9, 18, 24)).copy()
        CageDebris(padlock_img, (cx, cy), random.uniform(-3, 3), -11.0, 20)

        # Sparks / dust particles
        for _ in range(20):
            color = random.choice([
                (255, 230, 100), (255, 160, 50), (220, 220, 230), (180, 180, 190)
            ])
            s_vx = random.uniform(-7, 7)
            s_vy = random.uniform(-10, 2)
            CageSpark((cx, cy), color, s_vx, s_vy, radius=random.randint(2, 4))

        # Freedom banner
        FreedomBanner((cx, self.rect.top - 20), self.font)

        # Remove prompt & cage
        if self.prompt:
            self.prompt.kill()
        self.kill()
