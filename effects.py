"""
effects.py

Short-lived eye candy: sparkles and hearts, rings of light, goose feathers,
coin twinkles and brick debris. Each effect is a sprite in all_sprites_group
(so the level draws it) and in effects_group (so it keeps moving while the
"level cleared" banner freezes everything else).
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


def coin_twinkle(center):
    """A small golden star pop where a coin was picked up."""
    burst(center, 6, 3.2, hearts=0, colours=((255, 236, 150), (255, 255, 255), (255, 210, 90)),
          life=(12, 18), size=2)


class Feather(Effect):
    """A goose feather that pops up, then rocks from side to side as it floats down."""

    def __init__(self, pos):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(random.uniform(-3, 3), random.uniform(-5, -2))
        self.phase = random.uniform(0, 2 * math.pi)
        self.life = self.max_life = random.randint(70, 100)
        grey = random.choice(((250, 250, 252), (232, 234, 240), (210, 212, 222)))
        base = pygame.Surface((7, 3), pygame.SRCALPHA)
        pygame.draw.ellipse(base, grey, (0, 0, 7, 3))
        pygame.draw.line(base, (170, 172, 186), (1, 1), (5, 1))  # the quill
        self.base = base
        self.image = base
        self.rect = base.get_rect(center=pos)

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()
            return
        level = G.game_level
        if level is not None and level.solid_at_pixel(int(self.pos.x), int(self.pos.y) + 2):
            # landed: lie still on the ground and fade out
            self.life = min(self.life, 25)
            sway = 0.0
        else:
            self.phase += 0.12
            if self.vel.y < 1.0:
                self.vel.y += 0.25
            self.vel.x *= 0.94
            sway = math.sin(self.phase)
            self.pos += (self.vel.x + sway * 0.9, self.vel.y)
        image = pygame.transform.rotate(self.base, sway * 35)
        image.set_alpha(int(255 * min(1, self.life / 25)))
        self.image = image
        self.rect = image.get_rect(center=(round(self.pos.x), round(self.pos.y)))


def feathers(center, count=9):
    for _ in range(count):
        Feather((center[0] + random.randint(-8, 8), center[1] + random.randint(-6, 6)))


class Debris(Effect):
    """A spinning piece of a broken brick that falls off the screen."""

    def __init__(self, image, pos, velocity):
        super().__init__()
        self.base = image
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(velocity)
        self.angle = 0
        self.spin = random.choice((-1, 1)) * random.uniform(8, 16)
        self.life = 90
        self.image = image
        self.rect = image.get_rect(center=pos)

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()
            return
        self.vel.y += 0.8
        self.pos += self.vel
        self.angle += self.spin
        self.image = pygame.transform.rotate(self.base, self.angle)
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))


def brick_debris(texture, tile_rect):
    """Four quarters of a brick tile flying up and out."""
    half = tile_rect.width // 2
    for i, (qx, qy) in enumerate(((0, 0), (half, 0), (0, half), (half, half))):
        piece = texture.subsurface((qx, qy, half, half)).copy() if texture else None
        if piece is None:
            piece = pygame.Surface((half, half))
            piece.fill((175, 75, 50))
        side = -1 if qx == 0 else 1
        Debris(piece, (tile_rect.x + qx + half // 2, tile_rect.y + qy + half // 2),
               (side * random.uniform(2, 4), -random.uniform(9, 12) + (3 if qy else 0)))
