import copy
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from editor import Editor, SCREEN_H, SCREEN_W, TILESIZE


class RegionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_shift_each_map_right(self):
        for number in range(3):
            with self.subTest(level=number):
                editor = Editor(number, self.screen)
                before = copy.deepcopy(editor.level)
                editor.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=pygame.KMOD_CTRL))
                editor.cut_region()
                editor.paste_region((10, 0))
                self.assertIsNotNone(editor.clipboard)
                editor.change(lambda: editor.resize(10, 0))
                editor.paste_region((10, 0))
                self.assertEqual(editor.level["terrain"], ["." * 10 + row for row in before["terrain"]])
                for layer in ("entities", "decor"):
                    self.assertEqual(editor.level[layer], [dict(e, x=e["x"] + 10) for e in before[layer]])
                editor.undo()
                self.assertIsNotNone(editor.clipboard)
                editor.undo()
                editor.undo()
                self.assertEqual(editor.level, before)
                for _ in range(3):
                    editor.redo()
                self.assertEqual(editor.level["width"], before["width"] + 10)
                self.assertIsNone(editor.clipboard)

    def test_reverse_drag_and_overlapping_paste(self):
        editor = Editor(0, self.screen)
        editor.offset.update(0, 0)
        editor.level["terrain"][0] = "1234" + editor.level["terrain"][0][4:]
        editor.level["entities"] = [dict(type="hint", text="merhaba", x=1, y=0),
                                    dict(type="coin", x=3, y=0)]
        def key(code, mod=0):
            editor.handle_event(pygame.event.Event(pygame.KEYDOWN, key=code, mod=mod))

        key(pygame.K_m)
        editor.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(2 * TILESIZE, 0), button=1))
        editor.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(0, 0), button=1))
        key(pygame.K_x, pygame.KMOD_CTRL)
        with patch("pygame.mouse.get_pos", return_value=(TILESIZE, 0)):
            editor.draw()
            key(pygame.K_v, pygame.KMOD_CTRL)
        self.assertEqual(editor.level["terrain"][0][:4], ".123")
        self.assertEqual(editor.level["entities"], [dict(type="hint", text="merhaba", x=2, y=0)])
