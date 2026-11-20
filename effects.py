"""
effects.py

Short-lived eye candy: sparkles, hearts and rings of light. Each effect is a
sprite in all_sprites_group (so the level draws it) and in effects_group.
"""
import math
import random

import pygame

import globals as G

effects_group = pygame.sprite.Group()


class Effect(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(G.all_sprites_group, effects_group)


class Sparkle(Effect):
    """A twinkling star or heart that flies out and fades, drifting upwards."""
    COLOURS = ((255, 255, 255), (255, 236, 150), (255, 182, 206), (190, 230, 255))

    def __init__(self, pos, velocity, life, heart=False, colour=None, size=3, rise=0.06):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(velocity)
        self.life = self.max_life = life
        self.heart = heart
        self.colour = colour or random.choice(self.COLOURS)
        self.size = size
        self.rise = rise
        self.redraw()

    def redraw(self):
        fade = self.life / self.max_life
        size = 2 + round(self.size * fade)
        image = pygame.Surface((2 * size + 3, 2 * size + 3), pygame.SRCALPHA)
        c = size + 1
        col = (*self.colour, int(255 * min(1, fade * 1.6)))
        if self.heart:
            r = max(1, size // 2)
            pygame.draw.circle(image, col, (c - r, c - r // 2), r)
            pygame.draw.circle(image, col, (c + r, c - r // 2), r)
            pygame.draw.polygon(image, col, [(c - 2 * r, c - r // 2), (c + 2 * r, c - r // 2), (c, c + size)])
        else:
            pygame.draw.line(image, col, (c - size, c), (c + size, c))
            pygame.draw.line(image, col, (c, c - size), (c, c + size))
            pygame.draw.rect(image, col, (c - 1, c - 1, 3, 3))
        self.image = image
        self.rect = image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()
            return
        self.pos += self.vel
        self.vel *= 0.92
        self.vel.y -= self.rise
        self.redraw()


class Ring(Effect):
    """A soft ring of light that widens and fades."""

    def __init__(self, center, life=24, colour=(255, 246, 220), reach=70):
        super().__init__()
        self.center = center
        self.life = self.max_life = life
        self.colour = colour
        self.reach = reach
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=center)

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()
            return
        t = 1 - self.life / self.max_life
        radius = int(8 + self.reach * t)
        image = pygame.Surface((2 * radius + 4, 2 * radius + 4), pygame.SRCALPHA)
        pygame.draw.circle(image, (*self.colour, int(200 * (1 - t))), (radius + 2, radius + 2), radius,
                           max(1, int(5 * (1 - t))))
        self.image = image
        self.rect = image.get_rect(center=self.center)


def burst(center, count, speed, hearts=0.3, colours=None, life=(28, 46), size=3):
    """Sparkles (and some hearts) flying out in a ring."""
    for i in range(count):
        angle = 2 * math.pi * i / count + random.uniform(-0.2, 0.2)
        v = speed * random.uniform(0.6, 1.1)
        Sparkle(center, (math.cos(angle) * v, math.sin(angle) * v - 1), random.randint(*life),
                heart=random.random() < hearts,
                colour=random.choice(colours) if colours else None, size=size)
