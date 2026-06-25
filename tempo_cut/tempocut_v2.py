"""
TempoCut v1.2
Broadcast-grade time compression tool — PyQt5 UI
- Auto audio extraction from video (no separate WAV input needed)
- Live video preview with OpenCV in Editor + Preview tabs
- Sub-frame Premiere-style frame blending
- Spaces-in-paths safe subprocess calls
- Fast sequential-decode render core (time_compressor_SAFE_v2.py):
  OpenCV LRU-cached forward decode + raw ffmpeg pipe encode,
  replacing moviepy's per-frame reseeking for a large speedup.
"""

import sys, os, subprocess, tempfile
import numpy as np

try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QTabWidget, QSlider, QCheckBox, QComboBox, QGroupBox,
    QProgressBar, QTextEdit, QFrame, QSpinBox,
    QDoubleSpinBox, QScrollArea, QMessageBox, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import (
    QColor, QPalette, QFont, QPixmap, QPainter, QLinearGradient,
    QBrush, QPen, QImage, QIcon
)

# ── COLOURS ──────────────────────────────────
BG_DARK      = "#0e1520"
BG_MID       = "#141d2e"
BG_PANEL     = "#1a2438"
BG_FIELD     = "#0a0f1a"
BG_HEADER    = "#0d1828"
ACCENT_BLUE  = "#1a6fb5"
ACCENT_GREEN = "#1db86e"
ACCENT_RED   = "#c0392b"
ACCENT_GOLD  = "#c8a020"
TEXT_PRIMARY = "#d8e4f0"
TEXT_MUTED   = "#6a8aaa"
TEXT_LABEL   = "#8aaac8"
BORDER       = "#1e3050"
BORDER_BRIGHT= "#2a4870"
BASE_FONT    = "Segoe UI"
MONO_FONT    = "Consolas"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK}; color: {TEXT_PRIMARY};
    font-family: '{BASE_FONT}'; font-size: 12px;
}}
QTabWidget::pane {{ border: 1px solid {BORDER}; background: {BG_PANEL}; top: -1px; }}
QTabBar::tab {{
    background: {BG_MID}; color: {TEXT_MUTED}; padding: 7px 20px;
    border: 1px solid {BORDER}; border-bottom: none;
    font-size: 11px; font-weight: 600; letter-spacing: 1px;
}}
QTabBar::tab:selected {{ background: {BG_PANEL}; color: {TEXT_PRIMARY}; border-bottom: 2px solid {ACCENT_BLUE}; }}
QTabBar::tab:hover:!selected {{ background: {BG_PANEL}; color: {TEXT_PRIMARY}; }}
QGroupBox {{
    border: 1px solid {BORDER}; border-radius: 4px; margin-top: 18px; padding-top: 8px;
    font-size: 11px; font-weight: 700; color: {TEXT_LABEL}; letter-spacing: 1.5px;
}}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; left: 10px; top: 2px; color: {ACCENT_BLUE}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
    background: {BG_FIELD}; border: 1px solid {BORDER}; border-radius: 3px;
    color: {TEXT_PRIMARY}; padding: 4px 8px; font-family: '{MONO_FONT}'; font-size: 12px;
    selection-background-color: {ACCENT_BLUE};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 1px solid {ACCENT_BLUE}; }}
QComboBox::drop-down {{ border: none; background: {BG_MID}; width: 20px; }}
QComboBox QAbstractItemView {{ background: {BG_MID}; border: 1px solid {BORDER_BRIGHT}; color: {TEXT_PRIMARY}; selection-background-color: {ACCENT_BLUE}; }}
QPushButton {{
    background: {BG_MID}; border: 1px solid {BORDER_BRIGHT}; border-radius: 3px;
    color: {TEXT_PRIMARY}; padding: 5px 14px; font-size: 11px; font-weight: 600;
}}
QPushButton:hover {{ background: {ACCENT_BLUE}; border-color: {ACCENT_BLUE}; }}
QPushButton:pressed {{ background: #155a96; }}
QPushButton#btn_run {{
    background: {ACCENT_GREEN}; border-color: {ACCENT_GREEN}; color: #fff;
    font-size: 13px; font-weight: 700; padding: 8px 28px; letter-spacing: 1px;
}}
QPushButton#btn_run:hover {{ background: #18a060; }}
QPushButton#btn_clear {{
    background: {ACCENT_RED}; border-color: {ACCENT_RED}; color: #fff;
    font-size: 12px; font-weight: 600; padding: 8px 20px;
}}
QPushButton#btn_clear:hover {{ background: #a93226; }}
QPushButton#btn_stop {{
    background: {ACCENT_GOLD}; border-color: {ACCENT_GOLD}; color: #1a1404;
    font-size: 13px; font-weight: 700; padding: 8px 24px; letter-spacing: 1px;
}}
QPushButton#btn_stop:hover {{ background: #e0b428; }}
QPushButton#btn_stop:disabled {{
    background: {BG_MID}; border-color: {BORDER}; color: {TEXT_MUTED};
}}
QPushButton#btn_browse {{
    background: {ACCENT_BLUE}; border-color: {ACCENT_BLUE}; color: #fff;
    padding: 4px 12px; font-size: 11px;
}}
QPushButton#btn_browse:hover {{ background: #1560a0; }}
QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {ACCENT_BLUE}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT_BLUE}; border-radius: 2px; }}
QProgressBar {{
    background: {BG_FIELD}; border: 1px solid {BORDER}; border-radius: 3px;
    height: 16px; text-align: center; color: {TEXT_PRIMARY}; font-size: 11px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT_BLUE}, stop:1 {ACCENT_GREEN});
    border-radius: 2px;
}}
QCheckBox {{ color: {TEXT_PRIMARY}; spacing: 6px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {BORDER_BRIGHT}; border-radius: 2px; background: {BG_FIELD}; }}
QCheckBox::indicator:checked {{ background: {ACCENT_GREEN}; border-color: {ACCENT_GREEN}; }}
QScrollBar:vertical {{ background: {BG_DARK}; width: 8px; border: none; }}
QScrollBar::handle:vertical {{ background: {BORDER_BRIGHT}; border-radius: 4px; min-height: 20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLabel#section_header {{
    color: {ACCENT_BLUE}; font-size: 11px; font-weight: 700; letter-spacing: 2px;
    padding: 3px 0; border-bottom: 1px solid {BORDER};
}}
QLabel#field_label {{ color: {TEXT_LABEL}; font-size: 11px; }}
QFrame#divider {{ background: {BORDER}; max-height: 1px; }}
QStatusBar {{ background: {BG_HEADER}; color: {TEXT_MUTED}; border-top: 1px solid {BORDER}; font-size: 11px; }}
"""

# ── HELPERS ───────────────────────────────────

def _bundled_bin_dir():
    """Folder to check for bundled files (ffmpeg/ffprobe, embedded_python).
    Modern PyInstaller (6.x) onedir builds put all bundled data inside an
    _internal/ subfolder next to the .exe, not directly alongside it --
    check there first, falling back to the exe's own folder for older
    PyInstaller layouts that didn't use _internal."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(exe_dir, "_internal")
        return internal_dir if os.path.isdir(internal_dir) else exe_dir
    return os.path.dirname(os.path.abspath(__file__))


_BINARY_CACHE = {}

def find_binary(name):
    """
    Resolve 'ffmpeg' or 'ffprobe' to an actual path. Checks, in order:
      1. A copy bundled right next to TempoCut.exe (drop ffmpeg.exe and
         ffprobe.exe in the install folder and they'll be picked up here
         with zero configuration).
      2. The system PATH (works if the user already has ffmpeg installed
         globally, e.g. for other broadcast/video work).
    Raises a clear, actionable RuntimeError if neither is found, instead
    of letting a bare "ffmpeg" call fail deep inside a subprocess with an
    opaque [WinError 2].
    """
    if name in _BINARY_CACHE:
        return _BINARY_CACHE[name]

    exe_name = name + (".exe" if os.name == "nt" else "")
    bundled = os.path.join(_bundled_bin_dir(), exe_name)
    if os.path.exists(bundled):
        _BINARY_CACHE[name] = bundled
        return bundled

    import shutil
    on_path = shutil.which(name)
    if on_path:
        _BINARY_CACHE[name] = on_path
        return on_path

    raise RuntimeError(
        f"FATAL: '{name}' was not found. TempoCut needs {name}.exe to process "
        f"video/audio, but it isn't bundled in this install and isn't on your "
        f"system PATH.\n\n"
        f"Fix: download a static ffmpeg build (e.g. from gyan.dev or "
        f"github.com/BtbN/FFmpeg-Builds), then copy ffmpeg.exe and ffprobe.exe "
        f"directly into:\n{_bundled_bin_dir()}\n\n"
        f"Then try the job again."
    )


