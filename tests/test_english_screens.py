# -*- coding: utf-8 -*-
"""영어로 돌렸을 때 모든 화면의 글자 — 화면에 한글이 하나도 남아 있으면 안 된다 (2026-11-08).

언어를 English 로 바꾼 뒤 타이틀·메인 메뉴·설정 4탭·곡 선택(라이벌 탭·관리 팝업)·리더보드·결과·튜토리얼 전 대사·플레이 일시정지 창을 차례로 열어
보이는 글자·버튼·탭 제목·입력창 안내문에 한글이 섞여 있는지 본다. 언어 이름 '한국어'(언어 목록 안)와 사용자가 직접 정한 닉네임은 제외한다.
끝나면 한국어로 되돌린다. 서버·계정은 쓰지 않는다(--no-server).
"""
import json
import os
import re
import time

import pytest

import client
from godot_runner import GAME_APPDATA_DIR
from screen_helpers import labels, press, ui, wait_until

HANGUL = re.compile(r"[ㄱ-ㆎ가-힣]")
APP = os.path.join(GAME_APPDATA_DIR, "RhythmGame_New")


def nickname() -> str:
    return json.load(open(os.path.join(APP, "profile.json"), encoding="utf-8")).get("display_name", "")


def korean_found() -> list:
    """지금 화면에서 한글이 들어간 글자 — 닉네임 줄·언어 이름은 제외."""
    nick = nickname()
    out = []
    for i in client.screen()["items"]:
        texts = []
        if i["kind"] in ("label", "button", "tab"):
            texts.append(i["text"])
            texts += i.get("inner", [])
        elif i["kind"] == "edit":
            texts += [i["text"], i["placeholder"]]
        for t in texts:
            if HANGUL.search(t) and not (nick and nick in t) and t != "한국어":
                out.append(t)
    return out


def assert_english(where: str) -> None:
    ko = korean_found()
    assert not ko, f"영어 화면({where})에 한글이 남아 있습니다: {ko}"


@pytest.fixture(scope="module", autouse=True)
def english_mode():
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15)
    time.sleep(0.8)
    client.tap_mainmenu_settings()
    assert client.wait_for_scene("Settings", timeout=10)
    time.sleep(0.8)
    client.select_tab(ui("settings_game_tab"))
    time.sleep(0.4)
    assert client.pick_option(0, "English")["ok"]
    assert wait_until(lambda: ui("settings_account_tab", "en") in [t for t, _ in client.tabs()], timeout=8)
    yield
    client.navigate("main_menu")
    client.wait_for_scene("MainMenu", timeout=15)
    time.sleep(0.8)
    client.tap_mainmenu_settings()
    client.wait_for_scene("Settings", timeout=10)
    time.sleep(0.8)
    client.select_tab(ui("settings_game_tab", "en"))
    time.sleep(0.4)
    client.pick_option(0, "한국어")
    wait_until(lambda: ui("settings_account_tab") in [t for t, _ in client.tabs()], timeout=8)


def test_title_and_main_menu_have_no_korean():
    client.navigate("title")
    assert client.wait_for_scene("TitleScreen", timeout=10)
    time.sleep(0.8)
    assert ui("login_press_start", "en") in labels(), labels()
    assert_english("타이틀")
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=10)
    time.sleep(1.0)
    assert ui("menu_free_mode", "en") in labels()
    assert_english("메인 메뉴")


@pytest.mark.parametrize("tab", ["settings_account_tab", "settings_game_tab", "settings_sound_tab", "settings_credits_tab"])
def test_settings_tabs_have_no_korean(tab):
    client.navigate("main_menu")
    client.wait_for_scene("MainMenu", timeout=10)
    time.sleep(0.8)
    client.tap_mainmenu_settings()
    assert client.wait_for_scene("Settings", timeout=10)
    time.sleep(0.8)
    assert client.select_tab(ui(tab, "en"))
    time.sleep(0.4)
    assert_english("설정 " + tab)
    if tab == "settings_sound_tab":
        press(ui("settings_eq_title", "en"))
        time.sleep(0.4)
        assert_english("이퀄라이저 팝업")
    if tab == "settings_account_tab":
        press(ui("settings_nickname_btn", "en"))
        time.sleep(0.4)
        assert_english("닉네임 팝업")


def test_visual_theme_names_are_not_korean_in_english():
    client.navigate("main_menu")
    client.wait_for_scene("MainMenu", timeout=10)
    time.sleep(0.8)
    client.tap_mainmenu_settings()
    assert client.wait_for_scene("Settings", timeout=10)
    time.sleep(0.8)
    client.select_tab(ui("settings_game_tab", "en"))
    time.sleep(0.4)
    assert_english("설정 게임 탭 테마 이름")


def open_song_select():
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    client.tap_song_at(0)
    time.sleep(0.8)


def test_song_select_tabs_and_popups_have_no_korean():
    open_song_select()
    assert ui("select_folder_official", "en") in client.screen_buttons()
    assert_english("곡 선택")
    press(ui("select_tab_rival", "en"))
    time.sleep(0.6)
    assert_english("곡 선택 라이벌 탭")
    press(ui("select_rival_manage_btn", "en"))
    time.sleep(0.4)
    assert_english("라이벌 관리 팝업")
    client.fill_input("x")
    press(ui("select_rival_add_btn", "en"))
    assert wait_until(lambda: ui("err_rival_network", "en") in labels(), timeout=8), labels()
    assert_english("라이벌 등록 오류 팝업")


def test_leaderboard_offline_has_no_korean():
    open_song_select()
    press(ui("select_leaderboard_btn", "en"))
    assert client.wait_for_scene("Leaderboard", timeout=10)
    assert wait_until(lambda: ui("leaderboard_load_failed", "en") in labels(), timeout=8)
    assert_english("리더보드")


def test_result_screen_has_no_korean():
    client._req("POST", "/debug_show_result?grade=A&marks=clear,perfect")
    assert client.wait_for_scene("ResultScreen", timeout=10)
    time.sleep(1.2)
    assert ui("result_retry_btn", "en") in client.screen_buttons()
    assert_english("결과")


def test_every_tutorial_line_has_no_korean():
    client._req("POST", "/debug_profile?key=tutorial_seen&value=false")
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=10)
    time.sleep(0.8)
    client.tap_mainmenu_play()
    assert client.wait_for_scene("Tutorial", timeout=10)
    time.sleep(0.8)
    for stage in range(5):
        client._req("POST", f"/tap/tutorial_picker_stage?index={stage}")
        time.sleep(0.4)
        for line in range({0: 7, 1: 4, 2: 4, 3: 2, 4: 2}[stage]):          # 단계별로 '다음'으로 볼 수 있는 대사 수(마지막은 START/YES·NO/OK 로 바뀜)
            assert_english(f"튜토리얼 {stage + 1}단계 {line + 1}번째 대사")
            nxt = ui("tutorial_next_btn", "en")
            if nxt in client.screen_buttons():
                press(nxt)
    client._req("POST", "/tap/tutorial_skip")
    client.wait_for_scene("SongSelect", timeout=10)


def test_pause_overlay_has_no_korean():
    open_song_select()
    client.autoplay(True)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30)
    assert wait_until(lambda: "AUTO" in labels() and not any(l in ("3", "2", "1") for l in labels()), timeout=15)
    client.tap_pause_toggle()
    assert wait_until(lambda: "PAUSED" in labels(), timeout=5)
    assert_english("일시정지 창")
    client.tap_pause_quit()
    client.wait_for_scene("SongSelect", timeout=10)
    client.autoplay(False)
