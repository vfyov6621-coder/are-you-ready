#!/usr/bin/env python3
"""ARE YOU READY? - Launcher (CustomTkinter)"""
import os, sys, subprocess
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GAME_DIR); os.chdir(GAME_DIR)
import customtkinter as ctk
ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ARE YOU READY?"); self.geometry("520x600"); self.resizable(False, False)
        self.configure(fg_color=("#1a1a2e", "#1a1a2e"))
        self._build()
    def _build(self):
        ctk.CTkLabel(self, text="ARE YOU READY?", font=ctk.CTkFont(family="Impact", size=48), text_color="#e94560").pack(pady=(40,0))
        ctk.CTkLabel(self, text="TACTICAL SPECIAL FORCES", font=ctk.CTkFont(size=14), text_color="#555570").pack(pady=(0,30))
        ctk.CTkFrame(self, height=2, fg_color="#333355").pack(fill="x", padx=40, pady=5)
        ctk.CTkLabel(self, text="SELECT MAP", font=ctk.CTkFont(size=13, weight="bold"), text_color="#888899").pack(pady=(20,5))
        maps = self._find_maps()
        self.map_var = ctk.StringVar(value=maps[0] if maps else "")
        if maps:
            self.map_combo = ctk.CTkComboBox(self, variable=self.map_var, values=maps, font=ctk.CTkFont(size=14), width=320, button_color="#333355", dropdown_fg_color="#16213e")
            self.map_combo.pack(pady=5)
        self.info_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), text_color="#555570"); self.info_lbl.pack(pady=(10,0))
        if maps: self._show_info(maps[0])
        self.map_combo.bind("<<ComboboxSelected>>", lambda e: self._show_info(self.map_var.get()))
        ctk.CTkFrame(self, height=2, fg_color="#333355").pack(fill="x", padx=40, pady=20)
        bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(pady=10)
        self.play_btn = ctk.CTkButton(bf, text="START MISSION", font=ctk.CTkFont(size=16, weight="bold"), width=280, height=48, fg_color="#e94560", hover_color="#c73650", corner_radius=10, command=self._start)
        self.play_btn.pack(pady=8)
        ctk.CTkButton(bf, text="MAP CONSTRUCTOR", font=ctk.CTkFont(size=13), width=280, height=38, fg_color="#333355", hover_color="#444470", corner_radius=8, command=self._constructor).pack(pady=4)
        ctk.CTkButton(bf, text="QUIT", font=ctk.CTkFont(size=13), width=280, height=38, fg_color="#16213e", hover_color="#0f3460", corner_radius=8, command=self.destroy).pack(pady=4)
        ctk.CTkFrame(self, height=2, fg_color="#333355").pack(fill="x", padx=40, pady=15)
        ctk.CTkLabel(self, text="WASD-Move|E-Interact|LMB-Shoot|ESC-Pause", font=ctk.CTkFont(size=10), text_color="#444460").pack(pady=(0,10))
    def _find_maps(self):
        md = os.path.join(GAME_DIR, "maps"); os.makedirs(md, exist_ok=True)
        dp = os.path.join(md, ".json")
        if not os.path.exists(dp):
            from play import create_default_map; create_default_map(dp)
        return sorted([f for f in os.listdir(md) if f.endswith(".json")]) or ["default.json"]
    def _show_info(self, name):
        try:
            import json
            with open(os.path.join(GAME_DIR, "maps", name)) as f: d = json.load(f)
            g = d.get("grid", [[]]); e = len(d.get("enemies", []))
            self.info_lbl.configure(text=f"Size: {len(g[0]) if g else 0}x{len(g)}  |  Enemies: {e}")
        except: self.info_lbl.configure(text="")
    def _start(self):
        mn = self.map_var.get()
        if not mn: return
        self.play_btn.configure(state="disabled", text="LAUNCHING..."); self.update()
        mp = os.path.join(GAME_DIR, "maps", mn); ps = os.path.join(GAME_DIR, "play.py")
        self.withdraw()
        try: subprocess.run([sys.executable, ps, mp])
        except Exception as ex: print(f"Error: {ex}")
        self.deiconify(); self.play_btn.configure(state="normal", text="START MISSION")
    def _constructor(self):
        cd = os.path.join(os.path.dirname(GAME_DIR), "constructor")
        cm = os.path.join(cd, "main.py")
        if os.path.exists(cm): subprocess.Popen([sys.executable, cm])

if __name__ == "__main__": App().mainloop()
