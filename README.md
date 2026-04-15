# ARE YOU READY? - Tactical Special Forces

A top-down tactical shooter built with Pygame. Clear rooms, eliminate enemies, complete the mission.

## Version 1.1 Changelog

- Constructor now has full Save/Load support
- Patrol route editing: right-click on enemy, then left-click to place waypoints
- Improved enemy AI with search behavior and better state transitions
- Visual effects: muzzle flash, bullet trails, blood particles, screen shake
- Damage vignette and health bars on enemies
- Russian keyboard support (Cyrillic WASD)
- Restart mission with R key
- Windows on the default map
- CustomTkinter UI for both game launcher and constructor

## Download

Grab the latest Windows EXE builds from the [Releases](https://github.com/vfyov6621-coder/are-you-ready/releases) page.

## Controls

| Key | Action |
|-----|--------|
| WASD / ЦФЫВ | Move |
| Mouse | Aim |
| Left Click | Shoot |
| E / У | Interact (open/close doors) |
| ESC | Pause |
| R | Restart (when mission ends) |

## Running from Source

```bash
pip install -r requirements.txt
cd game
python main.py
```

## Map Constructor

```bash
cd constructor
python main.py
```

### Constructor Controls

| Action | Control |
|--------|---------|
| Place tiles | Left Click / Drag |
| Draw rectangle | Select Rect tool, then drag |
| Fill area | Select Fill tool, then click |
| Place enemy | Select Enemy tool, then click |
| Set player spawn | Select Spawn tool, then click |
| Edit patrol route | Right-click on enemy, then left-click waypoints |
| Finish route editing | Enter / Escape |
| Pan camera | Middle Mouse Button drag |
| Zoom | Mouse Wheel |
| Save map | Ctrl+S or Save button |
| Undo | Ctrl+Z |
