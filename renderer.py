import pygame
import random
import math

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

        self.time_offset = 0.0

    def draw_world(self, screen, world, cam_y):
        screen.fill((20, 20, 20)) # Outer border
        # Draw background base
        pygame.draw.rect(screen, (0, 0, 0), (self.ox, self.oy, self.play_w, self.play_h))
        
        # We only draw lanes visible on screen
        start_row = int(cam_y)
        end_row = int(cam_y) + self.grid_h + 1
        
        for y in range(start_row - 2, end_row + 2):
            lane = world.get_lane(y)
            if not lane: continue
                
            screen_y = self.oy + (self.grid_h - 1 - (y - cam_y)) * self.tile_size
            if screen_y + self.tile_size < self.oy or screen_y > self.oy + self.play_h:
                continue
                
            self.draw_lane_bg(screen, lane, screen_y)
            self.draw_lane_entities(screen, lane, screen_y, cam_y)

    def draw_lane_bg(self, screen, lane, screen_y):
        rect = pygame.Rect(self.ox, screen_y, self.play_w, self.tile_size)
        ts = self.tile_size
        
        # Clip rect to play area
        rect = rect.clip(pygame.Rect(self.ox, self.oy, self.play_w, self.play_h))
        if rect.height <= 0: return

        # Base procedural textures
        if lane.type == 'grass':
            pygame.draw.rect(screen, (50, 160, 60), rect) # Base green
            rng = random.Random(lane.y * 1337)
            for x in range(self.grid_w):
                tx = self.ox + x * ts
                # Flecks
                for _ in range(4):
                    fx = tx + rng.randint(0, ts-2)
                    fy = screen_y + rng.randint(0, ts-2)
                    if rect.collidepoint(fx, fy):
                        pygame.draw.rect(screen, (30, 120, 40), (fx, fy, 2, 2))
                # Dirt edge
                if rng.random() > 0.6:
                    dx = tx + rng.randint(0, ts-4)
                    dy = screen_y + (0 if rng.random() > 0.5 else ts-4)
                    if rect.collidepoint(dx, dy):
                        pygame.draw.rect(screen, (100, 70, 40), (dx, dy, 4, 2))
                        
        elif lane.type == 'road':
            pygame.draw.rect(screen, (60, 60, 60), rect) # Dark asphalt
            # Dashed lines
            for x in range(0, self.grid_w, 2):
                tx = self.ox + x * ts + ts // 4
                ty = screen_y + ts // 2 - 1
                dash = pygame.Rect(tx, ty, ts, 2).clip(rect)
                if dash.height > 0:
                    pygame.draw.rect(screen, (150, 150, 150), dash)
                    
        elif lane.type == 'river':
            pygame.draw.rect(screen, (30, 80, 180), rect) # Deep blue
            # Animated ripples
            r_offset = (self.time_offset * 10) % ts
            for x in range(0, self.grid_w):
                tx = self.ox + x * ts
                for dy in [ts//4, 3*ts//4]:
                    val = (x + lane.y) % 2
                    if val == 0:
                        rx = tx + r_offset
                        ry = screen_y + dy
                        rp = pygame.Rect(rx, ry, ts//2, 2).clip(rect)
                        if rp.height > 0:
                            pygame.draw.rect(screen, (60, 120, 220), rp)
                            
        elif lane.type == 'train':
            pygame.draw.rect(screen, (40, 30, 30), rect)
            # Tracks
            pygame.draw.line(screen, (120,120,120), (self.ox, screen_y+ts//3), (self.ox+self.play_w, screen_y+ts//3), 2)
            pygame.draw.line(screen, (120,120,120), (self.ox, screen_y+2*ts//3), (self.ox+self.play_w, screen_y+2*ts//3), 2)
            for x in range(0, self.grid_w):
                tx = self.ox + x * ts + ts//2
                tr = pygame.Rect(tx, screen_y+4, 4, ts-8).clip(rect)
                if tr.height > 0: pygame.draw.rect(screen, (80,60,40), tr)
                
        elif lane.type == 'ice':
            pygame.draw.rect(screen, (200, 230, 255), rect)
            for x in range(self.grid_w):
                tx = self.ox + x * ts
                gl = pygame.Rect(tx+2, screen_y+2, 6, 2).clip(rect)
                if gl.height > 0: pygame.draw.rect(screen, (255, 255, 255), gl)
                
        elif lane.type == 'mud':
            pygame.draw.rect(screen, (70, 50, 30), rect)
            rng = random.Random(lane.y * 7331)
            for x in range(self.grid_w):
                tx = self.ox + x * ts
                for _ in range(3):
                    mx = tx + rng.randint(0, ts-6)
                    my = screen_y + rng.randint(0, ts-6)
                    mr = pygame.Rect(mx, my, 6, 4).clip(rect)
                    if mr.height > 0: pygame.draw.rect(screen, (40, 30, 15), mr)

    def draw_lane_entities(self, screen, lane, screen_y, cam_y):
        ts = self.tile_size
        # Draw items (Cars, Logs, Trains, Coins)
        for coin in lane.coins:
            if not coin.collected:
                cx = self.ox + coin.x * ts + ts//2
                cy = screen_y + ts//2
                if self.oy <= cy <= self.oy + self.play_h:
                    pygame.draw.circle(screen, (255, 215, 0), (cx, cy), ts//3)
                    # Shine dot
                    pygame.draw.circle(screen, (255, 255, 200), (cx - ts//8, cy - ts//8), ts//8)
                    
        for e in lane.entities:
            ex = self.ox + int(e.x * ts)
            er = pygame.Rect(ex, screen_y + 2, e.length * ts, ts - 4)
            er_clipped = er.clip(pygame.Rect(self.ox, self.oy, self.play_w, self.play_h))
            if er_clipped.width <= 0 or er_clipped.height <= 0:
                continue
                
            if e.type == 'car':
                pygame.draw.rect(screen, e.color, er_clipped)
                # Windshield
                wx = ex + (ts if e.direction == 'right' else 4)
                wr = pygame.Rect(wx, screen_y + 4, ts - 8, ts - 8).clip(er_clipped)
                if wr.width > 0: pygame.draw.rect(screen, (20, 20, 20), wr)
                # Wheels
                pygame.draw.rect(screen, (0,0,0), pygame.Rect(ex+2, screen_y, 6, 2).clip(er_clipped))
                pygame.draw.rect(screen, (0,0,0), pygame.Rect(ex+2, screen_y+ts-2, 6, 2).clip(er_clipped))
                
            elif e.type == 'log':
                pygame.draw.rect(screen, (120, 70, 40), er_clipped)
                # Grain
                pygame.draw.line(screen, (80, 50, 30), (er_clipped.x, screen_y+ts//3), (er_clipped.right-1, screen_y+ts//3))
                pygame.draw.line(screen, (80, 50, 30), (er_clipped.x, screen_y+2*ts//3), (er_clipped.right-1, screen_y+2*ts//3))
                
            elif e.type == 'train':
                pygame.draw.rect(screen, (50, 50, 55), er_clipped)
                # Rivets
                for i in range(0, int(er.width), ts):
                    rx = ex + i + ts//2
                    if er_clipped.collidepoint(rx, screen_y + ts//2):
                        pygame.draw.circle(screen, (90, 90, 95), (rx, int(screen_y + ts//2)), 3)

        # Train warning flash
        if getattr(lane, 'warning_timer', 0) > 0:
            if int(self.time_offset * 10) % 2 == 0:
                flash = pygame.Surface((self.play_w, ts), pygame.SRCALPHA)
                flash.fill((255, 0, 0, 100))
                fr = pygame.Rect(self.ox, screen_y, self.play_w, ts).clip(pygame.Rect(self.ox, self.oy, self.play_w, self.play_h))
                if fr.height > 0:
                    screen.blit(flash, (fr.x, fr.y), (0, 0, fr.width, fr.height))

    def draw_player(self, screen, player, cam_y):
        ts = self.tile_size
        px = self.ox + int(player.x * ts)
        screen_y = self.oy + (self.grid_h - 1 - (player.y - cam_y)) * ts
        
        if not (self.oy <= screen_y <= self.oy + self.play_h): return
        
        # Invincibility flash
        if player.invincible_timer > 0 and int(self.time_offset * 15) % 2 == 0:
            return
            
        # Hopping scale
        scale = 1.0
        if player.state == "hopping":
            # Parabola peaking at 0.5 progress
            p = player.hop_progress
            scale = 1.0 + (0.3 * math.sin(p * math.pi))
            
        ps = int(28 * scale)
        offset = (ts - ps) // 2
        pr = pygame.Rect(px + offset, screen_y + offset, ps, ps)
        pr_clipped = pr.clip(pygame.Rect(self.ox, self.oy, self.play_w, self.play_h))
        if pr_clipped.height <= 0: return
        
        # Base body
        color = (255, 255, 255) # default white chicken
        if player.char_id == "Tank": color = (100, 120, 100)
        elif player.char_id == "Gambler": color = (255, 180, 50)
        elif player.char_id == "Runner": color = (50, 150, 255)
        elif player.char_id == "Ghost": color = (150, 150, 255)
        
        is_ghost = getattr(player, 'is_ghost_replay', False) or player.char_id == "Ghost"
        alpha = 100 if is_ghost else 255
        
        # Blink effect if damaged (invincible)
        if getattr(player, 'invincible', False) and not is_ghost:
            if int(getattr(player, 'invinc_timer', 0) * 10) % 2 == 0:
                return # Skip draw to create flashing effect
        
        surf = pygame.Surface((ps, ps), pygame.SRCALPHA)
        
        # Body
        pygame.draw.rect(surf, (*color[:3], alpha), (0, 0, ps, ps))
        
        # Chicken Details
        # Comb
        pygame.draw.rect(surf, (220, 20, 20, alpha), (ps//2 - 4, 0, 8, 4))
        
        # Eyes
        pygame.draw.rect(surf, (0, 0, 0, alpha), (ps//4 + 2, ps//4 + 2, 3, 3))
        pygame.draw.rect(surf, (0, 0, 0, alpha), (3*ps//4 - 4, ps//4 + 2, 3, 3))
        
        # Beak
        pygame.draw.rect(surf, (255, 150, 0, alpha), (ps//2 - 4, ps//2 - 2, 8, 6))
        
        # Wings
        wing_c = (max(0, color[0]-40), max(0, color[1]-40), max(0, color[2]-40), alpha)
        pygame.draw.rect(surf, wing_c, (0, ps//2, 4, ps//2))
        pygame.draw.rect(surf, wing_c, (ps - 4, ps//2, 4, ps//2))
        
        # Blit using the clipping rect to handle bounds
        screen.blit(surf, (pr.x, pr.y), (pr_clipped.x - pr.x, pr_clipped.y - pr.y, pr_clipped.width, pr_clipped.height))

    def draw_hud(self, screen, world, score, mult, coins, player_lives, biome, cam_y):
        # Pygame fonts
        if not pygame.font.get_init():
            pygame.font.init()
        font = pygame.font.SysFont("Courier", 20, bold=True)
        
        # Background bar
        pygame.draw.rect(screen, (30, 30, 30), (self.ox, 10, self.play_w, 50))
        pygame.draw.rect(screen, (100, 100, 100), (self.ox, 10, self.play_w, 50), 2)
        
        # Score & Multiplier
        s_txt = font.render(f"Score: {score}", True, (255, 255, 255))
        screen.blit(s_txt, (self.ox + 10, 15))
        
        if mult > 1:
            m_txt = font.render(f"x{mult}", True, (255, 200, 50))
            screen.blit(m_txt, (self.ox + 10 + s_txt.get_width() + 10, 15))
            
        # Coins
        c_txt = font.render(f"Coins: {coins}", True, (255, 215, 0))
        screen.blit(c_txt, (self.ox + 10, 35))
        
        # Biome
        b_txt = font.render(f"[{biome}]", True, (150, 255, 150))
        screen.blit(b_txt, (self.ox + self.play_w // 2 - b_txt.get_width()//2, 25))
        
        # Lives (Heart icons)
        for i in range(player_lives):
            hx = self.ox + self.play_w - 30 - (i * 25)
            hy = 30
            pygame.draw.polygon(screen, (255, 50, 50), [(hx, hy+5), (hx-5, hy), (hx-5, hy-5), (hx, hy-2), (hx+5, hy-5), (hx+5, hy)])
            
        # Minimap (top right corner of play area)
        map_w = 40
        map_h = 50
        map_x = self.ox + self.play_w - map_w - 10
        map_y = self.oy + 10
        pygame.draw.rect(screen, (0, 0, 0), (map_x, map_y, map_w, map_h))
        pygame.draw.rect(screen, (255, 255, 255), (map_x, map_y, map_w, map_h), 1)
        
        # 5 rows ahead of camera (cam_y to cam_y + 5)
        for i in range(5):
            ly = int(cam_y) + i
            lane = world.get_lane(ly)
            if not lane: continue
            
            c = (50, 160, 60) # grass
            if lane.type == 'road': c = (100, 100, 100)
            elif lane.type == 'river': c = (40, 100, 200)
            elif lane.type == 'train': c = (50, 30, 30)
            elif lane.type == 'ice': c = (200, 230, 255)
            elif lane.type == 'mud': c = (80, 50, 20)
            
            bh = map_h // 5
            by = map_y + map_h - (i * bh) - bh # draw bottom-up
            pygame.draw.rect(screen, c, (map_x + 1, by, map_w - 2, bh))

    def update_time(self, dt):
        self.time_offset += dt
