"""Run Anatolian Adventure: levels in order, saving, pause screen, game over, completion and restart."""
import os
import sys
import pygame
import globals as G
from settings import WIDTH, HEIGHT, FPS, WHITE, YELLOW, RED, BLACK, BEADS_NEEDED, game_stats
from player import Player
from ui import UI, level_name
from button import Button
from game_level import GameLevel
from enemy import resolve_enemy_collisions
import assets
import save
from cage import Cage


class BandWipe:
    """Cover the outgoing frame in five strips, then uncover the incoming frame."""

    def __init__(self, screen, opening_only=False):
        self.outgoing = None if opening_only else screen.copy()
        self.incoming = None
        self.elapsed = 0

    def draw(self, screen, dt):
        if self.incoming is None:
            self.incoming = screen.copy()
        width, height = screen.get_size()
        duration = 300  # milliseconds per phase
        closing = self.outgoing is not None and self.elapsed < duration
        phase_time = self.elapsed if closing or self.outgoing is None else self.elapsed - duration
        fraction = min(1, phase_time / duration)
        screen.blit(self.outgoing if closing else self.incoming, (0, 0))
        for band in range(5):
            top = band * height // 5
            bottom = (band + 1) * height // 5
            edge = top + round((bottom - top) * fraction)
            rect = (0, top, width, edge - top) if closing else (0, edge, width, bottom - edge)
            screen.fill(BLACK, rect)
        self.elapsed += dt
        if closing:
            self.elapsed = min(self.elapsed, duration)
        return not closing and fraction == 1


def create_game_objects(font):
    game_level = GameLevel(game_stats["current_level"])
    G.game_level = game_level
    player = Player(game_level.player_spawn)
    G.player = player
    G.all_sprites_group.add(player)
    prompt_font = pygame.font.Font("font/PublicPixel.ttf", 11)
    cage = Cage(player, prompt_font)
    G.cage = cage
    player.cage = cage
    ui = UI(font)
    G.ui = ui
    return game_level, player, ui


def reset_for_new_game(font, start_level=0, keep_score=False):
    """Clear the old session before creating fresh map, player, and HUD objects.

    keep_score=False starts the score and coins from zero. main() keeps them
    and sets them itself: the next level carries them on, a new game zeroes
    them, a retry after game over restores what the player had at the start
    of the level.
    """
    for sprite in list(G.all_sprites_group):
        sprite.kill()
    G.bullet_group.empty()
    G.items_group.empty()
    G.enemy_group.empty()
    game_stats["current_level"] = start_level
    if not keep_score:
        game_stats.update(coins=0, score=0, beads=0)
    return create_game_objects(font)


def has_level(level_num):
    return os.path.isfile(f"levels/{level_num}.json")


def start_level_from_args(args):
    """`python main.py --level 2` starts and restarts on level 2 (the map editor's F5).

    Such test runs never read or write the save, so playtesting a map cannot
    overwrite the player's progress.
    """
    if "--level" in args:
        return int(args[args.index("--level") + 1])
    return None


