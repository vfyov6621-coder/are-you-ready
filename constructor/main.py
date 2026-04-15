#!/usr/bin/env python3
"""ARE YOU READY? - Map Constructor"""
import os, sys, json, tkinter as tk
from tkinter import filedialog, messagebox, ttk

GAME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game")
sys.path.insert(0, GAME_DIR)

TILE_SIZE = 48
TOOL_PENCIL = 0
TOOL_RECT = 1
TOOL_FILL = 2
TOOL_ERASER = 3
TOOL_ENEMY = 4
TOOL_SPAWN = 5

TILE_NAMES = ["Floor", "Tile", "Grass", "Wall", "Window", "Door"]
TILE_COLORS = ["#A0A09B", "#BEB9AA", "#468C41", "#5A5A64", "#70D2F0", "#8C5A2D"]


class MapConstructor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ARE YOU READY? - Map Constructor")
        self.geometry("1200x800")
        self.configure(bg="#1a1a2e")

        self.map_w = 30
        self.map_h = 20
        self.grid_data = [[0] * self.map_w for _ in range(self.map_h)]
        self.enemies = []
        self.player_spawn = [2, 2]
        self.doors_open = []

        self.current_tool = TOOL_PENCIL
        self.current_tile = 3
        self.drawing = False
        self.rect_start = None
        self.undo_stack = []
        self.rect_preview = None

        self._build_ui()
        self._bind_events()

    def _build_ui(self):
        toolbar = tk.Frame(self, bg="#16213e", height=50)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="Tile:", bg="#16213e", fg="white",
                 font=("Consolas", 11)).pack(side="left", padx=(10, 5))

        self.tile_var = tk.IntVar(value=3)
        for i, name in enumerate(TILE_NAMES):
            f = tk.Frame(toolbar, bg="#333355", padx=4, pady=2)
            f.pack(side="left", padx=2)
            c = tk.Canvas(f, width=20, height=20, bg=TILE_COLORS[i],
                          highlightthickness=1, highlightbackground="#555")
            c.pack(side="left", padx=(0, 3))
            tk.Radiobutton(f, text=name, variable=self.tile_var, value=i,
                           bg="#333355", fg="white", selectcolor="#555570",
                           activebackground="#444470", activeforeground="white",
                           font=("Consolas", 10),
                           command=self._on_tile_change).pack(side="left")

        sep = tk.Frame(toolbar, bg="#555", width=2)
        sep.pack(side="left", fill="y", padx=10, pady=5)

        tk.Label(toolbar, text="Tool:", bg="#16213e", fg="white",
                 font=("Consolas", 11)).pack(side="left", padx=(0, 5))

        self.tool_var = tk.IntVar(value=TOOL_PENCIL)
        tools = [("Pencil", TOOL_PENCIL), ("Rect", TOOL_RECT),
                 ("Fill", TOOL_FILL), ("Eraser", TOOL_ERASER),
                 ("Enemy", TOOL_ENEMY), ("Spawn", TOOL_SPAWN)]
        for name, tid in tools:
            tk.Radiobutton(toolbar, text=name, variable=self.tool_var, value=tid,
                           bg="#16213e", fg="white", selectcolor="#333355",
                           activebackground="#16213e", activeforeground="white",
                           font=("Consolas", 10),
                           command=self._on_tool_change).pack(side="left", padx=3)

        tk.Button(toolbar, text="Undo", bg="#333355", fg="white",
                  font=("Consolas", 10), command=self._undo).pack(side="left", padx=10)
        tk.Button(toolbar, text="Clear", bg="#553333", fg="white",
                  font=("Consolas", 10), command=self._clear).pack(side="left", padx=3)

        status = tk.Frame(self, bg="#0f3460", height=30)
        status.pack(fill="x", side="bottom")
        self.status_lbl = tk.Label(status, text="Ready", bg="#0f3460", fg="#aaa",
                                   font=("Consolas", 10))
        self.status_lbl.pack(side="left", padx=10)

        self.canvas = tk.Canvas(self, bg="#2a2a3a", scrollregion=(0, 0,
                                   self.map_w * TILE_SIZE, self.map_h * TILE_SIZE))
        self.canvas.pack(fill="both", expand=True)

        self._draw_grid()

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._lmd)
        self.canvas.bind("<B1-Motion>", self._lmm)
        self.canvas.bind("<ButtonRelease-1>", self._lmu)
        self.canvas.bind("<Motion>", self._mouse_move)
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-s>", lambda e: self._save_map_file())

    def _on_tile_change(self):
        self.current_tile = self.tile_var.get()
        if self.current_tool in (TOOL_PENCIL, TOOL_RECT, TOOL_FILL):
            pass

    def _on_tool_change(self):
        self.current_tool = self.tool_var.get()

    def _s2g(self, sx, sy):
        gx = int(sx // TILE_SIZE)
        gy = int(sy // TILE_SIZE)
        return gx, gy

    def _save_undo(self):
        import copy
        state = {
            "grid": copy.deepcopy(self.grid_data),
            "enemies": [e.copy() for e in self.enemies],
            "player_spawn": self.player_spawn[:],
        }
        self.undo_stack.append(state)
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)

    def _lmd(self, e):
        self.drawing = True
        self._save_undo()
        gx, gy = self._s2g(e.x, e.y)
        if self.current_tool == TOOL_RECT:
            self.rect_start = (gx, gy)
        else:
            self._apply(gx, gy)

    def _lmm(self, e):
        if not self.drawing:
            return
        gx, gy = self._s2g(e.x, e.y)
        if self.current_tool == TOOL_RECT and self.rect_start:
            self.rect_preview = (self.rect_start, (gx, gy))
            self._draw_grid()
            self._draw_rect_preview()
        elif self.current_tool in (TOOL_PENCIL, TOOL_ERASER):
            self._apply(gx, gy)

    def _lmu(self, e):
        if not self.drawing:
            return
        self.drawing = False
        if self.current_tool == TOOL_RECT and self.rect_start:
            gx, gy = self._s2g(e.x, e.y)
            x1 = min(self.rect_start[0], gx)
            y1 = min(self.rect_start[1], gy)
            x2 = max(self.rect_start[0], gx)
            y2 = max(self.rect_start[1], gy)
            for ry in range(y1, y2 + 1):
                for rx in range(x1, x2 + 1):
                    if 0 <= rx < self.map_w and 0 <= ry < self.map_h:
                        self.grid_data[ry][rx] = self.current_tile
            self.rect_start = None
            self.rect_preview = None
            self._draw_grid()

    def _mouse_move(self, e):
        gx, gy = self._s2g(e.x, e.y)
        self.status_lbl.config(text=f"Tile: ({gx}, {gy})  |  "
                                    f"Size: {self.map_w}x{self.map_h}  |  "
                                    f"Enemies: {len(self.enemies)}")

    def _apply(self, gx, gy):
        if not (0 <= gx < self.map_w and 0 <= gy < self.map_h):
            return
        if self.current_tool == TOOL_PENCIL:
            self.grid_data[gy][gx] = self.current_tile
            self._draw_tile(gx, gy)
        elif self.current_tool == TOOL_ERASER:
            self.grid_data[gy][gx] = 0
            self._draw_tile(gx, gy)
        elif self.current_tool == TOOL_FILL:
            self._flood_fill(gx, gy, self.grid_data[gy][gx], self.current_tile)
            self._draw_grid()
        elif self.current_tool == TOOL_ENEMY:
            self.enemies.append({"x": gx, "y": gy, "patrol": [[gx, gy]]})
            self._draw_grid()
        elif self.current_tool == TOOL_SPAWN:
            self.player_spawn = [gx, gy]
            self._draw_grid()

    def _flood_fill(self, x, y, old, new):
        if old == new:
            return
        stack = [(x, y)]
        visited = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            if not (0 <= cx < self.map_w and 0 <= cy < self.map_h):
                continue
            if self.grid_data[cy][cx] != old:
                continue
            visited.add((cx, cy))
            self.grid_data[cy][cx] = new
            stack.append((cx + 1, cy))
            stack.append((cx - 1, cy))
            stack.append((cx, cy + 1))
            stack.append((cx, cy - 1))

    def _undo(self):
        if not self.undo_stack:
            return
        state = self.undo_stack.pop()
        self.grid_data = state["grid"]
        self.enemies = state["enemies"]
        self.player_spawn = state["player_spawn"]
        self._draw_grid()

    def _clear(self):
        self._save_undo()
        self.grid_data = [[0] * self.map_w for _ in range(self.map_h)]
        self.enemies.clear()
        self.player_spawn = [2, 2]
        self._draw_grid()

    def _draw_rect_preview(self):
        if not self.rect_preview:
            return
        (x1, y1), (x2, y2) = self.rect_preview
        px1 = min(x1, x2) * TILE_SIZE
        py1 = min(y1, y2) * TILE_SIZE
        px2 = (max(x1, x2) + 1) * TILE_SIZE
        py2 = (max(y1, y2) + 1) * TILE_SIZE
        idx = self.current_tile
        color = TILE_COLORS[idx] if idx < len(TILE_COLORS) else "#888"
        self.canvas.create_rectangle(px1, py1, px2, py2,
                                     fill=color, outline="#fff",
                                     stipple="gray50", tags="preview")

    def _draw_tile(self, gx, gy):
        tile = self.grid_data[gy][gx]
        color = TILE_COLORS[tile] if tile < len(TILE_COLORS) else "#333"
        x1 = gx * TILE_SIZE
        y1 = gy * TILE_SIZE
        x2 = x1 + TILE_SIZE
        y2 = y1 + TILE_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color,
                                     outline="#444", tags="grid")

    def _draw_grid(self):
        self.canvas.delete("grid")
        self.canvas.delete("entity")
        self.canvas.delete("preview")
        for gy in range(self.map_h):
            for gx in range(self.map_w):
                self._draw_tile(gx, gy)
        for ed in self.enemies:
            cx = ed["x"] * TILE_SIZE + TILE_SIZE // 2
            cy = ed["y"] * TILE_SIZE + TILE_SIZE // 2
            r = 8
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill="#FF4444", outline="#CC2222", width=2,
                                    tags="entity")
            self.canvas.create_text(cx, cy, text="E", fill="white",
                                    font=("Consolas", 9, "bold"), tags="entity")
        sx = self.player_spawn[0] * TILE_SIZE + TILE_SIZE // 2
        sy = self.player_spawn[1] * TILE_SIZE + TILE_SIZE // 2
        r = 10
        self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r,
                                fill="#4488FF", outline="#2266CC", width=2,
                                tags="entity")
        self.canvas.create_text(sx, sy, text="P", fill="white",
                                font=("Consolas", 10, "bold"), tags="entity")

    def _save_map_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir=os.path.join(GAME_DIR, "maps")
        )
        if not path:
            return
        data = {
            "name": os.path.splitext(os.path.basename(path))[0],
            "width": self.map_w,
            "height": self.map_h,
            "grid": self.grid_data,
            "doors_open": self.doors_open,
            "player_spawn": self.player_spawn,
            "enemies": self.enemies,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.status_lbl.config(text=f"Saved: {path}")

    def _load_map_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")],
            initialdir=os.path.join(GAME_DIR, "maps")
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.grid_data = data["grid"]
        self.map_w = data["width"]
        self.map_h = data["height"]
        self.player_spawn = data.get("player_spawn", [2, 2])
        self.enemies = data.get("enemies", [])
        self.doors_open = data.get("doors_open", [])
        self.canvas.config(scrollregion=(0, 0,
                          self.map_w * TILE_SIZE, self.map_h * TILE_SIZE))
        self._draw_grid()
        self.status_lbl.config(text=f"Loaded: {path}")


if __name__ == "__main__":
    app = MapConstructor()
    app.mainloop()
