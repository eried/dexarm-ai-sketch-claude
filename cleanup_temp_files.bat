@echo off
REM ============================================
REM Cleanup Script for AI Sketch Booth
REM Removes temporary and cache files
REM ============================================

echo Cleaning up temporary files...

REM Remove Python cache directories
echo Removing Python cache files...
del /s /q __pycache__\*.pyc 2>NUL
rmdir /s /q __pycache__ 2>NUL
rmdir /s /q dexarm_tests\__pycache__ 2>NUL

REM Remove Potrace temporary .pbm files
echo Removing Potrace temporary files...
del svgs\*.pbm 2>NUL

REM Remove optimized SVG temporary files
echo Removing optimized SVG temporary files...
del svgs\*_optimized.svg 2>NUL

REM Note: Do NOT remove the following as they contain user data:
REM - photos\*.jpg (user photos)
REM - caricatures\*.png (generated caricatures)
REM - svgs\drawing_*.svg (SVG drawings for robot arm)
REM - dexarm_config.json (robot arm calibration)

echo.
echo Cleanup complete!
echo.
echo Files removed:
echo - Python cache (.pyc files, __pycache__ directories)
echo - Potrace temporary files (.pbm)
echo - Optimized SVG temporary files (*_optimized.svg)
echo.
echo User data preserved (photos, caricatures, SVG drawings, calibration)
pause