def detect_video_fps(video_path):
    """Use ffprobe to read the source video's actual frame rate.
    Returns a float fps, or None if detection fails."""
    try:
        result = subprocess.run(
            [find_binary("ffprobe"), "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate",
             "-of", "default=noprint_wrappers=1:nokey=1",
             video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10
        )
        raw = result.stdout.strip()
        if not raw:
            return None
        if "/" in raw:
            num, den = raw.split("/")
            den = float(den)
            if den == 0:
                return None
            return float(num) / den
        return float(raw)
    except Exception:
        return None


def field_row(label_text, widget, browse_cb=None):
    row = QHBoxLayout()
    lbl = QLabel(label_text + ":")
    lbl.setObjectName("field_label")
    lbl.setFixedWidth(160)
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    if browse_cb:
        btn = QPushButton("Browse"); btn.setObjectName("btn_browse")
        btn.setFixedWidth(72); btn.clicked.connect(browse_cb)
        row.addWidget(btn)
    return row

def section_header(text):
    l = QLabel(text); l.setObjectName("section_header"); return l

def divider():
    f = QFrame(); f.setObjectName("divider"); f.setFrameShape(QFrame.HLine); return f

# ── TIMELINE BAR ──────────────────────────────
class TimelineBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(48)
        self.duration = 600.0
        self.playhead = 0.0
        self.setStyleSheet(f"background:{BG_FIELD};border:1px solid {BORDER};")

    def set_duration(self, d): self.duration = max(d, 1); self.update()
    def set_playhead(self, t): self.playhead = t; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(BG_FIELD))
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(ACCENT_GREEN))
        grad.setColorAt(0.7, QColor(ACCENT_GOLD))
        grad.setColorAt(1.0, QColor(ACCENT_RED))
        p.fillRect(0, 8, w, 20, QBrush(grad))
        p.setPen(QPen(QColor(TEXT_MUTED), 1))
        for i in range(11):
            x = int(i * w / 10)
            p.drawLine(x, 28, x, 36)
            t = i * self.duration / 10
            mins, secs = int(t // 60), int(t % 60)
            p.setPen(QColor(TEXT_MUTED)); p.setFont(QFont(MONO_FONT, 8))
            p.drawText(x - 20, 38, 40, 10, Qt.AlignCenter, f"{mins:02d}:{secs:02d}")
            p.setPen(QPen(QColor(TEXT_MUTED), 1))
        if self.duration > 0:
            px = int(self.playhead / self.duration * w)
            p.setPen(QPen(QColor("#ffffff"), 2)); p.drawLine(px, 4, px, 36)
        p.end()

# ── VIDEO PLAYER WIDGET ───────────────────────
class VideoPlayer(QWidget):
    """OpenCV-backed frame display with scrub + play/pause."""
    position_changed = pyqtSignal(float)   # emits current time in seconds

    def __init__(self, label="", parent=None):
        super().__init__(parent)
        self._cap    = None
        self._fps    = 30.0
        self._dur    = 0.0
        self._pos    = 0.0
        self._playing= False
        self._label  = label

        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(4)

        if label:
            hdr = QLabel(label)
            hdr.setStyleSheet(f"color:{ACCENT_BLUE};font-weight:700;font-size:11px;letter-spacing:2px;padding:2px 0;border-bottom:1px solid {BORDER};")
            lay.addWidget(hdr)

        self.canvas = QLabel()
        self.canvas.setAlignment(Qt.AlignCenter)
        self.canvas.setStyleSheet(f"background:#000;border:1px solid {BORDER};")
        self.canvas.setMinimumHeight(240)
        lay.addWidget(self.canvas, 1)

        self.tc = QLabel("00:00:00")
        self.tc.setAlignment(Qt.AlignCenter)
        self.tc.setStyleSheet(f"font-family:'{MONO_FONT}';font-size:14px;color:{ACCENT_GREEN};background:{BG_FIELD};border:1px solid {BORDER};padding:3px;")
        lay.addWidget(self.tc)

        ctrl = QHBoxLayout(); ctrl.setSpacing(8)
        ctrl.addStretch()
        for sym, tip, cb in [
            ("⏮","Go to start", self._go_start),
            ("⏪","Back 10s",    self._back10),
            ("▶","Play/Pause",  self._toggle_play),
            ("⏩","Fwd 10s",    self._fwd10),
            ("⏭","Go to end",   self._go_end),
        ]:
            b = QPushButton(sym); b.setToolTip(tip); b.setFixedSize(40, 32)
            if sym == "▶": self._btn_play = b
            b.clicked.connect(cb); ctrl.addWidget(b)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.scrub = QSlider(Qt.Horizontal)
        self.scrub.setRange(0, 10000)
        self.scrub.sliderMoved.connect(self._on_scrub)
        lay.addWidget(self.scrub)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        if not CV2_OK:
            self.canvas.setText("Install opencv-python for preview\npip install opencv-python")
            self.canvas.setStyleSheet(f"background:#000;color:{TEXT_MUTED};border:1px solid {BORDER};font-size:12px;")

    def load(self, path):
        if not CV2_OK: return
        if self._cap: self._cap.release()
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            self.canvas.setText("Could not open file"); return
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames    = self._cap.get(cv2.CAP_PROP_FRAME_COUNT)
        self._dur = frames / self._fps
        self._pos = 0.0
        self._show_frame(0.0)

    def _show_frame(self, t):
        if not CV2_OK or not self._cap: return
        t = max(0.0, min(t, self._dur - 1/self._fps))
        self._pos = t
        frame_idx = int(t * self._fps)
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self._cap.read()
        if not ret: return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img)
        cw, ch2 = self.canvas.width(), self.canvas.height()
        self.canvas.setPixmap(pix.scaled(cw, ch2, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        mins, secs = int(t // 60), int(t % 60)
        frames_rem = int((t % 1) * self._fps)
        self.tc.setText(f"{mins:02d}:{secs:02d}:{frames_rem:02d}")
        if self._dur > 0:
            self.scrub.setValue(int(t / self._dur * 10000))
        self.position_changed.emit(t)

    def _on_scrub(self, val):
        if self._dur > 0:
            self._show_frame(val / 10000.0 * self._dur)

    def _toggle_play(self):
        self._playing = not self._playing
        self._btn_play.setText("⏸" if self._playing else "▶")
        if self._playing:
            self._timer.start(int(1000 / self._fps))
        else:
            self._timer.stop()

    def _tick(self):
        if self._pos >= self._dur - 1/self._fps:
            self._playing = False; self._timer.stop(); self._btn_play.setText("▶"); return
        self._show_frame(self._pos + 1/self._fps)

    def _go_start(self): self._show_frame(0.0)
    def _go_end(self):   self._show_frame(self._dur - 1/self._fps)
    def _back10(self):   self._show_frame(self._pos - 10.0)
    def _fwd10(self):    self._show_frame(self._pos + 10.0)

    def get_pos(self): return self._pos
    def get_dur(self): return self._dur

# ── HEADER ────────────────────────────────────
class HeaderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(64)
        self.setStyleSheet(f"background:{BG_HEADER};border-bottom:2px solid {ACCENT_BLUE};")
        lay = QHBoxLayout(self); lay.setContentsMargins(20,0,20,0)
        logo = QLabel("TEMPO<span style='color:#1a6fb5'>CUT</span>")
        logo.setStyleSheet(f"font-size:26px;font-weight:900;color:{TEXT_PRIMARY};letter-spacing:3px;font-family:'{BASE_FONT}';")
        logo.setTextFormat(Qt.RichText); lay.addWidget(logo)
        tag = QLabel("Broadcast Time Compression Suite  ·  v1.2 (fast render)")
        tag.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;letter-spacing:1px;"); lay.addWidget(tag)
        lay.addStretch()
        for label, color in [("DTW ENGINE", ACCENT_BLUE), ("59.94p", ACCENT_GREEN), ("5.1 AUDIO", ACCENT_GOLD)]:
            b = QLabel(label)
            b.setStyleSheet(f"background:{color}22;color:{color};border:1px solid {color};border-radius:3px;padding:2px 8px;font-size:10px;font-weight:700;letter-spacing:1px;")
            lay.addWidget(b); lay.addSpacing(6)

# ── JOB TAB ───────────────────────────────────
class JobTab(QWidget):
    video_loaded = pyqtSignal(str)   # emits path when video is picked

    def __init__(self):
        super().__init__()
        self.detected_fps = None
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        main = QVBoxLayout(inner); main.setSpacing(14); main.setContentsMargins(16,16,16,16)

        # INPUT
        grp_in = QGroupBox("Input File Segment")
        gin = QVBoxLayout(grp_in); gin.setSpacing(8)
        gin.addWidget(section_header("Segment 1"))

        self.inp_video = QLineEdit(); self.inp_video.setPlaceholderText("Input video (.mp4 .mov .mxf …)")
        self.inp_subs  = QLineEdit(); self.inp_subs.setPlaceholderText("Subtitles / Captions (.srt .stl .scc) — optional")

        gin.addLayout(field_row("Input Video", self.inp_video, self._browse_video))
        gin.addLayout(field_row("Input Subtitles", self.inp_subs, self._browse_subs))

        note = QLabel("Audio is extracted automatically from the video — no separate WAV needed.")
        note.setStyleSheet(f"color:{ACCENT_GREEN};font-size:11px;padding:4px 0;")
        gin.addWidget(note)

        tc_row = QHBoxLayout()
        for label, attr, default in [("Start TC","tc_start","00:00:00:00"),("Stop TC","tc_stop","00:00:00:00")]:
            tc_row.addWidget(QLabel(label+":"))
            tc = QLineEdit(default); tc.setFixedWidth(110); setattr(self, attr, tc)
            tc_row.addWidget(tc); tc_row.addSpacing(12)
        tc_row.addStretch(); gin.addLayout(tc_row)

        gin.addWidget(divider())

        # ── Target Output Length ──
        # If the user knows exactly how long they want the final output to
        # be, this bypasses the manual Target Ratio entirely: the ratio gets
        # computed automatically from (original duration / target duration),
        # and the Compression tab auto-selects Light/Balanced/Heavy based on
        # how aggressive that computed ratio actually needs to be.
        target_row = QHBoxLayout()
        self.target_enable = QCheckBox("Target a specific output length (bypasses Target Ratio)")
        target_row.addWidget(self.target_enable)
        gin.addLayout(target_row)

        target_input_row = QHBoxLayout()
        target_lbl = QLabel("Target Length:"); target_lbl.setObjectName("field_label")
        target_input_row.addWidget(target_lbl)
        self.target_length = QLineEdit(); self.target_length.setPlaceholderText("e.g. 21:30 or 00:21:30")
        self.target_length.setFixedWidth(120)
        self.target_length.setEnabled(False)
        target_input_row.addWidget(self.target_length)
        target_input_row.addSpacing(10)
        target_input_row.addWidget(QLabel("Format:"))
        self.target_format = QComboBox()
        self.target_format.addItems(["MM:SS", "HH:MM:SS"])
        self.target_format.setFixedWidth(110)
        self.target_format.setEnabled(False)
        target_input_row.addWidget(self.target_format)
        target_input_row.addStretch()
        gin.addLayout(target_input_row)

        target_hint = QLabel("Computes the required Target Ratio automatically and picks the best Skippy Mode (Light/Balanced/Heavy) for it on the Compression tab.")
        target_hint.setWordWrap(True)
        target_hint.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;")
        gin.addWidget(target_hint)

        self.target_enable.toggled.connect(self.target_length.setEnabled)
        self.target_enable.toggled.connect(self.target_format.setEnabled)

        main.addWidget(grp_in)

        # TIMELINE
        grp_tl = QGroupBox("Output File Timeline")
        gtl = QVBoxLayout(grp_tl)
        self.timeline = TimelineBar(); gtl.addWidget(self.timeline)
        seg_hdr = QHBoxLayout()
        for col, w in [("Segment",100),("Start",110),("Stop",110),("Reduce",110),("Percent",80)]:
            l = QLabel(col); l.setStyleSheet(f"color:{TEXT_LABEL};font-size:11px;font-weight:700;"); l.setFixedWidth(w); seg_hdr.addWidget(l)
        seg_hdr.addStretch(); gtl.addLayout(seg_hdr)
        seg_row = QHBoxLayout()
        for val, w in [("Segment 1",100),("00:00:00:00",110),("00:09:54:00",110),("00:00:06:00",110),("1.00%",80)]:
            l = QLabel(val); l.setStyleSheet(f"color:{ACCENT_GREEN};font-family:'{MONO_FONT}';font-size:11px;"); l.setFixedWidth(w); seg_row.addWidget(l)
        seg_row.addStretch(); gtl.addLayout(seg_row)
        main.addWidget(grp_tl)

        # OUTPUT
        grp_out = QGroupBox("Output Settings")
        gout = QVBoxLayout(grp_out); gout.setSpacing(8)
        self.out_path = QLineEdit(); self.out_path.setPlaceholderText("Output folder")
        self.out_name = QLineEdit(); self.out_name.setPlaceholderText("Output filename (no extension)")
        gout.addLayout(field_row("Output Path", self.out_path, self._browse_out))
        gout.addLayout(field_row("Output File Name", self.out_name))
        codec_row = QHBoxLayout()
        codec_row.addWidget(QLabel("Video Codec:"))
        self.codec_v = QComboBox(); self.codec_v.addItems(["libx264 (H.264)","libx265 (H.265)","prores_ks (ProRes)","dnxhd (DNxHD)"]); self.codec_v.setFixedWidth(180)
        codec_row.addWidget(self.codec_v); codec_row.addSpacing(16)
        codec_row.addWidget(QLabel("Audio Codec:"))
        self.codec_a = QComboBox(); self.codec_a.addItems(["Match Source (auto-detect)","AAC 640k (5.1)","PCM 24LE","AC3 640k","EAC3"]); self.codec_a.setFixedWidth(190)
        self.codec_a.setCurrentIndex(0)
        codec_row.addWidget(self.codec_a); codec_row.addSpacing(16)
        codec_row.addWidget(QLabel("Bitrate (Mb/s):"))
        self.bitrate = QSpinBox(); self.bitrate.setRange(1,200); self.bitrate.setValue(25); self.bitrate.setFixedWidth(60)
        codec_row.addWidget(self.bitrate); codec_row.addStretch(); gout.addLayout(codec_row)
        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("Output FPS:"))
        self.out_fps = QComboBox()
        self.out_fps.addItems(["Detected (from source)","59.94","29.97","23.976","25","50","60"])
        self.out_fps.setCurrentIndex(0)
        self.out_fps.setFixedWidth(180)
        fps_row.addWidget(self.out_fps); fps_row.addSpacing(16)
        fps_row.addWidget(QLabel("Preset:"))
        self.enc_preset = QComboBox(); self.enc_preset.addItems(["fast","medium","slow","ultrafast","veryslow"]); self.enc_preset.setFixedWidth(110)
        fps_row.addWidget(self.enc_preset); fps_row.addStretch(); gout.addLayout(fps_row)
        main.addWidget(grp_out)

        # SUBTITLES
        grp_sub = QGroupBox("Closed Captions / Subtitles")
        gsub = QVBoxLayout(grp_sub)
        self.sub_enable = QCheckBox("Process Closed Captions"); gsub.addWidget(self.sub_enable)
        sub_note = QLabel("Supports .srt, .stl, and .scc (CEA-608 broadcast captions)")
        sub_note.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;")
        gsub.addWidget(sub_note)
        self.sub_output = QLineEdit(); self.sub_output.setPlaceholderText("Output subtitle/caption file")
        gsub.addLayout(field_row("Output Subtitle File", self.sub_output, self._browse_sub_out))
        main.addWidget(grp_sub)

        # JOB
        grp_job = QGroupBox("Job Settings")
        gjob = QVBoxLayout(grp_job)
        self.job_name = QLineEdit(); self.job_name.setPlaceholderText("Job name")
        self.job_priority = QComboBox(); self.job_priority.addItems(["Normal","High","Low"])
        gjob.addLayout(field_row("Job Name", self.job_name))
        gjob.addLayout(field_row("Job Priority", self.job_priority))
        main.addWidget(grp_job)
        main.addStretch()

        btn_row = QHBoxLayout(); btn_row.addStretch()
        self.btn_run = QPushButton("▶  CREATE JOB"); self.btn_run.setObjectName("btn_run"); self.btn_run.setFixedHeight(36)
        self.btn_stop = QPushButton("■  STOP"); self.btn_stop.setObjectName("btn_stop"); self.btn_stop.setFixedHeight(36)
        self.btn_stop.setEnabled(False)  # nothing to stop until a job is running
        self.btn_clear = QPushButton("✕  CLEAR"); self.btn_clear.setObjectName("btn_clear"); self.btn_clear.setFixedHeight(36)
        btn_row.addWidget(self.btn_run); btn_row.addSpacing(12)
        btn_row.addWidget(self.btn_stop); btn_row.addSpacing(12)
        btn_row.addWidget(self.btn_clear); btn_row.addStretch()
        main.addLayout(btn_row)

        scroll.setWidget(inner)
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(scroll)
        self.btn_clear.clicked.connect(self._clear)

    def _browse_video(self):
        f, _ = QFileDialog.getOpenFileName(self, "Input Video", "", "Video Files (*.mp4 *.mov *.mxf *.avi *.mkv);;All Files (*)")
        if f:
            self.inp_video.setText(f)
            if not self.out_name.text():
                self.out_name.setText(os.path.splitext(os.path.basename(f))[0] + "_TC")
            if not self.out_path.text():
                self.out_path.setText(os.path.dirname(f))
            detected = detect_video_fps(f)
            self.detected_fps = detected
            if detected:
                self.out_fps.setItemText(0, f"Detected ({detected:.3f})")
            else:
                self.out_fps.setItemText(0, "Detected (from source)")
            self.video_loaded.emit(f)

    def _browse_subs(self):
        f, _ = QFileDialog.getOpenFileName(self, "Subtitles", "", "Subtitle Files (*.srt *.stl *.scc);;SCC Captions (*.scc);;SRT (*.srt);;STL (*.stl);;All Files (*)")
        if f: self.inp_subs.setText(f)
    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "Output Folder")
        if d: self.out_path.setText(d)
    def _browse_sub_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "Output Subtitle", "", "SRT (*.srt);;STL (*.stl);;SCC Captions (*.scc)")
        if f: self.sub_output.setText(f)

    def _clear(self):
        for w in [self.inp_video, self.inp_subs, self.out_path, self.out_name, self.job_name, self.sub_output]:
            w.clear()
        for tc in [self.tc_start, self.tc_stop]:
            tc.setText("00:00:00:00")
        self.target_length.clear()
        self.target_enable.setChecked(False)

    CODEC_A_MAP = {
        "Match Source (auto-detect)": "match_source",
        "AAC 640k (5.1)": "aac",
        "PCM 24LE": "pcm",
        "AC3 640k": "ac3",
        "EAC3": "eac3",
    }

    def _resolve_fps(self):
        text = self.out_fps.currentText()
        if text.startswith("Detected"):
            return self.detected_fps if self.detected_fps else 59.94
        return float(text.split()[0])

    def _parse_target_length(self):
        """Returns target length in seconds, or None if disabled/invalid."""
        if not self.target_enable.isChecked():
            return None
        text = self.target_length.text().strip()
        if not text:
            return None
        fmt = self.target_format.currentText()
        parts = text.split(":")
        try:
            parts = [int(p) for p in parts]
        except ValueError:
            return None
        if fmt == "MM:SS":
            if len(parts) == 2:
                m, s = parts
                return m * 60 + s
            elif len(parts) == 1:
                return parts[0]  # bare seconds
        else:  # HH:MM:SS
            if len(parts) == 3:
                h, m, s = parts
                return h * 3600 + m * 60 + s
            elif len(parts) == 2:
                m, s = parts
                return m * 60 + s
        return None

    def get_params(self):
        return {
            "input_video":  self.inp_video.text(),
            "input_subs":   self.inp_subs.text(),
            "output_path":  self.out_path.text(),
            "output_name":  self.out_name.text(),
            "codec_v":      self.codec_v.currentText().split()[0],
            "codec_a":      self.CODEC_A_MAP.get(self.codec_a.currentText(), "match_source"),
            "bitrate":      self.bitrate.value(),
            "fps":          self._resolve_fps(),
            "detected_fps": self.detected_fps,  # raw probed source rate, independent of any dropdown selection
            "preset":       self.enc_preset.currentText(),
            "job_name":     self.job_name.text(),
            "target_length_sec": self._parse_target_length(),
            "sub_enable":   self.sub_enable.isChecked(),
            "sub_output":   self.sub_output.text(),
        }

