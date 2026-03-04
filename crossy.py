import curses
import random
import time
import json
import os
import sys
import configparser
import traceback
from datetime import date

FPS = 15
FRAME_TIME = 1.0 / FPS
CAR_RIGHT = '==>'
CAR_LEFT = '<=='
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
    pairs = [(1,curses.COLOR_BLACK,curses.COLOR_GREEN),(2,curses.COLOR_WHITE,curses.COLOR_BLACK),
        (3,curses.COLOR_WHITE,curses.COLOR_BLUE),(4,curses.COLOR_YELLOW,-1),
        (5,curses.COLOR_CYAN,-1),(6,curses.COLOR_RED,-1),
        (7,curses.COLOR_YELLOW,curses.COLOR_GREEN),(8,curses.COLOR_YELLOW,curses.COLOR_BLACK),
        (9,curses.COLOR_YELLOW,curses.COLOR_BLUE),(10,curses.COLOR_YELLOW,curses.COLOR_GREEN),
        (11,curses.COLOR_RED,curses.COLOR_BLACK),(12,curses.COLOR_RED,curses.COLOR_YELLOW),
        (13,curses.COLOR_WHITE,curses.COLOR_CYAN),(14,curses.COLOR_YELLOW,curses.COLOR_CYAN),
        (15,curses.COLOR_BLUE,-1),(16,curses.COLOR_WHITE,curses.COLOR_RED),
        (17,curses.COLOR_YELLOW,curses.COLOR_BLACK),(18,curses.COLOR_GREEN,-1),
        (19,curses.COLOR_MAGENTA,-1),(20,curses.COLOR_WHITE,curses.COLOR_MAGENTA)]
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
        nc=random.randint(2,3+int(diff*3)); sp=max(5,int(sw/nc)-int(diff*4))
        cars=[]
        for i in range(nc):
            c=make_car(sw,direction)
            c['x']=float((-CAR_LEN-i*sp+random.randint(0,2)) if direction=='right' else (sw+i*sp-random.randint(0,2)))
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
