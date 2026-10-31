"""Run Anatolian Adventure's test level, pause screen, and restart flow."""
import sys
import pygame
import globals as G
from settings import WIDTH, HEIGHT, FPS, WHITE, YELLOW, RED, BLACK, game_stats
from player import Player
from ui import UI
from button import Button
from game_level import GameLevel
from enemy import resolve_enemy_collisions
import assets
from cage import Cage


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


def reset_for_new_game(font):
    """Clear the old session before creating fresh map, player, and HUD objects."""
    for sprite in list(G.all_sprites_group):
        sprite.kill()
    G.bullet_group.empty()
    G.items_group.empty()
    G.enemy_group.empty()
    game_stats.update(coins=0, score=0, current_level=0)
    return create_game_objects(font)


def main():
    pygame.init()
    pygame.mixer.init()
    G.screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Anatolian Adventure")
    clock = pygame.time.Clock()
    font = pygame.font.Font("font/PublicPixel.ttf", 20)
    title_font = pygame.font.Font("font/PublicPixel.ttf", 50)
    assets.load_assets()
    game_level, player, ui = create_game_objects(font)
    volume_image = pygame.image.load("sounds/volume_icon.jpg").convert_alpha()
    volume_button = Button(WIDTH - 70, 20, volume_image, 0.05)
    game_active = True
    game_paused = False

    def display_end_screen():
        G.screen.fill(BLACK)
        G.screen.blit(title_font.render("GAME OVER", True, WHITE), (350, 50))
        G.screen.blit(font.render("Your score:", True, WHITE), (550, 150))
        G.screen.blit(title_font.render(f"{game_stats['score']:,}", True, WHITE), (550, 250))
        text = font.render("Press 'P' to play again", True, YELLOW)
        G.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT * 7 // 8)))

    def display_pause_screen():
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        G.screen.blit(overlay, (0, 0))
        if volume_button.draw(G.screen):
            assets.update_sound_volume(round((G.sound_volume + 0.25) % 1.25, 2))
        for text, text_font, color, y in (
            ("PAUSED", title_font, WHITE, HEIGHT // 2 - 50),
            ("Press 'ESC' to Resume", font, YELLOW, HEIGHT // 2 + 20),
            ("Press 'Q' to Quit Game", font, RED, HEIGHT // 2 + 60),
        ):
            surface = text_font.render(text, True, color)
            G.screen.blit(surface, surface.get_rect(center=(WIDTH // 2, y)))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if game_active and not game_paused and player.is_caged and (event.key == pygame.K_e or event.key == pygame.K_SPACE):
                    if player.cage and not player.cage.is_broken:
                        player.cage.break_open()
                elif game_active and event.key == pygame.K_ESCAPE:
                    game_paused = not game_paused
                elif game_active and game_paused and event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
                elif not game_active and event.key == pygame.K_p:
                    game_level, player, ui = reset_for_new_game(font)
                    game_active = True
                    game_paused = False

        if game_active:
            if not game_paused:
                G.all_sprites_group.update()
                resolve_enemy_collisions()
                player.check_enemy_collisions()
                game_level.update_camera()
                if player.health <= 0:
                    game_active = False
            if game_active:
                game_level.draw()
                ui.update()
                if game_paused:
                    display_pause_screen()
            else:
                display_end_screen()
        else:
            display_end_screen()
        pygame.display.set_caption(
            f"Anatolian Adventure | FPS: {clock.get_fps():.0f} | Score: {game_stats['score']}"
        )
        pygame.display.update()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
