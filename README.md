# TempoCut

**Broadcast-style video & audio time compression — recreate the classic “time tailoring” used by TBS, TNT, TruTV, Cartoon Network, and Adult Swim.**  
_Not affiliated with Warner Bros. Discovery or Prime Image. Educational use only._

---

## 📖 Overview

**TempoCut** is a Windows desktop app that mimics professional broadcast time compression systems (e.g., Prime Image Time Tailor). It shortens shows to fit time slots while keeping **exact A/V sync**.

As of v1.2, TempoCut uses a cut-based architecture: instead of continuously retiming video to approximately match time-compressed audio, it analyzes the *original* audio waveform and video frames together to find genuinely redundant moments — points where both audio is quiet and video is visually static — and removes matching, exact-length windows from both simultaneously. Sync is guaranteed by construction, not computed after the fact.

---

## ✨ Features

- **Joint audio + video redundancy detection** — cuts only land where both audio *and* video are redundant, not audio energy alone
- **Exact sync** — output duration is derived from one continuous, exact time map, not accumulated per-cut rounding
- **Subframe blending at cuts**, with a **Blend Amount** control (Full / Medium / Light / None, or a fine slider) — choose how gradual each cut transition feels, from a continuous Premiere-style blend down to a hard snap
- **Genuine 23.976 → 29.97 pulldown** — real frame duplication via re-encode, not interpolation, applied before any cutting happens
- **Self-contained install** — bundles its own Python runtime and ffmpeg; nothing else to install
- **Subtitle retiming** via the same exact cut map (no approximation)
- **Multichannel (5.1) and stereo** audio support

---

## 🚀 Quick Start (Windows app)

1. Download the latest installer from [Releases](../../releases)
2. Run it — no Python, no ffmpeg, nothing else to install
3. Open TempoCut, load your video, set your target compression ratio, hit **Create Job**

That's it for typical use. Everything below is for advanced/command-line use of the underlying engine.

---

## 🛠 Advanced: Running the Scripts Directly

**Python:** 3.10+

```bash
pip install -r requirements.txt
```

**Also required:** FFmpeg in your PATH.

### 1. Audio Redundancy Detection + Compression

```bash
python audio_skippy_SURROUND.py -i "input.wav" -o "output.wav" --target-ratio 1.02 --video "input.mp4"
```

`--video` enables joint audio+video redundancy detection (recommended) — omit it to fall back to audio-only detection. This step produces:
- The compressed audio file
- A `*_markers.txt` file (human-readable cut points, importable into Premiere Pro)
- A `*_cutlist.csv` file (exact, machine-readable cut windows — this is what the video step actually uses)

### 2. Video Cutting

```bash
python time_compressor_CUTLIST.py -i "input.mp4" --cutlist "input_cutlist.csv" -o "output.mp4" --blend-width 0.33
```

`--blend-width` ranges 0 (hard cut) to 1 (full continuous blend); default 0.33. Output video has no audio track yet — mux it with the compressed audio from step 1 using ffmpeg.

A `map_t_skip_to_t_orig.npy` warp map is also saved alongside the output, for subtitle retiming.

### 3. Subtitle Retiming

```bash
python subtitle_retime.py -i input.srt -o output.srt -m map_t_skip_to_t_orig.npy
```

---

## 🎚️ Audio Compression Tuning

| Parameter | Effect |
|---|---|
| `--target-ratio` | Total shortening (e.g. `1.02` ≈ 2% shorter) |
| `--frame-ms` | Analysis frame size — smaller = tighter sync, more frequent cuts |
| `--max-chop-ms` | Maximum length of any single removed window |
| `--cadence-ms` | Minimum spacing between cuts |
| `--crossfade-ms` | Crossfade duration at each cut |
| `--energy-quantile` | How quiet a moment must be to qualify (lower = stricter) |
| `--video-motion-quantile` | How static a moment must be to qualify (lower = stricter; only used with `--video`) |

Keep `--target-ratio` under **1.05** for natural-sounding results. Requiring both audio *and* video redundancy is inherently more conservative than audio alone — if there aren't enough jointly-redundant moments in the source, the achieved ratio may fall short of the target. This is expected, not a bug.

---

## 📂 Scripts in this repo

- `tempocut_v2.py` – the GUI application
- `audio_skippy_SURROUND.py` – joint audio+video redundancy detection and audio time compression, multichannel/5.1
- `time_compressor_CUTLIST.py` – exact cut-based video compression with subframe blending at cut points
- `subtitle_retime.py` – retimes SRTs via the exact cut map
- `tempocut.spec` / `TempoCut.iss` – build files for the installer

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.