# ── COMPRESSION PARAMS TAB ────────────────────
class CompressionTab(QWidget):
    def __init__(self):
        super().__init__()
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget(); main = QVBoxLayout(inner); main.setSpacing(14); main.setContentsMargins(16,16,16,16)

        grp_as = QGroupBox("Audio Skippy — Time Compression Engine")
        gas_outer = QVBoxLayout(grp_as); gas_outer.setSpacing(10)

        # Preset selector (Light / Balanced / Heavy)
        preset_row = QHBoxLayout()
        preset_lbl = QLabel("Skippy Mode:"); preset_lbl.setObjectName("field_label")
        preset_row.addWidget(preset_lbl)
        self.skippy_preset = QComboBox()
        self.skippy_preset.addItems([
            "Auto — tuned automatically to fit Target Ratio (recommended)",
            "Light — less skippy, less sped up feel",
            "Balanced — recommended default",
            "Heavy — most skippy, most accurate to TBS",
            "Custom — manual values below",
        ])
        self.skippy_preset.setCurrentIndex(0)
        self.skippy_preset.setFixedWidth(380)
        preset_row.addWidget(self.skippy_preset)
        preset_row.addStretch()
        gas_outer.addLayout(preset_row)

        preset_hint = QLabel("Auto continuously tunes Frame/Chop/Cadence/Crossfade/Energy to match whatever Target Ratio is set, scaling smoothly past Light/Balanced/Heavy rather than snapping to the nearest one. Switch to a fixed preset or Custom to take manual control.")
        preset_hint.setWordWrap(True)
        preset_hint.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;")
        gas_outer.addWidget(preset_hint)
        gas_outer.addWidget(divider())

        gas = QGridLayout(); gas.setSpacing(8)
        gas_outer.addLayout(gas)
        skippy_params = [
            ("Target Ratio","target_ratio",QDoubleSpinBox,(1.0,1.5,1.0129,0.0001,4),"Compression ratio (1.0129 = ~1.28%)"),
            ("Frame Ms","frame_ms",QSpinBox,(1,100,5),"Analysis frame length in ms"),
            ("Max Chop Ms","max_chop_ms",QSpinBox,(1,100,15),"Maximum silence chop in ms"),
            ("Cadence Ms","cadence_ms",QSpinBox,(10,1000,250),"Cadence window in ms"),
            ("Crossfade Ms","crossfade_ms",QSpinBox,(0,100,10),"Crossfade between chops in ms"),
            ("Energy Quantile","energy_q",QDoubleSpinBox,(0.0,1.0,0.35,0.01,2),"Silence detection quantile"),
        ]
        self._skippy = {}
        for row,(label,key,wtype,args,hint_txt) in enumerate(skippy_params):
            lbl = QLabel(label+":"); lbl.setObjectName("field_label"); gas.addWidget(lbl,row,0)
            if wtype==QDoubleSpinBox:
                w=QDoubleSpinBox(); w.setRange(args[0],args[1]); w.setValue(args[2]); w.setSingleStep(args[3]); w.setDecimals(args[4])
            else:
                w=QSpinBox(); w.setRange(args[0],args[1]); w.setValue(args[2])
            w.setFixedWidth(120); gas.addWidget(w,row,1)
            h=QLabel(hint_txt); h.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;"); gas.addWidget(h,row,2)
            self._skippy[key]=w
            if key == "target_ratio":
                w.valueChanged.connect(self._on_target_ratio_changed)
            else:
                w.valueChanged.connect(self._mark_custom)
        gas.setColumnStretch(2,1)

        self.skippy_preset.currentIndexChanged.connect(self._apply_skippy_preset)
        self._apply_skippy_preset(0)  # default to Auto on load
        main.addWidget(grp_as)

        grp_dtw = QGroupBox("DTW Video Compressor")
        gdtw = QGridLayout(grp_dtw); gdtw.setSpacing(8)
        dtw_params = [
            ("Target SR","target_sr",QSpinBox,(8000,48000,16000),""),
            ("N Mels","n_mels",QSpinBox,(16,256,64),""),
            ("Hop Length","hop",QSpinBox,(256,8192,2048),""),
            ("Time Decim","time_decim",QSpinBox,(1,8,2),""),
            ("Max Jump Ratio","max_jump",QDoubleSpinBox,(1.0,3.0,1.2,0.05,2),""),
        ]
        self._dtw = {}
        for row,(label,key,wtype,args,_) in enumerate(dtw_params):
            lbl=QLabel(label+":"); lbl.setObjectName("field_label"); gdtw.addWidget(lbl,row,0)
            if wtype==QDoubleSpinBox:
                w=QDoubleSpinBox(); w.setRange(args[0],args[1]); w.setValue(args[2]); w.setSingleStep(args[3]); w.setDecimals(args[4])
            else:
                w=QSpinBox(); w.setRange(args[0],args[1]); w.setValue(args[2])
            w.setFixedWidth(120); gdtw.addWidget(w,row,1); self._dtw[key]=w

        # Output FPS: dedicated dropdown with a "Detected" entry instead of
        # a generic spinbox, mirroring the Job tab so both stay in sync.
        fps_row = len(dtw_params)
        fps_lbl = QLabel("Output FPS:"); fps_lbl.setObjectName("field_label"); gdtw.addWidget(fps_lbl, fps_row, 0)
        self.out_fps = QComboBox()
        self.out_fps.addItems(["Detected (from source)","59.94","29.97","23.976","25","50","60"])
        self.out_fps.setCurrentIndex(0)
        self.out_fps.setFixedWidth(180)
        gdtw.addWidget(self.out_fps, fps_row, 1)
        self.detected_fps = None

        gdtw.setColumnStretch(2,1); main.addWidget(grp_dtw)
        main.addStretch()
        scroll.setWidget(inner); lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)

    def set_detected_fps(self, fps):
        """Called when a video is loaded in the Job tab, to keep this tab's
        FPS dropdown showing the same detected value."""
        self.detected_fps = fps
        if fps:
            self.out_fps.setItemText(0, f"Detected ({fps:.3f})")
        else:
            self.out_fps.setItemText(0, "Detected (from source)")

    def _resolve_fps(self):
        text = self.out_fps.currentText()
        if text.startswith("Detected"):
            fps = self.detected_fps if self.detected_fps else 59.94
            return fps
        return float(text.split()[0])

    def _mark_custom(self):
        # Auto=0, Light=1, Balanced=2, Heavy=3, Custom=4. Manual edits to any
        # slider always jump to Custom, same as before.
        if self.skippy_preset.currentIndex() != 4:
            self.skippy_preset.blockSignals(True)
            self.skippy_preset.setCurrentIndex(4)
            self.skippy_preset.blockSignals(False)

    def _on_target_ratio_changed(self, value):
        """Typing directly into Target Ratio behaves differently depending
        on the current mode: in Auto, it re-tunes every other parameter to
        match the new ratio live (this is the 'switch between target ratio
        and target duration' behavior -- both ultimately just drive the same
        ratio, Auto keeps the underlying parameters in sync with whichever
        one you're using). In any fixed preset or Custom, editing the ratio
        doesn't touch the other parameters and just marks Custom as usual."""
        if self.is_auto_mode():
            self.apply_auto_tuning(value)
        else:
            self._mark_custom()

    SKIPPY_PRESETS = {
        1: {"frame_ms": 20, "max_chop_ms": 25, "cadence_ms": 300, "crossfade_ms": 8,  "energy_q": 0.4},  # Light
        2: {"frame_ms": 15, "max_chop_ms": 35, "cadence_ms": 250, "crossfade_ms": 6,  "energy_q": 0.5},  # Balanced
        3: {"frame_ms": 10, "max_chop_ms": 45, "cadence_ms": 180, "crossfade_ms": 4,  "energy_q": 0.6},  # Heavy
    }

    # Anchor ratios the three fixed presets are calibrated around. Auto mode
    # uses these as control points for a continuous linear interpolation
    # across every skippy parameter, and EXTRAPOLATES past Light or Heavy
    # (rather than clamping to them) when the target ratio genuinely calls
    # for something gentler or more aggressive than either fixed preset --
    # this is what lets Auto "make up its own measurements" instead of just
    # snapping to the nearest bucket.
    AUTO_ANCHOR_RATIOS = [1.0075, 1.025, 1.05]   # Light, Balanced, Heavy
    AUTO_ANCHOR_VALUES = {
        "frame_ms":     [20, 15, 10],
        "max_chop_ms":  [25, 35, 45],
        "cadence_ms":   [300, 250, 180],
        "crossfade_ms": [8, 6, 4],
        "energy_q":     [0.4, 0.5, 0.6],
    }
    # Hard safety clamps so extrapolation at extreme ratios can never produce
    # a nonsensical value (zero/negative durations, energy quantile outside
    # 0-1, etc.) even though we deliberately allow going past the named
    # presets' own ranges.
    AUTO_CLAMPS = {
        "frame_ms":     (3, 30),
        "max_chop_ms":  (15, 70),
        "cadence_ms":   (80, 400),
        "crossfade_ms": (2, 12),
        "energy_q":     (0.2, 0.8),
    }

    @staticmethod
    def _lerp_extrap(x, x0, x1, y0, y1):
        if x1 == x0:
            return y0
        t = (x - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    def _compute_auto_params(self, ratio):
        """Continuous parameter tuning for a given target ratio. Interpolates
        between the Light/Balanced/Heavy anchor points, and linearly
        extrapolates beyond either end for ratios outside that range,
        clamped to safe bounds."""
        r0, r1, r2 = self.AUTO_ANCHOR_RATIOS
        result = {}
        for key, vals in self.AUTO_ANCHOR_VALUES.items():
            v0, v1, v2 = vals
            if ratio <= r1:
                v = self._lerp_extrap(ratio, r0, r1, v0, v1)
            else:
                v = self._lerp_extrap(ratio, r1, r2, v1, v2)
            lo, hi = self.AUTO_CLAMPS[key]
            result[key] = max(lo, min(hi, v))
        # Round to sensible precision per field (whole ms for most, 2dp for energy_q)
        for key in ("frame_ms", "max_chop_ms", "cadence_ms", "crossfade_ms"):
            result[key] = round(result[key])
        result["energy_q"] = round(result["energy_q"], 2)
        return result

    def apply_auto_tuning(self, ratio):
        """Called by the JobRunner (via the main window) whenever Auto mode
        is active and a target ratio is known -- either typed directly into
        Target Ratio, or computed from a Target Length. Tunes every skippy
        parameter continuously rather than snapping to Light/Balanced/Heavy."""
        params = self._compute_auto_params(ratio)
        for key, val in params.items():
            w = self._skippy.get(key)
            if w:
                w.blockSignals(True)
                w.setValue(val)
                w.blockSignals(False)

    def is_auto_mode(self):
        return self.skippy_preset.currentIndex() == 0

    def _apply_skippy_preset(self, idx):
        if idx == 0:
            # Auto selected: immediately tune based on whatever ratio is
            # currently in the Target Ratio box, rather than leaving
            # whatever values were there from a previous mode.
            self.apply_auto_tuning(self._skippy["target_ratio"].value())
            return
        if idx not in self.SKIPPY_PRESETS:
            return  # Custom — leave values as-is
        vals = self.SKIPPY_PRESETS[idx]
        for key, val in vals.items():
            w = self._skippy.get(key)
            if w:
                w.blockSignals(True)
                w.setValue(val)
                w.blockSignals(False)

    HEAVY_CEILING_WARNING = 1.06   # heads-up only -- past this point even
                                     # aggressive chopping may start to sound
                                     # noticeable, but we still attempt it.
    EXTREME_WARNING       = 1.15   # stronger heads-up: likely to undershoot
                                     # or sound rough, but no longer blocked --
                                     # Auto mode will extrapolate as far as it
                                     # can and let the result speak for itself.

    def apply_target_ratio(self, ratio):
        """Called by the JobRunner when Target Length is enabled: sets the
        Target Ratio spinbox to the computed value. If Auto mode is active,
        continuously tunes every skippy parameter to match (extrapolating
        past Light/Balanced/Heavy as needed); if a fixed preset or Custom is
        selected, leaves those parameters alone and just sets the ratio.
        Returns (warning_text_or_None, is_blocking) -- is_blocking is always
        False now; nothing is ever hard-blocked, only warned about."""
        self._skippy["target_ratio"].blockSignals(True)
        self._skippy["target_ratio"].setValue(ratio)
        self._skippy["target_ratio"].blockSignals(False)

        if self.is_auto_mode():
            self.apply_auto_tuning(ratio)

        if ratio >= self.EXTREME_WARNING:
            pct = (ratio - 1) * 100
            return (
                f"This target requires removing {pct:.0f}% of the runtime. "
                f"Auto mode will tune as aggressively as it safely can, but "
                f"most content doesn't contain enough true silence to hit "
                f"targets this steep cleanly -- expect possible undershoot "
                f"or audible chops. Consider a less aggressive target if the "
                f"result doesn't sound right.",
                False,
            )
        if ratio >= self.HEAVY_CEILING_WARNING:
            return (
                f"Target requires a {((ratio-1)*100):.1f}% time reduction — "
                f"this is past where the Heavy preset is calibrated. Auto mode "
                f"will tune more aggressively than Heavy to compensate.",
                False,
            )
        return None, False

    def get_params(self):
        params = {k:w.value() for k,w in {**self._skippy,**self._dtw}.items()}
        params["out_fps"] = self._resolve_fps()
        params["skippy_mode"] = self.skippy_preset.currentText()
        return params

# ── FRAME BLEND TAB ───────────────────────────
class FrameBlendTab(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self); main.setSpacing(14); main.setContentsMargins(16,16,16,16)
        main.addWidget(section_header("Frame Blending / Smear Settings"))

        grp = QGroupBox("Blend Engine")
        g = QVBoxLayout(grp); g.setSpacing(10)
        self.blend_enable = QCheckBox("Enable Frame Blending"); self.blend_enable.setChecked(True)
        g.addWidget(self.blend_enable); g.addWidget(divider())
        main.addWidget(grp)

        def slider_row(label, mn, mx, val, scale=1, decimals=0):
            row = QHBoxLayout()
            lbl = QLabel(label+":"); lbl.setObjectName("field_label"); lbl.setFixedWidth(160); row.addWidget(lbl)
            sl = QSlider(Qt.Horizontal); sl.setRange(int(mn*scale),int(mx*scale)); sl.setValue(int(val*scale)); row.addWidget(sl,1)
            disp = QLabel(f"{val}" if decimals==0 else f"{val:.{decimals}f}")
            disp.setFixedWidth(60); disp.setStyleSheet(f"color:{ACCENT_GREEN};font-family:'{MONO_FONT}';font-size:12px;")
            sl.valueChanged.connect(lambda v,d=disp,sc=scale,dec=decimals: d.setText(f"{v/sc}" if dec==0 else f"{v/sc:.{dec}f}"))
            row.addWidget(disp); return row, sl

        grp2 = QGroupBox("Blend Amount")
        g2 = QVBoxLayout(grp2); g2.setSpacing(8)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Preset:"))
        self.blend_mode = QComboBox()
        self.blend_mode.addItems([
            "Full blending",
            "Medium",
            "Light (recommended)",
            "None (hard cuts)",
        ])
        self.blend_mode.setCurrentText("Light (recommended)")
        self.blend_mode.setFixedWidth(300)
        mode_row.addWidget(self.blend_mode); mode_row.addStretch(); g2.addLayout(mode_row)

        r2, self.sl_blend_alpha = slider_row("Blend Width", 0, 1, 0.33, scale=100, decimals=2)
        g2.addLayout(r2)

        desc = QLabel(
            "Controls how much of each cut transition actually blends between the "
            "frame before and after it, versus snapping cleanly. The transition itself "
            "always starts exactly on the first frame and ends exactly on the second -- "
            "this only changes how gradual the middle of it is. Full = smoothest "
            "(Premiere-style continuous blend); None = a hard cut with no blending at all. "
            "Use the slider for finer control than the presets, or pick a preset to jump "
            "straight to a common value."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;padding:6px;background:{BG_PANEL};border:1px solid {BORDER};border-radius:3px;")
        desc.setTextFormat(Qt.RichText)
        g2.addWidget(desc)
        main.addWidget(grp2)
        main.addStretch()

        self.blend_mode.currentIndexChanged.connect(self._on_mode_changed)

    BLEND_PRESET_WIDTHS = {
        "Full blending": 100,
        "Medium": 66,
        "Light (recommended)": 33,
        "None (hard cuts)": 0,
    }

    def _on_mode_changed(self, index):
        preset_text = self.blend_mode.currentText()
        width = self.BLEND_PRESET_WIDTHS.get(preset_text)
        if width is not None:
            self.sl_blend_alpha.blockSignals(True)
            self.sl_blend_alpha.setValue(width)
            self.sl_blend_alpha.blockSignals(False)

    def get_params(self):
        return {
            "blend_enable": self.blend_enable.isChecked(),
            "blend_width":  self.sl_blend_alpha.value()/100.0,
        }

# ── EDITOR TAB ────────────────────────────────
class EditorTab(QWidget):
    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self); outer.setSpacing(0); outer.setContentsMargins(0,0,0,0)

        # ── Fixed top section: header + player (always visible, never crammed) ──
        top = QWidget()
        top_lay = QVBoxLayout(top); top_lay.setSpacing(8); top_lay.setContentsMargins(16,16,16,8)
        top_lay.addWidget(section_header("Pre-Compression Editor"))

        self.player = VideoPlayer(label="")
        self.player.setMinimumHeight(280)
        self.player.setMaximumHeight(420)
        top_lay.addWidget(self.player)

        if not CV2_OK:
            warn = QLabel("pip install opencv-python  to enable preview")
            warn.setStyleSheet(f"color:{ACCENT_GOLD};font-size:11px;")
            top_lay.addWidget(warn)

        outer.addWidget(top)

        # ── Scrollable bottom section: Trim / Color / Audio side-by-side ──
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        main = QHBoxLayout(inner); main.setSpacing(14); main.setContentsMargins(16,8,16,16)

        # COLUMN 1: Trim
        grp_trim = QGroupBox("Trim / Cut")
        gt = QVBoxLayout(grp_trim); gt.setSpacing(10)
        self.trim_in  = QLineEdit("00:00:00:00"); self.trim_in.setFixedWidth(110)
        self.trim_out = QLineEdit("00:00:00:00"); self.trim_out.setFixedWidth(110)

        in_row = QVBoxLayout(); in_row.setSpacing(4)
        in_lbl_row = QHBoxLayout()
        in_lbl_row.addWidget(QLabel("In Point:")); in_lbl_row.addWidget(self.trim_in); in_lbl_row.addStretch()
        in_row.addLayout(in_lbl_row)
        btn_in = QPushButton("Set In at Playhead")
        btn_in.clicked.connect(lambda: self.trim_in.setText(self._tc_str(self.player.get_pos())))
        in_row.addWidget(btn_in)
        gt.addLayout(in_row)
        gt.addWidget(divider())

        out_row = QVBoxLayout(); out_row.setSpacing(4)
        out_lbl_row = QHBoxLayout()
        out_lbl_row.addWidget(QLabel("Out Point:")); out_lbl_row.addWidget(self.trim_out); out_lbl_row.addStretch()
        out_row.addLayout(out_lbl_row)
        btn_out = QPushButton("Set Out at Playhead")
        btn_out.clicked.connect(lambda: self.trim_out.setText(self._tc_str(self.player.get_pos())))
        out_row.addWidget(btn_out)
        gt.addLayout(out_row)
        gt.addStretch()
        main.addWidget(grp_trim, 1)

        # COLUMN 2: Color
        grp_col = QGroupBox("Color / Brightness")
        gc = QVBoxLayout(grp_col); gc.setSpacing(10)
        self._color_sliders = {}
        for label, key, default in [("Brightness","brightness",0),("Contrast","contrast",0),("Saturation","saturation",0),("Gamma","gamma",0)]:
            lbl_row = QHBoxLayout()
            lbl=QLabel(label+":"); lbl.setObjectName("field_label"); lbl_row.addWidget(lbl)
            lbl_row.addStretch()
            val=QLabel(str(default)); val.setStyleSheet(f"color:{ACCENT_GREEN};font-family:'{MONO_FONT}';")
            lbl_row.addWidget(val)
            gc.addLayout(lbl_row)
            sl_row = QHBoxLayout()
            sl=QSlider(Qt.Horizontal); sl.setRange(-100,100); sl.setValue(default)
            sl.valueChanged.connect(lambda v,d=val: d.setText(str(v)))
            sl_row.addWidget(sl,1)
            rst=QPushButton("Reset"); rst.setFixedWidth(54); rst.clicked.connect(lambda _,s=sl,dv=default: s.setValue(dv))
            sl_row.addWidget(rst)
            gc.addLayout(sl_row)
            self._color_sliders[key]=sl
        gc.addStretch()
        main.addWidget(grp_col, 1)

        # COLUMN 3: Audio
        grp_aud = QGroupBox("Audio Level")
        ga = QVBoxLayout(grp_aud); ga.setSpacing(10)
        gain_lbl_row = QHBoxLayout()
        gain_lbl_row.addWidget(QLabel("Master Gain:"))
        gain_lbl_row.addStretch()
        self.lbl_gain = QLabel("0 dB"); self.lbl_gain.setStyleSheet(f"color:{ACCENT_GREEN};font-family:'{MONO_FONT}';")
        gain_lbl_row.addWidget(self.lbl_gain)
        ga.addLayout(gain_lbl_row)
        self.sl_gain = QSlider(Qt.Horizontal); self.sl_gain.setRange(-24,24); self.sl_gain.setValue(0)
        self.sl_gain.valueChanged.connect(lambda v: self.lbl_gain.setText(f"{v:+d} dB"))
        ga.addWidget(self.sl_gain)
        ga.addWidget(divider())
        self.chk_normalize = QCheckBox("Normalize to -23 LUFS (EBU R128)")
        self.chk_limiter   = QCheckBox("True peak limiter (-1 dBTP)")
        ga.addWidget(self.chk_normalize)
        ga.addWidget(self.chk_limiter)
        ga.addStretch()
        main.addWidget(grp_aud, 1)

        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

    def _tc_str(self, t):
        m,s = int(t//60), int(t%60)
        f = int((t%1)*30)
        return f"{m:02d}:{s:02d}:{f:02d}"

    def load_video(self, path): self.player.load(path)

    def get_params(self):
        return {
            "trim_in":    self.trim_in.text(),
            "trim_out":   self.trim_out.text(),
            "brightness": self._color_sliders["brightness"].value(),
            "contrast":   self._color_sliders["contrast"].value(),
            "saturation": self._color_sliders["saturation"].value(),
            "gamma":      self._color_sliders["gamma"].value(),
            "gain_db":    self.sl_gain.value(),
            "normalize":  self.chk_normalize.isChecked(),
            "limiter":    self.chk_limiter.isChecked(),
        }

# ── PREVIEW TAB ───────────────────────────────
class PreviewTab(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self); main.setSpacing(10); main.setContentsMargins(16,16,16,16)
        main.addWidget(section_header("A/B Preview — Original vs Compressed"))

        split = QHBoxLayout()
        self.pv_before = VideoPlayer(label="ORIGINAL")
        self.pv_after  = VideoPlayer(label="COMPRESSED")
        split.addWidget(self.pv_before,1); split.addWidget(self.pv_after,1)
        main.addLayout(split,1)

        linked_row = QHBoxLayout()
        self.chk_linked = QCheckBox("Linked scrub (A/B sync)"); self.chk_linked.setChecked(True)
        linked_row.addWidget(self.chk_linked); linked_row.addStretch()
        main.addLayout(linked_row)

        # stats
        stats = QHBoxLayout()
        self._stat_labels = {}
        for key, label, color in [("orig_dur","Original Duration",TEXT_PRIMARY),("comp_dur","Compressed Duration",ACCENT_GREEN),("saved","Time Saved",ACCENT_GOLD),("pct","Compression %",ACCENT_BLUE)]:
            box = QVBoxLayout()
            l1=QLabel(label); l1.setStyleSheet(f"color:{TEXT_MUTED};font-size:10px;letter-spacing:1px;")
            l2=QLabel("—"); l2.setStyleSheet(f"color:{color};font-family:'{MONO_FONT}';font-size:15px;font-weight:700;")
            box.addWidget(l1); box.addWidget(l2); stats.addLayout(box); stats.addSpacing(24)
            self._stat_labels[key]=l2
        stats.addStretch(); main.addLayout(stats)

        self.pv_before.position_changed.connect(self._on_before_move)

    def _on_before_move(self, t):
        if self.chk_linked.isChecked():
            # sync after player if loaded
            dur = self.pv_after.get_dur()
            if dur > 0:
                ratio = t / max(self.pv_before.get_dur(), 1)
                self.pv_after._show_frame(ratio * dur)

    def load_original(self, path):
        self.pv_before.load(path)
        dur = self.pv_before.get_dur()
        m,s = int(dur//60), int(dur%60)
        self._stat_labels["orig_dur"].setText(f"{m:02d}:{s:02d}:{int((dur%1)*30):02d}")

    def load_compressed(self, path):
        self.pv_after.load(path)
        comp = self.pv_after.get_dur()
        orig = self.pv_before.get_dur()
        mc,sc = int(comp//60), int(comp%60)
        self._stat_labels["comp_dur"].setText(f"{mc:02d}:{sc:02d}:{int((comp%1)*30):02d}")
        saved = orig - comp
        ms,ss = int(saved//60), int(saved%60)
        self._stat_labels["saved"].setText(f"{ms:02d}:{ss:02d}:{int((saved%1)*30):02d}")
        if orig > 0:
            self._stat_labels["pct"].setText(f"{(saved/orig*100):.2f}%")

# ── LOG TAB ───────────────────────────────────
class LogTab(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self); main.setSpacing(10); main.setContentsMargins(16,16,16,16)
        main.addWidget(section_header("Job Progress"))

        grp = QGroupBox("Pipeline Steps")
        g = QVBoxLayout(grp); g.setSpacing(8)
        self.bars = {}
        for label, key in [("Audio Extract","extract"),("Audio Skippy","audio_skippy"),("DTW Analysis","dtw"),("Frame Rendering","render"),("Audio Mux","mux"),("Subtitle Retime","subs")]:
            row = QHBoxLayout()
            lbl=QLabel(label+":"); lbl.setFixedWidth(140); lbl.setObjectName("field_label"); row.addWidget(lbl)
            bar=QProgressBar(); bar.setValue(0); bar.setFixedHeight(18); row.addWidget(bar,1)
            status=QLabel("Waiting"); status.setFixedWidth(80); status.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;"); row.addWidget(status)
            g.addLayout(row); self.bars[key]=(bar,status)
        main.addWidget(grp)

        overall_row = QHBoxLayout()
        overall_row.addWidget(QLabel("Overall:"))
        self.overall_bar = QProgressBar(); self.overall_bar.setValue(0); overall_row.addWidget(self.overall_bar,1)
        self.overall_label = QLabel("Idle"); self.overall_label.setStyleSheet(f"color:{ACCENT_GREEN};font-weight:700;"); overall_row.addWidget(self.overall_label)
        main.addLayout(overall_row)
        main.addWidget(divider())
        main.addWidget(section_header("Console Output"))

        self.log = QTextEdit(); self.log.setReadOnly(True)
        self.log.setFont(QFont(MONO_FONT,10))
        self.log.setStyleSheet(f"background:{BG_FIELD};color:{TEXT_PRIMARY};border:1px solid {BORDER};")
        self.log.setMinimumHeight(180); main.addWidget(self.log,1)

        btn_row = QHBoxLayout()
        self.btn_clear_log = QPushButton("Clear Log"); self.btn_clear_log.clicked.connect(self.log.clear)
        btn_row.addWidget(self.btn_clear_log); btn_row.addStretch(); main.addLayout(btn_row)

    def append(self, text, color=None):
        if color: self.log.append(f'<span style="color:{color}">{text}</span>')
        else: self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def set_step(self, key, pct, status_text, color=None):
        if key in self.bars:
            bar, lbl = self.bars[key]; bar.setValue(pct); lbl.setText(status_text)
            if color: lbl.setStyleSheet(f"color:{color};font-size:11px;font-weight:600;")

    def set_overall(self, pct, text):
        self.overall_bar.setValue(pct); self.overall_label.setText(text)

# ── JOB RUNNER ────────────────────────────────
class JobRunner(QThread):
    log_signal     = pyqtSignal(str, str)
    step_signal    = pyqtSignal(str, int, str, str)
    overall_signal = pyqtSignal(int, str)
    done_signal    = pyqtSignal(bool, str)

    def __init__(self, job_params, comp_params, blend_params, edit_params, script_dir):
        super().__init__()
        self.job=job_params; self.comp=comp_params; self.blend=blend_params
        self.edit=edit_params; self.script_dir=script_dir
        self.python_exe = self._find_python_interpreter()
        # ── Cancellation state ──
        # _current_proc tracks whichever subprocess is presently running so
        # request_stop() (called from the main/GUI thread) can terminate it
        # directly, rather than just setting a flag and hoping the worker
        # notices. Killing the process is what actually unblocks the
        # `for line in proc.stdout` read loop in _run() -- closing stdout is
        # what ends that loop, not the flag by itself.
        self._current_proc = None
        self._stop_requested = False

    def request_stop(self):
        """Called from the GUI thread when the user clicks Stop. Safe to
        call even if no subprocess is currently active (e.g. between
        pipeline steps) -- the flag alone causes the next step to bail
        before it starts."""
        self._stop_requested = True
        proc = self._current_proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def _find_embedded_python(self):
        """
        Looks for a bundled, portable copy of a real Python install at
        <install_dir>/embedded_python/python.exe. If present, this is used
        directly as a genuine external interpreter -- sidestepping
        PyInstaller's frozen-import path entirely for the companion
        scripts, since that path is what's actually been buggy (the
        scipy.stats NameError), not the packages themselves. A real,
        unmodified CPython interpreter running these scripts has worked
        reliably every time we've tested it (that's exactly what the
        system-Python fallback already proved) -- this just makes that
        same reliable path available without depending on the end user
        already having a working Python installed at all.
        """
        candidate = os.path.join(_bundled_bin_dir(), "embedded_python", "python.exe")
        return candidate if os.path.exists(candidate) else None

    def _find_python_interpreter(self):
        """
        Resolution order:
          1. From source: sys.executable IS the right Python, as always.
          2. Frozen + a bundled embedded_python/ is present: use that --
             a real interpreter, not PyInstaller's frozen-import path.
          3. Frozen, no embedded Python bundled: fall back to self-hosting
             via `TempoCut.exe --run-script ...` (see _build_script_cmd).
        Also sets self._using_embedded_python so _build_script_cmd knows
        whether to add the --run-script prefix or just run directly.
        """
        self._using_embedded_python = False
        if not getattr(sys, "frozen", False):
            return sys.executable

        embedded = self._find_embedded_python()
        if embedded:
            self._using_embedded_python = True
            return embedded

        return sys.executable

    def _find_system_python_fallback(self):
        """
        Safety net only -- NOT the primary path anymore. If self-hosting
        a companion script fails (e.g. the scipy/PyInstaller frozen-import
        bug some machines hit when loading scipy.stats), we retry once
        using a real system Python instead of just failing the job. This
        is the same search _find_python_interpreter used to do by default
        before self-hosting existed; it's kept around purely as a backup.
        Returns None if nothing usable is found (caller handles that).
        """
        import shutil
        for candidate in ("python", "python3", "py"):
            found = shutil.which(candidate)
            if found:
                return found
        import glob
        patterns = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python3*\python.exe"),
            r"C:\Python3*\python.exe",
            r"C:\Program Files\Python3*\python.exe",
        ]
        for pattern in patterns:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        return None

    def _stage_script_neutral(self, script_path):
        """
        Copy a companion script into a neutral temp folder before running
        it with a real external interpreter (embedded_python OR a system
        Python fallback). Necessary because the script's original location
        (inside _internal/ when frozen) ALSO contains the main app's own
        bundled copies of scipy/numpy/etc -- Python automatically puts a
        script's own folder first on sys.path, so running it in-place
        would silently import those bundled (frozen-targeted, possibly
        broken) packages instead of whichever interpreter's real
        site-packages we actually intended to use, defeating the entire
        point of using a separate interpreter at all. Returns the path to
        the staged copy, or None if staging failed (caller should treat
        that as a hard failure rather than silently using the original,
        unsafe path).
        """
        try:
            neutral_dir = tempfile.mkdtemp(prefix="tempocut_run_")
            neutral_script = os.path.join(neutral_dir, os.path.basename(script_path))
            import shutil as _shutil
            _shutil.copy2(script_path, neutral_script)
            return neutral_script
        except Exception as ex:
            self.log_signal.emit(f"[!] Could not stage a clean script copy: {ex}", ACCENT_RED)
            return None

    def _build_script_cmd(self, script_path, args):
        """
        Build the subprocess command list for running one of the
        companion scripts (audio_skippy_SURROUND.py, time_compressor_SAFE_v2.py,
        subtitle_retime.py), using whichever mode is appropriate:
          - From source: [python, script.py, *args]  (normal run, no
                staging needed -- nothing frozen, no competing bundled
                packages sitting next to the script)
          - Frozen + embedded Python available: [embedded_python, staged
                copy of script.py, *args]  -- staged to a neutral temp
                folder so it can't accidentally pick up the main app's
                OWN bundled (possibly broken) scipy/numpy sitting in
                _internal/ right next to the original script.
          - Frozen, no embedded Python: [TempoCut.exe, --run-script,
                script.py, *args]  (self-host, runs in-process -- no
                separate interpreter, so no sys.path collision to worry
                about here)
        """
        if not getattr(sys, "frozen", False):
            return [self.python_exe, "-u", script_path, *args]

        if self._using_embedded_python:
            staged = self._stage_script_neutral(script_path)
            if staged is None:
                # Staging failed -- fall back to self-hosting rather than
                # risking the known sys.path collision by running in-place.
                return [sys.executable, "--run-script", script_path, *args]
            return [self.python_exe, "-u", staged, *args]

        return [self.python_exe, "--run-script", script_path, *args]

    def _run_script_with_fallback(self, script_path, args, step_name):
        """
        Run a companion script self-hosted first. If that fails (any
        non-zero exit, not a cancellation), automatically retry once using
        a real system Python before giving up -- this is the safety net
        for the scipy/PyInstaller frozen-import bug some machines hit.
        Logs clearly which path actually succeeded, so it's obvious from
        the console output whether self-hosting is really working on a
        given machine or quietly falling back every time.
        """
        primary_cmd = self._build_script_cmd(script_path, args)
        ret = self._run(primary_cmd)
        if self._stop_requested or ret == 0:
            return ret

        if not getattr(sys, "frozen", False):
            return ret  # not self-hosted in the first place, nothing to fall back from

        self.log_signal.emit(
            f"[!] Self-hosted run of {os.path.basename(script_path)} failed -- "
            f"trying a system Python as a fallback...", ACCENT_GOLD
        )
        fallback_python = self._find_system_python_fallback()
        if not fallback_python:
            self.log_signal.emit(
                "[!] No system Python found on this machine either -- cannot fall back.",
                ACCENT_RED
            )
            return ret

        neutral_script = self._stage_script_neutral(script_path)
        if neutral_script is None:
            return ret

        fallback_cmd = [fallback_python, "-u", neutral_script, *args]
        ret2 = self._run(fallback_cmd)
        if ret2 == 0:
            self.log_signal.emit(
                f"[*] Fallback succeeded via system Python ({fallback_python}). "
                f"NOTE: that Python needs numpy/librosa/opencv-python/soundfile/"
                f"pysubs2 installed for this to keep working.", ACCENT_GOLD
            )
        return ret2

    def run(self):
        try:
            self._check_ffmpeg_available()
            self._run_pipeline()
        except Exception as ex:
            self.log_signal.emit(f"FATAL: {ex}", ACCENT_RED)
            self.done_signal.emit(False, str(ex))

    def _check_ffmpeg_available(self):
        """
        Confirm ffmpeg/ffprobe can actually be found (bundled next to the
        exe, or on system PATH) before the job starts, instead of letting
        the failure surface deep inside step 0 as an opaque [WinError 2].
        find_binary() raises a clear, actionable RuntimeError if neither
        is found; that's exactly what we want here.
        """
        find_binary("ffmpeg")
        find_binary("ffprobe")

    def _detect_source_audio(self, video_path):
        """Use ffprobe to read the original audio stream's codec, bitrate,
        sample rate, and channel count so we can re-encode the time-
        compressed audio back to match it exactly."""
        try:
            cmd = [
                find_binary("ffprobe"), "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,bit_rate,sample_rate,channels",
                "-of", "default=noprint_wrappers=1:nokey=0",
                video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            info = {}
            for line in result.stdout.strip().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k.strip()] = v.strip()
            return info
        except Exception as ex:
            self.log_signal.emit(f"[!] ffprobe audio detection failed: {ex}", ACCENT_GOLD)
            return {}

    # Maps ffprobe codec_name -> ffmpeg encoder name (a few codecs need translation)
    CODEC_NAME_TO_ENCODER = {
        "aac": "aac",
        "ac3": "ac3",
        "eac3": "eac3",
        "mp3": "libmp3lame",
        "pcm_s16le": "pcm_s16le",
        "pcm_s24le": "pcm_s24le",
        "flac": "flac",
        "vorbis": "libvorbis",
        "opus": "libopus",
        "dts": "ac3",   # no free DTS encoder in standard ffmpeg builds; fall back to AC3
        "truehd": "ac3",
    }

    def _build_audio_args(self, codec_a, source_info):
        """Returns the ffmpeg -c:a / -b:a / -ar / -ac args for the mux step."""
        if codec_a == "match_source" and source_info.get("codec_name"):
            codec_name = source_info["codec_name"]
            encoder = self.CODEC_NAME_TO_ENCODER.get(codec_name, "aac")
            args = ["-c:a", encoder]

            bit_rate = source_info.get("bit_rate")
            channels_for_floor = source_info.get("channels")
            channels_for_floor = int(channels_for_floor) if channels_for_floor and channels_for_floor.isdigit() else 2
            # This pipeline necessarily decodes the original lossy audio to
            # raw PCM (for the skippy edit) and re-encodes it once more --
            # a second lossy pass. Matching the source's exact original
            # bitrate doesn't account for that: a tight original bitrate
            # (e.g. 192k for 5.1, ~32kbps/channel) compounds noticeably
            # audible artifacts on the second pass even though the spec
            # matches exactly. Floor at a reasonable ~80kbps/channel for
            # lossy codecs so the re-encode has enough headroom to not
            # visibly stack on top of the original's own compression.
            min_floor_kbps = 80 * channels_for_floor if encoder not in ("pcm_s16le", "pcm_s24le", "flac") else 0
            if bit_rate and bit_rate.isdigit() and encoder not in ("pcm_s16le", "pcm_s24le", "flac"):
                kbps = max(1, int(bit_rate) // 1000, min_floor_kbps)
                args += ["-b:a", f"{kbps}k"]
            elif encoder not in ("pcm_s16le", "pcm_s24le", "flac"):
                args += ["-b:a", f"{max(640, min_floor_kbps)}k"]  # sensible broadcast default if source bitrate unknown

            sample_rate = source_info.get("sample_rate")
            if sample_rate and sample_rate.isdigit():
                args += ["-ar", sample_rate]

            channels = source_info.get("channels")
            if channels and channels.isdigit():
                args += ["-ac", channels]

            self.log_signal.emit(
                f"[*] Match Source: detected {codec_name} -> encoding as {encoder} "
                f"({args})", ACCENT_BLUE
            )
            return args

        # Manual codec selection fallback
        manual_map = {
            "aac":  ["-c:a", "aac",  "-b:a", "640k"],
            "pcm":  ["-c:a", "pcm_s24le"],
            "ac3":  ["-c:a", "ac3",  "-b:a", "640k"],
            "eac3": ["-c:a", "eac3", "-b:a", "640k"],
        }
        return manual_map.get(codec_a, ["-c:a", "aac", "-b:a", "640k"])

    def _cleanup_intermediates(self, raw_wav, skippy_wav, temp_vid):
        """Best-effort removal of scratch files. Shared by the normal
        completion path and the cancellation path so a stopped job doesn't
        leave half-finished WAVs/MP4s lying around either."""
        marker_file = raw_wav.rsplit(".", 1)[0] + "_markers.txt"
        cutlist_file = raw_wav.rsplit(".", 1)[0] + "_cutlist.csv"
        pulldown_guess = raw_wav.replace("_raw_audio.wav", "_pulldown2997.mp4")
        map_file = os.path.join(os.path.dirname(raw_wav), "map_t_skip_to_t_orig.npy")
        for f in [temp_vid, raw_wav, skippy_wav, marker_file, cutlist_file, pulldown_guess, map_file]:
            try: os.remove(f)
            except: pass

    def _check_cancelled(self, step_key, raw_wav, skippy_wav, temp_vid):
        """Call right after a pipeline step's _run() returns. If Stop was
        clicked (during that step or between steps), marks the current
        step as Cancelled rather than Failed, cleans up scratch files, and
        emits done_signal so the GUI re-enables Create Job. Returns True if
        the caller should stop running the rest of the pipeline."""
        if not self._stop_requested:
            return False
        self.step_signal.emit(step_key, 100, "Cancelled", ACCENT_GOLD)
        self._cleanup_intermediates(raw_wav, skippy_wav, temp_vid)
        self.overall_signal.emit(0, "Cancelled")
        self.done_signal.emit(False, "Job cancelled by user")
        return True

    def _run_pipeline(self):
        j=self.job; c=self.comp
        out_dir   = j["output_path"]
        out_name  = j["output_name"]
        out_video = os.path.join(out_dir, out_name + "_tc.mp4")
        raw_wav   = os.path.join(out_dir, out_name + "_raw_audio.wav")
        skippy_wav= os.path.join(out_dir, out_name + "_heavy.wav")
        temp_vid  = os.path.join(out_dir, out_name + "_temp.mp4")
        pulldown_vid = os.path.join(out_dir, out_name + "_pulldown2997.mp4")

        # ── Pulldown preprocessing ──
        # If the true source is ~23.976 and the user wants 29.97 output,
        # convert the RAW source to 29.97 via real frame duplication FIRST
        # -- before DTW/audio-skippy ever touch the footage. The renderer
        # then treats this pulldown'd file as its actual source (matching
        # native rate == output rate), so any blending it does reflects
        # ONLY genuine time-compression warp, never a rate-mismatch
        # interpolation artifact. No synthesized pixel content gets added
        # at this step at all -- it's the same plain frame duplication
        # ffmpeg's -r does by default during a real encode.
        true_source_fps = j.get("detected_fps")
        wants_2997 = abs(c.get("out_fps", j.get("fps", 59.94)) - 29.97) < 0.05
        dtw_input_video = j["input_video"]
        dtw_render_fps = c.get("out_fps", j.get("fps", 59.94))
        if true_source_fps and abs(true_source_fps - 23.976) < 0.05 and wants_2997:
            self.step_signal.emit("extract", 0, "Pulldown 23.976→29.97…", ACCENT_GOLD)
            self.overall_signal.emit(2, "Converting to 29.97 (pulldown)…")
            video_codec_args = {
                "libx264": ["-c:v", "libx264", "-preset", "slow", "-crf", "16"],
                "libx265": ["-c:v", "libx265", "-preset", "slow", "-crf", "18"],
                "prores_ks": ["-c:v", "prores_ks", "-profile:v", "3"],
                "dnxhd": ["-c:v", "dnxhd", "-profile:v", "dnxhr_hq"],
            }.get(j.get("codec_v", "libx264"), ["-c:v", "libx264", "-preset", "slow", "-crf", "16"])
            cmd_pulldown = [
                find_binary("ffmpeg"), "-y", "-i", j["input_video"],
                *video_codec_args, "-r", "29.97", "-c:a", "copy",
                pulldown_vid
            ]
            ret = self._run(cmd_pulldown)
            if self._check_cancelled("extract", raw_wav, skippy_wav, temp_vid): return
            if ret != 0:
                self.step_signal.emit("extract", 100, "FAILED", ACCENT_RED)
                self.done_signal.emit(False, "Pulldown conversion failed"); return
            dtw_input_video = pulldown_vid
            dtw_render_fps = 29.97  # matches the pulldown file's new native rate

        # STEP 0: Extract audio from video
        self.step_signal.emit("extract", 0, "Running…", ACCENT_GOLD)
        self.overall_signal.emit(5, "Extracting audio…")
        cmd_extract = [
            find_binary("ffmpeg"), "-y", "-i", j["input_video"],
            "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "6",
            raw_wav
        ]
        # fallback to stereo if 6ch fails
        ret = self._run(cmd_extract)
        if self._check_cancelled("extract", raw_wav, skippy_wav, temp_vid): return
        if ret != 0:
            self.log_signal.emit("[!] 6-channel extract failed, trying stereo…", ACCENT_GOLD)
            cmd_extract[-2] = "2"
            ret = self._run(cmd_extract)
            if self._check_cancelled("extract", raw_wav, skippy_wav, temp_vid): return
        if ret != 0:
            self.step_signal.emit("extract", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "Audio extraction failed"); return
        self.step_signal.emit("extract", 100, "Done", ACCENT_GREEN)
        self.overall_signal.emit(12, "Audio compression…")

        # STEP 1: Audio Skippy
        self.step_signal.emit("audio_skippy", 0, "Running…", ACCENT_GOLD)
        audio_skippy_script = os.path.join(self.script_dir, "audio_skippy_SURROUND.py")
        cutlist_path = raw_wav.rsplit(".", 1)[0] + "_cutlist.csv"
        ret = self._run_script_with_fallback(audio_skippy_script, [
            "-i", raw_wav, "-o", skippy_wav,
            "--target-ratio", str(c["target_ratio"]),
            "--frame-ms",     str(int(c["frame_ms"])),
            "--max-chop-ms",  str(int(c["max_chop_ms"])),
            "--cadence-ms",   str(int(c["cadence_ms"])),
            "--crossfade-ms", str(int(c["crossfade_ms"])),
            "--energy-quantile", str(c["energy_q"]),
            "--video", dtw_input_video,  # enables joint audio+video redundancy
                                          # detection -- cuts only land where
                                          # BOTH audio is quiet AND video is
                                          # visually static, not audio alone
        ], "audio_skippy")
        if self._check_cancelled("audio_skippy", raw_wav, skippy_wav, temp_vid): return
        if ret != 0:
            self.step_signal.emit("audio_skippy", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "audio_skippy failed"); return
        self.step_signal.emit("audio_skippy", 100, "Done", ACCENT_GREEN)
        self.overall_signal.emit(30, "Video cutting…")

        # STEP 2: Cut-list video compressor (replaces the old DTW renderer).
        # Reads the EXACT removal windows audio_skippy already computed and
        # cuts matching video at the same points -- no DTW re-discovery, no
        # continuous retiming curve, no drift/jitter/catch-up category of
        # bugs at all. Blend/output-fps settings from the Frame Blend tab
        # no longer apply here: blending is the exact subframe formula at
        # real cut points only, and output rate is always native (any fps
        # conversion happens via the pulldown preprocessing step above,
        # which dtw_input_video already reflects).
        self.step_signal.emit("dtw", 0, "Running…", ACCENT_GOLD)
        self.step_signal.emit("render", 0, "Queued…", TEXT_MUTED)
        tc_script = os.path.join(self.script_dir, "time_compressor_CUTLIST.py")
        b = self.blend
        effective_blend_width = b.get("blend_width", 1.0) if b.get("blend_enable", True) else 0.0
        ret = self._run_script_with_fallback(tc_script, [
            "-i", dtw_input_video, "--cutlist", cutlist_path, "-o", temp_vid,
            "--blend-width", str(effective_blend_width),
        ], "dtw")
        if self._check_cancelled("dtw", raw_wav, skippy_wav, temp_vid): return
        if ret != 0:
            self.step_signal.emit("dtw", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "Video cutter failed"); return
        self.step_signal.emit("dtw",    100, "Done", ACCENT_GREEN)
        self.step_signal.emit("render", 100, "Done", ACCENT_GREEN)
        self.overall_signal.emit(80, "Muxing audio…")

        # STEP 3: Mux
        self.step_signal.emit("mux", 0, "Running…", ACCENT_GOLD)
        source_audio_info = self._detect_source_audio(j["input_video"])
        audio_args = self._build_audio_args(j["codec_a"], source_audio_info)
        # No frame-rate special-casing needed here. The renderer computes
        # target_dur purely from the audio's measured duration -- totally
        # independent of --output-fps -- so feeding it whatever rate the
        # user picked directly gives correct duration by construction AND
        # genuine continuous blending computed at that resolution (no
        # literal duplicate frames, no pulldown judder). The earlier
        # "it slows down" issue was caused by a since-reverted metadata-only
        # relabel trick that genuinely broke duration; it was never caused
        # by rendering directly at a different target rate.
        cmd_mux = [
            find_binary("ffmpeg"), "-y",
            "-i", temp_vid, "-i", skippy_wav,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy",
        ]
        cmd_mux += [*audio_args, out_video]
        ret = self._run(cmd_mux)
        if self._check_cancelled("mux", raw_wav, skippy_wav, temp_vid): return
        if ret != 0:
            self.step_signal.emit("mux", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "Mux failed"); return
        self.step_signal.emit("mux", 100, "Done", ACCENT_GREEN)
        self.overall_signal.emit(92, "Subtitle retime…")

        # STEP 4: Subtitles
        if j["sub_enable"] and j["input_subs"]:
            self.step_signal.emit("subs", 0, "Running…", ACCENT_GOLD)
            map_file = os.path.join(out_dir, "map_t_skip_to_t_orig.npy")
            sub_out  = j["sub_output"] or os.path.join(out_dir, out_name + "_TC.srt")
            sub_script = os.path.join(self.script_dir, "subtitle_retime.py")
            ret = self._run_script_with_fallback(sub_script, ["-i", j["input_subs"], "-o", sub_out, "-m", map_file], "subs")
            if self._check_cancelled("subs", raw_wav, skippy_wav, temp_vid): return
            self.step_signal.emit("subs", 100, "Done" if ret==0 else "FAILED", ACCENT_GREEN if ret==0 else ACCENT_RED)
        else:
            self.step_signal.emit("subs", 100, "Skipped", TEXT_MUTED)

        # Cleanup -- once the final mux is done, we no longer need the
        # intermediate raw/skippy WAV files or the Premiere marker file
        # the audio engine writes alongside its output.
        self._cleanup_intermediates(raw_wav, skippy_wav, temp_vid)

        self.overall_signal.emit(100, "Complete!")
        self.done_signal.emit(True, out_video)

    def _run(self, cmd):
        # If Stop was already clicked (e.g. between pipeline steps), don't
        # even launch the next subprocess.
        if self._stop_requested:
            return -999  # sentinel: cancelled, not a real exit code

        # Log with quoted paths for display
        display = " ".join(f'"{a}"' if " " in a else a for a in cmd)
        self.log_signal.emit("$ " + display, ACCENT_BLUE)
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace"
            )
            self._current_proc = proc
            for line in proc.stdout:
                self.log_signal.emit(line.rstrip(), None)
            proc.wait()

            if self._stop_requested:
                # The loop above ended because we terminated the process
                # (terminate() closes its stdout), not because it finished
                # naturally. If terminate() didn't actually kill it within
                # a couple seconds (some processes catch/ignore SIGTERM),
                # force it.
                if proc.poll() is None:
                    try:
                        proc.kill()
                        proc.wait(timeout=5)
                    except Exception:
                        pass
                self.log_signal.emit("[!] Job cancelled by user.", ACCENT_GOLD)
                return -999

            return proc.returncode
        except FileNotFoundError as ex:
            self.log_signal.emit(f"[!] Could not launch: {ex}", ACCENT_GOLD)
            return 1
        finally:
            self._current_proc = None

# ── MAIN WINDOW ───────────────────────────────
class TempoCut(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TempoCut v1.2 — Broadcast Time Compression Suite (Fast Render)")
        self.setMinimumSize(1000,720); self.resize(1200,840)
        self.setStyleSheet(STYLESHEET)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Window/taskbar icon while the app is running. This is separate
        # from the .exe file's own icon (that one's set at build time via
        # PyInstaller's spec, not here). Looked up next to the exe the same
        # way the companion scripts are, so dropping the icon file into the
        # install folder is all that's needed -- no rebuild required.
        icon_path = os.path.join(self.script_dir, "tempocut_icon_256.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._last_output = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(HeaderWidget())

        self.tabs = QTabWidget(); self.tabs.setDocumentMode(True)
        self.tab_job     = JobTab()
        self.tab_comp    = CompressionTab()
        self.tab_blend   = FrameBlendTab()
        self.tab_editor  = EditorTab()
        self.tab_preview = PreviewTab()
        self.tab_log     = LogTab()

        self.tabs.addTab(self.tab_job,     "Job")
        self.tabs.addTab(self.tab_comp,    "Compression")
        self.tabs.addTab(self.tab_blend,   "Frame Blend")
        self.tabs.addTab(self.tab_editor,  "Editor")
        self.tabs.addTab(self.tab_preview, "Preview")
        self.tabs.addTab(self.tab_log,     "Log / Progress")
        root.addWidget(self.tabs,1)

        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.status.showMessage("TempoCut ready.  |  Load a video in the Job tab.")

        # Wire signals
        self.tab_job.btn_run.clicked.connect(self._run_job)
        self.tab_job.btn_stop.clicked.connect(self._stop_job)
        self.tab_job.btn_clear.clicked.connect(self._clear_all)
        self.tab_job.video_loaded.connect(self._on_video_loaded)

        if not CV2_OK:
            self.status.showMessage("TempoCut ready.  |  Install opencv-python for video preview.")

        self._runner = None

    def _on_video_loaded(self, path):
        self.tab_editor.load_video(path)
        self.tab_preview.load_original(path)
        self.tab_comp.set_detected_fps(self.tab_job.detected_fps)
        self.status.showMessage(f"Loaded: {path}")

    def _run_job(self):
        jp = self.tab_job.get_params()
        if not jp["input_video"]:
            QMessageBox.warning(self, "Missing Input", "Please specify an input video file."); return
        if not jp["output_path"]:
            QMessageBox.warning(self, "Missing Output", "Please specify an output folder."); return
        if not jp["output_name"]:
            jp["output_name"] = os.path.splitext(os.path.basename(jp["input_video"]))[0] + "_TC"

        # If Target Length is enabled, compute the required ratio from the
        # source video's actual duration and auto-select the best Skippy
        # Mode for it, bypassing whatever's in the Target Ratio field.
        target_sec = jp.get("target_length_sec")
        if target_sec:
            original_dur = self._probe_duration(jp["input_video"])
            if not original_dur:
                QMessageBox.warning(self, "Target Length",
                    "Could not read the source video's duration to compute "
                    "the target ratio. Check the input file and try again.")
                return
            if target_sec >= original_dur:
                QMessageBox.warning(self, "Target Length",
                    f"Target length ({target_sec:.0f}s) must be shorter than "
                    f"the source duration ({original_dur:.0f}s).")
                return
            computed_ratio = original_dur / target_sec
            warning, is_blocking = self.tab_comp.apply_target_ratio(computed_ratio)
            if is_blocking:
                QMessageBox.critical(self, "Target Length Not Achievable", warning)
                return
            self.status.showMessage(
                f"Target length {target_sec:.0f}s -> computed ratio {computed_ratio:.4f}"
            )
            if warning:
                QMessageBox.information(self, "Heads up", warning)

        cp = self.tab_comp.get_params()
        bp = self.tab_blend.get_params()
        ep = self.tab_editor.get_params()

        for key,(bar,lbl) in self.tab_log.bars.items():
            bar.setValue(0); lbl.setText("Waiting")
            lbl.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;")
        self.tab_log.set_overall(0,"Starting…")
        self.tab_log.log.clear()
        self.tabs.setCurrentWidget(self.tab_log)

        self._runner = JobRunner(jp, cp, bp, ep, self.script_dir)
        self._runner.log_signal.connect(lambda msg,col: self.tab_log.append(msg,col))
        self._runner.step_signal.connect(lambda k,p,s,c: self.tab_log.set_step(k,p,s,c))
        self._runner.overall_signal.connect(lambda p,t: self.tab_log.set_overall(p,t))
        self._runner.done_signal.connect(self._on_done)
        self._runner.start()
        self.status.showMessage(f"Running: {jp.get('job_name') or jp['output_name']} …")
        self.tab_job.btn_run.setEnabled(False)
        self.tab_job.btn_stop.setEnabled(True)

    def _probe_duration(self, video_path):
        """ffprobe the source video's duration in seconds, or None on failure."""
        try:
            result = subprocess.run(
                [find_binary("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10
            )
            return float(result.stdout.strip())
        except Exception:
            return None

    def _on_done(self, success, msg):
        self.tab_job.btn_run.setEnabled(True)
        self.tab_job.btn_stop.setEnabled(False)
        if success:
            self._last_output = msg
            self.status.showMessage(f"Job complete: {msg}")
            self.tab_preview.load_compressed(msg)
            self.tabs.setCurrentWidget(self.tab_preview)
            QMessageBox.information(self, "TempoCut", f"Done!\n\n{msg}")
        elif msg == "Job cancelled by user":
            # Cancellation isn't an error -- don't scare the user with a
            # red "critical" dialog over something they asked for.
            self.status.showMessage("Job cancelled.")
            QMessageBox.information(self, "TempoCut", "Job cancelled.")
        else:
            self.status.showMessage(f"Job failed: {msg}")
            QMessageBox.critical(self, "TempoCut", f"Job failed:\n{msg}")

    def _stop_job(self):
        if self._runner and self._runner.isRunning():
            self.status.showMessage("Stopping job…")
            self.tab_job.btn_stop.setEnabled(False)  # prevent double-clicks while it winds down
            self._runner.request_stop()

    def _clear_all(self):
        self.tab_job._clear()
        self.tab_log.log.clear()
        self.tab_log.set_overall(0,"Idle")
        for key in self.tab_log.bars:
            self.tab_log.set_step(key,0,"Waiting",TEXT_MUTED)
        self.status.showMessage("Cleared.")

# ── ENTRY ─────────────────────────────────────
def _maybe_run_as_script_host():
    """
    TempoCut.exe --run-script <path/to/script.py> [args...]

    When invoked this way, acts as a plain interpreter for that one
    script instead of launching the GUI -- using the SAME environment
    already bundled inside this exe (numpy, librosa, cv2, soundfile,
    pysubs2 are already sitting in _internal/ from this exe's own
    PyInstaller build). This is what lets audio_skippy_SURROUND.py,
    time_compressor_SAFE_v2.py, and subtitle_retime.py run without
    needing a separate system Python with those packages manually
    pip-installed -- which used to be a real, fragile requirement and
    a common point of failure on machines that didn't already have
    a "real" Python set up exactly right (e.g. the Windows Store stub
    python.exe, which exists by default but isn't a real interpreter).

    Exits the process when triggered; returns normally (does nothing)
    for a regular GUI launch.
    """
    if len(sys.argv) >= 3 and sys.argv[1] == "--run-script":
        script_path = sys.argv[2]
        sys.argv = [script_path] + sys.argv[3:]
        # Same buffering issue as the -u flag fixes for the other launch
        # paths: this process's stdout is being read through a pipe by
        # the GUI, which defaults Python to full buffering instead of
        # line buffering. Without this, real progress (DTW computation,
        # frame rendering) can happen correctly while looking completely
        # frozen in the console, since nothing gets flushed until the
        # buffer fills or the process exits.
        try:
            sys.stdout.reconfigure(line_buffering=True)
            sys.stderr.reconfigure(line_buffering=True)
        except Exception:
            pass
        import runpy
        try:
            runpy.run_path(script_path, run_name="__main__")
            sys.exit(0)
        except SystemExit:
            raise
        except Exception as ex:
            print(f"[!] Error running {script_path}: {ex}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    _maybe_run_as_script_host()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window,        QColor(BG_DARK))
    pal.setColor(QPalette.WindowText,    QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Base,          QColor(BG_FIELD))
    pal.setColor(QPalette.AlternateBase, QColor(BG_MID))
    pal.setColor(QPalette.Text,          QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Button,        QColor(BG_MID))
    pal.setColor(QPalette.ButtonText,    QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Highlight,     QColor(ACCENT_BLUE))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)
    win = TempoCut()
    win.show()
    sys.exit(app.exec_())
