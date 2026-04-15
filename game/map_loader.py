import json, os
from constants import TILE_FLOOR, DEFAULT_MAP_W, DEFAULT_MAP_H

def create_empty_map(width=DEFAULT_MAP_W, height=DEFAULT_MAP_H):
    grid = [[TILE_FLOOR] * width for _ in range(height)]
    return {"name":"Untitled","width":width,"height":height,
            "grid":grid,"doors_open":[],"player_spawn":[2,2],"enemies":[]}

def save_map(game_map, filepath):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(game_map, f, indent=2, ensure_ascii=False)

def load_map(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    data.setdefault("doors_open", [])
    data.setdefault("player_spawn", [2, 2])
    data.setdefault("enemies", [])
    data.setdefault("name", "Untitled")
    return data

def get_tile(grid, x, y):
    if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
        return grid[y][x]
    return TILE_FLOOR

def is_door_open(game_map, x, y):
    return any(d[0] == x and d[1] == y for d in game_map.get("doors_open", []))

def toggle_door(game_map, x, y):
    if get_tile(game_map["grid"], x, y) != 5: return False
    for i, d in enumerate(game_map.get("doors_open", [])):
        if d[0] == x and d[1] == y:
            game_map["doors_open"].pop(i); return True
    game_map["doors_open"].append([x, y]); return True
