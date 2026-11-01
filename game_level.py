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
    """Checkpoint or goal artwork standing in its tile."""
    FRAME_TICKS = 20

    def __init__(self, frames, cell, kind="goal"):
        super().__init__(G.all_sprites_group)
        self.kind = kind
        self.frames = frames
        self.ticks = 0
        self.image = frames[0]
        self.activated = False
        x, y = cell
        self.rect = self.image.get_rect(bottomleft=(x * TILESIZE, (y + 1) * TILESIZE))

    def update(self):
        if self.kind == "goal":
            self.ticks += 1
            self.image = self.frames[(self.ticks // self.FRAME_TICKS) % len(self.frames)]
        elif self.kind == "checkpoint":
            if self.activated and len(self.frames) > 1:
                self.image = self.frames[1]
            else:
                self.image = self.frames[0]


class HintSign(pygame.sprite.Sprite):
    """A sign whose tip pops up in a bubble while the player is close.

    The bubble floats above head height and is drawn after every sprite
    (GameLevel.draw), so the player never covers it.
    """
    REACH = (TILESIZE * 4, TILESIZE * 3)
    BUBBLE_LIFT = TILESIZE * 5 // 2

    def __init__(self, sign, text, cell, font):
        super().__init__(G.all_sprites_group)
        x, y = cell
        self.anchor = (x * TILESIZE + TILESIZE // 2, (y + 1) * TILESIZE)
        self.image = sign
        self.rect = sign.get_rect(midbottom=self.anchor)
        self.bubble = self.make_bubble(text, font) if text else None
        self.bubble_rect = (self.bubble.get_rect(midbottom=(self.anchor[0], self.anchor[1] - self.BUBBLE_LIFT))
                            if self.bubble else None)
        self.near = False

    @staticmethod
    def make_bubble(text, font):
        label = font.render(text, True, (255, 255, 255))
        bubble = pygame.Surface((label.get_width() + 20, label.get_height() + 14), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (20, 24, 36, 225), bubble.get_rect(), border_radius=6)
        bubble.blit(label, (10, 7))
        return bubble

    def update(self):
        player = G.player
        self.near = (player is not None
                     and abs(player.base_player_rect.centerx - self.anchor[0]) < self.REACH[0]
                     and abs(player.base_player_rect.bottom - self.anchor[1]) < self.REACH[1])


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
        self.checkpoints = []
        self.goal = None
        self.level_completed = False
        self.level_clear_timer = 0
        self.tunnels = {}
        self.decor_images = {}
        self.hint_signs = []
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
        tunnel_markers = {}
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
                   else [] for name in ("checkpoint", "goal", "chest", "wallet")}
        hint_font = pygame.font.Font("font/PublicPixel.ttf", 10)
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
            elif kind in ("checkpoint", "goal", "chest", "wallet"):
                frames = objects[kind] or [self.placeholder((TILESIZE, 2 * TILESIZE))]
                if kind == "chest":
                    frames = frames[:1]  # stays closed until chests can be opened
                obj = LevelObject(frames, (x, y), kind=kind)
                if kind == "checkpoint":
                    self.checkpoints.append(obj)
                elif kind == "goal":
                    self.goal = obj
            elif kind == "hint":
                sign = self.decor_image("sign") or self.placeholder((TILESIZE, TILESIZE))
                self.hint_signs.append(HintSign(sign, entity.get("text", ""), (x, y), hint_font))
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

    def try_enter_tunnel(self, player):
        """Enter a mouth while standing on the floor immediately beneath it.

        Mouth markers occupy empty space, not solid tiles. Centering the player
        over the marker prevents their wide sprite from entering a nearby mouth.
        """
        if not player.on_ground or player.health <= 0:
            return False
        for mouths in self.tunnels.values():
            for index, mouth in enumerate(mouths):
                if not (mouth.left <= player.base_player_rect.centerx < mouth.right
                        and player.base_player_rect.bottom == mouth.bottom):
                    continue
                destination = mouths[1 - index]
                target = player.base_player_rect.copy()
                target.midbottom = (destination.centerx, destination.bottom)
                if (not self.floor.get_rect().contains(target)
                        or any(target.colliderect(tile.rect) for tile in G.obstacles_group)):
                    return False
                player.base_player_rect = target
                player.rect.center = target.center
                # Do not treat the teleport path as movement for stomp detection.
                player.previous_rect = target.copy()
                player.vec_pos.update(target.center)
                player.velocity_x = 0
                player.velocity_y = 0
                player.on_ground = any(
                    target.bottom == tile.rect.top
                    and target.left < tile.rect.right and target.right > tile.rect.left
                    for tile in G.obstacles_group
                )
                self.offset.update(pygame.Vector2(target.center) - (WIDTH // 2, HEIGHT // 2))
                return True
        return False

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
        G.screen.fill(self.background)
        draw_offset = self.offset + self.shake_offset
        if self.decor_back is not None:
            G.screen.blit(self.decor_back, -draw_offset)
        G.screen.blit(self.floor, -draw_offset)
        for sprite in G.all_sprites_group:
            G.screen.blit(sprite.image, pygame.Vector2(sprite.rect.topleft) - draw_offset)
        if self.decor_front is not None:
            G.screen.blit(self.decor_front, -draw_offset)
        for sign in self.hint_signs:
            if sign.near and sign.bubble is not None:
                G.screen.blit(sign.bubble, pygame.Vector2(sign.bubble_rect.topleft) - draw_offset)
