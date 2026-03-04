import curses
import random
import time
import json
import os
import sys
import configparser
import traceback
from datetime import date

PLAY_W = 80
PLAY_H = 24
FPS = 15
FRAME_TIME = 1.0 / FPS
CAR_RIGHT = 'o-o'
CAR_LEFT = 'o-o'
CAR_LEN = 3
COIN_CHAR = 'o'
WORLD_BUFFER = 10
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crossy_save.json')
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
CRASH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crash.log')

SPEED_MILESTONES = {0:1.0, 15:1.15, 30:1.3, 50:1.5, 80:1.7, 120:1.9, 170:2.1, 250:2.4}

CHARACTERS = {
    'classic': {'symbol':'@','name':'Classic','color_idx':4,'lives':3,'speed':1.0,'inv_time':1.5,
        'score_mult':1,'desc':'Balanced. No gimmicks.','phase_cars':False,'sink_logs':False,
        'extra_drift':False,'double_score':False,'unlock':None},
    'tank': {'symbol':'&','name':'Tank','color_idx':4,'lives':3,'speed':0.8,'inv_time':2.5,
        'score_mult':1,'desc':'Slow but tough. Longer invincibility.','phase_cars':False,
        'sink_logs':False,'extra_drift':False,'double_score':False,'unlock':('score',30)},
    'gambler': {'symbol':'$','name':'Gambler','color_idx':4,'lives':1,'speed':1.0,'inv_time':0,
        'score_mult':2,'desc':'Double points. One life. No second chances.','phase_cars':False,
        'sink_logs':False,'extra_drift':False,'double_score':True,'unlock':('score',50)},
    'ghost': {'symbol':'#','name':'Ghost','color_idx':4,'lives':3,'speed':1.0,'inv_time':1.5,
        'score_mult':1,'desc':'Phase through one car per life. Sinks through logs.',
        'phase_cars':True,'sink_logs':True,'extra_drift':False,'double_score':False,
        'unlock':('rivers',10)},
    'runner': {'symbol':'%','name':'Runner','color_idx':4,'lives':3,'speed':1.0,'inv_time':1.5,
        'score_mult':1,'desc':'Moves two columns per input. Extra log drift.',
        'phase_cars':False,'sink_logs':False,'extra_drift':True,'double_score':False,
        'unlock':('score',80)},
    'wildcard': {'symbol':'?','name':'Wildcard','color_idx':4,'lives':0,'speed':0,'inv_time':0,
        'score_mult':0,'desc':'Random stats each run. Revealed on death.',
        'phase_cars':False,'sink_logs':False,'extra_drift':False,'double_score':False,
        'unlock':('score',100)},
}

BIOMES = ['city','forest','desert','tundra']
BIOME_LENGTH = 25

MILESTONES_TEXT = {
    25: {'classic':'Not bad. The road goes on.','tank':'Slow and steady.','gambler':'Feeling lucky?',
         'ghost':'The living do not see you.','runner':'Legs warmed up yet?','wildcard':'Who are you even?'},
    50: {'classic':'Halfway to nowhere.','tank':'Nothing dents you.','gambler':'Double or nothing.',
         'ghost':'Phasing gets lonely.','runner':'Wind in your hair.','wildcard':'Still guessing.'},
    100:{'classic':'A hundred rows deep.','tank':'An immovable object.','gambler':'The house always wins. Usually.',
         'ghost':'Between worlds now.','runner':'They cannot catch you.','wildcard':'Chaos favors the bold.'},
    200:{'classic':'Legend.','tank':'Fortress.','gambler':'Jackpot.','ghost':'Ethereal.',
         'runner':'Unstoppable.','wildcard':'Undefined.'},
}

CONTROL_NAMES = {'up':'Forward','down':'Backward','left':'Left','right':'Right','pause':'Pause'}

def load_config():
    cfg = configparser.ConfigParser()
    defaults = {'character':'classic','colorblind':'false','sound':'true','difficulty':'normal'}
    if os.path.exists(CONFIG_FILE):
        try:
            cfg.read(CONFIG_FILE)
        except Exception:
            pass
    if 'settings' not in cfg:
        cfg['settings'] = defaults
    for k,v in defaults.items():
        if k not in cfg['settings']:
            cfg['settings'][k] = v
    return cfg

def save_config(cfg):
    try:
        with open(CONFIG_FILE,'w') as f:
            cfg.write(f)
    except IOError:
        pass

def load_save():
    defaults = {'high_scores':[],'controls':{'up':119,'down':115,'left':97,'right':100,'pause':112},
                'unlocked':['classic'],'challenges':{'rivers_crossed':0,'no_death_best':0}}
    if not os.path.exists(SAVE_FILE):
        return defaults
    try:
        with open(SAVE_FILE,'r') as f:
            data = json.load(f)
        for k,v in defaults.items():
            if k not in data:
                data[k] = v
        return data
    except (json.JSONDecodeError,IOError):
        return defaults

def save_data(data):
    try:
        with open(SAVE_FILE,'w') as f:
            json.dump(data,f,indent=2)
    except IOError:
        pass

def record_score(score,save):
    save['high_scores'].append(score)
    save['high_scores'].sort(reverse=True)
    save['high_scores'] = save['high_scores'][:10]
    save_data(save)

def check_unlocks(save,score,stats):
    for cid,cdata in CHARACTERS.items():
        if cid in save['unlocked']:
            continue
        req = cdata['unlock']
        if req is None:
            if cid not in save['unlocked']:
                save['unlocked'].append(cid)
            continue
        kind,val = req
        if kind == 'score' and score >= val:
            save['unlocked'].append(cid)
        elif kind == 'rivers' and stats.get('rivers_crossed',0) >= val:
            save['unlocked'].append(cid)
    save_data(save)

def get_speed_mult(score):
    m = 1.0
    for t,v in sorted(SPEED_MILESTONES.items()):
        if score >= t:
            m = v
    return m

