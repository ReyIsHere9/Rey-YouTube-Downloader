# Rey YouTube Downloader — Mobile (Android)

A single, installable **APK** that downloads YouTube videos, audio and subtitles,
using the same yt-dlp engine as the desktop app.

```
mobile/
├── main.py            Kivy app (all features)
├── buildozer.spec     Android build config
└── README.md
```

## Features (same as desktop)

- Paste one or more links; **Preview titles** to see what each link points to.
- Playlists/multi-video links appear as a checklist — untick what you don't want.
- **MP4** (video + audio), **Video only**, **Audio only** (mp3/m4a/opus/wav).
- Quality cap, subtitle download/embed, live progress + activity log.

## Building the APK

Building an Android APK needs a Linux toolchain (python-for-android). Easiest
paths:

**Via GitHub Actions (recommended).** The repo's
`.github/workflows/mobile-build.yml` builds the APK on a Linux runner and
uploads it as an artifact (and to a release on a `vX.Y.Z` tag).

**Locally.** Windows can't run Buildozer directly — use WSL2 or a Linux box:

```bash
sudo pip3 install buildozer cython
cd mobile
buildozer init          # only if buildozer.spec is missing
buildozer android debug
```

The APK lands in `bin/reyytdlp-1.0.0-arm64-v8a-debug.apk`.

## Notes

- The **ffmpeg** recipe is bundled so MP4 merging and audio extraction work.
  If ffmpeg can't be found, downloads still work (as video/audio tracks) but
  won't merge or convert.
- On first launch the app requests storage permission so it can save into
  `Download/ReyYouTubeDownloader` on the device.
