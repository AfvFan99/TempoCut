@echo off
setlocal

REM === INPUTS ===
set PYTHON_SCRIPT=C:\Users\Owner\Final Time Compressor Draft\time_compressor_SAFE.py
set RETIME_SCRIPT=C:\Users\Owner\Final Time Compressor Draft\retime_subs.py
set MAP_FILE=D:\SBS2025 Prints\map_t_skip_to_t_orig.npy

set INPUT_VIDEO="D:\SBS2025 Prints\AFHV2106.mp4"
set INPUT_AUDIO="D:\SBS2025 Prints\AFHV2106_light.wav"
set INPUT_SUBS="D:\SBS2025 Prints\AFHV2106.mp4.srt"

set TEMP_OUTPUT="D:\SBS2025 Prints\output_tbs_59p.mp4"
set FINAL_OUTPUT="D:\SBS2025 Prints\AFHV2106_FINAL.mp4"
set FINAL_SUBS="D:\SBS2025 Prints\AFHV2106_FINAL.srt"

REM === STEP 1: Python compressor (59.94p with smears) ===
echo 🔹 Step 1: Python compressor @59.94p...
python "%PYTHON_SCRIPT%" -i %INPUT_VIDEO% -s %INPUT_AUDIO% -o %TEMP_OUTPUT%
if errorlevel 1 (
    echo ❌ Python compressor failed.
    pause & exit /b
)

REM === STEP 2: Mux 5.1 audio ===
echo 🔹 Step 2: Muxing 5.1 audio...
ffmpeg -y -i %TEMP_OUTPUT% -i %INPUT_AUDIO% -map 0:v -map 1:a ^
  -c:v copy -c:a aac -b:a 512k %FINAL_OUTPUT%
if errorlevel 1 (
    echo ❌ Muxing failed.
    pause & exit /b
)

REM === STEP 3: Retiming subtitles (new retime_subs.py) ===
if exist %INPUT_SUBS% (
    echo 🔹 Step 3: Retiming subtitles with warp map...
    python "%RETIME_SCRIPT%" "%MAP_FILE%" %INPUT_SUBS% %FINAL_SUBS%
    if errorlevel 1 (
        echo ⚠️ retime_subs.py failed, falling back to ffsubsync...
        ffsubsync %FINAL_OUTPUT% --sub %INPUT_SUBS% -o %FINAL_SUBS%
    ) else (
        echo ✅ Subtitles retimed and saved to %FINAL_SUBS%
    )
) else (
    echo ⚠️ No input subtitles found, skipping.
)

REM === STEP 4: Cleanup ===
echo 🔹 Step 4: Cleaning up temp files...
del %TEMP_OUTPUT%

echo ✅ Done! Final file: %FINAL_OUTPUT%
pause
