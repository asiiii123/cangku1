"""
桌面番茄钟 — 原生 Windows 桌面应用 (Python + tkinter)
双击运行或命令行: python pomodoro.py
"""

import tkinter as tk
from tkinter import ttk
import math
import json
import threading
import winsound
from pathlib import Path

# ── 配色 ──────────────────────────────────────────────────
BG          = "#0f0f14"
SURFACE     = "#1a1a24"
SURFACE2    = "#252536"
TEXT        = "#e8e8ed"
TEXT_DIM    = "#8888a0"
ACCENT      = "#ff6b6b"
ACCENT_HI   = "#ff8787"
BREAK_CLR   = "#4ecdc4"
BREAK_HI    = "#6ee7de"
RING_BG     = "#252536"
DOT_EMPTY   = "#2a2a3a"


class PomodoroApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("番茄钟")
        self.root.geometry("400x600")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.minsize(360, 540)

        # 居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 400, 600
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # ── 状态 ──────────────────────────────────────────
        self.mode = "pomodoro"
        self.running = False
        self.paused = False
        self.remaining = 25 * 60
        self.total = 25 * 60
        self.completed = 0
        self.timer_id = None
        self.half_notified = False

        # ── 配置 ──────────────────────────────────────────
        self.config_file = Path(__file__).parent / "pomodoro_config.json"
        self.config = self._load_config()

        # ── 构建界面 ──────────────────────────────────────
        self._build_ui()
        self._apply_mode()

        # ── 关闭事件 ──────────────────────────────────────
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══════════════════════════════════════════════════════
    # 配置读写
    # ══════════════════════════════════════════════════════

    def _load_config(self):
        defaults = {
            "pomodoro": 25, "shortBreak": 5,
            "longBreak": 15, "longBreakInterval": 4,
            "alwaysOnTop": False,
        }
        try:
            if self.config_file.exists():
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                defaults.update(data)
        except Exception:
            pass
        return defaults

    def _save_config(self):
        try:
            self.config_file.write_text(
                json.dumps(self.config, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ══════════════════════════════════════════════════════
    # UI 构建
    # ══════════════════════════════════════════════════════

    def _build_ui(self):
        container = tk.Frame(self.root, bg=BG)
        container.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        # ── 模式切换标签 ──────────────────────────────────
        tab_frame = tk.Frame(container, bg=SURFACE)
        tab_frame.pack(fill=tk.X, pady=(0, 28))
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_columnconfigure(1, weight=1)
        tab_frame.grid_columnconfigure(2, weight=1)

        self.tab_buttons = {}
        modes = [("pomodoro", "专注"), ("shortBreak", "短休"), ("longBreak", "长休")]
        for idx, (key, label) in enumerate(modes):
            btn = tk.Button(
                tab_frame, text=label,
                font=("Microsoft YaHei UI", 11),
                relief=tk.FLAT, borderwidth=0,
                cursor="hand2", padx=16, pady=8,
                command=lambda k=key: self._set_mode(k),
            )
            btn.grid(row=0, column=idx, sticky="ew", padx=2, pady=2)
            self.tab_buttons[key] = btn

        # ── 环形进度 Canvas ───────────────────────────────
        self.cv_size = 250
        self.canvas = tk.Canvas(
            container, width=self.cv_size, height=self.cv_size,
            bg=BG, highlightthickness=0,
        )
        self.canvas.pack(pady=(0, 8))

        # 时间 / 状态文字
        self.lbl_time = tk.Label(
            self.canvas, text="25:00",
            font=("Consolas", 46, "bold"),
            fg=TEXT, bg=BG,
        )
        self.lbl_time.place(relx=0.5, rely=0.43, anchor=tk.CENTER)

        self.lbl_status = tk.Label(
            self.canvas, text="准备开始",
            font=("Microsoft YaHei UI", 10),
            fg=TEXT_DIM, bg=BG,
        )
        self.lbl_status.place(relx=0.5, rely=0.62, anchor=tk.CENTER)

        self._draw_ring(1.0)

        # ── 控制按钮 ──────────────────────────────────────
        ctrl = tk.Frame(container, bg=BG)
        ctrl.pack(pady=(0, 20))

        self.btn_reset = tk.Button(
            ctrl, text="↻", font=("", 16),
            relief=tk.FLAT, borderwidth=0, cursor="hand2",
            fg=TEXT_DIM, bg=SURFACE,
            activebackground=SURFACE2, activeforeground=TEXT,
            width=3, height=1, command=self._reset,
        )
        self.btn_reset.pack(side=tk.LEFT, padx=6)

        self.btn_play = tk.Button(
            ctrl, text="▶", font=("", 20),
            relief=tk.FLAT, borderwidth=0, cursor="hand2",
            fg="white", bg=ACCENT,
            activebackground=ACCENT_HI, activeforeground="white",
            width=3, height=1, command=self._toggle_play,
        )
        self.btn_play.pack(side=tk.LEFT, padx=6)

        self.btn_skip = tk.Button(
            ctrl, text="⏭", font=("", 16),
            relief=tk.FLAT, borderwidth=0, cursor="hand2",
            fg=TEXT_DIM, bg=SURFACE,
            activebackground=SURFACE2, activeforeground=TEXT,
            width=3, height=1, command=self._skip,
        )
        self.btn_skip.pack(side=tk.LEFT, padx=6)

        # ── 番茄计数圆点 ──────────────────────────────────
        self.dots_canvas = tk.Canvas(
            container, width=200, height=18,
            bg=BG, highlightthickness=0,
        )
        self.dots_canvas.pack(pady=(0, 16))
        self._update_dots()

        # ── 设置按钮 ──────────────────────────────────────
        self.btn_settings = tk.Button(
            container, text="⚙ 设置",
            font=("Microsoft YaHei UI", 10),
            fg=TEXT_DIM, bg=BG,
            activeforeground=TEXT, activebackground=BG,
            relief=tk.FLAT, cursor="hand2",
            command=self._toggle_settings,
        )
        self.btn_settings.pack()

        # ── 设置面板 ──────────────────────────────────────
        self.settings_frame = tk.Frame(container, bg=SURFACE)

        fields = [
            ("专注时长 (分钟)", "pomodoro", 1, 120),
            ("短休时长 (分钟)", "shortBreak", 1, 60),
            ("长休时长 (分钟)", "longBreak", 1, 60),
            ("长休间隔 (番茄数)", "longBreakInterval", 1, 10),
        ]
        self._spin_vars = {}

        for label, key, lo, hi in fields:
            row = tk.Frame(self.settings_frame, bg=SURFACE)
            row.pack(fill=tk.X, padx=18, pady=5)

            tk.Label(
                row, text=label, font=("Microsoft YaHei UI", 10),
                fg=TEXT_DIM, bg=SURFACE,
            ).pack(side=tk.LEFT)

            var = tk.IntVar(value=self.config[key])
            self._spin_vars[key] = var
            var.trace_add("write", lambda *a, k=key: self._on_setting_change(k))

            sp = tk.Spinbox(
                row, textvariable=var, from_=lo, to=to,
                width=6, font=("Consolas", 12),
                fg=TEXT, bg=SURFACE2,
                buttonbackground=SURFACE2,
                relief=tk.FLAT, borderwidth=0,
                justify=tk.CENTER, increment=1,
                command=lambda k=key: self._on_setting_change(k),
            )
            sp.pack(side=tk.RIGHT)

        # 置顶开关
        row = tk.Frame(self.settings_frame, bg=SURFACE)
        row.pack(fill=tk.X, padx=18, pady=5)
        tk.Label(
            row, text="窗口置顶", font=("Microsoft YaHei UI", 10),
            fg=TEXT_DIM, bg=SURFACE,
        ).pack(side=tk.LEFT)

        self.top_var = tk.BooleanVar(value=self.config.get("alwaysOnTop", False))
        cb = tk.Checkbutton(
            row, variable=self.top_var,
            bg=SURFACE, fg=TEXT,
            activebackground=SURFACE, activeforeground=TEXT,
            selectcolor=SURFACE2,
            command=self._toggle_always_on_top,
        )
        cb.pack(side=tk.RIGHT)

    # ══════════════════════════════════════════════════════
    # 环形进度条
    # ══════════════════════════════════════════════════════

    def _draw_ring(self, ratio):
        self.canvas.delete("ring")
        cx = cy = self.cv_size // 2
        r = 115
        sw = 7

        # 背景圆
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=RING_BG, width=sw,
            tags="ring",
        )

        if ratio <= 0:
            return

        angle = 360 * ratio
        color = ACCENT if self.mode == "pomodoro" else BREAK_CLR
        # start=90 → 12 点钟方向, extent 为负 = 逆时针
        self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=-angle,
            outline=color, width=sw,
            style="arc", tags="ring",
        )

    # ══════════════════════════════════════════════════════
    # 模式
    # ══════════════════════════════════════════════════════

    def _apply_mode(self):
        mmap = {
            "pomodoro": self.config["pomodoro"],
            "shortBreak": self.config["shortBreak"],
            "longBreak": self.config["longBreak"],
        }
        self.total = mmap[self.mode] * 60
        self.remaining = self.total
        self.half_notified = False

        for key, btn in self.tab_buttons.items():
            if key == self.mode:
                btn.configure(bg=SURFACE2, fg=TEXT)
            else:
                btn.configure(bg=SURFACE, fg=TEXT_DIM)

        self._update_display()
        self._update_status()
        self._update_dots()
        self._update_play_button()

    def _set_mode(self, mode):
        if self.running:
            self._stop_timer()
        self.mode = mode
        self._apply_mode()

    # ══════════════════════════════════════════════════════
    # 计时控制
    # ══════════════════════════════════════════════════════

    def _toggle_play(self):
        if self.running:
            self._pause()
        else:
            self._start()

    def _start(self):
        if self.running:
            return
        self.running = True
        self.paused = False
        self._update_play_button()
        self._update_status()
        self._tick()

    def _pause(self):
        if not self.running:
            return
        self.running = False
        self.paused = True
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self._update_play_button()
        self._update_status()

    def _stop_timer(self):
        self.running = False
        self.paused = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    def _reset(self):
        self._stop_timer()
        mmap = {
            "pomodoro": self.config["pomodoro"],
            "shortBreak": self.config["shortBreak"],
            "longBreak": self.config["longBreak"],
        }
        self.total = mmap[self.mode] * 60
        self.remaining = self.total
        self.half_notified = False
        self._update_play_button()
        self._update_display()
        self._update_status()

    def _skip(self):
        self._stop_timer()
        self.remaining = 0
        self._finish()

    def _tick(self):
        if not self.running:
            return
        if self.remaining <= 0:
            self._finish()
            return

        self.remaining -= 1
        self._update_display()

        if not self.half_notified and self.mode == "pomodoro":
            if self.remaining <= self.total // 2:
                self.half_notified = True
                self._beep_async(660, 80)

        self.timer_id = self.root.after(1000, self._tick)

    def _finish(self):
        self._stop_timer()

        if self.mode == "pomodoro":
            self.completed += 1
            self._update_dots()
            self._play_finish_sound()
            self._show_toast("番茄时间到！", "专注结束，休息一下吧。")
            if self.completed % self.config["longBreakInterval"] == 0:
                self.mode = "longBreak"
            else:
                self.mode = "shortBreak"
        else:
            self._play_finish_sound()
            self._show_toast("休息结束！", "准备开始新的番茄钟。")
            self.mode = "pomodoro"

        self._apply_mode()

    # ══════════════════════════════════════════════════════
    # 界面更新
    # ══════════════════════════════════════════════════════

    def _update_display(self):
        m, s = divmod(self.remaining, 60)
        self.lbl_time.configure(text=f"{m:02d}:{s:02d}")
        ratio = self.remaining / self.total if self.total > 0 else 0
        self._draw_ring(ratio)
        names = {"pomodoro": "专注", "shortBreak": "短休", "longBreak": "长休"}
        self.root.title(f"{m:02d}:{s:02d} - {names[self.mode]} - 番茄钟")

    def _update_status(self):
        if self.running:
            m = {"pomodoro": "专注中", "shortBreak": "休息中", "longBreak": "长休息中"}
            self.lbl_status.configure(text=m[self.mode])
        elif self.paused:
            self.lbl_status.configure(text="已暂停")
        else:
            self.lbl_status.configure(text="准备开始")

    def _update_play_button(self):
        self.btn_play.configure(text="⏸" if self.running else "▶")

    def _update_dots(self):
        self.dots_canvas.delete("dot")
        w = 200
        h = 18
        total = self.config["longBreakInterval"]
        done = self.completed % total
        spacing = w / (total + 1)
        r = 6

        for i in range(total):
            x = spacing * (i + 1)
            y = h / 2
            if i < done:
                color = ACCENT if self.mode == "pomodoro" else BREAK_CLR
            else:
                color = DOT_EMPTY
            self.dots_canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill=color, outline="",
                tags="dot",
            )

    # ══════════════════════════════════════════════════════
    # 音效
    # ══════════════════════════════════════════════════════

    def _beep_async(self, freq, ms):
        try:
            threading.Thread(target=lambda: winsound.Beep(freq, ms), daemon=True).start()
        except Exception:
            pass

    def _play_finish_sound(self):
        # 三连音
        self.root.after(0, lambda: self._beep_async(880, 150))
        self.root.after(160, lambda: self._beep_async(1100, 150))
        self.root.after(320, lambda: self._beep_async(1320, 300))

    # ══════════════════════════════════════════════════════
    # Toast 弹窗
    # ══════════════════════════════════════════════════════

    def _show_toast(self, title, body):
        toast = tk.Toplevel(self.root)
        toast.title("")
        toast.configure(bg=SURFACE)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)

        self.root.update_idletasks()
        mx = self.root.winfo_x() + self.root.winfo_width() // 2
        my = self.root.winfo_y() + self.root.winfo_height() // 2
        toast.geometry(f"260x72+{mx - 130}+{my - 36}")

        inner = tk.Frame(toast, bg=SURFACE, highlightbackground=SURFACE2, highlightthickness=1)
        inner.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            inner, text=title, font=("Microsoft YaHei UI", 12, "bold"),
            fg=TEXT, bg=SURFACE,
        ).pack(pady=(12, 0))

        tk.Label(
            inner, text=body, font=("Microsoft YaHei UI", 9),
            fg=TEXT_DIM, bg=SURFACE,
        ).pack()

        toast.after(2500, toast.destroy)

    # ══════════════════════════════════════════════════════
    # 设置操作
    # ══════════════════════════════════════════════════════

    def _toggle_settings(self):
        if self.settings_frame.winfo_manager():
            self.settings_frame.pack_forget()
            self.btn_settings.configure(text="⚙ 设置")
        else:
            self.settings_frame.pack(fill=tk.X, pady=(12, 0), ipady=8)
            self.btn_settings.configure(text="▲ 收起设置")
            for key, var in self._spin_vars.items():
                var.set(self.config[key])

    def _on_setting_change(self, key):
        val = self._spin_vars[key].get()
        self.config[key] = val
        self._save_config()

        if not self.running:
            mmap = {
                "pomodoro": self.config["pomodoro"],
                "shortBreak": self.config["shortBreak"],
                "longBreak": self.config["longBreak"],
            }
            self.total = mmap[self.mode] * 60
            self.remaining = self.total
            self._update_display()
            self._update_dots()

    def _toggle_always_on_top(self):
        is_top = self.top_var.get()
        self.config["alwaysOnTop"] = is_top
        self.root.attributes("-topmost", is_top)
        self._save_config()

    # ══════════════════════════════════════════════════════
    # 键盘快捷键
    # ══════════════════════════════════════════════════════

    def _bind_keys(self):
        self.root.bind("<space>", lambda e: self._toggle_play())
        self.root.bind("<Key-r>", lambda e: self._reset())
        self.root.bind("<Key-s>", lambda e: self._skip())
        self.root.bind("<Key-1>", lambda e: self._set_mode("pomodoro"))
        self.root.bind("<Key-2>", lambda e: self._set_mode("shortBreak"))
        self.root.bind("<Key-3>", lambda e: self._set_mode("longBreak"))
        self.root.bind("<Escape>", lambda e: self._on_close())

    # ══════════════════════════════════════════════════════
    # 生命周期
    # ══════════════════════════════════════════════════════

    def _on_close(self):
        self._stop_timer()
        self._save_config()
        self.root.destroy()

    def run(self):
        if self.config.get("alwaysOnTop", False):
            self.root.attributes("-topmost", True)
        self._bind_keys()
        self.root.mainloop()


if __name__ == "__main__":
    PomodoroApp().run()
