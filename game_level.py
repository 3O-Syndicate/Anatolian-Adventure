"""
game_level.py

GameLevel class loads the map and builds the map environment with,
spawns enemies and health potions, and handles drawing the world offset relative to the player.

"""
import pygame
from assets import safe_load_image
from settings import *
import globals as G
import random

# Used for map boundaries
class Tile(pygame.sprite.Sprite):
	def __init__(self, pos, groups, sect):
		super().__init__(groups)
		self.rect = pygame.rect.Rect(pos, (32,32))
		self.image = None
		if sect: self.image = G.sectboundary_img

class GameLevel(pygame.sprite.Group):
	def __init__(self, level_num):
		super().__init__()
		# offset used for camera scrolling
		self.offset = pygame.math.Vector2()

		# background must have been loaded by assets.py and assigned to G.background
		self.floor = safe_load_image("levels/" + str(level_num) + ".png")
		self.enemy_spawn_pos = []
		self.health_spawn_pos = []
		self.player_spawn = (0,0)
		self.sect_boundaries = [[],[],[]]
		self.next_lvl_triggers = pygame.sprite.Group()
		self.next_lvl_trigger_active = False
		self.next_lvl_trigger_invoked = False
		self.prepare(level_num)

	def prepare(self, level_num):
		'''
		Read mask PNG layouts and create Tiles and spawn coordinate lists.
		'''
		mask = pygame.image.load("levels/" + str(level_num) +"_mask.png")
		G.obstacles_group.empty()
		for row in range(mask.get_height()):
			for col in range(mask.get_width()):
				px = mask.get_at((col,row))
				if(px==(0,0,0)): continue
				elif(px==(255,255,255)): continue

				x = col * TILESIZE
				y = row * TILESIZE
				if px.r == 255:
					if px.b == 255: # Boundary
						# print(x,y)
						t = Tile((x, y), [G.obstacles_group], px.g)
						if px.g != 0:
							self.sect_boundaries[px.g-1].append(t)
					elif px.g == 255: # Next level trigger
						Tile((x, y), [self.next_lvl_triggers], px.g)
					else: # Enemy spawn pos
						self.enemy_spawn_pos.append(((x, y), px.g))
				elif px==(0,255,0):
					self.health_spawn_pos.append((x, y))
				elif px==(0,255,255):
					self.player_spawn = (x,y)

		self.spawn_enemies()
		self.spawn_health_potions()

	def spawn_enemies(self):
		"""Spawn the configured number of enemies for the current wave."""
		G.enemy_group.empty()
		self.number_of_enemies = game_stats["number_of_enemies"][game_stats["current_wave"] - 1]
		enemy_name = ["necromancer", "nightborne"]
		num_of_enemies_spawned = 0
		# dynamic import to avoid top-level circular imports
		from enemy import Enemy
		while num_of_enemies_spawned < self.number_of_enemies:
			pos = random.choice(self.enemy_spawn_pos)
			if pos[1] == game_stats["current_wave"]:
				Enemy(random.choice(enemy_name), pos[0])
				num_of_enemies_spawned += 1

	def spawn_health_potions(self):
		"""Spawn a fixed number of health potions at random positions (based on settings)."""
		for i in range(game_stats["num_health_potions"]):
			from item import Item
			Item(random.choice(self.health_spawn_pos), "health potion")

	def custom_draw(self):
		"""
		Draw the world.
		Koddo Update: Smooth Camera + Mouse Peek (Fare Takibi) eklendi.
		"""

		# --- KAMERA HEDEF HESAPLAMA ---

		# 1. Oyuncunun Odak Noktası (Ekranın ortasına denk gelecek şekilde)
		player_target_x = G.player.rect.centerx - (WIDTH // 2)
		player_target_y = G.player.rect.centery - (HEIGHT // 2)

		# 2. Mouse Pozisyonunu Al
		mouse_x, mouse_y = pygame.mouse.get_pos()

		# 3. Mouse'un ekranın merkezine olan uzaklığını hesapla
		offset_mouse_x = mouse_x - (WIDTH // 2)
		offset_mouse_y = mouse_y - (HEIGHT // 2)

		# 4. "MOUSE_PEEK_FACTOR" (Hassasiyet Ayarı)
		# Bu sayı 0.0 ile 1.0 arasında olmalı.
		# 0.3 = Kamera, mouse ile oyuncu arasındaki mesafenin %30'una kadar kayar.
		# Sayıyı artırırsan kamera mouse'a daha çok yapışır, azaltırsan oyuncuda kalır.
		peek_factor = 0.3

		final_target_x = player_target_x + (offset_mouse_x * peek_factor)
		final_target_y = player_target_y + (offset_mouse_y * peek_factor)

		# 5. Lerp (Yumuşak Geçiş) - Kamera bu yeni hedefe yavaşça süzülür
		self.offset.x += (final_target_x - self.offset.x) * 0.05
		self.offset.y += (final_target_y - self.offset.y) * 0.05

		# --- KAMERA BİTİŞ ---

		# Çizim işlemleri (Aynı)
		floor_offset_pos = self.floor.get_rect().topleft - self.offset
		G.screen.blit(self.floor, floor_offset_pos)

		for sprite in G.all_sprites_group:
			offset_pos = sprite.rect.topleft - self.offset
			G.screen.blit(sprite.image, offset_pos)

		for i in self.sect_boundaries[game_stats["current_wave"]-1]:
			offset_pos = i.rect.topleft - self.offset
			G.screen.blit(i.image, offset_pos)

		# Check if player is triggering a level switch
		# Normally this should be on player code but its easier to put it here.

		if self.next_lvl_trigger_active:
			for sprite in self.next_lvl_triggers:
				if sprite.rect.colliderect(G.player.rect):
					self.next_lvl_trigger_invoked = True