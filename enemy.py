"""Walking platform enemies. Replace the placeholder Surface with artwork later."""
import pygame
import globals as G
from settings import TILESIZE


def resolve_enemy_collisions():
    """Turn touching enemies away from each other after all enemies move.

    Resolve each pair once, so sprite update order cannot reverse the same
    pair twice. Previous positions also detect enemies crossing in one frame.
    """
    if G.player is not None and getattr(G.player, "is_caged", False):
        return
    enemies = sorted(G.enemy_group, key=lambda enemy: enemy.previous_rect.centerx)
    for index, left in enumerate(enemies):
        for right in enemies[index + 1:]:
            if not left.alive() or not right.alive():
                continue
            if left.rect.bottom <= right.rect.top or right.rect.bottom <= left.rect.top:
                continue
            previous_gap = right.previous_rect.left - left.previous_rect.right
            current_gap = right.rect.left - left.rect.right
            crossed = previous_gap >= 0 and current_gap <= 0 and current_gap < previous_gap
            if not left.rect.colliderect(right.rect) and not crossed:
                continue

            if left.is_moving_shell or right.is_moving_shell:
                if left.is_moving_shell and right.is_moving_shell:
                    left.kill()
                    right.kill()
                elif left.is_moving_shell:
                    right.kill()
                else:
                    left.kill()
                continue

            if previous_gap >= 0:
                # Undo horizontal movement rather than pushing either into a wall.
                left.rect.x = left.previous_rect.x
                right.rect.x = right.previous_rect.x
            else:
                # Recover gracefully if overlapping spawn markers are added.
                overlap = left.rect.right - right.rect.left
                left.rect.x -= (overlap + 1) // 2
                right.rect.x += overlap // 2
            left.position.x = left.rect.x
            right.position.x = right.rect.x
            left.direction = -1
            right.direction = 1


