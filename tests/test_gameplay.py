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
        game_stats.pop("powers", None)
        game_stats.pop("shop_upgrades", None)
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


class ShopTest(LevelTestCase):
    level = 2

    def test_valley_doorway_and_purchases(self):
        shop = self.game_level.shop
        building, = shop.buildings
        self.assertTrue(self.game_level.solid_at_pixel(building.centerx, building.bottom))
        self.player.base_player_rect.midbottom = building.midbottom
        self.player.on_ground = True
        game_stats["coins"] = 28
        self.player.get_damage(50)
        reserve = self.player.total_ammo
        self.assertTrue(shop.try_open(self.player))
        for index in range(4):
            self.assertTrue(shop.buy(index))
        self.assertEqual(self.player.health, 90)
        self.assertEqual(self.player.total_ammo, reserve + 30)
        self.assertEqual(self.player.run_speed, 12)
        self.assertEqual(game_stats["coins"], 0)
        self.assertFalse(shop.buy(1))
        game_stats["coins"] = 10
        self.assertFalse(shop.buy(2))
        self.assertEqual(game_stats["coins"], 10)
        shop.close()


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


class KimizBase(LevelTestCase):
    """Level 1 a few tiles right of the start cage, without its enemies and items."""

    def setUp(self):
        super().setUp()
        for sprite in [*G.enemy_group, *G.items_group]:
            sprite.kill()  # only the bowls and geese made by the tests
        spawn_x, spawn_y = self.game_level.player_spawn
        # a few tiles right of the start cage, which turns walking enemies round
        self.put_player(spawn_x // TILESIZE + 5, spawn_y // TILESIZE + 1)

    def tearDown(self):
        game_stats.pop("powers", None)

    def drink(self, power):
        from item import Item
        bowl = Item(self.player.base_player_rect.center, "kimiz", power)
        self.step()
        self.assertFalse(bowl.alive())


class KimizTest(KimizBase):
    def test_one_bowl_in_levels_1_and_2(self):
        import level_format
        for level, power in ((1, "big"), (2, "gun")):
            bowls = [e for e in level_format.load_level(f"levels/{level}.json")["entities"]
                     if e["type"] == "kimiz"]
            self.assertEqual([b["power"] for b in bowls], [power], f"level {level}")

    def test_starts_small_without_a_gun(self):
        from player import hero_frames
        p = self.player
        self.assertFalse(p.has_gun)
        self.assertFalse(p.is_big)
        self.assertEqual(p.base_player_rect.size, (24, 56))
        unarmed, _ = hero_frames(False, 1.0)
        self.assertIn(p.image, unarmed[p.anim_name], "drawn from the gunless frames")

    def test_grows_with_the_effect_then_stays_big(self):
        from player import GROW_TICKS
        p = self.player
        feet = p.base_player_rect.midbottom
        self.drink("big")
        self.assertGreater(p.grow_timer, 0)
        self.assertEqual(game_stats["score"], 1000)
        self.step(GROW_TICKS + 2)
        self.assertEqual(p.grow_timer, 0)
        self.assertTrue(p.is_big)
        self.assertEqual(p.base_player_rect.size, (36, 84))
        self.assertEqual(p.base_player_rect.midbottom, feet, "grows upwards from the feet")
        self.assertEqual(p.image.get_height(), 96)
        self.assertEqual(game_stats["powers"], ["big"])

    def test_a_hit_while_big_only_shrinks(self):
        from enemy import WalkingEnemy
        from player import GROW_TICKS
        p = self.player
        self.drink("big")
        self.step(GROW_TICKS + 2)
        p.invulnerable_timer = 0
        x, floor = self.feet()
        goose = WalkingEnemy(((x + 1) * TILESIZE, (floor - 1) * TILESIZE), -1)
        goose.direction = -1  # walk straight into the player
        goose.position.x = goose.rect.x = p.base_player_rect.right + 2
        for _ in range(30):
            self.step()
            if not p.is_big:
                break
        self.assertFalse(p.is_big)
        self.assertEqual(p.health, 100)
        self.assertEqual(p.base_player_rect.size, (24, 56))
        self.assertNotIn("big", game_stats.get("powers", []))
        self.assertGreater(p.invulnerable_timer, 0)
        self.assertTrue(goose.alive())

    def test_gun_bowl_gives_the_shotgun(self):
        from player import hero_frames
        p = self.player
        self.drink("gun")
        self.assertTrue(p.has_gun)
        p.invulnerable_timer = 0  # no blinking copy of the frame
        self.step()
        armed, _ = hero_frames(True, 1.0)
        self.assertIn(p.image, armed[p.anim_name])
        p.is_shooting = True
        self.assertTrue(p.shoot())

    def test_respawn_is_small(self):
        from player import GROW_TICKS
        self.drink("big")
        self.step(GROW_TICKS + 2)
        checkpoint = self.game_level.checkpoints[0]
        self.player.respawn(checkpoint.rect.midbottom)
        self.assertFalse(self.player.is_big)
        self.assertNotIn("big", game_stats.get("powers", []))


if __name__ == "__main__":
    unittest.main()


class LittleTouchesTest(KimizBase):
    def make_big(self):
        from player import GROW_TICKS
        self.drink("big")
        self.step(GROW_TICKS + 2)
        self.player.invulnerable_timer = 10_000

    def test_big_head_breaks_a_brick_small_head_does_not(self):
        rows = self.game_level.terrain_rows
        # the floating bricks at (29..33, 25) over the start floor (top row 29)
        self.assertEqual(rows[25][30], "3")
        for big in (False, True):
            with self.subTest(big=big):
                if big:
                    self.make_big()
                self.put_player(30, 29)
                self.player.velocity_y = -20
                self.player.on_ground = False
                bricks = len(G.obstacles_group)
                for _ in range(12):
                    self.player.move()
                broken = len(G.obstacles_group) < bricks
                self.assertEqual(broken, big)
                self.assertEqual(rows[25][30] == ".", big)

    def test_goose_leaves_feathers(self):
        from effects import Feather
        from enemy import WalkingEnemy
        x, floor = self.feet()
        goose = WalkingEnemy(((x + 3) * TILESIZE, (floor - 1) * TILESIZE), -1)
        goose.on_stomp(self.player)
        self.assertTrue(any(isinstance(s, Feather) for s in G.all_sprites_group))

    def test_victory_pose_after_the_goal(self):
        p = self.player
        p.base_player_rect.midbottom = self.game_level.goal.rect.midbottom
        self.assertTrue(p.reached_goal())
        for _ in range(30):
            p.update_victory()
        self.assertEqual(p.anim_name, "victory")

    def test_neon_sign_mostly_lit(self):
        from shop import Shop
        lit = sum(Shop.neon_lit(ms) for ms in range(0, 4000, 10))
        self.assertTrue(300 < lit < 400)


class ShopNeonTest(LevelTestCase):
    level = 2

    def test_sign_letters_found(self):
        shop = self.game_level.shop
        self.assertIsNotNone(shop.neon)
        self.assertGreater(shop.neon.get_bounding_rect().width, 60, "ERDAL BAKKAL spans the board")
        self.assertIsNotNone(shop.nazar)

    def test_tesbih_beads_sit_on_the_elder(self):
        npc = self.game_level.npc
        for x, y in npc.bead_positions():
            self.assertTrue(npc.rect.collidepoint(x, y))


class NazarTest(KimizBase):
    def test_bead_blocks_a_hit_and_cracks(self):
        from effects import Debris
        from enemy import WalkingEnemy
        p = self.player
        p.take_item("armor", p.rect.center)
        self.assertEqual(p.armor, 1)
        p.invulnerable_timer = 0
        x, floor = self.feet()
        goose = WalkingEnemy(((x + 1) * TILESIZE, (floor - 1) * TILESIZE), -1)
        goose.direction = -1
        goose.position.x = goose.rect.x = p.base_player_rect.right + 2
        for _ in range(30):
            self.step()
            if p.armor == 0:
                break
        self.assertEqual(p.armor, 0)
        self.assertEqual(p.health, 100)
        self.assertTrue(any(isinstance(s, Debris) for s in G.all_sprites_group), "the halves fly off")

