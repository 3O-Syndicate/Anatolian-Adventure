"""Load the test map, build platform collisions, and draw the scrolling world."""
import pygame
from item import Item
from enemy import WalkingEnemy, TurtleEnemy
from settings import WIDTH, HEIGHT, TILESIZE, MAP_BACKGROUND
from terrain import terrain_type, TileTextures
import globals as G


class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, tile_type=0):
        super().__init__(G.obstacles_group)
        self.rect = pygame.Rect(pos, (TILESIZE, TILESIZE))
        self.tile_type = tile_type


class GameLevel:
    def __init__(self, level_num):
        self.offset = pygame.Vector2()
        self.shake_timer = 0
        self.shake_amount = 0
        self.shake_offset = pygame.Vector2()
        self.health_spawn_pos = []
        self.enemy_spawn_pos = []
        self.turtle_spawn_pos = []
        self.player_spawn = (0, 0)
        self.prepare(level_num)

    def prepare(self, level_num):
        """Magenta's green channel selects solid terrain (0 is invisible).

        Green is health, cyan is the player spawn, white/black are empty.
        (255, 1, 0) spawns a walking enemy, (255, 2, 0) a turtle.
        Exit markers remain inactive.
        """
        mask = pygame.image.load(f"levels/{level_num}_mask.png")
        self.floor = pygame.Surface(
            (mask.get_width() * TILESIZE, mask.get_height() * TILESIZE),
            pygame.SRCALPHA,
        )
        textures = TileTextures()
        G.obstacles_group.empty()
        for row in range(mask.get_height()):
            for col in range(mask.get_width()):
                color = tuple(mask.get_at((col, row)))[:3]
                pos = (col * TILESIZE, row * TILESIZE)
                tile_type = terrain_type(color)
                if tile_type is not None:
                    Tile(pos, tile_type)
                    texture = textures.get(tile_type)
                    if texture is not None:
                        self.floor.blit(texture, pos)
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
        if self.shake_timer > 0:
            import random
            self.shake_timer -= 1
            self.shake_offset = pygame.Vector2(
                random.uniform(-self.shake_amount, self.shake_amount),
                random.uniform(-self.shake_amount, self.shake_amount),
            )
        else:
            self.shake_offset = pygame.Vector2()

    def draw(self):
        draw_offset = self.offset + self.shake_offset
        G.screen.fill(MAP_BACKGROUND)
        G.screen.blit(self.floor, -draw_offset)
        for sprite in G.all_sprites_group:
            G.screen.blit(sprite.image, pygame.Vector2(sprite.rect.topleft) - draw_offset)
