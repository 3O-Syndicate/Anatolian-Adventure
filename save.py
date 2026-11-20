"""
save.py

Local progress save: the level to resume and what the player carries from
one level to the next. The game writes it when a level starts, so resuming
puts the player at the start of the level they reached.

The file is small JSON in the user's application data folder:
    Windows   %APPDATA%/AnatolianAdventure/save.json
    other     ~/.local/share/AnatolianAdventure/save.json
The ANATOLIAN_SAVE environment variable points the game (and the tests)
at another file.

Writing goes to a temporary file first and then replaces the save in one
step, so an interrupted write leaves the previous save intact. A file that
cannot be used (bad JSON, another version, missing or wrong fields, a level
that no longer exists) is renamed to save.json.bad and the game starts fresh.
"""
import json
import os

VERSION = 1
# progress field -> key in settings.game_stats
FIELDS = {"level": "current_level", "score": "score", "coins": "coins", "beads": "beads"}


def default_path():
    override = os.environ.get("ANATOLIAN_SAVE")
    if override:
        return override
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "AnatolianAdventure", "save.json")


def snapshot(stats):
    """The progress fields of a game_stats dict."""
    return {field: stats[key] for field, key in FIELDS.items()}


def apply(progress, stats):
    """Copy loaded progress into a game_stats dict."""
    for field, key in FIELDS.items():
        stats[key] = progress[field]


def problem(data, level_exists=None):
    """Why a loaded file cannot be used, or None when it is a valid save."""
    if not isinstance(data, dict):
        return "not a JSON object"
    if data.get("version") != VERSION:
        return f"version {data.get('version')!r}, expected {VERSION}"
    for field in FIELDS:
        value = data.get(field)
        # bool is an int in Python; true/false is not a count
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return f"{field} is {value!r}, expected a whole number >= 0"
    if level_exists is not None and not level_exists(data["level"]):
        return f"level {data['level']} does not exist"
    return None


def load(path=None, level_exists=None):
    """The saved progress as {field: value}, or None when there is nothing usable.

    level_exists(n) -> bool checks that the saved level is still in the game.
    """
    path = path or default_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as error:
        set_aside(path, f"unreadable: {error}")
        return None
    reason = problem(data, level_exists)
    if reason:
        set_aside(path, reason)
        return None
    return {field: data[field] for field in FIELDS}


def write(progress, path=None):
    """Save progress; returns False (and the game goes on) if the disk refuses."""
    path = path or default_path()
    data = {"version": VERSION, **{field: progress[field] for field in FIELDS}}
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return True
    except OSError as error:
        print(f"Warning: could not save progress to {path}: {error}")
        return False


def clear(path=None):
    """Forget the save (a new game, or the last level finished)."""
    path = path or default_path()
    for name in (path, path + ".tmp"):
        try:
            os.remove(name)
        except FileNotFoundError:
            pass
        except OSError as error:
            print(f"Warning: could not remove {name}: {error}")


def set_aside(path, reason):
    """Keep an unusable save as <path>.bad for inspection, so it is not read again."""
    print(f"Warning: ignoring the save file {path} ({reason}); starting a new game.")
    try:
        os.replace(path, path + ".bad")
    except OSError:
        pass
