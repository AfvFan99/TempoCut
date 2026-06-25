# tempo_gui.py
from gooey import Gooey, GooeyParser
import subprocess
import sys
import shlex

@Gooey(program_name="TempoCut GUI", default_size=(720, 600))
def main():
    p = GooeyParser(description="Time-compress audio/video with tempocut + ffmpeg")
    p.add_argument("-i", "--input",  required=True, help="Input file", widget="FileChooser")
    p.add_argument("-o", "--output", required=True, help="Output file", widget="FileSaver")
    p.add_argument("--target-ratio", type=float, default=1.02, help="Speed-up ratio (e.g. 1.03)")
    p.add_argument("--frame-ms",     type=int,   default=20)
    p.add_argument("--max-chop-ms",  type=int,   default=25)
    p.add_argument("--cadence-ms",   type=int,   default=300)
    p.add_argument("--crossfade-ms", type=int,   default=8)
    p.add_argument("--energy-quantile", type=float, default=0.4)

    args = p.parse_args()

    # Example: call your existing CLI exactly how you do in cmd.exe
    cmd = f'python audio_skippy_SURROUND.py -i "{args.input}" -o "{args.output}" ' \
          f'--target-ratio {args.target_ratio} --frame-ms {args.frame_ms} ' \
          f'--max-chop-ms {args.max_chop_ms} --cadence-ms {args.cadence_ms} ' \
          f'--crossfade-ms {args.crossfade_ms} --energy-quantile {args.energy_quantile}'

    try:
        # show live stdout in Gooey console
        proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            print(line, end="")
        sys.exit(proc.wait())
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
