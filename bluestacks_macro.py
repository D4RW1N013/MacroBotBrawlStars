"""
BlueStacks Macro Tool
Steuert BlueStacks via Tastatur und Maus (pynput)
pip install pynput tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import json
import copy
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button as MouseButton, Controller as MouseController

# ── Farben ──────────────────────────────────────────────────────────────────
BG       = "#0d1117"
SURFACE  = "#161b22"
SURFACE2 = "#21262d"
BORDER   = "#30363d"
ACCENT   = "#238636"
ACCENT2  = "#2ea043"
DANGER   = "#da3633"
TEXT     = "#e6edf3"
TEXT_DIM = "#8b949e"
BLUE     = "#1f6feb"
YELLOW   = "#d29922"
ORANGE   = "#e3760c"

keyboard = KeyboardController()
mouse    = MouseController()

# ── Verfügbare Aktionen ──────────────────────────────────────────────────────
KEY_ACTIONS = {
    # Häufig genutzte Keys im BlueStacks Keymapper
    "Taste: A": "a", "Taste: B": "b", "Taste: C": "c", "Taste: D": "d",
    "Taste: E": "e", "Taste: F": "f", "Taste: G": "g", "Taste: H": "h",
    "Taste: I": "i", "Taste: J": "j", "Taste: K": "k", "Taste: L": "l",
    "Taste: M": "m", "Taste: N": "n", "Taste: O": "o", "Taste: P": "p",
    "Taste: Q": "q", "Taste: R": "r", "Taste: S": "s", "Taste: T": "t",
    "Taste: U": "u", "Taste: V": "v", "Taste: W": "w", "Taste: X": "x",
    "Taste: Y": "y", "Taste: Z": "z",
    "Taste: 0": "0", "Taste: 1": "1", "Taste: 2": "2", "Taste: 3": "3",
    "Taste: 4": "4", "Taste: 5": "5", "Taste: 6": "6", "Taste: 7": "7",
    "Taste: 8": "8", "Taste: 9": "9",
    "Leertaste":    "space",
    "Enter":        "enter",
    "Escape":       "escape",
    "Tab":          "tab",
    "Backspace":    "backspace",
    "Shift":        "shift",
    "Strg (Ctrl)":  "ctrl",
    "Alt":          "alt",
    "Pfeil Oben":   "up",
    "Pfeil Unten":  "down",
    "Pfeil Links":  "left",
    "Pfeil Rechts": "right",
    "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4",
    "F5": "f5", "F6": "f6", "F7": "f7", "F8": "f8",
    "Numpad 0": "num_lock", # Platzhalter – wird überschrieben
}

SPECIAL_KEY_MAP = {
    "space": Key.space, "enter": Key.enter, "escape": Key.esc,
    "tab": Key.tab, "backspace": Key.backspace, "shift": Key.shift,
    "ctrl": Key.ctrl, "alt": Key.alt,
    "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
    "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
    "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
}

MOUSE_ACTIONS = [
    "Maus: Linksklick",
    "Maus: Rechtsklick",
    "Maus: Mittelklick",
    "Maus: Bewegen (absolut)",
    "Maus: Scrollen Oben",
    "Maus: Scrollen Unten",
]

ALL_ACTIONS = list(KEY_ACTIONS.keys()) + MOUSE_ACTIONS

# ── Datenstrukturen ──────────────────────────────────────────────────────────
@dataclass
class MacroStep:
    action: str
    duration_ms: int   = 100
    delay_after_ms: int = 300
    mouse_x: int       = 0
    mouse_y: int       = 0

@dataclass
class MacroLoop:
    name: str
    steps: List[MacroStep] = field(default_factory=list)
    loop_timer_hours: float = 1.0
    repeat_count: int       = 0

# ── Hauptfenster ─────────────────────────────────────────────────────────────
class BlueStacksMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BlueStacks Macro Tool")
        self.root.geometry("1080x760")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self.loops: List[MacroLoop] = []
        self.selected_loop_idx: Optional[int] = None
        self.selected_step_idx: Optional[int] = None

        self.running      = False
        self.stop_event   = threading.Event()
        self.status_var   = tk.StringVar(value="Bereit")
        self.elapsed_var  = tk.StringVar(value="00:00:00")
        self.count_var    = tk.StringVar(value="Durchlaeufe: 0")
        self._elapsed_timer = None

        self._build_ui()
        self._style_tree()

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Titelleiste
        bar = tk.Frame(self.root, bg=SURFACE, height=50)
        bar.pack(fill="x")
        tk.Label(bar, text="⚡  BlueStacks Macro Tool",
                 bg=SURFACE, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(side="left", padx=16, pady=10)

        # Statusstreifen
        sb = tk.Frame(self.root, bg=SURFACE2, height=32)
        sb.pack(fill="x")
        self.status_lbl = tk.Label(sb, textvariable=self.status_var,
                                    bg=SURFACE2, fg=ACCENT2, font=("Segoe UI", 9, "bold"))
        self.status_lbl.pack(side="left", padx=14, pady=5)
        tk.Label(sb, textvariable=self.elapsed_var,
                 bg=SURFACE2, fg=TEXT_DIM, font=("Consolas", 9)).pack(side="left", padx=8)
        tk.Label(sb, textvariable=self.count_var,
                 bg=SURFACE2, fg=TEXT_DIM, font=("Segoe UI", 9)).pack(side="left", padx=8)

        countdown_frame = tk.Frame(sb, bg=SURFACE2)
        countdown_frame.pack(side="right", padx=14)
        tk.Label(countdown_frame, text="Startverzoegerung (s):",
                 bg=SURFACE2, fg=TEXT_DIM, font=("Segoe UI", 9)).pack(side="left")
        self.countdown_var = tk.IntVar(value=3)
        tk.Spinbox(countdown_frame, from_=0, to=30, width=4,
                   textvariable=self.countdown_var, bg=SURFACE2, fg=TEXT,
                   buttonbackground=SURFACE2, relief="flat",
                   font=("Segoe UI", 9)).pack(side="left", padx=4)

        # Hauptbereich
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=8)
        main.columnconfigure(0, weight=1, minsize=230)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(0, weight=1)

        # ── Links: Loop-Liste ──
        left = tk.Frame(main, bg=SURFACE)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        lh = tk.Frame(left, bg=SURFACE2)
        lh.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(lh, text="LOOPS", bg=SURFACE2, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=12, pady=7)
        self._btn(lh, "+ Neu", self._add_loop, ACCENT).pack(side="right", padx=6, pady=4)

        self.loop_lb = tk.Listbox(left, bg=SURFACE, fg=TEXT, selectbackground=BLUE,
                                   selectforeground=TEXT, font=("Segoe UI", 10),
                                   bd=0, highlightthickness=0, activestyle="none")
        self.loop_lb.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.loop_lb.bind("<<ListboxSelect>>", self._on_loop_sel)

        sc = ttk.Scrollbar(left, orient="vertical", command=self.loop_lb.yview)
        sc.grid(row=1, column=1, sticky="ns")
        self.loop_lb.configure(yscrollcommand=sc.set)

        br = tk.Frame(left, bg=SURFACE)
        br.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=4)
        self._btn(br, "⬆", self._loop_up, SURFACE2).pack(side="left", padx=2)
        self._btn(br, "⬇", self._loop_down, SURFACE2).pack(side="left", padx=2)
        self._btn(br, "📋", self._dup_loop, SURFACE2).pack(side="left", padx=2)
        self._btn(br, "🗑", self._del_loop, DANGER).pack(side="right", padx=2)

        # ── Rechts ──
        right = tk.Frame(main, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        # Loop-Einstellungen
        sf = tk.Frame(right, bg=SURFACE)
        sf.grid(row=0, column=0, sticky="ew", pady=(0,8))
        self._build_settings(sf)

        # Schritt-Bereich
        stf = tk.Frame(right, bg=SURFACE)
        stf.grid(row=1, column=0, sticky="nsew")
        stf.rowconfigure(1, weight=1)
        stf.columnconfigure(0, weight=1)

        sh = tk.Frame(stf, bg=SURFACE2)
        sh.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(sh, text="SCHRITTE", bg=SURFACE2, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=12, pady=7)
        self._btn(sh, "+ Schritt", self._add_step, ACCENT).pack(side="right", padx=6, pady=4)

        cols = ("Nr.", "Aktion", "Dauer (ms)", "Verzög. (ms)", "X", "Y")
        self.tree = ttk.Treeview(stf, columns=cols, show="headings",
                                  selectmode="browse", height=14)
        widths = [36, 200, 90, 100, 60, 60]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.tree.bind("<<TreeviewSelect>>", self._on_step_sel)
        self.tree.bind("<Double-1>", lambda e: self._edit_step())

        ts = ttk.Scrollbar(stf, orient="vertical", command=self.tree.yview)
        ts.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=ts.set)

        sbr = tk.Frame(stf, bg=SURFACE)
        sbr.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=4)
        self._btn(sbr, "✏ Bearbeiten", self._edit_step, BLUE).pack(side="left", padx=2)
        self._btn(sbr, "⬆", self._step_up, SURFACE2).pack(side="left", padx=2)
        self._btn(sbr, "⬇", self._step_down, SURFACE2).pack(side="left", padx=2)
        self._btn(sbr, "📋", self._dup_step, SURFACE2).pack(side="left", padx=2)
        self._btn(sbr, "🗑 Löschen", self._del_step, DANGER).pack(side="right", padx=2)

        # ── Bottom ──
        bot = tk.Frame(self.root, bg=SURFACE, height=52)
        bot.pack(fill="x", side="bottom")
        self._btn(bot, "▶  START", self._start, ACCENT,
                  font=("Segoe UI", 11, "bold"), padx=20).pack(side="left", padx=10, pady=8)
        self._btn(bot, "⏹  STOP", self._stop, DANGER,
                  font=("Segoe UI", 11, "bold"), padx=20).pack(side="left", padx=4, pady=8)

        tk.Label(bot, text="BlueStacks muss im Fokus sein beim Start!",
                 bg=SURFACE, fg=YELLOW, font=("Segoe UI", 8)).pack(side="left", padx=16)

        self._btn(bot, "💾 Speichern", self._save, SURFACE2).pack(side="right", padx=10, pady=8)
        self._btn(bot, "📂 Laden", self._load, SURFACE2).pack(side="right", padx=4, pady=8)

    def _build_settings(self, parent):
        tk.Label(parent, text="LOOP EINSTELLUNGEN", bg=SURFACE, fg=TEXT_DIM,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, columnspan=8,
                                                     sticky="w", padx=12, pady=(8,2))
        def lbl(text, col):
            tk.Label(parent, text=text, bg=SURFACE, fg=TEXT_DIM,
                     font=("Segoe UI", 9)).grid(row=1, column=col, padx=(12,3), pady=6, sticky="e")

        lbl("Name:", 0)
        self.name_var = tk.StringVar()
        e = tk.Entry(parent, textvariable=self.name_var, bg=SURFACE2, fg=TEXT,
                     insertbackground=TEXT, font=("Segoe UI", 10), relief="flat", bd=4, width=16)
        e.grid(row=1, column=1, padx=4, pady=6)
        self.name_var.trace_add("write", lambda *a: self._sync_name())

        lbl("Timer (Std.):", 2)
        self.timer_var = tk.DoubleVar(value=1.0)
        tk.Spinbox(parent, from_=0, to=48, increment=0.5, width=6,
                   textvariable=self.timer_var, bg=SURFACE2, fg=TEXT,
                   buttonbackground=SURFACE2, relief="flat",
                   font=("Segoe UI", 10)).grid(row=1, column=3, padx=4)
        tk.Label(parent, text="(0=∞)", bg=SURFACE, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).grid(row=1, column=4, sticky="w")

        lbl("Wiederh.:", 5)
        self.repeat_var = tk.IntVar(value=0)
        tk.Spinbox(parent, from_=0, to=999999, increment=1, width=8,
                   textvariable=self.repeat_var, bg=SURFACE2, fg=TEXT,
                   buttonbackground=SURFACE2, relief="flat",
                   font=("Segoe UI", 10)).grid(row=1, column=6, padx=4)
        tk.Label(parent, text="(0=timer)", bg=SURFACE, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).grid(row=1, column=7, sticky="w")

        self._btn(parent, "✔ OK", self._apply_settings, BLUE).grid(
            row=1, column=8, padx=12, pady=6)

    def _btn(self, p, text, cmd, bg, font=("Segoe UI", 9), padx=10, pady=4):
        return tk.Button(p, text=text, command=cmd, bg=bg, fg=TEXT,
                         activebackground=bg, activeforeground=TEXT,
                         font=font, relief="flat", bd=0,
                         padx=padx, pady=pady, cursor="hand2")

    def _style_tree(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Treeview", background=SURFACE, foreground=TEXT,
                    fieldbackground=SURFACE, rowheight=25,
                    font=("Segoe UI", 9), borderwidth=0)
        s.configure("Treeview.Heading", background=SURFACE2, foreground=TEXT_DIM,
                    font=("Segoe UI", 9, "bold"), relief="flat")
        s.map("Treeview", background=[("selected", BLUE)])
        s.configure("Vertical.TScrollbar", background=SURFACE2,
                    troughcolor=SURFACE, arrowcolor=TEXT_DIM, borderwidth=0)

    # ── Loop-Ops ─────────────────────────────────────────────────────────────
    def _add_loop(self):
        l = MacroLoop(name=f"Loop {len(self.loops)+1}")
        self.loops.append(l)
        self._refresh_loops()
        self.loop_lb.selection_set(len(self.loops)-1)
        self._on_loop_sel()

    def _del_loop(self):
        if self.selected_loop_idx is None: return
        if messagebox.askyesno("Löschen", "Loop löschen?"):
            self.loops.pop(self.selected_loop_idx)
            self.selected_loop_idx = None
            self._refresh_loops()
            self._refresh_steps()

    def _dup_loop(self):
        if self.selected_loop_idx is None: return
        l = copy.deepcopy(self.loops[self.selected_loop_idx])
        l.name += " (Kopie)"
        self.loops.insert(self.selected_loop_idx+1, l)
        self._refresh_loops()

    def _loop_up(self):
        i = self.selected_loop_idx
        if i is None or i == 0: return
        self.loops[i], self.loops[i-1] = self.loops[i-1], self.loops[i]
        self.selected_loop_idx = i-1
        self._refresh_loops()
        self.loop_lb.selection_set(i-1)

    def _loop_down(self):
        i = self.selected_loop_idx
        if i is None or i >= len(self.loops)-1: return
        self.loops[i], self.loops[i+1] = self.loops[i+1], self.loops[i]
        self.selected_loop_idx = i+1
        self._refresh_loops()
        self.loop_lb.selection_set(i+1)

    def _refresh_loops(self):
        self.loop_lb.delete(0, "end")
        for l in self.loops:
            t = f"{l.loop_timer_hours}h" if l.loop_timer_hours > 0 else "∞"
            self.loop_lb.insert("end", f"  {l.name}  [{len(l.steps)} Schr. | {t}]")

    def _on_loop_sel(self, e=None):
        sel = self.loop_lb.curselection()
        if not sel: return
        self.selected_loop_idx = sel[0]
        l = self.loops[self.selected_loop_idx]
        self.name_var.set(l.name)
        self.timer_var.set(l.loop_timer_hours)
        self.repeat_var.set(l.repeat_count)
        self._refresh_steps()

    def _sync_name(self):
        if self.selected_loop_idx is None: return
        self.loops[self.selected_loop_idx].name = self.name_var.get()
        self._refresh_loops()
        self.loop_lb.selection_set(self.selected_loop_idx)

    def _apply_settings(self):
        if self.selected_loop_idx is None:
            messagebox.showinfo("Hinweis", "Erst einen Loop auswaehlen.")
            return
        l = self.loops[self.selected_loop_idx]
        l.name = self.name_var.get()
        try: l.loop_timer_hours = float(self.timer_var.get())
        except: pass
        try: l.repeat_count = int(self.repeat_var.get())
        except: pass
        self._refresh_loops()
        self.loop_lb.selection_set(self.selected_loop_idx)

    # ── Schritt-Ops ──────────────────────────────────────────────────────────
    def _add_step(self):
        if self.selected_loop_idx is None:
            messagebox.showinfo("Hinweis", "Erst einen Loop auswaehlen.")
            return
        self._step_dialog(None)

    def _edit_step(self):
        if self.selected_loop_idx is None or self.selected_step_idx is None: return
        self._step_dialog(self.selected_step_idx)

    def _del_step(self):
        if self.selected_loop_idx is None or self.selected_step_idx is None: return
        self.loops[self.selected_loop_idx].steps.pop(self.selected_step_idx)
        self.selected_step_idx = None
        self._refresh_steps()
        self._refresh_loops()

    def _dup_step(self):
        if self.selected_loop_idx is None or self.selected_step_idx is None: return
        s = copy.deepcopy(self.loops[self.selected_loop_idx].steps[self.selected_step_idx])
        self.loops[self.selected_loop_idx].steps.insert(self.selected_step_idx+1, s)
        self._refresh_steps()
        self._refresh_loops()

    def _step_up(self):
        i = self.selected_step_idx
        steps = self.loops[self.selected_loop_idx].steps
        if i is None or i == 0: return
        steps[i], steps[i-1] = steps[i-1], steps[i]
        self.selected_step_idx = i-1
        self._refresh_steps()
        self.tree.selection_set(self.tree.get_children()[i-1])

    def _step_down(self):
        i = self.selected_step_idx
        steps = self.loops[self.selected_loop_idx].steps
        if i is None or i >= len(steps)-1: return
        steps[i], steps[i+1] = steps[i+1], steps[i]
        self.selected_step_idx = i+1
        self._refresh_steps()
        self.tree.selection_set(self.tree.get_children()[i+1])

    def _on_step_sel(self, e=None):
        sel = self.tree.selection()
        if not sel: return
        self.selected_step_idx = list(self.tree.get_children()).index(sel[0])

    def _refresh_steps(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self.selected_loop_idx is None: return
        for i, s in enumerate(self.loops[self.selected_loop_idx].steps):
            xy = (s.mouse_x, s.mouse_y) if "Maus" in s.action else ("-", "-")
            self.tree.insert("", "end", values=(i+1, s.action, s.duration_ms,
                                                 s.delay_after_ms, xy[0], xy[1]))

    # ── Schritt-Dialog ────────────────────────────────────────────────────────
    def _step_dialog(self, idx):
        ex = self.loops[self.selected_loop_idx].steps[idx] if idx is not None else None

        dlg = tk.Toplevel(self.root)
        dlg.title("Schritt" + (" bearbeiten" if idx is not None else " hinzufügen"))
        dlg.configure(bg=SURFACE)
        dlg.geometry("430x320")
        dlg.grab_set()
        dlg.resizable(False, False)

        def row(r, label, widget_fn, col=1):
            tk.Label(dlg, text=label, bg=SURFACE, fg=TEXT_DIM,
                     font=("Segoe UI", 9)).grid(row=r, column=0, padx=18, pady=7, sticky="e")
            w = widget_fn()
            w.grid(row=r, column=col, padx=10, pady=7, sticky="w")
            return w

        # Aktion
        act_var = tk.StringVar(value=ex.action if ex else ALL_ACTIONS[0])
        tk.Label(dlg, text="Aktion:", bg=SURFACE, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).grid(row=0, column=0, padx=18, pady=(18,7), sticky="e")
        cb = ttk.Combobox(dlg, textvariable=act_var, values=ALL_ACTIONS,
                           font=("Segoe UI", 10), width=24, state="readonly")
        cb.grid(row=0, column=1, columnspan=2, padx=10, pady=(18,7), sticky="w")

        # Dauer
        dur_var = tk.IntVar(value=ex.duration_ms if ex else 100)
        tk.Label(dlg, text="Dauer gedrückt (ms):", bg=SURFACE, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).grid(row=1, column=0, padx=18, pady=7, sticky="e")
        tk.Spinbox(dlg, from_=1, to=60000, increment=50, textvariable=dur_var,
                   bg=SURFACE2, fg=TEXT, insertbackground=TEXT, buttonbackground=SURFACE2,
                   relief="flat", font=("Segoe UI", 10), width=10
                   ).grid(row=1, column=1, padx=10, pady=7, sticky="w")

        # Verzögerung
        del_var = tk.IntVar(value=ex.delay_after_ms if ex else 300)
        tk.Label(dlg, text="Verzögerung danach (ms):", bg=SURFACE, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).grid(row=2, column=0, padx=18, pady=7, sticky="e")
        tk.Spinbox(dlg, from_=0, to=60000, increment=50, textvariable=del_var,
                   bg=SURFACE2, fg=TEXT, insertbackground=TEXT, buttonbackground=SURFACE2,
                   relief="flat", font=("Segoe UI", 10), width=10
                   ).grid(row=2, column=1, padx=10, pady=7, sticky="w")

        # Maus X/Y (nur bei Maus-Aktionen)
        mx_var = tk.IntVar(value=ex.mouse_x if ex else 0)
        my_var = tk.IntVar(value=ex.mouse_y if ex else 0)

        xy_frame = tk.Frame(dlg, bg=SURFACE)
        xy_frame.grid(row=3, column=0, columnspan=3, padx=18, pady=4, sticky="w")
        mx_lbl = tk.Label(xy_frame, text="X:", bg=SURFACE, fg=TEXT_DIM, font=("Segoe UI", 9))
        mx_sp  = tk.Spinbox(xy_frame, from_=0, to=9999, textvariable=mx_var,
                             bg=SURFACE2, fg=TEXT, buttonbackground=SURFACE2,
                             relief="flat", font=("Segoe UI", 10), width=7)
        my_lbl = tk.Label(xy_frame, text="Y:", bg=SURFACE, fg=TEXT_DIM, font=("Segoe UI", 9))
        my_sp  = tk.Spinbox(xy_frame, from_=0, to=9999, textvariable=my_var,
                             bg=SURFACE2, fg=TEXT, buttonbackground=SURFACE2,
                             relief="flat", font=("Segoe UI", 10), width=7)
        pick_btn = tk.Button(xy_frame, text="🎯 Position wählen",
                              bg=BLUE, fg=TEXT, relief="flat", font=("Segoe UI", 9),
                              padx=8, pady=2, cursor="hand2",
                              command=lambda: self._pick_mouse_pos(mx_var, my_var, dlg))

        def toggle_xy(*args):
            if "Maus" in act_var.get() and "Bewegen" in act_var.get():
                mx_lbl.pack(side="left", padx=(0,4))
                mx_sp.pack(side="left", padx=(0,8))
                my_lbl.pack(side="left", padx=(0,4))
                my_sp.pack(side="left", padx=(0,8))
                pick_btn.pack(side="left")
            else:
                mx_lbl.pack_forget(); mx_sp.pack_forget()
                my_lbl.pack_forget(); my_sp.pack_forget()
                pick_btn.pack_forget()

        act_var.trace_add("write", toggle_xy)
        toggle_xy()

        # Info
        tk.Label(dlg, text="Dauer: wie lange Taste/Klick gehalten wird.\nVerzögerung: Pause vor dem nächsten Schritt.",
                 bg=SURFACE, fg=TEXT_DIM, font=("Segoe UI", 8), justify="left"
                 ).grid(row=4, column=0, columnspan=3, padx=18, pady=(4,0), sticky="w")

        def save():
            step = MacroStep(
                action=act_var.get(),
                duration_ms=dur_var.get(),
                delay_after_ms=del_var.get(),
                mouse_x=mx_var.get(),
                mouse_y=my_var.get(),
            )
            loop = self.loops[self.selected_loop_idx]
            if idx is not None:
                loop.steps[idx] = step
            else:
                loop.steps.append(step)
            self._refresh_steps()
            self._refresh_loops()
            dlg.destroy()

        brow = tk.Frame(dlg, bg=SURFACE)
        brow.grid(row=5, column=0, columnspan=3, pady=14)
        self._btn(brow, "✔ Speichern", save, ACCENT).pack(side="left", padx=8)
        self._btn(brow, "Abbrechen", dlg.destroy, SURFACE2).pack(side="left", padx=8)

    def _pick_mouse_pos(self, mx_var, my_var, dlg):
        """3-Sekunden-Countdown, dann aktuelle Mausposition übernehmen"""
        dlg.withdraw()
        pick_win = tk.Toplevel(self.root)
        pick_win.configure(bg=SURFACE)
        pick_win.geometry("300x100")
        pick_win.title("Position wählen")
        pick_win.attributes("-topmost", True)
        lbl = tk.Label(pick_win, text="Maus über BlueStacks bewegen...\nPosition wird in 3s übernommen.",
                        bg=SURFACE, fg=TEXT, font=("Segoe UI", 10))
        lbl.pack(expand=True)

        def capture():
            for i in range(3, 0, -1):
                lbl.config(text=f"Position wird in {i}s übernommen...\nMaus JETZT positionieren!")
                time.sleep(1)
            pos = mouse.position
            mx_var.set(int(pos[0]))
            my_var.set(int(pos[1]))
            pick_win.destroy()
            dlg.deiconify()

        threading.Thread(target=capture, daemon=True).start()

    # ── Macro ausführen ───────────────────────────────────────────────────────
    def _start(self):
        if self.running:
            messagebox.showinfo("Info", "Macro läuft bereits.")
            return
        if not self.loops or not any(l.steps for l in self.loops):
            messagebox.showinfo("Hinweis", "Keine Schritte vorhanden.")
            return

        self.running = True
        self.stop_event.clear()
        self._set_status("Warte auf Start...", YELLOW)
        threading.Thread(target=self._run, daemon=True).start()

    def _stop(self):
        self.stop_event.set()
        self.running = False
        if self._elapsed_timer:
            self.root.after_cancel(self._elapsed_timer)
        self._set_status("Gestoppt", YELLOW)

    def _run(self):
        # Countdown
        cd = self.countdown_var.get()
        for i in range(cd, 0, -1):
            if self.stop_event.is_set(): return
            self.root.after(0, self._set_status, f"Start in {i}s ... (BlueStacks fokussieren!)", YELLOW)
            time.sleep(1)

        self.root.after(0, self._set_status, "Läuft...", ACCENT2)
        self._elapsed_start = time.time()
        self.root.after(0, self._tick)

        total = 0
        for loop in self.loops:
            if self.stop_event.is_set(): break
            if not loop.steps: continue

            deadline = None
            if loop.loop_timer_hours > 0 and loop.repeat_count == 0:
                deadline = time.time() + loop.loop_timer_hours * 3600

            it = 0
            while not self.stop_event.is_set():
                if deadline and time.time() >= deadline: break
                if loop.repeat_count > 0 and it >= loop.repeat_count: break

                for step in loop.steps:
                    if self.stop_event.is_set(): break
                    self._exec(step)

                it += 1
                total += 1
                self.root.after(0, self.count_var.set, f"Durchlaeufe: {total}")

        if not self.stop_event.is_set():
            self.root.after(0, self._set_status, "Fertig ✔", ACCENT2)
        self.running = False

    def _exec(self, step: MacroStep):
        action = step.action
        dur    = step.duration_ms / 1000.0
        delay  = step.delay_after_ms / 1000.0

        try:
            if action in MOUSE_ACTIONS:
                if action == "Maus: Linksklick":
                    mouse.press(MouseButton.left)
                    self._sleep(dur)
                    mouse.release(MouseButton.left)
                elif action == "Maus: Rechtsklick":
                    mouse.press(MouseButton.right)
                    self._sleep(dur)
                    mouse.release(MouseButton.right)
                elif action == "Maus: Mittelklick":
                    mouse.press(MouseButton.middle)
                    self._sleep(dur)
                    mouse.release(MouseButton.middle)
                elif action == "Maus: Bewegen (absolut)":
                    mouse.position = (step.mouse_x, step.mouse_y)
                    self._sleep(dur)
                elif action == "Maus: Scrollen Oben":
                    mouse.scroll(0, 3)
                elif action == "Maus: Scrollen Unten":
                    mouse.scroll(0, -3)
            elif action in KEY_ACTIONS:
                key_str = KEY_ACTIONS[action]
                key = SPECIAL_KEY_MAP.get(key_str, key_str)
                keyboard.press(key)
                self._sleep(dur)
                keyboard.release(key)
        except Exception as ex:
            print(f"Fehler bei '{action}': {ex}")

        if delay > 0:
            self._sleep(delay)

    def _sleep(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            if self.stop_event.is_set(): return
            time.sleep(min(0.015, end - time.time()))

    def _tick(self):
        if not self.running: return
        e = int(time.time() - self._elapsed_start)
        h, m, s = e // 3600, (e % 3600) // 60, e % 60
        self.elapsed_var.set(f"{h:02}:{m:02}:{s:02}")
        self._elapsed_timer = self.root.after(1000, self._tick)

    def _set_status(self, text, color=TEXT):
        self.status_var.set(text)
        self.status_lbl.configure(fg=color)

    # ── Speichern/Laden ───────────────────────────────────────────────────────
    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            title="Profil speichern")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(l) for l in self.loops], f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Gespeichert", path)

    def _load(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")], title="Profil laden")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.loops = []
            for ld in data:
                steps = [MacroStep(**s) for s in ld.get("steps", [])]
                self.loops.append(MacroLoop(
                    name=ld["name"], steps=steps,
                    loop_timer_hours=ld.get("loop_timer_hours", 1.0),
                    repeat_count=ld.get("repeat_count", 0)))
            self._refresh_loops()
            self.selected_loop_idx = None
            self.selected_step_idx = None
            self._refresh_steps()
            messagebox.showinfo("Geladen", path)
        except Exception as e:
            messagebox.showerror("Fehler", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    BlueStacksMacroApp(root)
    root.mainloop()
