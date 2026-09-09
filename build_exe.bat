@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Rey YouTube Downloader - build script
echo  Outputs:
echo    dist\ReyYouTubeDownloader.exe      (the app, standalone)
echo    portable\ReyYouTubeDownloader.exe  (app + yt-dlp.exe, ready to share)
echo ============================================================
echo.

echo [1/3] Ensuring PyInstaller is installed ...
py -m pip install --upgrade pyinstaller >nul || py -m pip install pyinstaller
echo.

echo [2/3] Building the single-file executable ...
py -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "ReyYouTubeDownloader" ^
    --icon "icon.ico" ^
    --add-data "logo.png;." ^
    --add-data "icon.ico;." ^
    --exclude-module tkinter.test ^
    "yt_gui.py"
if errorlevel 1 (
    echo.
    echo Build FAILED. See the messages above.
    pause
    exit /b 1
)
echo.

echo [3/3] Refreshing the portable folder ...
if not exist "portable" mkdir "portable"
copy /y "dist\ReyYouTubeDownloader.exe" "portable\ReyYouTubeDownloader.exe" >nul
if exist "yt-dlp.exe" (
    copy /y "yt-dlp.exe" "portable\yt-dlp.exe" >nul
    echo   portable is ready: app + yt-dlp engine bundled.
) else (
    echo   portable is ready: no bundled yt-dlp, it auto-downloads on first run.
)
echo.
echo Done.
echo   dist\ReyYouTubeDownloader.exe
echo   portable\ReyYouTubeDownloader.exe
echo.
pause
endlocal
