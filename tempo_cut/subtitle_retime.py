#!/usr/bin/env python3
"""
retime_subs.py - Apply DTW time compression mapping to subtitles
Supports: .srt, .stl (via pysubs2), and .scc (CEA-608 broadcast captions, native parser)

Usage:
    python retime_subs.py -i input.srt -o output.srt -m map.npy
    python retime_subs.py -i input.scc -o output.scc -m map.npy --fps 29.97
"""

import argparse
import re
import numpy as np
import pysubs2
import os

# ─────────────────────────────────────────────
#  SCC (CEA-608) minimal read/write support
#  SCC lines look like:
#  00:01:02:15  9420 9420 94ae 94ae 9470 9470 c1d5 ...
#  i.e. a timecode, then space-separated hex byte-pairs.
#  We only need to retime the leading timecode per line —
#  the caption byte payload is passed through untouched.
# ─────────────────────────────────────────────

SCC_HEADER = "Scenarist_SCC V1.0"
SCC_LINE_RE = re.compile(
    r'^(?P<tc>\d{2}:\d{2}:\d{2}[:;]\d{2})\s+(?P<payload>.+)$'
)

def scc_tc_to_seconds(tc, fps=29.97):
    """Parse HH:MM:SS:FF or HH:MM:SS;FF (drop-frame) into seconds."""
    drop_frame = ';' in tc
    tc = tc.replace(';', ':')
    h, m, s, f = [int(x) for x in tc.split(':')]
    # Drop-frame correction (standard NTSC 29.97 drop-frame formula)
    if drop_frame:
        total_minutes = h * 60 + m
        frame_num = (h*3600 + m*60 + s) * 30 + f
        frame_num -= 2 * (total_minutes - total_minutes // 10)
        return frame_num / fps
    else:
        total_frames = (h*3600 + m*60 + s) * round(fps) + f
        return total_frames / fps

def seconds_to_scc_tc(t, fps=29.97, drop_frame=True):
    """Convert seconds back into an SCC timecode string."""
    t = max(0.0, t)
    if drop_frame:
        # inverse of standard drop-frame formula
        frame_rate_int = 30
        d = int(t * fps / 1.001 / frame_rate_int * frame_rate_int)  # approx frames at 30fps logical
        total_frames = int(round(t * fps))
        # Re-derive using iterative correction (good enough for retiming purposes)
        frame_num = int(round(t * fps))
        d_, m_ = divmod(frame_num, 17982)
        frame_num += 18 * d_ + 2 * ((m_ - 2) // 1798 if m_ >= 2 else 0)
        hours = frame_num // (3600 * 30)
        rem = frame_num % (3600 * 30)
        minutes = rem // (60 * 30)
        rem2 = rem % (60 * 30)
        secs = rem2 // 30
        frames = rem2 % 30
        return f"{hours:02d}:{minutes:02d}:{secs:02d};{frames:02d}"
    else:
        frame_rate_int = round(fps)
        total_frames = int(round(t * frame_rate_int))
        hours, rem = divmod(total_frames, 3600 * frame_rate_int)
        minutes, rem = divmod(rem, 60 * frame_rate_int)
        secs, frames = divmod(rem, frame_rate_int)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"

def load_scc(path):
    """Returns (header_line, [(tc_str, payload_str), ...])"""
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = [l.rstrip('\n').rstrip('\r') for l in f]
    header = lines[0] if lines and 'Scenarist' in lines[0] else SCC_HEADER
    entries = []
    for line in lines:
        m = SCC_LINE_RE.match(line.strip())
        if m:
            entries.append((m.group('tc'), m.group('payload')))
    return header, entries

def save_scc(path, header, entries):
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(header + "\n\n")
        for tc, payload in entries:
            f.write(f"{tc}\t{payload}\n\n")

def retime_scc(input_file, output_file, t_orig, t_skip, fps=29.97):
    header, entries = load_scc(input_file)
    new_entries = []
    drop_frame_out = True  # SCC is conventionally drop-frame at 29.97
    for tc, payload in entries:
        t_sec = scc_tc_to_seconds(tc, fps=fps)
        t_new = float(np.interp(t_sec, t_orig, t_skip, left=t_skip[0], right=t_skip[-1]))
        new_tc = seconds_to_scc_tc(t_new, fps=fps, drop_frame=drop_frame_out)
        new_entries.append((new_tc, payload))
    save_scc(output_file, header, new_entries)
    print(f"[OK] Retimed {len(new_entries)} SCC caption events -> {output_file}")

# ─────────────────────────────────────────────
#  Main retiming entry point
# ─────────────────────────────────────────────

def retime_subs(input_file, output_file, mapping_file, fps=29.97):
    mapping = np.load(mapping_file)
    t_skip = mapping[:, 0]
    t_orig = mapping[:, 1]

    in_ext  = os.path.splitext(input_file)[1].lower()
    out_ext = os.path.splitext(output_file)[1].lower()

    if in_ext == ".scc" or out_ext == ".scc":
        if in_ext != ".scc":
            raise ValueError("Cannot convert non-SCC input to SCC output directly. "
                              "Provide a .scc input file for .scc retiming.")
        retime_scc(input_file, output_file, t_orig, t_skip, fps=fps)
        return

    # SRT / STL path via pysubs2 (unchanged)
    subs = pysubs2.load(input_file, fps=fps)
    for line in subs:
        start_sec = line.start / 1000.0
        end_sec   = line.end / 1000.0
        line.start = int(np.interp(start_sec, t_orig, t_skip, left=t_skip[0], right=t_skip[-1]) * 1000)
        line.end   = int(np.interp(end_sec,   t_orig, t_skip, left=t_skip[0], right=t_skip[-1]) * 1000)

    if out_ext == ".stl":
        subs.save(output_file, format="srt", fps=fps)
    else:
        subs.save(output_file)
    print(f"[OK] Retimed {len(subs)} subtitle events -> {output_file}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, help="Input subtitle/caption file (.srt, .stl, .scc)")
    ap.add_argument("-o", "--output", required=True, help="Output subtitle/caption file (.srt, .stl, .scc)")
    ap.add_argument("-m", "--map", required=True, help="Mapping .npy file (from compressor)")
    ap.add_argument("--fps", type=float, default=29.97,
                    help="FPS for STL/SCC timecode interpretation (default=29.97)")
    args = ap.parse_args()

    retime_subs(args.input, args.output, args.map, fps=args.fps)
