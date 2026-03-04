# Pygame Crossy Road

A procedural tile-based endless runner written entirely in Python using Pygame. The game draws all visual elements procedurally using standard Pygame shape commands as layered rectangles, lines, and dots to simulate a pixel block aesthetic without any external image files. It includes procedurally generated sound effects using `pygame.mixer` arrays.

## Dependencies

- Python 3.8+
- Pygame (`pip install pygame`)
- Standard library (`json`, `os`, `configparser`, `random`, `math`, `datetime`, `array`)

## How to Run

1. Clone the repository.
2. Install dependencies.
3. Execute `py main.py` or `python main.py` in the root folder.

## Controls

- **Movement:** WASD or Arrow Keys (configurable via config file)
- **Menu Selection:** Left/Right Arrows, Enter
- **Pause Game:** ESC

## Configuration Options

Initialization configuration is written to `config.ini` in the root directory upon first run.
Available options under the `[Settings]` block:
- `sound_on`: `True` or `False`.
- `preferred_character`: String name of the unlocked character (e.g. `Default`, `Tank`).
- `up`, `down`, `left`, `right`: Movement keys bound (e.g. `w`, `s`, `a`, `d`).

## Save Data Location

Player progress, scores, unlocks, and recorded replays are stored in `save.json` in the root directory alongside the executable. Deleting this file will reset all progression and daily challenge histories.

## Known Limitations

- Alpha channel rendering for the Ghost player uses a secondary surface blit which can be performance intensive on extremely weak hardware.
- Procedural audio waveforms rely on a continuous buffer write. Very high frame drops could occasionally desync the beep playback duration.
