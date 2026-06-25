#!/usr/bin/env python3
"""
audio_skippy.py — Broadcast-style micro-skip + extend audio processor
Now supports BOTH:
- compression (skip removal)
- extension (micro duplication stretch)
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
    mode: str


def make_skip_plan(
    samples: np.ndarray,
    sr: int,
    target_ratio: float,
    frame_ms: float = 20.0,
    max_chop_ms: float = 30.0,
    cadence_ms: float = 300.0,
    energy_quantile: float = 0.4,
) -> SkipPlan:

    assert target_ratio > 0, "target_ratio must be > 0"

    # ---------------- MODE ----------------
    if target_ratio < 1.0:
        mode = "extend"
    elif target_ratio > 1.0:
        mode = "compress"
    else:
        return SkipPlan([], 1.0, 0.0, "neutral")

    total_samples = samples.shape[0]
    duration_s = total_samples / sr

    removals: List[Tuple[int, int]] = []

    frame_len = max(1, int(sr * (frame_ms / 1000.0)))
    max_chop = max(1, int(sr * (max_chop_ms / 1000.0)))
    cadence = max(1, int(sr * (cadence_ms / 1000.0)))

    n_frames = total_samples // frame_len

    frames = (
        samples[: n_frames * frame_len].reshape(n_frames, frame_len, -1)
        if samples.ndim == 2
        else samples[: n_frames * frame_len].reshape(n_frames, frame_len, 1)
    )

    energies = np.sqrt(np.mean(frames**2, axis=(1, 2)) + 1e-12)
    thresh = np.quantile(energies, energy_quantile)
    candidate_idxs = np.where(energies <= thresh)[0].tolist()

    cand_set = set(candidate_idxs)
    search_window = cadence // 2

    per_chop = min(frame_len, max_chop)
    checkpoints = list(range(0, total_samples, cadence))

    def pick_best_candidate_near(start_sample, window_samples):
        start_frame = max(0, (start_sample - window_samples) // frame_len)
        end_frame = min(n_frames - 1, (start_sample + window_samples) // frame_len)

        best_idx = None
        best_energy = 1e9

        for fi in range(int(start_frame), int(end_frame) + 1):
            if fi in cand_set and energies[fi] < best_energy:
                best_energy = energies[fi]
                best_idx = fi

        return best_idx

    removed_so_far = 0
    last_removal_end = -10**12

    # ---------------- COMPRESS ----------------
    if mode == "compress":

        remove_s = duration_s * (1.0 - 1.0 / target_ratio)
        if remove_s <= 0:
            return SkipPlan([], 1.0, 0.0, "compress")

        remove_samples_total = int(remove_s * sr)

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

            removals.append((start, end))
            removed_so_far += (end - start)
            last_removal_end = end

        achieved_ratio = (total_samples / sr) / ((total_samples - removed_so_far) / sr)

        return SkipPlan(removals, float(achieved_ratio), removed_so_far * 1000 / sr, "compress")

    # ---------------- EXTEND ----------------
    else:
        extend_s = duration_s * (1.0 / target_ratio - 1.0)
        extend_samples = int(extend_s * sr)

        insertions: List[Tuple[int, int]] = []

        inserted = 0

        for cp in checkpoints:
            if inserted >= extend_samples:
                break

            fi = pick_best_candidate_near(cp, search_window)
            if fi is None:
                continue

            start = int(fi * frame_len)
            end = min(start + per_chop, total_samples)

            insertions.append((start, end))
            inserted += (end - start)

        achieved_ratio = (total_samples + inserted) / total_samples

        return SkipPlan(insertions, float(achieved_ratio), inserted * 1000 / sr, "extend")


def apply_plan(samples: np.ndarray, sr: int, plan: SkipPlan, crossfade_ms: float = 8.0) -> np.ndarray:

    if plan.mode == "compress":
        return apply_removals(samples, sr, plan.removals, crossfade_ms)

    elif plan.mode == "extend":
        return apply_insertions(samples, sr, plan.removals, crossfade_ms)

    return samples


def apply_removals(samples, sr, removals, crossfade_ms):
    if not removals:
        return samples

    cross = max(1, int(sr * crossfade_ms / 1000.0))
    out = []
    cursor = 0

    for start, end in removals:
        out.append(samples[cursor:max(cursor, start - cross)])

        tail = samples[max(cursor, start - cross):start]
        head = samples[end:end + cross]

        if len(tail) and len(head):
            n = min(len(tail), len(head))
            t = np.linspace(0, 1, n, endpoint=False)
            xf = tail[-n:] * (1 - t)[:, None] + head[:n] * t[:, None]
            out.append(xf)

        cursor = end + cross

    out.append(samples[cursor:])

    return np.concatenate(out, axis=0)


def apply_insertions(samples, sr, insertions, crossfade_ms):
    """Simple extend mode: duplicate selected segments."""
    if not insertions:
        return samples

    out = []
    cursor = 0

    for start, end in insertions:
        out.append(samples[cursor:start])

        seg = samples[start:end]

        # duplicate once (basic stretch)
        out.append(seg)
        out.append(seg)

        cursor = start

    out.append(samples[cursor:])

    return np.concatenate(out, axis=0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--target-ratio", type=float, required=True)
    p.add_argument("--frame-ms", type=float, default=20.0)
    p.add_argument("--max-chop-ms", type=float, default=30.0)
    p.add_argument("--cadence-ms", type=float, default=300.0)
    p.add_argument("--crossfade-ms", type=float, default=8.0)
    p.add_argument("--energy-quantile", type=float, default=0.4)

    args = p.parse_args()

    x, sr = sf.read(args.input, always_2d=False)

    plan = make_skip_plan(
        x if x.ndim == 1 else x,
        sr,
        args.target_ratio,
        args.frame_ms,
        args.max_chop_ms,
        args.cadence_ms,
        args.energy_quantile,
    )

    y = apply_plan(x, sr, plan, args.crossfade_ms)

    sf.write(args.output, y, sr)

    print("Mode:", plan.mode)
    print("Achieved ratio:", plan.achieved_ratio)
    print("Removed/Inserted ms:", plan.removed_ms_total)
    print("Output written:", args.output)


if __name__ == "__main__":
    main()