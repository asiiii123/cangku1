@echo off
chcp 65001 >nul
title 番茄钟

set "FILE=%~dp0pomodoro-timer.html"

:: 查找浏览器
set "BROWSER="
if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    set "BROWSER=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)
if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
    set "BROWSER=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
)
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "BROWSER=C:\Program Files\Google\Chrome\Application\chrome.exe"
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "BROWSER=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

if "%BROWSER%"=="" (
    echo 未找到 Chrome/Edge，使用默认浏览器打开...
    start "" "%FILE%"
) else (
    start "" "%BROWSER%" --app="%FILE%" --window-size=450,680
)
