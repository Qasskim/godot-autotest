# -*- coding: utf-8 -*-
"""게임 시작 오류 팝업 — 채보를 못 읽을 때·키음 파일을 못 찾을 때 오류 팝업이 뜨고, 확인을 누르면 곡 선택으로 돌아간다 (기준 DESIGN §14 에러 팝업 2026-07-04,
GameManager.start_game: chart_load_failed / music_load_failed, TEST_SCENARIO "예외 팝업은 재현이 안 되면 PASS" — 이제 재현한다, 2026-11-10).

TestServer /debug_goto_gameplay 가 임의 경로로 플레이를 시작한다. 시험 채보는 시험이 만든 파일(tests/reports/_error_charts)이다.
  - 파일이 없는 채보 → "채보를 불러올 수 없습니다"
  - 노트에 key_sound 이름이 있는데 sounds 에 없는 채보 → "음악 파일을 찾을 수 없습니다"
이 시험의 채보 내용(노트 1개, 120BPM 4키)은 시험 작성자가 정했다. 서버·계정은 쓰지 않는다(--no-server).
"""
import json
import os
import time
import urllib.parse

import pytest

import client
from godot_runner import REPO_ROOT
from screen_helpers import labels, press, ui, wait_until

DIR = os.path.join(REPO_ROOT, "tests", "reports", "_error_charts")


def start(chart: str) -> None:
    q = urllib.parse.urlencode({"chart": chart, "music": "", "key_mode": 4})
    client._req("POST", "/debug_goto_gameplay?" + q)


def make_chart(name: str, score: list) -> str:
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, name)
    chart = {"meta": {"title": "오류 시험", "bpm": 120.0, "keymode": 4, "difficulty": "EZ"}, "sounds": [], "timing_events": [], "gimmick_events": [], "score": score}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chart, f, ensure_ascii=False)
    return path


@pytest.fixture(autouse=True)
def _back_to_menu():
    yield
    client.navigate("main_menu")
    client.wait_for_scene("MainMenu", timeout=15)


def test_missing_chart_file_shows_error_popup_and_ok_returns_to_song_select():
    start(os.path.join(DIR, "없는채보.rgds"))
    assert wait_until(lambda: ui("chart_load_failed") in labels(), timeout=15), f"채보 로드 실패 팝업이 안 뜹니다: {labels()}"
    assert ui("settings_confirm") in client.screen_buttons(), f"확인 버튼이 없습니다: {client.screen_buttons()}"
    press(ui("settings_confirm"))
    assert client.wait_for_scene("SongSelect", timeout=15), "확인을 눌렀는데 곡 선택으로 돌아가지 않습니다"


def test_unreadable_chart_file_shows_the_same_error_popup():
    os.makedirs(DIR, exist_ok=True)
    bad = os.path.join(DIR, "깨진채보.rgds")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("{깨진 json")
    start(bad)
    assert wait_until(lambda: ui("chart_load_failed") in labels(), timeout=15), f"깨진 채보인데 오류 팝업이 안 뜹니다: {labels()}"
    press(ui("settings_confirm"))
    assert client.wait_for_scene("SongSelect", timeout=15)


def test_note_with_unknown_key_sound_shows_music_error_popup_and_ok_returns():
    path = make_chart("키음없음.rgds", [{"type": "tap", "lane": 0, "timing_ms": 1000, "key_sound": "없는_키음"}])
    start(path)
    assert wait_until(lambda: ui("music_load_failed") in labels(), timeout=15), f"키음 파일 없음 팝업이 안 뜹니다: {labels()}"
    press(ui("settings_confirm"))
    assert client.wait_for_scene("SongSelect", timeout=15)
