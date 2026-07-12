@echo off
setlocal

set ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe
set APK=%~dp0apk\RhythmGame_debug.apk
set PKG=com.example.rhythmgame_new
set ACT=com.godot.game.GodotApp

if not exist "%ADB%" (
    echo [ERROR] adb.exe not found: %ADB%
    echo Please check your Android SDK Platform-Tools installation path.
    pause
    exit /b 1
)

echo ===== Checking connected device =====
"%ADB%" devices
echo.

echo ===== Installing APK =====
"%ADB%" install -r "%APK%"
if errorlevel 1 (
    echo [ERROR] APK install failed. Check USB debugging connection.
    pause
    exit /b 1
)

echo.
echo ===== Port forwarding (5000) =====
"%ADB%" forward tcp:5000 tcp:5000

echo.
echo ===== Keeping screen awake while USB is connected =====
echo (long test runs can otherwise let the device sleep and suspend the app)
"%ADB%" shell svc power stayon usb

echo.
echo ===== Restarting app =====
"%ADB%" shell am force-stop %PKG%
"%ADB%" shell am start -n %PKG%/%ACT%

echo.
echo App launched. Wait a moment, then run 2_run_tests.bat
pause
