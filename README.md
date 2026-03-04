# Crossy Road Terminal

A terminal-based Crossy Road clone written in Python. Uses `curses` for rendering. No external dependencies beyond the standard library (except `windows-curses` on Windows).

## How to Run

```
python crossy.py
```

On Windows, install `windows-curses` first:

```
pip install windows-curses
python crossy.py
```

On macOS and Linux, Python 3.6+ works out of the box.

## Controls

| Key              | Action        |
|------------------|---------------|
| W / Up Arrow     | Move forward  |
| S / Down Arrow   | Move backward |
| A / Left Arrow   | Move left     |
| D / Right Arrow  | Move right    |
| P                | Pause         |
| Q                | Quit          |

Controls are rebindable from the start screen (press C).

## Characters

Six playable characters, each with unique mechanics:

| Symbol | Name     | Trait                                                    |
|--------|----------|----------------------------------------------------------|
| `@`    | Classic  | Balanced, no gimmicks                                    |
| `&`    | Tank     | Slower, but longer invincibility after hits               |
| `$`    | Gambler  | Double score, one life, no second chances                 |
| `#`    | Ghost    | Phases through one car per life, but sinks through logs   |
| `%`    | Runner   | Moves two columns per input, extra drift on logs          |
| `?`    | Wildcard | Random stats each run, revealed on death                  |

Characters unlock at score thresholds or by completing challenges. Progress is saved locally.

## Gameplay

- **Grass rows** are safe zones with occasional coins for bonus points.
- **Road rows** have cars moving horizontally. Getting hit costs a life.
- **River rows** have floating logs. Stand on a log or die. Logs carry you with them.
- **Train tracks** send a full-width train after a blinking warning. Very fast.
- **Wind rows** push you sideways each tick. Fight the drift or get blown off.
- **Ice rows** delay your input by one tick. Road hazards on a slippery surface.
- **Mud rows** slow your movement to every other tick.
- **Dead ends** force you through a narrow gap in a wall.
- **Hawks** swoop diagonally across the screen at higher scores.

Difficulty scales at score milestones with speed jumps, denser traffic, and shorter logs.

## Features

- **Lives system** -- 3 lives (varies by character) with brief invincibility after respawn
- **Streak multiplier** -- consecutive forward moves multiply score gain
- **Biomes** -- terrain themes cycle every 25 rows (city, forest, desert, tundra)
- **Day/night cycle** -- colors dim periodically as score climbs
- **Weather** -- rain sweeps across the screen, obscuring visibility
- **Danger warnings** -- cells flash red when a car or train is about to hit them
- **Coins** -- scattered on grass rows for bonus points
- **Milestone text** -- each character has unique flavor text at score thresholds
- **Daily challenge** -- seeded run using the current date, same for everyone
- **Replay** -- watch back your last run from the game over screen
- **Leaderboard** -- top 10 scores saved locally
- **Colorblind mode** -- uses patterns instead of relying solely on color
- **Config file** -- `config.ini` for character, colorblind, sound, and difficulty settings
- **Crash logging** -- writes terminal state to `crash.log` if something breaks
- **Sound** -- terminal bell for hits, deaths, and milestones

## Configuration

A `config.ini` file is created automatically. You can edit it to set:

```ini
[settings]
character = classic
colorblind = false
sound = true
difficulty = normal
```

## Known Limitations

- Terminal must be at least 80x24. Larger is better.
- On Windows, use Windows Terminal for best color support. Classic `cmd.exe` may not render colors correctly.
- The terminal bell sound depends on your terminal emulator's settings.
- Ghost character sinking through logs makes river crossings a death sentence by design.
