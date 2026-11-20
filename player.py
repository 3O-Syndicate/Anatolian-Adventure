"""
player.py

Module Description:
    Implements the Player class which handles user input, movement mechanics,
    collision detection, the weapon system (shooting, reloading, ammo management),
    the kimiz power-ups (growing big, getting the shotgun) and the hero's animations.
"""
import math
import random

import pygame
import globals as G
import assets
from settings import *
from bullet import Bullet
from acid import AcidPuddle
from effects import Sparkle, Ring, burst, brick_debris, nazar_crack


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


BIG_SCALE = 1.5     # a big hero is drawn and collides at 1.5x
BRICK_TILE = 3      # terrain ID a big hero can break with his head
GROW_TICKS = 66     # the grow effect; the hero hangs still meanwhile
SHRINK_TICKS = 48   # flickering back to small after a hit


def has_power(name):
    """Kimiz powers the player carries: "big" until an enemy hits, "gun" for good."""
    return name in game_stats.get("powers", ())


def set_power(name, on):
    powers = game_stats.setdefault("powers", [])
    if on and name not in powers:
        powers.append(name)
    elif not on and name in powers:
        powers.remove(name)


_frame_cache = {}


def hero_frames(armed, scale):
    """(right-facing, left-facing) frame dicts for the gun/no-gun set at a size."""
    key = (armed, scale)
    if key not in _frame_cache:
        frames = G.hero_anims
        if not armed and G.hero_anims_unarmed:
            frames = G.hero_anims_unarmed
        if scale != 1:
            frames = {name: [pygame.transform.scale_by(f, scale) for f in fs]
                      for name, fs in frames.items()}
        left = {name: [pygame.transform.flip(f, True, False) for f in fs]
                for name, fs in frames.items()}
        _frame_cache[key] = (frames, left)
    return _frame_cache[key]


