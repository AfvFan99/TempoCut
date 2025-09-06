#!/usr/bin/env python3
"""
retime_subs.py - Apply DTW time compression mapping to subtitles (.srt or .stl)

Usage:
    python retime_subs.py -i input.srt -o output.srt -m map.npy
    python retime_subs.py -i input.srt -o output.stl -m map.npy --fps 29.97
"""

import argparse
import numpy as np
import pysubs2
import os

def retime_subs(input_file, output_file, mapping_file, fps=29.97):
    # Load time mapping: shape [N, 2] = [t_skip, t_orig]
    mapping = np.load(mapping_file)
    t_skip = mapping[:,0]
    t_orig = mapping[:,1]

    # Load subtitles (pysubs2 auto-detects format)
    subs = pysubs2.load(input_file, fps=fps)

    for line in subs:
        # pysubs2 stores times in ms
        start_sec = line.start / 1000.0
        end_sec   = line.end / 1000.0

        # Interpolate with mapping
        line.start = int(np.interp(start_sec, t_orig, t_skip) * 1000)
        line.end   = int(np.interp(end_sec,   t_orig, t_skip) * 1000)

    # Detect output extension
    ext = os.path.splitext(output_file)[1].lower()
    if ext == ".stl":
        subs.save(output_file, format="srt", fps=fps)
    else:
        subs.save(output_file)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, help="Input subtitle file (.srt)")
    ap.add_argument("-o", "--output", required=True, help="Output subtitle file (.srt or .stl)")
    ap.add_argument("-m", "--map", required=True, help="Mapping .npy file (from compressor)")
    ap.add_argument("--fps", type=float, default=29.97,
                    help="FPS for STL export (default=29.97)")
    args = ap.parse_args()

    retime_subs(args.input, args.output, args.map, fps=args.fps)
