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

    def on_stomp(self, player):
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


class TurtleEnemy(WalkingEnemy):
    """Walking turtle -> stationary shell -> kicked sliding shell.

    Stomping a sliding shell stops it. Stationary shells stay dormant until
    kicked; a kick is harmless to its kicker until they separate.
    """
    WALKING = "walking"
    SHELL = "shell"
    SLIDING = "sliding"

    def __init__(self, pos, direction=-1):
        super().__init__(pos, direction)
        self.state = self.WALKING
        self.image.fill((50, 170, 70))
        self.kicker = None

    @property
    def is_moving_shell(self):
        return self.state == self.SLIDING

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
        if self.state == self.WALKING:
            self.retreat()
        elif self.state == self.SLIDING:
            self.state = self.SHELL
            self.speed = 0
            self.kicker = None
        else:
            self.kick(player)

    def on_player_contact(self, player):
        if self.state == self.SHELL:
            self.kick(player)
            return False
        return self.kicker is not player