def main():
    test_level = start_level_from_args(sys.argv[1:])
    test_run = test_level is not None
    game_stats["current_level"] = test_level or 0
    saved = None if test_run else save.load(level_exists=has_level)
    pygame.init()
    pygame.mixer.init()
    G.screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Anatolian Adventure")
    clock = pygame.time.Clock()
    font = pygame.font.Font("font/PublicPixel.ttf", 20)
    title_font = pygame.font.Font("font/PublicPixel.ttf", 50)
    assets.load_assets()
    assets.play_bgm()
    volume_image = pygame.image.load("sounds/volume_icon.jpg").convert_alpha()
    volume_button = Button(WIDTH - 70, 20, volume_image, 0.05)
    game_active = True
    game_paused = False
    game_finished = False  # the last level's goal was reached
    in_menu = saved is not None  # "continue or new game?" before anything is built
    game_level = player = ui = None
    wipe = None
    level_start = save.snapshot(game_stats)  # stats a retry after game over returns to

    def start_level(level_num, opening_only=False):
        """Build a level with the stats the player has now; this is the save point."""
        nonlocal game_level, player, ui, level_start, wipe
        wipe = BandWipe(G.screen, opening_only)
        game_level, player, ui = reset_for_new_game(font, level_num, keep_score=True)
        game_level.snap_camera()
        level_start = save.snapshot(game_stats)
        if not test_run:
            save.write(level_start)

    def start_new_game():
        game_stats.update(coins=0, score=0, beads=0)
        start_level(0)

    if not in_menu:
        start_level(game_stats["current_level"], opening_only=True)

    def display_start_menu():
        G.screen.fill(BLACK)
        for text, text_font, color, y in (
            ("Anatolian Adventure", title_font, YELLOW, 170),
            (f"Kayıtlı oyun: {level_name(saved['level'])}", font, WHITE, 290),
            (f"Skor {saved['score']:,}   Altın {saved['coins']}   Boncuk {saved['beads']}/{BEADS_NEEDED}",
             font, WHITE, 330),
            ("Devam etmek için Enter", font, YELLOW, 430),
            ("Yeni oyun için N", font, WHITE, 480),
        ):
            surface = text_font.render(text, True, color)
            G.screen.blit(surface, surface.get_rect(center=(WIDTH // 2, y)))

    def display_level_cleared_banner():
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 90))
        G.screen.blit(overlay, (0, 0))
        cleared_text = title_font.render("Bölüm geçildi!", True, YELLOW)
        G.screen.blit(cleared_text, cleared_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30)))
        last = not has_level(game_stats["current_level"] + 1)
        next_text = font.render("Son bölümdü!" if last else "Sıradaki bölüm yükleniyor...", True, WHITE)
        G.screen.blit(next_text, next_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

    def display_end_screen():
        """Game over, or the completion screen after the last level."""
        G.screen.fill(BLACK)
        if game_finished:
            lines = (("Tebrikler!", title_font, YELLOW, 110),
                     ("Bütün bölümleri bitirdin", font, WHITE, 190))
            again = "Baştan oynamak için P"
        else:
            lines = (("Oyun bitti", title_font, WHITE, 110),)
            again = "Bu bölümü tekrar denemek için P"
        lines += (("Skorun:", font, WHITE, 290),
                  (f"{game_stats['score']:,}", title_font, WHITE, 360),
                  (f"Altın: {game_stats['coins']}   Boncuk: {game_stats['beads']}/{BEADS_NEEDED}",
                   font, (255, 223, 91), 430),
                  (again, font, YELLOW, HEIGHT * 7 // 8))
        for text, text_font, color, y in lines:
            surface = text_font.render(text, True, color)
            G.screen.blit(surface, surface.get_rect(center=(WIDTH // 2, y)))

    def display_pause_screen():
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        G.screen.blit(overlay, (0, 0))
        if volume_button.draw(G.screen):
            assets.update_sound_volume(round((G.sound_volume + 0.25) % 1.25, 2))
        for text, text_font, color, y in (
            ("Duraklatıldı", title_font, WHITE, HEIGHT // 2 - 50),
            ("Devam etmek için ESC", font, YELLOW, HEIGHT // 2 + 20),
            ("Oyundan çıkmak için Q", font, RED, HEIGHT // 2 + 60),
        ):
            surface = text_font.render(text, True, color)
            G.screen.blit(surface, surface.get_rect(center=(WIDTH // 2, y)))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if wipe is not None:
                continue
            if event.type == pygame.KEYDOWN and in_menu:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    save.apply(saved, game_stats)
                    start_level(saved["level"])
                    in_menu = False
                elif event.key == pygame.K_n:
                    save.clear()
                    start_new_game()
                    in_menu = False
            elif event.type == pygame.KEYDOWN:
                if game_active and game_level.level_completed:
                    continue
                if game_active and not game_paused and player.is_caged and (event.key == pygame.K_e or event.key == pygame.K_SPACE):
                    if player.cage and not player.cage.is_broken:
                        player.cage.break_open()
                elif game_active and event.key == pygame.K_ESCAPE:
                    game_paused = not game_paused
                    try:
                        vol = 0.1 if game_paused else 0.25
                        pygame.mixer.music.set_volume(G.sound_volume * vol)
                    except Exception:
                        pass
                elif game_active and game_paused and event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
                elif not game_active and event.key == pygame.K_p:
                    if game_finished:
                        start_new_game()
                    else:
                        # back to the start of this level with what the player had there
                        save.apply(level_start, game_stats)
                        start_level(level_start["level"])
                    game_active = True
                    game_paused = False
                    game_finished = False
                    assets.play_bgm()

        if wipe is not None and wipe.incoming is not None:
            pass  # The wipe draws its frozen frames below.
        elif in_menu:
            display_start_menu()
        elif game_active:
            if not game_paused and wipe is None:
                if game_level.level_completed:
                    game_level.level_clear_timer += 1
                    if game_level.level_clear_timer >= 90:
                        next_lvl = game_stats["current_level"] + 1
                        if has_level(next_lvl):
                            start_level(next_lvl)
                        else:
                            wipe = BandWipe(G.screen)
                            game_active = False
                            game_finished = True
                            if not test_run:
                                save.clear()
                            try:
                                pygame.mixer.music.fadeout(800)
                            except pygame.error:
                                pass
                elif player.health > 0:
                    for sprite in G.all_sprites_group.sprites():
                        sprite.update()
                        if game_level.level_completed:
                            break
                    if not game_level.level_completed:
                        if player.entered_tunnel:
                            wipe = BandWipe(G.screen)
                        resolve_enemy_collisions()
                        player.check_enemy_collisions()
                        game_level.update_camera()
                else:
                    player.update()  # death animation; the world waits for it
                if player.death_finished and game_level.last_checkpoint is not None:
                    wipe = BandWipe(G.screen)
                    player.respawn(game_level.last_checkpoint.rect.midbottom)
                    game_level.snap_camera()
                elif player.death_finished:
                    wipe = BandWipe(G.screen)
                    game_active = False
                    try:
                        pygame.mixer.music.fadeout(800)
                    except Exception:
                        pass
            if game_active:
                game_level.draw()
                ui.update()
                if game_level.level_completed:
                    display_level_cleared_banner()
                elif game_paused:
                    display_pause_screen()
            else:
                display_end_screen()
        else:
            display_end_screen()
        if wipe is not None and wipe.draw(G.screen, clock.get_time()):
            wipe = None
        pygame.display.set_caption(
            f"Anatolian Adventure | FPS: {clock.get_fps():.0f} | Skor: {game_stats['score']}"
        )
        pygame.display.update()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
