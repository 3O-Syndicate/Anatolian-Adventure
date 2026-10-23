"""
editor.py

Map editor for Anatolian Adventure levels (levels/<n>.json, see level_format.py).
It draws the level with the game's own tiles, decor and sprites.

Run:  python editor.py [level number]      (default 0)

Mouse
  left drag       paint the selected tile / decor / object
  right drag      erase on the current tab
  middle drag     move the view (or hold Space and left-drag)
  wheel           zoom
Keys
  1 2 3           Zemin / Dekor / Nesne tabs
  B  R            brush / rectangle (rectangle fills terrain)
  L               decor layer: back (behind terrain) / front (over the player)
  G               grid on/off
  arrows          move the view
  Alt+click / I   pick what is under the cursor
  F               turn the enemy under the cursor around
  + / -           change the pair number of the tunnel under the cursor
  Ctrl+Z / Ctrl+Y undo / redo
  Ctrl+arrows     resize: columns at the right edge, rows at the top
                  hold Shift for 10 tiles (also works on the +/- buttons)
  PgUp / PgDn     previous / next level (a missing number starts a new level)
  F5              save and play this level (python main.py --level <n>)
  Ctrl+S          save; problems such as unpaired tunnels are listed
  Esc             quit (press twice to drop unsaved changes)
"""
import copy
import math
import os
import subprocess
import sys

import pygame

import level_format
from settings import TILESIZE, TERRAIN_TEXTURES
from terrain import TileTextures

SCREEN_W, SCREEN_H = 1280, 720
PANEL_W = 270
VIEW_W = SCREEN_W - PANEL_W
ZOOMS = (0.5, 1, 2)
NEW_LEVEL_SIZE = (110, 32)

UI_BG = (30, 32, 44)
UI_BOX = (44, 47, 64)
UI_LINE = (70, 74, 96)
UI_TEXT = (230, 232, 240)
UI_DIM = (140, 146, 170)
UI_ACCENT = (255, 205, 80)
OUTSIDE = (22, 24, 32)

TABS = (("terrain", "Zemin"), ("decor", "Dekor"), ("entity", "Nesne"))
ENTITY_LABELS = {
    "player": "Oyuncu", "walker": "Kaz", "turtle": "Tosbağa", "health": "Can",
    "coin": "Altın", "tunnel": "Tünel", "checkpoint": "Kontrol", "goal": "Bitiş",
}
TERRAIN_LABELS = {0: "Görünmez", 1: "Zemin", 2: "Toprak", 3: "Tuğla"}
# entities that can be painted by dragging; the rest go down one per click
DRAG_ENTITIES = {"coin"}


def load_image(path):
    return pygame.image.load(path).convert_alpha() if os.path.isfile(path) else None


class Art:
    """Everything the editor draws, with scaled copies cached per zoom."""

    def __init__(self):
        self.textures = TileTextures()
        self.terrain_ids = sorted({0, *TERRAIN_TEXTURES} | {
            int(name[:-4]) for name in os.listdir("tiles")
            if name.endswith(".png") and name[:-4].isdigit()})
        self.decor = {}
        for name in sorted(os.listdir("decor")) if os.path.isdir("decor") else []:
            if name.endswith(".png"):
                self.decor[name[:-4]] = load_image(os.path.join("decor", name))
        # entity type -> (image, how it sits in its tile)
        self.entities = {
            "player": (load_image("player/hero/idle/0.png"), "midbottom"),
            "walker": (load_image("enemies/walker/walk/0.png"), "midbottom"),
            "turtle": (load_image("enemies/turtle/walk/0.png"), "midbottom"),
            "health": (load_image("items/health.png"), "center"),
            "coin": (load_image("items/coin/0.png"), "center"),
            "tunnel": (None, "center"),
            "checkpoint": (load_image("objects/checkpoint/1.png"), "bottomleft"),
            "goal": (load_image("objects/goal/0.png"), "bottomleft"),
        }
        self.invisible = pygame.Surface((TILESIZE, TILESIZE), pygame.SRCALPHA)
        self.invisible.fill((255, 0, 255, 70))
        for i in range(0, TILESIZE * 2, 8):
            pygame.draw.line(self.invisible, (255, 0, 255, 160), (i, 0), (i - TILESIZE, TILESIZE))
        self.cache = {}

    def tile(self, tile_id):
        if tile_id == 0:
            return self.invisible
        return self.textures.get(tile_id)

    def scaled(self, key, image, zoom, flip=False):
        cache_key = (key, zoom, flip)
        if cache_key not in self.cache:
            if flip:
                image = pygame.transform.flip(image, True, False)
            size = (max(1, round(image.get_width() * zoom)), max(1, round(image.get_height() * zoom)))
            self.cache[cache_key] = pygame.transform.scale(image, size)
        return self.cache[cache_key]

    def entity_rect(self, entity):
        """World rectangle an entity is drawn in (also used to pick it)."""
        image, placement = self.entities[entity["type"]]
        cell = pygame.Rect(entity["x"] * TILESIZE, entity["y"] * TILESIZE, TILESIZE, TILESIZE)
        size = image.get_size() if image else (TILESIZE, TILESIZE)
        rect = pygame.Rect((0, 0), size)
        setattr(rect, placement, getattr(cell, placement))
        return rect

    def decor_rect(self, decor):
        image = self.decor.get(decor["id"])
        size = image.get_size() if image else (TILESIZE, TILESIZE)
        return pygame.Rect((0, 0), size).move(
            decor["x"] * TILESIZE, (decor["y"] + 1) * TILESIZE - size[1])


