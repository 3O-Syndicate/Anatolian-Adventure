"""Load shared player, projectile, pickup, and sound assets after pygame.init()."""
import json
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
		G.death_sound.set_volume(volume * 0.8)
	if G.enemy_death_sound:
		G.enemy_death_sound.set_volume(volume * 0.75)
	if G.gun_shot_sound:
		G.gun_shot_sound.set_volume(volume * 0.7)
	if G.gun_shot_sounds:
		for s in G.gun_shot_sounds:
			s.set_volume(volume * 0.7)
	if G.cage_break_sound:
		G.cage_break_sound.set_volume(volume)
	if G.footstep_sounds:
		for snd in G.footstep_sounds:
			snd.set_volume(volume * 0.35)
	try:
		pygame.mixer.music.set_volume(volume * 0.25)
	except Exception:
		pass

def play_bgm(path="sounds/Tiled_Rooftop_Dash.mp3", volume_ratio=0.25):
	"""Load and loop background music at a balanced volume."""
	if os.path.exists(path):
		try:
			pygame.mixer.music.load(path)
			pygame.mixer.music.set_volume(G.sound_volume * volume_ratio)
			pygame.mixer.music.play(-1)
		except Exception as e:
			print(f"Warning: could not play BGM {path}: {e}")

HERO_ANIMATIONS = ("idle", "run", "jump", "fall", "land", "duck", "shoot",
                   "duck_shoot", "reload", "hurt", "death")
ENEMY_ANIMATIONS = ("walker/walk", "turtle/walk", "turtle/shell", "turtle/spin")

def placeholder_hero_animations():
	"""Single green frame for every hero animation, used when frames are missing."""
	frame = pygame.Surface((24, 56))
	frame.fill((100, 200, 100))
	meta = {
		"frame_size": [24, 56],
		"anchor": [12, 56],
		"hitbox": {"stand": [24, 56], "duck": [24, 42]},
		"anims": {name: {"durations": [100], "loop": True, "muzzle": [[24, 28]]}
		          for name in HERO_ANIMATIONS},
	}
	return meta, {name: [frame] for name in HERO_ANIMATIONS}

def load_hero_animations(root):
	"""Load every animation folder listed in <root>/anim.json.

	anim.json holds frame durations (ms), looping, the muzzle point of each
	frame, the frame anchor (placed on the hitbox's bottom centre) and the
	standing/ducking hitbox sizes. It is written by art/hero/hero_sprite.py.
	"""
	try:
		with open(os.path.join(root, "anim.json"), encoding="utf-8") as f:
			meta = json.load(f)
		anims = {name: import_folder(os.path.join(root, name)) for name in meta["anims"]}
		if all(anims.values()):
			return meta, anims
	except (OSError, ValueError, KeyError, pygame.error):
		pass
	print("Warning: hero animation frames not found, using placeholder.")
	return placeholder_hero_animations()

def load_assets():
	"""
	Loads all project assets and assigns them into globals.py and into settings.* entries
	where appropriate.

	Returns:
		assets (dict): mapping of asset-name -> loaded object
	"""
	assets = {}

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
		raw_player = safe_load_image("player/0.png")
		bbox = raw_player.get_bounding_rect()
		assets['player_image'] = raw_player.subsurface(bbox).copy()
	except FileNotFoundError:
		assets['player_image'] = pygame.Surface((64,64))
		assets['player_image'].fill((100, 200, 100))
		print("Warning: player image not found, using placeholder.")

	# hero animations (player/hero/<animation>/<n>.png, timings in anim.json)
	assets['hero_meta'], assets['hero_anims'] = load_hero_animations("player/hero")

	try:
		assets['muzzle_flash_imgs'] = import_folder("effects/muzzle_flash")
	except Exception:
		assets['muzzle_flash_imgs'] = []
		print("Warning: muzzle flash frames not found.")

	# enemy animations (enemies/<name>/<n>.png); missing ones keep flat colours
	assets['enemy_frames'] = {}
	for name in ENEMY_ANIMATIONS:
		try:
			frames = import_folder(os.path.join("enemies", name))
		except Exception:
			frames = []
		if frames:
			flipped = [pygame.transform.flip(frame, True, False) for frame in frames]
			assets['enemy_frames'][name] = (frames, flipped)
		else:
			print(f"Warning: enemy frames not found: enemies/{name}")

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
		if os.path.exists("sounds/mixkit-8-bit-lose-2031.wav"):
			assets['death_sound'] = safe_load_sound("sounds/mixkit-8-bit-lose-2031.wav")
		else:
			assets['death_sound'] = safe_load_sound("sounds/death.mp3")
		assets['death_sound'].set_volume(G.sound_volume * 0.8)
	except FileNotFoundError:
		assets['death_sound'] = None
		print("Warning: death sound not found.")

	try:
		if os.path.exists("sounds/enemy_death.wav"):
			assets['enemy_death_sound'] = safe_load_sound("sounds/enemy_death.wav")
		elif os.path.exists("sounds/mixkit-martial-arts-punch-2052.wav"):
			assets['enemy_death_sound'] = safe_load_sound("sounds/mixkit-martial-arts-punch-2052.wav")
		else:
			assets['enemy_death_sound'] = None
		if assets['enemy_death_sound']:
			assets['enemy_death_sound'].set_volume(G.sound_volume * 0.75)
	except FileNotFoundError:
		assets['enemy_death_sound'] = None

	try:
		assets['gun_shot_sound'] = safe_load_sound("sounds/gunshot.wav")
		assets['gun_shot_sound'].set_volume(G.sound_volume * 0.7)
	except FileNotFoundError:
		assets['gun_shot_sound'] = None
		print("Warning: gunshot sound not found.")

	assets['gun_shot_sounds'] = []
	for i in (1, 2, 3):
		path = f"sounds/shot_{i}.wav"
		try:
			s = safe_load_sound(path)
			s.set_volume(G.sound_volume * 0.7)
			assets['gun_shot_sounds'].append(s)
		except FileNotFoundError:
			pass

	try:
		assets['cage_break_sound'] = safe_load_sound("sounds/cage_break.wav")
	except FileNotFoundError:
		assets['cage_break_sound'] = None

	# --- Footsteps (individual footsteps extracted from loop) ---
	assets['footstep_sounds'] = []
	for i in range(3):
		path = f"sounds/footstep_{i}.wav"
		try:
			snd = safe_load_sound(path)
			snd.set_volume(G.sound_volume * 0.35)
			assets['footstep_sounds'].append(snd)
		except FileNotFoundError:
			pass

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
	G.coin_imgs = assets['coin_imgs']
	G.bullet_img = assets['bullet_img']
	G.player_image = assets['player_image']
	G.hero_meta = assets['hero_meta']
	G.hero_anims = assets['hero_anims']
	G.muzzle_flash_imgs = assets['muzzle_flash_imgs']
	G.enemy_frames = assets['enemy_frames']
	G.coin_icon = assets['coin_icon']

	# sounds
	G.coin_sound = assets.get('coin_sound')
	G.health_potion_sound = assets.get('health_potion_sound')
	G.hurt_sound = assets.get('hurt_sound')
	G.death_sound = assets.get('death_sound')
	G.enemy_death_sound = assets.get('enemy_death_sound')
	G.gun_shot_sound = assets.get('gun_shot_sound')
	G.gun_shot_sounds = assets.get('gun_shot_sounds', [])
	G.cage_break_sound = assets.get('cage_break_sound')
	G.footstep_sounds = assets.get('footstep_sounds', [])

	# return for caller if needed
	return assets