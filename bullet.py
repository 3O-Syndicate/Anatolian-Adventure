"""
bullet.py

Module Description:
    Defines the Bullet class. Handles linear movement calculations,
    visual representation based on source (Player vs Enemy), and
    collision detection against entities and walls.
"""

import pygame
import math
import globals as G

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, source="player"):
        super().__init__()
        self.source = source
        self.speed = 10
        self.damage = 10

        # --- Visual Configuration ---
        if self.source == "player":
            # Player Projectile
            self.image = G.bullet_img
            if self.image is None:
                self.image = pygame.Surface((10, 10))
                self.image.fill((255, 255, 0))
            self.image = pygame.transform.rotozoom(self.image, 0, 0.5)
            self.bullet_lifetime = 1000

        else:
            # Enemy Projectile
            self.image = pygame.Surface((16, 16))
            self.image.fill((255, 0, 0))
            pygame.draw.circle(self.image, (255, 100, 100), (8,8), 6)
            self.bullet_lifetime = 2000
            self.speed = 6

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.x = x
        self.y = y
        self.angle = angle

        # Velocity Calculation
        self.x_vel = math.cos(self.angle * (2*math.pi/360)) * self.speed
        self.y_vel = math.sin(self.angle * (2*math.pi/360)) * self.speed

        self.spawn_time = pygame.time.get_ticks()

    def bullet_movement(self):
        """Updates bullet position over time."""
        self.x += self.x_vel
        self.y += self.y_vel
        self.rect.centerx = int(self.x)
        self.rect.centery = int(self.y)

        if pygame.time.get_ticks() - self.spawn_time > self.bullet_lifetime:
            self.kill()

    def bullet_collisions(self):
        """
        Checks for collisions.
        Uses direct Hitbox detection for enemies to ensure accuracy.
        """

        if self.source == "player":
            # Player hits Enemies
            for enemy in G.enemy_group:
                # Using 'base_zombie_rect' for precise hitbox collision
                if enemy.base_zombie_rect.colliderect(self.rect):
                    enemy.health -= 35
                    self.kill()
                    break

        elif self.source == "enemy":
            # Enemy hits Player
            if self.rect.colliderect(G.player.base_player_rect):
                G.player.get_damage(10)
                self.kill()

        # Obstacle Collision
        if pygame.sprite.spritecollide(self, G.obstacles_group, False):
            self.kill()

    def update(self):
        self.bullet_movement()
        self.bullet_collisions()