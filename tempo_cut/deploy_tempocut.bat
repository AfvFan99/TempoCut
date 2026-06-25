@echo off
setlocal

rem ============================================================
rem  TempoCut -- deploy fresh build into the GitHub repo folder
rem ============================================================
rem  This mirrors the PyInstaller build output (the exe PLUS the
rem  companion scripts and icon it needs to actually run) into
rem  the repo, replacing everything except the .git folder
rem  itself. Git history is never touched by the copy step.
rem ============================================================

set BUILD_SRC=C:\Users\Owner\TempoCut_ffmpeg_experiment\dist\TempoCut
set REPO_DEST=C:\Users\Owner\Final Time Compressor Draft\tempo_cut

echo.
echo ================================================================
echo  Source (new build):  %BUILD_SRC%
echo  Destination (repo):  %REPO_DEST%
echo ================================================================
echo.
echo This will make the repo folder an EXACT match of the new build
echo (adds/updates new files, deletes anything no longer present).
echo The .git folder itself will NOT be touched.
echo.
pause

if not exist "%BUILD_SRC%" (
    echo.
    echo [!] Build folder not found: %BUILD_SRC%
    echo [!] Run the pyinstaller build first, then re-run this script.
    echo.
    pause
    exit /b 1
)

if not exist "%REPO_DEST%" (
    echo.
    echo [!] Repo folder not found: %REPO_DEST%
    echo [!] Check the path is right, then re-run this script.
    echo.
    pause
    exit /b 1
)

echo.
echo [*] Mirroring build into repo folder...
robocopy "%BUILD_SRC%" "%REPO_DEST%" /MIR /XD .git /R:2 /W:2 /NFL /NDL

rem robocopy's exit codes 0-7 all mean "success" in various forms
rem (8+ means something actually went wrong)
if %ERRORLEVEL% GEQ 8 (
    echo.
    echo [!] robocopy reported an error (code %ERRORLEVEL%). Stopping before touching git.
    echo.
    pause
    exit /b 1
)

echo.
echo [*] Copy complete.
echo.

cd /d "%REPO_DEST%"

echo [*] Staging changes...
git add -A

echo.
echo [*] Changes staged. Showing what will be committed:
echo.
git status --short

echo.
echo ================================================================
echo  Review the file list above.
echo  Next step will COMMIT (but not yet push) those changes.
echo ================================================================
pause

git commit -m "Update build: stop button, fps auto-detect, jitter fix, new icon"

echo.
echo ================================================================
echo  Committed locally. NOT pushed yet.
echo  Run this manually when you're ready to actually push to GitHub:
echo.
echo      git push
echo.
echo ================================================================
echo.
pause
