@echo off
cd /d "%~dp0"
echo Building OurYouTubeDownloader.exe ...
py -m pip install --upgrade pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "OurYouTubeDownloader" ^
    --exclude-module tkinter.test ^
    "yt_gui.py"
echo.
echo Done. The exe is in the "dist" folder:
echo   %~dp0dist\OurYouTubeDownloader.exe
pause
