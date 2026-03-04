# Pygame Crossy Road

A procedural tile-based endless runner written entirely in Python using Pygame. The game draws all visual elements procedurally using standard Pygame shape commands as layered rectangles, lines, and dots to simulate a pixel block aesthetic without any external image files. It includes procedurally generated sound effects using `pygame.mixer` arrays.

## Dependencies

- Python 3.8+
- Pygame (`pip install pygame`)
- Standard library (`json`, `os`, `configparser`, `random`, `math`, `datetime`, `array`)

## How to Play

1. **Launch from Terminal:** Open your terminal (PowerShell, CMD, or VS Code Terminal), navigate to the project directory, and run the game using Python:
   ```bash
   python main.py
   ```
2. The game will launch in a new 800x600 graphical window. Make sure the window is selected to capture your keyboard inputs!

## Play Controls

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

## Legal Disclaimer

Please note that this is a fan-made educational terminal/Pygame clone. The creator does not own any copyright, trademarks, or intellectual property pertaining to the official "Crossy Road" brand produced by Hipster Whale. All code logic and pixel assets were generated natively for fair use.
