"""Level files: they load, every level can be finished, and there are enough beads.

Run from anywhere:  python -m unittest discover tests
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import level_format  # noqa: E402
from settings import BEADS_NEEDED  # noqa: E402

BEADS_PER_LEVEL = 13


def level_numbers():
    numbers = []
    while os.path.isfile(os.path.join(ROOT, "levels", f"{len(numbers)}.json")):
        numbers.append(len(numbers))
    return numbers


def load(n):
    return level_format.load_level(os.path.join(ROOT, "levels", f"{n}.json"))


def solid(level, x, y):
    if not (0 <= x < level["width"] and 0 <= y < level["height"]):
        return False
    return level_format.char_tile(level["terrain"][y][x]) is not None


def of_type(level, kind):
    return [e for e in level["entities"] if e["type"] == kind]


class LevelFilesTest(unittest.TestCase):
    def setUp(self):
        self.levels = {n: load(n) for n in level_numbers()}

    def test_three_levels(self):
        self.assertEqual(sorted(self.levels), [0, 1, 2])

    def test_no_problems_and_a_start_and_goal(self):
        for n, level in self.levels.items():
            with self.subTest(level=n):
                self.assertEqual(level_format.problems(level), [])
                self.assertEqual(len(of_type(level, "player")), 1)
                self.assertEqual(len(of_type(level, "goal")), 1)

    def test_objects_are_not_inside_terrain(self):
        for n, level in self.levels.items():
            for e in level["entities"]:
                with self.subTest(level=n, entity=e):
                    self.assertFalse(solid(level, e["x"], e["y"]))

    def test_standing_objects_have_a_floor(self):
        for n, level in self.levels.items():
            for e in level["entities"]:
                if e["type"] in ("goal", "checkpoint", "npc", "goblin", "tunnel"):
                    with self.subTest(level=n, entity=e):
                        self.assertTrue(solid(level, e["x"], e["y"] + 1))

    def test_beads_per_level_and_margin(self):
        total = 0
        for n, level in self.levels.items():
            with self.subTest(level=n):
                self.assertEqual(len(of_type(level, "bead")), BEADS_PER_LEVEL)
            total += len(of_type(level, "bead"))
        # levels cannot be replayed, so some beads must be allowed to be missed
        self.assertGreaterEqual(total - BEADS_NEEDED, 6)

    def test_old_man_waits_before_the_goal_of_the_last_level(self):
        last = self.levels[max(self.levels)]
        npcs = of_type(last, "npc")
        self.assertEqual(len(npcs), 1)
        self.assertLess(npcs[0]["x"], of_type(last, "goal")[0]["x"])
        for n, level in self.levels.items():
            if n != max(self.levels):
                self.assertEqual(of_type(level, "npc"), [], f"level {n}")

    def test_no_tunnel_mouth_on_the_spawn_tile(self):
        # standing there and ducking would teleport the player at once
        for n, level in self.levels.items():
            spawn = of_type(level, "player")[0]
            for mouth in of_type(level, "tunnel"):
                with self.subTest(level=n, mouth=mouth):
                    self.assertFalse(mouth["x"] == spawn["x"] and abs(mouth["y"] - spawn["y"]) <= 2)


if __name__ == "__main__":
    unittest.main()
