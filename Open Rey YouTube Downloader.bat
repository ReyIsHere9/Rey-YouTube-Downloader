@echo off
setlocal
title Rey YouTube Downloader
cd /d "%~dp0"

echo ============================================
echo   Rey YouTube Downloader - setup ^& launch
echo ============================================
echo.

REM ---------------------------------------------------------------
REM 1) Python
REM ---------------------------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )

if not defined PY (
    echo [!] Python was not found.
    where winget >nul 2>nul
    if errorlevel 1 (
        echo     Please install Python 3 from https://www.python.org/downloads/
        echo     then run this file again.
        pause & exit /b 1
    )
    echo     Installing Python 3.13 with winget...
    winget install -e --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements
    call :refreshpath
    where py >nul 2>nul && set "PY=py -3"
    if not defined PY ( where python >nul 2>nul && set "PY=python" )
    if not defined PY (
        echo     Python still not found - please install it manually.
        pause & exit /b 1
    )
)

REM ---------------------------------------------------------------
REM 2) ffmpeg (for merging / converting / thumbnails / subtitles)
REM ---------------------------------------------------------------
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo [!] ffmpeg was not found - needed for merging audio,
    echo     converting to mp3/m4a, and embedding thumbnails/subtitles.
    where winget >nul 2>nul
    if errorlevel 1 (
        echo     Please install it manually:  winget install Gyan.FFmpeg
    ) else (
        echo     Installing ffmpeg with winget...
        winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
        call :refreshpath
    )
)

REM ---------------------------------------------------------------
REM 3) yt-dlp engine
REM ---------------------------------------------------------------
if not exist "yt-dlp.exe" (
    echo [*] Downloading the yt-dlp engine...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "try { Invoke-WebRequest -Uri 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' -OutFile 'yt-dlp.exe' -UseBasicParsing } catch { Write-Host '  download failed:' $_.Exception.Message }"
)

echo.
echo [*] Starting Rey YouTube Downloader...
echo.
%PY% "yt_gui.py"
if errorlevel 1 pause
exit /b 0

:refreshpath
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%i;%PATH%"
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine')"`) do set "PATH=%PATH%;%%i"
exit /b 0
