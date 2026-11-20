"""Load a level, build platform collisions, and draw the scrolling world."""
import os
import pygame
from item import Item
from enemy import WalkingEnemy, TurtleEnemy, GoblinEnemy
from settings import WIDTH, HEIGHT, TILESIZE, BEADS_NEEDED, game_stats, import_folder
from terrain import TileTextures
from shop import Shop, load_shop_image, shop_rect
from ui import FloatingText
import level_format
import globals as G


class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, tile_type=0):
        super().__init__(G.obstacles_group)
        self.rect = pygame.Rect(pos, (TILESIZE, TILESIZE))
        self.tile_type = tile_type


class LevelObject(pygame.sprite.Sprite):
    """Checkpoint, goal, chest or wallet artwork standing in its tile."""
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
        elif self.kind in ("checkpoint", "chest"):  # lit flag, open chest
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
        """Dark rounded box with the text; "\\n" starts a new line."""
        labels = [font.render(line, True, (255, 255, 255)) for line in text.split("\n")]
        gap = 5
        width = max(label.get_width() for label in labels) + 20
        height = sum(label.get_height() for label in labels) + gap * (len(labels) - 1) + 14
        bubble = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (20, 24, 36, 225), bubble.get_rect(), border_radius=6)
        y = 7
        for label in labels:
            bubble.blit(label, (10, y))
            y += label.get_height() + gap
        return bubble

    def set_text(self, text, font):
        self.bubble = self.make_bubble(text, font) if text else None
        self.bubble_rect = (self.bubble.get_rect(midbottom=(self.anchor[0], self.anchor[1] - self.BUBBLE_LIFT))
                            if self.bubble else None)

    def update(self):
        player = G.player
        # wait for the cage to break, so the cage prompt is the only instruction at the start
        self.near = (player is not None and not player.is_caged
                     and abs(player.base_player_rect.centerx - self.anchor[0]) < self.REACH[0]
                     and abs(player.base_player_rect.bottom - self.anchor[1]) < self.REACH[1])


