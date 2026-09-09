# Our YouTube Downloader

A simple, friendly desktop app for downloading YouTube videos, audio and
subtitles. It wraps the excellent [yt-dlp](https://github.com/yt-dlp/yt-dlp)
engine in a dark, YouTube-flavoured GUI.

![YouTube-style dark GUI with link box, found-videos picker and option cards]

## Features

- **Paste one or more links** (one per line) and press **Preview titles** to see
  exactly what each link points to.
- **Multi-video links** (playlists, channels, mixes) are shown as a checklist —
  untick anything you don't want before downloading.
- **Pick what to get** — tick any combination:
  - **MP4** — video + audio in one file (the usual download)
  - **Video only** — the picture track alone (no sound)
  - **Audio only** — extract sound as `mp3`, `m4a`, `opus` or `wav`
- **Subtitles** — embed into the MP4, or save as separate `.srt` / `.vtt` / `.ass`
  files (srt/vtt are plain text you can open in Notepad).
- **Quality limit** — Best / 2160p / 1440p / 1080p / 720p / 480p / 360p.
- **Real progress bar**, live status line and a colour-coded activity log.
- **Self-installing engine** — the app checks for `yt-dlp` on startup. The
  top-right button shows the engine status (`yt-dlp: not found`,
  `yt-dlp: installing…`, `yt-dlp: v2026.…`). If it's missing, the app offers to
  download the official `yt-dlp.exe` straight into its own folder.
- **Fully portable** — all paths are resolved relative to the app's own folder;
  nothing is written outside of it.

## Requirements

- **Windows** (the app is developed/tested on Windows).
- **Python 3.9+** to run the source (`yt_gui.py`) — only the standard library is
  used. No extra Python packages are needed.
  - ...or just use the prebuilt **`.exe`** which needs no Python at all.
- **ffmpeg** (optional but recommended) for MP4 merging, audio extraction and
  thumbnail/subtitle embedding. Install it once with:
  `winget install Gyan.FFmpeg`
- Internet connection on first run (to fetch `yt-dlp.exe` if it isn't present).

## Getting started

### Prebuilt .exe

1. Download the latest `OurYouTubeDownloader.exe` from **Releases**.
2. Put it in any folder (e.g. `D:\Videos`). It will create a `Downloads`
   subfolder next to itself for saved files.
3. Double-click to run. On first launch it checks the yt-dlp engine and offers
   to install it if needed.

### From source

```bat
git clone https://github.com/<you>/Our-YouTube-Downloader.git
cd Our-YouTube-Downloader
python yt_gui.py
```

Or double-click `Open Our YouTube Downloader.bat`.

### Using it

1. Paste link(s), one per line.
2. Press **Preview titles** → the app lists what each link resolves to
   (handy for playlists).
3. Untick any videos you don't want.
4. Tick what to produce under **What to get**.
5. Optionally tick **Subtitles** and pick a format/language.
6. Press **Download**.

## Audio format cheat-sheet (for music)

| Format     | Use it for                                                        |
| ---------- | ----------------------------------------------------------------- |
| `mp3`      | Most compatible — recommended for music                           |
| `m4a`      | Slightly better quality at the same size (AAC)                    |
| `opus`     | Best sound quality, fewer devices support it                      |
| `wav`      | Lossless, very large — only for editing                           |
| `original` | Keep YouTube's original audio, no conversion                      |

## Building the .exe yourself

```bat
python -m pip install pyinstaller
build_exe.bat
```

The single-file executable is written to `dist\OurYouTubeDownloader.exe`.

## Notes

- The app only downloads media; please respect content owners and the terms of
  the sites you use it with.
- For very long playlists the preview list is capped at the first 250 entries.
- The `yt-dlp.exe` engine is downloaded on demand from the official yt-dlp
  GitHub release and is not bundled in this repository.

## License

[MIT](LICENSE). The bundled wrapper (`yt-dlp`) has its own license — see
https://github.com/yt-dlp/yt-dlp#license.
