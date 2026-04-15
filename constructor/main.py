#!/usr/bin/env python3
"""ARE YOU READY? - Map Constructor v1.1"""
import os, sys, json, copy, math
import tkinter as tk

GAME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game")
sys.path.insert(0, GAME_DIR)

import customtkinter as ctk
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Constants ───────────────────────────────────────────────
TILE_SIZE = 48

TILE_FLOOR = 0; TILE_TILE_FLOOR = 1; TILE_GRASS = 2
TILE_WALL = 3; TILE_WINDOW = 4; TILE_DOOR = 5

TOOL_PENCIL = 0; TOOL_RECT = 1; TOOL_FILL = 2; TOOL_ERASER = 3
TOOL_ENEMY = 4; TOOL_SPAWN = 5; TOOL_ROUTE = 6

TILE_NAMES = ["Floor", "Tile", "Grass", "Wall", "Window", "Door"]
TILE_COLORS = ["#A0A09B", "#BEB9AA", "#468C41", "#5A5A64", "#70B8D0", "#8C5A2D"]

MODE_NORMAL = 0
MODE_ROUTE_EDIT = 1  # editing patrol route for selected enemy


class MapConstructor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ARE YOU READY? - Map Constructor v1.1")
        self.geometry("1280x860")
        self.resizable(True, True)
        self.configure(fg_color=("#1a1a2e", "#1a1a2e"))
        self.minsize(900, 600)

        # Map state
        self.map_w = 30
        self.map_h = 20
        self.grid_data = [[TILE_FLOOR] * self.map_w for _ in range(self.map_h)]
        self.enemies = []
        self.player_spawn = [2, 2]
        self.doors_open = []

        # Editor state
        self.current_tool = TOOL_PENCIL
        self.current_tile = TILE_WALL
        self.drawing = False
        self.rect_start = None
        self.rect_preview = None
        self.undo_stack = []

        # Route editing state
        self.edit_mode = MODE_NORMAL
        self.selected_enemy_idx = None  # index into self.enemies

        # Camera / zoom
        self.zoom = 1.0
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.panning = False
        self.pan_start = None

        # Build
        self._build_ui()
        self._bind_events()
        self._redraw()

    # ═══════════════════════════════════════════════════════════
    # UI Construction
    # ═══════════════════════════════════════════════════════════
    def _build_ui(self):
        # ── Top toolbar ──
        self.toolbar = ctk.CTkFrame(self, height=52, fg_color="#16213e", corner_radius=0)
        self.toolbar.pack(fill="x", side="top")
        self.toolbar.pack_propagate(False)

        # Tiles section
        ctk.CTkLabel(self.toolbar, text="Tile:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#aaa").pack(side="left", padx=(12, 4))
        self.tile_var = ctk.IntVar(value=TILE_WALL)
        for i, name in enumerate(TILE_NAMES):
            f = ctk.CTkFrame(self.toolbar, fg_color="#222244", corner_radius=6)
            f.pack(side="left", padx=2, pady=8)
            # color swatch
            swatch = tk.Canvas(f, width=18, height=18, bg=TILE_COLORS[i],
                               highlightthickness=1, highlightbackground="#555")
            swatch.pack(side="left", padx=(4, 2), pady=4)
            ctk.CTkRadioButton(f, text=name, variable=self.tile_var, value=i,
                               font=ctk.CTkFont(size=11),
                               fg_color="#e94560", hover_color="#c73650",
                               command=self._on_tile_change).pack(side="left", padx=(0, 6), pady=2)

        # Separator
        ctk.CTkFrame(self.toolbar, width=2, fg_color="#444").pack(side="left", fill="y", padx=10, pady=8)

        # Tools section
        ctk.CTkLabel(self.toolbar, text="Tool:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#aaa").pack(side="left", padx=(0, 4))
        self.tool_var = ctk.IntVar(value=TOOL_PENCIL)
        tools = [("Pencil", TOOL_PENCIL), ("Rect", TOOL_RECT), ("Fill", TOOL_FILL),
                 ("Eraser", TOOL_ERASER), ("Enemy", TOOL_ENEMY), ("Spawn", TOOL_SPAWN)]
        for name, tid in tools:
            ctk.CTkRadioButton(self.toolbar, text=name, variable=self.tool_var, value=tid,
                               font=ctk.CTkFont(size=11),
                               fg_color="#e94560", hover_color="#c73650",
                               command=self._on_tool_change).pack(side="left", padx=2, pady=4)

        # ── Right side of toolbar: Save / Load / etc ──
        btn_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        btn_frame.pack(side="right", padx=8)

        ctk.CTkButton(btn_frame, text="Save", width=60, height=30,
                      fg_color="#2d6a4f", hover_color="#1b4332",
                      font=ctk.CTkFont(size=11), command=self._save_map_file).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Load", width=60, height=30,
                      fg_color="#333355", hover_color="#444470",
                      font=ctk.CTkFont(size=11), command=self._load_map_file).pack(side="left", padx=2)

        # ── Status bar ──
        self.statusbar = ctk.CTkFrame(self, height=28, fg_color="#0f3460", corner_radius=0)
        self.statusbar.pack(fill="x", side="bottom")
        self.statusbar.pack_propagate(False)
        self.status_lbl = ctk.CTkLabel(self.statusbar, text="Ready", font=ctk.CTkFont(size=11),
                                       text_color="#aaa")
        self.status_lbl.pack(side="left", padx=10)

        self.mode_lbl = ctk.CTkLabel(self.statusbar, text="", font=ctk.CTkFont(size=11, weight="bold"),
                                     text_color="#e94560")
        self.mode_lbl.pack(side="right", padx=10)

        # ── Side panel ──
        self.side_panel = ctk.CTkFrame(self, width=220, fg_color="#16213e", corner_radius=0)
        self.side_panel.pack(fill="y", side="right")
        self.side_panel.pack_propagate(False)

        ctk.CTkLabel(self.side_panel, text="EDITOR", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#e94560").pack(pady=(12, 8))

        ctk.CTkButton(self.side_panel, text="Undo (Ctrl+Z)", width=190, height=32,
                      fg_color="#333355", hover_color="#444470",
                      font=ctk.CTkFont(size=11), command=self._undo).pack(pady=3, padx=10)
        ctk.CTkButton(self.side_panel, text="Clear Map", width=190, height=32,
                      fg_color="#553333", hover_color="#774444",
                      font=ctk.CTkFont(size=11), command=self._clear).pack(pady=3, padx=10)
        ctk.CTkButton(self.side_panel, text="Resize Map...", width=190, height=32,
                      fg_color="#333355", hover_color="#444470",
                      font=ctk.CTkFont(size=11), command=self._resize_dialog).pack(pady=3, padx=10)

        ctk.CTkFrame(self.side_panel, height=2, fg_color="#333355").pack(fill="x", padx=12, pady=10)

        # Route info panel
        ctk.CTkLabel(self.side_panel, text="PATROL ROUTES",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaa").pack(pady=(0, 6))
        self.route_info_lbl = ctk.CTkLabel(self.side_panel, text="RMB on enemy to edit route\nLMB to add waypoints",
                                           font=ctk.CTkFont(size=10), text_color="#666",
                                           justify="center")
        self.route_info_lbl.pack(pady=2, padx=10)

        self.route_detail_lbl = ctk.CTkLabel(self.side_panel, text="",
                                             font=ctk.CTkFont(size=11), text_color="#aaa",
                                             justify="left", wraplength=190)
        self.route_detail_lbl.pack(pady=4, padx=10)

        ctk.CTkButton(self.side_panel, text="Finish Route (Enter)", width=190, height=32,
                      fg_color="#2d6a4f", hover_color="#1b4332",
                      font=ctk.CTkFont(size=11), command=self._finish_route_edit).pack(pady=3, padx=10)
        ctk.CTkButton(self.side_panel, text="Clear Selected Route", width=190, height=32,
                      fg_color="#553333", hover_color="#774444",
                      font=ctk.CTkFont(size=11), command=self._clear_selected_route).pack(pady=3, padx=10)

        ctk.CTkFrame(self.side_panel, height=2, fg_color="#333355").pack(fill="x", padx=12, pady=10)

        # Zoom controls
        ctk.CTkLabel(self.side_panel, text="VIEW", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#aaa").pack(pady=(0, 6))
        zoom_f = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        zoom_f.pack(pady=2, padx=10)
        ctk.CTkButton(zoom_f, text="  +  ", width=60, height=28,
                      fg_color="#333355", hover_color="#444470",
                      font=ctk.CTkFont(size=12), command=self._zoom_in).pack(side="left", padx=2)
        ctk.CTkButton(zoom_f, text="  -  ", width=60, height=28,
                      fg_color="#333355", hover_color="#444470",
                      font=ctk.CTkFont(size=12), command=self._zoom_out).pack(side="left", padx=2)
        ctk.CTkButton(zoom_f, text="Fit", width=60, height=28,
                      fg_color="#333355", hover_color="#444470",
                      font=ctk.CTkFont(size=12), command=self._zoom_fit).pack(side="left", padx=2)

        ctk.CTkFrame(self.side_panel, height=2, fg_color="#333355").pack(fill="x", padx=12, pady=10)

        # Export
        ctk.CTkButton(self.side_panel, text="Copy to Game Folder", width=190, height=34,
                      fg_color="#e94560", hover_color="#c73650",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._copy_to_game).pack(pady=4, padx=10)

        # ── Canvas area ──
        self.canvas_frame = ctk.CTkFrame(self, fg_color="#2a2a3a", corner_radius=0)
        self.canvas_frame.pack(fill="both", expand=True, side="left")

        self.canvas = tk.Canvas(self.canvas_frame, bg="#2a2a3a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    # ═══════════════════════════════════════════════════════════
    # Event Binding
    # ═══════════════════════════════════════════════════════════
    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_lmb_down)
        self.canvas.bind("<B1-Motion>", self._on_lmb_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_lmb_up)
        self.canvas.bind("<ButtonPress-3>", self._on_rmb_down)
        self.canvas.bind("<ButtonPress-2>", self._on_mmb_down)
        self.canvas.bind("<B2-Motion>", self._on_mmb_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_mmb_up)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_in())
        self.canvas.bind("<Button-5>", lambda e: self._zoom_out())
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-s>", lambda e: self._save_map_file())
        self.bind("<Control-Z>", lambda e: self._undo())
        self.bind("<Control-S>", lambda e: self._save_map_file())
        self.bind("<Return>", lambda e: self._finish_route_edit())
        self.bind("<Escape>", lambda e: self._finish_route_edit())
        self.canvas.bind("<Configure>", lambda e: self._redraw())

    # ═══════════════════════════════════════════════════════════
    # Coordinate transforms
    # ═══════════════════════════════════════════════════════════
    def _screen_to_grid(self, sx, sy):
        gx = int((sx + self.cam_x) / (TILE_SIZE * self.zoom))
        gy = int((sy + self.cam_y) / (TILE_SIZE * self.zoom))
        return gx, gy

    def _grid_to_screen(self, gx, gy):
        sx = gx * TILE_SIZE * self.zoom - self.cam_x
        sy = gy * TILE_SIZE * self.zoom - self.cam_y
        return sx, sy

    # ═══════════════════════════════════════════════════════════
    # Tool / Tile change
    # ═══════════════════════════════════════════════════════════
    def _on_tile_change(self):
        self.current_tile = self.tile_var.get()
        self._finish_route_edit()

    def _on_tool_change(self):
        self.current_tool = self.tool_var.get()
        self._finish_route_edit()

    # ═══════════════════════════════════════════════════════════
    # Undo system
    # ═══════════════════════════════════════════════════════════
    def _save_undo(self):
        state = {
            "grid": copy.deepcopy(self.grid_data),
            "enemies": copy.deepcopy(self.enemies),
            "player_spawn": self.player_spawn[:],
        }
        self.undo_stack.append(state)
        if len(self.undo_stack) > 80:
            self.undo_stack.pop(0)

    def _undo(self):
        if not self.undo_stack:
            return
        state = self.undo_stack.pop()
        self.grid_data = state["grid"]
        self.enemies = state["enemies"]
        self.player_spawn = state["player_spawn"]
        self.selected_enemy_idx = None
        self.edit_mode = MODE_NORMAL
        self._update_mode_label()
        self._redraw()

    # ═══════════════════════════════════════════════════════════
    # Mouse events - Drawing tools
    # ═══════════════════════════════════════════════════════════
    def _on_lmb_down(self, e):
        # Route editing mode
        if self.edit_mode == MODE_ROUTE_EDIT and self.selected_enemy_idx is not None:
            gx, gy = self._screen_to_grid(e.x, e.y)
            self._add_route_point(gx, gy)
            return

        # Normal mode
        self.drawing = True
        self._save_undo()
        gx, gy = self._screen_to_grid(e.x, e.y)

        if self.current_tool == TOOL_RECT:
            self.rect_start = (gx, gy)
        elif self.current_tool == TOOL_ENEMY:
            # Check if clicking on existing enemy to select for route editing
            idx = self._find_enemy_at(gx, gy)
            if idx is not None:
                self._enter_route_edit(idx)
            else:
                self._place_enemy(gx, gy)
        else:
            self._apply_tool(gx, gy)

    def _on_lmb_drag(self, e):
        if self.edit_mode == MODE_ROUTE_EDIT:
            return

        if not self.drawing:
            return
        gx, gy = self._screen_to_grid(e.x, e.y)
        if self.current_tool == TOOL_RECT and self.rect_start:
            self.rect_preview = (self.rect_start, (gx, gy))
            self._redraw()
        elif self.current_tool in (TOOL_PENCIL, TOOL_ERASER):
            self._apply_tool(gx, gy)

    def _on_lmb_up(self, e):
        if self.edit_mode == MODE_ROUTE_EDIT:
            return

        if not self.drawing:
            return
        self.drawing = False

        if self.current_tool == TOOL_RECT and self.rect_start:
            gx, gy = self._screen_to_grid(e.x, e.y)
            x1, y1 = min(self.rect_start[0], gx), min(self.rect_start[1], gy)
            x2, y2 = max(self.rect_start[0], gx), max(self.rect_start[1], gy)
            for ry in range(y1, y2 + 1):
                for rx in range(x1, x2 + 1):
                    if 0 <= rx < self.map_w and 0 <= ry < self.map_h:
                        self.grid_data[ry][rx] = self.current_tile
            self.rect_start = None
            self.rect_preview = None
            self._redraw()

    def _on_rmb_down(self, e):
        """Right-click: enter route editing mode for enemy under cursor."""
        gx, gy = self._screen_to_grid(e.x, e.y)
        idx = self._find_enemy_at(gx, gy)
        if idx is not None:
            self._enter_route_edit(idx)
        else:
            # Right click outside enemy = cancel route editing
            self._finish_route_edit()

    def _on_mmb_down(self, e):
        self.panning = True
        self.pan_start = (e.x, e.y)

    def _on_mmb_drag(self, e):
        if not self.panning or not self.pan_start:
            return
        dx = e.x - self.pan_start[0]
        dy = e.y - self.pan_start[1]
        self.cam_x -= dx / self.zoom
        self.cam_y -= dy / self.zoom
        self.pan_start = (e.x, e.y)
        self._redraw()

    def _on_mmb_up(self, e):
        self.panning = False
        self.pan_start = None

    def _on_scroll(self, e):
        if e.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    def _on_mouse_move(self, e):
        gx, gy = self._screen_to_grid(e.x, e.y)
        tile_name = TILE_NAMES[self.grid_data[gy][gx]] if (0 <= gy < self.map_h and 0 <= gx < self.map_w) else "?"
        info = f"Tile: ({gx}, {gy}) {tile_name}  |  Map: {self.map_w}x{self.map_h}  |  Enemies: {len(self.enemies)}  |  Zoom: {self.zoom:.0%}"
        self.status_lbl.configure(text=info)

    # ═══════════════════════════════════════════════════════════
    # Tool application
    # ═══════════════════════════════════════════════════════════
    def _apply_tool(self, gx, gy):
        if not (0 <= gx < self.map_w and 0 <= gy < self.map_h):
            return
        if self.current_tool == TOOL_PENCIL:
            self.grid_data[gy][gx] = self.current_tile
        elif self.current_tool == TOOL_ERASER:
            self.grid_data[gy][gx] = TILE_FLOOR
        elif self.current_tool == TOOL_FILL:
            self._flood_fill(gx, gy, self.grid_data[gy][gx], self.current_tile)
        elif self.current_tool == TOOL_SPAWN:
            self.player_spawn = [gx, gy]
        self._redraw()

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

    def _place_enemy(self, gx, gy):
        if not (0 <= gx < self.map_w and 0 <= gy < self.map_h):
            return
        self.enemies.append({"x": gx, "y": gy, "patrol": [[gx, gy]]})
        self._redraw()

    def _find_enemy_at(self, gx, gy):
        """Find enemy at grid position. Returns index or None."""
        for i, ed in enumerate(self.enemies):
            if ed["x"] == gx and ed["y"] == gy:
                return i
        return None

    # ═══════════════════════════════════════════════════════════
    # Route editing
    # ═══════════════════════════════════════════════════════════
    def _enter_route_edit(self, enemy_idx):
        self._save_undo()
        self.edit_mode = MODE_ROUTE_EDIT
        self.selected_enemy_idx = enemy_idx
        self._update_mode_label()
        self._update_route_detail()
        self._redraw()

    def _finish_route_edit(self):
        if self.edit_mode == MODE_NORMAL:
            return
        # Remove duplicate consecutive points
        if self.selected_enemy_idx is not None and self.selected_enemy_idx < len(self.enemies):
            patrol = self.enemies[self.selected_enemy_idx].get("patrol", [])
            cleaned = []
            for pt in patrol:
                if not cleaned or cleaned[-1] != pt:
                    cleaned.append(pt)
            # Also remove point if it's same as first (would cause loop of 1)
            self.enemies[self.selected_enemy_idx]["patrol"] = cleaned
        self.edit_mode = MODE_NORMAL
        self.selected_enemy_idx = None
        self._update_mode_label()
        self._update_route_detail()
        self._redraw()

    def _add_route_point(self, gx, gy):
        if self.selected_enemy_idx is None or self.selected_enemy_idx >= len(self.enemies):
            return
        enemy = self.enemies[self.selected_enemy_idx]
        enemy.setdefault("patrol", [])
        # Don't add duplicate of last point
        if enemy["patrol"] and enemy["patrol"][-1] == [gx, gy]:
            return
        enemy["patrol"].append([gx, gy])
        self._update_route_detail()
        self._redraw()

    def _clear_selected_route(self):
        if self.selected_enemy_idx is not None and self.selected_enemy_idx < len(self.enemies):
            self._save_undo()
            enemy = self.enemies[self.selected_enemy_idx]
            enemy["patrol"] = [[enemy["x"], enemy["y"]]]
            self._update_route_detail()
            self._redraw()

    def _update_mode_label(self):
        if self.edit_mode == MODE_ROUTE_EDIT and self.selected_enemy_idx is not None:
            idx = self.selected_enemy_idx
            ex = self.enemies[idx]["x"]
            ey = self.enemies[idx]["y"]
            self.mode_lbl.configure(text=f"EDITING ROUTE: Enemy #{idx + 1} at ({ex},{ey})  [Enter=Finish]")
        else:
            self.mode_lbl.configure(text="")

    def _update_route_detail(self):
        if self.selected_enemy_idx is not None and self.selected_enemy_idx < len(self.enemies):
            enemy = self.enemies[self.selected_enemy_idx]
            pts = enemy.get("patrol", [])
            text = f"Enemy #{self.selected_enemy_idx + 1}\n"
            text += f"Position: ({enemy['x']}, {enemy['y']})\n"
            text += f"Waypoints: {len(pts)}\n"
            if pts:
                text += "Route: " + " -> ".join(f"({p[0]},{p[1]})" for p in pts)
            self.route_detail_lbl.configure(text=text)
        else:
            total = sum(len(e.get("patrol", [])) for e in self.enemies)
            self.route_detail_lbl.configure(text=f"Total enemies: {len(self.enemies)}\nTotal waypoints: {total}")

    # ═══════════════════════════════════════════════════════════
    # Zoom
    # ═══════════════════════════════════════════════════════════
    def _zoom_in(self):
        self.zoom = min(3.0, self.zoom * 1.2)
        self._redraw()

    def _zoom_out(self):
        self.zoom = max(0.2, self.zoom / 1.2)
        self._redraw()

    def _zoom_fit(self):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        zx = cw / (self.map_w * TILE_SIZE)
        zy = ch / (self.map_h * TILE_SIZE)
        self.zoom = min(zx, zy) * 0.9
        self.cam_x = 0
        self.cam_y = 0
        self._redraw()

    # ═══════════════════════════════════════════════════════════
    # Drawing
    # ═══════════════════════════════════════════════════════════
    def _redraw(self):
        self.canvas.delete("all")
        ts = TILE_SIZE * self.zoom
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        # Determine visible range
        gx0 = max(0, int(self.cam_x / ts))
        gy0 = max(0, int(self.cam_y / ts))
        gx1 = min(self.map_w, int((self.cam_x + cw) / ts) + 2)
        gy1 = min(self.map_h, int((self.cam_y + ch) / ts) + 2)

        # Draw tiles
        for gy in range(gy0, gy1):
            for gx in range(gx0, gx1):
                tile = self.grid_data[gy][gx]
                sx, sy = self._grid_to_screen(gx, gy)
                color = TILE_COLORS[tile] if tile < len(TILE_COLORS) else "#333"
                self.canvas.create_rectangle(sx, sy, sx + ts, sy + ts,
                                             fill=color, outline="#333", width=1)
                # Wall relief effect
                if tile == TILE_WALL:
                    rh = 6 * self.zoom
                    self.canvas.create_rectangle(sx, sy - rh, sx + ts, sy + 2,
                                                 fill="#6A6A78", outline="")
                elif tile == TILE_DOOR:
                    # Door handle
                    hx = sx + ts * 0.7
                    hy = sy + ts * 0.5
                    r = 3 * self.zoom
                    self.canvas.create_oval(hx - r, hy - r, hx + r, hy + r,
                                            fill="#C8B464", outline="")

        # Draw patrol routes
        for i, ed in enumerate(self.enemies):
            patrol = ed.get("patrol", [])
            if len(patrol) >= 2:
                is_selected = (self.edit_mode == MODE_ROUTE_EDIT and i == self.selected_enemy_idx)
                line_color = "#FF6666" if is_selected else "#AA4444"
                line_width = 3 if is_selected else 2
                # Draw route lines
                for j in range(len(patrol) - 1):
                    x1, y1 = self._grid_to_screen(patrol[j][0], patrol[j][1])
                    x2, y2 = self._grid_to_screen(patrol[j + 1][0], patrol[j + 1][1])
                    cx1 = x1 + ts / 2
                    cy1 = y1 + ts / 2
                    cx2 = x2 + ts / 2
                    cy2 = y2 + ts / 2
                    self.canvas.create_line(cx1, cy1, cx2, cy2,
                                            fill=line_color, width=line_width,
                                            dash=(6, 3) if not is_selected else ())
                # Connect last to first (loop) with dotted line
                if len(patrol) > 2:
                    x1, y1 = self._grid_to_screen(patrol[-1][0], patrol[-1][1])
                    x2, y2 = self._grid_to_screen(patrol[0][0], patrol[0][1])
                    self.canvas.create_line(x1 + ts / 2, y1 + ts / 2, x2 + ts / 2, y2 + ts / 2,
                                            fill=line_color, width=max(1, line_width - 1),
                                            dash=(4, 4))
                # Draw waypoint markers
                for j, pt in enumerate(patrol):
                    wx, wy = self._grid_to_screen(pt[0], pt[1])
                    wcx = wx + ts / 2
                    wcy = wy + ts / 2
                    wr = 5 * self.zoom
                    self.canvas.create_oval(wcx - wr, wcy - wr, wcx + wr, wcy + wr,
                                            fill="#FF8888" if is_selected else "#884444",
                                            outline="white", width=1)
                    if is_selected and self.zoom >= 0.6:
                        self.canvas.create_text(wcx, wcy, text=str(j + 1),
                                                fill="white",
                                                font=("Consolas", max(7, int(8 * self.zoom)), "bold"))

        # Draw enemies
        for i, ed in enumerate(self.enemies):
            ex, ey = self._grid_to_screen(ed["x"], ed["y"])
            cx = ex + ts / 2
            cy = ey + ts / 2
            r = 10 * self.zoom
            is_selected = (self.edit_mode == MODE_ROUTE_EDIT and i == self.selected_enemy_idx)

            outline_color = "#FFFF00" if is_selected else "#CC2222"
            outline_w = 3 if is_selected else 2
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill="#FF4444", outline=outline_color, width=outline_w)
            if self.zoom >= 0.5:
                self.canvas.create_text(cx, cy, text="E", fill="white",
                                        font=("Consolas", max(7, int(10 * self.zoom)), "bold"))

        # Draw player spawn
        psx, psy = self._grid_to_screen(self.player_spawn[0], self.player_spawn[1])
        pcx = psx + ts / 2
        pcy = psy + ts / 2
        r = 12 * self.zoom
        self.canvas.create_oval(pcx - r, pcy - r, pcx + r, pcy + r,
                                fill="#4488FF", outline="#2266CC", width=2)
        if self.zoom >= 0.5:
            self.canvas.create_text(pcx, pcy, text="P", fill="white",
                                    font=("Consolas", max(7, int(11 * self.zoom)), "bold"))

        # Draw rect preview
        if self.rect_preview:
            (x1, y1), (x2, y2) = self.rect_preview
            px1, py1 = self._grid_to_screen(min(x1, x2), min(y1, y2))
            px2, py2 = self._grid_to_screen(max(x1, x2) + 1, max(y1, y2) + 1)
            color = TILE_COLORS[self.current_tile]
            self.canvas.create_rectangle(px1, py1, px2, py2,
                                         fill=color, outline="#fff", width=2,
                                         stipple="gray50")

        # Update route detail when not in edit mode
        if self.edit_mode == MODE_NORMAL:
            self._update_route_detail()

    # ═══════════════════════════════════════════════════════════
    # Map operations
    # ═══════════════════════════════════════════════════════════
    def _clear(self):
        self._save_undo()
        self.grid_data = [[TILE_FLOOR] * self.map_w for _ in range(self.map_h)]
        self.enemies.clear()
        self.player_spawn = [2, 2]
        self.selected_enemy_idx = None
        self.edit_mode = MODE_NORMAL
        self._update_mode_label()
        self._redraw()

    def _resize_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Resize Map")
        dialog.geometry("300x160")
        dialog.configure(fg_color="#1a1a2e")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="New Size", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#e94560").pack(pady=(15, 10))
        f = ctk.CTkFrame(dialog, fg_color="transparent")
        f.pack(pady=5)
        ctk.CTkLabel(f, text="W:", font=ctk.CTkFont(size=13), text_color="#aaa").pack(side="left", padx=4)
        w_var = ctk.StringVar(value=str(self.map_w))
        ctk.CTkEntry(f, textvariable=w_var, width=60, font=ctk.CTkFont(size=13)).pack(side="left", padx=4)
        ctk.CTkLabel(f, text="H:", font=ctk.CTkFont(size=13), text_color="#aaa").pack(side="left", padx=(16, 4))
        h_var = ctk.StringVar(value=str(self.map_h))
        ctk.CTkEntry(f, textvariable=h_var, width=60, font=ctk.CTkFont(size=13)).pack(side="left", padx=4)

        def apply():
            try:
                nw = max(5, min(100, int(w_var.get())))
                nh = max(5, min(100, int(h_var.get())))
            except ValueError:
                return
            self._save_undo()
            new_grid = [[TILE_FLOOR] * nw for _ in range(nh)]
            for y in range(min(nh, self.map_h)):
                for x in range(min(nw, self.map_w)):
                    new_grid[y][x] = self.grid_data[y][x]
            self.grid_data = new_grid
            self.map_w = nw
            self.map_h = nh
            # Remove enemies outside bounds
            self.enemies = [e for e in self.enemies
                           if 0 <= e["x"] < nw and 0 <= e["y"] < nh]
            if self.player_spawn[0] >= nw or self.player_spawn[1] >= nh:
                self.player_spawn = [1, 1]
            self._redraw()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Apply", width=120, height=34,
                      fg_color="#e94560", hover_color="#c73650",
                      font=ctk.CTkFont(size=13), command=apply).pack(pady=12)

    def _save_map_file(self):
        maps_dir = os.path.join(GAME_DIR, "maps")
        os.makedirs(maps_dir, exist_ok=True)

        path = ctk.filedialog.asksaveasfilename(
            initialdir=maps_dir,
            defaultextension=".json",
            filetypes=[("JSON Map", "*.json"), ("All Files", "*.*")]
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
        self.status_lbl.configure(text=f"Saved: {os.path.basename(path)}")

    def _load_map_file(self):
        maps_dir = os.path.join(GAME_DIR, "maps")
        os.makedirs(maps_dir, exist_ok=True)

        path = ctk.filedialog.askopenfilename(
            initialdir=maps_dir,
            filetypes=[("JSON Map", "*.json"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.grid_data = data["grid"]
            self.map_w = data["width"]
            self.map_h = data["height"]
            self.player_spawn = data.get("player_spawn", [2, 2])
            self.enemies = data.get("enemies", [])
            self.doors_open = data.get("doors_open", [])
            # Ensure patrol exists for all enemies
            for e in self.enemies:
                if "patrol" not in e:
                    e["patrol"] = [[e["x"], e["y"]]]
            self.selected_enemy_idx = None
            self.edit_mode = MODE_NORMAL
            self._update_mode_label()
            self._zoom_fit()
            self.status_lbl.configure(text=f"Loaded: {os.path.basename(path)}")
        except Exception as ex:
            self.status_lbl.configure(text=f"Error loading: {ex}")

    def _copy_to_game(self):
        maps_dir = os.path.join(GAME_DIR, "maps")
        os.makedirs(maps_dir, exist_ok=True)
        name = f"custom_{len(os.listdir(maps_dir))}.json"
        path = os.path.join(maps_dir, name)
        data = {
            "name": name.replace(".json", ""),
            "width": self.map_w,
            "height": self.map_h,
            "grid": self.grid_data,
            "doors_open": self.doors_open,
            "player_spawn": self.player_spawn,
            "enemies": self.enemies,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.status_lbl.configure(text=f"Copied to game: {name}")


if __name__ == "__main__":
    app = MapConstructor()
    app.mainloop()
