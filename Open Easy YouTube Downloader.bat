@echo off
title Easy YouTube Downloader
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "yt_gui.py"
) else (
    python "yt_gui.py"
)
if errorlevel 1 pause
