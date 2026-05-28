# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

桌面番茄钟应用，包含两个独立版本：
- `pomodoro.py` — Python tkinter 原生桌面版（主要版本）
- `pomodoro-timer.html` — 单文件 HTML 网页版（备用）

## 启动命令

```bash
# Python 桌面版（pythonw 无控制台窗口）
pythonw pomodoro.py
# 或双击
启动番茄钟.bat

# 网页版（浏览器打开）
start pomodoro-timer.html
```

## 架构

两个版本功能对等，各自独立实现：

**Python 桌面版** (`pomodoro.py`)
- 单文件，`PomodoroApp` 类管理所有状态和 UI
- `tkinter.Canvas` 绘制环形进度条（`create_arc`）
- `root.after()` 驱动 1 秒间隔的倒计时循环
- `winsound.Beep()` 播放完成提示音
- 设置/统计持久化到同目录 JSON 文件（`pomodoro_settings.json`、`pomodoro_stats.json`）
- 深色/浅色主题通过两套颜色字典（`LIGHT`/`DARK`）切换

**HTML 网页版** (`pomodoro-timer.html`)
- 单文件，内嵌 CSS + JS，零依赖
- SVG `stroke-dashoffset` 实现环形进度
- Web Audio API 合成提示音，Notification API 桌面通知
- `localStorage` 持久化设置、任务、统计

**共享逻辑：**
- 三种模式：focus（25分）、short_break（5分）、long_break（15分）
- 4 个专注后自动切换长休（其余短休），跳过不会触发长休阈值
- 跳过操作：专注→短休，休息→专注

## 开关设置

运行期数据文件均以 `pomodoro_` 为前缀写入项目根目录，已由 `.gitignore` 排除：
- `pomodoro_settings.json` — 时长/主题/置顶
- `pomodoro_stats.json` — 当日和累计番茄数
