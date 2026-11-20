"""Local save file: fresh launch, restore in a new process, bad data, interrupted writes.

Run from anywhere:  python -m unittest discover tests
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import save  # noqa: E402


def level_exists(n):
    return os.path.isfile(os.path.join(ROOT, "levels", f"{n}.json"))


PROGRESS = {"level": 1, "score": 1230, "coins": 7, "beads": 19}


class SaveFileTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "AnatolianAdventure", "save.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_raw(self, data):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))

    def assert_rejected(self, data):
        self.write_raw(data)
        with contextlib.redirect_stdout(io.StringIO()) as out:  # the warning is expected
            self.assertIsNone(save.load(self.path, level_exists))
        self.assertIn("ignoring the save file", out.getvalue())
        self.assertFalse(os.path.exists(self.path), "an unusable save must not be read again")
        self.assertTrue(os.path.exists(self.path + ".bad"), "the unusable save is kept for inspection")

    def test_first_launch_has_no_save(self):
        self.assertIsNone(save.load(self.path, level_exists))

    def test_round_trip(self):
        self.assertTrue(save.write(PROGRESS, self.path))
        self.assertEqual(save.load(self.path, level_exists), PROGRESS)

    def test_new_process_restores_the_save(self):
        save.write(PROGRESS, self.path)
        code = "import json, save; print(json.dumps(save.load()))"
        env = dict(os.environ, ANATOLIAN_SAVE=self.path)
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out), PROGRESS)

    def test_broken_json(self):
        self.assert_rejected('{"version": 1, "level": ')

    def test_not_an_object(self):
        self.assert_rejected("[1, 2, 3]")

    def test_other_version(self):
        self.assert_rejected({**PROGRESS, "version": 99})

    def test_missing_field(self):
        data = {"version": save.VERSION, **PROGRESS}
        del data["beads"]
        self.assert_rejected(data)

    def test_negative_text_and_boolean_values(self):
        for bad in (-1, "3", True, 2.5, None):
            with self.subTest(bad=bad):
                self.assert_rejected({"version": save.VERSION, **PROGRESS, "coins": bad})
                os.remove(self.path + ".bad")

    def test_level_that_no_longer_exists(self):
        self.assert_rejected({"version": save.VERSION, **PROGRESS, "level": 999})

    def test_interrupted_write_keeps_the_old_save(self):
        save.write(PROGRESS, self.path)
        # a crash during the next write leaves only a half-written temporary file
        with open(self.path + ".tmp", "w", encoding="utf-8") as f:
            f.write('{"version": 1, "lev')
        self.assertEqual(save.load(self.path, level_exists), PROGRESS)
        newer = {**PROGRESS, "level": 2, "beads": 26}
        self.assertTrue(save.write(newer, self.path))
        self.assertEqual(save.load(self.path, level_exists), newer)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_unwritable_place_does_not_crash(self):
        blocker = os.path.join(self.dir, "blocker")
        with open(blocker, "w") as f:
            f.write("a file where a folder should be")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(save.write(PROGRESS, os.path.join(blocker, "save.json")))

    def test_clear(self):
        save.write(PROGRESS, self.path)
        save.clear(self.path)
        self.assertIsNone(save.load(self.path, level_exists))
        save.clear(self.path)  # nothing there: no error

    def test_snapshot_and_apply_use_game_stats_keys(self):
        stats = {"current_level": 2, "score": 5, "coins": 1, "beads": 30, "health_potion_heal": 20}
        progress = save.snapshot(stats)
        self.assertEqual(progress, {"level": 2, "score": 5, "coins": 1, "beads": 30})
        other = {"current_level": 0, "score": 0, "coins": 0, "beads": 0}
        save.apply(progress, other)
        self.assertEqual(other, {"current_level": 2, "score": 5, "coins": 1, "beads": 30})


if __name__ == "__main__":
    unittest.main()
