# TempoCut

**Broadcast-style video & audio time compression — recreate the classic “time tailoring” used by TBS, TNT, TruTV, Cartoon Network, and Adult Swim.**  
_Not affiliated with Warner Bros. Discovery or Prime Image. Educational use only._

---

## 📖 Overview

**TempoCut** is a Python toolkit that mimics professional broadcast time compression systems (e.g., Prime Image Time Tailor). It shortens shows to fit time slots while keeping **tight A/V sync**.

The audio engine is designed to sound very close to the Turner “skippy” style with minimal artifacts, while the video is retimed to match (59.94p output with subtle smears). Subtitle alignment is handled automatically via DTW warp maps.

---

## ✨ Features

- Broadcast-accurate time compression for **audio + video**
- Multiple audio “skippy” modes with marker export for Premiere Pro
- 29.97p or 59.94p output with micro-smear blending to reduce judder
- Saves DTW warp map for **subtitle** retiming
- Windows batch pipeline for one-click runs

---

## 🛠 Requirements

**Python:** 3.10+

**Install tools & libs**
```bash
pip install -r requirements.txt
```

**Also required**
- **FFmpeg** in your PATH (for I/O and muxing)
- (Optional) **ffsubsync** CLI in PATH if you want the batch script’s subtitle fallback

---

## 🚀 Usage

TempoCut has three main stages: **audio compression**, **video retiming**, and **subtitle alignment**. You can run them individually or together with the provided batch script.

### 1. Audio Compression

Choose stereo or surround based on your source.

**Stereo**
```bash
python audio_skippy_STEREO.py -i "input.wav" -o "output.wav" --target-ratio 1.02
```

**Surround (5.1 WAV)**
```bash
python audio_skippy_SURROUND.py -i "input.wav" -o "output.wav" --target-ratio 1.02
```

👉 This step creates both the compressed audio file **and** a `*_markers.txt` file listing “skippy” points, which you can import into Premiere Pro.

---

### 2. Video Retime

Now retime the video to match the skippy audio.

```bash
python time_compressor_SAFE.py -i "input.mp4" -s "output.wav" -o "out_59p.mp4"
```

- Output is 29.97p or 59.94p video with micro-smear blending (to hide jumps).
- A warp map file `map_t_skip_to_t_orig.npy` is also created — you’ll need it if you want subtitles.

---

### 3. Subtitle Alignment

If you have subtitles, retime them using the warp map:

```bash
python retime_subs.py map_t_skip_to_t_orig.npy input.srt output.srt
```

This adjusts every subtitle cue to stay in sync with the new compressed video.

---

### 4. One-Click Workflow (Windows)

Edit the paths inside:
```bat
time_compressor_pipeline.bat
```

Then run it. It will:
1. Retime video  
2. Mux audio  
3. Retime subs (or fall back to `ffsubsync`)  
4. Clean up temp files  

---

## 🎚️ Audio Compression Modes

**Basic usage**
```bash
python audio_skippy.py -i "input.wav" -o "output_timecompressed.wav" --target-ratio 1.0198
```
*(Change `--target-ratio` to your desired total compression.)*

**Advanced usage (classic “skippy” cadence)**
```bat
python audio_skippy.py ^
 -i "input.wav" ^
 -o "output_compress.wav" ^
 --target-ratio **** ^
 --frame-ms 15 ^
 --max-chop-ms 35 ^
 --cadence-ms 250 ^
 --crossfade-ms 6 ^
 --energy-quantile 0.5
```

**Lighter compression (smoother)**
```bat
python audio_skippy.py ^
 -i "input.wav" ^
 -o "output_light.wav" ^
 --target-ratio **** ^
 --frame-ms 20 ^
 --max-chop-ms 25 ^
 --cadence-ms 300 ^
 --crossfade-ms 8 ^
 --energy-quantile 0.4
```

**Heavier compression (more TBS-like “skips”)**
```bat
python audio_skippy.py ^
 -i "input.wav" ^
 -o "output_heavy.wav" ^
 --target-ratio **** ^
 --frame-ms 10 ^
 --max-chop-ms 45 ^
 --cadence-ms 180 ^
 --crossfade-ms 4 ^
 --energy-quantile 0.6
```

**Tips**
- `--target-ratio` ≈ total shortening (e.g., `1.02` ≈ 2% shorter).
- Smaller `--frame-ms`/`--cadence-ms` = tighter sync, more obvious “skips”.
- Larger values = smoother, lighter compression.
- Keep ratios under **1.05** for natural sound.
- For 5.1, use `audio_skippy_SURROUND.py`.

---

## ⚠️ Known Issues & Workarounds

- **Brief freeze at start** if the first audio/video frames are silent/black.  
  *Workaround:* Trim a tiny leading sliver (100–300 ms) before processing.
- **Occasional mid-video frame pauses** if off-by-one sync drift appears.  
  *Workaround:* Try a larger `--frame-ms` or gentler `--target-ratio` on audio.
- **Library compatibility**  
  Pinned: `moviepy==1.0.5`, `numpy<2.0`.

---

## 📂 Scripts in this repo

- `audio_skippy_STEREO.py` – stereo micro-skip engine + Premiere markers
- `audio_skippy_SURROUND.py` – multichannel/5.1 micro-skip engine + markers
- `time_compressor_SAFE.py` – DTW-based video retime to skippy audio (59.94p + smears) and saves warp map
- `retime_subs.py` – retimes SRTs via the saved warp map
- `time_compressor_pipeline.bat` – Windows pipeline for the whole flow

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.
