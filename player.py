"""
player.py

Module Description:
    Implements the Player class which handles user input, movement mechanics,
    collision detection, the weapon system (shooting, reloading, ammo management)
    and the hero's animations.
"""

import pygame
import globals as G
import assets
from settings import *
from bullet import Bullet


class MuzzleFlash(pygame.sprite.Sprite):
    """Short flash that stays on the gun's muzzle while it plays."""
    TICKS_PER_FRAME = 2

    def __init__(self, player):
        super().__init__(G.all_sprites_group)
        self.player = player
        self.age = 0
        self.place()

    def place(self):
        frame = G.muzzle_flash_imgs[self.age // self.TICKS_PER_FRAME]
        muzzle = self.player.muzzle_position()
        if self.player.direction == 1:
            self.image = frame
            self.rect = frame.get_rect(midleft=muzzle)
        else:
            self.image = pygame.transform.flip(frame, True, False)
            self.rect = self.image.get_rect(midright=muzzle)

    def update(self):
        self.age += 1
        if self.age >= len(G.muzzle_flash_imgs) * self.TICKS_PER_FRAME:
            self.kill()
        else:
            self.place()


class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()

        # Animations: frames face right; left-facing copies are flipped once here.
        if G.hero_anims is None:
            G.hero_meta, G.hero_anims = assets.placeholder_hero_animations()
        self.anim_meta = G.hero_meta
        self.frames_right = G.hero_anims
        self.frames_left = {name: [pygame.transform.flip(f, True, False) for f in frames]
                            for name, frames in self.frames_right.items()}
        self.frame_width = self.anim_meta["frame_size"][0]
        self.anchor = self.anim_meta["anchor"]
        self.stand_size = self.anim_meta["hitbox"]["stand"]
        self.duck_size = self.anim_meta["hitbox"]["duck"]
        self.anim_name = "idle"
        self.frame_index = 0
        self.frame_time = 0.0

        # Physics Components (the hitbox is fixed; frames are drawn around it)
        self.vec_pos = pygame.math.Vector2(pos)
        self.base_player_rect = pygame.Rect((0, 0), self.stand_size)
        self.base_player_rect.center = pos
        self.previous_rect = self.base_player_rect.copy()

        # Movement Stats
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
        self.jump_was_pressed = False
        self.coyote_timer = 0
        self.jump_buffer_timer = 0
        self.fell_in_pit = False
        self.down_was_pressed = False  # S held while the game starts must not crash the tunnel check
        self.tunnel_requested = False
        self.direction = 1 # 0 = left, 1 = right
        self.is_ducking = False

        # Animation timers, in game ticks
        self.shot_timer = 0
        self.land_timer = 0
        self.hurt_timer = 0
        self.death_timer = 0
        self.death_finished = False
        self.flash = None
        self.invulnerable_timer = 0  # after a respawn, enemies cannot hurt the player

        # --- WEAPON & AMMO SYSTEM ---
        self.is_shooting = False
        self.shoot_cooldown = 0

        # Ammo Management
        self.max_ammo = 30         # Magazine Capacity
        self.current_ammo = 30     # Rounds in Magazine
        self.total_ammo = 120      # Reserve Ammo

        self.is_reloading = False
        self.reload_timer = 0
        self.reload_duration = 1500

        self.health = 100
        self.is_caged = False
        self.cage = None

        self.animate()

    # --- ANIMATION ---
    def current_animation(self):
        """Pick the animation for the player's state, most important first."""
        if self.health <= 0:
            return "death"
        if self.hurt_timer > 0:
            return "hurt"
        if not self.on_ground:
            return "jump" if self.velocity_y < 0 else "fall"
        if self.is_ducking:
            return "duck_shoot" if self.shot_timer > 0 else "duck"
        if self.velocity_x != 0:
            return "run"
        if self.is_reloading:
            return "reload"
        if self.shot_timer > 0:
            return "shoot"
        if self.land_timer > 0:
            return "land"
        return "idle"

    def animate(self, restart=False):
        name = self.current_animation()
        prev_frame = self.frame_index
        if restart or name != self.anim_name:
            self.anim_name = name
            self.frame_index = 0
            self.frame_time = 0.0
        elif name == "run":
            # legs keep pace with the speed
            self.advance_frame(max(0.5, abs(self.velocity_x) / 6))
        else:
            self.advance_frame(1)
        if name == "reload":
            self.frame_index = self.reload_frame()

        frames = self.frames_right if self.direction == 1 else self.frames_left
        self.image = frames[name][self.frame_index]
        self.place_image()

        # Footstep audio synced with run animation (frames 0 and 3 in the 6-frame cycle)
        if name == "run" and self.on_ground and not self.is_ducking:
            if self.frame_index != prev_frame and self.frame_index in (0, 3):
                self.play_footstep()

    def play_footstep(self):
        sounds = getattr(G, "footstep_sounds", None)
        if sounds:
            import random
            random.choice(sounds).play()

    def advance_frame(self, speed):
        info = self.anim_meta["anims"][self.anim_name]
        durations = info["durations"]
        self.frame_time += 1000 / FPS * speed
        while self.frame_time >= durations[self.frame_index]:
            if self.frame_index + 1 < len(durations):
                self.frame_time -= durations[self.frame_index]
                self.frame_index += 1
            elif info["loop"]:
                self.frame_time -= durations[self.frame_index]
                self.frame_index = 0
            else:
                self.frame_time = 0.0  # hold the last frame
                break

    def reload_frame(self):
        """Reload frames follow the reload timer so the gun closes as ammo arrives."""
        durations = self.anim_meta["anims"]["reload"]["durations"]
        progress = (pygame.time.get_ticks() - self.reload_timer) / self.reload_duration
        elapsed = progress * sum(durations)
        for index, duration in enumerate(durations):
            if elapsed < duration:
                return index
            elapsed -= duration
        return len(durations) - 1

    def place_image(self):
        """Put the frame's anchor (between the feet) on the hitbox's bottom centre."""
        anchor_x = self.anchor[0] if self.direction == 1 else self.frame_width - self.anchor[0]
        self.rect = self.image.get_rect(topleft=(self.base_player_rect.centerx - anchor_x,
                                                 self.base_player_rect.bottom - self.anchor[1]))

    def muzzle_position(self):
        """World position of the gun's muzzle in the frame being shown."""
        mx, my = self.anim_meta["anims"][self.anim_name]["muzzle"][self.frame_index]
        if self.direction == 0:
            mx = self.frame_width - mx
        return (self.rect.left + mx, self.rect.top + my)

    def set_ducking(self, ducking):
        """Swap the standing and ducking hitbox, keeping the feet in place.

        Standing up is skipped while something solid is overhead.
        """
        if ducking == self.is_ducking:
            return
        rect = pygame.Rect((0, 0), self.duck_size if ducking else self.stand_size)
        rect.midbottom = self.base_player_rect.midbottom
        if not ducking and any(tile.rect.colliderect(rect) for tile in G.obstacles_group):
            return
        self.base_player_rect = rect
        self.is_ducking = ducking

    def player_input(self):
        # Processes keyboard and mouse events for movement and actions.
        keys = pygame.key.get_pressed()
        down_pressed = keys[pygame.K_s]
        self.tunnel_requested = down_pressed and not self.down_was_pressed and self.on_ground
        self.down_was_pressed = down_pressed

        if self.is_caged:
            if keys[pygame.K_d]:
                self.direction = 1
            elif keys[pygame.K_a]:
                self.direction = 0
            self.velocity_x = 0
            self.is_shooting = False
            if keys[pygame.K_e] or keys[pygame.K_SPACE]:
                if self.cage and not self.cage.is_broken:
                    self.cage.break_open()
            return

        # Hold S on the ground to duck
        self.set_ducking(keys[pygame.K_s] and self.on_ground)

        # Coyote time & Jump buffering
        jump_pressed = keys[pygame.K_w]
        if jump_pressed and not self.jump_was_pressed:
            self.jump_buffer_timer = 8
        self.jump_was_pressed = jump_pressed

        if self.on_ground:
            self.coyote_timer = 8
        elif self.coyote_timer > 0:
            self.coyote_timer -= 1

        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= 1

        can_jump = (self.on_ground or self.coyote_timer > 0) and not self.is_ducking
        if self.jump_buffer_timer > 0 and can_jump:
            self.velocity_y = -30
            self.on_ground = False
            self.coyote_timer = 0
            self.jump_buffer_timer = 0

        # Variable jump height: releasing jump key cuts upward velocity
        if not jump_pressed and self.velocity_y < -8:
            self.velocity_y *= 0.55

        if keys[pygame.K_s] and self.velocity_y < 0:
            self.velocity_y = -self.velocity_y

        if self.is_ducking:
            # Ducking: turn around in place and slide to a stop
            if keys[pygame.K_d]: self.direction = 1
            elif keys[pygame.K_a]: self.direction = 0
            if self.velocity_x > 0: self.velocity_x -= 1
            elif self.velocity_x < 0: self.velocity_x += 1
        elif keys[pygame.K_d]:
            if self.velocity_x<0: self.velocity_x*=-1;
            elif self.velocity_x<10: self.velocity_x += 1
            self.direction = 1
        elif keys[pygame.K_a]:
            if self.velocity_x>0: self.velocity_x*=-1;
            elif self.velocity_x>-10: self.velocity_x -= 1
            self.direction = 0
        elif self.velocity_x:
            if self.velocity_x>0: self.velocity_x -= 1
            else: self.velocity_x += 1

        # Reload Action
        if keys[pygame.K_r] and self.current_ammo < self.max_ammo and self.total_ammo > 0 and not self.is_reloading:
            self.start_reload()

        # Shooting Action
        if (pygame.mouse.get_pressed() == (1, 0, 0) or keys[pygame.K_SPACE]) and not self.is_reloading and self.current_ammo > 0:
            self.is_shooting = True
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
        self.previous_rect = self.base_player_rect.copy()
        was_airborne = not self.on_ground

        # Gravity runs every frame, including while jump/down is held.
        self.velocity_y = min(self.velocity_y + 1, 20)
        self.on_ground = False
        landing_speed = self.velocity_y

        self.base_player_rect.centerx += self.velocity_x 
        self.check_collision(True)
        self.base_player_rect.centery += self.velocity_y
        self.check_collision(False)

        if self.on_ground and was_airborne and landing_speed > 4:
            self.land_timer = 6

        self.vec_pos.update(self.base_player_rect.center)

    def shoot(self):
        """Starts a shot; the bullet leaves from the muzzle once the frame is chosen."""
        if self.shoot_cooldown == 0 and self.is_shooting:
            if getattr(G, "gun_shot_sounds", None) and len(G.gun_shot_sounds) > 0:
                import random
                random.choice(G.gun_shot_sounds).play()
            elif G.gun_shot_sound:
                G.gun_shot_sound.play()
            self.current_ammo -= 1
            self.shoot_cooldown = 10
            self.shot_timer = 9
            if G.game_level:
                G.game_level.shake_timer = max(G.game_level.shake_timer, 2)
                G.game_level.shake_amount = max(G.game_level.shake_amount, 1.5)
            return True
        return False

    def fire_from_muzzle(self):
        x, y = self.muzzle_position()
        Bullet(x, y, 0 if self.direction == 1 else 180)
        if G.muzzle_flash_imgs:
            self.flash = MuzzleFlash(self)

    def get_damage(self, amount):
        """Handles damage calculation and death sounds."""
        if self.is_caged:
            return
        if G.ui.current_health > 0:
            G.ui.current_health -= amount
            self.health -= amount
            if G.ui.current_health > 0:
                if G.hurt_sound: G.hurt_sound.play()
                self.hurt_timer = 18
                if G.game_level:
                    G.game_level.shake_timer = 10
                    G.game_level.shake_amount = 5
            else:
                if G.death_sound: G.death_sound.play()
                if G.game_level:
                    G.game_level.shake_timer = 14
                    G.game_level.shake_amount = 6
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
            if sprite is getattr(self, "cage", None):
                continue
            if sprite.rect.colliderect(self.base_player_rect):
                if horizontal:
                    if self.velocity_x > 0: self.base_player_rect.right = sprite.rect.left
                    elif self.velocity_x < 0: self.base_player_rect.left = sprite.rect.right
                else:
                    if self.velocity_y < 0: 
                        self.base_player_rect.top = sprite.rect.bottom
                        self.velocity_y = 0
                    elif self.velocity_y > 0: 
                        self.base_player_rect.bottom = sprite.rect.top
                        self.velocity_y = 0
                        self.on_ground = True

    def check_enemy_collisions(self):
        """Resolve contacts after both the player and enemies have moved.

        Crossing an enemy's top while descending is a stomp. Using the
        previous positions also catches fast falls through a small enemy.
        """
        if self.is_caged or self.health <= 0:
            return
        for enemy in list(G.enemy_group):
            enemy.update_player_grace(self)
            old_gap = enemy.previous_rect.top - self.previous_rect.bottom
            new_gap = enemy.rect.top - self.base_player_rect.bottom
            stomp = False
            if self.velocity_y > 0 and old_gap >= 0 and new_gap <= 0 and old_gap > new_gap:
                contact_time = old_gap / (old_gap - new_gap)
                player_left = self.previous_rect.left + (
                    self.base_player_rect.left - self.previous_rect.left
                ) * contact_time
                enemy_left = enemy.previous_rect.left + (
                    enemy.rect.left - enemy.previous_rect.left
                ) * contact_time
                stomp = (player_left < enemy_left + enemy.rect.width
                         and player_left + self.base_player_rect.width > enemy_left)
            if stomp:
                contact_top = enemy.rect.top
                enemy.on_stomp(self)
                self.base_player_rect.bottom = contact_top
                self.place_image()
                self.vec_pos.update(self.base_player_rect.center)
                self.velocity_y = -15
                self.on_ground = False
            elif self.base_player_rect.colliderect(enemy.rect) and enemy.on_player_contact(self):
                if self.invulnerable_timer > 0:
                    continue
                self.get_damage(self.health)
                break

    def check_level_objects(self):
        if G.game_level is None or self.health <= 0:
            return
        # Checkpoints
        for cp in getattr(G.game_level, "checkpoints", []):
            if not cp.activated and self.base_player_rect.colliderect(cp.rect):
                cp.activated = True
                G.game_level.player_spawn = (cp.rect.centerx, cp.rect.bottom)
                G.game_level.last_checkpoint = cp
                from settings import game_stats
                game_stats["score"] += 200
                if getattr(G, "create_floating_text", None):
                    G.create_floating_text("CHECKPOINT!", (cp.rect.centerx, cp.rect.top - 12), (100, 255, 150))

        # Goal
        goal = getattr(G.game_level, "goal", None)
        if goal and not getattr(G.game_level, "level_completed", False):
            if self.base_player_rect.colliderect(goal.rect):
                G.game_level.level_completed = True
                from settings import game_stats
                game_stats["score"] += 1000
                if getattr(G, "create_floating_text", None):
                    G.create_floating_text("STAGE CLEAR! +1000", (goal.rect.centerx, goal.rect.top - 16), (255, 215, 0))
                if G.game_level:
                    G.game_level.shake_timer = 12
                    G.game_level.shake_amount = 4

    def respawn(self, feet):
        """Stand up again at a checkpoint: full health, same ammo, a short grace period.

        The world keeps its state (defeated enemies stay defeated, collected
        coins stay collected), so dying costs only the way back.
        """
        self.base_player_rect = pygame.Rect((0, 0), self.stand_size)
        self.base_player_rect.midbottom = feet
        self.previous_rect = self.base_player_rect.copy()
        self.vec_pos.update(self.base_player_rect.center)
        self.velocity_x = self.velocity_y = 0
        self.on_ground = True
        self.is_ducking = False
        self.fell_in_pit = False
        self.death_timer = 0
        self.death_finished = False
        self.hurt_timer = self.shot_timer = self.land_timer = 0
        self.health = 100
        if G.ui is not None:
            G.ui.current_health = G.ui.maximum_health
        self.invulnerable_timer = 120
        self.animate(restart=True)

    def update_death(self):
        """Mario-style death: freeze in the death pose, pop up, then fall off screen."""
        self.death_timer += 1
        if self.fell_in_pit and self.death_timer == 1 and G.game_level:
            self.base_player_rect.centery = int(G.game_level.offset.y + HEIGHT + 10)
            self.place_image()
        if self.flash is not None:
            self.flash.kill()  # the world is frozen, so it would never finish
        if self.death_timer == 30:
            self.velocity_y = -14
        if self.death_timer > 30:
            self.velocity_y = min(self.velocity_y + 1, 30)
            self.base_player_rect.y += self.velocity_y
        if self.death_timer >= 110:
            self.death_finished = True
        self.animate()

    def update(self):
        if self.health <= 0:
            self.update_death()
            return

        # Pit death check
        if G.game_level is not None and self.base_player_rect.top > G.game_level.floor.get_height() + 16:
            self.fell_in_pit = True
            self.get_damage(self.health)
            return

        self.check_level_objects()
        for timer in ("shot_timer", "land_timer", "hurt_timer"):
            if getattr(self, timer) > 0:
                setattr(self, timer, getattr(self, timer) - 1)
        self.check_reload()
        self.player_input()
        self.move()
        if self.tunnel_requested and G.game_level is not None:
            G.game_level.try_enter_tunnel(self)
        if self.shoot_cooldown > 0: self.shoot_cooldown -= 1
        fired = self.shoot()
        self.animate(restart=fired and self.anim_name in ("shoot", "duck_shoot"))
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
            if (self.invulnerable_timer // 4) % 2:  # blink while enemies cannot hurt
                self.image = self.image.copy()
                self.image.set_alpha(90)
        if fired:
            self.fire_from_muzzle()
