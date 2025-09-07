import argparse, subprocess, sys, shutil, os

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PY = shutil.which("python") or sys.executable

def run(cmd):
    print("> " + " ".join(cmd))
    return subprocess.call(cmd)

def cmd_audio(args):
    script = os.path.join(ROOT, "tempo_cut", "audio_stereo.py" if args.stereo else "audio_surround.py")
    cmd = [PY, script, "-i", args.input, "-o", args.output, "--target-ratio", str(args.target_ratio)]
    if args.frame_ms is not None:        cmd += ["--frame-ms", str(args.frame_ms)]
    if args.max_chop_ms is not None:     cmd += ["--max-chop-ms", str(args.max_chop_ms)]
    if args.cadence_ms is not None:      cmd += ["--cadence-ms", str(args.cadence_ms)]
    if args.crossfade_ms is not None:    cmd += ["--crossfade-ms", str(args.crossfade_ms)]
    if args.energy_quantile is not None: cmd += ["--energy-quantile", str(args.energy_quantile)]
    sys.exit(run(cmd))

def cmd_video(args):
    script = os.path.join(ROOT, "tempo_cut", "video.py")
    cmd = [PY, script, "-i", args.input_video, "-s", args.input_audio, "-o", args.output]
    sys.exit(run(cmd))

def cmd_subs(args):
    script = os.path.join(ROOT, "tempo_cut", "subs.py")
    cmd = [PY, script, args.map, args.input_srt, args.output_srt]
    sys.exit(run(cmd))

def cmd_pipeline(args):
    # 1) video retime
    ret = run([PY, os.path.join(ROOT, "tempo_cut", "video.py"),
               "-i", args.input_video, "-s", args.input_audio, "-o", args.temp_out])
    if ret:
        sys.exit(ret)

    # 2) mux with ffmpeg
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ERROR: ffmpeg not found in PATH")
        sys.exit(1)
    ret = run([ffmpeg, "-y", "-i", args.temp_out, "-i", args.input_audio,
               "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "512k", args.output_video])
    if ret:
        sys.exit(ret)

    # 3) subtitle retime (optional)
    if args.input_srt and os.path.exists(args.input_srt):
        map_file = "map_t_skip_to_t_orig.npy"
        if os.path.exists(map_file):
            ret = run([PY, os.path.join(ROOT, "tempo_cut", "subs.py"),
                       map_file, args.input_srt, args.output_srt])
            if ret:
                ffsubsync = shutil.which("ffsubsync")
                if ffsubsync:
                    run([ffsubsync, args.output_video, "--sub", args.input_srt, "-o", args.output_srt])
        else:
            print("WARN: map file not found; skipping subtitle retime")
    # 4) cleanup
    try:
        os.remove(args.temp_out)
    except OSError:
        pass

def build_parser():
    p = argparse.ArgumentParser(prog="tempocut", description="Broadcast-style A/V time compression")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audio", help="Time compress audio (skippy)")
    a.add_argument("-i","--input", required=True)
    a.add_argument("-o","--output", required=True)
    a.add_argument("--target-ratio", type=float, required=True)
    a.add_argument("--stereo", action="store_true", help="Use stereo engine (default is surround)")
    a.add_argument("--frame-ms", type=float)
    a.add_argument("--max-chop-ms", type=float)
    a.add_argument("--cadence-ms", type=float)
    a.add_argument("--crossfade-ms", type=float)
    a.add_argument("--energy-quantile", type=float)
    a.set_defaults(func=cmd_audio)

    v = sub.add_parser("video", help="Retime video to skippy audio (59.94p)")
    v.add_argument("-i","--input-video", required=True)
    v.add_argument("-s","--input-audio", required=True)
    v.add_argument("-o","--output", required=True)
    v.set_defaults(func=cmd_video)

    s = sub.add_parser("subs", help="Retime SRT using warp map")
    s.add_argument("map")
    s.add_argument("input_srt")
    s.add_argument("output_srt")
    s.set_defaults(func=cmd_subs)

    pl = sub.add_parser("pipeline", help="One-shot: video retime + mux + subs")
    pl.add_argument("--input-video", default="input.mp4")
    pl.add_argument("--input-audio", default="input.wav")
    pl.add_argument("--input-srt", default="input.srt")
    pl.add_argument("--temp-out", default="output_temp.mp4")
    pl.add_argument("--output-video", default="output_final.mp4")
    pl.add_argument("--output-srt", default="output_final.srt")
    pl.set_defaults(func=cmd_pipeline)

    return p

def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)

if __name__ == "__main__":
    main()
