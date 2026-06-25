"""
TempoCut v1.0
Broadcast-grade time compression tool — PyQt5 UI
Wraps: audio_skippy_SURROUND.py, time_compressor_SAFE.py, subtitle_retime.py
"""

import sys, os, subprocess, json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QTabWidget, QSlider, QCheckBox, QComboBox, QGroupBox,
    QProgressBar, QTextEdit, QSplitter, QFrame, QSpinBox,
    QDoubleSpinBox, QScrollArea, QSizePolicy, QToolButton,
    QStackedWidget, QMessageBox, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl, QSize
from PyQt5.QtGui import (
    QColor, QPalette, QFont, QPixmap, QPainter, QLinearGradient,
    QBrush, QPen, QIcon, QFontDatabase
)

# ─────────────────────────────────────────────
#  STYLE CONSTANTS  (Prime Image dark broadcast)
# ─────────────────────────────────────────────
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
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: '{BASE_FONT}';
    font-size: 12px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {BG_PANEL};
    top: -1px;
}}
QTabBar::tab {{
    background: {BG_MID};
    color: {TEXT_MUTED};
    padding: 7px 20px;
    border: 1px solid {BORDER};
    border-bottom: none;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QTabBar::tab:selected {{
    background: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT_BLUE};
}}
QTabBar::tab:hover:!selected {{
    background: {BG_PANEL};
    color: {TEXT_PRIMARY};
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 18px;
    padding-top: 8px;
    font-size: 11px;
    font-weight: 700;
    color: {TEXT_LABEL};
    letter-spacing: 1.5px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 10px;
    top: 2px;
    color: {ACCENT_BLUE};
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
    background: {BG_FIELD};
    border: 1px solid {BORDER};
    border-radius: 3px;
    color: {TEXT_PRIMARY};
    padding: 4px 8px;
    font-family: '{MONO_FONT}';
    font-size: 12px;
    selection-background-color: {ACCENT_BLUE};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    background: {BG_MID};
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {BG_MID};
    border: 1px solid {BORDER_BRIGHT};
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT_BLUE};
}}
QPushButton {{
    background: {BG_MID};
    border: 1px solid {BORDER_BRIGHT};
    border-radius: 3px;
    color: {TEXT_PRIMARY};
    padding: 5px 14px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
}}
QPushButton:pressed {{
    background: #155a96;
}}
QPushButton#btn_run {{
    background: {ACCENT_GREEN};
    border-color: {ACCENT_GREEN};
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 28px;
    letter-spacing: 1px;
}}
QPushButton#btn_run:hover {{ background: #18a060; }}
QPushButton#btn_clear {{
    background: {ACCENT_RED};
    border-color: {ACCENT_RED};
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 20px;
}}
QPushButton#btn_clear:hover {{ background: #a93226; }}
QPushButton#btn_browse {{
    background: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
    color: #fff;
    padding: 4px 12px;
    font-size: 11px;
}}
QPushButton#btn_browse:hover {{ background: #1560a0; }}
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT_BLUE};
    width: 14px; height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{ background: {ACCENT_BLUE}; border-radius: 2px; }}
