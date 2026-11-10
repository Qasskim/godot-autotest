# -*- coding: utf-8 -*-
"""개발용/릴리스용 분리 — 엔진 인자 --hide-debug 가 개발 편의 화면 요소를 숨기는지 (기준 DESIGN §4 "개발용/릴리스용 분리", 2026-11-02·11-05, 시험 2026-11-10).

게임을 두 번 띄운다: 인자 없이(개발용 화면) / --hide-debug 를 주고(릴리스와 같은 화면).
곡 선택: DEBUG 버튼과 하단 F키 안내 글자, 게임 중: 좌하단 FPS 글자가 인자가 있으면 안 보이고 없으면 보이는지 본다.
숨기지 않는 것: 게임 중 AUTO 표시(자동 플레이를 켰다는 표시), 키보드 디버그 키와 TestServer(인자를 줘도 동작해야 이 시험이 돌 수 있다).
릴리스 APK 에서 실제로 숨겨지는지(OS.is_debug_build() == false)는 이 시험이 보지 못한다 — 릴리스 빌드는 PC 에서 띄울 수 없으므로 확인 필요: 릴리스 APK.
이 시험의 값(곡 SYNTHWAVE)은 사용자가 정한 값이 아니라 시험 작성자가 정했다. 서버·계정은 쓰지 않는다(--no-server).
"""
import time

import pytest

import client
from godot_runner import start_game, stop_game
from screen_helpers import labels, press, wait_until

pytestmark = pytest.mark.no_server      # 이 파일이 게임을 직접 띄운다(포트 5000을 쓰므로 다른 게임이 있으면 중단)

SONG = "SYNTHWAVE"


def buttons() -> list:
    return client.screen_buttons()


def open_song_select() -> None:
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)


def has_f_key_hint() -> bool:
    """하단 F키 안내(select_auto_off_hint / select_auto_on_hint)가 화면에 보이는지 — 'F' 키 이름이 든 글자를 찾는다."""
    return any("F1" in t or "F3" in t or "F4" in t for t in labels())


def fps_label_visible() -> bool:
    return any(t.startswith("FPS ") for t in labels())


def collect(extra_args: tuple) -> dict:
    proc = start_game(extra_args=extra_args)
    try:
        open_song_select()
        seen = {"debug_button": "DEBUG" in buttons(), "f_hint": has_f_key_hint()}
        client.tap_song_at(client.songs()["songs"].index(SONG))
        time.sleep(0.5)
        client.autoplay(True)
        press("PLAY")
        assert client.wait_for_scene("GameScene", timeout=30)
        assert wait_until(lambda: "AUTO" in labels() and not any(l in ("3", "2", "1") for l in labels()), timeout=20)
        time.sleep(1.0)       # FPS 글자는 매 프레임 갱신되므로 한 번 뜬 뒤에 읽는다
        seen["fps"] = fps_label_visible()
        seen["auto_badge"] = "AUTO" in labels()
        return seen
    finally:
        stop_game(proc)


@pytest.fixture(scope="module")
def dev_screen():
    return collect(())


@pytest.fixture(scope="module")
def hidden_screen():
    return collect(("--hide-debug",))


def test_without_the_switch_dev_ui_is_shown(dev_screen):
    assert dev_screen["debug_button"], f"인자 없이 띄웠는데 DEBUG 버튼이 안 보입니다: {dev_screen}"
    assert dev_screen["f_hint"], f"인자 없이 띄웠는데 F키 안내가 안 보입니다: {dev_screen}"
    assert dev_screen["fps"], f"인자 없이 띄웠는데 FPS 글자가 안 보입니다: {dev_screen}"


def test_hide_debug_hides_debug_button_f_key_hint_and_fps(hidden_screen):
    assert not hidden_screen["debug_button"], f"--hide-debug 인데 DEBUG 버튼이 보입니다: {hidden_screen}"
    assert not hidden_screen["f_hint"], f"--hide-debug 인데 F키 안내가 보입니다: {hidden_screen}"
    assert not hidden_screen["fps"], f"--hide-debug 인데 FPS 글자가 보입니다: {hidden_screen}"


def test_hide_debug_keeps_the_auto_badge(hidden_screen):
    assert hidden_screen["auto_badge"], f"--hide-debug 에서도 자동 플레이 표시(AUTO)는 남아야 합니다: {hidden_screen}"
