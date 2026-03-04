import pygame

class Player:
    def __init__(self, char_id, x, y):
        self.char_id = char_id
        self.x = x
        self.y = y
        self.best_y_this_run = y
        
        self.lives = 3
        if char_id == "Gambler":
            self.lives = 1
            
        self.invincible_timer = 0.0
        self.hop_progress = 0.0
        self.state = "idle" # idle, hopping
        
    def handle_input(self, events, config):
        moved = False
        # Stub logic for input
        return moved
        
    def update(self, dt):
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
            
        if self.state == "hopping":
            self.hop_progress += dt * 5.0
            if self.hop_progress >= 1.0:
                self.hop_progress = 0.0
                self.state = "idle"

    def take_hit(self):
        if self.invincible_timer <= 0:
            self.lives -= 1
            self.invincible_timer = 2.0
            
    def is_alive(self):
        return self.lives > 0
