"""Rey YouTube Downloader - Android (Kivy) app.

A single, installable APK that downloads YouTube videos, audio and subtitles
using the yt-dlp engine. Mirrors the desktop app's features:

  - preview what a link points to (playlist-aware) and pick videos
  - MP4 merge / video-only / audio-only
  - quality cap, subtitle download & embedding, audio format

Built / packaged with Buildozer + python-for-android.
"""
import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.utils import platform
from kivy.graphics import Color, RoundedRectangle

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# ---------------- palette ----------------
BG = (0.055, 0.055, 0.055, 1)
CARD = (0.09, 0.09, 0.09, 1)
CARD2 = (0.13, 0.13, 0.13, 1)
BORD = (0.16, 0.16, 0.16, 1)
RED = (0.93, 0.08, 0.13, 1)          # accent
TEXT = (0.94, 0.94, 0.94, 1)
MUTED = (0.55, 0.55, 0.55, 1)
GREEN = (0.25, 0.72, 0.31, 1)
WARN = (0.89, 0.70, 0.25, 1)

QUALITIES = ["Best", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_FMTS = ["mp3", "m4a", "opus", "wav", "original"]
MAX_PREVIEW = 250


def default_save_dir():
    """A folder the user can reach, different on Android vs desktop."""
    if platform == "android":
        try:
            from android.storage import primary_external_storage_path
            base = primary_external_storage_path()
            if base:
                return os.path.join(base, "Download", "ReyYouTubeDownloader")
        except Exception:
            pass
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads")


def find_ffmpeg():
    """Try to locate an ffmpeg binary (bundled on Android, or on PATH)."""
    if platform == "android":
        import glob
        roots = [
            "/data/data/org.rey.reyytdlp/files",
            "/data/user/0/org.rey.reyytdlp",
            "/data/app",
            "/sdcard",
        ]
        cand = []
        for r in roots:
            cand += glob.glob(r + "/**/ffmpeg", recursive=True)
            cand += glob.glob(r + "/**/ffmpeg.exe", recursive=True)
        for c in cand:
            if os.path.exists(c):
                return c
    import shutil
    return shutil.which("ffmpeg")


# ---------------- style helpers ----------------
def card(children, padding=(10, 8)):
    box = BoxLayout(orientation="vertical", size_hint_y=None,
                    padding=dp(padding[0]), spacing=dp(6))
    with box.canvas.before:
        Color(*CARD, 1)
        box.bind(size=lambda *_: setattr(
            box.canvas.before, "_rect", None))  # placeholder, replaced below
        box._rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(8)])
        box.bind(pos=lambda _, v: setattr(box._rect, "pos", v),
                 size=lambda _, v: setattr(box._rect, "size", v))
    if not isinstance(children, (list, tuple)):
        children = [children]
    for c in children:
        box.add_widget(c)
    return box


class Section(Label):
    def __init__(self, text, **kw):
        super().__init__(text=text.upper(), font_size=dp(11), bold=True,
                         color=MUTED, size_hint_y=None, height=dp(18), **kw)


def lbl(text, size=13, color=TEXT, bold=False):
    return Label(text=text, font_size=dp(size), color=color, bold=bold,
                 halign="left", valign="middle", padding=(dp(4), 0))
    # padding forces left alignment inward


class FlatBtn(Button):
    def __init__(self, text, cmd, bg=RED, fg=(1, 1, 1, 1), height=46, **kw):
        super().__init__(text=text, size_hint_y=None, height=dp(height),
                         background_normal="", background_color=bg, bold=True,
                         color=fg, font_size=dp(14), **kw)
        self.bind(on_release=cmd)


def chip_row(text):
    return BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))


class CheckRow(BoxLayout):
    """A tickable row: checkbox + text, used for 'what to get' & video list."""

    def __init__(self, text, on_change=None, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, **kw)
        self.on_change = on_change
        self.cb = CheckBox(active=False, size_hint=(None, 1), width=dp(36),
                           size_hint_y=None, height=dp(30),
                           color=RED, group=None)
        self.cb.bind(active=lambda i, v: self._change(v))
        self.tx = Label(text=text, color=TEXT, font_size=dp(12), bold=True,
                        halign="left", valign="middle", size_hint_y=None,
                        height=dp(30))
        self.add_widget(self.cb)
        self.add_widget(self.tx)
        self.active = False

    def _change(self, v):
        self.active = v
        self.tx.color = TEXT if v else MUTED
        if self.on_change:
            self.on_change()


