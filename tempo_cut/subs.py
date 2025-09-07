import sys
import numpy as np
import pysrt

def map_time(t, t_skip, t_orig):
    return np.interp(t, t_orig, t_skip)

def retime_subs(map_file, input_srt, output_srt):
    # Load the 2D array
    arr = np.load(map_file, allow_pickle=True)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("Expected a 2D array with 2 columns (t_skip, t_orig).")

    t_skip = arr[:, 0]
    t_orig = arr[:, 1]

    subs = pysrt.open(input_srt)

    for sub in subs:
        start_sec = sub.start.ordinal / 1000.0
        end_sec   = sub.end.ordinal / 1000.0

        new_start = map_time(start_sec, t_skip, t_orig)
        new_end   = map_time(end_sec, t_skip, t_orig)

        # Safety: no negative times and avoid zero-length subs
        new_start = max(0, new_start)
        new_end   = max(new_start + 0.1, new_end)

        sub.start.ordinal = int(new_start * 1000)
        sub.end.ordinal   = int(new_end * 1000)

    subs.save(output_srt, encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python retime_subs.py <map.npy> <input.srt> <output.srt>")
        sys.exit(1)

    map_file, input_srt, output_srt = sys.argv[1:4]
    retime_subs(map_file, input_srt, output_srt)
    print(f"✅ Subtitles retimed and saved to {output_srt}")
