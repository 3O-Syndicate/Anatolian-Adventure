"""Goblin, beads and the old man, run headless in the real level code.

Run from anywhere:  python -m unittest discover tests
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import globals as G  # noqa: E402
from settings import TILESIZE, BEADS_NEEDED, game_stats  # noqa: E402

FONT = None


def setUpModule():
    global FONT
    os.chdir(ROOT)  # assets are loaded by relative path
    pygame.init()
    G.screen = pygame.display.set_mode((1280, 720))
    import assets
    assets.load_assets()
    FONT = pygame.font.Font("font/PublicPixel.ttf", 20)


def tearDownModule():
    pygame.quit()


class FakeBullet:
    def __init__(self, x_vel):
        self.x_vel = x_vel


class LevelTestCase(unittest.TestCase):
    level = 1

    def setUp(self):
        import main
        game_stats.update(score=0, coins=0, beads=0)
        self.game_level, self.player, self.ui = main.reset_for_new_game(FONT, self.level, keep_score=True)
        self.player.is_caged = False  # skip the start cage
        self.player.invulnerable_timer = 10_000

    def put_player(self, tile_x, floor_row):
        """Stand the player on the floor whose top is row `floor_row`."""
        p = self.player
        p.base_player_rect.midbottom = (tile_x * TILESIZE + TILESIZE // 2, floor_row * TILESIZE)
        p.previous_rect = p.base_player_rect.copy()
        p.vec_pos.update(p.base_player_rect.center)
        p.velocity_x = p.velocity_y = 0
        p.on_ground = True

    def feet(self):
        r = self.player.base_player_rect
        return r.centerx // TILESIZE, r.bottom // TILESIZE

    def step(self, frames=1):
        from enemy import resolve_enemy_collisions
        for _ in range(frames):
            G.all_sprites_group.update()
            resolve_enemy_collisions()
            self.player.check_enemy_collisions()


class PitTest(LevelTestCase):
    def test_camera_stops_at_map_bottom(self):
        from settings import HEIGHT
        level = self.game_level
        bottom = level.floor.get_height()
        self.player.rect.centery = bottom + HEIGHT
        level.snap_camera()
        self.assertEqual(level.offset.y + HEIGHT, bottom)
        level.offset.y -= 100
        for _ in range(180):
            level.update_camera()
        self.assertAlmostEqual(level.offset.y + HEIGHT, bottom, places=1)
        self.assertLessEqual(level.offset.y + HEIGHT, bottom)

    def test_enemies_stop_at_first_pit(self):
        from enemy import WalkingEnemy, TurtleEnemy, GoblinEnemy
        rows = self.game_level.terrain_rows
        gap = rows[-1].index(".")
        floor = next(y for y, row in enumerate(rows) if row[gap - 1] != ".")
        self.put_player(gap + 2, floor)  # lure the goblin across the gap
        for kind in (WalkingEnemy, TurtleEnemy, GoblinEnemy):
            with self.subTest(kind=kind.__name__):
                enemy = kind(((gap - 2) * TILESIZE, (floor - 1) * TILESIZE), direction=1)
                for _ in range(50):
                    enemy.update()
                    self.assertLessEqual(enemy.rect.right, gap * TILESIZE)
                    self.assertEqual(enemy.rect.bottom, floor * TILESIZE)


class GoblinTest(LevelTestCase):
    def goblin(self, tiles_away, direction=-1):
        from enemy import GoblinEnemy
        x, floor = self.feet()
        return GoblinEnemy(((x + tiles_away) * TILESIZE, (floor - 1) * TILESIZE), direction)

    def setUp(self):
        super().setUp()
        for enemy in list(G.enemy_group):
            enemy.kill()  # only the goblins made by the tests
        spawn_x, spawn_y = self.game_level.player_spawn
        self.put_player(spawn_x // TILESIZE, spawn_y // TILESIZE + 1)

    def test_stands_on_its_spawn_floor(self):
        goblin = self.goblin(8)
        self.assertEqual(goblin.rect.bottom, self.player.base_player_rect.bottom)

    def test_runs_at_a_player_who_comes_near(self):
        goblin = self.goblin(4, direction=1)  # walking away from the player
        self.step()
        self.assertTrue(goblin.charging)
        self.assertEqual(goblin.direction, -1)
        self.assertEqual(goblin.speed, goblin.RUN_SPEED)

    def test_ignores_a_far_player_and_gives_up(self):
        goblin = self.goblin(12)
        self.step()
        self.assertFalse(goblin.charging)
        goblin.charge(0)
        self.step()
        self.assertFalse(goblin.charging, "beyond GIVE_UP it calms down")

    def test_two_bullets(self):
        goblin = self.goblin(12)
        goblin.on_bullet_hit(FakeBullet(10))
        self.assertTrue(goblin.alive())
        self.assertTrue(goblin.charging, "the first bullet makes it run at the shooter")
        self.assertEqual(goblin.direction, -1)
        goblin.on_bullet_hit(FakeBullet(10))
        self.assertFalse(goblin.alive())
        self.assertEqual(game_stats["score"], goblin.SCORE)

    def test_stomp_from_above(self):
        goblin = self.goblin(3)
        goblin.look_for_player = lambda: None  # keep it standing still
        goblin.speed = 0
        p = self.player
        p.base_player_rect.midbottom = (goblin.rect.centerx, goblin.rect.top - 30)
        p.velocity_y = 2
        for _ in range(20):
            p.update()
            self.step()
            if not goblin.alive():
                break
        self.assertFalse(goblin.alive())
        self.assertLess(p.velocity_y, 0, "the player bounces off")


class BeadTest(LevelTestCase):
    def test_pickup_counts_and_survives_a_respawn(self):
        from item import Item
        x, floor = self.feet()
        bead = Item(self.player.base_player_rect.center, "bead")
        self.step()
        self.assertFalse(bead.alive())
        self.assertEqual(game_stats["beads"], 1)

        checkpoint = self.game_level.checkpoints[0]
        self.game_level.last_checkpoint = checkpoint
        self.player.respawn(checkpoint.rect.midbottom)
        self.step()
        self.assertEqual(game_stats["beads"], 1, "collected beads stay collected")
        self.assertFalse(bead.alive())

    def test_level_holds_its_beads(self):
        beads = [s for s in G.items_group if s.type == "bead"]
        self.assertEqual(len(beads), 13)


class OldManTest(LevelTestCase):
    level = 2

    def test_speech_follows_the_bead_count(self):
        npc = self.game_level.npc
        self.assertIsNotNone(npc)
        x = npc.anchor[0] // TILESIZE
        self.put_player(x - 2, npc.anchor[1] // TILESIZE)

        game_stats["beads"] = 30
        self.step()
        self.assertTrue(npc.near)
        self.assertIn("3 tane daha", npc.speech(30))
        self.assertFalse(npc.greeted)
        self.assertEqual(game_stats["score"], 0)

        game_stats["beads"] = BEADS_NEEDED
        self.step(3)
        self.assertTrue(npc.greeted)
        self.assertEqual(game_stats["score"], 500, "the reward is given once")
        self.assertIn("tamam", npc.speech(BEADS_NEEDED))

    def test_goal_after_the_old_man_finishes_the_level(self):
        goal = self.game_level.goal
        self.put_player(goal.rect.x // TILESIZE, goal.rect.bottom // TILESIZE)
        self.player.update()
        self.assertTrue(self.game_level.level_completed)


if __name__ == "__main__":
    unittest.main()
