import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from tkinter import ttk, filedialog, messagebox

# ---------------- palette ----------------
BG      = "#0F0F0F"
PANEL   = "#141414"
CARD    = "#1E1E1E"
CARD_ON = "#262626"
BORD    = "#2B2B2B"
BORD_ON = "#FF0033"
HOVER   = "#2A2A2A"
TEXT    = "#F1F1F1"
MUTED   = "#9E9E9E"
RED     = "#FF0000"
RED_HI  = "#FF1F3D"
GREEN   = "#3FB950"
WARN    = "#E3B341"
ERR     = "#FF5252"

FONT = "Segoe UI"
FONT_MONO = "Consolas"

def app_dir():
    """Folder the program lives in (works when frozen into an .exe too)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    """Path to a bundled asset (logo/icon) whether frozen or running source."""
    base = getattr(sys, "_MEIPASS", None) or app_dir()
    return os.path.join(base, name)


YDLP = os.path.join(app_dir(), "yt-dlp.exe")
DEFAULT_OUT = os.path.join(app_dir(), "Downloads")
YDLP_URL = ("https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe")

QUALITIES = ["Best", "2160p (4K)", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_FMTS = ["mp3", "m4a", "opus", "wav", "original (no conversion)"]
SUB_FMTS = ["srt", "vtt", "ass"]
MAX_PREVIEW = 250

DEST_RE = re.compile(r"^\[[^\]]+\] Destination: (.*)$")
PCT_RE  = re.compile(r"^\[download\]\s+([\d.]+)%")
ITEM_RE = re.compile(r"^\[download\] Downloading item (\d+) of (\d+)")

HELP_TEXT = (
    "\u2022 Paste one or more links (one per line) and press \u201cPreview titles\u201d. "
    "The app shows exactly what each link points to.\n"
    "\u2022 If a link is a playlist / channel / multi-video page, every video appears "
    "under \u201cFound videos\u201d \u2014 untick any you don\u2019t want, then Download.\n"
    "\u2022 Under \u201cWhat to get\u201d tick what you want: MP4 (video + audio in one file), "
    "Video only (no sound), Audio only. Tick several to get them all.\n"
    "\u2022 Audio format for music:  mp3 = most compatible (recommended for music)   "
    "m4a = slightly better quality at the same size   opus = best sound but fewer devices "
    "support it   wav = lossless, huge \u2014 only for editing   original = keep YouTube\u2019s "
    "audio untouched.\n"
    "\u2022 Subtitles: embedded into the MP4 when that is selected, otherwise written as "
    "separate .srt/.vtt files (plain text, open in Notepad).\n"
    "\u2022 Files are saved to the folder under \u201cSave to\u201d. Watch the Activity area "
    "for live progress."
)


def res_of(q):
    if q == "Best":
        return None
    return q.split("p")[0].split(" ")[0]


def short(text, n=110):
    return text if len(text) <= n else text[: n - 1].rstrip() + "\u2026"


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self._id = None
        widget.bind("<Enter>", self._enter)
        widget.bind("<Leave>", self._leave)
        widget.bind("<Button-1>", self._leave, add="+")

    def _enter(self, _e):
        self._schedule()

    def _schedule(self):
        self._cancel()
        self._id = self.widget.after(600, self._show)

    def _leave(self, _e=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None

    def _show(self):
        self._hide()
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        lab = tk.Label(self.tip, text=self.text, justify="left", bg="#2E2E2E",
                       fg=TEXT, font=(FONT, 8), padx=8, pady=5,
                       wraplength=280)
        lab.pack()

    def _hide(self):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class Tile(tk.Frame):
    """A clickable selectable card."""

    def __init__(self, master, title, desc, var, on_toggle):
        super().__init__(master, bg=BORD, cursor="hand2")
        self.var = var
        self.on_toggle = on_toggle
        self.inner = tk.Frame(self, bg=CARD)
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)
        for w in (self, self.inner):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._hover)
            w.bind("<Leave>", self._leave)

        self.dot = tk.Canvas(self.inner, width=24, height=24,
                             bg=CARD, highlightthickness=0, cursor="hand2")
        self.dot.bind("<Button-1>", self._click)
        self.dot.pack(side="left", padx=(12, 12), pady=12)

        box = tk.Frame(self.inner, bg=CARD)
        box.bind("<Button-1>", self._click)
        box.pack(side="left", fill="x", expand=True, pady=10)
        self.title_lbl = tk.Label(box, text=title, bg=CARD, fg=TEXT, anchor="w",
                                  font=(FONT, 11, "bold"), cursor="hand2")
        self.title_lbl.bind("<Button-1>", self._click)
        self.title_lbl.pack(fill="x")
        self.desc_lbl = tk.Label(box, text=desc, bg=CARD, fg=MUTED, anchor="w",
                                 font=(FONT, 8), cursor="hand2")
        self.desc_lbl.bind("<Button-1>", self._click)
        self.desc_lbl.pack(fill="x", pady=(1, 0))
        self._redraw()

    def _click(self, _e):
        self.var.set(not self.var.get())
        self._redraw()
        self.on_toggle()

    def _hover(self, _e):
        if not self.var.get():
            self._set_bg(HOVER)

    def _leave(self, _e):
        self._redraw()

    def _set_bg(self, c):
        self.inner.configure(bg=c)
        self.title_lbl.configure(bg=c)
        self.desc_lbl.configure(bg=c)
        self.dot.configure(bg=c)

    def _redraw(self):
        on = self.var.get()
        c = CARD_ON if on else CARD
        self.configure(bg=BORD_ON if on else BORD)
        self._set_bg(c)
        self.dot.delete("all")
        if on:
            self.dot.create_oval(3, 3, 21, 21, fill=RED, outline=RED)
            self.dot.create_line(7, 12, 11, 16, 17, 8,
                                 fill="white", width=2.2,
                                 capstyle="round", joinstyle="round")
        else:
            self.dot.create_oval(3, 3, 21, 21, outline="#5A5A5A", width=1.6)


class YTdlpGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rey YouTube Downloader")
        self.configure(bg=BG)
        self.geometry("760x920")
        self.minsize(680, 700)
        self.downloading = False
        self.previewing = False
        self.yt_state = "checking"      # checking | ok:<ver> | missing | busy
        self.resume_after_install = None
        self.links = []            # [{'url','entries':[(idx,id,title)],'vars':[]}]
        self.sig = None            # signature of url text the preview reflects
        self.plan = []             # [(label, argv)] ready to run
        self.cur_name = ""
        self.last_pct = -1.0
        self.help_on = False
        self.ui_q = queue.Queue()      # (fn, args) posted from worker threads
        self._style()
        self._build_ui()
        self._set_window_icon()
        self.after(120, self._drain_ui)
        self.after(500, self.check_ytdlp, False)

    def _set_window_icon(self):
        try:
            ico = resource_path("icon.ico")
            if os.path.exists(ico):
                self.iconbitmap(ico)
        except tk.TclError:
            pass

    # ---------- thread-safe UI helpers ----------
    def _post(self, fn, *args):
        """Run fn(*args) on the main thread (safe to call from any thread)."""
        if threading.current_thread() is threading.main_thread():
            fn(*args)
        else:
            self.ui_q.put((fn, args))

    def _drain_ui(self):
        try:
            while True:
                fn, args = self.ui_q.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.after(90, self._drain_ui)

    # ---------------- styling ----------------
    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=CARD, background=CARD,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=BORD,
                        lightcolor=BORD, darkcolor=BORD, padding=4)
        style.map("TCombobox",
                  fieldbackground=[("readonly", CARD), ("disabled", "#141414")],
                  foreground=[("readonly", TEXT), ("disabled", "#555")])
        style.configure("Horizontal.TProgressbar", troughcolor="#2A2A2A",
                        background=RED, bordercolor="#2A2A2A", lightcolor=RED,
                        darkcolor=RED)
        style.configure("Vertical.TScrollbar", troughcolor=BG,
                        background="#3A3A3A", bordercolor=BG, arrowcolor=TEXT)
        self.option_add("*TCombobox*Listbox.background", CARD_ON)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", RED)
        self.option_add("*TCombobox*Listbox.selectForeground", TEXT)
        self.option_add("*TCombobox*Listbox.font", (FONT, 9))

    # ---------------- ui ----------------
    def _build_ui(self):
        self._header()
        self._build_help()

        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True, padx=20, pady=(6, 0))
        body = self.body

        # --- URL ---
        url_hdr = tk.Frame(body, bg=BG)
        url_hdr.pack(fill="x")
        tk.Label(url_hdr, text="PASTE LINK(S)", bg=BG, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(side="left")
        tk.Label(url_hdr, text="   one per line", bg=BG, fg="#5A5A5A",
                 font=(FONT, 8)).pack(side="left")
        prev = tk.Button(url_hdr, text="Preview titles", command=self.preview,
                         bg=CARD_ON, fg=TEXT, relief="flat", font=(FONT, 8, "bold"),
                         cursor="hand2", padx=10, pady=2, bd=0,
                         activebackground=HOVER, activeforeground=TEXT)
        prev.pack(side="right")
        ToolTip(prev, "Fetch the video title(s) behind each link. "
                      "Useful when a link points to a playlist or many videos.")

        self.url_box = tk.Text(body, height=2, bg=PANEL, fg=TEXT, relief="flat",
                               insertbackground=TEXT, font=(FONT_MONO, 10),
                               padx=10, pady=8, highlightthickness=1,
                               highlightbackground=BORD, highlightcolor=RED)
        self.url_box.pack(fill="x", pady=(6, 10))
        self.url_box.bind("<KeyRelease>", lambda _e: self._invalidate())

        # --- Found videos panel ---
        self.found_card = tk.Frame(body, bg=PANEL, highlightthickness=1,
                                   highlightbackground=BORD)
        fhdr = tk.Frame(self.found_card, bg=PANEL)
        fhdr.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(fhdr, text="FOUND VIDEOS", bg=PANEL, fg=TEXT,
                 font=(FONT, 8, "bold")).pack(side="left")
        self.count_var = tk.StringVar(value="")
        tk.Label(fhdr, textvariable=self.count_var, bg=PANEL, fg=MUTED,
                 font=(FONT, 8)).pack(side="left", padx=(8, 0))
        both = tk.Frame(fhdr, bg=PANEL)
        both.pack(side="right")
        for t, fn in (("Select all", self._sel_all),
                      ("Clear", self._sel_none)):
            b = tk.Label(both, text=t, bg=PANEL, fg=RED, cursor="hand2",
                         font=(FONT, 8, "bold"), padx=6)
            b.bind("<Button-1>", lambda _e, f=fn: f())
            b.pack(side="left")
        self.found_wrap = tk.Frame(self.found_card, bg=BG)
        self.found_wrap.pack(fill="x", padx=10, pady=(0, 8))
        self.found_canvas = tk.Canvas(self.found_wrap, bg=PANEL,
                                      highlightthickness=0, height=120)
        self.found_sb = ttk.Scrollbar(self.found_wrap, orient="vertical",
                                      command=self.found_canvas.yview,
                                      style="Vertical.TScrollbar")
        self.found_canvas.configure(yscrollcommand=self.found_sb.set)
        self.found_sb.pack(side="right", fill="y")
        self.found_canvas.pack(side="left", fill="x", expand=True)
        self.found_inner = tk.Frame(self.found_canvas, bg=PANEL)
        self._found_win = self.found_canvas.create_window((0, 0), anchor="nw",
                                                          window=self.found_inner)
        self.found_inner.bind(
            "<Configure>",
            lambda e: self.found_canvas.configure(scrollregion=self.found_canvas.bbox("all")))
        self.found_canvas.bind(
            "<Configure>",
            lambda e: self.found_canvas.itemconfigure(self._found_win, width=e.width))
        self.found_canvas.bind("<MouseWheel>", self._wheel)
        self.found_card.pack_forget()

        # --- What to get ---
        self._section(body, "What to get")
        self.var_mp4 = tk.BooleanVar(value=True)
        self.var_vid = tk.BooleanVar(value=False)
        self.var_aud = tk.BooleanVar(value=False)

        t = Tile(body, "MP4 \u2014 video + audio together",
                 "One combined file. The classic download.", self.var_mp4, self._sync)
        t.pack(fill="x", pady=(6, 6))
        ToolTip(t.title_lbl, "Creates a single MP4 with both picture and sound. "
                             "Requires ffmpeg (already installed).")
        t = Tile(body, "Video only",
                 "Just the picture track, no sound (webm/mp4).", self.var_vid, self._sync)
        t.pack(fill="x", pady=(0, 6))
        ToolTip(t.title_lbl, "Downloads the video stream alone. The file will have "
                             "no audio track \u2014 combine it with an Audio only "
                             "download later if you like.")
        t = Tile(body, "Audio only",
                 "Sound only \u2014 convert to mp3 / m4a / opus / wav.", self.var_aud, self._sync)
        t.pack(fill="x", pady=(0, 4))
        ToolTip(t.title_lbl, "Extracts just the sound. For music choose the format "
                             "below the cards \u2014 mp3 or m4a is usually best.")

        # quality / audio format
        frow = tk.Frame(body, bg=BG)
        frow.pack(fill="x", pady=(8, 2))
        self.qlbl = tk.Label(frow, text="Video quality", bg=BG, fg=MUTED,
                             font=(FONT, 9))
        self.qlbl.pack(side="left", padx=(2, 8))
        self.qcombo = ttk.Combobox(frow, values=QUALITIES, state="readonly",
                                   width=14, font=(FONT, 9))
        self.qcombo.current(2)
        self.qcombo.pack(side="left")
        ToolTip(self.qcombo, "Upper limit for the video. \u201cBest\u201d takes the "
                             "highest available (can be very large). 1080p is a good "
                             "balance for most people.")

        frow2 = tk.Frame(body, bg=BG)
        frow2.pack(fill="x", pady=(6, 2))
        self.albl = tk.Label(frow2, text="Audio format", bg=BG, fg=MUTED,
                             font=(FONT, 9))
        self.albl.pack(side="left", padx=(2, 8))
        self.acombo = ttk.Combobox(frow2, values=AUDIO_FMTS, state="readonly",
                                   width=22, font=(FONT, 9))
        self.acombo.current(0)
        self.acombo.pack(side="left")
        ToolTip(self.acombo, "For music:  mp3 = most compatible  \u2022  m4a = slightly "
                             "better quality per MB  \u2022  opus = best quality, fewer "
                             "devices  \u2022  wav = lossless but huge.")
        tk.Label(frow2, text="only when \u201cAudio only\u201d is ticked",
                 bg=BG, fg="#5A5A5A", font=(FONT, 8)).pack(side="left", padx=(10, 0))

        # --- subtitles ---
        self._section(body, "Subtitles")
        srow = tk.Frame(body, bg=BG)
        srow.pack(fill="x", pady=(6, 2))
        self.sub_var = tk.BooleanVar(value=False)
        self.sub_chk = tk.Checkbutton(srow, text="Download", variable=self.sub_var,
                                      command=self._sync, bg=BG, fg=TEXT, selectcolor=CARD_ON,
                                      activebackground=BG, activeforeground=TEXT,
                                      font=(FONT, 9, "bold"), highlightthickness=0)
        self.sub_chk.pack(side="left")
        tk.Label(srow, text="languages", bg=BG, fg=MUTED, font=(FONT, 9)).pack(side="left")
        self.sub_box = tk.Entry(srow, width=14, bg=PANEL, fg=TEXT, relief="flat",
                                insertbackground=TEXT, font=(FONT, 9),
                                highlightthickness=1, highlightbackground=BORD,
                                highlightcolor=RED)
        self.sub_box.insert(0, "en")
        self.sub_box.pack(side="left", padx=(6, 12), ipady=3)
        self.auto_var = tk.BooleanVar(value=True)
        self.auto_chk = tk.Checkbutton(srow, text="Auto-generated", variable=self.auto_var,
                                       bg=BG, fg=TEXT, selectcolor=CARD_ON,
                                       activebackground=BG, activeforeground=TEXT,
                                       font=(FONT, 9), highlightthickness=0)
        self.auto_chk.pack(side="left")
        frow3 = tk.Frame(body, bg=BG)
        frow3.pack(fill="x", pady=(6, 2))
        tk.Label(frow3, text="Sub file type", bg=BG, fg=MUTED, font=(FONT, 9)).pack(
            side="left", padx=(2, 8))
        self.subfmt = ttk.Combobox(frow3, values=SUB_FMTS, state="readonly",
                                   width=8, font=(FONT, 9))
        self.subfmt.current(0)
        self.subfmt.pack(side="left")
        tk.Label(frow3, text="  srt / vtt = plain text \u2014 open in Notepad",
                 bg=BG, fg="#5A5A5A", font=(FONT, 8)).pack(side="left")

        # --- destination ---
        self._section(body, "Save to")
        drow = tk.Frame(body, bg=BG)
        drow.pack(fill="x", pady=(6, 4))
        self.dir_var = tk.StringVar(value=DEFAULT_OUT)
        self.dir_box = tk.Entry(drow, textvariable=self.dir_var, bg=PANEL, fg=TEXT,
                                relief="flat", insertbackground=TEXT, font=(FONT, 9),
                                highlightthickness=1, highlightbackground=BORD,
                                highlightcolor=RED)
        self.dir_box.pack(side="left", fill="x", expand=True, ipady=4)
        b = tk.Button(drow, text="Browse", command=self._browse, bg=CARD_ON, fg=TEXT,
                      relief="flat", font=(FONT, 9), cursor="hand2", padx=14, pady=3,
                      bd=0, activebackground=HOVER, activeforeground=TEXT)
        b.pack(side="left", padx=(8, 0))

        # --- download ---
        self.dl = tk.Button(body, text="Download", command=self._download, bg=RED, fg="white",
                            activebackground=RED_HI, activeforeground="white",
                            relief="flat", font=(FONT, 12, "bold"), cursor="hand2",
                            pady=9, bd=0)
        self.dl.pack(fill="x", pady=(12, 6))
        self.dl.bind("<Enter>",
                     lambda _e: self.dl.configure(bg=RED_HI) if not self.downloading else None)
        self.dl.bind("<Leave>", lambda _e: self.dl.configure(bg=RED))
        ToolTip(self.dl, "Downloads everything still ticked under \u201cFound videos\u201d.")

        self.bar = ttk.Progressbar(body, mode="determinate",
                                   style="Horizontal.TProgressbar", maximum=100)
        self.bar.pack(fill="x", pady=(0, 4))
        self.status = tk.Label(body, text="Ready \u2014 paste a link and press Preview "
                                          "titles, then Download.", bg=BG, fg=MUTED,
                               anchor="w", font=(FONT, 8))
        self.status.pack(fill="x", pady=(0, 6))

        # --- activity ---
        self._section(body, "Activity")
        self.log = tk.Text(body, bg="#0B0B0B", fg="#C9C9C9", relief="flat", state="disabled",
                           font=(FONT_MONO, 8), padx=8, pady=6,
                           highlightthickness=1, highlightbackground=BORD)
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("ok", foreground=GREEN)
        self.log.tag_configure("warn", foreground=WARN)
        self.log.tag_configure("err", foreground=ERR)
        self.log.tag_configure("head", foreground=TEXT)
        self._sync()

    def _header(self):
        h = tk.Frame(self, bg=BG)
        h.pack(fill="x", padx=20, pady=(14, 8))
        try:
            logo = tk.PhotoImage(file=resource_path("logo.png"))
            self.logo_img = logo.subsample(14, 14)
        except (tk.TclError, OSError):
            self.logo_img = None
        if self.logo_img is not None:
            tk.Label(h, image=self.logo_img, bg=BG).pack(side="left")
        tk.Label(h, text="Rey YouTube", bg=BG, fg=TEXT, font=(FONT, 18, "bold")
                 ).pack(side="left", padx=(10, 0))
        tk.Label(h, text="Downloader", bg=BG, fg=RED, font=(FONT, 18, "bold")
                 ).pack(side="left")
        help_btn = tk.Button(h, text="\u24D8", command=self.toggle_help, bg=BG,
                             fg=MUTED, relief="flat", font=(FONT, 16, "bold"),
                             cursor="hand2", bd=0, activebackground=BG,
                             activeforeground=RED)
        help_btn.pack(side="right", padx=(0, 2))

        self.yt_chip = tk.Button(h, text="yt-dlp: \u2026", command=self.check_ytdlp,
                                 bg="#262626", fg=TEXT, relief="flat",
                                 font=(FONT, 8, "bold"), cursor="hand2", bd=0,
                                 padx=8, pady=3, activebackground=HOVER,
                                 activeforeground=TEXT)
        self.yt_chip.pack(side="right", padx=(6, 8))
        ToolTip(self.yt_chip, "Checks that the yt-dlp engine is present and working. "
                              "If it\u2019s missing, this button installs it for you "
                              "(click it any time to verify / reinstall).")
        line = tk.Frame(self, bg="#262626", height=1)
        line.pack(fill="x")

    def _build_help(self):
        self.help_card = tk.Frame(self, bg=PANEL, highlightthickness=1,
                                  highlightbackground=BORD)
        lab = tk.Label(self.help_card, text="QUICK GUIDE", bg=PANEL, fg=TEXT,
                       font=(FONT, 8, "bold"), anchor="w")
        lab.pack(fill="x", padx=12, pady=(8, 2))
        tx = tk.Label(self.help_card, text=HELP_TEXT, bg=PANEL, fg="#C9C9C9",
                      font=(FONT, 9), justify="left", anchor="w",
                      wraplength=690)
        tx.pack(fill="x", padx=12, pady=(0, 10))
        self.help_card.pack(fill="x", padx=20, pady=(8, 0))
        self.help_card.pack_forget()

    def toggle_help(self):
        if self.help_on:
            self.help_card.pack_forget()
            self.help_on = False
        else:
            self.help_card.pack(fill="x", padx=20, pady=(8, 0), before=self.body)
            self.help_on = True

    def _section(self, parent, text):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(10, 0))
        tk.Label(row, text=text.upper(), bg=BG, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(side="left")

    # ---------------- misc ----------------
    def _wheel(self, e):
        self.found_canvas.yview_scroll(int(-e.delta / 120), "units")

    def _sync(self):
        has_video = self.var_mp4.get() or self.var_vid.get()
        self.qcombo.configure(state="readonly" if has_video else "disabled")
        self.qlbl.configure(fg=TEXT if has_video else "#555")
        self.acombo.configure(state="readonly" if self.var_aud.get() else "disabled")
        self.albl.configure(fg=TEXT if self.var_aud.get() else "#555")
        st = "normal" if self.sub_var.get() else "disabled"
        self.sub_box.configure(state=st)
        self.subfmt.configure(state="readonly" if self.sub_var.get() else "disabled")
        self.auto_chk.configure(state=st)

    def _invalidate(self):
        self.sig = None
        if not self.previewing:
            self._count_selected()  # keep label consistent

    def _apply_log(self, msg, kind=None):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n", kind)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _log(self, msg, kind=None):
        self._post(self._apply_log, msg, kind)

    # ---------------- yt-dlp engine ----------------
    def _apply_yt_chip(self, text, color, state="normal"):
        self.yt_chip.configure(text=text, fg=color, state=state)

    def _set_yt_chip(self, text, color, state="normal"):
        self._post(self._apply_yt_chip, text, color, state)

    def _apply_bar(self, value):
        self.bar.configure(value=value)

    def _set_bar(self, value):
        self._post(self._apply_bar, value)

    def check_ytdlp(self, prompt_if_missing=True):
        """Verify the yt-dlp engine; called on startup, on button click and
        whenever the app needs it."""
        if self.yt_state == "busy":
            return
        self.yt_state = "busy"
        self._set_yt_chip("yt-dlp: checking\u2026", MUTED, "disabled")
        threading.Thread(target=self._do_check, args=(prompt_if_missing,),
                         daemon=True).start()

    def _do_check(self, prompt_if_missing):
        ok = False
        ver = ""
        if os.path.exists(YDLP):
            try:
                proc = subprocess.run([YDLP, "--version"],
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, encoding="utf-8", errors="replace",
                                      timeout=30,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                ver = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
                ok = proc.returncode == 0
            except Exception:
                ok = False
        self.yt_state = f"ok:{ver}" if ok else "missing"
        if ok:
            self._set_yt_chip(f"yt-dlp: v{ver}", GREEN)
            self._log(f"yt-dlp engine present: v{ver}", "ok")
            self._post(self._run_resume)
        else:
            self._set_yt_chip("yt-dlp: not found", ERR)
            self._log("yt-dlp engine not found \u2014 click the \u201cyt-dlp: not found\u201d "
                      "button in the top-right (or it can be installed automatically).", "err")
            if prompt_if_missing:
                self._post(self._ask_install)

    def _ask_install(self):
        if self.resume_after_install is None:
            self.resume_after_install = "waiting"
        install = messagebox.askyesno(
            "yt-dlp not installed",
            "This app needs the yt-dlp download engine, which wasn\u2019t found.\n\n"
            "Install it now? (Downloads ~20 MB from the official GitHub release "
            "straight into the app folder \u2014 nothing else changes.)")
        if install:
            self.install_ytdlp()
        else:
            self.resume_after_install = None
            self.after(0, self._set_status,
                       "yt-dlp is missing. Press the red \u201cyt-dlp: not found\u201d "
                       "button above when you\u2019re ready to install it.")

    def install_ytdlp(self):
        if self.yt_state == "busy":
            return
        self.yt_state = "busy"
        self._set_yt_chip("yt-dlp: installing\u2026", WARN, "disabled")
        self._set_status("Installing yt-dlp (downloading from GitHub)\u2026")
        threading.Thread(target=self._do_install, daemon=True).start()

    def _do_install(self):
        tmp = YDLP + ".part"
        try:
            req = urllib.request.Request(YDLP_URL, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 256 * 1024)
            if os.path.exists(YDLP):
                os.remove(YDLP)
            os.replace(tmp, YDLP)
            self._log("yt-dlp downloaded successfully.", "ok")
            self.yt_state = "checking"
            self._post(self.check_ytdlp, False)
        except Exception as e:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            self.yt_state = "missing"
            self._set_yt_chip("yt-dlp: install failed", ERR)
            self._log(f"Could not download yt-dlp: {e}", "err")
            self._set_status("yt-dlp install failed. Check your internet connection and try "
                             "again, or download it yourself from the yt-dlp GitHub page.",
                             ERR)

    def require_engine(self, resume_action):
        """True if yt-dlp is present; otherwise kick off the install flow and
        remember to resume the requested action afterwards."""
        if os.path.exists(YDLP):
            return True
        self.resume_after_install = resume_action
        self.check_ytdlp(True)
        return False

    def _run_resume(self):
        if self.resume_after_install in ("download", "preview"):
            act = self.resume_after_install
            self.resume_after_install = None
            self.after(0, getattr(self, "download" if act == "download" else "preview"))
        elif self.resume_after_install == "waiting":
            self.resume_after_install = None

    # ---------------- preview ----------------
    def _text_sig(self):
        return self.url_box.get("1.0", "end").strip()

    def preview(self):
        if self.previewing or self.downloading:
            return
        urls = [u.strip() for u in self.url_box.get("1.0", "end").splitlines() if u.strip()]
        if not urls:
            messagebox.showinfo("Nothing to look up", "Paste a link first, then press "
                                                      "\u201cPreview titles\u201d.")
            return
        if not self.require_engine("preview"):
            return
        self.previewing = True
        self._set_status("Looking up link(s)\u2026")
        threading.Thread(target=self._fetch_all, args=(urls,), daemon=True).start()

    def _fetch_all(self, urls):
        self.links = []
        total = 0
        for i, url in enumerate(urls, 1):
            self._set_status(f"Looking up link {i}/{len(urls)}\u2026")
            out = err = ""
            try:
                proc = subprocess.run(
                    [YDLP, "--flat-playlist", "--simulate", "--skip-download",
                     "--no-warnings", "--quiet", "--print", "%(id)s\t%(title)s", url],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW)
                out, err = proc.stdout, proc.stderr.strip()
            except Exception as e:
                err = str(e)
            entries = []
            if proc and proc.returncode == 0 and out.strip():
                for n, line in enumerate(out.splitlines(), 1):
                    if "\t" in line:
                        vid, title = line.split("\t", 1)
                    else:
                        vid, title = "", line
                    if n > MAX_PREVIEW:
                        self._log(f"[link {i}] only first {MAX_PREVIEW} videos shown.",
                                  "warn")
                        break
                    entries.append((n, vid.strip(), title.strip() or f"(video {n})"))
                total += len(entries)
            if err:
                self._log(f"[link {i}] {url}", "warn")
                self._log(f"   {err[:300]}", "warn")
            self._log(f"[link {i}] found {len(entries)} video(s):  {url}", "ok")
            self.links.append({"url": url, "entries": entries})
        self._post(self._preview_done, total)

    def _preview_done(self, total):
        self.previewing = False
        self.sig = self._text_sig()
        # drop links that resolved to nothing but keep them in list w/o entries
        self.links = [l for l in self.links if l["entries"]]
        self._render_found()
        if total == 0:
            self._set_status("No videos found for those link(s).")
        else:
            self._set_status(f"Found {total} video(s). Untick any you don't want, "
                             "then press Download.")
        if getattr(self, "_auto_download", False):
            self._auto_download = False
            if total == 1:
                self.after(100, self._download)
            else:
                messagebox.showinfo("Multiple videos found",
                                    f"This link points to {total} videos.\n\n"
                                    "Untick the ones you don\u2019t want in the "
                                    "\u201cFound videos\u201d list, then press Download again.")

    def _render_found(self):
        for w in self.found_inner.winfo_children():
            w.destroy()
        if not self.links:
            self.found_card.pack_forget()
            return
        for li, l in enumerate(self.links, 1):
            if len(self.links) > 1:
                tk.Label(self.found_inner, text=f"Link {li}", bg="#191919", fg=MUTED,
                         anchor="w", font=(FONT, 8, "bold")).pack(fill="x", padx=6, pady=(6, 1))
            l["vars"] = []
            for idx, _vid, title in l["entries"]:
                var = tk.BooleanVar(value=True)
                l["vars"].append(var)
                cb = tk.Checkbutton(
                    self.found_inner, variable=var, command=self._count_selected,
                    text=f"{idx}.  {short(title)}", bg=PANEL, fg="#D9D9D9",
                    selectcolor=RED, activebackground=PANEL,
                    activeforeground=TEXT, font=(FONT, 8), anchor="w",
                    highlightthickness=0, wraplength=620, justify="left",
                    padx=8, pady=0)
                cb.pack(fill="x", anchor="w", pady=1)
        self.found_card.pack(fill="x", pady=(0, 6))
        self._count_selected()

    def _selected(self):
        out = []
        for l in self.links:
            for i, (var, _entry) in enumerate(zip(l["vars"], l["entries"])):
                if var.get():
                    out.append(i)
        return out

    def _count_selected(self):
        if not self.links:
            self.count_var.set("")
            return
        total = sum(len(l["entries"]) for l in self.links)
        sel = len(self._selected())
        self.count_var.set(f"\u2014 {sel} of {total} selected")

    def _sel_all(self):
        for l in self.links:
            for var in l["vars"]:
                var.set(True)
        self._count_selected()

    def _sel_none(self):
        for l in self.links:
            for var in l["vars"]:
                var.set(False)
        self._count_selected()

    # ---------------- plan ----------------
    def _sub_lang_args(self):
        langs = self.sub_box.get().strip() or "en"
        a = ["--sub-langs", "all" if langs.lower() == "all" else langs]
        if self.auto_var.get():
            a += ["--write-auto-subs"]
        return a

    def _base(self, out):
        try:
            os.makedirs(out, exist_ok=True)
        except OSError:
            pass
        return [YDLP, "--newline", "--no-warnings", "--no-mtime",
                "-P", out, "-o", "%(title).120s [%(id)s].%(ext)s"]

    def _quality(self, a):
        h = res_of(self.qcombo.get())
        if h:
            a += ["-S", f"res:{h}"]

    def _link_tasks(self, url, indices):
        """yt-dlp argv per deliverable for one link (selected indices, 1-based)."""
        multi = len(indices) > 1
        csv = ",".join(map(str, indices))
        def items(a):
            return a + (["--playlist-items", csv] if multi else []) + [url]

        out = self.dir_var.get().strip() or DEFAULT_OUT
        mp4 = self.var_mp4.get()
        vid = self.var_vid.get()
        aud = self.var_aud.get()
        subs = self.sub_var.get()
        tasks = []
        if mp4:
            a = self._base(out) + ["-f", "bv*+ba/b"]
            self._quality(a)
            a += ["--merge-output-format", "mp4",
                  "--embed-thumbnail", "--embed-metadata"]
            if subs:
                a += self._sub_lang_args()
                a += ["--embed-subs", "--convert-subs", "srt"]
            tasks.append(("MP4 (video + audio)", items(a)))
        if vid:
            a = self._base(out) + ["-f", "bv*"]
            self._quality(a)
            a += ["--embed-thumbnail", "--embed-metadata"]
            tasks.append(("Video only", items(a)))
        if aud:
            a = self._base(out)
            af = self.acombo.get()
            if af.startswith("original"):
                a += ["-f", "bestaudio"]
            else:
                a += ["-x", "--audio-format", af]
            a += ["--embed-thumbnail", "--embed-metadata"]
            tasks.append(("Audio only", items(a)))
        if subs and not mp4:
            a = self._base(out) + ["--skip-download"]
            a += self._sub_lang_args()
            a += ["--write-subs", "--convert-subs", self.subfmt.get() or "srt"]
            tasks.append(("Subtitles only", items(a)))
        return tasks

    def _make_plan(self):
        plan = []
        for li, l in enumerate(self.links, 1):
            chosen = [idx + 1 for idx, (var, _e) in enumerate(zip(l["vars"], l["entries"]))
                      if var.get()]
            if not chosen:
                continue
            tag = f"link {li}" if len(self.links) > 1 else ""
            n = len(chosen)
            label = f"{n} video(s)" if n > 1 else "1 video"
            for dl, argv in self._link_tasks(l["url"], chosen):
                plan.append((f"{dl} \u00b7 {label}{' \u00b7 ' + tag if tag else ''}", argv))
        return plan

    # ---------------- download ----------------
    def _download(self):
        if self.downloading:
            return
        sig = self._text_sig()
        if not sig:
            messagebox.showinfo("Nothing to do", "Paste a video link first.")
            return
        if not self.require_engine("download"):
            return
        if self.links and self.sig == sig:
            if not self._selected():
                messagebox.showwarning("Nothing selected",
                                       "Every video is unticked. Tick the ones you "
                                       "want under \u201cFound videos\u201d.")
                return
            if not (self.var_mp4.get() or self.var_vid.get()
                    or self.var_aud.get() or self.sub_var.get()):
                messagebox.showwarning("Nothing to download",
                                       "Tick at least one item under \u201cWhat to get\u201d.")
                return
            self._start(self._make_plan())
        else:
            # need a fresh lookup first
            self._auto_download = True
            self.preview()

    def _start(self, plan):
        if not plan:
            messagebox.showwarning("Nothing to download",
                                   "Nothing is ticked to download.")
            return
        self.plan = plan
        self.downloading = True
        self.dl.configure(state="disabled", text="Downloading\u2026")
        self.bar.configure(value=0)
        self.last_pct = -1
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        total_steps = len(self.plan)
        for i, (label, argv) in enumerate(self.plan, 1):
            self._set_status(f"Step {i}/{total_steps} \u00b7 {label}")
            self._log(f"\n--- step {i}/{total_steps}: {label} ---", "head")
            try:
                proc = subprocess.Popen(argv, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True,
                                        encoding="utf-8", errors="replace",
                                        creationflags=subprocess.CREATE_NO_WINDOW)
                for line in proc.stdout:
                    self._handle_line(line.rstrip("\n"), i, total_steps, label)
                proc.wait()
                if proc.returncode == 0:
                    self._log("\u2713 done", "ok")
                else:
                    self._log(f"step failed with code {proc.returncode}", "err")
            except Exception as e:
                self._log(f"ERROR: {e}", "err")
        self._log("\nAll finished.", "ok")
        self._post(self._done)

    def _handle_line(self, line, step, steps, label):
        if not line:
            return
        m = DEST_RE.match(line)
        if m:
            self.cur_name = os.path.basename(m.group(1).strip())
            return
        m = PCT_RE.match(line)
        if m:
            pct = min(100.0, float(m.group(1)))
            if pct != self.last_pct:
                self.last_pct = pct
                self._ui_progress(pct, self.cur_name, step, steps, label)
            return
        m = ITEM_RE.match(line)
        if m:
            self._set_status(f"Step {step}/{steps} \u00b7 {label} \u00b7 "
                             f"item {m.group(1)} of {m.group(2)}")
            return
        if re.search(r"\bERROR\b|\[error\]|failed", line, re.I):
            self._log(line, "err")
        elif re.search(r"\bwarning", line, re.I):
            self._log(line, "warn")
        elif line.startswith("["):
            self._log(line)

    def _ui_progress(self, pct, name, step, steps, label):
        name_part = f" \u00b7 {name}" if name else ""
        self._set_bar(pct)
        self._set_status(f"Step {step}/{steps} \u00b7 {label}{name_part} \u00b7 {pct:.1f}%")

    # ---------------- small helpers ----------------
    def _apply_status(self, text, color=TEXT):
        self.status.configure(text=text, fg=color)

    def _set_status(self, text, color=TEXT):
        self._post(self._apply_status, text, color)

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get() or app_dir())
        if d:
            self.dir_var.set(d)

    def _done(self):
        self._set_bar(0)
        self.downloading = False
        self.dl.configure(state="normal", text="Download")
        self.status.configure(text="Finished.", fg=GREEN)


if __name__ == "__main__":
    app = YTdlpGUI()
    app.mainloop()
