# Building TempoCut.exe + Installer

This turns TempoCut into a real downloadable Windows app: `TempoCut_Setup.exe`,
which installs TempoCut.exe + a Start Menu shortcut + a desktop icon, just like
any normal Windows software.

## Folder layout (put all of these in ONE folder before building)

```
TempoCut\
├── tempocut_v2.py
├── audio_skippy_SURROUND.py
├── time_compressor_SAFE_v2.py
├── subtitle_retime.py
├── tempocut.spec
└── TempoCut.iss
```

## Step 1 — Install build tools (one-time)

```
pip install pyinstaller
```

Also install **Inno Setup 6** (free): https://jrsoftware.org/isinfo.php
Just run the installer, defaults are fine.

## Step 2 — Build the app folder with PyInstaller

From inside the `TempoCut\` folder:

```
pyinstaller tempocut.spec
```

This takes a few minutes. When it's done you'll have:

```
TempoCut\dist\TempoCut\TempoCut.exe   <- the actual app, plus all its dependencies
```

You can already double-click `TempoCut.exe` at this point and it'll run —
no Python install needed on whatever machine you copy that folder to.

## Step 3 — Build the installer with Inno Setup

Option A — GUI:
1. Open Inno Setup Compiler
2. File → Open → select `TempoCut.iss`
3. Click the green ▶ Compile button

Option B — command line:
```
iscc TempoCut.iss
```

Either way, you'll get:

```
TempoCut\Output\TempoCut_Setup.exe
```

**That's the file you share.** Anyone can double-click it, click through the
install wizard, and get a working TempoCut shortcut on their desktop and in
their Start Menu — no Python, no pip, no terminal.

## Important: ffmpeg is still required

TempoCut shells out to `ffmpeg` and `ffprobe` for audio extraction, muxing,
and source-codec detection. PyInstaller bundles your Python code and
libraries, but it does **not** bundle ffmpeg automatically.

The installer checks for ffmpeg on PATH and warns the user if it's missing,
but you have two real options for distribution:

**Option A (simplest for you):** tell whoever installs it to grab ffmpeg
from https://ffmpeg.org/download.html and add it to PATH once.

**Option B (zero-setup for them):** download a static `ffmpeg.exe` and
`ffprobe.exe` build, drop them in the same `TempoCut\` folder as your scripts
before running Step 2, and add this line to `tempocut.spec`'s `companion_scripts`
list... actually simpler — just add this to the `[Files]` section of
`TempoCut.iss`:

```
Source: "ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion
```

Then update `tempocut_v2.py`'s subprocess calls to use the bundled exe path
instead of relying on PATH — happy to wire that up if you want the fully
zero-setup version.

## Re-building after future code changes

Every time you update `tempocut_v2.py` or the companion scripts, just re-run:

```
pyinstaller tempocut.spec
iscc TempoCut.iss
```

and a fresh `TempoCut_Setup.exe` pops out.

## Optional: custom icon

Make or download a `.ico` file, name it `tempocut.ico`, drop it in the same
folder, then uncomment these two lines:

- in `tempocut.spec`: `icon="tempocut.ico"`
- in `TempoCut.iss`: `SetupIconFile=tempocut.ico`

Rebuild and your installer + app will use that icon everywhere.