class Editor:
    def __init__(self, level_num, screen):
        self.screen = screen
        self.font = pygame.font.Font("font/PublicPixel.ttf", 8)
        self.font_big = pygame.font.Font("font/PublicPixel.ttf", 12)
        self.art = Art()
        self.message = ""
        self.tab = "terrain"
        self.selected = {"terrain": 1, "decor": next(iter(self.art.decor), None), "entity": "walker"}
        self.decor_layer = "back"
        self.tool = "brush"
        self.zoom = 1
        self.show_grid = True
        self.running = True
        self.quit_armed = False
        self.pan_from = None       # mouse position while panning
        self.stroke = None         # "paint" / "erase" while a mouse button is held
        self.stroke_before = None  # level copy from the start of a stroke, for undo
        self.rect_start = None     # first cell of a rectangle drag
        self.last_cell = None
        self.hits = []             # (screen rect, action) for panel buttons, rebuilt each draw
        self.load(level_num)

    def load(self, level_num):
        """Open (or start) a level and reset the history and view."""
        self.level_num = level_num
        self.path = os.path.join("levels", f"{level_num}.json")
        self.level = self.open_level()
        self.dirty = False
        self.undo_stack, self.redo_stack = [], []
        self.stroke = self.stroke_before = self.rect_start = self.last_cell = None
        self.pan_from = None
        self.quit_armed = False
        world_h = self.level["height"] * TILESIZE
        self.offset = pygame.Vector2(0, max(0, world_h - SCREEN_H))  # start at the bottom-left
        pygame.display.set_caption(f"Anatolian Adventure - Harita Editörü (bölüm {level_num})")

    # --- level file ---------------------------------------------------------

    def open_level(self):
        if os.path.exists(self.path):
            self.message = f"Açıldı: {self.path}"
            return level_format.load_level(self.path)
        mask = os.path.join("levels", f"{self.level_num}_mask.png")
        if os.path.exists(mask):
            self.message = f"Maske içe aktarıldı: {mask}"
            return level_format.mask_to_level(pygame.image.load(mask))
        self.message = "Yeni bölüm"
        return level_format.new_level(*NEW_LEVEL_SIZE)

    def save(self):
        self.finish_stroke()
        try:
            level_format.check_shape(self.level)
            level_format.save_level(self.level, self.path)
        except (OSError, ValueError) as error:
            self.message = f"Kaydedilemedi: {error}"
            return False
        self.dirty = False
        self.message = f"Kaydedildi: {self.path}"
        issues = level_format.problems(self.level)
        if issues:
            self.message += ". Uyarı: " + "; ".join(issues)
        return True

    def playtest(self):
        """Save, then run the game on this level in its own window."""
        if not self.save():
            return
        unpaired = [pair for pair, spots in level_format.tunnel_pairs(self.level).items()
                    if len(spots) != 2]
        if unpaired:
            self.message = f"Oyun açılmadı: eşi olmayan tünel {unpaired}"
            return
        subprocess.Popen([sys.executable, "main.py", "--level", str(self.level_num)])
        self.message += " | Oyun başlatıldı"

    def switch_level(self, delta):
        self.finish_stroke()
        if self.dirty:
            self.message = "Önce kaydet (Ctrl+S)"
            return
        self.load(max(0, self.level_num + delta))

    # --- history ------------------------------------------------------------

    def remember(self, before):
        """Record the level as it was before an edit, if the edit changed anything."""
        if before != self.level:
            self.undo_stack.append(before)
            del self.undo_stack[:-100]
            self.redo_stack.clear()
            self.dirty = True

    def change(self, action):
        """Run a one-shot edit as a single undo step."""
        self.finish_stroke()
        before = copy.deepcopy(self.level)
        action()
        self.remember(before)

    def undo(self):
        self.finish_stroke()
        if self.undo_stack:
            self.redo_stack.append(self.level)
            self.level = self.undo_stack.pop()
            self.dirty = True
            self.message = "Geri alındı"

    def redo(self):
        self.finish_stroke()
        if self.redo_stack:
            self.undo_stack.append(self.level)
            self.level = self.redo_stack.pop()
            self.dirty = True
            self.message = "Yinelendi"

    # --- coordinates --------------------------------------------------------

    def to_cell(self, pos):
        """Screen position -> (col, row) inside the map, or None."""
        if pos[0] >= VIEW_W:
            return None
        col = math.floor((pos[0] / self.zoom + self.offset.x) / TILESIZE)
        row = math.floor((pos[1] / self.zoom + self.offset.y) / TILESIZE)
        if 0 <= col < self.level["width"] and 0 <= row < self.level["height"]:
            return (col, row)
        return None

    def to_screen(self, world_pos):
        return ((world_pos[0] - self.offset.x) * self.zoom, (world_pos[1] - self.offset.y) * self.zoom)

    def screen_rect(self, world_rect):
        x, y = self.to_screen(world_rect.topleft)
        return pygame.Rect(round(x), round(y), round(world_rect.w * self.zoom),
                           round(world_rect.h * self.zoom))

    def set_zoom(self, zoom, around):
        """Change zoom keeping the world point under `around` in place."""
        world = (around[0] / self.zoom + self.offset.x, around[1] / self.zoom + self.offset.y)
        self.zoom = zoom
        self.offset.update(world[0] - around[0] / zoom, world[1] - around[1] / zoom)

    # --- editing ------------------------------------------------------------

    def set_tile(self, col, row, tile_id):
        line = self.level["terrain"][row]
        char = level_format.tile_char(tile_id)
        if line[col] != char:
            self.level["terrain"][row] = line[:col] + char + line[col + 1:]
            self.dirty = True

    def fill_rect(self, a, b, tile_id):
        for row in range(min(a[1], b[1]), max(a[1], b[1]) + 1):
            for col in range(min(a[0], b[0]), max(a[0], b[0]) + 1):
                self.set_tile(col, row, tile_id)

    def place_decor(self, col, row):
        decor_id = self.selected["decor"]
        if decor_id is None:
            return
        item = {"id": decor_id, "x": col, "y": row, "layer": self.decor_layer}
        if item not in self.level["decor"]:
            self.level["decor"].append(item)
            self.dirty = True

    def erase_decor(self, col, row):
        """Remove the top decor of the current layer covering this tile."""
        point = ((col + 0.5) * TILESIZE, (row + 0.5) * TILESIZE)
        for item in reversed(self.level["decor"]):
            if item.get("layer", "back") == self.decor_layer and self.art.decor_rect(item).collidepoint(point):
                self.level["decor"].remove(item)
                self.dirty = True
                return

    def entity_at(self, col, row):
        for entity in self.level["entities"]:
            if (entity["x"], entity["y"]) == (col, row):
                return entity
        return None

    def place_entity(self, col, row):
        kind = self.selected["entity"]
        entities = self.level["entities"]
        old = self.entity_at(col, row)
        if old is not None:
            entities.remove(old)
        if level_format.ENTITY_TYPES[kind][1] == "one":  # player and goal move instead of duplicating
            entities[:] = [e for e in entities if e["type"] != kind]
        entity = level_format.new_entity(kind, col, row)
        if kind == "tunnel":
            entity["pair"] = self.free_tunnel_pair()
        if kind in ("walker", "turtle") and old is not None and old["type"] == kind:
            entity["dir"] = old["dir"]
        entities.append(entity)
        self.dirty = True

    def free_tunnel_pair(self):
        """Join a tunnel that has no partner yet, otherwise start a new pair."""
        pairs = level_format.tunnel_pairs(self.level)
        lonely = sorted(pair for pair, spots in pairs.items() if len(spots) == 1)
        return lonely[0] if lonely else max(pairs, default=0) + 1

    def entity_under(self, cell):
        """Topmost object in this tile or drawn over it."""
        col, row = cell
        point = ((col + 0.5) * TILESIZE, (row + 0.5) * TILESIZE)
        for entity in reversed(self.level["entities"]):
            if (entity["x"], entity["y"]) == (col, row) or \
                    self.art.entity_rect(entity).collidepoint(point):
                return entity
        return None

    def erase_entity(self, col, row):
        entity = self.entity_under((col, row))
        if entity is not None:
            self.level["entities"].remove(entity)
            self.dirty = True

    def pick(self, cell):
        """Select whatever is under the cursor on the current tab."""
        if cell is None:
            return
        col, row = cell
        if self.tab == "terrain":
            tile_id = level_format.char_tile(self.level["terrain"][row][col])
            if tile_id is not None:
                self.selected["terrain"] = tile_id
        elif self.tab == "decor":
            point = ((col + 0.5) * TILESIZE, (row + 0.5) * TILESIZE)
            for item in reversed(self.level["decor"]):
                if self.art.decor_rect(item).collidepoint(point):
                    self.selected["decor"] = item["id"]
                    self.decor_layer = item.get("layer", "back")
                    return
        else:
            entity = self.entity_under(cell)
            if entity is not None:
                self.selected["entity"] = entity["type"]

    def flip_enemy(self, cell):
        entity = self.entity_under(cell) if cell else None
        if entity is not None and "dir" in entity:
            self.change(lambda: entity.__setitem__("dir", -entity["dir"]))

    def change_pair(self, cell, delta):
        entity = self.entity_under(cell) if cell else None
        if entity is not None and entity["type"] == "tunnel":
            self.change(lambda: entity.__setitem__("pair", max(1, entity["pair"] + delta)))
            self.message = f"Tünel eşi: {entity['pair']}"

    def resize(self, d_width, d_height):
        """Columns come and go at the right edge, rows at the top, so the ground stays put."""
        level = self.level
        width, height = level["width"] + d_width, level["height"] + d_height
        if not (20 <= width <= 1000 and 15 <= height <= 200):
            self.message = "Boyut sınırı: 20-1000 x 15-200 karo"
            return
        terrain = [row[:width].ljust(width, level_format.EMPTY) for row in level["terrain"]]
        if d_height > 0:
            terrain = [level_format.EMPTY * width] * d_height + terrain
        else:
            terrain = terrain[-d_height:]
        for item in level["entities"] + level["decor"]:
            item["y"] += d_height
        level["entities"] = [e for e in level["entities"]
                             if 0 <= e["x"] < width and 0 <= e["y"] < height]
        level["decor"] = [d for d in level["decor"] if 0 <= d["x"] < width and 0 <= d["y"] < height]
        level["terrain"], level["width"], level["height"] = terrain, width, height
        self.offset.y += d_height * TILESIZE
        self.message = f"Boyut: {width}x{height}"

    def resize_canvas(self, d_width, d_height):
        """The sidebar and keyboard share the same undoable resize action."""
        step = 10 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1
        self.change(lambda: self.resize(d_width * step, d_height * step))

    def apply(self, cell, first):
        """Paint or erase at a cell during a stroke; `first` is the button-down cell."""
        col, row = cell
        if self.stroke == "erase":
            {"terrain": lambda: self.set_tile(col, row, None),
             "decor": lambda: self.erase_decor(col, row),
             "entity": lambda: self.erase_entity(col, row)}[self.tab]()
        elif self.tab == "terrain":
            self.set_tile(col, row, self.selected["terrain"])
        elif self.tab == "decor":
            image = self.art.decor.get(self.selected["decor"])
            if first or (image is not None and image.get_width() <= TILESIZE):
                self.place_decor(col, row)
        elif first or self.selected["entity"] in DRAG_ENTITIES:
            self.place_entity(col, row)

    # --- input --------------------------------------------------------------

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.request_quit()
        elif event.type == pygame.KEYDOWN:
            self.handle_key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.handle_mouse_up(event)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event)
        elif event.type == pygame.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            if pos[0] < VIEW_W:
                index = ZOOMS.index(self.zoom) + (1 if event.y > 0 else -1)
                self.set_zoom(ZOOMS[max(0, min(len(ZOOMS) - 1, index))], pos)

    def request_quit(self):
        if self.dirty and not self.quit_armed:
            self.quit_armed = True
            self.message = "Kaydedilmemiş değişiklik var! Çıkmak için tekrar Esc"
        else:
            self.running = False

    def handle_key(self, event):
        ctrl = event.mod & pygame.KMOD_CTRL
        if event.key != pygame.K_ESCAPE:
            self.quit_armed = False
        cell = self.to_cell(pygame.mouse.get_pos())
        resize = {pygame.K_RIGHT: (1, 0), pygame.K_LEFT: (-1, 0),
                  pygame.K_UP: (0, 1), pygame.K_DOWN: (0, -1)}
        if event.key == pygame.K_ESCAPE:
            self.request_quit()
        elif ctrl and event.key == pygame.K_s:
            self.save()
        elif ctrl and event.key == pygame.K_z:
            if event.mod & pygame.KMOD_SHIFT:
                self.redo()
            else:
                self.undo()
        elif ctrl and event.key == pygame.K_y:
            self.redo()
        elif ctrl and event.key in resize:
            self.resize_canvas(*resize[event.key])
        elif event.key == pygame.K_F5:
            self.playtest()
        elif event.key == pygame.K_PAGEUP:
            self.switch_level(-1)
        elif event.key == pygame.K_PAGEDOWN:
            self.switch_level(1)
        elif event.key == pygame.K_i:
            self.pick(cell)
        elif event.key == pygame.K_f:
            self.flip_enemy(cell)
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.change_pair(cell, 1)
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.change_pair(cell, -1)
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.tab = TABS[event.key - pygame.K_1][0]
        elif event.key == pygame.K_b:
            self.tool = "brush"
        elif event.key == pygame.K_r:
            self.tool = "rect"
        elif event.key == pygame.K_l:
            self.decor_layer = "front" if self.decor_layer == "back" else "back"
        elif event.key == pygame.K_g:
            self.show_grid = not self.show_grid

    def handle_mouse_down(self, event):
        if event.pos[0] >= VIEW_W:
            if event.button == 1:
                for rect, action in self.hits:
                    if rect.collidepoint(event.pos):
                        action()
                        break
            return
        space = pygame.key.get_pressed()[pygame.K_SPACE]
        if event.button == 2 or (event.button == 1 and space):
            self.pan_from = event.pos
            return
        if event.button not in (1, 3):
            return
        cell = self.to_cell(event.pos)
        if event.button == 1 and pygame.key.get_mods() & pygame.KMOD_ALT:
            self.pick(cell)
            return
        self.stroke = "paint" if event.button == 1 else "erase"
        self.stroke_before = copy.deepcopy(self.level)
        if self.tool == "rect" and self.tab == "terrain":
            self.rect_start = cell
        elif cell is not None:
            self.apply(cell, first=True)
        self.last_cell = cell

    def handle_mouse_up(self, event):
        if event.button == 2 or (event.button == 1 and self.pan_from is not None):
            self.pan_from = None
            return
        if event.button not in (1, 3):
            return
        self.finish_stroke(event.pos)

    def finish_stroke(self, pos=None):
        """Commit a drag before saving, resizing, undoing or switching levels."""
        if self.rect_start is not None:
            end = (self.to_cell(pos) if pos is not None else None) or self.last_cell
            if end is not None:
                tile = self.selected["terrain"] if self.stroke == "paint" else None
                self.fill_rect(self.rect_start, end, tile)
        if self.stroke_before is not None:
            self.remember(self.stroke_before)
            self.stroke_before = None
        self.rect_start = None
        self.stroke = None
        self.last_cell = None

    def handle_mouse_motion(self, event):
        if self.pan_from is not None:
            self.offset -= pygame.Vector2(event.rel) / self.zoom
            return
        if self.stroke is None:
            return
        cell = self.to_cell(event.pos)
        if cell is not None and cell != self.last_cell:
            if self.rect_start is None:
                self.apply(cell, first=False)
            self.last_cell = cell

    def update(self):
        keys = pygame.key.get_pressed()
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            return  # Ctrl+arrows resize instead
        speed = 12 / self.zoom
        self.offset.x += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * speed
        self.offset.y += (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * speed

    # --- drawing ------------------------------------------------------------

    def draw(self):
        self.screen.fill(OUTSIDE)
        view = pygame.Rect(0, 0, VIEW_W, SCREEN_H)
        self.screen.set_clip(view)
        world = pygame.Rect(0, 0, self.level["width"] * TILESIZE, self.level["height"] * TILESIZE)
        self.screen.fill(self.level["background"], self.screen_rect(world).clip(view))
        self.draw_decor("back")
        self.draw_terrain()
        self.draw_entities()
        self.draw_decor("front")
        if self.show_grid:
            self.draw_grid(world)
        self.draw_cursor()
        self.screen.set_clip(None)
        self.draw_panel()

    def visible_cells(self):
        x0 = max(0, int(self.offset.x // TILESIZE))
        y0 = max(0, int(self.offset.y // TILESIZE))
        x1 = min(self.level["width"], int((self.offset.x + VIEW_W / self.zoom) // TILESIZE) + 1)
        y1 = min(self.level["height"], int((self.offset.y + SCREEN_H / self.zoom) // TILESIZE) + 1)
        return x0, y0, x1, y1

    def draw_terrain(self):
        x0, y0, x1, y1 = self.visible_cells()
        for row in range(y0, y1):
            line = self.level["terrain"][row]
            for col in range(x0, x1):
                tile_id = level_format.char_tile(line[col])
                if tile_id is None:
                    continue
                image = self.art.tile(tile_id)
                if image is not None:
                    pos = self.to_screen((col * TILESIZE, row * TILESIZE))
                    self.screen.blit(self.art.scaled(("tile", tile_id), image, self.zoom), pos)

    def draw_decor(self, layer):
        for item in self.level["decor"]:
            if item.get("layer", "back") != layer:
                continue
            image = self.art.decor.get(item["id"])
            rect = self.screen_rect(self.art.decor_rect(item))
            if image is None:
                pygame.draw.rect(self.screen, (255, 0, 0), rect, 1)
                continue
            self.screen.blit(self.art.scaled(("decor", item["id"]), image, self.zoom), rect)

    def draw_entities(self):
        for entity in self.level["entities"]:
            image, _ = self.art.entities[entity["type"]]
            rect = self.screen_rect(self.art.entity_rect(entity))
            if entity["type"] == "tunnel":
                self.draw_tunnel(rect, entity["pair"])
            elif image is not None:
                flip = entity.get("dir", 1) < 0
                self.screen.blit(self.art.scaled(("entity", entity["type"]), image, self.zoom, flip), rect)

    def draw_tunnel(self, rect, pair):
        hue = (pair * 67) % 360
        colour = pygame.Color(0)
        colour.hsva = (hue, 70, 95, 100)
        pygame.draw.rect(self.screen, colour, rect.inflate(-4, -4), border_radius=4)
        pygame.draw.rect(self.screen, (20, 20, 30), rect.inflate(-4, -4), 2, border_radius=4)
        label = self.font.render(f"T{pair}", True, (20, 20, 30))
        self.screen.blit(label, label.get_rect(center=rect.center))

    def draw_grid(self, world):
        area = self.screen_rect(world).clip(pygame.Rect(0, 0, VIEW_W, SCREEN_H))
        x0, y0, x1, y1 = self.visible_cells()
        colour = (0, 0, 0)
        grid = pygame.Surface(area.size, pygame.SRCALPHA)
        for col in range(x0, x1 + 1):
            x = round(self.to_screen((col * TILESIZE, 0))[0]) - area.x
            pygame.draw.line(grid, (*colour, 40), (x, 0), (x, area.h))
        for row in range(y0, y1 + 1):
            y = round(self.to_screen((0, row * TILESIZE))[1]) - area.y
            pygame.draw.line(grid, (*colour, 40), (0, y), (area.w, y))
        self.screen.blit(grid, area)

    def draw_cursor(self):
        mouse = pygame.mouse.get_pos()
        cell = self.to_cell(mouse)
        if self.rect_start is not None and cell is not None:
            a, b = self.rect_start, cell
            world = pygame.Rect(min(a[0], b[0]) * TILESIZE, min(a[1], b[1]) * TILESIZE,
                                (abs(a[0] - b[0]) + 1) * TILESIZE, (abs(a[1] - b[1]) + 1) * TILESIZE)
            colour = UI_ACCENT if self.stroke == "paint" else (255, 80, 80)
            pygame.draw.rect(self.screen, colour, self.screen_rect(world), 2)
            return
        if cell is None:
            return
        tile = pygame.Rect(cell[0] * TILESIZE, cell[1] * TILESIZE, TILESIZE, TILESIZE)
        ghost, world = self.ghost(cell)
        if ghost is not None:
            ghost = self.art.scaled(("ghost",) + self.ghost_key(), ghost, self.zoom).copy()
            ghost.set_alpha(140)
            self.screen.blit(ghost, self.screen_rect(world))
        pygame.draw.rect(self.screen, UI_ACCENT, self.screen_rect(tile), 1)

    def ghost_key(self):
        return (self.tab, self.selected[self.tab])

    def ghost(self, cell):
        """Image and world rect previewing the selected item at a cell."""
        col, row = cell
        if self.tab == "terrain":
            image = self.art.tile(self.selected["terrain"])
            return image, pygame.Rect(col * TILESIZE, row * TILESIZE, TILESIZE, TILESIZE)
        if self.tab == "decor":
            decor = {"id": self.selected["decor"], "x": col, "y": row}
            return self.art.decor.get(self.selected["decor"]), self.art.decor_rect(decor)
        entity = level_format.new_entity(self.selected["entity"], col, row)
        return self.art.entities[entity["type"]][0], self.art.entity_rect(entity)

    # --- side panel -----------------------------------------------------------

    def text(self, string, pos, colour=UI_TEXT, font=None):
        surface = (font or self.font).render(string, True, colour)
        self.screen.blit(surface, pos)
        return surface.get_rect(topleft=pos)

    def button(self, rect, label, active, action):
        pygame.draw.rect(self.screen, UI_ACCENT if active else UI_BOX, rect, border_radius=3)
        text = self.font.render(label, True, UI_BG if active else UI_TEXT)
        self.screen.blit(text, text.get_rect(center=rect.center))
        self.hits.append((rect, action))

    def palette_items(self):
        if self.tab == "terrain":
            return [(tile_id, TERRAIN_LABELS.get(tile_id, f"#{tile_id}"), self.art.tile(tile_id))
                    for tile_id in self.art.terrain_ids]
        if self.tab == "decor":
            return [(name, name, image) for name, image in self.art.decor.items()]
        return [(kind, ENTITY_LABELS[kind], self.art.entities[kind][0])
                for kind in level_format.ENTITY_TYPES]

    def draw_panel(self):
        self.hits = []
        panel = pygame.Rect(VIEW_W, 0, PANEL_W, SCREEN_H)
        pygame.draw.rect(self.screen, UI_BG, panel)
        pygame.draw.line(self.screen, UI_LINE, panel.topleft, panel.bottomleft, 2)
        x, y = VIEW_W + 12, 12
        star = " *" if self.dirty else ""
        self.text(f"Bölüm {self.level_num}{star}", (x, y), UI_ACCENT, self.font_big)
        self.text(self.path, (x, y + 20), UI_DIM)
        self.button(pygame.Rect(x, 48, 118, 22), "Kaydet Ctrl+S", False, self.save)
        self.button(pygame.Rect(x + 124, 48, 118, 22), "Oyna F5", False, self.playtest)
        self.button(pygame.Rect(x, 76, 118, 22), "< Önceki", False,
                    lambda: self.switch_level(-1))
        self.button(pygame.Rect(x + 124, 76, 118, 22), "Sonraki >", False,
                    lambda: self.switch_level(1))
        for y, label, value, delta in (
                (106, "Genişlik", self.level['width'], (1, 0)),
                (134, "Yükseklik", self.level['height'], (0, 1))):
            self.text(f"{label}: {value}", (x, y + 7))
            self.button(pygame.Rect(x + 174, y, 30, 22), "-", False,
                        lambda delta=delta: self.resize_canvas(-delta[0], -delta[1]))
            self.button(pygame.Rect(x + 210, y, 30, 22), "+", False,
                        lambda delta=delta: self.resize_canvas(*delta))
        self.text("Sağ/üst kenar; Shift: 10 karo", (x, 162), UI_DIM)

        y = 182
        tab_w = (PANEL_W - 24 - 8) // 3
        for i, (key, label) in enumerate(TABS):
            rect = pygame.Rect(x + i * (tab_w + 4), y, tab_w, 22)
            self.button(rect, f"{i + 1} {label}", self.tab == key,
                        lambda key=key: setattr(self, "tab", key))

        y += 32
        cell = 60
        for i, (key, label, image) in enumerate(self.palette_items()):
            rect = pygame.Rect(x + (i % 3) * 82, y + (i // 3) * (cell + 16), cell, cell)
            selected = self.selected[self.tab] == key
            pygame.draw.rect(self.screen, UI_BOX, rect, border_radius=3)
            if image is not None:
                fit = min((cell - 8) / image.get_width(), (cell - 8) / image.get_height())
                fit = math.floor(fit) if fit >= 1 else fit
                thumb = self.art.scaled(("thumb", self.tab, key), image, fit)
                self.screen.blit(thumb, thumb.get_rect(center=rect.center))
            elif self.tab == "entity" and key == "tunnel":
                self.draw_tunnel(rect.inflate(-14, -14), 1)
            if selected:
                pygame.draw.rect(self.screen, UI_ACCENT, rect, 2, border_radius=3)
            name = self.font.render(label[:9], True, UI_TEXT if selected else UI_DIM)
            self.screen.blit(name, name.get_rect(midtop=(rect.centerx, rect.bottom + 3)))
            self.hits.append((rect, lambda key=key: self.selected.__setitem__(self.tab, key)))

        y = 446
        self.text("Araç", (x, y), UI_DIM)
        self.button(pygame.Rect(x, y + 14, 118, 22), "B Fırça", self.tool == "brush",
                    lambda: setattr(self, "tool", "brush"))
        self.button(pygame.Rect(x + 124, y + 14, 118, 22), "R Dikdörtgen", self.tool == "rect",
                    lambda: setattr(self, "tool", "rect"))
        self.text("Dekor katmanı", (x, y + 44), UI_DIM)
        self.button(pygame.Rect(x, y + 58, 118, 22), "Arka", self.decor_layer == "back",
                    lambda: setattr(self, "decor_layer", "back"))
        self.button(pygame.Rect(x + 124, y + 58, 118, 22), "L Ön", self.decor_layer == "front",
                    lambda: setattr(self, "decor_layer", "front"))

        y = 530
        cell_pos = self.to_cell(pygame.mouse.get_pos())
        where = f"{cell_pos[0]}, {cell_pos[1]}" if cell_pos else "-"
        self.text(f"Hücre: {where}   Zoom: {self.zoom}x", (x, y), UI_DIM)
        for i, line in enumerate(self.wrap(self.message, 30)[:4]):
            self.text(line, (x, y + 16 + i * 12), UI_TEXT)

        help_lines = ["Sol: boya   Sağ: sil", "Orta/Space: kaydır",
                      "Teker: zoom  G: ızgara", "Alt+tık / I: seç",
                      "F: yön  +/-: tünel eşi", "Ctrl+Z/Y: geri al/yinele",
                      "Ctrl+oklar: boyut", "PgUp/Dn: bölüm / yeni",
                      "Ctrl+S: kaydet  Esc: çık"]
        for i, line in enumerate(help_lines):
            self.text(line, (x, SCREEN_H - 114 + i * 12), UI_DIM)

    @staticmethod
    def wrap(message, width):
        lines, line = [], ""
        for word in message.split():
            if len(line) + len(word) + 1 > width and line:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        return lines + ([line] if line else [])


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    level_num = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    editor = Editor(level_num, screen)
    clock = pygame.time.Clock()
    while editor.running:
        for event in pygame.event.get():
            editor.handle_event(event)
        editor.update()
        editor.draw()
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
