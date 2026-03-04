import pygame

class Player:
    def __init__(self, char_id, x, y):
        self.char_id = char_id
        self.x = float(x)
        self.y = int(y)
        self.best_y_this_run = y
        
        self.lives = 1 # New default for lives
        self.inv_time = 2.0
        self.speed_mult = 1.0 # default
        
        # Character special rules
        self.ghost_phases = 0
        if self.char_id == "Tank":
            self.lives = 2 # Tank gets 2 lives
            self.inv_time = 3.5 # Tank invincibility
        elif self.char_id == "Gambler":
            self.lives = 1 # Gambler gets 1 life
        elif char_id == "Ghost":
            self.ghost_phases = 1
        elif char_id == "Runner":
            self.speed_mult = 2.0 # Can move further? Spec: "moves two tiles per input but drifts further" Wait, "moves two tiles per input". We'll just leap 2 units per input.
            
        self.invincible_timer = 0.0
        self.hop_progress = 0.0
        self.state = "idle"
        self.ice_penalty = 0
        
        # Audio
        pygame.mixer.init()
        # Generating a simple beep using pygame buffer, but for simplicity we'll just queue a sound when possible or assume sound.py handles it.
        # Here we just flag actions for game.py to play sounds.
        self.moved_flag = False

    def handle_input(self, events, config):
        if self.state != "idle":
            return False
            
        if self.ice_penalty > 0:
            self.ice_penalty -= 1
            if self.ice_penalty > 0:
                return False

        up_key = getattr(pygame, 'K_' + config["Settings"].get("up", "w").lower(), pygame.K_w)
        down_key = getattr(pygame, 'K_' + config["Settings"].get("down", "s").lower(), pygame.K_s)
        left_key = getattr(pygame, 'K_' + config["Settings"].get("left", "a").lower(), pygame.K_a)
        right_key = getattr(pygame, 'K_' + config["Settings"].get("right", "d").lower(), pygame.K_d)
        
        dx, dy = 0, 0
        for event in events:
            if event.type == pygame.KEYDOWN:
                k = event.key
                if k == up_key or k == pygame.K_UP: dy = 1
                elif k == down_key or k == pygame.K_DOWN: dy = -1
                elif k == left_key or k == pygame.K_LEFT: dx = -1
                elif k == right_key or k == pygame.K_RIGHT: dx = 1
                
                # Check runner leap
                if (dx != 0 or dy != 0) and self.char_id == "Runner":
                    dy *= 2; dx *= 2
                    
        # Apply movement
        if dx != 0 or dy != 0:
            self.x = max(0, min(19, int(self.x) + dx))
            self.y += dy
            self.state = "hopping"
            self.hop_progress = 0.0
            self.moved_flag = True
            return True
            
        return False

    def update(self, dt):
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
            
        if self.state == "hopping":
            self.hop_progress += dt * 6.0
            if self.hop_progress >= 1.0:
                self.hop_progress = 0.0
                self.state = "idle"

    def take_hit(self):
        if self.invincible_timer <= 0:
            self.lives -= 1
            self.invincible_timer = self.inv_time
            if self.char_id == "Ghost":
                self.ghost_phases = 1 # refresh phases? The spec says "phases through one car per life".
            
    def is_alive(self):
        return self.lives > 0
