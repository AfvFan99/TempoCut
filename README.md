# TempoCut
**Broadcast-style video & audio time compression — recreate the classic “time tailoring” used by TBS, TNT, TruTV, Cartoon Network, and Adult Swim.**  
_Not affiliated with Warner Bros. Discovery or Prime Image. Educational use only._

---

## Overview
**TempoCut** is a Python toolkit that mimics professional broadcast time compression systems (e.g., Prime Image Time Tailor). It shortens shows to fit time slots while keeping **tight A/V sync**.  

The audio engine is designed to sound very close to the Turner “skippy” style with minimal artifacts, while the video is retimed to match (59.94p output with subtle smears). Subtitle alignment is handled automatically via DTW warp maps.

---

## Features
- Broadcast-accurate time compression for **audio + video**
- Multiple audio “skippy” modes with marker export
- 59.94p output with micro-smear blending to reduce judder
- Saves DTW warp map for **subtitle** retiming
- Windows batch pipeline for one-click runs

---

## Requirements

**Python:** 3.10+

**Install tools & libs**
```bash
pip install -r requirements.txt