QProgressBar {{
    background: {BG_FIELD};
    border: 1px solid {BORDER};
    border-radius: 3px;
    height: 16px;
    text-align: center;
    color: {TEXT_PRIMARY};
    font-size: 11px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {ACCENT_BLUE}, stop:1 {ACCENT_GREEN});
    border-radius: 2px;
}}
QCheckBox {{ color: {TEXT_PRIMARY}; spacing: 6px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {BORDER_BRIGHT};
    border-radius: 2px;
    background: {BG_FIELD};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT_GREEN};
    border-color: {ACCENT_GREEN};
    image: none;
}}
QScrollBar:vertical {{
    background: {BG_DARK};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_BRIGHT};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLabel#section_header {{
    color: {ACCENT_BLUE};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 3px 0;
    border-bottom: 1px solid {BORDER};
}}
QLabel#field_label {{
    color: {TEXT_LABEL};
    font-size: 11px;
    text-align: right;
}}
QFrame#divider {{
    background: {BORDER};
    max-height: 1px;
}}
QStatusBar {{
    background: {BG_HEADER};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
    font-size: 11px;
}}
"""

# ─────────────────────────────────────────────
#  HEADER WIDGET
# ─────────────────────────────────────────────
class HeaderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(64)
        self.setStyleSheet(f"background: {BG_HEADER}; border-bottom: 2px solid {ACCENT_BLUE};")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("TEMPO<span style='color:#1a6fb5'>CUT</span>")
        logo.setStyleSheet(f"font-size: 26px; font-weight: 900; color: {TEXT_PRIMARY}; letter-spacing: 3px; font-family: '{BASE_FONT}';")
        logo.setTextFormat(Qt.RichText)
        lay.addWidget(logo)

        tagline = QLabel("Broadcast Time Compression Suite  ·  v1.0")
        tagline.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; letter-spacing: 1px;")
        lay.addWidget(tagline)
        lay.addStretch()

        for label, color in [("DTW ENGINE", ACCENT_BLUE), ("59.94p", ACCENT_GREEN), ("5.1 AUDIO", ACCENT_GOLD)]:
            badge = QLabel(label)
            badge.setStyleSheet(f"background: {color}22; color: {color}; border: 1px solid {color}; border-radius: 3px; padding: 2px 8px; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
            lay.addWidget(badge)
            lay.addSpacing(6)

# ─────────────────────────────────────────────
#  TIMELINE BAR WIDGET
# ─────────────────────────────────────────────
class TimelineBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(48)
        self.duration = 600.0
        self.segments = []
        self.playhead = 0.0
        self.setStyleSheet(f"background: {BG_FIELD}; border: 1px solid {BORDER};")

    def set_duration(self, d): self.duration = max(d, 1); self.update()
    def set_playhead(self, t): self.playhead = t; self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # background
        p.fillRect(0, 0, w, h, QColor(BG_FIELD))

        # gradient fill (green → red like Prime Image)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(ACCENT_GREEN))
        grad.setColorAt(0.7, QColor(ACCENT_GOLD))
        grad.setColorAt(1.0, QColor(ACCENT_RED))
        p.fillRect(0, 8, w, 20, QBrush(grad))

        # tick marks
        p.setPen(QPen(QColor(TEXT_MUTED), 1))
        num_ticks = 10
        for i in range(num_ticks + 1):
            x = int(i * w / num_ticks)
            p.drawLine(x, 28, x, 36)
            t = i * self.duration / num_ticks
            mins = int(t // 60); secs = int(t % 60)
            p.setPen(QColor(TEXT_MUTED))
            p.setFont(QFont(MONO_FONT, 8))
            p.drawText(x - 20, 38, 40, 10, Qt.AlignCenter, f"{mins:02d}:{secs:02d}:00")
            p.setPen(QPen(QColor(TEXT_MUTED), 1))

        # playhead
        if self.duration > 0:
            px = int(self.playhead / self.duration * w)
            p.setPen(QPen(QColor("#ffffff"), 2))
            p.drawLine(px, 4, px, 36)

        p.end()

# ─────────────────────────────────────────────
#  FIELD ROW HELPER
# ─────────────────────────────────────────────
def field_row(label_text, widget, browse_cb=None):
    row = QHBoxLayout()
    lbl = QLabel(label_text + ":")
    lbl.setObjectName("field_label")
    lbl.setFixedWidth(160)
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    if browse_cb:
        btn = QPushButton("Browse")
        btn.setObjectName("btn_browse")
        btn.setFixedWidth(72)
        btn.clicked.connect(browse_cb)
        row.addWidget(btn)
    return row

def section_header(text):
    lbl = QLabel(text)
    lbl.setObjectName("section_header")
    return lbl

def divider():
    f = QFrame()
    f.setObjectName("divider")
    f.setFrameShape(QFrame.HLine)
    return f

# ─────────────────────────────────────────────
#  JOB TAB  (main compression panel)
# ─────────────────────────────────────────────
class JobTab(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        main = QVBoxLayout(inner)
        main.setSpacing(14)
        main.setContentsMargins(16, 16, 16, 16)

        # ── INPUT SEGMENTS ──
        grp_in = QGroupBox("Input File Segments")
        gin = QVBoxLayout(grp_in)
        gin.setSpacing(8)

        gin.addWidget(section_header("Segment 1"))

        self.inp_video = QLineEdit(); self.inp_video.setPlaceholderText("Path to input video (.mp4, .mov, .mxf…)")
        self.inp_audio = QLineEdit(); self.inp_audio.setPlaceholderText("Path to input audio (.wav, 5.1 surround)")
        self.inp_subs  = QLineEdit(); self.inp_subs.setPlaceholderText("Path to subtitles (.srt) — optional")

        gin.addLayout(field_row("Input Video", self.inp_video, self._browse_video))
        gin.addLayout(field_row("Input Audio (WAV)", self.inp_audio, self._browse_audio))
        gin.addLayout(field_row("Input Subtitles", self.inp_subs, self._browse_subs))

        # timecodes
        tc_row = QHBoxLayout()
        for label, attr in [("Start TC", "tc_start"), ("Stop TC", "tc_stop"), ("Target Length", "tc_target")]:
            tc_row.addWidget(QLabel(label + ":"))
            tc = QLineEdit("00:00:00:00"); tc.setFixedWidth(110)
            setattr(self, attr, tc)
            tc_row.addWidget(tc)
            tc_row.addSpacing(12)
        tc_row.addStretch()
        gin.addLayout(tc_row)

        main.addWidget(grp_in)

        # ── TIMELINE ──
        grp_tl = QGroupBox("Output File Timeline")
        gtl = QVBoxLayout(grp_tl)
        self.timeline = TimelineBar()
        gtl.addWidget(self.timeline)

        # segment table header
        seg_hdr = QHBoxLayout()
        for col, w in [("Segment", 100), ("Start", 110), ("Stop", 110), ("Reduce", 110), ("Percent", 80)]:
            l = QLabel(col)
            l.setStyleSheet(f"color: {TEXT_LABEL}; font-size: 11px; font-weight: 700;")
            l.setFixedWidth(w)
            seg_hdr.addWidget(l)
        seg_hdr.addStretch()
        gtl.addLayout(seg_hdr)

        seg_row = QHBoxLayout()
        defaults = [("Segment 1", 100), ("00:00:00:00", 110), ("00:09:54:00", 110), ("00:00:06:00", 110), ("1.00%", 80)]
        for val, w in defaults:
            l = QLabel(val)
            l.setStyleSheet(f"color: {ACCENT_GREEN}; font-family: '{MONO_FONT}'; font-size: 11px;")
            l.setFixedWidth(w)
            seg_row.addWidget(l)
        seg_row.addStretch()
        gtl.addLayout(seg_row)
        main.addWidget(grp_tl)

        # ── OUTPUT ──
        grp_out = QGroupBox("Output Settings")
        gout = QVBoxLayout(grp_out)
        gout.setSpacing(8)

        self.out_path = QLineEdit(); self.out_path.setPlaceholderText("Output folder")
        self.out_name = QLineEdit(); self.out_name.setPlaceholderText("Output filename (no extension)")

        gout.addLayout(field_row("Output Path", self.out_path, self._browse_out))
        gout.addLayout(field_row("Output File Name", self.out_name))

        codec_row = QHBoxLayout()
        codec_row.addWidget(QLabel("Video Codec:"))
        self.codec_v = QComboBox()
        self.codec_v.addItems(["libx264 (H.264)", "libx265 (H.265)", "prores_ks (ProRes)", "dnxhd (DNxHD)"])
        self.codec_v.setFixedWidth(180)
        codec_row.addWidget(self.codec_v)
        codec_row.addSpacing(16)
        codec_row.addWidget(QLabel("Audio Codec:"))
        self.codec_a = QComboBox()
        self.codec_a.addItems(["AAC 640k (5.1)", "PCM 24LE", "AC3 640k", "EAC3"])
        self.codec_a.setFixedWidth(150)
        codec_row.addWidget(self.codec_a)
        codec_row.addSpacing(16)
        codec_row.addWidget(QLabel("Bitrate (Mb/s):"))
        self.bitrate = QSpinBox(); self.bitrate.setRange(1, 200); self.bitrate.setValue(25); self.bitrate.setFixedWidth(60)
        codec_row.addWidget(self.bitrate)
        codec_row.addStretch()
        gout.addLayout(codec_row)

        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("Output FPS:"))
        self.out_fps = QComboBox()
        self.out_fps.addItems(["59.94 (default)", "29.97", "23.976", "25", "50", "60"])
        self.out_fps.setFixedWidth(140)
        fps_row.addWidget(self.out_fps)
        fps_row.addSpacing(16)
        fps_row.addWidget(QLabel("Preset:"))
        self.enc_preset = QComboBox()
        self.enc_preset.addItems(["fast", "medium", "slow", "ultrafast", "veryslow"])
        self.enc_preset.setFixedWidth(110)
        fps_row.addWidget(self.enc_preset)
        fps_row.addStretch()
        gout.addLayout(fps_row)

        main.addWidget(grp_out)

        # ── SUBTITLES ──
        grp_sub = QGroupBox("Closed Captions / Subtitles")
        gsub = QVBoxLayout(grp_sub)
        self.sub_enable = QCheckBox("Process Closed Captions")
        gsub.addWidget(self.sub_enable)
        self.sub_input = QLineEdit(); self.sub_input.setPlaceholderText("system defined file")
        self.sub_output = QLineEdit(); self.sub_output.setPlaceholderText("Merged output subtitle file")
        gsub.addLayout(field_row("Extract / Input File", self.sub_input, self._browse_sub_in))
        gsub.addLayout(field_row("Merge and Output File", self.sub_output, self._browse_sub_out))
        main.addWidget(grp_sub)

        # ── JOB META ──
        grp_job = QGroupBox("Job Settings")
        gjob = QVBoxLayout(grp_job)
        self.job_name = QLineEdit(); self.job_name.setPlaceholderText("Job name")
        self.job_priority = QComboBox(); self.job_priority.addItems(["Normal", "High", "Low"])
        gjob.addLayout(field_row("Job Name", self.job_name))
        gjob.addLayout(field_row("Job Priority", self.job_priority))
        main.addWidget(grp_job)

        main.addStretch()

        # ── BUTTONS ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_run = QPushButton("▶  CREATE JOB")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setFixedHeight(36)
        self.btn_clear = QPushButton("✕  CLEAR")
        self.btn_clear.setObjectName("btn_clear")
        self.btn_clear.setFixedHeight(36)
        btn_row.addWidget(self.btn_run)
        btn_row.addSpacing(12)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        main.addLayout(btn_row)

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        outer.addWidget(scroll)

        self.btn_clear.clicked.connect(self._clear)

    def _browse_video(self):
        f, _ = QFileDialog.getOpenFileName(self, "Input Video", "", "Video Files (*.mp4 *.mov *.mxf *.avi *.mkv);;All Files (*)")
        if f: self.inp_video.setText(f)
    def _browse_audio(self):
        f, _ = QFileDialog.getOpenFileName(self, "Input Audio", "", "Audio Files (*.wav *.aiff);;All Files (*)")
        if f: self.inp_audio.setText(f)
    def _browse_subs(self):
        f, _ = QFileDialog.getOpenFileName(self, "Input Subtitles", "", "Subtitle Files (*.srt *.stl);;All Files (*)")
        if f: self.inp_subs.setText(f)
    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "Output Folder")
        if d: self.out_path.setText(d)
    def _browse_sub_in(self):
        f, _ = QFileDialog.getOpenFileName(self, "Input Subtitle", "", "Subtitle Files (*.srt *.stl);;All Files (*)")
        if f: self.sub_input.setText(f)
    def _browse_sub_out(self):
        f, _ = QFileDialog.getSaveFileName(self, "Output Subtitle", "", "SRT (*.srt);;STL (*.stl)")
        if f: self.sub_output.setText(f)

    def _clear(self):
        for w in [self.inp_video, self.inp_audio, self.inp_subs,
                  self.out_path, self.out_name, self.job_name,
                  self.sub_input, self.sub_output]:
            w.clear()
        for tc in [self.tc_start, self.tc_stop, self.tc_target]:
            tc.setText("00:00:00:00")

    def get_params(self):
        return {
            "input_video":  self.inp_video.text(),
            "input_audio":  self.inp_audio.text(),
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
            "sub_input":    self.sub_input.text(),
            "sub_output":   self.sub_output.text(),
        }

# ─────────────────────────────────────────────
#  COMPRESSION PARAMS TAB
# ─────────────────────────────────────────────
class CompressionTab(QWidget):
    def __init__(self):
        super().__init__()
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        main = QVBoxLayout(inner); main.setSpacing(14); main.setContentsMargins(16,16,16,16)

        # ── AUDIO SKIPPY ──
        grp_as = QGroupBox("Audio Skippy — Time Compression Engine")
        gas = QGridLayout(grp_as); gas.setSpacing(8)

        params_skippy = [
            ("Target Ratio", "target_ratio", QDoubleSpinBox, (1.0, 1.1, 1.0129, 0.0001, 4)),
            ("Frame Ms", "frame_ms", QSpinBox, (1, 100, 5)),
            ("Max Chop Ms", "max_chop_ms", QSpinBox, (1, 100, 15)),
            ("Cadence Ms", "cadence_ms", QSpinBox, (10, 1000, 250)),
            ("Crossfade Ms", "crossfade_ms", QSpinBox, (0, 100, 10)),
            ("Energy Quantile", "energy_q", QDoubleSpinBox, (0.0, 1.0, 0.35, 0.01, 2)),
        ]
        self._skippy = {}
        for row, (label, key, wtype, args) in enumerate(params_skippy):
            lbl = QLabel(label + ":"); lbl.setObjectName("field_label")
            gas.addWidget(lbl, row, 0)
            if wtype == QDoubleSpinBox:
                w = QDoubleSpinBox()
                w.setRange(args[0], args[1]); w.setValue(args[2]); w.setSingleStep(args[3]); w.setDecimals(args[4])
            else:
                w = QSpinBox()
                w.setRange(args[0], args[1]); w.setValue(args[2])
            w.setFixedWidth(120)
            gas.addWidget(w, row, 1)
            desc_map = {
                "target_ratio": "Compression ratio (1.0129 = ~1.28%)",
                "frame_ms": "Analysis frame length in ms",
                "max_chop_ms": "Maximum silence chop in ms",
                "cadence_ms": "Cadence window in ms",
                "crossfade_ms": "Crossfade between chops in ms",
                "energy_q": "Energy quantile for silence detection",
            }
            hint = QLabel(desc_map.get(key, ""))
            hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
            gas.addWidget(hint, row, 2)
            self._skippy[key] = w
        gas.setColumnStretch(2, 1)
        main.addWidget(grp_as)

        # ── DTW VIDEO ──
        grp_dtw = QGroupBox("DTW Video Compressor")
        gdtw = QGridLayout(grp_dtw); gdtw.setSpacing(8)

        params_dtw = [
            ("Target SR", "target_sr", QSpinBox, (8000, 48000, 16000)),
            ("N Mels", "n_mels", QSpinBox, (16, 256, 64)),
            ("Hop Length", "hop", QSpinBox, (256, 8192, 2048)),
            ("Time Decim", "time_decim", QSpinBox, (1, 8, 2)),
            ("Max Jump Ratio", "max_jump", QDoubleSpinBox, (1.0, 3.0, 1.2, 0.05, 2)),
            ("Output FPS", "out_fps", QDoubleSpinBox, (23.0, 120.0, 59.94, 0.01, 3)),
        ]
        self._dtw = {}
        for row, (label, key, wtype, args) in enumerate(params_dtw):
            lbl = QLabel(label + ":"); lbl.setObjectName("field_label")
            gdtw.addWidget(lbl, row, 0)
            if wtype == QDoubleSpinBox:
                w = QDoubleSpinBox()
                w.setRange(args[0], args[1]); w.setValue(args[2]); w.setSingleStep(args[3]); w.setDecimals(args[4])
            else:
                w = QSpinBox()
                w.setRange(args[0], args[1]); w.setValue(args[2])
            w.setFixedWidth(120)
            gdtw.addWidget(w, row, 1)
            self._dtw[key] = w
        gdtw.setColumnStretch(2, 1)
        main.addWidget(grp_dtw)

        main.addStretch()
        scroll.setWidget(inner)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(scroll)

    def get_params(self):
        return {k: w.value() for k, w in {**self._skippy, **self._dtw}.items()}

# ─────────────────────────────────────────────
#  FRAME BLEND EDITOR TAB
# ─────────────────────────────────────────────
class FrameBlendTab(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self); main.setSpacing(14); main.setContentsMargins(16,16,16,16)

        main.addWidget(section_header("Frame Blending / Smear Settings"))

        grp = QGroupBox("Blend Engine")
        g = QVBoxLayout(grp); g.setSpacing(10)

        self.blend_enable = QCheckBox("Enable Frame Blending (micro-smear)")
        self.blend_enable.setChecked(True)
        g.addWidget(self.blend_enable)
        g.addWidget(divider())

        def make_slider_row(label, mn, mx, val, scale=1, decimals=0):
            row = QHBoxLayout()
            lbl = QLabel(label + ":"); lbl.setObjectName("field_label"); lbl.setFixedWidth(160)
            row.addWidget(lbl)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(int(mn*scale), int(mx*scale)); sl.setValue(int(val*scale))
            row.addWidget(sl, 1)
            disp = QLabel(f"{val}" if decimals==0 else f"{val:.{decimals}f}")
            disp.setFixedWidth(60)
            disp.setStyleSheet(f"color: {ACCENT_GREEN}; font-family: '{MONO_FONT}'; font-size: 12px;")
            row.addWidget(disp)
            def on_change(v, d=disp, sc=scale, dec=decimals):
                real = v/sc
                d.setText(f"{real}" if dec==0 else f"{real:.{dec}f}")
            sl.valueChanged.connect(on_change)
            return row, sl, disp

        r1, self.sl_blend_every, self.lbl_blend_every = make_slider_row("Blend Every N Frames", 1, 120, 20)
        r2, self.sl_blend_alpha, self.lbl_blend_alpha = make_slider_row("Blend Alpha", 0, 1, 0.50, scale=100, decimals=2)
        r3, self.sl_smear_ms,    self.lbl_smear_ms    = make_slider_row("Smear Duration (ms)", 1, 200, 32)
        g.addLayout(r1); g.addLayout(r2); g.addLayout(r3)

        main.addWidget(grp)

        # blend mode
        grp2 = QGroupBox("Blend Mode")
        g2 = QVBoxLayout(grp2); g2.setSpacing(8)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:")); mode_row.setSpacing(8)
        self.blend_mode = QComboBox()
        self.blend_mode.addItems(["Forward Smear (default)", "Backward Smear", "Bilateral (avg prev+next)", "Motion Adaptive"])
        self.blend_mode.setFixedWidth(220)
        mode_row.addWidget(self.blend_mode); mode_row.addStretch()
        g2.addLayout(mode_row)

        self.blend_motion = QCheckBox("Motion-Compensated Blend (slower, cleaner on fast motion)")
        g2.addWidget(self.blend_motion)
        main.addWidget(grp2)

        # preview hint
        hint = QLabel("💡 Tip: Use the Preview tab to compare blend on/off before running the full compression job.")
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; padding: 8px; background: {BG_PANEL}; border: 1px solid {BORDER}; border-radius: 4px;")
        hint.setWordWrap(True)
        main.addWidget(hint)
        main.addStretch()

    def get_params(self):
        return {
            "blend_enable": self.blend_enable.isChecked(),
            "blend_every":  self.sl_blend_every.value(),
            "blend_alpha":  self.sl_blend_alpha.value() / 100.0,
            "smear_ms":     self.sl_smear_ms.value(),
            "blend_mode":   self.blend_mode.currentText(),
            "motion_comp":  self.blend_motion.isChecked(),
        }

# ─────────────────────────────────────────────
#  VIDEO EDITOR TAB  (pre-compression edits)
# ─────────────────────────────────────────────
class EditorTab(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self); main.setSpacing(12); main.setContentsMargins(16,16,16,16)

        main.addWidget(section_header("Pre-Compression Editor"))

        # preview area
        self.preview = QLabel("No video loaded — browse a file in the Job tab first")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet(f"background: #000; color: {TEXT_MUTED}; border: 1px solid {BORDER}; font-size: 13px;")
        self.preview.setMinimumHeight(260)
        main.addWidget(self.preview, 1)

        # playback controls
        ctrl = QHBoxLayout()
        for label, tip in [("⏮", "Go to start"), ("⏪", "Back 10s"), ("▶ / ⏸", "Play/Pause"), ("⏩", "Fwd 10s"), ("⏭", "Go to end")]:
            b = QPushButton(label); b.setToolTip(tip); b.setFixedSize(40, 32)
            ctrl.addWidget(b)
        ctrl.addSpacing(12)
        self.tc_display = QLabel("00:00:00:00")
        self.tc_display.setStyleSheet(f"font-family: '{MONO_FONT}'; font-size: 16px; color: {ACCENT_GREEN}; background: {BG_FIELD}; padding: 4px 12px; border: 1px solid {BORDER}; border-radius: 3px;")
        ctrl.addWidget(self.tc_display)
        ctrl.addStretch()
        main.addLayout(ctrl)

        # scrub bar
        self.scrub = QSlider(Qt.Horizontal)
        self.scrub.setRange(0, 1000)
        main.addWidget(self.scrub)

        # ── TRIM ──
        grp_trim = QGroupBox("Trim / Cut")
        gt = QGridLayout(grp_trim); gt.setSpacing(8)
        for col, label in enumerate(["Point", "Timecode", "Action"]):
            l = QLabel(label); l.setStyleSheet(f"color: {TEXT_LABEL}; font-weight: 700; font-size: 11px;")
            gt.addWidget(l, 0, col)
        self.trim_in  = QLineEdit("00:00:00:00"); self.trim_in.setFixedWidth(120)
        self.trim_out = QLineEdit("00:00:00:00"); self.trim_out.setFixedWidth(120)
        gt.addWidget(QLabel("In Point:"),  1, 0)
        gt.addWidget(self.trim_in,         1, 1)
        btn_set_in = QPushButton("Set In at Playhead"); gt.addWidget(btn_set_in, 1, 2)
        gt.addWidget(QLabel("Out Point:"), 2, 0)
        gt.addWidget(self.trim_out,        2, 1)
        btn_set_out = QPushButton("Set Out at Playhead"); gt.addWidget(btn_set_out, 2, 2)
        main.addWidget(grp_trim)

        # ── COLOR / BRIGHTNESS ──
        grp_col = QGroupBox("Color / Brightness Adjustments")
        gc = QVBoxLayout(grp_col); gc.setSpacing(8)

        def color_row(label, default=0, mn=-100, mx=100):
            row = QHBoxLayout()
            lbl = QLabel(label+":"); lbl.setObjectName("field_label"); lbl.setFixedWidth(130)
            row.addWidget(lbl)
            sl = QSlider(Qt.Horizontal); sl.setRange(mn, mx); sl.setValue(default)
            row.addWidget(sl, 1)
            val = QLabel(str(default)); val.setFixedWidth(40)
            val.setStyleSheet(f"color:{ACCENT_GREEN};font-family:'{MONO_FONT}';")
            sl.valueChanged.connect(lambda v, d=val: d.setText(str(v)))
            row.addWidget(val)
            rst = QPushButton("Reset"); rst.setFixedWidth(56)
            rst.clicked.connect(lambda _, s=sl, dv=default: s.setValue(dv))
            row.addWidget(rst)
            gc.addLayout(row)
            return sl

        self.sl_brightness = color_row("Brightness", 0, -100, 100)
        self.sl_contrast   = color_row("Contrast",   0, -100, 100)
        self.sl_saturation = color_row("Saturation", 0, -100, 100)
        self.sl_gamma      = color_row("Gamma",      0, -50,   50)
        main.addWidget(grp_col)

        # ── AUDIO LEVEL ──
        grp_aud = QGroupBox("Audio Level")
        ga = QVBoxLayout(grp_aud); ga.setSpacing(8)

        aud_row = QHBoxLayout()
        aud_row.addWidget(QLabel("Master Gain (dB):")); aud_row.setSpacing(8)
        self.sl_gain = QSlider(Qt.Horizontal); self.sl_gain.setRange(-24, 24); self.sl_gain.setValue(0)
        self.lbl_gain = QLabel("0 dB")
        self.lbl_gain.setStyleSheet(f"color:{ACCENT_GREEN};font-family:'{MONO_FONT}';")
        self.sl_gain.valueChanged.connect(lambda v: self.lbl_gain.setText(f"{v:+d} dB"))
        aud_row.addWidget(self.sl_gain, 1)
        aud_row.addWidget(self.lbl_gain)
        ga.addLayout(aud_row)

        norm_row = QHBoxLayout()
        self.chk_normalize = QCheckBox("Normalize audio to -23 LUFS (EBU R128)")
        norm_row.addWidget(self.chk_normalize)
        self.chk_limiter   = QCheckBox("Apply true peak limiter (-1 dBTP)")
        norm_row.addWidget(self.chk_limiter)
        norm_row.addStretch()
        ga.addLayout(norm_row)
        main.addWidget(grp_aud)

    def get_params(self):
        return {
            "trim_in":     self.trim_in.text(),
            "trim_out":    self.trim_out.text(),
            "brightness":  self.sl_brightness.value(),
            "contrast":    self.sl_contrast.value(),
            "saturation":  self.sl_saturation.value(),
            "gamma":       self.sl_gamma.value(),
            "gain_db":     self.sl_gain.value(),
            "normalize":   self.chk_normalize.isChecked(),
            "limiter":     self.chk_limiter.isChecked(),
        }

# ─────────────────────────────────────────────
#  PREVIEW TAB
# ─────────────────────────────────────────────
class PreviewTab(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self); main.setSpacing(10); main.setContentsMargins(16,16,16,16)

        main.addWidget(section_header("Video Preview"))

        split = QHBoxLayout()

        # A/B panels
        for side, label in [("before", "ORIGINAL"), ("after", "COMPRESSED")]:
            panel = QVBoxLayout()
            hdr = QLabel(label)
            color = ACCENT_BLUE if side=="before" else ACCENT_GREEN
            hdr.setStyleSheet(f"color:{color};font-weight:700;font-size:12px;letter-spacing:2px;padding:4px 0;border-bottom:1px solid {BORDER};")
            panel.addWidget(hdr)
            pv = QLabel("Load a file to preview")
            pv.setAlignment(Qt.AlignCenter)
            pv.setStyleSheet(f"background:#000;color:{TEXT_MUTED};border:1px solid {BORDER};font-size:12px;")
            pv.setMinimumHeight(240)
            panel.addWidget(pv, 1)
            setattr(self, f"pv_{side}", pv)
            tc = QLabel("00:00:00:00")
            tc.setAlignment(Qt.AlignCenter)
            tc.setStyleSheet(f"font-family:'{MONO_FONT}';font-size:14px;color:{color};background:{BG_FIELD};border:1px solid {BORDER};padding:3px;")
            panel.addWidget(tc)
            split.addLayout(panel)

        main.addLayout(split, 1)

        # linked scrub
        linked_row = QHBoxLayout()
        self.chk_linked = QCheckBox("Linked scrub (A/B sync)")
        self.chk_linked.setChecked(True)
        linked_row.addWidget(self.chk_linked)
        linked_row.addStretch()
        main.addLayout(linked_row)

        self.scrub = QSlider(Qt.Horizontal)
        self.scrub.setRange(0, 1000)
        main.addWidget(self.scrub)

        ctrl = QHBoxLayout()
        for label in ["⏮", "⏪", "▶ / ⏸", "⏩", "⏭"]:
            b = QPushButton(label); b.setFixedSize(40, 32)
            ctrl.addWidget(b)
        ctrl.addStretch()

        self.chk_blend_preview = QCheckBox("Show blend overlay")
        ctrl.addWidget(self.chk_blend_preview)
        main.addLayout(ctrl)

        # stats bar
        stats = QHBoxLayout()
        for label, val, color in [("Original Duration", "00:10:00:00", TEXT_PRIMARY),
                                   ("Compressed Duration", "—", ACCENT_GREEN),
                                   ("Time Saved", "—", ACCENT_GOLD),
                                   ("Compression %", "—", ACCENT_BLUE)]:
            box = QVBoxLayout()
            l1 = QLabel(label); l1.setStyleSheet(f"color:{TEXT_MUTED};font-size:10px;letter-spacing:1px;")
            l2 = QLabel(val); l2.setStyleSheet(f"color:{color};font-family:'{MONO_FONT}';font-size:15px;font-weight:700;")
            box.addWidget(l1); box.addWidget(l2)
            stats.addLayout(box)
            stats.addSpacing(24)
        stats.addStretch()
        main.addLayout(stats)

# ─────────────────────────────────────────────
#  LOG / PROGRESS TAB
# ─────────────────────────────────────────────
class LogTab(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self); main.setSpacing(10); main.setContentsMargins(16,16,16,16)

        main.addWidget(section_header("Job Progress"))

        # progress bars
        grp = QGroupBox("Pipeline Steps")
        g = QVBoxLayout(grp); g.setSpacing(8)

        self.bars = {}
        steps = [
            ("Audio Skippy",    "audio_skippy"),
            ("DTW Analysis",    "dtw"),
            ("Frame Rendering", "render"),
            ("Audio Mux",       "mux"),
            ("Subtitle Retime", "subs"),
        ]
        for label, key in steps:
            row = QHBoxLayout()
            lbl = QLabel(label+":"); lbl.setFixedWidth(140); lbl.setObjectName("field_label")
            row.addWidget(lbl)
            bar = QProgressBar(); bar.setValue(0); bar.setFixedHeight(18)
            row.addWidget(bar, 1)
            status = QLabel("Waiting"); status.setFixedWidth(80)
            status.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;")
            row.addWidget(status)
            g.addLayout(row)
            self.bars[key] = (bar, status)

        main.addWidget(grp)

        # overall
        overall_row = QHBoxLayout()
        overall_row.addWidget(QLabel("Overall:"))
        self.overall_bar = QProgressBar(); self.overall_bar.setValue(0)
        overall_row.addWidget(self.overall_bar, 1)
        self.overall_label = QLabel("Idle")
        self.overall_label.setStyleSheet(f"color:{ACCENT_GREEN};font-weight:700;")
        overall_row.addWidget(self.overall_label)
        main.addLayout(overall_row)

        main.addWidget(divider())

        # log output
        main.addWidget(section_header("Console Output"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont(MONO_FONT, 10))
        self.log.setStyleSheet(f"background:{BG_FIELD};color:{TEXT_PRIMARY};border:1px solid {BORDER};")
        self.log.setMinimumHeight(180)
        main.addWidget(self.log, 1)

        btn_row = QHBoxLayout()
        self.btn_clear_log = QPushButton("Clear Log")
        self.btn_clear_log.clicked.connect(self.log.clear)
        btn_row.addWidget(self.btn_clear_log)
        btn_row.addStretch()
        main.addLayout(btn_row)

    def append(self, text, color=None):
        if color:
            self.log.append(f'<span style="color:{color}">{text}</span>')
        else:
            self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def set_step(self, key, pct, status_text, color=None):
        if key in self.bars:
            bar, lbl = self.bars[key]
            bar.setValue(pct)
            lbl.setText(status_text)
            if color: lbl.setStyleSheet(f"color:{color};font-size:11px;font-weight:600;")

    def set_overall(self, pct, text):
        self.overall_bar.setValue(pct)
        self.overall_label.setText(text)

# ─────────────────────────────────────────────
#  JOB RUNNER THREAD
# ─────────────────────────────────────────────
class JobRunner(QThread):
    log_signal    = pyqtSignal(str, str)
    step_signal   = pyqtSignal(str, int, str, str)
    overall_signal= pyqtSignal(int, str)
    done_signal   = pyqtSignal(bool, str)

    def __init__(self, job_params, comp_params, blend_params, edit_params, script_dir):
        super().__init__()
        self.job    = job_params
        self.comp   = comp_params
        self.blend  = blend_params
        self.edit   = edit_params
        self.script_dir = script_dir

    def run(self):
        try:
            self._run_pipeline()
        except Exception as ex:
            self.log_signal.emit(f"❌ Fatal error: {ex}", "#e74c3c")
            self.done_signal.emit(False, str(ex))

    def _run_pipeline(self):
        j = self.job; c = self.comp; b = self.blend; e = self.edit
        out_video = os.path.join(j["output_path"], j["output_name"] + "_tc.mp4")
        skippy_wav = os.path.join(j["output_path"], j["output_name"] + "_heavy.wav")
        temp_video  = os.path.join(j["output_path"], j["output_name"] + "_temp.mp4")

        # STEP 0: Audio Skippy
        self.step_signal.emit("audio_skippy", 0, "Running…", ACCENT_GOLD)
        self.overall_signal.emit(5, "Audio compression…")
        audio_skippy_script = os.path.join(self.script_dir, "audio_skippy_SURROUND.py")
        cmd0 = [
            sys.executable, audio_skippy_script,
            "-i", j["input_audio"], "-o", skippy_wav,
            "--target-ratio", str(c["target_ratio"]),
            "--frame-ms", str(int(c["frame_ms"])),
            "--max-chop-ms", str(int(c["max_chop_ms"])),
            "--cadence-ms", str(int(c["cadence_ms"])),
            "--crossfade-ms", str(int(c["crossfade_ms"])),
            "--energy-quantile", str(c["energy_q"]),
        ]
        ret = self._run(cmd0)
        if ret != 0:
            self.step_signal.emit("audio_skippy", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "audio_skippy failed"); return
        self.step_signal.emit("audio_skippy", 100, "Done ✓", ACCENT_GREEN)
        self.overall_signal.emit(25, "DTW analysis…")

        # STEP 1: Video compressor
        self.step_signal.emit("dtw", 0, "Running…", ACCENT_GOLD)
        tc_script = os.path.join(self.script_dir, "time_compressor_SAFE.py")
        cmd1 = [sys.executable, tc_script, "-i", j["input_video"], "-s", skippy_wav, "-o", temp_video]
        ret = self._run(cmd1)
        if ret != 0:
            self.step_signal.emit("dtw", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "DTW compressor failed"); return
        self.step_signal.emit("dtw", 100, "Done ✓", ACCENT_GREEN)
        self.step_signal.emit("render", 100, "Done ✓", ACCENT_GREEN)
        self.overall_signal.emit(70, "Muxing audio…")

        # STEP 2: Mux
        self.step_signal.emit("mux", 0, "Running…", ACCENT_GOLD)
        cmd2 = [
            "ffmpeg", "-y", "-i", temp_video, "-i", skippy_wav,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "640k",
            out_video
        ]
        ret = self._run(cmd2)
        if ret != 0:
            self.step_signal.emit("mux", 100, "FAILED", ACCENT_RED)
            self.done_signal.emit(False, "Mux failed"); return
        self.step_signal.emit("mux", 100, "Done ✓", ACCENT_GREEN)
        self.overall_signal.emit(88, "Subtitle retime…")

        # STEP 3: Subtitles
        if j["sub_enable"] and j["sub_input"]:
            self.step_signal.emit("subs", 0, "Running…", ACCENT_GOLD)
            map_file = os.path.join(j["output_path"], "map_t_skip_to_t_orig.npy")
            sub_script = os.path.join(self.script_dir, "subtitle_retime.py")
            cmd3 = [sys.executable, sub_script, "-i", j["sub_input"], "-o", j["sub_output"], "-m", map_file]
            ret = self._run(cmd3)
            if ret != 0:
                self.step_signal.emit("subs", 100, "FAILED", ACCENT_RED)
            else:
                self.step_signal.emit("subs", 100, "Done ✓", ACCENT_GREEN)
        else:
            self.step_signal.emit("subs", 100, "Skipped", TEXT_MUTED)

        # cleanup temp
        try: os.remove(temp_video)
        except: pass

        self.overall_signal.emit(100, "Complete ✓")
        self.done_signal.emit(True, out_video)

    def _run(self, cmd):
        self.log_signal.emit("$ " + " ".join(cmd), ACCENT_BLUE)
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                self.log_signal.emit(line.rstrip(), None)
            proc.wait()
            return proc.returncode
        except FileNotFoundError as ex:
            self.log_signal.emit(f"⚠ Could not launch: {ex}", ACCENT_GOLD)
            return 1

# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────
class TempoCut(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TempoCut v1.0 — Broadcast Time Compression Suite")
        self.setMinimumSize(1000, 720)
        self.resize(1160, 800)
        self.setStyleSheet(STYLESHEET)

        # Script directory (same folder as this file)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        root.addWidget(HeaderWidget())

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tab_job    = JobTab(config={})
        self.tab_comp   = CompressionTab()
        self.tab_blend  = FrameBlendTab()
        self.tab_editor = EditorTab()
        self.tab_preview= PreviewTab()
        self.tab_log    = LogTab()

        self.tabs.addTab(self.tab_job,     "Job")
        self.tabs.addTab(self.tab_comp,    "Compression")
        self.tabs.addTab(self.tab_blend,   "Frame Blend")
        self.tabs.addTab(self.tab_editor,  "Editor")
        self.tabs.addTab(self.tab_preview, "Preview")
        self.tabs.addTab(self.tab_log,     "Log / Progress")

        root.addWidget(self.tabs, 1)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("TempoCut ready.  |  Set input files and click CREATE JOB to begin.")

        # Wire run button
        self.tab_job.btn_run.clicked.connect(self._run_job)
        self.tab_job.btn_clear.clicked.connect(self._clear_all)

        self._runner = None

    def _run_job(self):
        jp = self.tab_job.get_params()
        if not jp["input_video"]:
            QMessageBox.warning(self, "Missing Input", "Please specify an input video file.")
            return
        if not jp["input_audio"]:
            QMessageBox.warning(self, "Missing Input", "Please specify an input audio (WAV) file.")
            return
        if not jp["output_path"]:
            QMessageBox.warning(self, "Missing Output", "Please specify an output folder.")
            return
        if not jp["output_name"]:
            jp["output_name"] = os.path.splitext(os.path.basename(jp["input_video"]))[0] + "_TC"

        cp = self.tab_comp.get_params()
        bp = self.tab_blend.get_params()
        ep = self.tab_editor.get_params()

        # Reset log
        for key, (bar, lbl) in self.tab_log.bars.items():
            bar.setValue(0)
            lbl.setText("Waiting")
            lbl.setStyleSheet(f"color:{TEXT_MUTED};font-size:11px;")
        self.tab_log.set_overall(0, "Starting…")
        self.tab_log.log.clear()
        self.tabs.setCurrentWidget(self.tab_log)

        self._runner = JobRunner(jp, cp, bp, ep, self.script_dir)
        self._runner.log_signal.connect(lambda msg, col: self.tab_log.append(msg, col))
        self._runner.step_signal.connect(lambda k, p, s, c: self.tab_log.set_step(k, p, s, c))
        self._runner.overall_signal.connect(lambda p, t: self.tab_log.set_overall(p, t))
        self._runner.done_signal.connect(self._on_done)
        self._runner.start()
        self.status.showMessage(f"Running job: {jp.get('job_name') or jp['output_name']} …")
        self.tab_job.btn_run.setEnabled(False)

    def _on_done(self, success, msg):
        self.tab_job.btn_run.setEnabled(True)
        if success:
            self.status.showMessage(f"✅ Job complete: {msg}")
            QMessageBox.information(self, "TempoCut", f"Job complete!\n\nOutput: {msg}")
        else:
            self.status.showMessage(f"❌ Job failed: {msg}")
            QMessageBox.critical(self, "TempoCut", f"Job failed:\n{msg}")

    def _clear_all(self):
        self.tab_job._clear()
        self.tab_log.log.clear()
        self.tab_log.set_overall(0, "Idle")
        for key in self.tab_log.bars:
            self.tab_log.set_step(key, 0, "Waiting", TEXT_MUTED)
        self.status.showMessage("Cleared.")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Fusion dark palette base (our stylesheet overrides most)
    pal = QPalette()
    pal.setColor(QPalette.Window,          QColor(BG_DARK))
    pal.setColor(QPalette.WindowText,      QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Base,            QColor(BG_FIELD))
    pal.setColor(QPalette.AlternateBase,   QColor(BG_MID))
    pal.setColor(QPalette.Text,            QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Button,          QColor(BG_MID))
    pal.setColor(QPalette.ButtonText,      QColor(TEXT_PRIMARY))
    pal.setColor(QPalette.Highlight,       QColor(ACCENT_BLUE))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)

    win = TempoCut()
    win.show()
    sys.exit(app.exec_())