class Player(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()

        # Animations: frames face right; left-facing copies are flipped once here.
        if G.hero_anims is None:
            G.hero_meta, G.hero_anims = assets.placeholder_hero_animations()
        self.anim_meta = G.hero_meta
        self.frame_width = self.anim_meta["frame_size"][0]
        self.anchor = self.anim_meta["anchor"]
        # size: the hitbox scale (1 or BIG_SCALE); scale: the drawn one, which
        # differs only while the grow/shrink effect plays
        self.size = self.scale = BIG_SCALE if has_power("big") else 1.0
        self.squash = (1.0, 1.0)  # extra (x, y) stretch while growing
        self.grow_timer = 0
        self.shrink_timer = 0
        self.victory_ticks = 0  # counts up after the goal flag
        self.anim_name = "idle"
        self.frame_index = 0
        self.frame_time = 0.0

        # Physics Components (the hitbox is fixed; frames are drawn around it)
        self.vec_pos = pygame.math.Vector2(pos)
        self.base_player_rect = pygame.Rect((0, 0), self.stand_size)
        self.base_player_rect.midbottom = (pos[0], pos[1] + self.anim_meta["hitbox"]["stand"][1] // 2)
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
        self.entered_tunnel = False
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
        self.armor = 0             # nazar beads: each one stops one enemy hit
        self.acid = 0              # acid flasks, poured with Q
        self.acid_was_pressed = False
        self.is_caged = False
        self.cage = None

        self.animate()

    # --- POWERS ---
    @property
    def has_gun(self):
        return has_power("gun")

    @property
    def is_big(self):
        return self.size != 1

    def sized(self, name):
        w, h = self.anim_meta["hitbox"][name]
        return (round(w * self.size), round(h * self.size))

    @property
    def stand_size(self):
        return self.sized("stand")

    @property
    def duck_size(self):
        return self.sized("duck")

    def resize(self, size):
        """Change the hitbox scale, feet in place, then step out of any wall it now overlaps."""
        self.size = size
        rect = pygame.Rect((0, 0), self.duck_size if self.is_ducking else self.stand_size)
        rect.midbottom = self.base_player_rect.midbottom
        solids = [tile.rect for tile in G.obstacles_group if tile is not getattr(self, "cage", None)]
        if any(rect.colliderect(t) for t in solids):
            for dy in range(1, rect.height):
                for candidate in (rect.move(0, dy), rect.move(0, -dy)):
                    if not any(candidate.colliderect(t) for t in solids):
                        rect = candidate
                        break
                else:
                    continue
                break
        self.base_player_rect = rect
        self.previous_rect = rect.copy()
        self.vec_pos.update(rect.center)

    def drink_kimiz(self, power, where):
        """A kimiz bowl: "big" makes the hero grow, "gun" gives him the shotgun."""
        game_stats["score"] += 1000
        text, colour = "Kımız: +1000", (255, 246, 220)
        if power == "big" and not self.is_big:
            set_power("big", True)
            self.grow_timer = GROW_TICKS
            self.velocity_x = self.velocity_y = 0
            self.invulnerable_timer = max(self.invulnerable_timer, GROW_TICKS + 60)
            text, colour = "Kımız içtin, büyüdün!", (255, 200, 225)
            burst(self.base_player_rect.center, 14, 4, hearts=0.4)
        elif power == "gun" and not self.has_gun:
            set_power("gun", True)
            self.current_ammo = self.max_ammo
            text, colour = "Tüfeğin geri geldi!  Boşluk: ateş", (255, 235, 140)
            burst(self.base_player_rect.center, 16, 5, hearts=0)
            Ring(self.base_player_rect.center, colour=(255, 230, 140))
        if G.health_potion_sound:
            G.health_potion_sound.play()
        if getattr(G, "create_floating_text", None):
            G.create_floating_text(text, where, colour, duration=150)

    def update_grow(self):
        """Grow effect: a few happy hops between sizes, then a wobbly settle at big."""
        self.grow_timer -= 1
        t = 1 - self.grow_timer / GROW_TICKS
        if t < 0.55:
            steps = (1.0, 1.18, 1.0, 1.3, 1.12, 1.42, 1.25, BIG_SCALE)
            self.scale = steps[min(len(steps) - 1, int(t / 0.55 * len(steps)))]
            self.squash = (1.0, 1.0)
        else:
            k = (t - 0.55) / 0.45
            wobble = math.sin(k * math.pi * 3) * (1 - k) * 0.14
            self.scale = BIG_SCALE
            self.squash = (1 + wobble, 1 - wobble)
        center = self.base_player_rect.midbottom
        if self.grow_timer % 6 == 0:
            Sparkle((center[0] + random.randint(-30, 30), center[1] - random.randint(10, 80)),
                    (random.uniform(-1, 1), random.uniform(-2.5, -1)), 34,
                    heart=random.random() < 0.5)
        if self.grow_timer == int(GROW_TICKS * 0.45):
            self.resize(BIG_SCALE)
            Ring((self.base_player_rect.centerx, self.base_player_rect.centery))
            burst(self.base_player_rect.center, 20, 6)
            if G.game_level:
                G.game_level.shake_timer = 8
                G.game_level.shake_amount = 3
        if self.grow_timer == 0:
            self.scale, self.squash = BIG_SCALE, (1.0, 1.0)
        self.animate()

    def update_victory(self):
        """After the goal flag: land, then raise the kimiz bowl among sparkles."""
        self.victory_ticks += 1
        self.velocity_x = 0
        if not self.on_ground:
            self.move()
        for timer in ("hurt_timer", "land_timer", "shot_timer", "shrink_timer"):
            setattr(self, timer, 0)
        self.invulnerable_timer = 0
        self.animate()
        if self.on_ground and self.victory_ticks % 7 == 0:
            sx, sy = getattr(self, "drawn_scale", (1.0, 1.0))
            hand_x = 13 if self.direction == 1 else self.frame_width - 13
            bowl = (self.rect.left + hand_x * sx, self.rect.top + 4 * sy)
            Sparkle((bowl[0] + random.randint(-6, 6), bowl[1]),
                    (random.uniform(-1.2, 1.2), random.uniform(-2.5, -1)), random.randint(30, 44),
                    heart=random.random() < 0.4)

    def shrink(self, enemy):
        """A hit while big costs the size instead of the life."""
        set_power("big", False)
        self.resize(1.0)
        self.shrink_timer = SHRINK_TICKS
        self.invulnerable_timer = 120
        self.hurt_timer = 18
        away = 1 if self.base_player_rect.centerx >= enemy.rect.centerx else -1
        self.velocity_x = 8 * away
        self.velocity_y = -8
        self.on_ground = False
        burst(self.base_player_rect.center, 10, 3, hearts=0)
        if G.hurt_sound:
            G.hurt_sound.play()
        if G.game_level:
            G.game_level.shake_timer = 10
            G.game_level.shake_amount = 4
        if getattr(G, "create_floating_text", None):
            G.create_floating_text("Küçüldün!", (self.base_player_rect.centerx, self.rect.top - 8),
                                   (255, 200, 225), duration=90)

    # --- ANIMATION ---
    def current_animation(self):
        """Pick the animation for the player's state, most important first."""
        if self.health <= 0:
            return "death"
        if self.victory_ticks and self.on_ground:
            return "victory"
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

        self.image = self.frame_image(name, self.frame_index)
        self.place_image()

        # Footstep audio synced with run animation (frames 0 and 3 in the 6-frame cycle)
        if name == "run" and self.on_ground and not self.is_ducking:
            if self.frame_index != prev_frame and self.frame_index in (0, 3):
                self.play_footstep()

    def frame_image(self, name, index):
        if self.shrink_timer > 0:  # flicker between the big and small hero
            scale = BIG_SCALE if (self.shrink_timer // 4) % 2 else 1.0
        else:
            scale = self.scale
        cached = scale in (1.0, BIG_SCALE)
        right, left = hero_frames(self.has_gun, scale if cached else 1.0)
        frames = right if self.direction == 1 else left
        if name not in frames:  # unarmed: no shoot or reload frames
            name = "duck" if name == "duck_shoot" else "idle"
            index = 0
        image = frames[name][min(index, len(frames[name]) - 1)]
        sx, sy = self.squash
        if not cached or (sx, sy) != (1.0, 1.0):
            factor = 1.0 if cached else scale
            w, h = image.get_size()
            image = pygame.transform.scale(image, (max(1, round(w * factor * sx)),
                                                   max(1, round(h * factor * sy))))
        self.drawn_scale = image.get_width() / self.frame_width, image.get_height() / self.frame_width
        if self.armor > 0 and name != "death":
            image = image.copy()
            sx, sy = self.drawn_scale
            x, y = self.pin_offset(name)
            if self.direction == 0:
                x = self.frame_width - x
            centre = (round(x * sx), round(y * sy))
            r = max(2, round(2.6 * sx))
            pygame.draw.circle(image, (40, 24, 28), centre, r + 1)   # the game's outline colour
            pygame.draw.circle(image, (36, 88, 146), centre, r)
            pygame.draw.circle(image, (248, 248, 250), centre, max(1, r - 1))
            pygame.draw.circle(image, (20, 20, 40), centre, max(1, r - 2))
        return image

    # where the nazar bead is pinned on the tank top, in frame pixels facing right
    PIN = (37, 31)
    PIN_DROP = {"duck": 11, "duck_shoot": 11, "land": 2}

    def pin_offset(self, name):
        return self.PIN[0], self.PIN[1] + self.PIN_DROP.get(name, 0)

    def pin_position(self):
        """World position of the pinned nazar bead in the frame being shown."""
        sx, sy = getattr(self, "drawn_scale", (1.0, 1.0))
        x, y = self.pin_offset(self.anim_name)
        if self.direction == 0:
            x = self.frame_width - x
        return (self.rect.left + x * sx, self.rect.top + y * sy)

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
        sx, sy = getattr(self, "drawn_scale", (1.0, 1.0))
        anchor_x = self.anchor[0] if self.direction == 1 else self.frame_width - self.anchor[0]
        self.rect = self.image.get_rect(topleft=(self.base_player_rect.centerx - round(anchor_x * sx),
                                                 self.base_player_rect.bottom - round(self.anchor[1] * sy)))

    def muzzle_position(self):
        """World position of the gun's muzzle in the frame being shown."""
        mx, my = self.anim_meta["anims"][self.anim_name]["muzzle"][self.frame_index]
        if self.direction == 0:
            mx = self.frame_width - mx
        sx, sy = getattr(self, "drawn_scale", (1.0, 1.0))
        return (self.rect.left + mx * sx, self.rect.top + my * sy)

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

    @property
    def run_speed(self):
        return 12 if "speed" in game_stats.get("shop_upgrades", ()) else 10

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
            self.velocity_y = -22 if "jump" in game_stats.get("shop_upgrades", ()) else -20
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
            elif self.velocity_x < self.run_speed: self.velocity_x += 1
            self.direction = 1
        elif keys[pygame.K_a]:
            if self.velocity_x>0: self.velocity_x*=-1;
            elif self.velocity_x > -self.run_speed: self.velocity_x -= 1
            self.direction = 0
        elif self.velocity_x:
            if self.velocity_x>0: self.velocity_x -= 1
            else: self.velocity_x += 1

        # Pour acid on the floor in front (Q)
        acid_pressed = keys[pygame.K_q]
        if acid_pressed and not self.acid_was_pressed:
            self.pour_acid()
        self.acid_was_pressed = acid_pressed

        if not self.has_gun:
            self.is_shooting = False
            return

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

    def pour_acid(self):
        """Q: a puddle on the floor one tile ahead dissolves enemies for a few seconds."""
        if self.acid <= 0 or not self.on_ground:
            return
        self.acid -= 1
        front = self.base_player_rect.centerx + (TILESIZE if self.direction == 1 else -TILESIZE)
        AcidPuddle((front, self.base_player_rect.bottom))

    def take_item(self, item, where):
        """Chest contents: shotgun ammo, a nazar bead against one hit, or acid flasks."""
        if item == "shotgun":
            self.total_ammo += 30
            text = "Tüfek: +30 mermi" if self.has_gun else "+30 mermi (tüfeği bulunca)"
        elif item == "armor":
            self.armor += 1
            text = "Nazar boncuğu: bir darbeyi durdurur"
        elif item == "acid":
            self.acid += 3
            text = "Asit x3: Q ile yere dök"
        else:
            return
        if G.health_potion_sound:
            G.health_potion_sound.play()
        if getattr(G, "create_floating_text", None):
            G.create_floating_text(text, where, (255, 235, 140), duration=150)

    def lose_armor(self, enemy):
        """A nazar bead takes the hit and cracks: knocked back, then a short grace period."""
        self.armor -= 1
        nazar_crack(self.pin_position())
        self.invulnerable_timer = 90
        self.hurt_timer = 18
        away = 1 if self.base_player_rect.centerx >= enemy.rect.centerx else -1
        self.velocity_x = 8 * away
        self.velocity_y = -8
        self.on_ground = False
        if G.hurt_sound:
            G.hurt_sound.play()
        if G.game_level:
            G.game_level.shake_timer = 10
            G.game_level.shake_amount = 4
        if getattr(G, "create_floating_text", None):
            G.create_floating_text("Çat! Nazar boncuğu seni korudu", (self.base_player_rect.centerx, self.rect.top - 8),
                                   (160, 210, 255), duration=110)

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
        rising = self.velocity_y < 0
        probe = self.base_player_rect.copy()  # before any push-back
        bumped = []  # tiles hit with the head
        for sprite in G.obstacles_group:
            if sprite is getattr(self, "cage", None):
                continue
            if sprite.rect.colliderect(self.base_player_rect):
                if horizontal:
                    if self.velocity_x > 0: self.base_player_rect.right = sprite.rect.left
                    elif self.velocity_x < 0: self.base_player_rect.left = sprite.rect.right
                else:
                    if rising:
                        self.base_player_rect.top = sprite.rect.bottom
                        self.velocity_y = 0
                        bumped.append(sprite)
                    elif self.velocity_y > 0: 
                        self.base_player_rect.bottom = sprite.rect.top
                        self.velocity_y = 0
                        self.on_ground = True
        if bumped and self.is_big and G.game_level is not None:
            # a big hero breaks the brick right above his head
            # every tile across the head, not only the first one that pushed back
            bumped = [t for t in G.obstacles_group if t is not getattr(self, "cage", None)
                      and t.rect.colliderect(probe) and t.rect.bottom == self.base_player_rect.top]
            head = self.base_player_rect.centerx
            tile = min(bumped, key=lambda t: abs(t.rect.centerx - head))
            if tile.tile_type == BRICK_TILE:
                G.game_level.break_brick(tile)

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
                if self.armor > 0:
                    self.lose_armor(enemy)
                    continue
                if self.is_big:
                    self.shrink(enemy)
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
                    G.create_floating_text("Kontrol noktası!", (cp.rect.centerx, cp.rect.top - 12), (100, 255, 150))

        # Chests open once; wallets are picked up
        for chest in getattr(G.game_level, "chests", []):
            if not chest.activated and self.base_player_rect.colliderect(chest.rect):
                chest.activated = True
                self.take_item(chest.item, (chest.rect.centerx, chest.rect.top - 12))
        for wallet in getattr(G.game_level, "wallets", []):
            if wallet.alive() and self.base_player_rect.colliderect(wallet.rect):
                wallet.kill()
                from settings import game_stats
                game_stats["coins"] += 5
                game_stats["score"] += 50
                if G.coin_sound:
                    G.coin_sound.play()
                if getattr(G, "create_floating_text", None):
                    G.create_floating_text("Cüzdan: +5 altın", (wallet.rect.centerx, wallet.rect.top - 12),
                                           (255, 223, 91), duration=90)

    def reached_goal(self):
        goal = getattr(G.game_level, "goal", None)
        if goal and not getattr(G.game_level, "level_completed", False):
            if self.base_player_rect.colliderect(goal.rect):
                G.game_level.level_completed = True
                self.victory_ticks = 1
                self.is_ducking = False
                from settings import game_stats
                game_stats["score"] += 1000
                if getattr(G, "create_floating_text", None):
                    G.create_floating_text("Bölüm sonu! +1000", (goal.rect.centerx, goal.rect.top - 16), (255, 215, 0))
                return True
        return False

    def respawn(self, feet):
        """Stand up again at a checkpoint: full health, same ammo, small, a short grace period.

        The world keeps its state (defeated enemies stay defeated, collected
        coins stay collected), so dying costs only the way back.
        """
        set_power("big", False)
        self.size = self.scale = 1.0
        self.squash = (1.0, 1.0)
        self.grow_timer = self.shrink_timer = 0
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
        self.entered_tunnel = False
        if self.health <= 0:
            self.update_death()
            return

        # Pit death check
        if G.game_level is not None and self.base_player_rect.top > G.game_level.floor.get_height() + 16:
            self.fell_in_pit = True
            self.get_damage(self.health)
            return

        if self.grow_timer > 0:
            self.update_grow()
            return
        if self.shrink_timer > 0:
            self.shrink_timer -= 1

        self.check_level_objects()
        if self.reached_goal():
            return
        for timer in ("shot_timer", "land_timer", "hurt_timer"):
            if getattr(self, timer) > 0:
                setattr(self, timer, getattr(self, timer) - 1)
        self.check_reload()
        self.player_input()
        self.move()
        if self.reached_goal():
            self.place_image()
            return
        if self.tunnel_requested and G.game_level is not None:
            self.entered_tunnel = G.game_level.try_enter_tunnel(self)
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
