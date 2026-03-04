import pygame

class UI:
    def __init__(self, screen, save_data):
        self.screen = screen
        self.save_data = save_data
        
    def handle_menu(self, events):
        self.screen.fill((30, 30, 30))
        # Draw placeholder text
        return None # "start" or "daily"
        
    def handle_game_over(self, events, game):
        self.screen.fill((50, 0, 0))
        return None # "menu" or "retry"
        
    def exit_game(self):
        pass
