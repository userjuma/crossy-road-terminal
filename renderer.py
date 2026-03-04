import pygame

class Renderer:
    def __init__(self, tile_size, grid_w, grid_h):
        self.tile_size = tile_size
        self.grid_w = grid_w
        self.grid_h = grid_h
        
        # Center offset calculations
        self.screen_w = 800
        self.screen_h = 600
        self.play_w = self.grid_w * self.tile_size
        self.play_h = self.grid_h * self.tile_size
        self.ox = (self.screen_w - self.play_w) // 2
        self.oy = (self.screen_h - self.play_h) // 2
        
    def draw_world(self, screen, world, cam_y):
        screen.fill((20, 20, 20)) # Outer border
        pygame.draw.rect(screen, (0, 0, 0), (self.ox, self.oy, self.play_w, self.play_h))
        
    def draw_player(self, screen, player, cam_y):
        pass
        
    def draw_hud(self, screen, score, mult, coins, lives, biome):
        pass
