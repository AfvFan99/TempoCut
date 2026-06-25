# tempocut.spec
# Build with:  pyinstaller tempocut.spec
#
# This bundles tempocut_v2.py into a single-folder Windows app, and copies
# the companion scripts (audio_skippy_SURROUND.py, time_compressor_SAFE_v2.py,
# subtitle_retime.py) alongside the exe so subprocess calls can find them.
#
# Requires: pip install pyinstaller

import os
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.datastruct import Tree

block_cipher = None

# ── Adjust these paths if your scripts live elsewhere ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(SPEC))

companion_scripts = [
    "audio_skippy_SURROUND.py",
    "time_compressor_CUTLIST.py",
    "subtitle_retime.py",
]

# Runtime window/taskbar icon (set via setWindowIcon() in tempocut_v2.py).
# Bundled the same way as the companion scripts above so it's always
# present in dist/ after a build, instead of relying on a manual copy.
companion_assets = [
    "tempocut_icon_256.png",
    "ffmpeg.exe",   # optional: only bundled if actually present at build time.
    "ffprobe.exe",  # find_binary() in tempocut_v2.py falls back to system
                     # PATH if these aren't here, but bundling them removes
                     # the dependency on the user having ffmpeg installed
                     # separately at all.
]

datas = []
for script in companion_scripts + companion_assets:
    src = os.path.join(SCRIPT_DIR, script)
    if os.path.exists(src):
        datas.append((src, "."))

# Optional: a complete, portable copy of a real, working Python install
# (python.exe + Lib/ + Lib/site-packages/ with numpy/scipy/librosa/cv2/etc
# already installed and PROVEN working). If present at build time, this
# gets bundled wholesale and used by tempocut_v2.py as a real external
# interpreter for the companion scripts -- sidestepping PyInstaller's own
# frozen-import path entirely, which is what's actually been buggy (the
# scipy.stats NameError), not the packages themselves.
#
# To create this folder: copy your entire working Python install
# (e.g. C:\Users\you\AppData\Local\Programs\Python\Python312) into
# SCRIPT_DIR\embedded_python\ before running this build. Whatever's in
# that folder's Lib\site-packages\ is exactly what TempoCut will run the
# companion scripts with on every machine this installer goes to.
embedded_python_dir = os.path.join(SCRIPT_DIR, "embedded_python")
extra_trees = []
if os.path.isdir(embedded_python_dir):
    extra_trees.append(Tree(embedded_python_dir, prefix="embedded_python"))

# scipy.stats builds its distribution classes dynamically at import time
# (_distn_infrastructure.py). The default PyInstaller scipy hook doesn't
# always capture this correctly across scipy versions, which is what
# causes "NameError: name 'obj' is not defined" deep inside a frozen
# build -- librosa pulls in scipy.stats indirectly, so this bites even
# though nothing in TempoCut's own code imports scipy.stats directly.
hidden_scipy = [
    m for m in (
        collect_submodules("scipy.stats")
        + collect_submodules("scipy.special")
        + collect_submodules("scipy.signal")
        + collect_submodules("scipy._lib")
    )
    if ".tests" not in m  # exclude scipy's own internal test suites -- bloat, never needed at runtime
]

a = Analysis(
    ["tempocut_v2.py"],
    pathex=[SCRIPT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "cv2",
        "numpy",
        "librosa",
        "librosa.sequence",
        "scipy",
        "soundfile",
        "pysubs2",
    ] + hidden_scipy,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True,  # experiment: workaround attempt for the scipy.stats
                     # frozen-import NameError ('obj' is not defined) --
                     # stores modules as individual .pyc files instead of
                     # packed into one archive. Revert to False if this
                     # doesn't help or causes other issues.
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TempoCut",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # set True temporarily if you need to see crash tracebacks
    icon=os.path.join(SCRIPT_DIR, "tempocut.ico"),
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    *extra_trees,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TempoCut",
)
