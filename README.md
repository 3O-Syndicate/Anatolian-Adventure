# Anatolian Adventure

A single-player 2D platform game in the spirit of classic run-and-jump games,
with original characters, levels and art, a Turkish interface and settings
inspired by Türkiye. Team 3O Syndicate, SE3003 Software Project Management.

## Running

Python 3 with pygame:

```
pip install pygame
python main.py
```

On Python versions that have no pygame wheel yet, `pip install pygame-ce`
works the same way. `python main.py --level 1` starts on a given level.

## Controls

| Key | Action |
| --- | --- |
| `A` / `D` | Walk left / right |
| `W` | Jump (hold for a higher jump) |
| `S` | Duck; standing in a tunnel mouth (in the tutorial: on top of the pipe), go through the tunnel |
| `Space` or left click | Shoot |
| `R` | Reload |
| `Q` | Pour acid (after finding it in a chest) |
| `E` or `Space` | Break the cage at the start of a level |
| `Esc` | Pause; `Q` quits while paused |
| `P` | Play again after game over or after the last level |

Touching a checkpoint flag makes it the place to respawn after dying. Chests
open on touch: the shotgun chest gives ammo, the armor chest stops one enemy
hit, the acid chest gives three flasks for `Q`.

## Levels

Level 0 is the tutorial; the game moves to the next level when the goal flag
is touched. Levels are JSON files in `levels/`, built with the map editor
(`python editor.py 1`). See [levels/README.md](levels/README.md) for the
level list, the editor's keys and the file format.

## Project layout

| Path | Contents |
| --- | --- |
| `main.py` | Game loop, level flow, pause, game over and completion screens |
| `player.py` | Movement, shooting, items, checkpoints and respawning |
| `enemy.py`, `bullet.py`, `acid.py`, `item.py`, `cage.py` | Enemies, projectiles, acid puddles, pickups, the start cage |
| `game_level.py`, `level_format.py`, `terrain.py` | Level loading, the JSON level format, terrain textures |
| `ui.py` | HUD and floating texts |
| `editor.py` | Internal map editor (a development tool, not a game feature) |
| `assets.py`, `settings.py`, `globals.py` | Asset loading, constants, shared objects |
| `art/` | Scripts that draw the hero, enemies, decor, objects and some tiles ([art/README.md](art/README.md)) |
| `tiles/` | Terrain textures ([tiles/README.md](tiles/README.md)) |