def bell():
    sys.stdout.write('\a')
    sys.stdout.flush()

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    pairs = [(1,curses.COLOR_GREEN,-1), (2,curses.COLOR_WHITE,-1),
        (3,curses.COLOR_CYAN,-1), (4,curses.COLOR_YELLOW,-1),
        (5,curses.COLOR_CYAN,-1), (6,curses.COLOR_RED,-1),
        (7,curses.COLOR_GREEN,-1), (8,curses.COLOR_WHITE,-1),
        (9,curses.COLOR_CYAN,-1), (10,curses.COLOR_YELLOW,-1),
        (11,curses.COLOR_RED,-1), (12,curses.COLOR_YELLOW,-1),
        (13,curses.COLOR_WHITE,-1), (14,curses.COLOR_CYAN,-1),
        (15,curses.COLOR_BLUE,-1), (16,curses.COLOR_RED,-1),
        (17,curses.COLOR_MAGENTA,-1), (18,curses.COLOR_GREEN,-1),
        (19,curses.COLOR_MAGENTA,-1), (20,curses.COLOR_WHITE,-1)]
    for p in pairs:
        curses.init_pair(p[0],p[1],p[2])

def get_biome(row_index):
    idx = abs(row_index) // BIOME_LENGTH
    return BIOMES[idx % len(BIOMES)]

