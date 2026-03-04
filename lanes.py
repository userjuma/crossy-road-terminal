import random

class Entity:
    def __init__(self, e_type, x, length, speed, direction, color=(255,255,255)):
        self.type = e_type
        self.x = float(x)
        self.length = length
        self.speed = speed
        self.direction = direction
        self.color = color

class Coin:
    def __init__(self, x):
        self.x = x
        self.collected = False

class Lane:
    def __init__(self, y, l_type, biome, score):
        self.y = y
        self.type = l_type
        self.biome = biome
        self.entities = []
        self.coins = []
        self.speed_mult = self.get_speed_mult(score)
        self.warning_timer = 0.0
        
        self.generate(score)
        
    def get_speed_mult(self, score):
        if score >= 200: return 2.0
        if score >= 100: return 1.6
        if score >= 50: return 1.3
        if score >= 25: return 1.15
        return 1.0
        
    def generate(self, score):
        # Base speed
        base_speed = random.uniform(2.0, 4.0) * self.speed_mult
        direction = random.choice(['left', 'right'])
        
        if self.type == 'road':
            num_cars = random.randint(1, 3)
            # 20 tiles wide. Minimum 6-tile gap between cars + car length (2). Spacing = 8.
            # 20 // 3 = 6.6. Actually, to get a 6-tile gap, we just space them equally.
            spacing = max(8, 20 // num_cars)
            for i in range(num_cars):
                x = (-2 - i * spacing) if direction == 'right' else (20 + i * spacing)
                color = random.choice([(220,50,50), (50,220,50), (50,50,220), (220,220,50), (220,100,220), (255,255,255)])
                self.entities.append(Entity('car', x, 2, base_speed, direction, color))
                
        elif self.type == 'river':
            max_log = max(2, 6 - (score // 40))
            min_log = max(2, max_log - 2)
            num_logs = random.randint(2, 4)
            spacing = 20 // num_logs
            for i in range(num_logs):
                length = random.randint(min_log, max_log)
                x = (-length - i * spacing) if direction == 'right' else (20 + i * spacing)
                self.entities.append(Entity('log', x, length, base_speed * 0.8, direction))
                
        elif self.type == 'train':
            self.train_timer = random.uniform(2.0, 5.0)
            self.train_active = False
            self.train_direction = direction
            self.train_speed = 15.0 * self.speed_mult
            
        elif self.type == 'grass':
            if random.random() < 0.3:
                num_coins = random.randint(1, 3)
                positions = random.sample(range(20), num_coins)
                for p in positions:
                    self.coins.append(Coin(p))
                    
    def update(self, dt):
        if self.type == 'train':
            if not self.train_active:
                self.train_timer -= dt
                if self.train_timer <= 1.5:
                    self.warning_timer = self.train_timer # flashes red when \<= 1.5
                if self.train_timer <= 0:
                    self.train_active = True
                    self.warning_timer = 0
                    x = -20 if self.train_direction == 'right' else 20
                    self.entities.append(Entity('train', x, 20, self.train_speed, self.train_direction))
            else:
                for e in self.entities:
                    dx = e.speed * dt
                    e.x += dx if e.direction == 'right' else -dx
                # Reset train
                if (self.train_direction == 'right' and self.entities[0].x > 21) or \
                   (self.train_direction == 'left' and self.entities[0].x < -21):
                   self.entities.clear()
                   self.train_active = False
                   self.train_timer = random.uniform(3.0, 6.0)
        else:
            for e in self.entities:
                dx = e.speed * dt
                e.x += dx if e.direction == 'right' else -dx
                if e.direction == 'right' and e.x > 21:
                    e.x = -e.length - random.uniform(0, 2)
                elif e.direction == 'left' and e.x < -e.length - 1:
                    e.x = 20 + random.uniform(0, 2)

    def check_collision(self, player):
        px = player.x + 0.5
        hit = False
        
        if self.type == 'road' or self.type == 'ice':
            for e in self.entities:
                if e.x <= px <= e.x + e.length:
                    if player.char_id == 'Ghost' and player.ghost_phases > 0:
                        player.ghost_phases -= 1
                        return False # dodged!
                    return True # hit!
                    
        elif self.type == 'river':
            if player.char_id == 'Ghost':
                return True # Ghosts sink through logs
            on_log = None
            for e in self.entities:
                if e.x <= px <= e.x + e.length:
                    on_log = e
                    break
            if not on_log:
                return True # fell in water
            else:
                # Drift with log
                dx = on_log.speed * (1.0/60.0)
                # runner drifts twice as fast? "Runner moves two tiles per input, drifts further on logs"
                if player.char_id == 'Runner': dx *= 1.5
                player.x += dx if on_log.direction == 'right' else -dx
                if player.x < -0.5 or player.x > 19.5:
                    return True # drifted off screen
                    
        elif self.type == 'train':
            for e in self.entities:
                if e.x <= px <= e.x + e.length:
                    player.lives = 0 # instant death
                    return True
                    
        elif self.type == 'dead_end':
            # terminal game had it, user spec didn't mention it for pygame rewrite. Skip.
            pass
            
        return hit

    def check_coin(self, player):
        px = int(player.x + 0.5)
        for c in self.coins:
            if not c.collected and c.x == px:
                c.collected = True
                return True
        return False

class World:
    def __init__(self, grid_w, grid_h, daily=False):
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.lanes = {}
        self.current_biome = "City"
        self.biomes = ["City", "Forest", "Desert"]
        
        if daily:
            import datetime
            seed = datetime.date.today().toordinal()
            random.seed(seed)
            
    def get_biome(self, y):
        idx = (abs(y) // 25) % 3
        return self.biomes[idx]
        
    def generate_lanes(self, cam_y, score):
        top = int(cam_y) - 2 # buffer above screen
        bot = int(cam_y) + self.grid_h + 5 # buffer ahead
        
        for r in range(top, bot + 1):
            if r not in self.lanes:
                biome = self.get_biome(r)
                self.current_biome = biome
                
                # Biome frequencies
                if r == 0:
                    l_type = 'grass'
                elif biome == 'City':
                    l_type = random.choices(['grass', 'road', 'river', 'train', 'ice', 'mud'],
                                            weights=[1, 6, 2, 2, 0, 1])[0]
                elif biome == 'Forest':
                    l_type = random.choices(['grass', 'road', 'river', 'train', 'ice', 'mud'],
                                            weights=[3, 2, 5, 1, 0, 2])[0]
                else: # Desert
                    l_type = random.choices(['grass', 'road', 'river', 'train', 'ice', 'mud'],
                                            weights=[1, 7, 1, 1, 2, 0])[0]
                
                # Force grass every ~6 rows as safe zones
                if r % 6 == 0: l_type = 'grass'
                
                self.lanes[r] = Lane(r, l_type, biome, score)
                
        # cleanup old lanes to prevent memory leak
        delete_keys = [k for k in self.lanes.keys() if k < top - 20]
        for k in delete_keys: del self.lanes[k]
        
    def update(self, dt, score):
        for y, lane in self.lanes.items():
            lane.update(dt)
            
    def get_lane(self, y):
        return self.lanes.get(y)