class ElderNPC(HintSign):
    """The old man who wants the 33 golden tesbih beads (code name npc).

    He talks like a hint sign: the bubble shows while the player is near,
    and its text follows the bead count. With enough beads he will summon
    the final boss; until the boss exists he says that it is coming.
    """
    REACH = (TILESIZE * 5, TILESIZE * 3)
    BUBBLE_LIFT = TILESIZE * 3
    FRAME_TICKS = 24

    def __init__(self, frames, cell, font):
        super().__init__(frames[0], "", cell, font)
        self.frames = frames
        self.font = font
        self.ticks = 0
        self.shown_beads = None
        self.greeted = False  # the "enough beads" reward is given once

    @staticmethod
    def speech(beads):
        if beads >= BEADS_NEEDED:
            return f"{BEADS_NEEDED} boncuk tamam, aferin evlat!\nOnu çağırmanın vakti yakında gelecek..."
        missing = BEADS_NEEDED - beads
        return f"Tesbihimin altın boncukları dağıldı.\n{missing} tane daha getir, evlat."

    def update(self):
        super().update()
        self.ticks += 1
        self.image = self.frames[(self.ticks // self.FRAME_TICKS) % len(self.frames)]
        beads = game_stats["beads"]
        if beads != self.shown_beads:
            self.shown_beads = beads
            self.set_text(self.speech(beads), self.font)
        if self.near and beads >= BEADS_NEEDED and not self.greeted:
            self.greeted = True
            from effects import burst, Ring
            tesbih = self.bead_positions()
            centre = tesbih[len(tesbih) // 2]
            Ring(centre, life=30, colour=(255, 230, 140), reach=50)
            burst(centre, 16, 4, hearts=0, colours=((255, 236, 150), (255, 255, 255)))
            game_stats["score"] += 500
            if getattr(G, "create_floating_text", None):
                G.create_floating_text("Tesbih tamam! +500", (self.anchor[0], self.rect.top - 8),
                                       (255, 235, 140), duration=150)


    # The tesbih loop in objects/npc frames (40 wide, drawn facing right and
    # saved flipped): hand at (25, 42), the loop shifted by the frame's swing.
    HAND = (25, 42)

    def bead_positions(self):
        """World centres of the loop's beads in the frame being shown."""
        swing = (self.ticks // self.FRAME_TICKS) % len(self.frames)
        hx, hy = self.HAND
        loop = [(hx - 1, hy + 2), (hx - 2 + swing, hy + 4), (hx - 2 + swing, hy + 6),
                (hx - 1 + swing, hy + 8), (hx + 1 + swing, hy + 8), (hx + 2 + swing, hy + 6),
                (hx + 2 + swing, hy + 4), (hx + 1, hy + 2)]
        width = self.image.get_width()
        return [(self.rect.left + width - 1 - x + 0.5, self.rect.top + y + 0.5) for x, y in loop]

    def draw_glow(self, screen, offset):
        """With all the beads back, they light up one after another round the loop."""
        if game_stats["beads"] < BEADS_NEEDED:
            return
        beads = self.bead_positions()
        lit = (self.ticks // 5) % len(beads)
        for back, alpha in ((2, 70), (1, 140), (0, 255)):
            x, y = beads[(lit - back) % len(beads)]
            halo = pygame.Surface((11, 11), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 220, 120, alpha // 2), (5, 5), 5)
            pygame.draw.circle(halo, (255, 250, 215, alpha), (5, 5), 2)
            screen.blit(halo, (round(x - offset.x) - 5, round(y - offset.y) - 5))
        if self.ticks % 20 == 0:
            from effects import Sparkle
            x, y = beads[lit]
            Sparkle((x, y), (0, -1.2), 30, colour=(255, 236, 150), size=2)


class GameLevel:
    TIME_LIMIT_MS = 120_000

    def __init__(self, level_num):
        self.time_left_ms = self.TIME_LIMIT_MS
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
        self.last_checkpoint = None  # the player respawns here after dying
        self.chests = []
        self.wallets = []
        self.level_completed = False
        self.level_clear_timer = 0
        self.tunnels = {}
        self.decor_images = {}
        self.hint_signs = []
        self.npc = None
        self.prepare(level_num)

    def prepare(self, level_num):
        """Build levels/<n>.json, or the old levels/<n>_mask.png when there is no JSON.

        See level_format.py for the file format. Terrain and both decor layers
        are rendered once here, then blitted while scrolling.
        """
        level = level_format.load_for_game(level_num)
        self.shop = Shop(level["decor"])
        self.terrain_rows = list(level["terrain"])  # broken bricks are cleared here
        size = (level["width"] * TILESIZE, level["height"] * TILESIZE)
        self.background = tuple(level["background"])
        self.floor = pygame.Surface(size, pygame.SRCALPHA)
        textures = self.textures = TileTextures()
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
            elif kind == "bead":
                Item(centre, "bead")
            elif kind == "kimiz":
                Item(centre, "kimiz", entity.get("power", "big"))
            elif kind == "walker":
                self.enemy_spawn_pos.append(pos)
                WalkingEnemy(pos, entity.get("dir", -1))
            elif kind == "turtle":
                self.turtle_spawn_pos.append(pos)
                TurtleEnemy(pos, entity.get("dir", -1))
            elif kind == "goblin":
                GoblinEnemy(pos, entity.get("dir", -1))
            elif kind in ("checkpoint", "goal", "chest", "wallet"):
                frames = objects[kind] or [self.placeholder((TILESIZE, 2 * TILESIZE))]
                obj = LevelObject(frames, (x, y), kind=kind)
                if kind == "checkpoint":
                    self.checkpoints.append(obj)
                elif kind == "goal":
                    self.goal = obj
                elif kind == "chest":
                    obj.item = entity.get("item", "shotgun")
                    self.chests.append(obj)
                else:
                    self.wallets.append(obj)
            elif kind == "hint":
                sign = self.decor_image("sign") or self.placeholder((TILESIZE, TILESIZE))
                self.hint_signs.append(HintSign(sign, entity.get("text", ""), (x, y), hint_font))
            elif kind == "npc":
                frames = (import_folder("objects/npc") if os.path.isdir("objects/npc") else []) \
                    or [self.placeholder((TILESIZE, 2 * TILESIZE))]
                self.npc = ElderNPC(frames, (x, y), hint_font)
                self.hint_signs.append(self.npc)  # drawn with the hint bubbles
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
        items = level_format.decor_in_draw_order(level, layer)
        if not items:
            return None
        surface = pygame.Surface(size, pygame.SRCALPHA)
        for decor in items:
            image = self.decor_image(decor["id"])
            if image is not None:
                bottom_left = (decor["x"] * TILESIZE, (decor["y"] + 1) * TILESIZE)
                rect = shop_rect(decor) if decor["id"] == "shop" else image.get_rect(bottomleft=bottom_left)
                surface.blit(image, rect)
        return surface

    def decor_image(self, decor_id):
        if decor_id not in self.decor_images:
            path = f"decor/{decor_id}.png"
            if decor_id == "shop":
                self.decor_images[decor_id] = load_shop_image()
            elif os.path.isfile(path):
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
                self.snap_camera()
                return True
        return False

    def break_brick(self, tile):
        """A big hero's head breaks a brick: the tile, its picture and its map cell go."""
        from effects import brick_debris
        tile.kill()
        self.floor.fill((0, 0, 0, 0), tile.rect)
        col, row = tile.rect.x // TILESIZE, tile.rect.y // TILESIZE
        line = self.terrain_rows[row]
        self.terrain_rows[row] = line[:col] + level_format.EMPTY + line[col + 1:]
        brick_debris(self.textures.get(tile.tile_type), tile.rect)
        game_stats["score"] += 50
        if getattr(G, "cage_break_sound", None):
            G.cage_break_sound.play()
        self.shake_timer = max(self.shake_timer, 6)
        self.shake_amount = max(self.shake_amount, 3)

    def solid_at_pixel(self, x, y):
        col, row = x // TILESIZE, y // TILESIZE
        return (0 <= row < len(self.terrain_rows) and 0 <= col < len(self.terrain_rows[row])
                and self.terrain_rows[row][col] != level_format.EMPTY)

    def camera_target(self):
        target = pygame.Vector2(G.player.rect.center) - (WIDTH // 2, HEIGHT // 2)
        target.y = min(target.y, self.floor.get_height() - HEIGHT)
        return target

    def snap_camera(self):
        """Centre the view on the player at once (after a teleport or respawn)."""
        self.offset.update(self.camera_target())

    def update_camera(self):
        target = self.camera_target()
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
        draw_offset.y = min(draw_offset.y, self.floor.get_height() - HEIGHT)
        if self.decor_back is not None:
            G.screen.blit(self.decor_back, -draw_offset)
        G.screen.blit(self.floor, -draw_offset)
        self.shop.draw_world(G.screen, draw_offset)
        texts = []
        for sprite in G.all_sprites_group:
            if isinstance(sprite, FloatingText):
                texts.append(sprite)
            else:
                G.screen.blit(sprite.image, pygame.Vector2(sprite.rect.topleft) - draw_offset)
        if self.npc is not None:
            self.npc.draw_glow(G.screen, draw_offset)
        if self.decor_front is not None:
            G.screen.blit(self.decor_front, -draw_offset)
        for sign in self.hint_signs:
            if sign.near and sign.bubble is not None:
                G.screen.blit(sign.bubble, pygame.Vector2(sign.bubble_rect.topleft) - draw_offset)
        # score and pickup texts go over everything, hint bubbles included
        for text in texts:
            G.screen.blit(text.image, pygame.Vector2(text.rect.topleft) - draw_offset)
