"""
Godot TestServer HTTP API 클라이언트
베이스 URL: http://localhost:5000
사전 조건: adb forward tcp:5000 tcp:5000
"""
import time
import requests

BASE = "http://localhost:5000"
TIMEOUT = 5  # 단일 요청 타임아웃 (초)


def _get(path: str) -> dict:
    resp = requests.get(f"{BASE}{path}", timeout=TIMEOUT)
    return resp.json()


def _post(path: str) -> dict:
    resp = requests.post(f"{BASE}{path}", timeout=TIMEOUT)
    return resp.json()


def ping() -> bool:
    try:
        return _get("/ping").get("status") == "ok"
    except Exception:
        return False


def get_scene() -> str:
    return _get("/scene").get("scene", "")


def get_autoplay() -> bool:
    return _get("/autoplay").get("auto_play", False)


def get_result() -> dict:
    return _get("/result")


def autoplay_on() -> bool:
    return _post("/autoplay/on").get("ok", False)


def autoplay_off() -> bool:
    return _post("/autoplay/off").get("ok", False)


def navigate_main_menu() -> bool:
    return _post("/navigate/main_menu").get("ok", False)


def navigate_song_select() -> bool:
    return _post("/navigate/song_select").get("ok", False)


def tap_first_song() -> bool:
    return _post("/tap/first_song").get("ok", False)


def tap_play() -> bool:
    return _post("/tap/play").get("ok", False)


def tap_retry() -> bool:
    return _post("/tap/retry").get("ok", False)


def tap_select_song() -> bool:
    return _post("/tap/select_song").get("ok", False)


def wait_for_scene(scene_name: str, timeout: float = 30.0, interval: float = 1.0) -> bool:
    """씬 이름이 scene_name이 될 때까지 폴링. timeout 초 내에 도달하면 True."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if get_scene() == scene_name:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def wait_for_ping(timeout: float = 15.0, interval: float = 1.0) -> bool:
    """앱이 HTTP 응답을 줄 때까지 대기."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ping():
            return True
        time.sleep(interval)
    return False
