@echo off
setlocal

cd /d "%~dp0tests"

echo ===== Installing Python packages =====
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Package install failed. Check your Python/pip installation.
    pause
    exit /b 1
)

echo.
echo ===== Full scenario test =====
echo Covers every screen/button + full song list loop + clean app exit in one run.
echo NOTE: this test quits the app at the very end.
echo       Run 1_install_and_launch.bat again before testing further.
echo.
pytest test_full_scenario.py -v

echo.
echo Result file: tests\reports\test_results.xlsx
echo Failure screenshots: tests\reports\FAIL_*.png
pause
