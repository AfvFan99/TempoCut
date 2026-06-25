"""
TempoCut v1.1
Broadcast-grade time compression tool — PyQt5 UI
- Auto audio extraction from video (no separate WAV input needed)
- Live video preview with OpenCV in Editor + Preview tabs
- Sub-frame Premiere-style frame blending
- Spaces-in-paths safe subprocess calls
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
    QBrush, QPen, QImage
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

        ctrl = QHBoxLayout(); ctrl.setSpacing(4)
        for sym, tip, cb in [
            ("⏮","Go to start", self._go_start),
            ("⏪","Back 10s",    self._back10),
            ("▶","Play/Pause",  self._toggle_play),
            ("⏩","Fwd 10s",    self._fwd10),
            ("⏭","Go to end",   self._go_end),
        ]:
            b = QPushButton(sym); b.setToolTip(tip); b.setFixedSize(34, 28)
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
        tag = QLabel("Broadcast Time Compression Suite  ·  v1.1")
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
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        main = QVBoxLayout(inner); main.setSpacing(14); main.setContentsMargins(16,16,16,16)

        # INPUT
        grp_in = QGroupBox("Input File Segment")
        gin = QVBoxLayout(grp_in); gin.setSpacing(8)
        gin.addWidget(section_header("Segment 1"))

        self.inp_video = QLineEdit(); self.inp_video.setPlaceholderText("Input video (.mp4 .mov .mxf …)")
        self.inp_subs  = QLineEdit(); self.inp_subs.setPlaceholderText("Subtitles (.srt) — optional")

        gin.addLayout(field_row("Input Video", self.inp_video, self._browse_video))
        gin.addLayout(field_row("Input Subtitles", self.inp_subs, self._browse_subs))

        note = QLabel("Audio is extracted automatically from the video — no separate WAV needed.")
        note.setStyleSheet(f"color:{ACCENT_GREEN};font-size:11px;padding:4px 0;")
        gin.addWidget(note)

        tc_row = QHBoxLayout()
        for label, attr, default in [("Start TC","tc_start","00:00:00:00"),("Stop TC","tc_stop","00:00:00:00"),("Target Length","tc_target","00:00:00:00")]:
            tc_row.addWidget(QLabel(label+":"))
            tc = QLineEdit(default); tc.setFixedWidth(110); setattr(self, attr, tc)
            tc_row.addWidget(tc); tc_row.addSpacing(12)
        tc_row.addStretch(); gin.addLayout(tc_row)
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
        self.codec_a = QComboBox(); self.codec_a.addItems(["AAC 640k (5.1)","PCM 24LE","AC3 640k","EAC3"]); self.codec_a.setFixedWidth(150)
        codec_row.addWidget(self.codec_a); codec_row.addSpacing(16)
        codec_row.addWidget(QLabel("Bitrate (Mb/s):"))
        self.bitrate = QSpinBox(); self.bitrate.setRange(1,200); self.bitrate.setValue(25); self.bitrate.setFixedWidth(60)
        codec_row.addWidget(self.bitrate); codec_row.addStretch(); gout.addLayout(codec_row)
        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("Output FPS:"))
        self.out_fps = QComboBox(); self.out_fps.addItems(["59.94 (default)","29.97","23.976","25","50","60"]); self.out_fps.setFixedWidth(140)
        fps_row.addWidget(self.out_fps); fps_row.addSpacing(16)
        fps_row.addWidget(QLabel("Preset:"))
        self.enc_preset = QComboBox(); self.enc_preset.addItems(["fast","medium","slow","ultrafast","veryslow"]); self.enc_preset.setFixedWidth(110)
        fps_row.addWidget(self.enc_preset); fps_row.addStretch(); gout.addLayout(fps_row)
        main.addWidget(grp_out)

        # SUBTITLES
        grp_sub = QGroupBox("Closed Captions / Subtitles")
        gsub = QVBoxLayout(grp_sub)
        self.sub_enable = QCheckBox("Process Closed Captions"); gsub.addWidget(self.sub_enable)
        self.sub_output = QLineEdit(); self.sub_output.setPlaceholderText("Output subtitle file")
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
        self.btn_clear = QPushButton("✕  CLEAR"); self.btn_clear.setObjectName("btn_clear"); self.btn_clear.setFixedHeight(36)
        btn_row.addWidget(self.btn_run); btn_row.addSpacing(12); btn_row.addWidget(self.btn_clear); btn_row.addStretch()
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
            self.video_loaded.emit(f)

    def _browse_subs(self):
        f, _ = QFileDialog.getOpenFileName(self, "Subtitles", "", "Subtitle Files (*.srt *.stl);;All Files (*)")
        if f: self.inp_subs.setText(f)
    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "Output Folder")
        if d: self.out_path.setText(d)
    def _browse_sub_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "Output Subtitle", "", "SRT (*.srt);;STL (*.stl)")
        if f: self.sub_output.setText(f)

    def _clear(self):
        for w in [self.inp_video, self.inp_subs, self.out_path, self.out_name, self.job_name, self.sub_output]:
            w.clear()
        for tc in [self.tc_start, self.tc_stop, self.tc_target]:
            tc.setText("00:00:00:00")

    def get_params(self):
        return {
            "input_video":  self.inp_video.text(),
            "input_subs":   self.inp_subs.text(),
            "output_path":  self.out_path.text(),
            "output_name":  self.out_name.text(),
            "codec_v":      self.codec_v.currentText().split()[0],
            "codec_a":      self.codec_a.currentText().split()[0].lower(),
            "bitrate":      self.bitrate.value(),
            "fps":          self.out_fps.currentText().split()[0],
            "preset":       self.enc_preset.currentText(),
            "job_name":     self.job_name.text(),
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
        gas = QGridLayout(grp_as); gas.setSpacing(8)
        skippy_params = [
            ("Target Ratio","target_ratio",QDoubleSpinBox,(1.0,1.1,1.0129,0.0001,4),"Compression ratio (1.0129 = ~1.28%)"),
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
        gas.setColumnStretch(2,1); main.addWidget(grp_as)

        grp_dtw = QGroupBox("DTW Video Compressor")
        gdtw = QGridLayout(grp_dtw); gdtw.setSpacing(8)
        dtw_params = [
            ("Target SR","target_sr",QSpinBox,(8000,48000,16000),""),
            ("N Mels","n_mels",QSpinBox,(16,256,64),""),
            ("Hop Length","hop",QSpinBox,(256,8192,2048),""),
            ("Time Decim","time_decim",QSpinBox,(1,8,2),""),
            ("Max Jump Ratio","max_jump",QDoubleSpinBox,(1.0,3.0,1.2,0.05,2),""),
            ("Output FPS","out_fps",QDoubleSpinBox,(23.0,120.0,59.94,0.01,3),""),
        ]
        self._dtw = {}
        for row,(label,key,wtype,args,_) in enumerate(dtw_params):
            lbl=QLabel(label+":"); lbl.setObjectName("field_label"); gdtw.addWidget(lbl,row,0)
            if wtype==QDoubleSpinBox:
                w=QDoubleSpinBox(); w.setRange(args[0],args[1]); w.setValue(args[2]); w.setSingleStep(args[3]); w.setDecimals(args[4])
            else:
                w=QSpinBox(); w.setRange(args[0],args[1]); w.setValue(args[2])
            w.setFixedWidth(120); gdtw.addWidget(w,row,1); self._dtw[key]=w
        gdtw.setColumnStretch(2,1); main.addWidget(grp_dtw)
        main.addStretch()
        scroll.setWidget(inner); lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)

    def get_params(self):
        return {k:w.value() for k,w in {**self._skippy,**self._dtw}.items()}

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

        def slider_row(label, mn, mx, val, scale=1, decimals=0):
            row = QHBoxLayout()
            lbl = QLabel(label+":"); lbl.setObjectName("field_label"); lbl.setFixedWidth(160); row.addWidget(lbl)
            sl = QSlider(Qt.Horizontal); sl.setRange(int(mn*scale),int(mx*scale)); sl.setValue(int(val*scale)); row.addWidget(sl,1)
            disp = QLabel(f"{val}" if decimals==0 else f"{val:.{decimals}f}")
            disp.setFixedWidth(60); disp.setStyleSheet(f"color:{ACCENT_GREEN};font-family:'{MONO_FONT}';font-size:12px;")
            sl.valueChanged.connect(lambda v,d=disp,sc=scale,dec=decimals: d.setText(f"{v/sc}" if dec==0 else f"{v/sc:.{dec}f}"))
            row.addWidget(disp); return row, sl

        r1,self.sl_blend_every = slider_row("Blend Every N Frames",1,120,20)
        r2,self.sl_blend_alpha = slider_row("Blend Alpha",0,1,0.50,scale=100,decimals=2)
        r3,self.sl_smear_ms    = slider_row("Smear Duration (ms)",1,200,32)
        g.addLayout(r1); g.addLayout(r2); g.addLayout(r3)
        main.addWidget(grp)

        grp2 = QGroupBox("Blend Mode")
        g2 = QVBoxLayout(grp2); g2.setSpacing(8)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.blend_mode = QComboBox()
        self.blend_mode.addItems([
            "Sub-Frame / Premiere-style (recommended)",
            "Forward Smear",
            "Backward Smear",
            "Bilateral (avg prev+next)",
            "Motion Adaptive",
        ])
        self.blend_mode.setFixedWidth(300)
        mode_row.addWidget(self.blend_mode); mode_row.addStretch(); g2.addLayout(mode_row)

        desc = QLabel(
            "<b>Sub-Frame / Premiere-style</b>: blend weight = exact sub-frame position between source frames. "
            "If the output frame lands 70% between frame A and B, you get 30% A + 70% B — "
            "identical to Premiere Pro's Frame Blending mode on speed-ramped clips."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;padding:6px;background:{BG_PANEL};border:1px solid {BORDER};border-radius:3px;")
        desc.setTextFormat(Qt.RichText)
        g2.addWidget(desc)
        self.blend_motion = QCheckBox("Motion-Compensated Blend (slower, cleaner on fast motion)")
        g2.addWidget(self.blend_motion)
        main.addWidget(grp2)
        main.addStretch()

    def get_params(self):
        return {
            "blend_enable": self.blend_enable.isChecked(),
            "blend_every":  self.sl_blend_every.value(),
            "blend_alpha":  self.sl_blend_alpha.value()/100.0,
            "smear_ms":     self.sl_smear_ms.value(),
            "blend_mode":   self.blend_mode.currentText(),
            "motion_comp":  self.blend_motion.isChecked(),
        }

# ── EDITOR TAB ────────────────────────────────
class EditorTab(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self); main.setSpacing(12); main.setContentsMargins(16,16,16,16)
        main.addWidget(section_header("Pre-Compression Editor"))

        self.player = VideoPlayer(label="")
        self.player.setMinimumHeight(320)
        main.addWidget(self.player, 1)

        if not CV2_OK:
            warn = QLabel("pip install opencv-python  to enable preview")
            warn.setStyleSheet(f"color:{ACCENT_GOLD};font-size:11px;")
            main.addWidget(warn)

        # TRIM
        grp_trim = QGroupBox("Trim / Cut")
        gt = QGridLayout(grp_trim); gt.setSpacing(8)
        self.trim_in  = QLineEdit("00:00:00:00"); self.trim_in.setFixedWidth(120)
        self.trim_out = QLineEdit("00:00:00:00"); self.trim_out.setFixedWidth(120)
        gt.addWidget(QLabel("In Point:"),  1,0); gt.addWidget(self.trim_in,  1,1)
        btn_in = QPushButton("Set In at Playhead")
        btn_in.clicked.connect(lambda: self.trim_in.setText(self._tc_str(self.player.get_pos())))
        gt.addWidget(btn_in, 1,2)
        gt.addWidget(QLabel("Out Point:"), 2,0); gt.addWidget(self.trim_out, 2,1)
        btn_out = QPushButton("Set Out at Playhead")
        btn_out.clicked.connect(lambda: self.trim_out.setText(self._tc_str(self.player.get_pos())))
        gt.addWidget(btn_out, 2,2)
        main.addWidget(grp_trim)

        # COLOUR
        grp_col = QGroupBox("Color / Brightness")
        gc = QVBoxLayout(grp_col); gc.setSpacing(8)
        self._color_sliders = {}
        for label, key, default in [("Brightness","brightness",0),("Contrast","contrast",0),("Saturation","saturation",0),("Gamma","gamma",0)]:
            row = QHBoxLayout()
            lbl=QLabel(label+":"); lbl.setObjectName("field_label"); lbl.setFixedWidth(130); row.addWidget(lbl)
            sl=QSlider(Qt.Horizontal); sl.setRange(-100,100); sl.setValue(default); row.addWidget(sl,1)
            val=QLabel(str(default)); val.setFixedWidth(40); val.setStyleSheet(f"color:{ACCENT_GREEN};font-family:'{MONO_FONT}';")
            sl.valueChanged.connect(lambda v,d=val: d.setText(str(v))); row.addWidget(val)
            rst=QPushButton("Reset"); rst.setFixedWidth(56); rst.clicked.connect(lambda _,s=sl,dv=default: s.setValue(dv)); row.addWidget(rst)
            gc.addLayout(row); self._color_sliders[key]=sl
        main.addWidget(grp_col)

        # AUDIO LEVEL
        grp_aud = QGroupBox("Audio Level")
        ga = QVBoxLayout(grp_aud); ga.setSpacing(8)
        aud_row = QHBoxLayout()
        aud_row.addWidget(QLabel("Master Gain (dB):"))
        self.sl_gain = QSlider(Qt.Horizontal); self.sl_gain.setRange(-24,24); self.sl_gain.setValue(0)
        self.lbl_gain = QLabel("0 dB"); self.lbl_gain.setStyleSheet(f"color:{ACCENT_GREEN};font-family:'{MONO_FONT}';")
        self.sl_gain.valueChanged.connect(lambda v: self.lbl_gain.setText(f"{v:+d} dB"))
        aud_row.addWidget(self.sl_gain,1); aud_row.addWidget(self.lbl_gain); ga.addLayout(aud_row)
        norm_row = QHBoxLayout()
        self.chk_normalize = QCheckBox("Normalize to -23 LUFS (EBU R128)")
        self.chk_limiter   = QCheckBox("True peak limiter (-1 dBTP)")
        norm_row.addWidget(self.chk_normalize); norm_row.addWidget(self.chk_limiter); norm_row.addStretch()
        ga.addLayout(norm_row); main.addWidget(grp_aud)

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

    def run(self):
        try: self._run_pipeline()
        except Exception as ex:
            self.log_signal.emit(f"FATAL: {ex}", ACCENT_RED)
            self.done_signal.emit(False, str(ex))

    def _run_pipeline(self):
        j=self.job; c=self.comp
        out_dir   = j["output_path"]
        out_name  = j["output_name"]
        out_video = os.path.join(out_dir, out_name + "_tc.mp4")
        raw_wav   = os.path.join(out_dir, out_name + "_raw_audio.wav")
        skippy_wav= os.path.join(out_dir, out_name + "_heavy.wav")
        temp_vid  = os.path.join(out_dir, out_name + "_temp.mp4")

        # STEP 0: Extract audio from video
        self.step_signal.emit("extract", 0, "Running…", ACCENT_GOLD)
        self.overall_signal.emit(5, "Extracting audio…")
        cmd_extract = [
            "ffmpeg", "-y", "-i", j["input_video"],
            "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "6",
            raw_wav
        ]
        # fallback to stereo if 6ch fails
        ret = self._run(cmd_extract)
        if ret != 0:
            self.log_signal.emit("[!] 6-channel extract failed, trying stereo…", ACCENT_GOLD)
            cmd_extract[-3] = "2"
            ret = self._run(cmd_extract)
        if ret != 0:
            self.step_signal.emit("extract", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "Audio extraction failed"); return
        self.step_signal.emit("extract", 100, "Done", ACCENT_GREEN)
        self.overall_signal.emit(12, "Audio compression…")

        # STEP 1: Audio Skippy
        self.step_signal.emit("audio_skippy", 0, "Running…", ACCENT_GOLD)
        audio_skippy_script = os.path.join(self.script_dir, "audio_skippy_SURROUND.py")
        cmd_skippy = [
            sys.executable, audio_skippy_script,
            "-i", raw_wav, "-o", skippy_wav,
            "--target-ratio", str(c["target_ratio"]),
            "--frame-ms",     str(int(c["frame_ms"])),
            "--max-chop-ms",  str(int(c["max_chop_ms"])),
            "--cadence-ms",   str(int(c["cadence_ms"])),
            "--crossfade-ms", str(int(c["crossfade_ms"])),
            "--energy-quantile", str(c["energy_q"]),
        ]
        ret = self._run(cmd_skippy)
        if ret != 0:
            self.step_signal.emit("audio_skippy", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "audio_skippy failed"); return
        self.step_signal.emit("audio_skippy", 100, "Done", ACCENT_GREEN)
        self.overall_signal.emit(30, "DTW video compression…")

        # STEP 2: DTW video compressor
        self.step_signal.emit("dtw", 0, "Running…", ACCENT_GOLD)
        self.step_signal.emit("render", 0, "Queued…", TEXT_MUTED)
        tc_script = os.path.join(self.script_dir, "time_compressor_SAFE.py")
        cmd_dtw = [sys.executable, tc_script, "-i", j["input_video"], "-s", skippy_wav, "-o", temp_vid]
        ret = self._run(cmd_dtw)
        if ret != 0:
            self.step_signal.emit("dtw", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "DTW compressor failed"); return
        self.step_signal.emit("dtw",    100, "Done", ACCENT_GREEN)
        self.step_signal.emit("render", 100, "Done", ACCENT_GREEN)
        self.overall_signal.emit(80, "Muxing audio…")

        # STEP 3: Mux
        self.step_signal.emit("mux", 0, "Running…", ACCENT_GOLD)
        cmd_mux = [
            "ffmpeg", "-y",
            "-i", temp_vid, "-i", skippy_wav,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "640k",
            out_video
        ]
        ret = self._run(cmd_mux)
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
            cmd_subs = [sys.executable, sub_script, "-i", j["input_subs"], "-o", sub_out, "-m", map_file]
            ret = self._run(cmd_subs)
            self.step_signal.emit("subs", 100, "Done" if ret==0 else "FAILED", ACCENT_GREEN if ret==0 else ACCENT_RED)
        else:
            self.step_signal.emit("subs", 100, "Skipped", TEXT_MUTED)

        # Cleanup
        for f in [temp_vid, raw_wav]:
            try: os.remove(f)
            except: pass

        self.overall_signal.emit(100, "Complete!")
        self.done_signal.emit(True, out_video)

    def _run(self, cmd):
        # Log with quoted paths for display
        display = " ".join(f'"{a}"' if " " in a else a for a in cmd)
        self.log_signal.emit("$ " + display, ACCENT_BLUE)
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace"
            )
            for line in proc.stdout:
                self.log_signal.emit(line.rstrip(), None)
            proc.wait()
            return proc.returncode
        except FileNotFoundError as ex:
            self.log_signal.emit(f"[!] Could not launch: {ex}", ACCENT_GOLD)
            return 1

# ── MAIN WINDOW ───────────────────────────────
class TempoCut(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TempoCut v1.1 — Broadcast Time Compression Suite")
        self.setMinimumSize(1000,720); self.resize(1200,840)
        self.setStyleSheet(STYLESHEET)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
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
        self.tab_job.btn_clear.clicked.connect(self._clear_all)
        self.tab_job.video_loaded.connect(self._on_video_loaded)

        if not CV2_OK:
            self.status.showMessage("TempoCut ready.  |  Install opencv-python for video preview.")

        self._runner = None

    def _on_video_loaded(self, path):
        self.tab_editor.load_video(path)
        self.tab_preview.load_original(path)
        self.status.showMessage(f"Loaded: {path}")

    def _run_job(self):
        jp = self.tab_job.get_params()
        if not jp["input_video"]:
            QMessageBox.warning(self, "Missing Input", "Please specify an input video file."); return
        if not jp["output_path"]:
            QMessageBox.warning(self, "Missing Output", "Please specify an output folder."); return
        if not jp["output_name"]:
            jp["output_name"] = os.path.splitext(os.path.basename(jp["input_video"]))[0] + "_TC"

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

    def _on_done(self, success, msg):
        self.tab_job.btn_run.setEnabled(True)
        if success:
            self._last_output = msg
            self.status.showMessage(f"Job complete: {msg}")
            self.tab_preview.load_compressed(msg)
            self.tabs.setCurrentWidget(self.tab_preview)
            QMessageBox.information(self, "TempoCut", f"Done!\n\n{msg}")
        else:
            self.status.showMessage(f"Job failed: {msg}")
            QMessageBox.critical(self, "TempoCut", f"Job failed:\n{msg}")

    def _clear_all(self):
        self.tab_job._clear()
        self.tab_log.log.clear()
        self.tab_log.set_overall(0,"Idle")
        for key in self.tab_log.bars:
            self.tab_log.set_step(key,0,"Waiting",TEXT_MUTED)
        self.status.showMessage("Cleared.")

# ── ENTRY ─────────────────────────────────────
if __name__ == "__main__":
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
