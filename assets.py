"""
assets.py

Centralized asset loader. Call load_assets() after pygame.init() and pygame.mixer.init().

Behavior:
 - Loads images and sounds from file paths defined in settings.py
 - Assigns loaded Surfaces/Sounds into the globals module (globals.py) so other modules
   can access them as G.background, G.coin_imgs, G.bullet_img, etc.
 - Also updates settings.monster_data and settings.items entries to include loaded Surfaces
   (keeps runtime code in Enemy/Item unchanged).
 - Returns a dict of loaded assets for convenience.
"""
import os
import pygame
import globals as G
import settings
from settings import import_folder  # import_folder uses pygame so must be called after pygame.init()

def safe_load_image(path, use_alpha=True):
	"""Load an image and return a Surface. Raises FileNotFoundError if missing."""
	if not os.path.exists(path):
		raise FileNotFoundError(f"Image not found: {path}")
	surf = pygame.image.load(path)
	return surf.convert_alpha() if use_alpha else surf.convert()

def safe_load_sound(path):
	"""Load a sound and return a Sound object. Raises FileNotFoundError if missing."""
	if not os.path.exists(path):
		raise FileNotFoundError(f"Sound not found: {path}")
	sound = pygame.mixer.Sound(path)
	sound.set_volume(G.sound_volume)
	return sound

def update_sound_volume(volume):
	"""
	Update the volume of all loaded sounds in globals.
	Called when user changes volume settings.
	"""
	G.sound_volume = volume
	if G.coin_sound:
		G.coin_sound.set_volume(volume)
	if G.health_potion_sound:
		G.health_potion_sound.set_volume(volume)
	if G.hurt_sound:
		G.hurt_sound.set_volume(volume)
	if G.death_sound:
		G.death_sound.set_volume(volume)
	if G.gun_shot_sound:
		G.gun_shot_sound.set_volume(volume)
	if G.necromancer_death_sound:
		G.necromancer_death_sound.set_volume(volume)
	if G.nightborne_death_sound:
		G.nightborne_death_sound.set_volume(volume)
