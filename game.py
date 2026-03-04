import pygame
from player import Player
from lanes import World
from renderer import Renderer

class Game:
    def __init__(self, save_data, config, daily=False):
        self.save_data = save_data
        self.config = config
        self.is_daily = daily
        
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
        
        char_id = config["Settings"].get("preferred_character", "Default")
        self.player = Player(char_id, self.grid_w // 2, 0)
        self.world = World(self.grid_w, self.grid_h, daily)
        self.renderer = Renderer(self.tile_size, self.grid_w, self.grid_h)
        
        # Camera handles scrolling (tracks player y)
        self.camera_y = 0.0

    def update(self, dt, events):
        if self.game_over:
            return

        # Player input
        moved = self.player.handle_input(events, self.config)
        if moved:
            # Check for forward movement multiplier logic
            if self.player.y > self.score:  # basic tracking
                self.streak += 1
                self.score = self.player.y
            elif self.player.y < self.player.best_y_this_run:
                self.streak = 0
            
            self.multiplier = 1 + (self.streak // 5)
            self.player.best_y_this_run = max(self.player.best_y_this_run, self.player.y)

        # Update entities
        self.player.update(dt)
        self.world.update(dt, self.score)
        
        # Camera logic
        target_cam = self.player.y - (self.grid_h // 2)
        if target_cam > self.camera_y:
            self.camera_y = target_cam
            
        # Death conditions
        if self.player.y < self.camera_y - 2:
            self.player.take_hit()
            self.player.y = int(self.camera_y) + 1  # push forward to prevent instant multi-death if they have lives
            
        # World lane generation
        self.world.generate_lanes(int(self.camera_y), self.score)
        
        # Collision
        lane = self.world.get_lane(self.player.y)
        if lane:
            hit = lane.check_collision(self.player)
            if hit:
                self.player.take_hit()
                
            coin = lane.check_coin(self.player)
            if coin:
                self.coins_collected += 1
                self.score += 5
                
        if not self.player.is_alive():
            self.game_over = True

    def draw(self, screen):
        self.renderer.draw_world(screen, self.world, self.camera_y)
        self.renderer.draw_player(screen, self.player, self.camera_y)
        self.renderer.draw_hud(screen, self.score, self.multiplier, self.coins_collected, self.player.lives, self.world.current_biome)

    def is_over(self):
        return self.game_over
