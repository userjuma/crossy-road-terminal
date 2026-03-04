import json
import os
import configparser

SAVE_FILE = "save.json"
CONFIG_FILE = "config.ini"

DEFAULT_SAVE = {
    "high_score": 0,
    "unlocked_characters": ["Default"],
    "daily_challenge_played": "",
    "daily_score": 0
}

def load_save():
    if not os.path.exists(SAVE_FILE):
        return DEFAULT_SAVE.copy()
    try:
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_SAVE.copy()

def write_save(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        config["Settings"] = {
            "sound_on": "True",
            "preferred_character": "Default",
            "up": "w",
            "down": "s",
            "left": "a",
            "right": "d"
        }
        with open(CONFIG_FILE, "w") as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE)
    return config

def write_config(config):
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