def load_assets():
	"""
	Loads all project assets and assigns them into globals.py and into settings.* entries
	where appropriate.

	Returns:
		assets (dict): mapping of asset-name -> loaded object
	"""
	assets = {}

	# --- Images & backgrounds ---
	try:
		assets['background'] = safe_load_image("levels/1.png", use_alpha=False)
	except FileNotFoundError:
		assets['background'] = pygame.Surface((settings.WIDTH, settings.HEIGHT))
		assets['background'].fill((40, 40, 40))
		print("Warning: background image not found, using placeholder surface.")

	assets['plain_bg'] = pygame.Surface((settings.WIDTH, settings.HEIGHT))
	assets['plain_bg'].fill((0, 0, 0))

	# Bullet image
	try:
		assets['bullet_img'] = safe_load_image("bullet/0.png")
	except FileNotFoundError:
		assets['bullet_img'] = pygame.Surface((4,4))
		assets['bullet_img'].fill((255,255,255))
		print("Warning: bullet image not found, using placeholder.")

	# coin animation frames (folder)
	try:
		assets['coin_imgs'] = import_folder("items/coin")
	except Exception:
		assets['coin_imgs'] = []
		print("Warning: coin animation folder not found or empty.")

	# player base image (single image path)
	try:
		assets['player_image'] = safe_load_image("player/0.png")
	except FileNotFoundError:
		assets['player_image'] = pygame.Surface((64,64))
		assets['player_image'].fill((100, 200, 100))
		print("Warning: player image not found, using placeholder.")

	# coin icon for UI (take first coin frame if available)
	if assets['coin_imgs']:
		try:
			coin_icon = pygame.transform.scale(assets['coin_imgs'][0], (assets['coin_imgs'][0].get_width()*3, assets['coin_imgs'][0].get_height()*3))
			assets['coin_icon'] = coin_icon
		except Exception:
			assets['coin_icon'] = None
	else:
		assets['coin_icon'] = None

	# --- Sounds ---
	try:
		assets['coin_sound'] = safe_load_sound("sounds/coin.wav")
	except FileNotFoundError:
		assets['coin_sound'] = None
		print("Warning: coin sound not found.")

	try:
		assets['health_potion_sound'] = safe_load_sound("sounds/health_pick_up.wav")
	except FileNotFoundError:
		assets['health_potion_sound'] = None
		print("Warning: health potion sound not found.")

	try:
		assets['hurt_sound'] = safe_load_sound("sounds/hurt.mp3")
	except FileNotFoundError:
		assets['hurt_sound'] = None
		print("Warning: hurt sound not found.")

	try:
		assets['death_sound'] = safe_load_sound("sounds/death.mp3")
	except FileNotFoundError:
		assets['death_sound'] = None
		print("Warning: death sound not found.")

	try:
		assets['gun_shot_sound'] = safe_load_sound("sounds/gunshot.wav")
	except FileNotFoundError:
		assets['gun_shot_sound'] = None
		print("Warning: gunshot sound not found.")

	try:
		assets['necromancer_death_sound'] = safe_load_sound("sounds/necromancer death.wav")
	except FileNotFoundError:
		assets['necromancer_death_sound'] = None
		print("Warning: necromancer death sound not found.")

	try:
		assets['nightborne_death_sound'] = safe_load_sound("sounds/nightborne death.mp3")
	except FileNotFoundError:
		assets['nightborne_death_sound'] = None
		print("Warning: nightborne death sound not found.")

	# --- Monster images (update settings.monster_data to include loaded Surfaces and Rects) ---
	for name, info in settings.monster_data.items():
		img_path = info.get("image_path")
		if img_path:
			try:
				surf = safe_load_image(img_path)
				settings.monster_data[name]["image"] = surf
			except FileNotFoundError:
				# fallback placeholder
				settings.monster_data[name]["image"] = pygame.Surface((64, 64))
				settings.monster_data[name]["image"].fill((150, 0, 0))
				print(f"Warning: monster base image for '{name}' not found: {img_path}")
		# convert hitbox tuple into pygame.Rect here
		hb = info.get("hitbox_rect")
		if isinstance(hb, tuple) and hb and hb[0] == "rect":
			_, x, y, w, h = hb
			settings.monster_data[name]["hitbox_rect"] = pygame.Rect(x, y, w, h)

	# --- Items: pre-load item images and (where applicable) animation folders ---
	for item_name, item_info in settings.items.items():
		img_path = item_info.get("image_path")
		anim_folder = item_info.get("anim_folder")
		if img_path:
			try:
				settings.items[item_name]["image"] = safe_load_image(img_path)
			except FileNotFoundError:
				settings.items[item_name]["image"] = pygame.Surface((32, 32))
				settings.items[item_name]["image"].fill((200, 200, 0))
				print(f"Warning: item image not found: {img_path}")
		if item_info.get("has_animation") and anim_folder:
			try:
				assets.setdefault('item_anim', {})[item_name] = import_folder(anim_folder)
			except Exception:
				assets.setdefault('item_anim', {})[item_name] = []
				print(f"Warning: failed to load animation folder for item '{item_name}': {anim_folder}")

	# --- Assign assets into globals for easy access across modules ---
	G.sectboundary_img = safe_load_image("levels/sectboundary.png")
	G.plain_bg = assets['plain_bg']
	G.coin_imgs = assets['coin_imgs']
	G.bullet_img = assets['bullet_img']
	G.player_image = assets['player_image']
	G.coin_icon = assets['coin_icon']

	# sounds
	G.coin_sound = assets.get('coin_sound')
	G.health_potion_sound = assets.get('health_potion_sound')
	G.hurt_sound = assets.get('hurt_sound')
	G.death_sound = assets.get('death_sound')
	G.gun_shot_sound = assets.get('gun_shot_sound')
	G.necromancer_death_sound = assets.get('necromancer_death_sound')
	G.nightborne_death_sound = assets.get('nightborne_death_sound')

	# return for caller if needed
	return assets