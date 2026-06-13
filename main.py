"""
리듬게임 테스트 자동화 메인
사용법:
  python main.py                        # 실기기 (R3CR501XHAJ)
  python main.py emulator-5554          # AVD
  python main.py R3CR501XHAJ emulator-5554  # 복수 기기 순차 실행
  python main.py --skip-build emulator-5554  # 빌드 생략
"""
import os
import sys
import subprocess
import common.driver_setup as ds
from common.driver_setup import create_driver
from common.result_writer import init_workbook
from tests import test_autoplay, test_result_screen, test_navigation

ADB    = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "platform-tools", "adb.exe")
GODOT  = r"D:\Godot_v4.4.1-stable_win64.exe\Godot_v4.4.1-stable_win64_console.exe"
PROJECT = r"D:\Godot\RhythmGame_New\Godot"
APK    = r"D:\Automation\apk\RhythmGame_debug.apk"
os.makedirs("screenshots", exist_ok=True)


def build_apk() -> None:
    print("  Godot 빌드 중...")
    subprocess.run(
        [GODOT, "--headless", "--export-debug", "Android", APK, "--path", PROJECT],
        check=True
    )
    print("  빌드 완료")


def adb_forward(device: str) -> None:
    subprocess.run([ADB, "-s", device, "forward", "tcp:5000", "tcp:5000"], check=True)
    print(f"  adb forward tcp:5000:tcp:5000 ({device})")


def run_all(device_name: str) -> None:
    ds.capabilities["deviceName"] = device_name

    print(f"  APK 설치 중...")
    subprocess.run([ADB, "-s", device_name, "install", "-r", APK], check=True)

    print(f"  포트 포워딩...")
    adb_forward(device_name)

    driver = create_driver()
    wb, ws = init_workbook(device_name)

    try:
        case_num = 0
        case_num = test_autoplay.run(driver, wb, ws, case_num)
        case_num = test_result_screen.run(driver, wb, ws, case_num)
        case_num = test_navigation.run(driver, wb, ws, case_num)
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    args = sys.argv[1:]
    skip_build = "--skip-build" in args
    devices = [a for a in args if not a.startswith("--")] or ["R3CR501XHAJ"]

    if not skip_build:
        build_apk()

    for device in devices:
        print(f"\n{'='*50}")
        print(f"  기기: {device}")
        print(f"{'='*50}")
        run_all(device)
    print("\n모든 기기 테스트 완료. 결과: test_results.xlsx")
