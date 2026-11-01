"""Acid the player pours on the ground: a puddle that dissolves enemies for a few seconds."""
import random
import pygame
import globals as G
from settings import TILESIZE

PUDDLE_SIZE = (TILESIZE * 3, 12)
LIFETIME = 240     # game ticks the puddle stays (4 seconds)
FADE_TICKS = 60    # it fades out over the last second


def puddle_frames(count=4):
    """Bubbling green puddle; each frame moves the bubbles."""
    width, height = PUDDLE_SIZE
    rng = random.Random(7)
    bubbles = [(rng.randrange(8, width - 8), rng.randrange(count)) for _ in range(7)]
    frames = []
    for frame in range(count):
        surface = pygame.Surface(PUDDLE_SIZE, pygame.SRCALPHA)
        pygame.draw.ellipse(surface, (40, 120, 30, 230), (0, 3, width, height - 3))
        pygame.draw.ellipse(surface, (110, 210, 60, 230), (4, 4, width - 8, height - 7))
        pygame.draw.ellipse(surface, (190, 250, 120, 200), (14, 5, width // 3, 3))
        for x, phase in bubbles:
            rise = (frame + phase) % count
            pygame.draw.circle(surface, (210, 255, 150, 230), (x, height - 5 - rise * 2), 2 if rise < 3 else 1)
        frames.append(surface)
    return frames


class AcidPuddle(pygame.sprite.Sprite):
    FRAME_TICKS = 6
    frames = None

    def __init__(self, midbottom):
        super().__init__(G.all_sprites_group)
        if AcidPuddle.frames is None:
            AcidPuddle.frames = puddle_frames()
        self.image = self.frames[0]
        self.rect = self.image.get_rect(midbottom=midbottom)
        self.age = 0

    def update(self):
        self.age += 1
        if self.age >= LIFETIME:
            self.kill()
            return
        self.image = self.frames[(self.age // self.FRAME_TICKS) % len(self.frames)]
        if self.age > LIFETIME - FADE_TICKS:
            self.image = self.image.copy()
            self.image.set_alpha(255 * (LIFETIME - self.age) // FADE_TICKS)
        for enemy in list(G.enemy_group):
            if enemy.alive() and self.rect.colliderect(enemy.rect):
                self.dissolve(enemy)

    @staticmethod
    def dissolve(enemy):
        from settings import game_stats
        game_stats["score"] += 100
        if getattr(G, "enemy_death_sound", None):
            G.enemy_death_sound.play()
        if getattr(G, "create_floating_text", None):
            G.create_floating_text("+100", enemy.rect.center, (150, 255, 90))
        enemy.kill()
