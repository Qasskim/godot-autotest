# -*- coding: utf-8 -*-
"""Godot TestServer HTTP 클라이언트 래퍼"""

import base64
import time
import urllib.request
import urllib.parse
import json

HOST = "http://127.0.0.1:5000"
DEFAULT_TIMEOUT = 5


def _req(method: str, path: str, timeout=DEFAULT_TIMEOUT) -> dict:
    req = urllib.request.Request(HOST + path, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def ping() -> bool:
    try:
        return _req("GET", "/ping").get("status") == "ok"
    except Exception:
        return False


def scene() -> str:
    return _req("GET", "/scene").get("scene", "")


def game_state() -> dict:
    return _req("GET", "/game_state")


def result() -> dict:
    return _req("GET", "/result")


def best(song_id: str, difficulty: str, platform: str = "android") -> dict:
    qs = urllib.parse.urlencode({"song_id": song_id, "difficulty": difficulty, "platform": platform})
    return _req("GET", f"/best?{qs}")


def navigate(target: str) -> dict:
    return _req("POST", f"/navigate/{target}")


def tap(action: str) -> dict:
    return _req("POST", f"/tap/{action}")


def autoplay(on: bool) -> dict:
    return _req("POST", f"/autoplay/{'on' if on else 'off'}")


def autoremix(on: bool) -> dict:
    return _req("POST", f"/autoremix/{'on' if on else 'off'}")


# ── MainMenu ──────────────────────────────────────────────────────
def tap_mainmenu_play() -> dict:
    return _req("POST", "/tap/mainmenu_play")


def tap_mainmenu_settings() -> dict:
    return _req("POST", "/tap/mainmenu_settings")


def tap_mainmenu_back() -> dict:
    return _req("POST", "/tap/mainmenu_back")


def tap_mainmenu_quit() -> dict:
    return _req("POST", "/tap/mainmenu_quit")


# ── Settings ──────────────────────────────────────────────────────
def tap_settings_back() -> dict:
    return _req("POST", "/tap/settings_back")


def tap_settings_calibrate_open() -> dict:
    return _req("POST", "/tap/settings_calibrate_open")


def tap_settings_calibrate_tap() -> dict:
    return _req("POST", "/tap/settings_calibrate_tap")


def tap_settings_calibrate_retry() -> dict:
    return _req("POST", "/tap/settings_calibrate_retry")


def tap_settings_calibrate_apply() -> dict:
    return _req("POST", "/tap/settings_calibrate_apply")


def tap_settings_calibrate_close() -> dict:
    return _req("POST", "/tap/settings_calibrate_close")


# ── SongSelect ────────────────────────────────────────────────────
def tap_songselect_tab_world() -> dict:
    return _req("POST", "/tap/songselect_tab_world")


def tap_songselect_tab_my() -> dict:
    return _req("POST", "/tap/songselect_tab_my")


def tap_songselect_tab_rival() -> dict:
    return _req("POST", "/tap/songselect_tab_rival")


def tap_songselect_debug_open() -> dict:
    return _req("POST", "/tap/songselect_debug_open")


def tap_songselect_debug_close() -> dict:
    return _req("POST", "/tap/songselect_debug_close")


def tap_songselect_back() -> dict:
    return _req("POST", "/tap/songselect_back")


def songs() -> dict:
    """SongSelect 화면이 지금 렌더링한 곡 목록을 그 자리에서 라이브 조회 (캐싱 없음)."""
    return _req("GET", "/songs")


def tap_song_at(index: int) -> dict:
    return _req("POST", f"/tap/song_at?index={index}")


# ── GameScene 포즈 오버레이 ──────────────────────────────────────────
def tap_pause_toggle() -> dict:
    return _req("POST", "/tap/pause_toggle")


def tap_pause_speed_up() -> dict:
    return _req("POST", "/tap/pause_speed_up")


def tap_pause_speed_down() -> dict:
    return _req("POST", "/tap/pause_speed_down")


def pause_calibration(value: float) -> dict:
    return _req("POST", f"/pause/calibration?value={value}")


def tap_pause_quit() -> dict:
    return _req("POST", "/tap/pause_quit")


# ── GameScene 터치존 ─────────────────────────────────────────────────
def touchzone(on: bool) -> dict:
    return _req("POST", f"/touchzone/{'on' if on else 'off'}")


def screenshot(save_path: str) -> bool:
    try:
        data = _req("GET", "/screenshot", timeout=10)
        b64 = data.get("png_base64", "")
        if not b64:
            return False
        with open(save_path, "wb") as f:
            f.write(base64.b64decode(b64))
        return True
    except Exception as e:
        print(f"[screenshot] 실패: {e}")
        return False


def wait_for_scene(expected: str, timeout: float = 15.0, interval: float = 0.5) -> bool:
    """씬이 expected로 전환될 때까지 대기. 타임아웃 시 False."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if scene() == expected:
            return True
        time.sleep(interval)
    return False


def wait_for_shutdown(timeout: float = 15.0, interval: float = 0.5) -> bool:
    """QUIT 이후 서버가 응답을 멈출 때까지(=프로세스 정상 종료) 대기. 타임아웃 시 False."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not ping():
            return True
        time.sleep(interval)
    return False


def wait_game_finished(interval: float = 1.0) -> None:
    """/game_state가 finished=true 될 때까지 타임아웃 없이 폴링."""
    while True:
        try:
            if game_state().get("finished") is True:
                return
        except Exception:
            pass
        time.sleep(interval)
