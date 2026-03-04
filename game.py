import pygame
import random
import array
import math
from player import Player
from lanes import World, get_speed_mult
from renderer import Renderer

class AudioGen:
    def __init__(self):
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        self.enabled = True
        
    def _gen_wave(self, freq, duration, vol=0.5):
        if not self.enabled: return None
        n_samples = int(22050 * duration)
        buf = array.array('h')
        for i in range(n_samples):
            t = float(i) / 22050.0
            # simple square wave
            v = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
            # quick fade out
            env = 1.0 - (i / n_samples)
            buf.append(int(v * vol * 32767 * env))
        return pygame.mixer.Sound(buf)

    def play_move(self):
        if self.enabled: self._gen_wave(440, 0.05, 0.2).play()
    def play_coin(self):
        if self.enabled: self._gen_wave(880, 0.1, 0.3).play()
    def play_death(self):
        if self.enabled: self._gen_wave(150, 0.5, 0.4).play()
    def play_milestone(self):
        # rising tone manually
        if not self.enabled: return
        self._gen_wave(600, 0.2, 0.3).play()

class Game:
    def __init__(self, save_data, config, daily=False):
        self.save_data = save_data
        self.config = config
        self.is_daily = daily
        self.audio = AudioGen()
        self.audio.enabled = config["Settings"].get("sound_on", "True") == "True"
        
        # Grid dimensions: 20 blocks wide, 18 blocks tall. Block size: 32x32.
        self.grid_w = 20
        self.grid_h = 18
        self.tile_size = 32
        
        # Internal state
        self.score = 0
        self.coins_collected = 0
        self.multiplier = 1
        self.streak = 0
        self.game_over = False
        self.paused = False
        self.time_elapsed = 0.0
        
        # Eagle hazard
        self.eagle_timer = random.uniform(10.0, 20.0)
        self.eagle = None
        
        # Replay system
        self.recorded_inputs = []
        self.ghost_data = save_data.get("best_run_replay", []) if not daily else []
        self.ghost_idx = 0
        self.ghost_player = None
        if self.ghost_data:
            self.ghost_player = Player("Default", self.grid_w//2, 0)
        
        char_id = config["Settings"].get("preferred_character", "Default")
        self.player = Player(char_id, self.grid_w // 2, 0)
        self.world = World(self.grid_w, self.grid_h, daily)
        self.renderer = Renderer(self.tile_size, self.grid_w, self.grid_h)
        
        # Camera handles scrolling (tracks player y)
        self.camera_y = 0.0

    def update(self, dt, events):
        if self.game_over: return
        self.renderer.update_time(dt)
        self.time_elapsed += dt

        # Global keys
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.paused = not self.paused
                return

        if self.paused:
            return

        # Player input
        before_y = self.player.y
        moved = self.player.handle_input(events, self.config)
        if moved:
            self.audio.play_move()
            self.recorded_inputs.append((self.time_elapsed, self.player.x, self.player.y))
            # Check for forward movement multiplier logic
            if self.player.y > self.score:
                self.streak += 1
                self.score = self.player.y
            elif self.player.y < self.player.best_y_this_run:
                self.streak = 0
                
            self.multiplier = 1 + (self.streak // 5)
            self.player.best_y_this_run = max(self.player.best_y_this_run, self.player.y)

        # Ghost logic
        if self.ghost_player and self.ghost_idx < len(self.ghost_data):
            # parse recorded
            while self.ghost_idx < len(self.ghost_data) and self.time_elapsed >= self.ghost_data[self.ghost_idx][0]:
                self.ghost_player.x = self.ghost_data[self.ghost_idx][1]
                self.ghost_player.y = self.ghost_data[self.ghost_idx][2]
                self.ghost_idx += 1

        # Check speed milestones
        old_mult = get_speed_mult(self.score)

        # Eagle logic
        if self.eagle is None:
            self.eagle_timer -= dt
            if self.eagle_timer <= 0:
                start_x = -5 if random.random() < 0.5 else 25
                self.eagle = {
                    'x': start_x,
                    'y': self.player.y - 8,
                    'dir_x': 1 if start_x < 0 else -1,
                    'dir_y': 0.6,
                    'speed': 18.0
                }
        else:
            self.eagle['x'] += self.eagle['dir_x'] * self.eagle['speed'] * dt
            self.eagle['y'] += self.eagle['dir_y'] * self.eagle['speed'] * dt
            
            if abs(self.eagle['x'] - self.player.x) < 1.0 and abs(self.eagle['y'] - self.player.y) < 1.0:
                self.player.lives = 0
                self.player.take_hit()
                self.audio.play_death()
                
            if self.eagle['y'] > self.player.y + 15:
                self.eagle = None
                self.eagle_timer = random.uniform(20.0, 35.0)

        # Update entities
        self.player.update(dt)
        self.world.update(dt, self.score)
        
        if get_speed_mult(self.score) > old_mult:
            self.audio.play_milestone()
        
        # Camera logic
        target_cam = self.player.y - (self.grid_h // 2) + 2
        if target_cam > self.camera_y:
            self.camera_y += (target_cam - self.camera_y) * dt * 5.0
            
        # Death conditions
        if self.player.y < self.camera_y - 2:
            self.player.take_hit()
            self.player.y = int(self.camera_y) + 1  # push forward
            self.audio.play_death()
            
        # World lane generation
        self.world.generate_lanes(int(self.camera_y), self.score)
        
        # Collision
        lane = self.world.get_lane(self.player.y)
        if lane:
            hit = lane.check_collision(self.player)
            if hit:
                self.player.take_hit()
                self.audio.play_death()
                
            coin = lane.check_coin(self.player)
            if coin:
                self.coins_collected += 1
                self.score += 5
                self.audio.play_coin()
                
        if not self.player.is_alive():
            self.game_over = True
            
            # Save ghost if personal best
            if not self.is_daily:
                if self.score > self.save_data.get("high_score", 0):
                    self.save_data["best_run_replay"] = self.recorded_inputs

    def draw(self, screen):
        self.renderer.draw_world(screen, self.world, self.camera_y)
        
        if self.ghost_player:
            self.ghost_player.char_id = "Ghost" # Kept original char_id assignment
            self.renderer.draw_player(screen, self.ghost_player, self.camera_y)
            
        self.renderer.draw_player(screen, self.player, self.camera_y)
        
        if self.eagle:
            self.renderer.draw_eagle(screen, self.eagle, self.camera_y)
            
        self.renderer.draw_hud(screen, self.world, self.score, self.multiplier, self.coins_collected, self.player.lives, self.world.current_biome, self.camera_y)
        
        if self.paused:
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            font = pygame.font.SysFont("Courier", 50, bold=True)
            t = font.render("PAUSED [ESC to unpause]", True, (255,255,255))
            screen.blit(t, (400 - t.get_width()//2, 250))

    def is_over(self):
        return self.game_over
