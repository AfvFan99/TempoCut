#!/usr/bin/env python3
"""
time_compressor_CUTLIST.py — Joint video+audio cut-based time compression.

Replaces the DTW-based approach entirely. Instead of approximately
re-discovering where audio_skippy_SURROUND.py removed audio (via mel-
spectrogram DTW alignment) and then continuously retiming/blending the
WHOLE video to match that approximate curve, this reads the EXACT
removal list audio_skippy already computed and cuts matching video frame
ranges at the same points.

Video plays at native speed everywhere except the sparse, exact cut
points, where a short cross-dissolve (matching audio's own crossfade
duration) smooths the join -- the same technique audio_skippy already
uses for audio, just applied to video too, only right at real cuts.

This is what eliminates the entire class of drift/jitter/slow-catch-up
bugs that come from continuous retiming: there's no retiming curve left
to overshoot, drift, or need guards for. Sync is guaranteed by
construction (both streams are cut from the same list), not computed
after the fact.
"""

import argparse, os, sys
import numpy as np
import cv2
import subprocess
from collections import OrderedDict
from tqdm import tqdm

FRAME_CACHE_SIZE = 48


class SequentialFrameSource:
    """Wraps cv2.VideoCapture for fast, frame-accurate access when reads
    are mostly forward (true here -- we only jump forward, to skip the
    bulk of a removed range, never backward). Identical to the proven
    reader used by the DTW-based script; copied here so this file stays
    fully standalone."""
    def __init__(self, path, cache_size=FRAME_CACHE_SIZE, forward_tolerance=120):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video: {path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0.0

        self._cache = OrderedDict()
        self._cache_size = max(cache_size, 48)
        self._cur_pos = 0
        self._forward_tolerance = forward_tolerance
        self._last_good_frame = None
        self._last_good_idx = None

    def _decode_next(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32)
        idx = self._cur_pos
        self._cur_pos += 1
        self._cache[idx] = frame
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        self._last_good_frame = frame
        self._last_good_idx = idx
        return frame

    def get(self, frame_idx):
        frame_idx = max(0, min(frame_idx, self.total_frames - 1))
        if frame_idx in self._cache:
            self._cache.move_to_end(frame_idx)
            return self._cache[frame_idx]

        gap = frame_idx - self._cur_pos
        if 0 <= gap <= self._forward_tolerance:
            frame = None
            for _ in range(gap + 1):
                f = self._decode_next()
                if f is None:
                    break
                frame = f
            if frame is not None and self._last_good_idx == frame_idx:
                return frame
            if self._last_good_frame is not None:
                return self._last_good_frame

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        actual_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self._cur_pos = actual_pos
        frame = self._decode_next()
        if frame is None:
            if self._last_good_frame is not None:
                return self._last_good_frame
            raise RuntimeError(f"Failed to decode frame {frame_idx} (no fallback available)")

        steps_remaining = frame_idx - self._last_good_idx
        steps_taken = 0
        while steps_remaining > 0 and steps_taken < self._forward_tolerance:
            f = self._decode_next()
            if f is None:
                break
            steps_taken += 1
            steps_remaining -= 1
        return self._last_good_frame

    def release(self):
        self.cap.release()


def read_cutlist(path):
    """Reads the precise cutlist CSV written by audio_skippy_SURROUND.py:
    start_sec,end_sec,crossfade_sec per row, sorted by start time."""
    removals = []
    with open(path, "r", encoding="utf-8") as f:
        f.readline()  # header
        for line in f:
            line = line.strip()
            if not line:
                continue
            start_sec, end_sec, crossfade_sec = line.split(",")
            removals.append((float(start_sec), float(end_sec), float(crossfade_sec)))
    removals.sort(key=lambda r: r[0])
    return removals


def build_exact_time_map(removals, total_duration):
    """
    Exact (t_skip, t_orig) piecewise-linear map for SUBTITLE retiming --
    an instant jump at each cut (subtitles don't need a smooth transition,
    just to land on the correct side of it).
    """
    t_skip_pts = [0.0]
    t_orig_pts = [0.0]
    cum_removed = 0.0
    for start, end, cross in removals:
        cum_removed_with_cross = cum_removed + (end - start) + cross
        t_orig_pts.append(start)
        t_skip_pts.append(start - cum_removed)
        t_orig_pts.append(end)
        t_skip_pts.append(end - cum_removed_with_cross)
        cum_removed = cum_removed_with_cross
    t_orig_pts.append(total_duration)
    t_skip_pts.append(total_duration - cum_removed)
    return np.array(t_skip_pts), np.array(t_orig_pts)


def build_render_time_map(removals, total_duration):
    """
    Continuous (t_skip, t_orig) map for RENDERING -- each transition is a
    steep-but-finite slope (compressing the pre-crossfade + bulk + post-
    crossfade original-time span into just the crossfade's own output-time
    width) instead of a flat segment. This is what makes true subframe
    blending emerge naturally just from evaluating this map continuously
    (frac comes directly from where in the steep slope a given output
    frame falls), and it's what eliminates the frame-rounding bug
    entirely: total output frame count is derived from ONE single final
    duration value, never accumulated from many independently-rounded
    per-cut frame counts, so there's no per-cut error to compound.
    """
    t_skip_pts = [0.0]
    t_orig_pts = [0.0]
    out_cursor = 0.0
    orig_cursor = 0.0
    for start, end, cross in removals:
        pre_start_orig = start - cross
        if pre_start_orig > orig_cursor:
            out_cursor += (pre_start_orig - orig_cursor)
        t_skip_pts.append(out_cursor)
        t_orig_pts.append(pre_start_orig)

        post_end_orig = end + cross
        out_cursor += cross  # the transition's own output-time width
        t_skip_pts.append(out_cursor)
        t_orig_pts.append(post_end_orig)
        orig_cursor = post_end_orig

    if total_duration > orig_cursor:
        out_cursor += (total_duration - orig_cursor)
    t_skip_pts.append(out_cursor)
    t_orig_pts.append(total_duration)
    return np.array(t_skip_pts), np.array(t_orig_pts)


def detect_source_video_bitrate(video_path):
    """Probes the source's actual video bitrate via ffprobe. Used to
    target the SAME bitrate on encode, so output file size tracks the
    original closely instead of whatever a fixed quality target (CRF)
    happens to produce for this particular content. Returns bits/sec, or
    None if it can't be determined (caller falls back to a sensible
    default in that case)."""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=bit_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ], capture_output=True, text=True, timeout=15)
        bitrate_str = result.stdout.strip()
        if bitrate_str and bitrate_str.isdigit():
            return int(bitrate_str)
    except Exception:
        pass
    return None


