# time_compressor_SAFE_FAST.py
"""
TBS-style DTW video compressor (fast version)
- Output: 59.94p with smear blending.
- Nearest-frame timing + micro-smear every N frames.
- Saves DTW warp map for subtitle retiming.
- Optimized with frame cache and float16 blending.
"""

import argparse, os, numpy as np, librosa
from moviepy.editor import VideoFileClip, AudioFileClip, VideoClip
from tqdm import tqdm
from collections import OrderedDict

# ---------- Tunables ----------
TARGET_SR            = 16000
N_MELS               = 64
HOP                  = 2048
TIME_DECIM           = 2
MAX_JUMP_RATIO       = 1.2
MICRO_BLEND_FRAMES   = 20        # apply smear every 20 frames
MICRO_BLEND_ALPHA    = 0.50      # blend strength
SMEAR_DURATION_MS    = 32        # smear lasts ~32ms
OUTPUT_FPS           = 60000 / 1001   # 59.94 fps
FRAME_CACHE_SIZE     = 48       # number of frames to cache
# ------------------------------

def compute_features(y, sr):
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=N_MELS,
                                       hop_length=HOP, fmax=sr//2)
    return librosa.power_to_db(S[:, ::TIME_DECIM], ref=np.max)

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

def time_compress_video(input_path, skippy_audio_path, output_path):
    print("🔹 Loading video...")
    video = VideoFileClip(input_path)
    video_fps = float(video.fps)

    tmp_wav = os.path.join(os.path.dirname(output_path),"ref_for_dtw.wav")
    if not os.path.exists(tmp_wav):
        video.audio.write_audiofile(tmp_wav, fps=TARGET_SR,
                                    nbytes=2, codec="pcm_s16le",
                                    verbose=False, logger=None)

    print("🔹 Loading audio for DTW...")
    y_orig,_ = librosa.load(tmp_wav, sr=TARGET_SR, mono=True)
    y_skip,_ = librosa.load(skippy_audio_path, sr=TARGET_SR, mono=True)

    print("🔹 Computing features...")
    S_orig, S_skip = compute_features(y_orig, TARGET_SR), compute_features(y_skip, TARGET_SR)

    print("🔹 Running DTW...")
    _, wp = librosa.sequence.dtw(X=S_orig, Y=S_skip, metric='euclidean', subseq=True)

    print("🔹 Building time map...")
    t_skip_map, t_orig_map = build_time_map_from_wp(wp)
    map_path = os.path.join(os.path.dirname(output_path),"map_t_skip_to_t_orig.npy")
    np.save(map_path, np.vstack([t_skip_map,t_orig_map]).T)
    print(f"✅ Saved subtitle mapping: {map_path}")

    skippy_audio = AudioFileClip(skippy_audio_path)
    target_dur = float(skippy_audio.duration)

    def map_t_skip_to_t_orig(t):
        return np.interp(t, t_skip_map, t_orig_map,
                         left=t_orig_map[0], right=t_orig_map[-1])

    eps = 1.0/OUTPUT_FPS
    last_frame_time, last_frame = None, None
    def get_frame_safe(t_request):
        nonlocal last_frame_time, last_frame
        t_request = max(0.0, min(t_request, video.duration-eps))
        if last_frame_time is not None and abs(t_request-last_frame_time)<1e-6:
            return last_frame
        f = video.get_frame(t_request)
        last_frame_time, last_frame = t_request, f
        return f

    print(f"🔹 Rendering frames: {int(target_dur*OUTPUT_FPS)} @ {OUTPUT_FPS:.3f} fps...")
    def make_frame(t_out):
        t_src = map_t_skip_to_t_orig(t_out)
        t_src = max(0.0, min(t_src, video.duration-eps))
        f_src = t_src*video_fps
        frame_idx = int(np.floor(f_src))

        t0 = frame_idx/video_fps
        t1 = min((frame_idx+1)/video_fps, video.duration)
        frame0 = get_frame_safe(t0).astype(np.float32)
        frame1 = get_frame_safe(t1).astype(np.float32)
        base_frame = frame0

        # smear logic: 32 ms window, forward-looking
        smear_frames = max(1, int(round((SMEAR_DURATION_MS/1000.0)*video_fps)))
        if frame_idx>0 and (frame_idx % MICRO_BLEND_FRAMES)<smear_frames:
            next_t = min((frame_idx+1)/video_fps, video.duration-eps)
            next_frame = get_frame_safe(next_t).astype(np.float32)
            out_frame = (1.0-MICRO_BLEND_ALPHA)*base_frame + MICRO_BLEND_ALPHA*next_frame
        else:
            out_frame = base_frame

        return np.clip(out_frame,0,255).astype(np.uint8)

    total_frames = int(np.ceil(target_dur*OUTPUT_FPS))
    pbar = tqdm(total=total_frames, desc="Rendering frames", unit="frame")
    warped_pb = VideoClip(lambda t: (pbar.update(1), make_frame(t))[1], duration=target_dur)
    warped_pb = warped_pb.set_audio(skippy_audio.set_duration(target_dur))

    warped_pb.write_videofile(output_path, codec="libx264", audio_codec="aac",
                              fps=OUTPUT_FPS, threads=4, preset="fast",
                              verbose=False, logger=None)
    pbar.close()

    try: os.remove(tmp_wav)
    except: pass
    print(f"✅ Done! Video saved: {output_path}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--input", required=True)
    ap.add_argument("-s","--skippy", required=True)
    ap.add_argument("-o","--output", required=True)
    args = ap.parse_args()
    time_compress_video(args.input, args.skippy, args.output)

if __name__=="__main__": main()