# ---------------- app ----------------
class ReyApp(App):
    title = "Rey YouTube Downloader"

    def build(self):
        self.entries = []          # [(id, title)]
        self.checks = []           # [CheckRow]
        self.selected = []         # [bool]
        self.downloading = False
        self.ffmpeg = find_ffmpeg()
        self.root_widget = self._build_ui()
        return self.root_widget

    def on_start(self):
        if platform == "android":
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
                                     Permission.READ_EXTERNAL_STORAGE,
                                     Permission.INTERNET])
            except Exception:
                pass

    # ---------- ui ----------
    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10),
                         size_hint_y=None, height=dp(60))
        root.bind(minimum_height=root.setter("height"))
        root.size_hint_y = 1

        head = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50))
        head.add_widget(lbl("Rey YouTube ", 20, TEXT, True))
        add = lbl("Downloader", 20, RED, True)
        head.add_widget(add)
        root.add_widget(head)

        # URLs
        self.url_in = TextInput(text="", hint_text="Paste one or more YouTube links, "
                                                  "one per line", multiline=True,
                                size_hint_y=None, height=dp(80),
                                background_color=CARD2, foreground_color=(1, 1, 1, 1),
                                cursor_color=(1, 1, 1, 1), padding=(dp(8), dp(8)))
        root.add_widget(self.url_in)

        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        prev = FlatBtn("Preview titles", self.preview, bg=CARD2, fg=TEXT)
        row.add_widget(prev)
        self.status = lbl("Ready.", 12, MUTED)
        row.add_widget(self.status)
        root.add_widget(row)

        # Found videos
        self.found_scroll = ScrollView(size_hint_y=None, height=dp(220),
                                       do_scroll_x=False)
        self.found_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4),
                                     padding=dp(4))
        self.found_grid.bind(minimum_height=self.found_grid.setter("height"))
        self.found_scroll.add_widget(self.found_grid)
        root.add_widget(self.found_scroll)
        self.found_hint = lbl("Links will appear here after tapping Preview titles.",
                              11, MUTED)
        self.found_grid.add_widget(self.found_hint)

        # What to get
        root.add_widget(Section("What to get"))
        self.mp4_row = CheckRow("MP4  (video + audio)")
        self.vdo_row = CheckRow("Video only")
        self.aud_row = CheckRow("Audio only")
        self.mp4_row.cb.active = True
        self.mp4_row.active = True
        root.add_widget(self.mp4_row)
        root.add_widget(self.vdo_row)
        root.add_widget(self.aud_row)

        root.add_widget(Section("Options"))
        r1 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        r1.add_widget(lbl("Quality", 13))
        self.quality = Spinner(text="1080p", values=QUALITIES, size_hint_x=0.5,
                               background_color=CARD2, color=TEXT,
                               background_normal="", size_hint_y=None, height=dp(36))
        r1.add_widget(self.quality)
        root.add_widget(r1)

        r2 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        r2.add_widget(lbl("Audio format", 13))
        self.afmt = Spinner(text="mp3", values=AUDIO_FMTS, size_hint_x=0.5,
                            background_color=CARD2, color=TEXT,
                            background_normal="", size_hint_y=None, height=dp(36))
        r2.add_widget(self.afmt)
        root.add_widget(r2)

        root.add_widget(Section("Subtitles"))
        self.sub_row = CheckRow("Download subtitles")
        root.add_widget(self.sub_row)
        r3 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.sub_lang = TextInput(text="en", hint_text="lang", size_hint_x=0.4,
                                  background_color=CARD2, foreground_color=(1, 1, 1, 1),
                                  size_hint_y=None, height=dp(36))
        r3.add_widget(self.sub_lang)
        self.auto_cb = CheckBox(active=True, color=RED, size_hint_y=None, height=dp(36))
        r3.add_widget(self.auto_cb)
        r3.add_widget(lbl("Auto-generated", 12))
        root.add_widget(r3)

        r4 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        r4.add_widget(lbl("Save to", 13))
        self.ddir = TextInput(text=default_save_dir(), size_hint_x=0.7,
                              background_color=CARD2, foreground_color=(1, 1, 1, 1),
                              size_hint_y=None, height=dp(36))
        r4.add_widget(self.ddir)
        root.add_widget(r4)

        self.dl_btn = FlatBtn("Download", self.download, height=56)
        root.add_widget(self.dl_btn)

        self.bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(10))
        self.bar.color = RED
        root.add_widget(self.bar)

        # activity log (wrapping)
        log_scroll = ScrollView(size_hint_y=1, do_scroll_x=False)
        self.log = Label(text="", color=(0.8, 0.8, 0.8, 1), font_size=dp(10),
                         size_hint_y=None, halign="left", valign="top")
        self.log.bind(texture_size=self._set_log_height)
        log_scroll.add_widget(self.log)
        root.add_widget(log_scroll)

        return root

    def _set_log_height(self, *args):
        self.log.height = self.log.texture_size[1]

    def _set_status(self, text, color=TEXT):
        Clock.schedule_once(lambda _d: setattr(self.status, "text", text) or
                            setattr(self.status, "color", color), 0)

    def _log_line(self, text):
        Clock.schedule_once(lambda _d: setattr(self.log, "text",
                                               self.log.text + text + "\n"), 0)

    # ---------- preview ----------
    def preview(self, *_):
        if yt_dlp is None or self.downloading:
            return
        urls = [u.strip() for u in self.url_in.text.splitlines() if u.strip()]
        if not urls:
            self._set_status("Paste a link first.", WARN)
            return
        self._set_status("Looking up links…", MUTED)
        threading.Thread(target=self._fetch, args=(urls,), daemon=True).start()

    def _fetch(self, urls):
        entries = []
        try:
            with yt_dlp.YoutubeDL({
                "skip_download": True, "quiet": True, "no_warnings": True,
                "extract_flat": "in_playlist",
            }) as ydl:
                for u in urls:
                    info = ydl.extract_info(u, download=False)
                    if info and info.get("entries"):
                        for e in info["entries"]:
                            if e:
                                entries.append((e.get("id") or "", e.get("title") or ""))
                    elif info:
                        entries.append((info.get("id") or "", info.get("title") or ""))
                    if len(entries) >= MAX_PREVIEW:
                        break
        except Exception as e:
            self._log_line("preview error: %s" % e)
        Clock.schedule_once(lambda _d: self._render_found(entries), 0)

    def _render_found(self, entries):
        self.found_grid.clear_widgets()
        self.entries = entries[:MAX_PREVIEW]
        self.checks = []
        self.selected = [True] * len(self.entries)
        if not entries:
            self.found_hint = lbl("No videos found for those link(s).", 11, WARN)
            self.found_grid.add_widget(self.found_hint)
            self._set_status("No videos found.", WARN)
            return
        self.found_hint = lbl("Found %d. Untick any you don't want." % len(entries),
                              11, MUTED)
        self.found_grid.add_widget(self.found_hint)
        for i, (vid, title) in enumerate(self.entries):
            r = CheckRow("%d.  %s" % (i + 1, title or "(untitled)"))
            r.cb.active = True
            r.active = True
            r.on_change = None
            # capture index
            def cb(i=i, r=r): self.selected[i] = r.cb.active
            r.cb.bind(active=lambda inst, v, i=i: self._toggle(i, v))
            self.checks.append(r)
            self.found_grid.add_widget(r)
        self._set_status("Found %d. Press Download." % len(entries), GREEN)

    def _toggle(self, i, v):
        self.selected[i] = v

    # ---------- download ----------
    def download(self, *_):
        if self.downloading or yt_dlp is None:
            return
        if not (self.mp4_row.active or self.vdo_row.active or self.aud_row.active):
            self._set_status("Tick at least one item under What to get.", WARN)
            return
        urls = [u.strip() for u in self.url_in.text.splitlines() if u.strip()]
        if not urls:
            self._set_status("Paste a link first.", WARN)
            return
        self.downloading = True
        self.dl_btn.disabled = True
        self.bar.value = 0
        self._set_status("Downloading…", MUTED)
        threading.Thread(target=self._work, args=(urls,), daemon=True).start()

    def _opts_for(self, url):
        out = self.ddir.text.strip() or default_save_dir()
        os.makedirs(out, exist_ok=True)
        o = {
            "outtmpl": os.path.join(out, "%(title).120s [%(id)s].%(ext)s"),
            "quiet": True, "no_warnings": True, "newline": True,
            "progress_hooks": [self._hook],
        }
        if self.ffmpeg:
            o["ffmpeg_location"] = self.ffmpeg
        q = self.quality.text
        if q != "Best":
            o["format_sort"] = [("res", q)]

        mp4 = self.mp4_row.active
        vid = self.vdo_row.active
        aud = self.aud_row.active

        # subtitle flags
        subs = self.sub_row.active
        if subs:
            langs = self.sub_lang.text.strip() or "en"
            o["subtitleslangs"] = ["all"] if langs.lower() == "all" else [langs]
            o["writesubtitles"] = True
            if self.auto_cb.active:
                o["writeautomaticsub"] = True
            if mp4:
                o["writesubtitles"] = True
                o["writeautomaticsub"] = self.auto_cb.active
                o["embedsubs"] = True
                o["subformat"] = "srt"

        if mp4:
            o["format"] = "bv*+ba/b"
            o["merge_output_format"] = "mp4"
            o["embedthumbnail"] = True
        elif vid:
            o["format"] = "bv*"
            o["embedthumbnail"] = True
        elif aud:
            o["format"] = "bestaudio"
            af = self.afmt.text
            if af != "original":
                o["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": af,
                }]
            o["embedthumbnail"] = True
        return o

    def _hook(self, d):
        if d.get("status") == "downloading":
            tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            pct = (done / tot * 100) if tot else 0
            Clock.schedule_once(lambda _d: setattr(self.bar, "value", min(100, pct)), 0)
            self._set_status("Downloading %s (%s)" % (
                os.path.basename(d.get("filename", "")), "%.1f%%" % min(100, pct)), MUTED)
        elif d.get("status") == "finished":
            self._set_status("Processing…", MUTED)

    def _work(self, urls):
        try:
            for url in urls:
                self._log_line("=== %s" % url)
                try:
                    with yt_dlp.YoutubeDL(self._opts_for(url)) as ydl:
                        ydl.download([url])
                    self._log_line("OK: done")
                except Exception as e:
                    self._log_line("ERROR: %s" % e)
        finally:
            Clock.schedule_once(lambda _d: self._finished(), 0)

    def _finished(self):
        self.downloading = False
        self.dl_btn.disabled = False
        self._set_status("Finished.", GREEN)


if __name__ == "__main__":
    ReyApp().run()
