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
echo ===== Running tests (scene flow / autoplay result / marks / best record) =====
echo The app must already be running (run 1_install_and_launch.bat first).
echo.
pytest -v --ignore=test_full_scenario.py

echo.
echo Result file: tests\reports\test_results.xlsx
echo Failure screenshots: tests\reports\FAIL_*.png
pause
