"""Player projectiles with wall collisions and a limited lifetime."""
import math
import pygame
import globals as G


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle):
        super().__init__(G.bullet_group, G.all_sprites_group)
        image = G.bullet_img
        if image is None:
            image = pygame.Surface((10, 10))
            image.fill((255, 255, 0))
        self.image = pygame.transform.rotozoom(image, 0, 0.5)
        self.rect = self.image.get_rect(center=(x, y))
        self.x = x
        self.y = y
        self.x_vel = math.cos(math.radians(angle)) * 10
        self.y_vel = math.sin(math.radians(angle)) * 10
        self.spawn_time = pygame.time.get_ticks()
        self.bullet_lifetime = 1000

    def update(self):
        self.x += self.x_vel
        self.y += self.y_vel
        self.rect.center = (int(self.x), int(self.y))
        if (pygame.time.get_ticks() - self.spawn_time > self.bullet_lifetime
                or pygame.sprite.spritecollideany(self, G.obstacles_group)):
            self.kill()
