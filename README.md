# TempoCut

**Broadcast-style video & audio time compression — recreate the classic "time tailoring" used by TBS, TNT, TruTV, Cartoon Network, and Adult Swim.**
*Not affiliated with Warner Bros. Discovery or Prime Image. Educational use only.*

---

## Overview

TempoCut is a Python toolkit (with a full PyQt5 GUI) that mimics professional broadcast time compression systems like Prime Image's Time Tailor. It shortens video to fit a target time slot while keeping tight A/V sync, using a redundancy-based "skippy" approach: short, low-energy/low-motion moments are found in the audio and video and either cut out entirely or sped through, rather than uniformly speeding up the whole timeline.

The audio engine analyzes 5.1/stereo audio for quiet, redundant moments using joint audio+video motion detection, producing an exact cut list. Video compression then has **two selectable modes** built on that same cut list:

- **Cut mode** — removes each redundant window entirely, with a crossfade at the cut boundary. This is the classic Time Tailor approach: sparse, exact cuts with a brief blend right at the seam.
- **Blend-Through mode** — never deletes a frame. Instead, it plays faster through each redundant window by cross-blending neighboring frames (the "1 2 3 [blend] 1 2 [blend]" cadence), which can look smoother on some content. Automatically widens windows when needed to guarantee enough room for the blend to be visible and to hit the requested duration exactly, even when the natural redundancy found is smaller than the requested compression.

Subtitle alignment retimes SRT/STL/SCC cues to stay in sync with the compressed timeline.

---

## Features

- Broadcast-accurate time compression for **audio + video**, with joint audio+video redundancy detection (cuts only land where both audio is quiet *and* video is visually static)
- Two video compression modes: **Cut** (classic hard-cut + crossfade) and **Blend-Through** (frame-blended speed-through, nothing dropped)
- Five built-in Skippy presets (Gentle, Light, Balanced, Heavy, Extreme) plus a continuous **Auto** mode that tunes parameters smoothly across the full range, or full manual control
- Exact-sync guarantee: video duration is computed directly from audio's true (crossfade-inclusive) duration reduction — no DTW re-discovery, no drift
- Full PyQt5 GUI (`tempocut_v2.py`) with live progress bars, a render-position scrubber, pause/resume, and an Editor tab for trim/color/audio gain before compression
- Subtitle retiming via exact warp maps
- Windows installer build (PyInstaller + Inno Setup)

---

## Requirements

**Python:** 3.10+

```
pip install -r requirements.txt
```

**Also required:**
- **FFmpeg** and **ffprobe** in your PATH (or bundled alongside the built `.exe`)

---

## Usage

### GUI (recommended)

```
python tempocut_v2.py
```

Load a video in the **Job** tab, choose a Skippy preset and Target Ratio in **Compression**, pick **Cut** or **Blend-Through** mode in **Frame Blend**, and hit Run. Progress, including a render-position scrubber, is shown live in the **Log / Progress** tab.

### Command-line / scripted pipeline

TempoCut's pipeline has three stages, each runnable standalone:

**1. Audio compression** — finds redundant windows and writes the exact cut list:

```
python audio_skippy_SURROUND.py -i "input.wav" -o "output.wav" --target-ratio 1.02 --video "input.mp4"
```

This produces `output_cutlist.csv` (exact start/end/crossfade per cut, used by both video modes below) and a `*_markers.txt` file for reference in an NLE.

**2. Video compression** — pick one mode:

Cut mode (hard cut + boundary crossfade):
```
python time_compressor_CUTLIST.py -i "input.mp4" --cutlist "output_cutlist.csv" -o "out.mp4" --blend-width 0.33
```

Blend-Through mode (frame-blended speed-through, nothing dropped):
```
python time_compressor_BLENDTHROUGH.py -i "input.mp4" --cutlist "output_cutlist.csv" -o "out.mp4" --window-blend 0.75 --audio-duration 81.84
```

**3. Subtitle alignment** (optional) — retimes SRT/STL/SCC cues using the warp map produced by either video script above:

```
python subtitle_retime.py map_t_skip_to_t_orig.npy input.srt output.srt
```

---

## Audio Compression Parameters

```
python audio_skippy_SURROUND.py ^
 -i "input.wav" ^
 -o "output.wav" ^
 --target-ratio 1.02 ^
 --frame-ms 15 ^
 --max-chop-ms 35 ^
 --cadence-ms 250 ^
 --crossfade-ms 6 ^
 --energy-quantile 0.5 ^
 --video "input.mp4"
```

- `--target-ratio` ≈ total shortening (e.g., `1.02` ≈ 2% shorter)
- `--video` enables joint audio+video redundancy detection — cuts only land where audio is quiet *and* video is static
- Smaller `--frame-ms` / `--cadence-ms` = tighter sync, more frequent cuts
- Larger values = smoother, lighter compression
- These map directly to the GUI's Gentle/Light/Balanced/Heavy/Extreme presets — see `tempocut_v2.py`'s `CompressionTab.SKIPPY_PRESETS` for exact values

---

## Blend-Through Mode Notes

Blend-Through reads the same cut list as Cut mode but treats each window as a "speed through" zone instead of a deletion:

- `--window-blend` (0–1) controls how strongly neighboring frames are cross-blended within a window. 0 = hard frame-skip (faster playback, no blending); 1 = maximal blend.
- `--audio-duration` should be the actual measured duration of the compressed audio output, so video duration matches it exactly. If omitted, it's estimated from the cutlist alone.
- Windows are automatically widened (borrowing time from surrounding footage, capped per-side) when the natural redundancy found isn't enough to hit the target duration, or when a window is too short relative to the frame rate to produce a visible blend at all.
- A short lead-in blend eases into each window from normal-speed playback, rather than a hard transition straight into the sped-up section.

---

## Known Issues & Workarounds

- **Brief freeze at start** if the first audio/video frames are silent/black. *Workaround:* trim a tiny leading sliver (100–300 ms) before processing.
- **Blend-Through with very tight Skippy presets** (e.g. Gentle on long, low-redundancy content) may print a warning if even maximal window-widening can't fully close the gap to the target duration — in that case, use a less aggressive preset or switch to Cut mode for that job.

---

## Scripts in this repo

- `tempocut_v2.py` — full PyQt5 GUI
- `audio_skippy_SURROUND.py` — joint audio+video redundancy detection, multichannel/5.1-aware (also handles stereo/mono)
- `time_compressor_CUTLIST.py` — Cut mode video compressor
- `time_compressor_BLENDTHROUGH.py` — Blend-Through mode video compressor
- `subtitle_retime.py` — retimes SRT/STL/SCC subtitles via the saved warp map
- `tempocut.spec` — PyInstaller build spec
- `TempoCut.iss` — Inno Setup installer script

---

## License

MIT License — see [LICENSE](LICENSE) for details.
