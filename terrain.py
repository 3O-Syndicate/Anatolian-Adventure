"""Map-mask terrain IDs and cached tile textures."""
from pathlib import Path
import pygame
from settings import TILESIZE, TERRAIN_TEXTURES


def terrain_type(color):
    """Return the green-channel terrain ID, or None for a non-terrain pixel.

    White is reserved for empty space. Alpha is currently ignored so mask
    opacity never changes collision behavior or texture appearance.
    """
    if color[0] == 255 and color[2] == 255 and color[1] != 255:
        return color[1]
    return None


class TileTextures:
    def __init__(self):
        self.cache = {}

    def get(self, tile_type):
        if tile_type == 0:
            return None
        if tile_type not in self.cache:
            path = Path(TERRAIN_TEXTURES.get(tile_type, f"tiles/{tile_type}.png"))
            if path.is_file():
                tile = pygame.image.load(str(path)).convert_alpha()
                tile = pygame.transform.scale(tile, (TILESIZE, TILESIZE))
            else:
                # Flat placeholders until repeating texture assets are supplied.
                colors = {1: (90, 155, 65), 2: (120, 80, 45), 3: (175, 75, 50)}
                color = colors.get(tile_type, (
                    50 + tile_type * 67 % 180,
                    50 + tile_type * 97 % 180,
                    50 + tile_type * 41 % 180,
                ))
                tile = pygame.Surface((TILESIZE, TILESIZE), pygame.SRCALPHA)
                tile.fill(color)
            self.cache[tile_type] = tile
        return self.cache[tile_type]
