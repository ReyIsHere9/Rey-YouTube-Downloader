@echo off
cd /d "%~dp0"
echo Building EasyYouTubeDownloader.exe ...
py -m pip install --upgrade pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "EasyYouTubeDownloader" ^
    --exclude-module tkinter.test ^
    "yt_gui.py"
echo.
echo Done. The exe is in the "dist" folder:
echo   %~dp0dist\EasyYouTubeDownloader.exe
pause
