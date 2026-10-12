"""Load the test map, build platform collisions, and draw the scrolling world."""
import pygame
from assets import safe_load_image
from item import Item
from enemy import WalkingEnemy, TurtleEnemy
from settings import WIDTH, HEIGHT, TILESIZE
import globals as G


class Tile(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__(G.obstacles_group)
        self.rect = pygame.Rect(pos, (TILESIZE, TILESIZE))


class GameLevel:
    def __init__(self, level_num):
        self.offset = pygame.Vector2()
        self.floor = safe_load_image(f"levels/{level_num}.png")
        self.health_spawn_pos = []
        self.enemy_spawn_pos = []
        self.turtle_spawn_pos = []
        self.player_spawn = (0, 0)
        self.prepare(level_num)

    def prepare(self, level_num):
        """Magenta is solid, green is health, cyan is the player spawn.

        (255, 1, 0) spawns a walking enemy, (255, 2, 0) a turtle.
        Exit markers remain inactive.
        """
        mask = pygame.image.load(f"levels/{level_num}_mask.png")
        G.obstacles_group.empty()
        for row in range(mask.get_height()):
            for col in range(mask.get_width()):
                color = tuple(mask.get_at((col, row)))[:3]
                pos = (col * TILESIZE, row * TILESIZE)
                if color[0] == 255 and color[2] == 255 and color != (255, 255, 255):
                    Tile(pos)
                elif color == (0, 255, 0):
                    self.health_spawn_pos.append(pos)
                elif color == (0, 255, 255):
                    self.player_spawn = pos
                elif color == (255, 1, 0):
                    self.enemy_spawn_pos.append(pos)
                elif color == (255, 2, 0):
                    self.turtle_spawn_pos.append(pos)
        for pos in self.health_spawn_pos:
            Item(pos, "health potion")
        for pos in self.enemy_spawn_pos:
            WalkingEnemy(pos)
        for pos in self.turtle_spawn_pos:
            TurtleEnemy(pos)

    def update_camera(self):
        target = pygame.Vector2(G.player.rect.center) - (WIDTH // 2, HEIGHT // 2)
        self.offset += (target - self.offset) * 0.05

    def draw(self):
        G.screen.fill((0, 0, 0))
        G.screen.blit(self.floor, -self.offset)
        for sprite in G.all_sprites_group:
            G.screen.blit(sprite.image, pygame.Vector2(sprite.rect.topleft) - self.offset)