def windowed_blend_frac(frac, blend_width):
    """
    Remaps a raw subframe frac (0..1) into an effective blend weight,
    controlling how MUCH of a transition actually blends versus snaps
    cleanly -- without ever changing WHERE the transition starts or ends.
    blend_width=1 reproduces the original frac exactly (full continuous
    blend). blend_width=0 is a hard snap at the midpoint. Anything between
    snaps outside a centered window and blends only within it.

    Always returns exactly 0.0 at frac=0 and exactly 1.0 at frac=1,
    regardless of blend_width -- this is what guarantees the transition
    stays perfectly continuous with normal playback on both sides, no
    matter how little blending happens in the middle of it.
    """
    if blend_width <= 0:
        return 0.0 if frac < 0.5 else 1.0
    if blend_width >= 1:
        return frac
    half = blend_width / 2.0
    lo, hi = 0.5 - half, 0.5 + half
    if frac <= lo:
        return 0.0
    if frac >= hi:
        return 1.0
    return (frac - lo) / (hi - lo)


def cut_compress_video(input_path, cutlist_path, output_path, blend_width=0.33):
    print("[*] Opening video (sequential decoder)...")
    src = SequentialFrameSource(input_path)
    video_fps = src.fps
    video_duration = src.duration
    print(f"[*] Source: {src.width}x{src.height} @ {video_fps:.3f} fps, "
          f"{src.total_frames} frames, {video_duration:.2f}s")

    removals = read_cutlist(cutlist_path)
    print(f"[*] Loaded {len(removals)} exact removal windows from cutlist")

    # Subtitle map: instant jump at each cut (subtitles just need to land
    # on the correct side, no smooth transition needed there).
    sub_skip_map, sub_orig_map = build_exact_time_map(removals, video_duration)
    map_path = os.path.join(os.path.dirname(output_path), "map_t_skip_to_t_orig.npy")
    np.save(map_path, np.vstack([sub_skip_map, sub_orig_map]).T)
    print(f"[OK] Saved subtitle mapping: {map_path}")

    # Render map: continuous, steep-but-finite slope through each
    # transition instead of a flat jump. Total output duration comes
    # straight from this map's last point -- ONE number, not an
    # accumulation of many independently-rounded per-cut frame counts,
    # which is what eliminates the frame-rounding drift entirely.
    render_skip_map, render_orig_map = build_render_time_map(removals, video_duration)
    total_output_duration = float(render_skip_map[-1])
    total_output_frames = int(round(total_output_duration * video_fps))
    print(f"[*] Rendering frames: {total_output_frames} "
          f"(output duration {total_output_duration:.3f}s via {len(removals)} cuts)...")

    def map_t_skip_to_t_orig(t):
        return float(np.interp(t, render_skip_map, render_orig_map,
                                left=render_orig_map[0], right=render_orig_map[-1]))

    source_bitrate = detect_source_video_bitrate(input_path)
    if source_bitrate:
        print(f"[*] Matching source video bitrate: {source_bitrate/1000:.0f} kbps "
              f"(targets similar file size to the original)")
        bitrate_args = [
            "-b:v", str(source_bitrate),
            "-maxrate", str(int(source_bitrate * 1.5)),
            "-bufsize", str(int(source_bitrate * 2)),
        ]
    else:
        print("[*] Could not detect source bitrate -- falling back to CRF 16")
        bitrate_args = ["-crf", "16"]

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{src.width}x{src.height}", "-r", f"{video_fps:.6f}",
        "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "fast", *bitrate_args,
        "-pix_fmt", "yuv420p",
        output_path
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             text=False)

    pbar = tqdm(total=total_output_frames, desc="Rendering frames", unit="frame")
    eps = 1.0 / video_fps

    def write_frame(arr):
        proc.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())

    try:
        for out_idx in range(total_output_frames):
            t_out = out_idx / video_fps
            t_orig = map_t_skip_to_t_orig(t_out)
            t_orig = max(0.0, min(t_orig, video_duration - eps))

            f_src = t_orig * video_fps
            frame_idx = int(np.floor(f_src))
            frac = float(f_src - frame_idx)

            frame_a = src.get(frame_idx)
            # Fast path: the vast majority of frames are pure passthrough
            # (frac ~0, nowhere near a cut). Skip fetching frame_b and the
            # blend math entirely in that case -- a frac this small would
            # produce an output indistinguishable from frame_a alone, so
            # there's no actual result change, just less wasted work on
            # almost every single frame in the video.
            if frac < 1e-4:
                out_frame = frame_a
            else:
                frame_b = src.get(frame_idx + 1)
                # The exact subframe weighting formula, remapped through
                # blend_width to control how much of the transition
                # actually blends versus snaps -- always continuous at
                # both ends regardless of the value.
                effective_frac = windowed_blend_frac(frac, blend_width)
                out_frame = (1.0 - effective_frac) * frame_a + effective_frac * frame_b
            write_frame(out_frame)
            pbar.update(1)

    finally:
        pbar.close()
        proc.stdin.close()
        proc.wait()
        src.release()

    print(f"[DONE] Video saved: {output_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("--cutlist", required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--blend-width", type=float, default=0.33,
                     help="0=hard cut at each transition's midpoint, 1=full "
                          "continuous subframe blend. Default 0.33 blends "
                          "enough to camouflage the cut without being fully "
                          "smooth. Always continuous at the transition's "
                          "start/end regardless of value.")
    args = ap.parse_args()
    cut_compress_video(args.input, args.cutlist, args.output, blend_width=args.blend_width)


if __name__ == "__main__":
    main()
