# time_compressor_SAFE_FAST.py
"""
TBS-style DTW video compressor (fast version)
- Output: 59.94p with smear blending.
- Nearest-frame timing + micro-smear every N frames.
- Saves DTW warp map for subtitle retiming.

v2: Sequential OpenCV decode + small LRU frame cache + raw ffmpeg pipe encode.
    Avoids moviepy's per-call get_frame(t) seeking, which forces ffmpeg to
    reseek on almost every frame for warped/non-monotonic timelines.
    This is the same "decode forward, cache, reuse" approach editors like
    Premiere use for frame blending — no extra CPU acceleration needed,
    just not re-decoding the same regions of video over and over.
"""

import argparse, os, subprocess, sys
import numpy as np
import librosa
import cv2
import numba
from tqdm import tqdm
from collections import OrderedDict

sys.stdout.reconfigure(encoding='utf-8')

# ---------- Tunables ----------
# These match the proven working values from the original video.py
# (FAST_STRETCH version) that actually drove successful renders.
TARGET_SR            = 16000
N_MELS               = 64
HOP                  = 2048
TIME_DECIM           = 2
MAX_JUMP_RATIO       = 1.2
MICRO_BLEND_FRAMES   = 30        # apply smear every 30 frames
MICRO_BLEND_ALPHA    = 0.50      # blend strength
SMEAR_DURATION_MS    = 64        # smear lasts ~64ms
OUTPUT_FPS           = 60000 / 1001   # 59.94 fps
FRAME_CACHE_SIZE     = 64        # number of decoded frames to keep in LRU cache
# ------------------------------

