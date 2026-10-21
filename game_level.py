"""Load a level, build platform collisions, and draw the scrolling world."""
import os
import pygame
from item import Item
from enemy import WalkingEnemy, TurtleEnemy
from settings import WIDTH, HEIGHT, TILESIZE, import_folder
from terrain import TileTextures
import level_format
import globals as G


class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, tile_type=0):
        super().__init__(G.obstacles_group)
        self.rect = pygame.Rect(pos, (TILESIZE, TILESIZE))
        self.tile_type = tile_type


class LevelObject(pygame.sprite.Sprite):
    """Checkpoint or goal artwork standing in its tile. No behaviour yet."""
    FRAME_TICKS = 20

    def __init__(self, frames, cell):
        super().__init__(G.all_sprites_group)
        self.frames = frames
        self.ticks = 0
        self.image = frames[0]
        x, y = cell
        self.rect = self.image.get_rect(bottomleft=(x * TILESIZE, (y + 1) * TILESIZE))

    def update(self):
        self.ticks += 1
        self.image = self.frames[(self.ticks // self.FRAME_TICKS) % len(self.frames)]


class GameLevel:
    def __init__(self, level_num):
        self.offset = pygame.Vector2()
        self.health_spawn_pos = []
        self.enemy_spawn_pos = []
        self.turtle_spawn_pos = []
        self.player_spawn = (0, 0)
        self.tunnels = {}
        self.decor_images = {}
        self.prepare(level_num)

    def prepare(self, level_num):
        """Build levels/<n>.json, or the old levels/<n>_mask.png when there is no JSON.

        See level_format.py for the file format. Terrain and both decor layers
        are rendered once here, then blitted while scrolling.
        """
        level = level_format.load_for_game(level_num)
        size = (level["width"] * TILESIZE, level["height"] * TILESIZE)
        self.background = tuple(level["background"])
        self.floor = pygame.Surface(size, pygame.SRCALPHA)
        textures = TileTextures()
        G.obstacles_group.empty()
        for row, line in enumerate(level["terrain"]):
            for col, char in enumerate(line):
                tile_type = level_format.char_tile(char)
                if tile_type is None:
                    continue
                pos = (col * TILESIZE, row * TILESIZE)
                Tile(pos, tile_type)
                texture = textures.get(tile_type)
                if texture is not None:
                    self.floor.blit(texture, pos)
        self.decor_back = self.render_decor(level, "back", size)
        self.decor_front = self.render_decor(level, "front", size)
        self.spawn_entities(level, level_num)

    def spawn_entities(self, level, level_num):
        objects = {name: import_folder(f"objects/{name}") if os.path.isdir(f"objects/{name}")
                   else [] for name in ("checkpoint", "goal")}
        tunnel_cells = {}
        for entity in level["entities"]:
            kind = entity["type"]
            x, y = entity["x"], entity["y"]
            pos = (x * TILESIZE, y * TILESIZE)
            centre = (pos[0] + TILESIZE // 2, pos[1] + TILESIZE // 2)
            if kind == "player":
                # the player's feet stand in this tile
                self.player_spawn = (centre[0], pos[1])
            elif kind == "health":
                self.health_spawn_pos.append(pos)
                Item(centre, "health potion")
            elif kind == "coin":
                Item(centre, "coin")
            elif kind == "walker":
                self.enemy_spawn_pos.append(pos)
                WalkingEnemy(pos, entity.get("dir", -1))
            elif kind == "turtle":
                self.turtle_spawn_pos.append(pos)
                TurtleEnemy(pos, entity.get("dir", -1))
            elif kind in ("checkpoint", "goal"):
                frames = objects[kind] or [self.placeholder((TILESIZE, 2 * TILESIZE))]
                # checkpoints stay unlit until they have behaviour
                LevelObject(frames[:1] if kind == "checkpoint" else frames, (x, y))
            elif kind == "tunnel":
                tunnel_cells.setdefault(entity["pair"], []).append(
                    pygame.Rect(pos, (TILESIZE, TILESIZE)))

        errors = [f"Tunnel pair {pair}: expected 2 mouths, found {len(cells)} at "
                  f"{[(c.x // TILESIZE, c.y // TILESIZE) for c in cells]}"
                  for pair, cells in tunnel_cells.items() if len(cells) != 2]
        if errors:
            raise ValueError(f"Invalid tunnels in level {level_num}:\n" + "\n".join(errors))
        self.tunnels = {pair: tuple(cells) for pair, cells in tunnel_cells.items()}

    def render_decor(self, level, layer, size):
        """One decor layer drawn onto a transparent surface; None when it is empty."""
        items = [d for d in level["decor"] if d.get("layer", "back") == layer]
        if not items:
            return None
        surface = pygame.Surface(size, pygame.SRCALPHA)
        for decor in items:
            image = self.decor_image(decor["id"])
            if image is not None:
                bottom_left = (decor["x"] * TILESIZE, (decor["y"] + 1) * TILESIZE)
                surface.blit(image, image.get_rect(bottomleft=bottom_left))
        return surface

    def decor_image(self, decor_id):
        if decor_id not in self.decor_images:
            path = f"decor/{decor_id}.png"
            if os.path.isfile(path):
                self.decor_images[decor_id] = pygame.image.load(path).convert_alpha()
            else:
                print(f"Warning: decor image not found: {path}")
                self.decor_images[decor_id] = None
        return self.decor_images[decor_id]

    @staticmethod
    def placeholder(size):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((230, 200, 60))
        return surface

    def update_camera(self):
        target = pygame.Vector2(G.player.rect.center) - (WIDTH // 2, HEIGHT // 2)
        self.offset += (target - self.offset) * 0.05

    def draw(self):
        G.screen.fill(self.background)
        if self.decor_back is not None:
            G.screen.blit(self.decor_back, -self.offset)
        G.screen.blit(self.floor, -self.offset)
        for sprite in G.all_sprites_group:
            G.screen.blit(sprite.image, pygame.Vector2(sprite.rect.topleft) - self.offset)
        if self.decor_front is not None:
            G.screen.blit(self.decor_front, -self.offset)
