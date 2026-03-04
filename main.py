import pygame
import sys
from game import Game
from save import load_save, load_config
from ui import UI

def main():
    pygame.init()
    pygame.display.set_caption("Crossy Road - Pygame")
    
    # Core display surfaces
    screen = pygame.display.set_mode((800, 600))
    clock = pygame.time.Clock()
    
    # Game data
    config = load_config()
    save_data = load_save()
    
    # Main state components
    ui = UI(screen, save_data)
    game = None
    
    # State flags: menu, playing, game_over
    state = "menu"
    
    while True:
        dt = clock.tick(60) / 1000.0  # limit framerate to 60 FPS, get delta time
        
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                ui.exit_game()
                pygame.quit()
                sys.exit()
                
        # Main state machine
        if state == "menu":
            action = ui.handle_menu(events)
            if action == "start":
                game = Game(save_data, config, daily=False)
                state = "playing"
            elif action == "daily":
                game = Game(save_data, config, daily=True)
                state = "playing"
                
        elif state == "playing":
            game.update(dt, events)
            game.draw(screen)
            if game.is_over():
                state = "game_over"
                
        elif state == "game_over":
            action = ui.handle_game_over(events, game)
            if action == "menu":
                state = "menu"
            elif action == "retry":
                game = Game(save_data, config, daily=game.is_daily)
                state = "playing"

        pygame.display.flip()

if __name__ == "__main__":
    main()