def _manual_mel_filterbank(sr, n_fft, n_mels, fmax, fmin=0.0):
    """
    Pure-numpy triangular mel filterbank, replacing librosa.filters.mel().
    That function does almost no real work (just builds a small matrix from
    sr/n_fft/n_mels/fmax), but calling it was found to hang indefinitely --
    librosa lazy-loads its heavy dependencies (including the same scipy
    chain that caused trouble earlier tonight) on first real use of a
    function, not on `import librosa` itself, which is why plain import
    was instant but this specific call wasn't. This avoids librosa
    entirely for filter construction. Uses the standard HTK mel scale
    (simpler than librosa's Slaney-by-default piecewise formula) -- exact
    convention doesn't matter here since both audio streams go through
    this identical filterbank, only consistency between them does.
    """
    def hz_to_mel(hz):
        return 2595.0 * np.log10(1.0 + hz / 700.0)

    def mel_to_hz(mel):
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    mel_min, mel_max = hz_to_mel(fmin), hz_to_mel(fmax)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points = mel_to_hz(mel_points)
    bins = np.floor((n_fft + 1) * hz_points / sr).astype(int)
    bins = np.clip(bins, 0, n_fft // 2)

    fb = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for m in range(1, n_mels + 1):
        left, center, right = bins[m - 1], bins[m], bins[m + 1]
        if center == left:
            center += 1
        if right == center:
            right += 1
        for k in range(left, center):
            if center > left:
                fb[m - 1, k] = (k - left) / (center - left)
        for k in range(center, right):
            if right > center:
                fb[m - 1, k] = (right - k) / (right - center)
        # Area-normalize so filter outputs stay in a sane, comparable range.
        band_width = hz_points[m + 1] - hz_points[m - 1]
        if band_width > 0:
            fb[m - 1] *= 2.0 / band_width
    return fb


def _manual_power_to_db(S, ref=None, amin=1e-10, top_db=80.0):
    """
    Pure-numpy replacement for librosa.power_to_db(), same reasoning as
    above -- avoids triggering librosa's lazy-loaded scipy chain.
    """
    S = np.asarray(S, dtype=np.float32)
    ref_value = np.max(S) if ref is None else ref
    ref_value = max(float(ref_value), amin)
    log_spec = 10.0 * np.log10(np.maximum(amin, S))
    log_spec -= 10.0 * np.log10(ref_value)
    if top_db is not None:
        log_spec = np.maximum(log_spec, log_spec.max() - top_db)
    return log_spec


def fast_melspectrogram(y, sr, n_mels=N_MELS, hop_length=HOP, fmax=None):
    """
    Drop-in replacement for librosa.feature.melspectrogram(), built from
    fully vectorized numpy operations -- no internal per-frame Python loop
    at all. Same fix strategy as fast_load_mono() above: librosa's own
    wrapper functions were found to hang on long audio in this environment
    even though equivalent raw numpy/scipy math is fast, so this avoids
    librosa's internal STFT/framing implementation entirely.

    Note: this won't numerically match librosa's STFT convention exactly
    (windowing/padding details differ slightly), but that doesn't matter
    here -- compute_features() calls this identically for both audio
    streams being aligned, so internal consistency between the two calls
    is all the DTW alignment actually needs, not an exact match to
    librosa's own output.
    """
    n_fft = hop_length  # matches the original call: hop_length == n_fft, no overlap
    if fmax is None:
        fmax = sr // 2

    if len(y) < n_fft:
        y = np.pad(y, (0, n_fft - len(y)))

    n_frames = 1 + (len(y) - n_fft) // hop_length
    y = np.ascontiguousarray(y, dtype=np.float32)
    shape = (n_fft, n_frames)
    strides = (y.strides[0], y.strides[0] * hop_length)
    frames = np.lib.stride_tricks.as_strided(y, shape=shape, strides=strides)

    window = np.hanning(n_fft).astype(np.float32)
    windowed = frames * window[:, None]

    # Single batched FFT across every frame at once -- no per-frame loop.
    spectrum = np.fft.rfft(windowed, n=n_fft, axis=0)
    power = (np.abs(spectrum) ** 2).astype(np.float32)

    mel_basis = _manual_mel_filterbank(sr, n_fft, n_mels, fmax)
    return mel_basis @ power


def compute_features(y, sr):
    S = fast_melspectrogram(y, sr, n_mels=N_MELS, hop_length=HOP, fmax=sr//2)
    return _manual_power_to_db(S[:, ::TIME_DECIM])

def build_time_map_from_wp(wp, sr=TARGET_SR, hop=HOP, time_decim=TIME_DECIM):
    wp = np.array(wp)
    i, j = wp[:,0].astype(np.int64), wp[:,1].astype(np.int64)

    frame_stride = hop * time_decim
    t_orig = i * frame_stride / sr
    t_skip = j * frame_stride / sr

    order = np.argsort(t_skip)
    t_skip, t_orig = t_skip[order], t_orig[order]

    uniq = np.concatenate(([True], np.diff(t_skip) > 0))
    t_skip, t_orig = t_skip[uniq], t_orig[uniq]

    dt = np.diff(t_orig)
    median_dt = np.median(dt) if len(dt)>0 else 1.0/OUTPUT_FPS
    max_dt = median_dt * MAX_JUMP_RATIO
    for k in range(1,len(t_orig)):
        delta = t_orig[k]-t_orig[k-1]
        if delta>max_dt: t_orig[k] = t_orig[k-1]+max_dt
        elif delta<0:    t_orig[k] = t_orig[k-1]+median_dt

    return t_skip, t_orig


class SequentialFrameSource:
    """
    Wraps cv2.VideoCapture for fast access to frames whose request order is
    'mostly forward' (true even for warped/time-compressed timelines, since
    DTW maps forward in source time overall — but smear/blend logic
    re-requests recently-seen frames constantly, which is NOT a forward gap).

    Strategy:
    - Keep an LRU cache of the last FRAME_CACHE_SIZE decoded frames.
      This is what actually serves repeated/backward requests from smear
      blending — NOT seeking.
    - On a genuine cache miss that's a small step forward, decode forward
      sequentially (cheap, frame-accurate).
    - Only hard-seek when the gap is large. cv2 seeking is frame-INACCURATE
      on many H.264 streams (lands near a keyframe), so after seeking we
      re-sync _cur_pos to wherever the decoder actually landed rather than
      trusting the requested index — and we never return a frame without
      a successful read().
    """
    def __init__(self, path, cache_size=FRAME_CACHE_SIZE, forward_tolerance=120):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video: {path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0.0

        self._cache = OrderedDict()   # frame_idx -> frame (RGB, float32)
        self._cache_size = max(cache_size, 48)  # 48 HD float32 frames (~1.1GB)
                                                  # is plenty to cover smear/blend
                                                  # lookback without eating multiple
                                                  # GB of RAM (256 frames was ~6GB)
        self._cur_pos = 0             # index that the NEXT cap.read() will return
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

        # 1) Cache hit — covers backward/repeated requests from smear blending.
        if frame_idx in self._cache:
            self._cache.move_to_end(frame_idx)
            return self._cache[frame_idx]

        # 2) Small forward gap — decode forward sequentially (frame-accurate).
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
            # If we ran out of stream before reaching frame_idx, fall through
            # to return the last successfully decoded frame instead of stalling.
            if self._last_good_frame is not None:
                return self._last_good_frame

        # 3) Large gap (or backward jump beyond cache) — hard seek.
        #    cv2 seeking can be inaccurate, so re-sync _cur_pos to where we
        #    actually land, and verify with a real successful read().
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        actual_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self._cur_pos = actual_pos
        frame = self._decode_next()

        if frame is None:
            # End of stream or decode failure: return last known-good frame
            # rather than silently freezing on a cached value.
            if self._last_good_frame is not None:
                return self._last_good_frame
            raise RuntimeError(f"Failed to decode frame {frame_idx} (no fallback available)")

        # If the seek overshot/undershot and we still need to reach frame_idx,
        # step forward the remainder (bounded, to avoid pathological loops).
        steps_remaining = frame_idx - self._last_good_idx
        steps_taken = 0
        while steps_remaining > 0 and steps_taken < self._forward_tolerance:
            f = self._decode_next()
            if f is None:
                break
            frame = f
            steps_remaining = frame_idx - self._last_good_idx
            steps_taken += 1

        return frame

    def release(self):
        self.cap.release()


def extract_audio_for_dtw(input_path, tmp_wav, target_sr=TARGET_SR):
    """Use ffmpeg directly (fast, no moviepy overhead) to pull a mono WAV for DTW analysis."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn", "-ac", "1", "-ar", str(target_sr),
        "-acodec", "pcm_s16le",
        tmp_wav
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print(result.stdout)
        raise RuntimeError("ffmpeg audio extraction for DTW failed")


def fast_load_mono(path, target_sr):
    """
    Drop-in replacement for librosa.load(path, sr=target_sr, mono=True).

    librosa.load() was found to hang indefinitely on some long files in
    some environments, even though every individual primitive it should
    be using internally -- soundfile.read() for the full file, numpy.mean()
    for the mono downmix -- was separately verified to complete in under
    2 seconds each, even on a 65-million-frame, 6-channel, 23-minute file.
    The exact cause inside librosa's own loading wrapper was never
    pinned down (likely an internal chunked-read loop with high per-call
    overhead in certain environments), but bypassing it entirely with
    these same known-fast building blocks sidesteps the problem
    regardless of root cause.
    """
    import soundfile as sf
    data, native_sr = sf.read(path, always_2d=False)
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    data = data.astype(np.float32, copy=False)
    if native_sr != target_sr:
        import soxr
        data = soxr.resample(data, native_sr, target_sr)
    return data, target_sr


@numba.njit(cache=True)
def _dtw_subseq_core(C):
    """
    Core DP recurrence for subsequence DTW: Y (columns) must be fully
    consumed start-to-end, but X (rows) may start matching at ANY row with
    zero accumulated cost (that's the 'subsequence' relaxation -- it lets
    the alignment begin anywhere in the original timeline rather than
    forcing it to start exactly at frame 0). JIT-compiled because this is
    an inherently sequential O(N1*N2) recurrence -- at real file sizes
    (tens of thousands of frames per side) that's potentially hundreds of
    millions of cells, far too slow as a plain Python loop, but numba
    compiles it to native speed.
    """
    N1, N2 = C.shape
    D = np.empty((N1, N2), dtype=np.float64)
    for i in range(N1):
        D[i, 0] = C[i, 0]
    for j in range(1, N2):
        D[0, j] = D[0, j - 1] + C[0, j]
    for i in range(1, N1):
        for j in range(1, N2):
            best = D[i - 1, j]
            if D[i, j - 1] < best:
                best = D[i, j - 1]
            if D[i - 1, j - 1] < best:
                best = D[i - 1, j - 1]
            D[i, j] = C[i, j] + best
    return D


@numba.njit(cache=True)
def _dtw_backtrack(D):
    """Backtrack from the minimum-cost end-of-Y cell to build the warping
    path. Stops once Y is fully traced back to j=0 (X's start is free, per
    the subsequence relaxation above, so there's nothing further to trace
    once j reaches 0)."""
    N1, N2 = D.shape
    i = 0
    best = D[0, N2 - 1]
    for r in range(1, N1):
        if D[r, N2 - 1] < best:
            best = D[r, N2 - 1]
            i = r
    j = N2 - 1
    path_i = np.empty(N1 + N2, dtype=np.int64)
    path_j = np.empty(N1 + N2, dtype=np.int64)
    n = 0
    path_i[n] = i; path_j[n] = j; n += 1
    while j > 0:
        if i > 0 and j > 0:
            options = (D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
            best_idx = 0
            best_val = options[0]
            if options[1] < best_val:
                best_val = options[1]; best_idx = 1
            if options[2] < best_val:
                best_val = options[2]; best_idx = 2
            if best_idx == 0:
                i -= 1
            elif best_idx == 1:
                j -= 1
            else:
                i -= 1; j -= 1
        elif i > 0:
            i -= 1
        else:
            j -= 1
        path_i[n] = i; path_j[n] = j; n += 1
    return path_i[:n][::-1], path_j[:n][::-1]


def fast_subseq_dtw(X, Y):
    """
    Drop-in replacement for librosa.sequence.dtw(X=X, Y=Y, metric='euclidean',
    subseq=True), returning a warping path array in the same [i, j] pair
    format consumed by build_time_map_from_wp(). Same reasoning as the
    other replacements in this file: librosa's wrapper hangs on first real
    use (its lazy-loaded scipy import chain), so this builds the pairwise
    distance matrix with plain vectorized numpy (a matmul -- already
    proven fast) and the DP recurrence with numba directly (not through
    librosa), which has been working fine all night since it isn't
    subject to librosa's lazy-import issue at all.
    """
    X2 = np.sum(X.astype(np.float64) ** 2, axis=0)
    Y2 = np.sum(Y.astype(np.float64) ** 2, axis=0)
    cross = X.astype(np.float64).T @ Y.astype(np.float64)
    C = np.sqrt(np.maximum(X2[:, None] + Y2[None, :] - 2 * cross, 0.0))
    D = _dtw_subseq_core(C)
    path_i, path_j = _dtw_backtrack(D)
    return np.stack([path_i, path_j], axis=1)


def time_compress_video(input_path, skippy_audio_path, output_path,
                         blend_mode="subframe", blend_alpha=MICRO_BLEND_ALPHA,
                         blend_every=MICRO_BLEND_FRAMES, smear_ms=SMEAR_DURATION_MS,
                         output_fps=None):
    print("[*] Opening video (sequential decoder)...")
    src = SequentialFrameSource(input_path)
    video_fps = src.fps
    video_duration = src.duration
    print(f"[*] Source: {src.width}x{src.height} @ {video_fps:.3f} fps, "
          f"{src.total_frames} frames, {video_duration:.2f}s")

    # ── Output FPS: auto-detect from source by default ──
    # Previously this always fell back to a hardcoded 59.94005994005994
    # constant unless --output-fps was passed manually. That's a problem
    # because cv2's reported fps for a given file can differ from that
    # constant by a tiny fraction (rounding/container metadata quirks), and
    # over a 10+ minute / 37,000+ frame render that tiny per-frame error
    # accumulates into real drift between the rendered timeline and the
    # audio -- a slow, creeping desync that can read as jitter on long
    # files even when nothing else is wrong. Matching the source's own
    # reported rate avoids introducing that drift in the first place.
    # Manual override via --output-fps still works if you ever need to
    # force a specific rate (e.g. intentionally retiming to a different
    # broadcast standard).
    if output_fps:
        out_fps = float(output_fps)
    else:
        if video_fps and video_fps > 1.0:
            out_fps = video_fps
            print(f"[*] No --output-fps specified; auto-detected source rate: {out_fps:.6f} fps")
        else:
            # Source fps detection failed/looked bogus (e.g. cv2 fallback of
            # 30.0 from a broken container) -- fall back to the known-good
            # constant rather than trusting a suspicious value.
            out_fps = OUTPUT_FPS
            print(f"[*] Source fps looked invalid ({video_fps}); "
                  f"falling back to default {out_fps:.6f} fps")

    tmp_wav = os.path.join(os.path.dirname(output_path), "ref_for_dtw.wav")
    if not os.path.exists(tmp_wav):
        print("[*] Extracting reference audio for DTW...")
        extract_audio_for_dtw(input_path, tmp_wav)

    print("[*] Loading audio for DTW...")
    y_orig, _ = fast_load_mono(tmp_wav, TARGET_SR)
    y_skip, _ = fast_load_mono(skippy_audio_path, TARGET_SR)

    print("[*] Computing features...")
    S_orig, S_skip = compute_features(y_orig, TARGET_SR), compute_features(y_skip, TARGET_SR)

    print("[*] Running DTW...")
    wp = fast_subseq_dtw(S_orig, S_skip)

    print("[*] Building time map...")
    t_skip_map, t_orig_map = build_time_map_from_wp(wp)
    map_path = os.path.join(os.path.dirname(output_path), "map_t_skip_to_t_orig.npy")
    np.save(map_path, np.vstack([t_skip_map, t_orig_map]).T)
    print(f"[OK] Saved subtitle mapping: {map_path}")

    # Get skippy audio duration via ffprobe (fast, no moviepy)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", skippy_audio_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    target_dur = float(probe.stdout.strip())

    def map_t_skip_to_t_orig(t):
        return np.interp(t, t_skip_map, t_orig_map,
                         left=t_orig_map[0], right=t_orig_map[-1])

    eps = 1.0 / out_fps
    smear_frames = max(1, int(round((smear_ms / 1000.0) * video_fps)))

    total_frames = int(np.ceil(target_dur * out_fps))
    print(f"[*] Rendering frames: {total_frames} @ {out_fps:.3f} fps "
          f"(blend mode: {blend_mode})...")

    # ── Raw-frame pipe straight into ffmpeg for encoding ──
    # Avoids moviepy's per-frame Python/subprocess overhead entirely.
    width, height = src.width, src.height
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
        "-r", f"{out_fps:.6f}",
        "-i", "-",                      # video from stdin
        "-i", skippy_audio_path,        # audio from file
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "640k",
        "-shortest",
        output_path
    ]
    # ffmpeg's stderr must NOT be subprocess.PIPE here unless something is
    # continuously draining it. ffmpeg writes a constant stream of progress
    # info to stderr; if that pipe's OS buffer fills up with nobody reading
    # it, ffmpeg blocks on its own stderr write, which blocks it from reading
    # our stdin frames, which blocks OUR stdin.write()/flush() calls below.
    # Both processes deadlock waiting on each other -- exactly the kind of
    # silent freeze (0% CPU, no progress) seen in testing. Redirect to a log
    # file instead so ffmpeg can write freely with no reader required, and we
    # can still inspect it after the fact if something goes wrong.
    ffmpeg_log_path = os.path.join(os.path.dirname(output_path), "ffmpeg_encode.log")
    ffmpeg_log = open(ffmpeg_log_path, "wb")
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=ffmpeg_log)

    # ── Gap/stall detection state ──
    # During long renders, decoder stalls or cache-pressure hiccups can cause
    # a few consecutive output frames to come out near-identical (the "random
    # stops" / freezes you'd see in playback). Rather than just holding the
    # last good frame (which is what the old patch script did), we detect the
    # repeat and nudge the frame forward by blending toward the next available
    # source frame, so a stall reads as a brief soft transition instead of a
    # hard freeze.
    DUP_DIFF_THRESHOLD = 0.001   # mean abs pixel diff below this = "same frame"
                                  # This now targets TRUE bit-identical duplicate
                                  # frames (genuine decoder stalls) rather than an
                                  # arbitrary similarity magnitude. Real data from
                                  # an actual render: of 11,231 frames flagged at
                                  # the old threshold of 0.5, only 135 (1.2%) were
                                  # exactly 0.0 diff (truly identical frames), and
                                  # only 241 (2.1%) were under 0.001. The other
                                  # 97.9% were genuinely different frames that just
                                  # happened to look similar (slow motion, static
                                  # shots, compression noise) -- not stalls at all.
                                  # Magnitude thresholds (0.2/0.5/4.0) all mixed
                                  # real stalls and false positives together in
                                  # different proportions; this instead asks "is
                                  # this frame ACTUALLY identical to the last one"
                                  # which is what a genuine stall actually looks
                                  # like, and ignores everything else.
    MAX_DUP_RUN_NUDGE   = 6      # cap how many consecutive dups we'll nudge
    SCENE_CUT_THRESHOLD = 30.0   # mean abs pixel diff above this = real scene
                                  # cut, not continuous motion -- e.g. a hard
                                  # transition from black to color. Blending
                                  # across a genuine cut (subframe mode does
                                  # this unconditionally otherwise) produces a
                                  # 1-2 frame flicker: a dim, washed hybrid of
                                  # both frames. This is an estimated starting
                                  # point, not calibrated against real footage
                                  # the way DUP_DIFF_THRESHOLD was -- worth
                                  # adjusting if cuts still flicker or if
                                  # genuine fast-motion blending starts
                                  # snapping instead of blending.
    SUBFRAME_LOWFPS_THRESHOLD = 35.0  # output rates below this get a softer
                                        # blend (catches 23.976/29.97; leaves
                                        # 50/59.94 at full strength)
    SUBFRAME_LOWFPS_SCALE = 0.5        # scales the blend weight at low output
                                        # rates -- e.g. turns a 50% midpoint
                                        # blend into a 25% one. Subframe's full
                                        # continuous blend reads as smooth at
                                        # 50/59.94 but too strong/resampled-
                                        # looking at lower rates; this softens
                                        # it there while leaving 50/59.94
                                        # completely untouched.
    prev_out_frame = None
    dup_run_count = 0
    repaired_count = 0

    # ── Diagnostic log: one row PER OUTPUT FRAME (not just repaired ones) ──
    # Raising DUP_DIFF_THRESHOLD from 0.5 to 4.0 made jitter worse, which
    # means there's a real population of stalls somewhere in the 0.5-4.0
    # diff range we never actually saw, because the old log only recorded
    # frames that were ALREADY below the threshold being tested. Logging
    # every frame's mean_diff -- repaired or not -- gives us the full
    # distribution so the right cutoff can be picked from a real histogram
    # instead of guessed at twice in opposite directions.
    dup_log_path = os.path.join(os.path.dirname(output_path), "dup_repair_log.csv")
    dup_log = open(dup_log_path, "w", encoding="utf-8")
    dup_log.write("out_idx,t_out_sec,t_src_sec,frame_idx,mean_diff,repaired,dup_run_count\n")

    pbar = tqdm(total=total_frames, desc="Rendering frames", unit="frame")
    try:
        for out_idx in range(total_frames):
            t_out = out_idx / out_fps
            t_src = map_t_skip_to_t_orig(t_out)
            t_src = max(0.0, min(t_src, video_duration - eps))

            f_src = t_src * video_fps
            frame_idx = int(np.floor(f_src))
            frac = float(f_src - frame_idx)   # cast off numpy float64 to avoid
                                                # upcasting the whole frame array
                                                # to float64 in the blend math below

            if blend_mode == "none":
                out_frame = src.get(frame_idx)

            elif blend_mode == "subframe":
                # Premiere-style continuous blend: every output frame gets
                # its own weight based on exactly where it falls between
                # source frame A and source frame B. No on/off windowing.
                frame_a = src.get(frame_idx)
                frame_b = src.get(frame_idx + 1)
                cut_diff = float(np.abs(frame_a.astype(np.float32) - frame_b.astype(np.float32)).mean())
                if cut_diff > SCENE_CUT_THRESHOLD:
                    # Real scene cut, not continuous motion -- snap to the
                    # nearer frame instead of cross-fading across it.
                    # Uses the true (unscaled) frac -- this is about which
                    # real frame is temporally closer, not blend strength.
                    out_frame = frame_b if frac >= 0.5 else frame_a
                else:
                    effective_frac = (frac * SUBFRAME_LOWFPS_SCALE
                                       if out_fps < SUBFRAME_LOWFPS_THRESHOLD else frac)
                    out_frame = (1.0 - effective_frac) * frame_a + effective_frac * frame_b

            elif blend_mode == "forward":
                base_frame = src.get(frame_idx)
                if frame_idx > 0 and (frame_idx % blend_every) < smear_frames:
                    next_frame = src.get(frame_idx + 1)
                    out_frame = (1.0 - blend_alpha) * base_frame + blend_alpha * next_frame
                else:
                    out_frame = base_frame

            elif blend_mode == "backward":
                base_frame = src.get(frame_idx)
                if frame_idx > 0 and (frame_idx % blend_every) < smear_frames:
                    prev_frame = src.get(frame_idx - 1)
                    out_frame = (1.0 - blend_alpha) * base_frame + blend_alpha * prev_frame
                else:
                    out_frame = base_frame

            elif blend_mode == "bilateral":
                base_frame = src.get(frame_idx)
                if frame_idx > 0 and (frame_idx % blend_every) < smear_frames:
                    prev_frame = src.get(frame_idx - 1)
                    next_frame = src.get(frame_idx + 1)
                    out_frame = 0.5 * prev_frame + 0.5 * next_frame
                    out_frame = (1.0 - blend_alpha) * base_frame + blend_alpha * out_frame
                else:
                    out_frame = base_frame

            elif blend_mode == "motion":
                # Motion-adaptive: blend more where the frame actually changed,
                # less on static backgrounds (reduces ghosting on still areas).
                base_frame = src.get(frame_idx)
                if frame_idx > 0 and (frame_idx % blend_every) < smear_frames:
                    next_frame = src.get(frame_idx + 1)
                    diff = np.abs(next_frame - base_frame)
                    motion_mask = np.clip(diff.mean(axis=2, keepdims=True) / 32.0, 0.0, 1.0)
                    local_alpha = blend_alpha * motion_mask
                    out_frame = (1.0 - local_alpha) * base_frame + local_alpha * next_frame
                else:
                    out_frame = base_frame

            else:
                out_frame = src.get(frame_idx)

            # ── Gap/stall repair: detect a near-duplicate of the previous
            # output frame (a sign the decoder stalled/repeated under load)
            # and nudge it toward the next source frame instead of letting
            # it freeze. This replaces the old "hold the last good frame"
            # patch with something that reads as a brief soft blend instead.
            if prev_out_frame is not None:
                mean_diff = float(np.abs(out_frame - prev_out_frame).mean())
                was_repaired = 0
                if mean_diff < DUP_DIFF_THRESHOLD and dup_run_count < MAX_DUP_RUN_NUDGE:
                    dup_run_count += 1
                    nudge_amount = min(0.15 * dup_run_count, 0.6)
                    try:
                        lookahead_frame = src.get(frame_idx + 1 + dup_run_count)
                        # Don't nudge across a real scene cut -- if the
                        # lookahead frame belongs to a different scene
                        # entirely (e.g. a stretch of flat black right
                        # before a hard cut to color), blending toward it
                        # bleeds the new scene's content into frames that
                        # should still be black, reading as a flicker
                        # right at the transition.
                        lookahead_diff = float(np.abs(
                            lookahead_frame.astype(np.float32) - out_frame
                        ).mean())
                        if lookahead_diff <= SCENE_CUT_THRESHOLD:
                            out_frame = (1.0 - nudge_amount) * out_frame + nudge_amount * lookahead_frame
                            repaired_count += 1
                            was_repaired = 1
                        # else: leave out_frame as-is (a brief duplicate
                        # reads far better than bleeding in the wrong scene)
                    except Exception:
                        pass  # if lookahead isn't available, just leave as-is
                else:
                    dup_run_count = 0
                # Log every frame's diff, not just repaired ones -- this is
                # what lets us see the full distribution afterward instead
                # of only the slice that happened to cross whatever
                # threshold was set for THIS particular run.
                dup_log.write(f"{out_idx},{t_out:.4f},{t_src:.4f},{frame_idx},"
                               f"{mean_diff:.4f},{was_repaired},{dup_run_count}\n")

            out_frame = np.clip(out_frame, 0, 255).astype(np.uint8)
            prev_out_frame = out_frame.astype(np.float32)

            try:
                proc.stdin.write(out_frame.tobytes())
                proc.stdin.flush()   # force backpressure: block here if ffmpeg
                                      # can't keep up, instead of letting writes
                                      # queue up faster than the encoder consumes
            except (BrokenPipeError, OSError) as e:
                ffmpeg_log.flush()
                try:
                    with open(ffmpeg_log_path, "rb") as f:
                        stderr_out = f.read().decode(errors="replace")
                except Exception:
                    stderr_out = "(could not read ffmpeg log file)"
                raise RuntimeError(
                    f"ffmpeg encoder pipe closed unexpectedly at frame {out_idx}/{total_frames}. "
                    f"ffmpeg log (tail):\n{stderr_out[-2000:]}"
                ) from e

            # Explicitly drop references so numpy can reclaim this frame's
            # memory immediately rather than waiting for the next loop
            # iteration's assignment to overwrite the name.
            del out_frame
            pbar.update(1)
    finally:
        pbar.close()
        proc.stdin.close()
        proc.wait()
        ffmpeg_log.close()
        dup_log.close()
        src.release()

    try: os.remove(tmp_wav)
    except: pass
    if proc.returncode != 0:
        try:
            with open(ffmpeg_log_path, "rb") as f:
                tail = f.read().decode(errors="replace")[-2000:]
        except Exception:
            tail = "(could not read ffmpeg log file)"
        raise RuntimeError(
            f"ffmpeg exited with code {proc.returncode}. ffmpeg log (tail):\n{tail}"
        )
    if repaired_count > 0:
        print(f"[*] Repaired {repaired_count} stalled/duplicate frames during render.")
        print(f"[*] Repair diagnostic log written to: {dup_log_path}")
    print(f"[DONE] Video saved: {output_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-s", "--skippy", required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--blend-mode", default="subframe",
                     choices=["subframe", "forward", "backward", "bilateral", "motion", "none"],
                     help="subframe = Premiere-style continuous blend (default)")
    ap.add_argument("--blend-alpha", type=float, default=MICRO_BLEND_ALPHA,
                     help="Blend strength for forward/backward/bilateral modes")
    ap.add_argument("--blend-every", type=int, default=MICRO_BLEND_FRAMES,
                     help="Apply smear every N frames (forward/backward modes only)")
    ap.add_argument("--smear-ms", type=float, default=SMEAR_DURATION_MS,
                     help="Smear window duration in ms (forward/backward modes only)")
    ap.add_argument("--output-fps", type=float, default=None,
                     help="Output frame rate (default: 59.94 if not specified)")
    args = ap.parse_args()
    time_compress_video(args.input, args.skippy, args.output,
                         blend_mode=args.blend_mode,
                         blend_alpha=args.blend_alpha,
                         blend_every=args.blend_every,
                         smear_ms=args.smear_ms,
                         output_fps=args.output_fps)

if __name__ == "__main__":
    main()
