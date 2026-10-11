"""
player.py

Module Description:
    Implements the Player class which handles user input, movement mechanics,
    collision detection, and the weapon system (shooting, reloading, ammo management).
"""

import pygame
import math
import random
import globals as G
from settings import *
from bullet import Bullet

class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()

        # Asset Initialization
        try:
            self.base_player_image = pygame.image.load("player/0.png").convert_alpha()
        except Exception:
            self.base_player_image = pygame.Surface((64,64))
            self.base_player_image.fill((100,200,100))

        self.base_player_image = pygame.transform.rotozoom(self.base_player_image, 0, 0.35)
        self.image = self.base_player_image.copy()

        # Physics Components
        self.vec_pos = pygame.math.Vector2(pos)
        self.base_player_rect = self.base_player_image.get_rect(center=pos)
        self.rect = self.base_player_rect.copy()

        # Movement Stats
        self.velocity_x = 0
        self.velocity_y = 0
        self.is_running = False
        self.direction = 0 # 0 = left, 1 = right

        # --- WEAPON & AMMO SYSTEM ---
        self.is_shooting = False
        self.shoot_cooldown = 0
        self.gun_barrel_offset = pygame.math.Vector2(45, 20)

        # Ammo Management
        self.max_ammo = 30         # Magazine Capacity
        self.current_ammo = 30     # Rounds in Magazine
        self.total_ammo = 120      # Reserve Ammo

        self.is_reloading = False
        self.reload_timer = 0
        self.reload_duration = 1500

        self.health = 100

    def player_turning(self):
        """Rotates the player sprite to face the mouse cursor."""
        if self.direction == 0:
            self.image = pygame.transform.flip(self.base_player_image, True, False)
        else:
            self.image = self.base_player_image
        self.rect = self.image.get_rect(center=self.base_player_rect.center)

    def player_input(self):
        # Processes keyboard and mouse events for movement and actions.
        keys = pygame.key.get_pressed()

        if keys[pygame.K_w]: 
            if(self.velocity_y == 0): self.velocity_y = -30
        elif keys[pygame.K_s]:
            if(self.velocity_y < 0):
                self.velocity_y = -self.velocity_y
        elif self.velocity_y:
            self.velocity_y += 1
            if(self.velocity_y == 0): self.velocity_y = 1
            if(self.velocity_y > 30): self.velocity_y = 30

        if keys[pygame.K_d]:
            if self.velocity_x<0: self.velocity_x*=-1;
            elif self.velocity_x<10: self.velocity_x += 1
            self.direction = 1
            if(self.velocity_y == 0): self.velocity_y = 1
        elif keys[pygame.K_a]:
            if self.velocity_x>0: self.velocity_x*=-1;
            elif self.velocity_x>-10: self.velocity_x -= 1
            self.direction = 0
            if(self.velocity_y == 0): self.velocity_y = 1
        elif self.velocity_x:
            if self.velocity_x>0: self.velocity_x -= 1
            else: self.velocity_x += 1

        # Reload Action
        if keys[pygame.K_r] and self.current_ammo < self.max_ammo and self.total_ammo > 0 and not self.is_reloading:
            self.start_reload()

        # DEBUG: Kill all enemies
        if keys[pygame.K_x]:
            for x in G.enemy_group:
                if x.alive:
                    x.alive = False
                    game_stats['enemies_killed_or_removed']+=1
            G.enemy_group.empty()

        # DEBUG: refresh screen
        if keys[pygame.K_c]:
            for i in range(1,144,4):
                for j in range(5):
                    rect = pygame.rect.Rect(0, 0, 1280, i)
                    G.screen.blit(G.plain_bg, (0,j*144), rect)
                    pygame.display.update()

        # Shooting Action
        if (pygame.mouse.get_pressed() == (1, 0, 0) or keys[pygame.K_SPACE]) and not self.is_reloading and self.current_ammo > 0:
            self.is_shooting = True
            self.shoot()
        else:
            self.is_shooting = False

        # Auto-Reload Logic
        if (pygame.mouse.get_pressed() == (1, 0, 0) or keys[pygame.K_SPACE]) and self.current_ammo <= 0 and self.total_ammo > 0 and not self.is_reloading:
            self.start_reload()

    def start_reload(self):
        self.is_reloading = True
        self.reload_timer = pygame.time.get_ticks()

    def check_reload(self):
        """Calculates ammo transfer from reserves to magazine after delay."""
        if self.is_reloading:
            current_time = pygame.time.get_ticks()
            if current_time - self.reload_timer >= self.reload_duration:
                needed_ammo = self.max_ammo - self.current_ammo

                if self.total_ammo >= needed_ammo:
                    self.current_ammo += needed_ammo
                    self.total_ammo -= needed_ammo
                else:
                    self.current_ammo += self.total_ammo
                    self.total_ammo = 0

                self.is_reloading = False

    def move(self):
        """Applies velocity and resolves collisions."""

        # # Normalize diagonal vector
        # if self.velocity_x != 0 and self.velocity_y != 0:
        #     self.velocity_x /= math.sqrt(2)
        #     self.velocity_y /= math.sqrt(2)

        self.base_player_rect.centerx += self.velocity_x
        self.check_collision(True)
        self.base_player_rect.centery += self.velocity_y
        self.check_collision(False)

        # Revert multiplications caused by tactical movements.

        self.rect.center = self.base_player_rect.center
        self.vec_pos = (self.base_player_rect.centerx, self.base_player_rect.centery)

    def shoot(self):
        """Spawns a bullet with random spread."""
        if self.shoot_cooldown == 0 and self.is_shooting:
            if G.gun_shot_sound:
                G.gun_shot_sound.play()

            final_angle = 0
            if(self.direction == 0): final_angle = 180

            spawn_bullet_pos = self.vec_pos + self.gun_barrel_offset.rotate(final_angle)
            bullet = Bullet(spawn_bullet_pos[0], spawn_bullet_pos[1], final_angle)

            G.bullet_group.add(bullet)
            G.all_sprites_group.add(bullet)

            self.current_ammo -= 1
            self.shoot_cooldown = 10

    def get_damage(self, amount):
        """Handles damage calculation and death sounds."""
        if G.ui.current_health > 0:
            G.ui.current_health -= amount
            self.health -= amount
            if G.ui.current_health > 0:
                if G.hurt_sound: G.hurt_sound.play()
            else:
                if G.death_sound: G.death_sound.play()
        if G.ui.current_health <= 0:
            G.ui.current_health = 0
            self.health = 0

    def increase_health(self, amount):
        if G.ui.current_health < G.ui.maximum_health:
            G.ui.current_health += amount
            self.health += amount
        if G.ui.current_health >= G.ui.maximum_health:
            G.ui.current_health = G.ui.maximum_health
            self.health = G.ui.maximum_health

    def check_collision(self, horizontal):
        for sprite in G.obstacles_group:
            if sprite.rect.colliderect(self.base_player_rect):
                if horizontal:
                    if self.velocity_x > 0: self.base_player_rect.right = sprite.rect.left
                    elif self.velocity_x < 0: self.base_player_rect.left = sprite.rect.right
                else:
                    if self.velocity_y < 0: 
                        self.base_player_rect.top = sprite.rect.bottom
                        self.velocity_y = 1
                    elif self.velocity_y > 0: 
                        self.base_player_rect.bottom = sprite.rect.top
                        self.velocity_y = 0

    def update(self):
        self.player_turning()
        self.check_reload()
        self.player_input()
        self.move()
        if self.shoot_cooldown > 0: self.shoot_cooldown -= 1
        if self.shoot: self.shoot()