@echo off
cd /d "C:\Users\Owner\TempoCut_ffmpeg_experiment"

echo ============================================
echo Cleaning previous build...
echo ============================================
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo ============================================
echo Building with PyInstaller...
echo ============================================
pyinstaller --clean tempocut.spec
if errorlevel 1 (
    echo PyInstaller build failed
    pause
    exit /b 1
)

echo ============================================
echo Building installer with Inno Setup...
echo ============================================
"C:\Program Files\Inno Setup 7\ISCC.exe" TempoCut.iss
if errorlevel 1 (
    echo Inno Setup build failed
    pause
    exit /b 1
)

echo ============================================
echo Build complete!
echo ============================================
pause
