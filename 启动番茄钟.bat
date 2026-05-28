@echo off
chcp 65001 >nul
title 番茄钟
cd /d "%~dp0"
start "" pythonw "%~dp0pomodoro.py"
