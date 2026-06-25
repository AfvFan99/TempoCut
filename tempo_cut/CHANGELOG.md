# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/).

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
