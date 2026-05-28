"""
桌面番茄钟 - Python tkinter 原生桌面应用
专注/短休/长休三种模式，环形进度条，音效提醒，桌面通知
"""
import tkinter as tk
from tkinter import messagebox, simpledialog
import math
import time
import json
import os
import threading
import winsound

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_settings.json")

# 默认设置
DEFAULTS = {
    "focus": 25,
    "short_break": 5,
    "long_break": 15,
    "always_on_top": True,
    "theme": "light",
}

# 颜色方案
LIGHT = {
    "bg": "#f5f5f5",
    "card": "#ffffff",
    "text": "#2c3e50",
    "subtext": "#95a5a6",
    "ring_bg": "#e8e8e8",
    "focus": "#e74c3c",
    "short_break": "#27ae60",
    "long_break": "#2980b9",
    "btn_bg": "#e0e0e0",
    "btn_active": "#d0d0d0",
    "mode_bg": "#e0e0e0",
    "mode_active": "#ffffff",
    "divider": "#e0e0e0",
}
DARK = {
    "bg": "#1a1a2e",
    "card": "#16213e",
    "text": "#e0e0e0",
    "subtext": "#7f8c8d",
    "ring_bg": "#2a2a4a",
    "focus": "#e74c3c",
    "short_break": "#2ecc71",
    "long_break": "#3498db",
    "btn_bg": "#2a2a4a",
    "btn_active": "#3a3a5a",
    "mode_bg": "#2a2a4a",
    "mode_active": "#0f3460",
    "divider": "#2a2a4a",
}

MODE_NAMES = {"focus": "专注", "short_break": "短休", "long_break": "长休"}
MODE_COLORS = {"focus": "focus", "short_break": "short_break", "long_break": "long_break"}


class PomodoroApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("番茄钟")
        self.root.geometry("380x540")
        self.root.minsize(340, 480)
        self.root.resizable(True, True)

        # 加载设置
        self.settings = self.load_settings()
        self.theme = DARK if self.settings.get("theme") == "dark" else LIGHT

        # 状态
        self.mode = "focus"
        self.running = False
        self.total_seconds = self.settings["focus"] * 60
        self.remaining = self.total_seconds
        self.completed_count = 0
        self.timer_id = None

        # 应用颜色
        self._colors = self.theme
        self.root.configure(bg=self._colors["bg"])

        # 置顶
        if self.settings.get("always_on_top", True):
            self.root.attributes("-topmost", True)

        self.build_ui()
        self.update_display()
        self.center_window()

        # 窗口关闭时清理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ===== 设置持久化 =====
    def load_settings(self):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULTS, **json.load(f)}
        except (FileNotFoundError, json.JSONDecodeError):
            return {**DEFAULTS}

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ===== UI 构建 =====
    def build_ui(self):
        c = self._colors

        # 主容器
        self.main_frame = tk.Frame(self.root, bg=c["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # 顶部：主题和置顶按钮
        top_bar = tk.Frame(self.main_frame, bg=c["bg"])
        top_bar.pack(fill=tk.X)

        self.pin_btn = tk.Button(top_bar, text="📌" if self.settings.get("always_on_top", True) else "📍",
                                 font=("", 12), bg=c["bg"], fg=c["text"], bd=0,
                                 activebackground=c["bg"], cursor="hand2",
                                 command=self.toggle_always_on_top)
        self.pin_btn.pack(side=tk.LEFT)

        theme_text = "☀ 浅色" if self.settings.get("theme") == "dark" else "☾ 深色"
        self.theme_btn = tk.Button(top_bar, text=theme_text, font=("", 10),
                                    bg=c["bg"], fg=c["text"], bd=0,
                                    activebackground=c["bg"], cursor="hand2",
                                    command=self.toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT)

        # 模式切换按钮
        mode_frame = tk.Frame(self.main_frame, bg=c["mode_bg"])
        mode_frame.pack(fill=tk.X, pady=(10, 16))
        mode_frame.configure(relief=tk.FLAT)
        # 用 tk.Frame 模拟圆角分段控件
        inner = tk.Frame(mode_frame, bg=c["mode_bg"], bd=0)
        inner.pack(padx=2, pady=2)

        self.mode_buttons = {}
        for key, label in [("focus", "🎯 专注"), ("short_break", "☕ 短休"), ("long_break", "🌿 长休")]:
            btn = tk.Button(inner, text=label, font=("Microsoft YaHei UI", 10),
                            bg=c["mode_bg"], fg=c["subtext"], bd=0,
                            activebackground=c["mode_bg"], cursor="hand2",
                            command=lambda m=key: self.switch_mode(m))
            btn.pack(side=tk.LEFT, padx=1, pady=1, ipadx=10, ipady=4)
            self.mode_buttons[key] = btn

        # 环形进度条画布
        self.canvas_size = 260
        self.canvas = tk.Canvas(self.main_frame, width=self.canvas_size, height=self.canvas_size,
                                bg=c["bg"], highlightthickness=0)
        self.canvas.pack(pady=10)

        # 中央计时文字
        self.timer_text = self.canvas.create_text(
            self.canvas_size / 2, self.canvas_size / 2,
            text="25:00", font=("Consolas", 36, "bold"), fill=c["text"]
        )

        # 模式标签
        self.mode_label = tk.Label(self.main_frame, text="准备开始专注",
                                   font=("Microsoft YaHei UI", 10), bg=c["bg"], fg=c["subtext"])
        self.mode_label.pack(pady=(0, 12))

        # 控制按钮
        ctrl_frame = tk.Frame(self.main_frame, bg=c["bg"])
        ctrl_frame.pack()

        self.reset_btn = tk.Button(ctrl_frame, text="↺", font=("", 16),
                                   bg=c["btn_bg"], fg=c["text"], bd=0,
                                   activebackground=c["btn_active"], cursor="hand2",
                                   width=3, height=1, command=self.reset)
        self.reset_btn.pack(side=tk.LEFT, padx=6)

        self.play_btn = tk.Button(ctrl_frame, text="▶", font=("", 20),
                                  bg=c["focus"], fg="white", bd=0,
                                  activebackground=c["focus"], cursor="hand2",
                                  width=4, height=1, command=self.toggle_timer)
        self.play_btn.pack(side=tk.LEFT, padx=6)

        self.skip_btn = tk.Button(ctrl_frame, text="⏭", font=("", 16),
                                  bg=c["btn_bg"], fg=c["text"], bd=0,
                                  activebackground=c["btn_active"], cursor="hand2",
                                  width=3, height=1, command=self.skip)
        self.skip_btn.pack(side=tk.LEFT, padx=6)

        # 统计
        stats_frame = tk.Frame(self.main_frame, bg=c["bg"])
        stats_frame.pack(pady=(16, 5))

        self.today_label = tk.Label(stats_frame, text="今日 0 🍅", font=("Microsoft YaHei UI", 9),
                                    bg=c["bg"], fg=c["subtext"])
        self.today_label.pack(side=tk.LEFT, padx=12)

        self.total_label = tk.Label(stats_frame, text="总计 0 🍅", font=("Microsoft YaHei UI", 9),
                                    bg=c["bg"], fg=c["subtext"])
        self.total_label.pack(side=tk.LEFT, padx=12)

        # 底部设置按钮
        settings_btn = tk.Button(self.main_frame, text="⚙ 设置", font=("Microsoft YaHei UI", 9),
                                 bg=c["bg"], fg=c["subtext"], bd=0,
                                 activebackground=c["bg"], cursor="hand2",
                                 command=self.open_settings)
        settings_btn.pack(pady=(8, 0))

        # 快捷键提示
        hint = tk.Label(self.main_frame, text="空格 开始/暂停  |  R 重置  |  S 跳过",
                        font=("Microsoft YaHei UI", 8), bg=c["bg"], fg=c["subtext"])
        hint.pack(pady=(4, 0))

        self.draw_ring(1.0)
        self.bind_keys()

    def bind_keys(self):
        self.root.bind("<space>", lambda e: self.toggle_timer())
        self.root.bind("<r>", lambda e: self.reset())
        self.root.bind("<R>", lambda e: self.reset())
        self.root.bind("<s>", lambda e: self.skip())
        self.root.bind("<S>", lambda e: self.skip())
        self.root.bind("<Configure>", self.on_resize)

    # ===== 环形进度条绘制 =====
    def draw_ring(self, ratio):
        """ratio: 0.0(空) ~ 1.0(满) 表示剩余比例"""
        self.canvas.delete("ring")
        c = self._colors
        cx = self.canvas_size / 2
        cy = self.canvas_size / 2
        r = 105
        width = 10

        # 背景圆环
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                outline=c["ring_bg"], width=width, tags="ring")
        # 进度弧线（从顶部顺时针）
        if ratio > 0.001:
            angle = 360 * ratio
            # tkinter 的 create_arc 从 3 点钟方向开始，start 是角度（逆时针为正）
            # 我们要从 12 点（-90 度）开始，逆时针减少
            start_angle = 90  # 12 点钟方向
            extent = -angle    # 逆时针
            color_key = MODE_COLORS[self.mode]
            self.canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                                   start=start_angle, extent=extent,
                                   outline=c[color_key], width=width,
                                   style=tk.ARC, tags="ring")

        # 更新中央文字
        self.canvas.itemconfig(self.timer_text, fill=c["text"])

    def on_resize(self, event=None):
        if self.canvas.winfo_width() > 50:
            self.canvas_size = min(self.canvas.winfo_width(), self.canvas.winfo_height())
            self.canvas.coords(self.timer_text, self.canvas_size / 2, self.canvas_size / 2)
            ratio = self.remaining / self.total_seconds if self.total_seconds > 0 else 0
            self.draw_ring(ratio)

    # ===== 模式切换 =====
    def switch_mode(self, mode):
        if self.running:
            if not messagebox.askokcancel("切换模式", f"计时器正在运行，确定切换到{MODE_NAMES[mode]}吗？"):
                return
        self.mode = mode
        self.total_seconds = self.settings[mode] * 60
        self.remaining = self.total_seconds
        self.running = False
        self._cancel_timer()
        self.update_display()
        self.update_mode_buttons()

    def update_mode_buttons(self):
        c = self._colors
        for key, btn in self.mode_buttons.items():
            if key == self.mode:
                btn.configure(bg=c["mode_active"], fg=c[MODE_COLORS[key]])
            else:
                btn.configure(bg=c["mode_bg"], fg=c["subtext"])

    # ===== 计时器逻辑 =====
    def toggle_timer(self):
        if self.running:
            self.pause()
        else:
            self.start()

    def start(self):
        if self.remaining <= 0:
            self.remaining = self.total_seconds
        self.running = True
        self.play_btn.configure(text="⏸", bg=self._colors[MODE_COLORS[self.mode]])
        self.mode_label.configure(text=f"正在{MODE_NAMES[self.mode]}...")
        self._tick()

    def pause(self):
        self.running = False
        self.play_btn.configure(text="▶", bg=self._colors[MODE_COLORS[self.mode]])
        self.mode_label.configure(text="已暂停")
        self._cancel_timer()

    def reset(self):
        self.running = False
        self.remaining = self.total_seconds
        self.play_btn.configure(text="▶", bg=self._colors[MODE_COLORS[self.mode]])
        self.mode_label.configure(text=f"准备开始{MODE_NAMES[self.mode]}")
        self._cancel_timer()
        self.update_display()

    def skip(self):
        self._cancel_timer()
        self.running = False
        self.play_btn.configure(text="▶", bg=self._colors[MODE_COLORS[self.mode]])
        if self.mode == "focus":
            self.switch_mode("short_break")
        else:
            self.switch_mode("focus")

    def _tick(self):
        if not self.running:
            return
        if self.remaining <= 0:
            self._finish()
            return
        self.remaining -= 1
        self.update_display()
        self.timer_id = self.root.after(1000, self._tick)

    def _cancel_timer(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    def _finish(self):
        self.running = False
        self.play_btn.configure(text="▶", bg=self._colors[MODE_COLORS[self.mode]])
        self._cancel_timer()

        # 播放音效
        self._play_sound()

        # 桌面通知弹窗
        if self.mode == "focus":
            msg = "专注时间结束！休息一下吧 ☕"
            self.completed_count += 1
            self._update_stats()
        else:
            msg = "休息时间结束！开始新的专注吧 🎯"

        # 弹窗提醒
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        threading.Thread(target=self._show_notification, args=(msg,), daemon=True).start()

        # 自动切换模式
        if self.mode == "focus":
            if self.completed_count > 0 and self.completed_count % 4 == 0:
                next_mode = "long_break"
            else:
                next_mode = "short_break"
        else:
            next_mode = "focus"

        self.switch_mode(next_mode)

    def _play_sound(self):
        """用 winsound 播放完成提示音"""
        try:
            winsound.Beep(880, 150)
            self.root.after(200, lambda: winsound.Beep(1100, 150))
            self.root.after(400, lambda: winsound.Beep(1320, 300))
        except Exception:
            pass

    def _show_notification(self, msg):
        """临时弹窗提示"""
        popup = tk.Toplevel(self.root)
        popup.title("番茄钟")
        popup.geometry("260x80")
        popup.resizable(False, False)
        popup.configure(bg=self._colors["card"])
        popup.attributes("-topmost", True)
        # 居中
        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 260) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 80) // 2
        popup.geometry(f"+{x}+{y}")

        tk.Label(popup, text=msg, font=("Microsoft YaHei UI", 11),
                 bg=self._colors["card"], fg=self._colors["text"]).pack(expand=True)
        tk.Button(popup, text="知道了", command=popup.destroy,
                  font=("Microsoft YaHei UI", 9),
                  bg=self._colors["focus"], fg="white", bd=0, padx=16, pady=2,
                  cursor="hand2").pack(pady=(0, 12))
        popup.focus_force()

    # ===== 统计 =====
    def _update_stats(self):
        today_key = time.strftime("%Y-%m-%d")
        stats = self.load_stats()
        if stats.get("date") != today_key:
            stats = {"date": today_key, "today": 0, "total": stats.get("total", 0)}
        stats["today"] += 1
        stats["total"] = stats.get("total", 0) + 1
        self._save_stats(stats)
        self.update_display()

    def load_stats(self):
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_stats.json")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"date": "", "today": 0, "total": 0}

    def _save_stats(self, stats):
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_stats.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False)
        except OSError:
            pass

    # ===== UI 更新 =====
    def update_display(self):
        m = self.remaining // 60
        s = self.remaining % 60
        text = f"{m:02d}:{s:02d}"
        self.canvas.itemconfig(self.timer_text, text=text)

        ratio = self.remaining / self.total_seconds if self.total_seconds > 0 else 0
        self.draw_ring(ratio)

        # 更新标题
        mode_name = MODE_NAMES[self.mode]
        self.root.title(f"{text} - {mode_name} | 番茄钟")

        # 更新统计
        stats = self.load_stats()
        self.today_label.configure(text=f"今日 {stats.get('today', 0)} 🍅")
        self.total_label.configure(text=f"总计 {stats.get('total', 0)} 🍅")

        # 播放按钮颜色
        color_key = MODE_COLORS[self.mode]
        self.play_btn.configure(bg=self._colors[color_key])

    # ===== 主题 =====
    def toggle_theme(self):
        current = self.settings.get("theme", "light")
        self.settings["theme"] = "dark" if current == "light" else "light"
        self.save_settings()
        self.theme = DARK if self.settings["theme"] == "dark" else LIGHT
        self._colors = self.theme
        self.root.configure(bg=self._colors["bg"])
        self.main_frame.configure(bg=self._colors["bg"])
        self.canvas.configure(bg=self._colors["bg"])
        self.mode_label.configure(bg=self._colors["bg"], fg=self._colors["subtext"])
        self.today_label.configure(bg=self._colors["bg"], fg=self._colors["subtext"])
        self.total_label.configure(bg=self._colors["bg"], fg=self._colors["subtext"])
        self.canvas.itemconfig(self.timer_text, fill=self._colors["text"])

        theme_text = "☀ 浅色" if self.settings["theme"] == "dark" else "☾ 深色"
        self.theme_btn.configure(text=theme_text, bg=self._colors["bg"], fg=self._colors["text"],
                                  activebackground=self._colors["bg"])

        self.update_mode_buttons()
        self.reset()
        self.update_display()

        # 重建控制按钮外观
        for btn in [self.reset_btn, self.skip_btn]:
            btn.configure(bg=self._colors["btn_bg"], fg=self._colors["text"],
                          activebackground=self._colors["btn_active"])
        self.pin_btn.configure(bg=self._colors["bg"], fg=self._colors["text"],
                               activebackground=self._colors["bg"])

    def toggle_always_on_top(self):
        current = self.settings.get("always_on_top", True)
        self.settings["always_on_top"] = not current
        self.save_settings()
        self.root.attributes("-topmost", self.settings["always_on_top"])
        self.pin_btn.configure(text="📌" if self.settings["always_on_top"] else "📍")

    # ===== 设置窗口 =====
    def open_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("番茄钟设置")
        dialog.geometry("300x240")
        dialog.resizable(False, False)
        dialog.configure(bg=self._colors["card"])
        dialog.attributes("-topmost", True)
        dialog.transient(self.root)

        x = self.root.winfo_x() + (self.root.winfo_width() - 300) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 240) // 2
        dialog.geometry(f"+{x}+{y}")

        c = self._colors

        tk.Label(dialog, text="时长设置（分钟）", font=("Microsoft YaHei UI", 11, "bold"),
                 bg=c["card"], fg=c["text"]).pack(pady=(16, 12))

        entries = {}
        for key, label in [("focus", "专注"), ("short_break", "短休"), ("long_break", "长休")]:
            row = tk.Frame(dialog, bg=c["card"])
            row.pack(fill=tk.X, padx=30, pady=4)
            tk.Label(row, text=f"  {label}", font=("Microsoft YaHei UI", 10),
                     bg=c["card"], fg=c["text"]).pack(side=tk.LEFT)
            var = tk.StringVar(value=str(self.settings[key]))
            ent = tk.Entry(row, textvariable=var, font=("Consolas", 11),
                           bg=c["ring_bg"] if "ring_bg" in c else c["btn_bg"],
                           fg=c["text"], width=6, justify=tk.CENTER,
                           insertbackground=c["text"], relief=tk.FLAT)
            ent.pack(side=tk.RIGHT)
            entries[key] = var

        def save():
            try:
                for key, var in entries.items():
                    val = int(var.get())
                    if val < 1:
                        val = 1
                    if val > 120:
                        val = 120
                    self.settings[key] = val
                    var.set(str(val))
                self.save_settings()
                if not self.running:
                    self.total_seconds = self.settings[self.mode] * 60
                    self.remaining = self.total_seconds
                    self.update_display()
                dialog.destroy()
            except ValueError:
                messagebox.showwarning("输入错误", "请输入有效的数字", parent=dialog)

        tk.Button(dialog, text="保存", command=save,
                  font=("Microsoft YaHei UI", 10),
                  bg=c["focus"], fg="white", bd=0, padx=20, pady=4,
                  activebackground=c["focus"], cursor="hand2").pack(pady=(12, 8))

        dialog.grab_set()
        dialog.focus_force()

    # ===== 窗口管理 =====
    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

    def on_close(self):
        self._cancel_timer()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
