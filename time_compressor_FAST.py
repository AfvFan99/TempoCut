import sys
import numpy as np
from moviepy.editor import VideoFileClip
import cv2

# ✅ Take input/output paths from command line
if len(sys.argv) < 3:
    print("Usage: python time_compressor_FAST.py <input_video> <output_video>")
    sys.exit(1)

INPUT_FILE = sys.argv[1]
OUTPUT_FILE = sys.argv[2]

# Load video
video = VideoFileClip(INPUT_FILE)

# Strengthened smear: blend each frame with the NEXT 20 frames
def smear_frame(get_frame, t):
    frame = get_frame(t)
    h, w, c = frame.shape
    acc = np.zeros((h, w, c), dtype=np.float32)
    count = 0
    # Look ahead up to 20 frames (≈ 32ms @59.94p)
    for i in range(20):
        t_offset = t + i / video.fps
        if t_offset < video.duration:
            acc += get_frame(t_offset).astype(np.float32)
            count += 1
    return np.clip(acc / count, 0, 255).astype(np.uint8)

smeared = video.fl(lambda gf, t: smear_frame(gf, t))

# Export at same fps
smeared.write_videofile(
    OUTPUT_FILE,
    codec="libx264",
    fps=video.fps,
    preset="fast",
    bitrate="6000k",
    audio=False
)