def make_log(sw,direction,score):
    mx = max(4, 9 - score//60)
    mn = max(3, 5 - score//80)
    if mn > mx: mn = mx
    length = random.randint(mn,mx)
    x = random.randint(-length,sw) if direction=='right' else random.randint(0,sw+length)
    return {'x':float(x),'length':length}

def make_car(sw,direction):
    x = random.randint(-CAR_LEN,sw) if direction=='right' else random.randint(0,sw+CAR_LEN)
    return {'x':float(x)}

def generate_lane(row_index,sw,score):
    diff = min(score/120.0,1.0)
    biome = get_biome(row_index)
    if row_index == 0:
        return {'type':'grass','row':row_index,'coins':[],'biome':biome}
    gi = max(3, 5 - int(diff*2))
    if biome == 'desert': gi = max(4, gi+1)
    if row_index % gi == 0:
        coins = _place_coins(sw,diff)
        return {'type':'grass','row':row_index,'coins':coins,'biome':biome}
    # dead end corridors every ~40 rows at higher difficulty
    if diff > 0.3 and abs(row_index) % 40 == 20:
        return {'type':'dead_end','row':row_index,'biome':biome,'gap_x':random.randint(3,max(4,sw-6)),'gap_w':max(3,6-int(diff*3))}
    wt = {'grass':max(1,3-int(diff*2)),'road':4+int(diff*3),'river':3+int(diff*2),
          'train':1 if score>=20 else 0,'wind':1 if score>=10 else 0,
          'ice':1 if score>=15 else 0,'mud':1 if score>=25 else 0}
    if biome=='city': wt['road']+=3; wt['river']=max(0,wt['river']-2)
    elif biome=='forest': wt['river']+=2; wt['road']=max(1,wt['road']-1)
    elif biome=='desert': wt['grass']=max(0,wt['grass']-1); wt['wind']+=2
    elif biome=='tundra': wt['ice']+=3; wt['mud']+=1
    types=list(wt.keys()); ws=[wt[t] for t in types]
    lt = random.choices(types,weights=ws)[0]
    direction = random.choice(['left','right'])
    if lt=='grass':
        return {'type':'grass','row':row_index,'coins':_place_coins(sw,diff),'biome':biome}
    bs = 0.5+diff*1.5; speed = max(0.3,bs+random.uniform(-0.2,0.4))
    if lt=='road':
        nc=random.randint(1,min(3, 1+int(diff*2)))
        sp=max(9, int(sw/nc))
        cars=[]
        for i in range(nc):
            c=make_car(sw,direction)
            c['x']=float((-CAR_LEN-i*sp) if direction=='right' else (sw+i*sp))
            cars.append(c)
        return {'type':'road','row':row_index,'direction':direction,'speed':speed,'cars':cars,'biome':biome}
    if lt=='river':
        nl=random.randint(2,3+int(diff)); sp=max(7,int(sw/nl))
        logs=[]
        for i in range(nl):
            lg=make_log(sw,direction,score)
            lg['x']=float((-lg['length']-i*sp+random.randint(0,3)) if direction=='right' else (sw+i*sp-random.randint(0,3)))
            logs.append(lg)
        return {'type':'river','row':row_index,'direction':direction,'speed':speed*0.7,'logs':logs,'biome':biome}
    if lt=='train':
        return {'type':'train','row':row_index,'direction':direction,'speed':3.0+diff*2.0,
            'train_x':None,'warning_timer':0.0,'cooldown':random.uniform(3.0,6.0-diff*2),
            'time_since_last':random.uniform(0,2.0),'train_length':sw,'biome':biome}
    if lt=='wind':
        return {'type':'wind','row':row_index,'wind_dir':random.choice(['left','right']),
            'wind_strength':0.3+diff*0.5,'biome':biome}
    if lt=='ice':
        nc=random.randint(2,3+int(diff*2)); sp=max(6,int(sw/nc))
        cars=[]
        for i in range(nc):
            c=make_car(sw,direction)
            c['x']=float((-CAR_LEN-i*sp) if direction=='right' else (sw+i*sp))
            cars.append(c)
        return {'type':'ice','row':row_index,'direction':direction,'speed':speed*0.8,'cars':cars,'biome':biome}
    if lt=='mud':
        return {'type':'mud','row':row_index,'biome':biome}
    return {'type':'grass','row':row_index,'coins':[],'biome':biome}

def _place_coins(sw,diff):
    coins=[]
    if random.random() < max(0.15,0.4-diff*0.2):
        for _ in range(random.randint(1,3)):
            coins.append({'x':random.randint(2,max(3,sw-3)),'collected':False})
    return coins

class Hawk:
    def __init__(self,sw,sh):
        self.active=False; self.x=0.0; self.y=0.0; self.dx=0; self.dy=0
        self.timer=0.0; self.cooldown=random.uniform(10,20); self.sw=sw; self.sh=sh
    def update(self,dt,score):
        self.timer+=dt
        if not self.active:
            if self.timer>=self.cooldown and score>=15:
                self.active=True; self.timer=0
                side=random.choice(['left','right'])
                self.y=float(random.randint(2,max(3,self.sh-3)))
                if side=='left': self.x=-2.0; self.dx=1
                else: self.x=float(self.sw+1); self.dx=-1
                self.dy=random.choice([-1,0,1])*0.3
        else:
            self.x+=self.dx*20*dt; self.y+=self.dy*10*dt
            if self.x<-5 or self.x>self.sw+5 or self.y<-3 or self.y>self.sh+3:
                self.active=False; self.cooldown=random.uniform(8,18)
    def check_hit(self,px,py,cam):
        if not self.active: return False
        sy=py-cam; return abs(int(self.x)-px)<=1 and abs(int(self.y)-sy)<=1
    def resize(self,sw,sh): self.sw=sw; self.sh=sh

class Weather:
    def __init__(self,sw,sh):
        self.drops=[]; self.active=False; self.timer=0.0; self.duration=0.0
        self.cooldown=random.uniform(8,15); self.w=sw; self.h=sh
    def update(self,dt):
        self.timer+=dt
        if not self.active:
            if self.timer>=self.cooldown:
                self.active=True; self.timer=0; self.duration=random.uniform(5,12)
                self.drops=[{'x':random.randint(0,max(0,self.w-1)),'y':random.uniform(0,self.h),
                    'speed':random.uniform(0.5,1.5),'char':random.choice(['|','.',':'])} for _ in range(max(5,self.w//6))]
        else:
            if self.timer>=self.duration:
                self.active=False; self.timer=0; self.cooldown=random.uniform(8,15); self.drops=[]; return
            for d in self.drops:
                d['y']+=d['speed']
                if d['y']>=self.h: d['y']=0.0; d['x']=random.randint(0,max(0,self.w-1))
    def resize(self,w,h): self.w=w; self.h=h

class Replay:
    def __init__(self):
        self.inputs=[]; self.frame=0
    def record(self,key): self.inputs.append((self.frame,key))
    def tick(self): self.frame+=1
    def reset(self): self.inputs=[]; self.frame=0

class World:
    def __init__(self,sw,sh):
        self.lanes={}; self.screen_width=sw; self.screen_height=sh
        for r in range(-(sh+WORLD_BUFFER),WORLD_BUFFER):
            self.lanes[r]=generate_lane(r,sw,0)
    def ensure_lanes(self,cam,score):
        top=cam-self.screen_height-WORLD_BUFFER; bot=cam+WORLD_BUFFER
        for r in range(top,bot+1):
            if r not in self.lanes: self.lanes[r]=generate_lane(r,self.screen_width,score)
        self.lanes={r:l for r,l in self.lanes.items() if top-30<=r<=bot+30}
    def get_lane(self,row): return self.lanes.get(row)
    def update(self,dt,score):
        sm=get_speed_mult(score)
        for lane in self.lanes.values():
            lt=lane['type']
            if lt in ('road','ice'): self._move_cars(lane,dt,sm)
            elif lt=='river': self._move_logs(lane,dt,sm)
            elif lt=='train': self._update_train(lane,dt,sm)
    def _move_cars(self,lane,dt,sm):
        d=lane['direction']; dx=lane['speed']*sm*15*dt
        for c in lane['cars']:
            if d=='right':
                c['x']+=dx
                if c['x']>self.screen_width+5: c['x']=float(-CAR_LEN-random.randint(0,8))
            else:
                c['x']-=dx
                if c['x']<-CAR_LEN-5: c['x']=float(self.screen_width+random.randint(0,8))
    def _move_logs(self,lane,dt,sm):
        d=lane['direction']; dx=lane['speed']*sm*15*dt
        for lg in lane['logs']:
            if d=='right':
                lg['x']+=dx
                if lg['x']>self.screen_width+5: lg['x']=float(-lg['length']-random.randint(0,10))
            else:
                lg['x']-=dx
                if lg['x']<-lg['length']-5: lg['x']=float(self.screen_width+random.randint(0,10))
    def _update_train(self,lane,dt,sm):
        lane['time_since_last']+=dt
        if lane['train_x'] is None:
            if lane['time_since_last']>=lane['cooldown']:
                lane['warning_timer']+=dt
                if lane['warning_timer']>=1.0:
                    lane['train_x']=float(-lane['train_length']) if lane['direction']=='right' else float(self.screen_width)
                    lane['warning_timer']=0; lane['time_since_last']=0
        else:
            dx=lane['speed']*sm*15*dt
            if lane['direction']=='right':
                lane['train_x']+=dx
                if lane['train_x']>self.screen_width+5: lane['train_x']=None; lane['cooldown']=random.uniform(3,6)
            else:
                lane['train_x']-=dx
                if lane['train_x']+lane['train_length']<-5: lane['train_x']=None; lane['cooldown']=random.uniform(3,6)

class Player:
    def __init__(self,x,y,char_id='classic'):
        ch=CHARACTERS[char_id] if char_id!='wildcard' else self._roll_wildcard()
        self.char_id=char_id; self.symbol=ch['symbol']; self.x=x; self.y=y
        self.score=0; self.best_row=0; self.alive=True; self.death_reason=''
        self.lives=ch['lives']; self.max_lives=ch['lives']; self.inv_time=ch['inv_time']
        self.invincible_timer=0.0; self.speed_mod=ch['speed']; self.score_mult=ch['score_mult']
        self.phase_cars=ch['phase_cars']; self.phases_left=1 if ch['phase_cars'] else 0
        self.sink_logs=ch['sink_logs']; self.extra_drift=ch['extra_drift']
        self.hop_frames=0; self.streak=0; self.streak_mult=1; self.coins=0
        self.on_ice=False; self.ice_queue=None; self.mud_tick=0
        self.stats={'rivers_crossed':0}; self.color_idx=ch['color_idx']
        self.last_river_row=None
    def _roll_wildcard(self):
        return {'symbol':'?','color_idx':19,'lives':random.randint(1,4),
            'speed':random.uniform(0.7,1.3),'inv_time':random.uniform(0.5,2.5),
            'score_mult':random.randint(1,3),'phase_cars':random.random()<0.3,
            'sink_logs':random.random()<0.2,'extra_drift':random.random()<0.3,
            'double_score':False,'desc':'???','name':'Wildcard','unlock':None}
    def move(self,dx,dy,sw):
        if self.extra_drift and dx!=0: dx*=2
        nx=max(0,min(self.x+dx,sw-1)); ny=self.y+dy
        self.x=nx; self.y=ny
        if dx!=0 or dy!=0: self.hop_frames=2
        if dy<0:
            self.streak+=1; self.streak_mult=1+self.streak//5
            rg=self.best_row-ny
            if rg>0: self.score+=rg*self.streak_mult*self.score_mult; self.best_row=ny
        elif dy>0: self.streak=0; self.streak_mult=1
    def take_hit(self,reason,sound_on=True):
        if self.invincible_timer>0: return
        self.lives-=1
        if sound_on: bell()
        if self.lives<=0: self.alive=False; self.death_reason=reason
        else: self.invincible_timer=self.inv_time
    def update(self,dt):
        if self.invincible_timer>0:
            self.invincible_timer-=dt
            if self.invincible_timer<0: self.invincible_timer=0
        if self.hop_frames>0: self.hop_frames-=1
    def get_char(self):
        return '^' if self.hop_frames>0 else self.symbol
    def track_river(self,row):
        if self.last_river_row!=row:
            self.last_river_row=row; self.stats['rivers_crossed']+=1

def check_collisions(player,world,sound_on=True):
    lane=world.get_lane(player.y)
    if lane is None: return
    lt=lane['type']
    if lt in ('road','ice'):
        for c in lane.get('cars',[]):
            cx=int(c['x'])
            if cx<=player.x<=cx+CAR_LEN-1:
                if player.phase_cars and player.phases_left>0:
                    player.phases_left-=1; return
                player.take_hit('Hit by a car!',sound_on); return
    if lt=='river':
        player.track_river(lane['row'])
        if player.sink_logs:
            player.take_hit('Sank through the log!',sound_on); return
        on_log=False
        for lg in lane.get('logs',[]):
            lx=int(lg['x'])
            if lx<=player.x<=lx+lg['length']-1: on_log=True; break
        if not on_log: player.take_hit('Fell in the river!',sound_on); return
    if lt=='train' and lane.get('train_x') is not None:
        tx=int(lane['train_x'])
        if tx<=player.x<=tx+lane['train_length']-1:
            player.take_hit('Hit by a train!',sound_on); return
    if lt=='dead_end':
        gx=lane['gap_x']; gw=lane['gap_w']
        if not(gx<=player.x<gx+gw):
            player.take_hit('Hit a wall!',sound_on); return
    if lt=='grass' and 'coins' in lane:
        for coin in lane['coins']:
            if not coin['collected'] and coin['x']==int(player.x):
                coin['collected']=True; player.coins+=1; player.score+=5
                if sound_on: bell()

def apply_log_drift(player,world,dt,score):
    lane=world.get_lane(player.y)
    if lane is None or lane['type']!='river': return
    sm=get_speed_mult(score); drift_mult=1.5 if player.extra_drift else 1.0
    for lg in lane.get('logs',[]):
        lx=int(lg['x'])
        if lx<=player.x<=lx+lg['length']-1:
            dx=lane['speed']*sm*15*dt*drift_mult
            player.x+=dx if lane['direction']=='right' else -dx
            player.x=int(player.x)
            if player.x<0 or player.x>=world.screen_width:
                player.take_hit('Drifted off the edge!')
            return

def apply_wind(player,world,dt):
    lane=world.get_lane(player.y)
    if lane is None or lane['type']!='wind': return
    drift=lane['wind_strength']*15*dt
    player.x+=(drift if lane['wind_dir']=='right' else -drift)
    player.x=int(player.x)
    if player.x<0 or player.x>=world.screen_width:
        player.take_hit('Blown off the edge!')

def get_night_level(score):
    c=(score//40)%6
    if c<2: return 0
    elif c<4: return 1
    else: return 2

def night_attr(attr,nl):
    return attr|curses.A_DIM if nl>=2 else attr

def get_seasonal():
    d=date.today(); m,dy=d.month,d.day
    if m==12 and dy>=20: return 'winter'
    if m==10 and dy>=25: return 'halloween'
    return None

CB_PATTERNS = {'grass':'.',  'road':'#',  'river':'~',  'train':'=',  'wind':'>',  'ice':'*',  'mud':'%',  'dead_end':'|'}

def draw_frame(stdscr,ox,oy,w,h,nl):
    col=night_attr(curses.color_pair(2),nl)
    try:
        if 0<=oy-1<curses.LINES: stdscr.addstr(oy-1,ox,'-'*w,col)
        if 0<=oy+h<curses.LINES: stdscr.addstr(oy+h,ox,'-'*w,col)
        for y in range(-1,h+1):
            if 0<=oy+y<curses.LINES:
                if 0<=ox-1<curses.COLS: stdscr.addch(oy+y,ox-1,'|',col)
                if 0<=ox+w<curses.COLS: stdscr.addch(oy+y,ox+w,'|',col)
    except curses.error: pass

def draw_lane(stdscr,sy,lane,sw,nl,fc,colorblind=False,ox=0,oy=0):
    if sy<0 or sy>=PLAY_H: return
    dy=oy+sy
    if not(0<=dy<curses.LINES): return
    lt=lane['type']
    if lt=='grass':
        col=night_attr(curses.color_pair(1),nl)
        rng=random.Random(lane['row']*997)
        for gx in range(0,sw,rng.choice([4,5,7])):
            if gx<sw and 0<=ox+gx<curses.COLS:
                try: stdscr.addch(dy,ox+gx,'.',col)
                except curses.error: pass
        if 'coins' in lane:
            cc=night_attr(curses.color_pair(10),nl)
            for coin in lane['coins']:
                if not coin['collected'] and 0<=coin['x']<sw and 0<=ox+coin['x']<curses.COLS:
                    try: stdscr.addch(dy,ox+coin['x'],COIN_CHAR,cc|curses.A_BOLD)
                    except curses.error: pass
    elif lt in ('road','ice'):
        col=night_attr(curses.color_pair(3) if lt=='ice' else curses.color_pair(8),nl)
        cs=CAR_RIGHT if lane['direction']=='right' else CAR_LEFT
        for c in lane.get('cars',[]):
            cx=int(c['x'])
            for i,ch in enumerate(cs):
                px=cx+i
                if 0<=px<sw and 0<=ox+px<curses.COLS:
                    try: stdscr.addch(dy,ox+px,ch,col|curses.A_BOLD)
                    except curses.error: pass
    elif lt=='river':
        col=night_attr(curses.color_pair(9),nl)
        try: stdscr.addstr(dy,ox,('~'*sw)[:curses.COLS-ox],col|curses.A_DIM)
        except curses.error: pass
        for lg in lane.get('logs',[]):
            lx=int(lg['x']); ls='['+('='*(lg['length']-2))+']'
            for i,ch in enumerate(ls):
                px=lx+i
                if 0<=px<sw and 0<=ox+px<curses.COLS:
                    try: stdscr.addch(dy,ox+px,ch,col|curses.A_BOLD)
                    except curses.error: pass
    elif lt=='train':
        tc=night_attr(curses.color_pair(11),nl)
        warn=(lane['train_x'] is None and lane['time_since_last']>=lane['cooldown'] and lane['warning_timer']>0)
        if warn and fc%6<3: tc=curses.color_pair(12)|curses.A_BOLD
        if warn:
            try: stdscr.addstr(dy,ox,('!'*sw)[:curses.COLS-ox],tc)
            except curses.error: pass
        if lane['train_x'] is not None:
            tx=int(lane['train_x'])
            for i in range(lane['train_length']):
                px=tx+i
                if 0<=px<sw and 0<=ox+px<curses.COLS:
                    try: stdscr.addch(dy,ox+px,'=',tc|curses.A_BOLD)
                    except curses.error: pass
    elif lt=='wind':
        col=night_attr(curses.color_pair(5),nl)
        wc='>' if lane['wind_dir']=='right' else '<'
        rng=random.Random(lane['row']*1013+fc//4)
        for wx in range(rng.randint(0,3),sw,rng.randint(6,10)):
            if 0<=wx<sw and 0<=ox+wx<curses.COLS:
                try: stdscr.addch(dy,ox+wx,wc,col)
                except curses.error: pass
    elif lt=='mud':
        col=night_attr(curses.color_pair(8),nl)
        for mx in range(0,sw,3):
            if 0<=ox+mx<curses.COLS:
                try: stdscr.addch(dy,ox+mx,'"',col)
                except curses.error: pass
    elif lt=='dead_end':
        col=night_attr(curses.color_pair(8),nl)|curses.A_BOLD
        gx=lane['gap_x']; gw=lane['gap_w']
        try:
            stdscr.addstr(dy,ox,('|'*sw)[:curses.COLS-ox],col)
            for px in range(gx,min(gx+gw,sw)):
                if 0<=ox+px<curses.COLS:
                    stdscr.addch(dy,ox+px,' ',col)
        except curses.error: pass

def draw_player(stdscr,player,cam,sh,sw,world,nl,ox=0,oy=0):
    sy=player.y-cam; sx=int(player.x)
    if not(0<=sy<PLAY_H and 0<=sx<PLAY_W): return
    if player.invincible_timer>0 and int(player.invincible_timer*FPS)%4<2: return
    lane=world.get_lane(player.y)
    tp={'grass':7,'road':8,'river':9,'wind':14,'train':17,'ice':9,'mud':8,'dead_end':8}
    pair=tp.get(lane['type'],4) if lane else 4
    if player.lives==1 and player.max_lives>1: pair=6
    pc=night_attr(curses.color_pair(pair),nl)|curses.A_BOLD|curses.A_REVERSE
    if 0<=oy+sy<curses.LINES and 0<=ox+sx<curses.COLS:
        try: stdscr.addch(oy+sy,ox+sx,player.get_char(),pc)
        except curses.error: pass

def draw_hawk(stdscr,hawk,nl,ox=0,oy=0):
    if not hawk.active: return
    hx=int(hawk.x); hy=int(hawk.y)
    if not(0<=hy<PLAY_H and 0<=hx<PLAY_W): return
    col=curses.color_pair(19)|curses.A_BOLD
    if 0<=oy+hy<curses.LINES and 0<=ox+hx<curses.COLS:
        try: stdscr.addch(oy+hy,ox+hx,'V',col)
        except curses.error: pass

def draw_danger(stdscr,world,cam,sh,sw,ox=0,oy=0):
    col=curses.color_pair(16)|curses.A_BOLD
    for sy in range(PLAY_H):
        wr=cam+sy; lane=world.get_lane(wr)
        if lane and lane['type'] == 'train' and lane['train_x'] is not None:
            tx=int(lane['train_x'])
            if 0<=oy+sy<curses.LINES:
                if tx<0 and 0<=ox<curses.COLS:
                    try: stdscr.addch(oy+sy,ox,'<',col)
                    except curses.error: pass
                elif tx>PLAY_W and 0<=ox+PLAY_W-1<curses.COLS:
                    try: stdscr.addch(oy+sy,ox+PLAY_W-1,'>',col)
                    except curses.error: pass

def draw_rain(stdscr,weather,sh,sw,ox=0,oy=0):
    if not weather.active: return
    col=curses.color_pair(15)
    for d in weather.drops:
        dy=int(d['y']); dx=int(d['x'])
        if 0<=dy<PLAY_H-1 and 0<=dx<PLAY_W:
            if 0<=oy+dy<curses.LINES and 0<=ox+dx<curses.COLS:
                try: stdscr.addch(oy+dy,ox+dx,d['char'],col)
                except curses.error: pass

def draw_hud(stdscr,player,sw,nl,ox=0,oy=0):
    parts=[]
    parts.append(f' Score:{player.score}')
    if player.streak_mult>1: parts.append(f' x{player.streak_mult}')
    if player.coins>0: parts.append(f' Coins:{player.coins}')
    parts.append(f' Lives:{player.lives}')
    hud=''.join(parts)
    col=night_attr(curses.color_pair(5)|curses.A_BOLD,nl)
    y = max(0, oy-2)
    x = max(0, ox + PLAY_W - len(hud))
    if y<curses.LINES and x<curses.COLS:
        try: stdscr.addstr(y,x,hud,col)
        except curses.error: pass

def draw_game_over(stdscr,player,sh,sw,pb):
    lines=[player.death_reason,'',f'Final Score: {player.score}',f'Coins: {player.coins}',
        f'Personal Best: {pb}','','[R] Restart  [Q] Quit  [W] Watch Replay']
    sy=sh//2-len(lines)//2; col=curses.color_pair(6)|curses.A_BOLD
    for i,line in enumerate(lines):
        y=sy+i; x=max(0,sw//2-len(line)//2)
        if 0<=y<sh:
            try: stdscr.addstr(y,x,line,col)
            except curses.error: pass

def draw_pause(stdscr,sh,sw):
    lines=['-- PAUSED --','','Press P to resume','Press Q to quit']
    sy=sh//2-len(lines)//2; col=curses.color_pair(5)|curses.A_BOLD
    for i,line in enumerate(lines):
        y=sy+i; x=max(0,sw//2-len(line)//2)
        if 0<=y<sh:
            try: stdscr.addstr(y,x,line,col)
            except curses.error: pass

def draw_milestone(stdscr,text,sh,sw,timer):
    if timer<=0: return
    alpha=min(1.0,timer/1.5)
    col=curses.color_pair(18)|curses.A_BOLD if alpha>0.5 else curses.color_pair(18)
    y=sh//2; x=max(0,sw//2-len(text)//2)
    try: stdscr.addstr(y,x,text,col)
    except curses.error: pass

def key_name(kc):
    names={curses.KEY_UP:'Up',curses.KEY_DOWN:'Down',curses.KEY_LEFT:'Left',curses.KEY_RIGHT:'Right',ord(' '):'Space'}
    if kc in names: return names[kc]
    if 32<=kc<127: return chr(kc).upper()
    return f'({kc})'

def draw_start_screen(stdscr,save):
    stdscr.nodelay(False); curses.curs_set(0)
    while True:
        sh,sw=stdscr.getmaxyx(); stdscr.erase()
        tc=curses.color_pair(18)|curses.A_BOLD; hc=curses.color_pair(5); nc=curses.color_pair(4)
        lines=[]
        lines.append(('CROSSY ROAD TERMINAL',tc)); lines.append(('',nc))
        controls=save['controls']
        lines.append(('-- Controls --',hc))
        for a in ['up','down','left','right','pause']:
            k=controls.get(a,119); lines.append((f'  {CONTROL_NAMES[a]}: {key_name(k)}',nc))
        lines.append(('  Arrow keys also work for movement',nc)); lines.append(('',nc))
        lines.append(('-- High Scores --',hc))
        if save['high_scores']:
            for i,hs in enumerate(save['high_scores'][:10]): lines.append((f'  {i+1}. {hs}',nc))
        else: lines.append(('  No scores yet',nc))
        lines.append(('',nc))
        lines.append(('[ENTER] Play  [S] Select Character  [C] Controls  [D] Daily Challenge  [Q] Quit',hc))
        sy=max(0,sh//2-len(lines)//2)
        for i,(text,col) in enumerate(lines):
            y=sy+i; x=max(0,sw//2-len(text)//2)
            if 0<=y<sh:
                try: stdscr.addstr(y,x,text,col)
                except curses.error: pass
        stdscr.refresh()
        key=stdscr.getch()
        if key==curses.KEY_RESIZE: continue
        if key in(10,13,curses.KEY_ENTER): return 'play'
        if key in(ord('q'),ord('Q')): return 'quit'
        if key in(ord('c'),ord('C')): configure_controls(stdscr,save); continue
        if key in(ord('s'),ord('S')): select_character(stdscr,save); continue
        if key in(ord('d'),ord('D')): return 'daily'

def configure_controls(stdscr,save):
    actions=['up','down','left','right','pause']; controls=save['controls']
    for action in actions:
        stdscr.erase(); sh,sw=stdscr.getmaxyx()
        prompt=f"Press key for '{CONTROL_NAMES[action]}' (now: {key_name(controls.get(action,119))})"
        y=sh//2; x=max(0,sw//2-len(prompt)//2)
        try: stdscr.addstr(y,x,prompt,curses.color_pair(5)|curses.A_BOLD)
        except curses.error: pass
        stdscr.refresh()
        while True:
            key=stdscr.getch()
            if key==curses.KEY_RESIZE: continue
            if key!=-1: controls[action]=key; break
    save['controls']=controls; save_data(save)

def select_character(stdscr,save):
    stdscr.nodelay(False); curses.curs_set(0)
    char_ids=list(CHARACTERS.keys()); idx=0
    while True:
        stdscr.erase(); sh,sw=stdscr.getmaxyx()
        tc=curses.color_pair(18)|curses.A_BOLD; nc=curses.color_pair(4)
        hc=curses.color_pair(5); lc=curses.color_pair(6)
        try: stdscr.addstr(1,max(0,sw//2-10),'-- Select Character --',tc)
        except curses.error: pass
        for i,cid in enumerate(char_ids):
            ch=CHARACTERS[cid]; locked=cid not in save['unlocked']
            y=3+i*2
            if y>=sh-2: break
            marker='> ' if i==idx else '  '
            name=ch['name']; sym=ch['symbol']
            if locked:
                req=ch.get('unlock')
                lock_txt=f'LOCKED (need {req[0]}:{req[1]})' if req else 'LOCKED'
                line=f'{marker}[{sym}] {name} - {lock_txt}'
                col=lc
            else:
                line=f'{marker}[{sym}] {name} - {ch["desc"]}'
                col=hc if i==idx else nc
            x=max(0,sw//2-len(line)//2)
            try: stdscr.addstr(y,x,line,col)
            except curses.error: pass
        try: stdscr.addstr(sh-2,2,'[ENTER] Select  [ESC] Back',nc)
        except curses.error: pass
        stdscr.refresh()
        key=stdscr.getch()
        if key==curses.KEY_RESIZE: continue
        if key in(curses.KEY_UP,ord('w'),ord('W')): idx=(idx-1)%len(char_ids)
        elif key in(curses.KEY_DOWN,ord('s'),ord('S')): idx=(idx+1)%len(char_ids)
        elif key in(10,13,curses.KEY_ENTER):
            cid=char_ids[idx]
            if cid in save['unlocked']:
                save['selected_char']=cid; save_data(save); return
        elif key==27: return

def play_replay(stdscr,replay_data,save,char_id):
    stdscr.nodelay(True); curses.curs_set(0)
    sh,sw=stdscr.getmaxyx(); controls=save['controls']
    if sh < PLAY_H+3 or sw < PLAY_W+2: return
    world=World(PLAY_W,PLAY_H); player=Player(PLAY_W//2,0,char_id)
    cam=-(PLAY_H-2); weather=Weather(PLAY_W,PLAY_H)
    imap={}
    for(f,k) in replay_data.inputs:
        imap.setdefault(f,[]).append(k)
    frame=0; mf=replay_data.frame
    while frame<=mf and player.alive:
        fs=time.time()
        key=stdscr.getch()
        if key in(ord('q'),ord('Q'),27): break
        nh,nw=stdscr.getmaxyx()
        if nh!=sh or nw!=sw: sh,sw=nh,nw
        if sh < PLAY_H+3 or sw < PLAY_W+2: break
        ox=max(0,(sw-PLAY_W)//2); oy=max(0,(sh-PLAY_H)//2)
        if frame in imap:
            for rk in imap[frame]:
                dx,dy=0,0
                if rk in(curses.KEY_UP,controls.get('up',119)): dy=-1
                elif rk in(curses.KEY_DOWN,controls.get('down',115)): dy=1
                elif rk in(curses.KEY_LEFT,controls.get('left',97)): dx=-1
                elif rk in(curses.KEY_RIGHT,controls.get('right',100)): dx=1
                if dx or dy: player.move(dx,dy,PLAY_W)
        dt=FRAME_TIME; world.update(dt,player.score); player.update(dt)
        apply_log_drift(player,world,dt,player.score); apply_wind(player,world,dt)
        tc=player.y-PLAY_H+PLAY_H//3
        if tc<cam: cam=tc
        if player.y>cam+PLAY_H-1: break
        world.ensure_lanes(cam,player.score); check_collisions(player,world,False)
        nl=get_night_level(player.score); weather.update(dt)
        stdscr.erase()
        draw_frame(stdscr,ox,oy,PLAY_W,PLAY_H,nl)
        for sy in range(PLAY_H):
            wr=cam+sy; lane=world.get_lane(wr)
            if lane: draw_lane(stdscr,sy,lane,PLAY_W,nl,frame,ox=ox,oy=oy)
        draw_player(stdscr,player,cam,PLAY_H,PLAY_W,world,nl,ox=ox,oy=oy)
        draw_rain(stdscr,weather,PLAY_H,PLAY_W,ox=ox,oy=oy); draw_hud(stdscr,player,PLAY_W,nl,ox=ox,oy=oy)
        try: stdscr.addstr(0,0,' REPLAY (Q to stop) ',curses.color_pair(6)|curses.A_BOLD)
        except curses.error: pass
        stdscr.refresh(); frame+=1
        sl=FRAME_TIME-(time.time()-fs)
        if sl>0: time.sleep(sl)

def handle_input(stdscr,player,world,controls,replay):
    key=stdscr.getch()
    if key==-1: return None
    if key==curses.KEY_RESIZE: return None
    replay.record(key)
    if key in(ord('q'),ord('Q')): return 'quit'
    if key==controls.get('pause',112): return 'pause'
    dx,dy=0,0
    if key in(curses.KEY_UP,controls.get('up',119)): dy=-1
    elif key in(curses.KEY_DOWN,controls.get('down',115)): dy=1
    elif key in(curses.KEY_LEFT,controls.get('left',97)): dx=-1
    elif key in(curses.KEY_RIGHT,controls.get('right',100)): dx=1
    if dx or dy:
        # mud slows to every other tick
        lane=world.get_lane(player.y)
        if lane and lane['type']=='mud':
            player.mud_tick+=1
            if player.mud_tick%2==0: return None
        # ice delays input by one tick
        if lane and lane['type']=='ice':
            player.ice_queue=(dx,dy); return None
        player.move(dx,dy,world.screen_width)
    return None

def game_loop(stdscr,save,daily=False):
    curses.curs_set(0); stdscr.nodelay(True); stdscr.timeout(0); init_colors()
    sh,sw=stdscr.getmaxyx(); controls=save['controls']
    if sh < PLAY_H+3 or sw < PLAY_W+2: return 0,Replay(),True,'classic'
    cfg=load_config(); colorblind=cfg['settings'].get('colorblind','false')=='true'
    sound_on=cfg['settings'].get('sound','true')=='true'
    char_id=save.get('selected_char','classic')
    if char_id not in save.get('unlocked',['classic']): char_id='classic'
    if daily:
        seed=date.today().toordinal(); random.seed(seed)
    world=World(PLAY_W,PLAY_H); player=Player(PLAY_W//2,0,char_id)
    cam=-(PLAY_H-2); weather=Weather(PLAY_W,PLAY_H); hawk=Hawk(PLAY_W,PLAY_H)
    replay=Replay(); fc=0; ms_text=''; ms_timer=0.0; shown_ms=set()
    while True:
        fs=time.time()
        nh,nw=stdscr.getmaxyx()
        if nh!=sh or nw!=sw: sh,sw=nh,nw
        if sh < PLAY_H+3 or sw < PLAY_W+2: return player.score,replay,True,char_id
        ox=max(0,(sw-PLAY_W)//2); oy=max(0,(sh-PLAY_H)//2)
        
        action=handle_input(stdscr,player,world,controls,replay)
        if action=='quit': return player.score,replay,True,char_id
        if action=='pause':
            stdscr.nodelay(False)
            while True:
                stdscr.erase(); draw_pause(stdscr,sh,sw); stdscr.refresh()
                pk=stdscr.getch()
                if pk==curses.KEY_RESIZE: sh,sw=stdscr.getmaxyx(); continue
                if pk==controls.get('pause',112): break
                if pk in(ord('q'),ord('Q')): return player.score,replay,True,char_id
            stdscr.nodelay(True)
        if not player.alive: break
        dt=FRAME_TIME; world.update(dt,player.score); player.update(dt)
        if player.ice_queue:
            player.move(player.ice_queue[0],player.ice_queue[1],PLAY_W)
            player.ice_queue=None
        apply_log_drift(player,world,dt,player.score); apply_wind(player,world,dt)
        hawk.update(dt,player.score)
        if hawk.check_hit(int(player.x),player.y,cam):
            player.take_hit('Snatched by a hawk!',sound_on)
        if not player.alive: break
        tc=player.y-PLAY_H+PLAY_H//3
        if tc<cam: cam=tc
        if player.y>cam+PLAY_H-1: player.alive=False; player.death_reason='Left behind!'; break
        world.ensure_lanes(cam,player.score); check_collisions(player,world,sound_on)
        if not player.alive: break
        for threshold in sorted(MILESTONES_TEXT.keys()):
            if player.score>=threshold and threshold not in shown_ms:
                shown_ms.add(threshold)
                texts=MILESTONES_TEXT[threshold]
                ms_text=texts.get(player.char_id,texts.get('classic',''))
                ms_timer=2.5
                if sound_on: bell()
        if ms_timer>0: ms_timer-=dt
        nl=get_night_level(player.score); weather.update(dt)
        
        stdscr.erase()
        draw_frame(stdscr,ox,oy,PLAY_W,PLAY_H,nl)
        for sy in range(PLAY_H):
            wr=cam+sy; lane=world.get_lane(wr)
            if lane: draw_lane(stdscr,sy,lane,PLAY_W,nl,fc,colorblind,ox=ox,oy=oy)
        draw_danger(stdscr,world,cam,PLAY_H,PLAY_W,ox=ox,oy=oy)
        draw_player(stdscr,player,cam,PLAY_H,PLAY_W,world,nl,ox=ox,oy=oy)
        draw_hawk(stdscr,hawk,nl,ox=ox,oy=oy); draw_rain(stdscr,weather,PLAY_H,PLAY_W,ox=ox,oy=oy)
        draw_hud(stdscr,player,PLAY_W,nl,ox=ox,oy=oy)
        if ms_timer>0: draw_milestone(stdscr,ms_text,sh,sw,ms_timer)
        stdscr.refresh(); replay.tick(); fc+=1
        sl=FRAME_TIME-(time.time()-fs)
        if sl>0: time.sleep(sl)
    pb=save['high_scores'][0] if save['high_scores'] else 0
    record_score(player.score,save); check_unlocks(save,player.score,player.stats)
    npb=save['high_scores'][0] if save['high_scores'] else 0
    if sound_on: bell()
    stdscr.nodelay(False)
    while True:
        stdscr.erase(); sh,sw=stdscr.getmaxyx()
        ox=max(0,(sw-PLAY_W)//2); oy=max(0,(sh-PLAY_H)//2)
        draw_frame(stdscr,ox,oy,PLAY_W,PLAY_H,0)
        for sy in range(PLAY_H):
            wr=cam+sy; lane=world.get_lane(wr)
            if lane: draw_lane(stdscr,sy,lane,PLAY_W,0,fc,ox=ox,oy=oy)
        draw_game_over(stdscr,player,sh,sw,npb); stdscr.refresh()
        key=stdscr.getch()
        if key==curses.KEY_RESIZE: continue
        if key in(ord('r'),ord('R')): return -1,replay,False,char_id
        if key in(ord('q'),ord('Q')): return player.score,replay,True,char_id
        if key in(ord('w'),ord('W')): play_replay(stdscr,replay,save,char_id); continue

def main(stdscr):
    init_colors(); save=load_save()
    while True:
        action=draw_start_screen(stdscr,save)
        if action=='quit': break
        daily=(action=='daily')
        score,replay,qf,cid=game_loop(stdscr,save,daily)
        if qf: break

if __name__=='__main__':
    try:
        curses.wrapper(main)
    except Exception as e:
        try:
            with open(CRASH_LOG,'w') as f:
                f.write(traceback.format_exc())
        except Exception:
            pass
        raise

