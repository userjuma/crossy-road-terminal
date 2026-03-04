import pygame
import sys
from save import write_config, write_save

class UI:
    def __init__(self, screen, save_data):
        self.screen = screen
        self.save_data = save_data
        pygame.font.init()
        self.title_font = pygame.font.SysFont("Courier", 60, bold=True)
        self.menu_font = pygame.font.SysFont("Courier", 30, bold=True)
        self.small_font = pygame.font.SysFont("Courier", 20)

        # Character roster
        self.roster = [
            {"name": "Default", "desc": "Balanced.", "unlock": 0},
            {"name": "Tank", "desc": "Slower, longer invincibility.", "unlock": 50},
            {"name": "Gambler", "desc": "1 life, double score.", "unlock": 150},
            {"name": "Ghost", "desc": "Phase thru 1 car/life. Sinks in water.", "unlock": 200},
            {"name": "Runner", "desc": "Leaps 2 tiles. Drifts on logs.", "unlock": 300},
            {"name": "Wildcard", "desc": "Random stats.", "unlock": 500}
        ]
        
        self.char_idx = 0
        pref = self.save_data.get("preferred_character", "Default")
        for i, c in enumerate(self.roster):
            if c["name"] == pref:
                self.char_idx = i

    def handle_menu(self, events):
        self.screen.fill((20, 30, 40))
        
        # Title
        t_surf = self.title_font.render("CROSSY ROAD", True, (255, 255, 255))
        self.screen.blit(t_surf, (400 - t_surf.get_width()//2, 100))
        
        # High Score
        hs = self.save_data.get("high_score", 0)
        hs_surf = self.small_font.render(f"High Score: {hs}", True, (200, 200, 200))
        self.screen.blit(hs_surf, (400 - hs_surf.get_width()//2, 180))

        # Character Selection
        char = self.roster[self.char_idx]
        unlocked = hs >= char["unlock"] or char["name"] == "Default"
        
        c_name = char["name"] if unlocked else "???"
        c_desc = char["desc"] if unlocked else f"Unlock at {char['unlock']} score"
        
        color = (200, 200, 200) if unlocked else (50, 50, 50)
        c_surf = self.menu_font.render(f"< {c_name} >", True, color)
        self.screen.blit(c_surf, (400 - c_surf.get_width()//2, 300))
        
        d_surf = self.small_font.render(c_desc, True, (150, 150, 150))
        self.screen.blit(d_surf, (400 - d_surf.get_width()//2, 350))
        
        # Instructions
        start_t = self.small_font.render("[ENTER] Start | [D] Daily Challenge", True, (255, 255, 100))
        self.screen.blit(start_t, (400 - start_t.get_width()//2, 450))

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.char_idx = (self.char_idx - 1) % len(self.roster)
                elif event.key == pygame.K_RIGHT:
                    self.char_idx = (self.char_idx + 1) % len(self.roster)
                elif event.key == pygame.K_RETURN:
                    if unlocked:
                        self.save_data["preferred_character"] = char["name"]
                        return "start"
                elif event.key == pygame.K_d:
                    if unlocked:
                        self.save_data["preferred_character"] = char["name"]
                        return "daily"
                        
        return None

    def handle_game_over(self, events, game):
        # Semi-transparent overlay
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        go_surf = self.title_font.render("GAME OVER", True, (255, 50, 50))
        self.screen.blit(go_surf, (400 - go_surf.get_width()//2, 150))
        
        score_t = self.menu_font.render(f"Final Score: {game.score}", True, (255, 255, 255))
        self.screen.blit(score_t, (400 - score_t.get_width()//2, 250))
        
        coin_t = self.small_font.render(f"Coins Collected: {game.coins_collected}", True, (255, 215, 0))
        self.screen.blit(coin_t, (400 - coin_t.get_width()//2, 300))
        
        # High Score processing
        hs = self.save_data.get("high_score", 0)
        ds = self.save_data.get("daily_score", 0)
        is_new_best = False
        
        import datetime
        today_str = str(datetime.date.today().toordinal())
        
        if not game.is_daily:
            if game.score > hs:
                hs = game.score
                self.save_data["high_score"] = hs
                self.save_data["best_run_replay"] = game.recorded_inputs
                write_save(self.save_data)
                is_new_best = True
                
            if is_new_best:
                best_t = self.menu_font.render("NEW PERSONAL BEST!", True, (100, 255, 100))
                self.screen.blit(best_t, (400 - best_t.get_width()//2, 350))
            else:
                best_t = self.small_font.render(f"Personal Best: {hs}", True, (150, 150, 150))
                self.screen.blit(best_t, (400 - best_t.get_width()//2, 350))
        else:
            if today_str != self.save_data.get("daily_challenge_played", "") or game.score > ds:
                ds = game.score
                self.save_data["daily_challenge_played"] = today_str
                self.save_data["daily_score"] = ds
                write_save(self.save_data)
                is_new_best = True
                
            if is_new_best:
                best_t = self.menu_font.render("NEW DAILY BEST!", True, (100, 255, 100))
                self.screen.blit(best_t, (400 - best_t.get_width()//2, 350))
            else:
                best_t = self.small_font.render(f"Daily Best: {ds}", True, (150, 150, 150))
                self.screen.blit(best_t, (400 - best_t.get_width()//2, 350))

        inst_t = self.small_font.render("[ENTER] Retry | [ESC] Menu", True, (255, 255, 255))
        self.screen.blit(inst_t, (400 - inst_t.get_width()//2, 450))

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return "retry"
                elif event.key == pygame.K_ESCAPE:
                    return "menu"
        return None

    def exit_game(self):
        write_save(self.save_data)
