"""
main.py

Project: Anatolian Adventure
Description:
	This is the main entry point for the application. It orchestrates the game loop,
	manages global game states (Start Menu, Gameplay, Pause, Game Over), and handles
	core initialization of Pygame modules and assets.

Key Responsibilities:
	- Initializing Pygame and loading assets.
	- Managing the main while-loop.
	- Handling user input for state transitions.
	- Rendering the appropriate screen based on the current game state.
"""
import sys
import pygame
from sys import exit
import random
import globals as G
from settings import *

# Import game modules
from player import Player
from ui import UI
from button import Button
from game_level import GameLevel
import assets

# Ensure other modules are registered
import bullet  # noqa: F401
import item    # noqa: F401

def create_game_objects(font):
	"""
	Instantiates the core game objects: Level, Player, and UI.
	Registers them into the global state manager.
	"""
	game_level = GameLevel(game_stats["current_level"])
	G.game_level = game_level

	player = Player(game_level.player_spawn)
	G.player = player
	G.all_sprites_group.add(player)

	ui = UI(font)
	G.ui = ui

	return game_level, player, ui

def reset_for_new_game(level_num, full_reset):
	global game_level
	"""
	Resets game statistics and entities to their initial state for a new session.
	"""
	game_stats["current_wave"] = 1
	game_stats["current_level"] = level_num
	game_stats["enemies_killed_or_removed"] = 0
	game_level = GameLevel(level_num)
	G.game_level = game_level
	G.player.base_player_rect = G.player.base_player_image.get_rect(center=game_level.player_spawn)

	# Clear dynamic sprites
	for sprite in list(G.enemy_group):
		sprite.kill()
	for sprite in list(G.items_group):
		sprite.kill()

	if full_reset == True:
		game_stats["coins"] = 0
		game_stats["score"] = 0
		game_stats["current_level"] = 0
		G.player.health = 100
		G.ui.current_health = 100

	# Respawn entities
	game_level.spawn_enemies()
	game_level.spawn_health_potions()
	return game_level

