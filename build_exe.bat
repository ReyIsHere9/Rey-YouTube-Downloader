@echo off
cd /d "%~dp0"
echo Building ReyYouTubeDownloader.exe ...
echo Preparing logo + icon assets ...
py -3 assets.py
py -m pip install --upgrade pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "ReyYouTubeDownloader" ^
    --icon "icon.ico" ^
    --add-data "logo.png;." ^
    --add-data "icon.ico;." ^
    --exclude-module tkinter.test ^
    "yt_gui.py"
echo.
echo Done. The exe is in the "dist" folder:
echo   %~dp0dist\ReyYouTubeDownloader.exe
pause
