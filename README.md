# Anatolian Adventure

A single-player 2D platform game in the spirit of classic run-and-jump games,
with original characters, levels and art, a Turkish interface and settings
inspired by Türkiye. Team 3O Syndicate, SE3003 Software Project Management.

## Running

Python 3 (tested with 3.14 on Windows). From a fresh clone on Windows
(PowerShell):

```
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

On macOS or Linux use `python3 -m venv .venv` and `source .venv/bin/activate`.
`requirements.txt` installs pygame-ce, which provides the `pygame` module and
has wheels for current Python versions; if the plain `pygame` package is
already installed in the same environment, `pip uninstall pygame` first.

`python main.py --level 1` starts on a given level (the map editor's F5 does
this); such runs never read or write the save.

## Saving

The game saves when a level starts: the level, score, coins and beads.
When a save exists the game opens on a start screen: `Enter` continues at
the start of the saved level, `N` starts a new game. Finishing the last
level deletes the save. The file is `%APPDATA%\AnatolianAdventure\save.json`
on Windows (`~/.local/share/AnatolianAdventure/save.json` elsewhere; the
`ANATOLIAN_SAVE` environment variable points to another file). A damaged
save is renamed to `save.json.bad` and the game starts fresh.

## Controls

| Key | Action |
| --- | --- |
| `A` / `D` | Walk left / right |
| `W` | Jump (hold for a higher jump) |
| `S` | Duck; standing in a tunnel mouth (in the tutorial: on top of the pipe), go through the tunnel |
| `Space` or left click | Shoot (once you have the shotgun) |
| `R` | Reload (once you have the shotgun) |
| `Q` | Pour acid (after finding it in a chest) |
| `E` or `Space` | Break the cage at the start of a level |
| `Esc` | Pause; `Q` quits while paused |
| `Enter` / `N` | Start screen: continue the saved game / new game |
| `P` | After game over: retry the level with what you had at its start; after the last level: play again |

The hero starts without a gun. Bowls of kımız float in the air like big
coins, one per level: the one in level 1 makes him grow to 1.5x with a short
sparkly effect (the world goes on, the hero hangs still and cannot be hurt).
While big, an enemy hit only shrinks him back instead of costing his life;
dying another way (a pit, the clock) also leaves him small. The one in
level 2 gives the shotgun back for good. Both carry into later levels and are
saved; each bowl is also worth 1000 points. A big hero breaks brick blocks (terrain
ID 3) by jumping into them from below, for 50 points.

Little touches: a stomped or shot goose bursts into feathers, coins and beads
twinkle when picked up, the timer pops in red and the screen edges pulse
through the last ten seconds, the ERDAL BAKKAL sign flickers like neon and the
nazar on its door swings (harder when you run past), the hero raises a kımız
bowl at the goal flag, and once the 33 beads are back the old man's tesbih
lights up bead by bead. They live in `effects.py`.

Touching a checkpoint flag makes it the place to respawn after dying. Chests
open on touch: the shotgun chest gives ammo (kept for later if the hero has
no gun yet), the armor chest gives a nazar bead (it is pinned on the hero's
tank top and shown in the HUD; it stops one enemy hit, then cracks), the acid chest gives three
flasks for `Q`.

Each map gives you 120 seconds from the moment you leave the starting cage.
The HUD shows the remaining seconds under the level name. Pausing and tunnel
transitions freeze the countdown. Running out of time costs a life, and a
checkpoint respawn or level retry starts a fresh 120 seconds.

Level 2 has a white shop in the valley. Stand in the centre doorway and press
`E` to shop. The world and countdown pause. Click an offer or press `1`–`4`
to buy, then press `E` or `Esc` to leave. First aid restores 40 health for
5 coins, and 30 reserve rounds cost 3 coins. Running boots (+20% speed) and
jump boots (+10% jump strength) cost 10 coins each and carry into later levels.
To place another shop, select `shop` under **Dekor** and click the doorway tile.

Golden tesbih beads (13 in every level) are counted under the coins. The old
man at the end of the last level wants 33 of them; with 33 he says the time
to summon "him" is coming (the final boss is planned for a later milestone).
Goblins with long yellow hair walk slowly until the player comes near, then
run at them: stomp on them or, with the shotgun, shoot them twice.

## Levels

Level 0 is the tutorial; the game moves to the next level when the goal flag
is touched. Levels are JSON files in `levels/`, built with the map editor
(`python editor.py 1`). See [levels/README.md](levels/README.md) for the
level list, the editor's keys and the file format.

## Tests

```
python -m unittest discover tests
```

Headless checks of the save file, the level files and the goblin, bead and
old man logic; they take about a second.

## Project layout

| Path | Contents |
| --- | --- |
| `main.py` | Game loop, start screen, level flow, pause, game over and completion screens |
| `save.py` | Local save file: write, load, checks |
| `player.py` | Movement, shooting, kımız powers (growing, the shotgun) and their effects, items, checkpoints and respawning |
| `enemy.py`, `bullet.py`, `acid.py`, `item.py`, `cage.py` | Enemies (goose, tortoise, goblin), projectiles, acid puddles, pickups (coins, beads, kımız), the start cage |
| `game_level.py`, `level_format.py`, `terrain.py` | Level loading, hint signs and the old man, the JSON level format, terrain textures |
| `ui.py` | HUD and floating texts |
| `effects.py` | Sparkles, rings, feathers, coin twinkles and brick debris |
| `editor.py` | Internal map editor (a development tool, not a game feature) |
| `assets.py`, `settings.py`, `globals.py` | Asset loading, constants, shared objects |
| `art/` | Scripts that draw the hero, enemies, decor, objects and some tiles ([art/README.md](art/README.md)) |
| `tiles/` | Terrain textures ([tiles/README.md](tiles/README.md)) |
| `tests/` | Test suite (`python -m unittest discover tests`) |
