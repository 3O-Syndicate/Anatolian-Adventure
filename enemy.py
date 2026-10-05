"""
enemy.py

Module Description:
    Defines the Enemy class and AI behaviors.
    Handles pathfinding, state transitions (Idle/Roam/Hunt), animation cycles,
    and interaction with the player (damage dealing).

Key Features:
    - Distinct AI behaviors for melee (Nightborne) and ranged (Necromancer) enemies.
    - Collision avoidance and unstuck mechanics.
    - Loot drop system upon death.
"""
import pygame
import random
import math
import globals as G
from settings import *
from settings import import_folder
from bullet import Bullet

class Enemy(pygame.sprite.Sprite):
    def __init__(self, name, position):
        super().__init__(G.enemy_group, G.all_sprites_group)
        self.alive = True
        self.position = pygame.math.Vector2(position)
        self.name = name

        # Load Enemy Stats from Settings
        enemy_info = monster_data[self.name]
        self.health = enemy_info["health"]
        self.roaming_speed = enemy_info["roaming_speed"]
        self.hunting_speed = random.choice(enemy_info["hunting_speed"])
        self.image_scale = enemy_info["image_scale"]

        # Combat Attributes
        self.can_attack = True
        self.attack_time = 0
        self.attack_cooldown = 2000 # 2 seconds

        # Asset Initialization
        base_image = enemy_info.get("image")
        if base_image is None:
            try:
                base_image = pygame.image.load(enemy_info.get("image_path")).convert_alpha()
            except Exception:
                base_image = pygame.Surface((64,64)); base_image.fill((150,0,0))

        self.image = base_image.convert_alpha()
        self.image = pygame.transform.rotozoom(self.image, 0, self.image_scale)

        # Animation Settings
        self.animation_speed = enemy_info["animation_speed"]
        self.roam_animation_speed = enemy_info["roam_animation_speed"]
        self.death_animation_speed = enemy_info["death_animation_speed"]
        self.notice_radius = enemy_info["notice_radius"]
        self.attack_damage = enemy_info["attack_damage"]

        self.import_graphics(name)
        self.current_index = 0
        self.image.set_colorkey((0,0,0))

        # Physics & Hitboxes
        self.rect = self.image.get_rect(center=position)
        self.hitbox_rect = enemy_info["hitbox_rect"]
        self.base_zombie_rect = self.hitbox_rect.copy()
        self.base_zombie_rect.center = self.rect.center

        # Movement Vectors
        self.velocity = pygame.math.Vector2()
        self.direction = pygame.math.Vector2()

        # Roaming Logic
        self.direction_list = [(1,1), (1,-1), (-1,1), (-1,-1)]
        self.direction_index = random.randint(0, 3)
        self.steps = random.randint(3, 6) * TILESIZE

        self.coin_dropped = False
        self.stuck_timer = 0
        self.last_pos = pygame.math.Vector2(position)

    def check_alive(self):
        """Checks health status and handles death events (score/sound)."""
        if self.health <= 0:
            self.alive = False
            if self.name == "necromancer":
                if G.necromancer_death_sound: G.necromancer_death_sound.play()
                game_stats["necromancer_death_count"] += 1
                game_stats["score"] += 250
            if self.name == "nightborne":
                if G.nightborne_death_sound: G.nightborne_death_sound.play()
                game_stats["nightborne_death_count"] += 1
                game_stats["score"] += 100
            game_stats["enemies_killed_or_removed"] += 1

    def import_graphics(self, name):
        """Loads sprite sheets for different states."""
        self.animations = {'roam': [], 'death': [], 'hunt': []}
        main_path = f'{name}/'
        for animation in self.animations.keys():
            try:
                self.animations[animation] = import_folder(main_path + animation)
            except Exception:
                self.animations[animation] = []

    def animate(self, index, animation_speed, sprite_list, type):
        """Handles frame updates and sprite flipping."""
        index += animation_speed
        if index >= len(sprite_list):
            index = 0
            if type == "death":
                self.kill()
                return index

        if sprite_list:
            self.image = sprite_list[int(index)]
            self.image = pygame.transform.rotozoom(self.image, 0, self.image_scale)
            if self.velocity.x < 0:
                self.image = pygame.transform.flip(self.image, True, False)
        return index

    def get_vector_distance(self, vector_1, vector_2):
        return (vector_1 - vector_2).magnitude()

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if not self.can_attack:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True

    # --- MOVEMENT & PHYSICS ENGINE ---
    def move_and_collide(self, speed):
        """
        Updates position based on direction and handles collisions independently on X and Y axes.
        """
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        self.velocity = self.direction * speed
        self.position += self.velocity

        self.base_zombie_rect.centerx = self.position.x
        self.check_collision("horizontal")
        self.base_zombie_rect.centery = self.position.y
        self.check_collision("vertical")

        self.rect.center = self.base_zombie_rect.center
        self.position = pygame.math.Vector2(self.base_zombie_rect.center)

    def check_collision(self, direction):
        """Resolves collisions with environment obstacles."""
        for sprite in G.obstacles_group:
            if sprite.rect.colliderect(self.base_zombie_rect):
                if direction == "horizontal":
                    if self.velocity.x > 0: self.base_zombie_rect.right = sprite.rect.left
                    if self.velocity.x < 0: self.base_zombie_rect.left = sprite.rect.right
                if direction == "vertical":
                    if self.velocity.y < 0: self.base_zombie_rect.top = sprite.rect.bottom
                    if self.velocity.y > 0: self.base_zombie_rect.bottom = sprite.rect.top

                # Reroute roaming enemies upon hitting a wall
                if self.get_vector_distance(pygame.math.Vector2(G.player.rect.center), self.position) > self.notice_radius:
                    self.direction_index = random.randint(0, 3)
                    self.steps = random.randint(3, 6) * TILESIZE

    # --- ARTIFICIAL INTELLIGENCE (AI) ---

    def ai_roam(self):
        """Default behavior when player is out of range."""
        self.direction.x, self.direction.y = self.direction_list[self.direction_index]
        self.move_and_collide(self.roaming_speed)
        self.steps -= 1
        if self.steps <= 0:
            self.direction_index = random.randint(0, 3)
            self.steps = random.randint(3, 6) * TILESIZE

        self.current_index = self.animate(self.current_index, self.roam_animation_speed, self.animations["roam"], "idle")

    def ai_nightborne_hunt(self, player_pos):
        """
        Melee AI: Aggressively chases the player.
        """
        self.direction = (player_pos - self.position)
        # Unstuck mechanism
        if self.stuck_check():
             self.direction += pygame.math.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5))

        self.move_and_collide(self.hunting_speed)
        self.current_index = self.animate(self.current_index, self.animation_speed, self.animations["hunt"], "hunt")

        # Melee Attack
        if self.base_zombie_rect.colliderect(G.player.base_player_rect):
            self.kill()
            G.player.get_damage(self.attack_damage)
            game_stats["enemies_killed_or_removed"] += 1

    def ai_necromancer_hunt(self, player_pos, dist):
        """
        Ranged AI: Maintains optimal distance and fires projectiles.
        """
        target_distance = 350
        retreat_distance = 200

        # Attack Logic
        if dist < 400 and self.can_attack:
            self.shoot_fireball(player_pos)
            self.velocity = pygame.math.Vector2(0,0)

        # Positioning Logic
        if dist < retreat_distance:
            # Retreat if too close
            self.direction = (self.position - player_pos)
            self.move_and_collide(self.hunting_speed * 0.8)
            self.current_index = self.animate(self.current_index, self.animation_speed, self.animations["hunt"], "hunt")

        elif dist > target_distance:
            # Chase if too far
            self.direction = (player_pos - self.position)
            if self.stuck_check():
                 self.direction += pygame.math.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5))
            self.move_and_collide(self.hunting_speed)
            self.current_index = self.animate(self.current_index, self.animation_speed, self.animations["hunt"], "hunt")

        else:
            # Hold position
            self.velocity = pygame.math.Vector2(0,0)
            self.current_index = self.animate(self.current_index, self.roam_animation_speed, self.animations["roam"], "idle")

    def shoot_fireball(self, target_pos):
        """Creates a projectile aiming at the player."""
        dx = target_pos.x - self.position.x
        dy = target_pos.y - self.position.y
        angle = math.degrees(math.atan2(dy, dx))

        b = Bullet(self.position.x, self.position.y, angle, source="enemy")
        G.bullet_group.add(b)
        G.all_sprites_group.add(b)

        self.can_attack = False
        self.attack_time = pygame.time.get_ticks()

    def stuck_check(self):
        """Detects if the entity is stuck against geometry."""
        is_stuck = False
        if pygame.time.get_ticks() % 500 < 50:
            if self.position.distance_to(self.last_pos) < 2:
                is_stuck = True
            self.last_pos = pygame.math.Vector2(self.position)
        return is_stuck

    def draw_enemy_health(self):
        """Renders a dynamic health bar above the entity."""
        x, y = self.position
        if self.health > 60: col = GREEN
        elif self.health > 30: col = YELLOW
        else: col = RED
        width = int(self.base_zombie_rect.width * self.health / 100)
        pygame.draw.rect(G.screen, col, (x - 40 - G.game_level.offset.x, y - 45 - G.game_level.offset.y, width, 5))

    def update(self):
        self.cooldowns()
        self.draw_enemy_health()

        if self.alive:
            self.check_alive()

            player_pos = pygame.math.Vector2(G.player.base_player_rect.center)
            dist = self.get_vector_distance(player_pos, self.position)

            if dist < self.notice_radius:
                if self.name == "necromancer":
                    self.ai_necromancer_hunt(player_pos, dist)
                else:
                    self.ai_nightborne_hunt(player_pos)
            else:
                self.ai_roam()

        else:
            # --- LOOT DROP SYSTEM ---
            if not self.coin_dropped:
                self.coin_dropped = True
                import random
                rng = random.random()
                from item import Item

                # Drop Probabilities
                if rng < 0.60: Item(self.position, "coin")
                elif rng < 0.70: Item(self.position, "ammo")
                else:
                    if random.random() < 0.5: Item(self.position, "health potion")

            self.current_index = self.animate(self.current_index, self.death_animation_speed, self.animations["death"], "death")