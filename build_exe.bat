@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Rey YouTube Downloader - build script
echo  Outputs:
echo    dist\ReyYouTubeDownloader.exe      (the app, standalone)
echo    portable\                          (app + yt-dlp + ffmpeg, ready to share)
echo ============================================================
echo.

echo [1/4] Ensuring PyInstaller + Pillow are installed ...
py -m pip install --upgrade pyinstaller pillow >nul || py -m pip install pyinstaller pillow
echo.

echo [2/4] Building the single-file executable ...
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

echo [3/4] Ensuring the yt-dlp engine is present ...
if not exist "yt-dlp.exe" (
    echo   downloading yt-dlp...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "try { Invoke-WebRequest -Uri 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' -OutFile 'yt-dlp.exe' -UseBasicParsing } catch { Write-Host '  yt-dlp download failed' }"
)

echo [4/4] Ensuring ffmpeg is present (one-time ~80 MB) ...
if not exist "ffmpeg\ffmpeg.exe" (
    echo   downloading ffmpeg from the official GitHub mirror...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$ErrorActionPreference='Stop'; $u='https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip'; $t=Join-Path $env:TEMP 'rey_ff'; New-Item -ItemType Directory -Force -Path $t | Out-Null; $z=Join-Path $t 'ff.zip'; Invoke-WebRequest -Uri $u -OutFile $z; Expand-Archive -Path $z -DestinationPath $t -Force; New-Item -ItemType Directory -Force -Path 'ffmpeg' | Out-Null; (Get-ChildItem $t -Recurse -Filter ffmpeg.exe | Select-Object -First 1) | Copy-Item -Destination 'ffmpeg\ffmpeg.exe' -Force; (Get-ChildItem $t -Recurse -Filter ffprobe.exe | Select-Object -First 1) | Copy-Item -Destination 'ffmpeg\ffprobe.exe' -Force; Remove-Item $t -Recurse -Force; Write-Host '  ffmpeg ready'"
)

echo.
echo Building the portable folder ...
if not exist "portable" mkdir "portable"
if not exist "portable\ffmpeg" mkdir "portable\ffmpeg"
copy /y "dist\ReyYouTubeDownloader.exe" "portable\ReyYouTubeDownloader.exe" >nul
if exist "yt-dlp.exe" copy /y "yt-dlp.exe" "portable\yt-dlp.exe" >nul
if exist "ffmpeg\ffmpeg.exe" copy /y "ffmpeg\ffmpeg.exe" "portable\ffmpeg\ffmpeg.exe" >nul
if exist "ffmpeg\ffprobe.exe" copy /y "ffmpeg\ffprobe.exe" "portable\ffmpeg\ffprobe.exe" >nul
echo.
echo Done. The portable folder is fully self-contained:
echo   portable\ReyYouTubeDownloader.exe   (Python is bundled inside)
echo   portable\yt-dlp.exe                 (download engine)
echo   portable\ffmpeg\ffmpeg.exe          (merging / conversion)
echo.
echo Just copy the whole "portable" folder to any Windows PC and run the exe.
echo.
pause
endlocal
