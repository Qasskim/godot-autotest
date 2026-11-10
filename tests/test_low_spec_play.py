# -*- coding: utf-8 -*-
"""저사양 모드 재생 경로 — 켜고 곡 폴더에 full_mix.ogg 가 있으면 그것으로 재생하고 키음 개별 재생을 억제한다 (GameManager.start_game, 기준 DESIGN §8 곡 폴더 구조 풀믹스, 코드 주석 2026-08-08).

곡 선택의 '저사양 모드' 버튼으로 켜고 SYNTHWAVE(풀믹스 있음)를 플레이해 TestServer /debug_play_state 의 low_spec_full_mix 가 켜졌는지, 끄고 플레이하면 꺼졌는지 본다.
소리가 실제로 어떻게 들리는지는 사람이 확인한다. 설정 파일은 시험 뒤 원래 값으로 되돌린다. 서버·계정은 쓰지 않는다(--no-server).
"""
import time

import pytest

import client
from screen_helpers import labels, press, ui, wait_until

SONG = "SYNTHWAVE"


def open_song() -> None:
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    client.tap_song_at(client.songs()["songs"].index(SONG))
    time.sleep(0.5)


def low_spec_on_screen() -> bool:
    return bool(client._req("GET", "/debug_play_state").get("low_spec_full_mix"))


def play_and_read() -> bool:
    client.autoplay(True)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30)
    assert wait_until(lambda: "AUTO" in labels() and not any(l in ("3", "2", "1") for l in labels()), timeout=20)
    on = low_spec_on_screen()
    client.tap_pause_toggle()
    time.sleep(0.5)
    client.tap_pause_quit()
    client.wait_for_scene("SongSelect", timeout=10)
    return on


@pytest.fixture(autouse=True)
def _restore():
    yield
    client.autoplay(False)


def test_low_spec_on_uses_full_mix_and_off_does_not():
    open_song()
    from test_songselect import read_cfg
    original = read_cfg()["low_spec_mode"] == "true"      # 설정 읽기 함수는 글자("true"/"false")를 돌려준다
    try:
        if original:
            press(ui("select_low_spec_toggle_short"))      # 먼저 끈다
        assert read_cfg()["low_spec_mode"] == "false"
        assert play_and_read() is False, "저사양 모드가 꺼져 있는데 풀믹스 재생 경로가 켜졌습니다"
        press(ui("select_low_spec_toggle_short"))
        assert read_cfg()["low_spec_mode"] == "true"
        assert play_and_read() is True, "저사양 모드를 켰고 곡 폴더에 full_mix.ogg 가 있는데 풀믹스 재생 경로가 켜지지 않았습니다"
    finally:
        if (read_cfg()["low_spec_mode"] == "true") != original:
            press(ui("select_low_spec_toggle_short"))
