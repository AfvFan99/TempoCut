#!/usr/bin/env python3
"""
audio_skippy.py  —  Broadcast-style micro-skip time compression for audio,
now with Premiere Pro marker export.

Usage (basic):
    python audio_skippy_SURROUND.py -i input.wav -o output.wav --target-ratio 1.02

This will also produce input_markers.txt with timestamps of skippy points.
"""

import argparse
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
import soundfile as sf

@dataclass
class SkipPlan:
    removals: List[Tuple[int, int]]
    achieved_ratio: float
    removed_ms_total: float

def make_skip_plan(
    samples: np.ndarray,
    sr: int,
    target_ratio: float,
    frame_ms: float = 20.0,
    max_chop_ms: float = 30.0,
    cadence_ms: float = 300.0,
    energy_quantile: float = 0.4,
) -> SkipPlan:
    assert target_ratio >= 1.0, "target_ratio must be >= 1.0 (speed-up)."
    if target_ratio == 1.0:
        return SkipPlan(removals=[], achieved_ratio=1.0, removed_ms_total=0.0)

    total_samples = samples.shape[0]
    duration_s = total_samples / sr
    remove_s = duration_s * (1.0 - 1.0 / target_ratio)
    if remove_s <= 0:
        return SkipPlan(removals=[], achieved_ratio=1.0, removed_ms_total=0.0)

    frame_len = max(1, int(sr * (frame_ms / 1000.0)))
    max_chop = max(1, int(sr * (max_chop_ms / 1000.0)))
    cadence = max(1, int(sr * (cadence_ms / 1000.0)))

    n_frames = total_samples // frame_len
    frames = samples[: n_frames * frame_len].reshape(n_frames, frame_len, -1) if samples.ndim == 2 else \
             samples[: n_frames * frame_len].reshape(n_frames, frame_len, 1)

    energies = np.sqrt(np.mean(frames**2, axis=(1,2)) + 1e-12)
    thresh = np.quantile(energies, energy_quantile)
    candidate_idxs = np.where(energies <= thresh)[0].tolist()

    remove_samples_total = int(remove_s * sr)
    removals: List[Tuple[int,int]] = []
    removed_so_far = 0
    last_removal_end = -10**12
    per_chop = min(frame_len, max_chop)
    checkpoints = list(range(0, total_samples, cadence))
    cand_set = set(candidate_idxs)
    search_window = cadence // 2

    def pick_best_candidate_near(start_sample, window_samples):
        start_frame = max(0, (start_sample - window_samples) // frame_len)
        end_frame = min(n_frames-1, (start_sample + window_samples) // frame_len)
        best_idx = None
        best_energy = 1e9
        for fi in range(int(start_frame), int(end_frame)+1):
            if fi in cand_set:
                e = energies[fi]
                if e < best_energy:
                    best_energy = e
                    best_idx = fi
        return best_idx

    for cp in checkpoints:
        if removed_so_far >= remove_samples_total:
            break
        fi = pick_best_candidate_near(cp, search_window)
        if fi is None:
            continue
        start = int(fi * frame_len)
        end = min(int(start + per_chop), total_samples)
        if start - last_removal_end < cadence:
            continue
        if end <= start:
            continue
        removals.append((start,end))
        removed_so_far += (end-start)
        last_removal_end = end

    achieved_ratio = (total_samples / sr) / ((total_samples - removed_so_far) / sr)
    return SkipPlan(removals=removals, achieved_ratio=float(achieved_ratio), removed_ms_total=1000.0*removed_so_far/sr)

def apply_removals_with_crossfade(samples: np.ndarray, sr: int, removals: List[Tuple[int,int]], crossfade_ms: float = 8.0) -> np.ndarray:
    if not removals:
        return samples

    cross = max(1, int(sr * (crossfade_ms/1000.0)))
    rem_idx = 0
    out_chunks = []
    cursor = 0

    def xfade(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        n = a.shape[0]
        t = np.linspace(0,1,n,endpoint=False,dtype=a.dtype)
        wa, wb = 1.0-t, t
        return (a*wa[:,None] + b*wb[:,None]) if a.ndim==2 else (a*wa + b*wb)

    while rem_idx < len(removals):
        start,end = removals[rem_idx]
        keep_end = max(cursor, start-cross)
        if keep_end > cursor:
            out_chunks.append(samples[cursor:keep_end])
        tail = samples[max(cursor,start-cross):start]
        head = samples[end:end+cross]
        if len(tail) and len(head):
            n = min(len(tail), len(head))
            out_chunks.append(xfade(tail[-n:], head[:n]))
            cursor = end+cross
        else:
            cursor = end
        rem_idx +=1

    if cursor < samples.shape[0]:
        out_chunks.append(samples[cursor:])
    return np.concatenate(out_chunks, axis=0)

def main():
    p = argparse.ArgumentParser(description="Micro-skip audio time compression with Premiere markers.")
    p.add_argument("-i","--input",required=True,help="Input WAV path")
    p.add_argument("-o","--output",required=True,help="Output WAV path")
    p.add_argument("--target-ratio",type=float,required=True,help="Overall speed-up factor (e.g., 1.02 for 2%% faster)")
    p.add_argument("--frame-ms", type=float, default=20.0)
    p.add_argument("--max-chop-ms", type=float, default=30.0)
    p.add_argument("--cadence-ms", type=float, default=300.0)
    p.add_argument("--crossfade-ms", type=float, default=8.0)
    p.add_argument("--energy-quantile", type=float, default=0.4)
    args = p.parse_args()

    x,sr = sf.read(args.input, always_2d=False)
    orig_len = x.shape[0]

    plan = make_skip_plan(
        samples=x if x.ndim==1 else x,
        sr=sr,
        target_ratio=args.target_ratio,
        frame_ms=args.frame_ms,
        max_chop_ms=args.max_chop_ms,
        cadence_ms=args.cadence_ms,
        energy_quantile=args.energy_quantile
    )

    y = apply_removals_with_crossfade(x, sr, plan.removals, crossfade_ms=args.crossfade_ms)

    new_len = y.shape[0]
    achieved = (orig_len / sr) / (new_len / sr)
    print("Original duration (s):", orig_len/sr)
    print("Target ratio:", args.target_ratio)
    print("Planned achieved ratio:", plan.achieved_ratio)
    print("Achieved ratio after render:", achieved)
    print("Removed total (ms):", plan.removed_ms_total)
    print("Number of removals:", len(plan.removals))

    sf.write(args.output, y, sr)
    print("Wrote:", args.output)

    # --- NEW: Export Premiere Pro marker timestamps ---
    marker_times = [start/sr for start,_ in plan.removals]
    marker_file = args.input.rsplit(".",1)[0]+"_markers.txt"
    np.savetxt(marker_file, marker_times, fmt="%.2f")
    print(f"[INFO] Marker file saved for Premiere: {marker_file}")
    print(f"[INFO] {len(marker_times)} skippy points written.")

if __name__=="__main__":
    main()