def main():
	# --- Initialization ---
	pygame.init()
	pygame.mixer.init()

	# Window Setup
	G.screen = pygame.display.set_mode((WIDTH, HEIGHT))
	G.WIDTH = WIDTH
	G.HEIGHT = HEIGHT
	pygame.display.set_caption('Campus Mayhem')

	# Timing & Fonts
	clock = pygame.time.Clock()
	font = pygame.font.Font("font/PublicPixel.ttf", 20)
	title_font = pygame.font.Font("font/PublicPixel.ttf", 50)
	score_font = pygame.font.Font("font/PublicPixel.ttf", 50)

	# Asset Loading
	assets.load_assets()

	# Object Creation
	game_level, player, ui = create_game_objects(font)

	# --- Preload Static Assets for Screens ---
	try:
		coin_image = pygame.image.load("items/coin/0.png").convert_alpha()
		coin_image = pygame.transform.rotozoom(coin_image, 0, 4)
		coin_image_rect = coin_image.get_rect(center=(215,540))
	except Exception:
		coin_image = pygame.Surface((64,64)); coin_image.fill((255,223,91))
		coin_image_rect = coin_image.get_rect(center=(215,540))

	start_time = 0

	# --- Game State Variables ---
	game_started = False  # Start Screen active
	game_active = False   # Gameplay active
	game_paused = False   # Pause Overlay active
	beat_game = False
	level_done = False

	current_time = 0
	level_over_time = 0
	ready_to_spawn = False
	display_countdown_time = False

	def display_end_screen(score):
		"""Renders the Game Over or Victory screen."""
		G.screen.fill((0,0,0))
		# G.screen.blit(necromancer_image, necromancer_image_rect)
		# G.screen.blit(nightborne_image, nightborne_image_rect)
		G.screen.blit(coin_image, coin_image_rect)
		if beat_game:
			beat_game_surface = font.render("You Win! Thanks for playing!", True, WHITE)
			G.screen.blit(beat_game_surface, (300, 50))
		else:
			game_over_surface = title_font.render("GAME OVER", True, WHITE)
			G.screen.blit(game_over_surface, (350, 50))

		text_surface = font.render("> Press 'P' to play again", True, YELLOW)

		# text_1 = font.render(f"You killed:", True, WHITE)
		# text_2 = font.render(f"{game_stats['necromancer_death_count']} x", True, WHITE)
		# text_3 = font.render(f"{game_stats['nightborne_death_count']} x", True, WHITE)
		# text_4 = font.render(f"You collected:", True, WHITE)
		# text_5 = font.render(f"{game_stats['coins']} x", True, WHITE)

		# G.screen.blit(text_surface, (WIDTH / 2 - 150, HEIGHT * 7 / 8))
		# G.screen.blit(text_1, (100, 150))
		# G.screen.blit(text_2, (100, 250))
		# G.screen.blit(text_3, (100, 350))
		# G.screen.blit(text_4, (100, 450))
		# G.screen.blit(text_5, (100, 530))
		score_text_1 = font.render(f"Your score:", False, WHITE)
		score_text_2 = score_font.render(f"{score:,}", False, WHITE)
		G.screen.blit(score_text_1, (550, 150))
		G.screen.blit(score_text_2, (550, 250))

	def display_pause_screen():
		"""Renders a semi-transparent overlay when the game is paused."""
		overlay = pygame.Surface((WIDTH, HEIGHT))
		overlay.set_alpha(150) # Transparency level
		overlay.fill(BLACK)
		G.screen.blit(overlay, (0, 0))

		# volume set button
		volume_button_img = pygame.image.load("sounds/volume_icon.jpg").convert_alpha()
		volume_button = Button(WIDTH - 70, 20, volume_button_img, 0.05)
		volume_button.draw(G.screen)
		if volume_button.clicked:
			G.sound_volume = random.randint(0, 100) / 100
			assets.update_sound_volume(G.sound_volume)
			print(G.sound_volume)

		pause_surf = title_font.render("PAUSED", True, WHITE)
		pause_rect = pause_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))

		info_surf = font.render("Press 'ESC' to Resume", True, YELLOW)
		info_rect = info_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))

		quit_surf = font.render("Press 'Q' to Quit Game", True, RED)
		quit_rect = quit_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))

		G.screen.blit(pause_surf, pause_rect)
		G.screen.blit(info_surf, info_rect)
		G.screen.blit(quit_surf, quit_rect)

	# --- Main Loop ---
	while True:
		current_time = pygame.time.get_ticks()
		if G.player.health <= 0 and game_active:
			game_active = False

		keys = pygame.key.get_pressed()
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				pygame.quit()
				sys.exit()

			# Input: Main Menu
			if not game_started:
				if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
					game_started = True
					game_active = True
					start_time = pygame.time.get_ticks()


			# Input: Pause Toggle
			elif game_active:
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						game_paused = not game_paused
					if game_paused and event.key == pygame.K_q:
						pygame.quit()
						sys.exit()

			# Input: Restart Game
			if game_started and not game_active and keys[pygame.K_p]:
				game_active = True
				game_paused = False
				start_time = pygame.time.get_ticks()
				reset_for_new_game(0, True)

		# --- State Handling ---
		if not game_started:
			game_started = 1
			game_active = 1

		elif game_active:
			# Render Game World (Camera & UI)
			game_level.draw() # Render level
			ui.update() # Render HUD

			# Update Logic (Only when not paused)
			if not game_paused:
				G.all_sprites_group.update()

				# Wave Management
				if level_done: # All waves are done, can go to next level.
					if game_level.next_lvl_trigger_invoked:
						level_done = False
						# Going to next level...
						# Fade screen to black
						for i in range(1,148,4):
							for j in range(5):
								rect = pygame.rect.Rect(0, 0, 1280, i)
								G.screen.blit(G.plain_bg, (0,j*144), rect)
								pygame.display.update()
						# Set game data to next level
						game_stats["current_level"]+=1
						if game_stats["current_level"] == 3:
							beat_game = True
							game_active = False
						else:
							game_level = reset_for_new_game(game_stats["current_level"], False)
							# Fade screen to map
							for i in range(1,144,4):
								game_level.custom_draw() # Render level
								ui.update() # Render HUD
								for j in range(5):
									rect = pygame.rect.Rect(0, 0, 1280, 144-i)
									G.screen.blit(G.plain_bg, (0,j*144), rect)
									pygame.display.update()

				score = game_stats["score"]
				pygame.display.set_caption(f"Anatolian Adventure | FPS: {clock.get_fps():.0f} | Score: {score}")
			else:
				display_pause_screen()

		else:
			# Game Over or Win
			display_end_screen(game_stats["score"])

		pygame.display.update()
		clock.tick(FPS)

if __name__ == "__main__":
	main()