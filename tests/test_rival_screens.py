# -*- coding: utf-8 -*-
"""곡 선택의 Best Score·라이벌 탭, 라이벌 관리 팝업, 전체 리더보드 화면 — 서버 없이(--no-server) 화면에 보이는 글자로 확인 (2026-11-08).

서버 데이터가 있을 때의 모습(1위 기록, 순위표 줄, R 표시, 라이벌 등록·해제)은 test_server_screens.py 가 맡는다.
"""
import time

import pytest

import client
from screen_helpers import labels, norm, press, ui, wait_until


def buttons() -> list:
    return client.screen_buttons()


def open_select() -> None:
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    client.tap_song_at(0)
    time.sleep(0.8)


@pytest.fixture(autouse=True)
def _fresh_screen():
    open_select()
    yield


# ── Best Score 탭 ───────────────────────────────────────────────────

def test_best_score_tab_is_default_and_shows_offline_message_and_leaderboard_button():
    for name in (ui("select_tab_world"), ui("select_tab_rival"), ui("select_leaderboard_btn")):
        assert name in buttons(), f"'{name}' 버튼이 없습니다: {buttons()}"
    assert "—" in labels() and ui("leaderboard_load_failed") in labels(), f"서버 없이 Best Score 탭이 '—' 와 불러올 수 없다는 문구를 보여야 합니다: {labels()}"
    assert ui("select_replay_btn") not in buttons(), "1위 기록이 없는데 리플레이 버튼이 보입니다"
    assert "◀" not in buttons() and "▶" not in buttons(), "Best Score 탭에 라이벌 이동 버튼이 보입니다"


# ── 라이벌 탭 ───────────────────────────────────────────────────────

def test_rival_tab_shows_world_target_with_no_record_and_manage_button():
    press(ui("select_tab_rival"))
    time.sleep(0.8)
    for name in ("◀", "▶", ui("select_rival_manage_btn")):
        assert name in buttons(), f"'{name}' 버튼이 없습니다: {buttons()}"
    assert norm(f"{ui('select_tab_world')} (1/1)") in labels(), f"라이벌 이름 칸이 'Best Score (1/1)' 이 아닙니다: {labels()}"
    assert ui("select_no_record") in labels()
    assert ui("select_replay_btn") not in buttons()


def test_rival_tab_arrows_do_nothing_with_a_single_target():
    press(ui("select_tab_rival"))
    time.sleep(0.8)
    before = labels()
    press("▶")
    press("◀")
    assert labels() == before, "대상이 하나뿐인데 ◀▶ 를 눌렀더니 화면이 바뀌었습니다"


def test_tabs_switch_back_and_forth():
    press(ui("select_tab_rival"))
    time.sleep(0.4)
    assert "◀" in buttons() and ui("select_leaderboard_btn") not in buttons()
    press(ui("select_tab_world"))
    time.sleep(0.4)
    assert ui("select_leaderboard_btn") in buttons() and "◀" not in buttons()


# ── 라이벌 관리 팝업 ────────────────────────────────────────────────

def open_manage() -> None:
    press(ui("select_tab_rival"))
    time.sleep(0.4)
    press(ui("select_rival_manage_btn"))
    time.sleep(0.4)


def test_manage_popup_shows_search_box_add_and_close_and_closes():
    open_manage()
    edits = [i for i in client.screen()["items"] if i["kind"] == "edit"]
    assert edits and edits[0]["placeholder"] == ui("select_rival_search_placeholder"), f"닉네임 검색 입력창이 없습니다: {edits}"
    assert ui("select_rival_add_btn") in buttons() and ui("settings_close") in buttons()
    assert ui("select_rival_remove_btn") not in buttons(), "라이벌이 없는데 해제 버튼이 보입니다"
    press(ui("settings_close"))
    time.sleep(0.3)
    assert not [i for i in client.screen()["items"] if i["kind"] == "edit"], "닫기를 눌렀는데 팝업의 입력창이 남아 있습니다"


def test_manage_popup_add_with_empty_name_does_nothing():
    open_manage()
    assert client.fill_input("")
    press(ui("select_rival_add_btn"))
    time.sleep(0.5)
    assert ui("err_rival_network") not in labels() and ui("err_rival_not_found") not in labels(), f"빈 닉네임인데 오류 팝업이 떴습니다: {labels()}"
    assert ui("select_rival_add_btn") in buttons()


def test_manage_popup_add_offline_shows_network_error():
    open_manage()
    assert client.fill_input("아무나")
    press(ui("select_rival_add_btn"))
    assert wait_until(lambda: ui("err_rival_network") in labels(), timeout=8), f"서버 없이 등록했는데 통신 오류 문구가 안 보입니다: {labels()}"


# ── 전체 리더보드 화면 ──────────────────────────────────────────────

def test_full_leaderboard_screen_offline_shows_title_message_and_back_returns():
    press(ui("select_leaderboard_btn"))
    assert client.wait_for_scene("Leaderboard", timeout=10), f"전체 리더보드를 눌렀는데 리더보드 화면이 안 열립니다 — 지금 화면: {client.scene()}"
    assert wait_until(lambda: ui("leaderboard_load_failed") in labels(), timeout=8), f"불러오기 실패 문구가 안 보입니다: {labels()}"
    assert ui("leaderboard_title") in labels()
    assert ui("leaderboard_back") in buttons()
    press(ui("leaderboard_back"))
    assert client.wait_for_scene("SongSelect", timeout=10)
