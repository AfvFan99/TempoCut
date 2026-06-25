# Changelog
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.2] - 2026-06-25

### Added
- **Cut-based time compression architecture**, replacing the previous DTW-based continuous video retiming entirely. The video step now reads the exact removal windows the audio engine already computed and cuts matching video at the same points, instead of approximately re-discovering them via DTW alignment and warping the whole timeline to match.
- **Joint audio + video redundancy detection** (`--video` flag on `audio_skippy_SURROUND.py`) — cut candidates now require both low audio energy *and* low video motion, closer to genuine broadcast-style time tailoring than audio-only detection.
- **`time_compressor_CUTLIST.py`** — new video compressor consuming the exact cutlist, with subframe blending applied only at real cut transitions.
- **Blend Amount control** (`--blend-width`, 0–1) — lets the amount of blending at each cut transition be tuned from a hard snap to a full continuous Premiere-style blend, while always remaining mathematically continuous at the transition boundaries regardless of setting. Default 0.33.
- Genuine 23.976 → 29.97 hard pulldown via real frame duplication on re-encode, applied before any cutting or detection.
- Source-bitrate-matched video encoding, so output file size tracks the original instead of a fixed quality setting unrelated to size.

### Fixed
- Long files no longer hang indefinitely during processing. Root cause was `librosa`'s lazy-loaded import chain, unrelated to file size or content; replaced with direct `numpy`/`numba`/`soundfile` calls throughout.
- Audio/video sync drift on long files with many cuts, caused by the crossfade duration export not matching what was actually applied during audio rendering.
- Off-by-one bug in the 6-channel→stereo audio extraction fallback that produced a malformed ffmpeg command on failure.
- Flicker at hard scene cuts (black-to-color and similar), via scene-cut detection in the blend path.
- Output audio quality on sources with a low original bitrate, by flooring the re-encode bitrate per channel.

### Removed
- DTW-based video retiming (`time_compressor_SAFE_v2.py`) is no longer used by the app, superseded by the cut-based architecture. Kept in the repo for reference.
- Forward/Backward/Bilateral/Motion-Adaptive blend modes, no longer meaningful in the cut-based architecture — replaced by the single Blend Amount control.

---

## [0.1.0] - 2025-09-06

### Added
- Initial release of **TempoCut**
- `audio_skippy_STEREO.py` and `audio_skippy_SURROUND.py`: stereo & surround micro-skip compressors with Premiere marker export
- `time_compressor_SAFE.py`: DTW-based video retime @ 59.94p with micro-smear blending + subtitle warp map
- `retime_subs.py`: subtitle realignment using the warp map
- `time_compressor_pipeline.bat`: one-click Windows workflow
- Full `README.md` with install instructions, usage, audio modes, and known issues
- `requirements.txt` with pinned dependencies (`moviepy==1.0.5`, `numpy<2.0`)

### Notes
- Large raw files (e.g., WAV, MP4) are excluded via `.gitignore`
- Intended for educational/hobbyist use; not affiliated with Prime Image or Warner Bros. Discovery