class WalkingEnemy(pygame.sprite.Sprite):
    is_moving_shell = False
    # game ticks per animation frame
    FRAME_TICKS = {"walker/walk": 8, "turtle/walk": 10, "turtle/shell": 1, "turtle/spin": 3,
                   "goblin/walk": 9, "goblin/run": 5}

    def __init__(self, pos, direction=-1):
        super().__init__(G.enemy_group, G.all_sprites_group)
        self.image = pygame.Surface((TILESIZE, TILESIZE), pygame.SRCALPHA)
        self.image.fill((160, 85, 45))
        self.rect = self.image.get_rect(topleft=pos)
        self.previous_rect = self.rect.copy()
        self.position = pygame.Vector2(pos)
        self.direction = -1 if direction < 0 else 1
        self.speed = 2
        self.velocity_y = 0
        self.anim_ticks = 0
        self.animate()

    def current_animation(self):
        return "walker/walk"

    def animate(self):
        """Show the artwork frame for the current state, facing the walk direction.

        Frames match the rect size, so swapping them never moves the hitbox.
        Without artwork the flat placeholder colours stay.
        """
        name = self.current_animation()
        frames = (G.enemy_frames or {}).get(name)
        if not frames:
            return
        right, left = frames
        frames = right if self.direction > 0 else left
        self.image = frames[(self.anim_ticks // self.FRAME_TICKS[name]) % len(frames)]
        self.anim_ticks += 1

    def on_stomp(self, player):
        from settings import game_stats
        game_stats["score"] += 100
        if getattr(G, "enemy_death_sound", None):
            G.enemy_death_sound.play()
        if getattr(G, "create_floating_text", None):
            G.create_floating_text("+100", self.rect.center, (255, 220, 50))
        self.kill()

    def on_bullet_hit(self, bullet):
        from settings import game_stats
        game_stats["score"] += 100
        if getattr(G, "enemy_death_sound", None):
            G.enemy_death_sound.play()
        if getattr(G, "create_floating_text", None):
            G.create_floating_text("+100", self.rect.center, (255, 220, 50))
        self.kill()

    def on_player_contact(self, player):
        """Return whether a non-stomp contact should kill the player."""
        return True

    def update_player_grace(self, player):
        pass

    def update(self):
        if G.player is not None and getattr(G.player, "is_caged", False):
            return
        self.previous_rect = self.rect.copy()
        self.position.x += self.direction * self.speed
        self.rect.x = round(self.position.x)
        walls = pygame.sprite.spritecollide(self, G.obstacles_group, False)
        if walls:
            if self.direction > 0:
                self.rect.right = min(wall.rect.left for wall in walls)
            else:
                self.rect.left = max(wall.rect.right for wall in walls)
            self.position.x = self.rect.x
            self.direction *= -1

        self.velocity_y = min(self.velocity_y + 1, 12)
        self.position.y += self.velocity_y
        self.rect.y = round(self.position.y)
        floors = pygame.sprite.spritecollide(self, G.obstacles_group, False)
        if floors:
            self.rect.bottom = min(tile.rect.top for tile in floors)
            self.position.y = self.rect.y
            self.velocity_y = 0

        # Enemies walk off ledges, as in SMB, and disappear below the map.
        if G.game_level is not None and self.rect.top > G.game_level.floor.get_height():
            self.kill()
        self.animate()


class TurtleEnemy(WalkingEnemy):
    """Walking turtle -> stationary shell -> kicked sliding shell.

    Stomping a sliding shell stops it. Stationary shells stay dormant until
    kicked; a kick is harmless to its kicker until they separate.
    """
    WALKING = "walking"
    SHELL = "shell"
    SLIDING = "sliding"

    def __init__(self, pos, direction=-1):
        self.state = self.WALKING  # set first: the base __init__ picks the first frame
        super().__init__(pos, direction)
        if not (G.enemy_frames or {}).get("turtle/walk"):
            self.image.fill((50, 170, 70))  # artwork frames are shared; only tint the placeholder
        self.kicker = None

    @property
    def is_moving_shell(self):
        return self.state == self.SLIDING

    def current_animation(self):
        return {self.WALKING: "turtle/walk", self.SHELL: "turtle/shell",
                self.SLIDING: "turtle/spin"}[self.state]

    def retreat(self):
        bottom = self.rect.midbottom
        self.state = self.SHELL
        self.speed = 0
        self.image = pygame.Surface((TILESIZE, TILESIZE // 2), pygame.SRCALPHA)
        self.image.fill((25, 100, 40))
        self.rect = self.image.get_rect(midbottom=bottom)
        self.position.update(self.rect.topleft)
        self.kicker = None

    def kick(self, player):
        self.state = self.SLIDING
        self.speed = 12
        if player.base_player_rect.centerx == self.rect.centerx:
            self.direction = 1 if player.direction == 1 else -1
        else:
            self.direction = 1 if player.base_player_rect.centerx < self.rect.centerx else -1
        self.kicker = player

    def update_player_grace(self, player):
        if self.kicker is player and not self.rect.colliderect(player.base_player_rect):
            self.kicker = None

    def on_stomp(self, player):
        from settings import game_stats
        if getattr(G, "enemy_death_sound", None):
            G.enemy_death_sound.play()
        if self.state == self.WALKING:
            self.retreat()
            game_stats["score"] += 50
            if getattr(G, "create_floating_text", None):
                G.create_floating_text("+50", self.rect.center, (255, 220, 50))
        elif self.state == self.SLIDING:
            self.state = self.SHELL
            self.speed = 0
            self.kicker = None
            game_stats["score"] += 50
            if getattr(G, "create_floating_text", None):
                G.create_floating_text("+50", self.rect.center, (255, 220, 50))
        else:
            self.kick(player)
            game_stats["score"] += 50
            if getattr(G, "create_floating_text", None):
                G.create_floating_text("+50", self.rect.center, (255, 220, 50))

    def on_bullet_hit(self, bullet):
        from settings import game_stats
        if getattr(G, "enemy_death_sound", None):
            G.enemy_death_sound.play()
        if self.state == self.WALKING:
            self.retreat()
            game_stats["score"] += 50
            if getattr(G, "create_floating_text", None):
                G.create_floating_text("+50", self.rect.center, (255, 220, 50))
        elif self.state == self.SHELL:
            self.state = self.SLIDING
            self.speed = 12
            self.direction = 1 if bullet.x_vel > 0 else -1
            self.kicker = None
            game_stats["score"] += 50
            if getattr(G, "create_floating_text", None):
                G.create_floating_text("+50", self.rect.center, (255, 220, 50))
        elif self.state == self.SLIDING:
            self.kill()
            game_stats["score"] += 100
            if getattr(G, "create_floating_text", None):
                G.create_floating_text("+100", self.rect.center, (255, 220, 50))

    def on_player_contact(self, player):
        if self.state == self.SHELL:
            self.kick(player)
            return False
        return self.kicker is not player


class GoblinEnemy(WalkingEnemy):
    """Long-nosed goblin with long yellow hair: patrols slowly and runs at a
    player who comes near on about the same level.

    It gives up when the player gets far away. A stomp kills it; it takes
    two bullets, and the first one makes it run at the shooter.
    """
    WALK_SPEED = 1.5
    RUN_SPEED = 4.5
    SIGHT = 6 * TILESIZE        # how far ahead or behind it notices the player
    GIVE_UP = 10 * TILESIZE
    HEIGHT_RANGE = 2 * TILESIZE  # feet within this height difference count as "same level"
    HEALTH = 2
    SCORE = 150
    SIZE = (TILESIZE, 44)       # used when the artwork is missing
    HIT_FLASH = 8

    def __init__(self, pos, direction=-1):
        self.charging = False   # set first: the base __init__ picks the first frame
        self.hit_flash = 0
        super().__init__(pos, direction)
        frames = (G.enemy_frames or {}).get("goblin/walk")
        size = frames[0][0].get_size() if frames else self.SIZE
        if not frames:
            self.image = pygame.Surface(size, pygame.SRCALPHA)
            self.image.fill((102, 146, 60))
        # stand on the floor of the spawn tile; the sprite is taller than a tile
        self.rect = pygame.Rect((0, 0), size)
        self.rect.midbottom = (pos[0] + TILESIZE // 2, pos[1] + TILESIZE)
        self.previous_rect = self.rect.copy()
        self.position = pygame.Vector2(self.rect.topleft)
        self.speed = self.WALK_SPEED
        self.health = self.HEALTH

    def current_animation(self):
        return "goblin/run" if self.charging else "goblin/walk"

    def animate(self):
        super().animate()
        if self.hit_flash > 0:
            self.hit_flash -= 1
            self.image = self.image.copy()
            self.image.fill((90, 90, 90), special_flags=pygame.BLEND_RGB_ADD)

    def charge(self, toward_x):
        if not self.charging and getattr(G, "create_floating_text", None):
            G.create_floating_text("!", (self.rect.centerx, self.rect.top - 6), (255, 90, 60), duration=30)
        self.charging = True
        self.speed = self.RUN_SPEED
        self.face(toward_x)

    def calm_down(self):
        self.charging = False
        self.speed = self.WALK_SPEED

    def face(self, x):
        if abs(x - self.rect.centerx) > 4:  # no flipping back and forth right under the player
            self.direction = 1 if x > self.rect.centerx else -1

    def look_for_player(self):
        player = G.player
        if player is None or player.is_caged or player.health <= 0:
            self.calm_down()
            return
        dx = abs(player.base_player_rect.centerx - self.rect.centerx)
        dy = abs(player.base_player_rect.bottom - self.rect.bottom)
        if self.charging:
            if dx > self.GIVE_UP or dy > self.HEIGHT_RANGE * 2:
                self.calm_down()
            else:
                self.face(player.base_player_rect.centerx)
        elif dx < self.SIGHT and dy < self.HEIGHT_RANGE:
            self.charge(player.base_player_rect.centerx)

    def update(self):
        if G.player is not None and getattr(G.player, "is_caged", False):
            return
        self.look_for_player()
        super().update()

    def die(self):
        from settings import game_stats
        game_stats["score"] += self.SCORE
        if getattr(G, "enemy_death_sound", None):
            G.enemy_death_sound.play()
        if getattr(G, "create_floating_text", None):
            G.create_floating_text(f"+{self.SCORE}", self.rect.center, (255, 220, 50))
        self.kill()

    def on_stomp(self, player):
        self.die()

    def on_bullet_hit(self, bullet):
        self.health -= 1
        if self.health <= 0:
            self.die()
            return
        self.hit_flash = self.HIT_FLASH
        if getattr(G, "hurt_sound", None):
            G.hurt_sound.play()
        # knocked back a little, then it comes for the shooter
        self.position.x += 6 if bullet.x_vel > 0 else -6
        self.rect.x = round(self.position.x)
        self.charge(self.rect.centerx - bullet.x_vel * 100)
