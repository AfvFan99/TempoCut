#!/usr/bin/env bash
set -euo pipefail

VIDEO="${1:-input.mp4}"
AUDIO="${2:-input.wav}"
SRT="${3:-input.srt}"
TEMP="output_temp.mp4"
OUT="output_final.mp4"
OUTSRT="output_final.srt"

# 1) video retime (via CLI -> underlying Python module)
tempocut video -i "$VIDEO" -s "$AUDIO" -o "$TEMP"

# 2) mux
ffmpeg -y -i "$TEMP" -i "$AUDIO" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 512k "$OUT"

# 3) subs if present and map exists
if [[ -f "$SRT" && -f "map_t_skip_to_t_orig.npy" ]]; then
  tempocut subs map_t_skip_to_t_orig.npy "$SRT" "$OUTSRT"
fi

rm -f "$TEMP"
echo "Done -> $OUT"
