# -*- coding: utf-8 -*-
"""처음 실행 흐름 — 게임을 처음 설치해 처음 켠 상태(빈 프로필)에서 화면에 보이는 글자로 확인 (2026-11-08, 사용자와 정한 케이스 17~20).

로그인 화면 → 게스트 → 경고 팝업 → 닉네임 입력 → 메인 메뉴 → PLAY → 튜토리얼이 한 번의 흐름이라 파일 안 순서대로 이어서 돈다(앞 테스트가 만든 화면에서 다음이 시작).
게임은 빈 프로필·한국어·--no-server 로 새로 띄운다(마커 fresh_profile). 서버·계정은 쓰지 않는다.
"""
import time

import pytest

import client
from screen_helpers import DIALOGUE, labels, norm, press, stage_label, ui, wait_until

pytestmark = pytest.mark.fresh_profile


def buttons() -> list:
    return client.screen_buttons()


# ── 17. 처음 켜면 로그인 화면 ───────────────────────────────────────

def test_first_launch_shows_login_screen_with_guest_button():
    """로고와 타이틀을 지나 게스트 버튼이 있는 로그인 화면이 나온다(구글 로그인 버튼도 같이 보이는 PC 빌드)."""
    assert wait_until(lambda: client.scene() == "LoginScreen", timeout=40), f"로그인 화면이 40초 안에 나오지 않았습니다 — 지금 화면: {client.scene()}"
    time.sleep(0.8)
    assert ui("login_guest_btn") in buttons(), f"게스트 버튼이 없습니다: {buttons()}"
    assert ui("login_pc_google_btn") in buttons(), f"PC 구글 로그인 버튼이 없습니다: {buttons()}"


# ── 18. 게스트 → 경고 팝업 → 닉네임 입력창 ──────────────────────────

def test_guest_shows_warning_popup_and_cancel_keeps_login_screen():
    press(ui("login_guest_btn"))
    assert norm(ui("login_guest_warning")) in labels(), f"게스트 경고 문구가 안 보입니다 — 화면: {labels()}"
    assert ui("settings_confirm") in buttons() and ui("settings_cancel") in buttons()
    press(ui("settings_cancel"))
    assert norm(ui("login_guest_warning")) not in labels(), "취소했는데 경고 팝업이 남아 있습니다"
    assert client.scene() == "LoginScreen"
    assert ui("login_guest_btn") in buttons()


def test_guest_confirm_opens_nickname_popup_without_cancel_button():
    press(ui("login_guest_btn"))
    press(ui("settings_confirm"))
    assert ui("settings_nickname_popup_title") in labels(), f"닉네임 설정 팝업이 안 뜹니다 — 화면: {labels()}"
    edits = [i for i in client.screen()["items"] if i["kind"] == "edit"]
    assert edits and edits[0]["placeholder"] == ui("settings_nickname_placeholder"), f"닉네임 입력창이 안 보입니다: {edits}"
    assert ui("settings_apply") in buttons()
    assert ui("settings_cancel") not in buttons(), "첫 닉네임 입력창에는 취소 버튼이 없어야 합니다"


# ── 19. 닉네임 저장 검사 ────────────────────────────────────────────

def test_empty_nickname_shows_length_error_and_stays():
    assert client.fill_input("")
    press(ui("settings_apply"))
    assert norm(ui("err_nickname_length")) in labels(), f"빈 닉네임 오류 문구가 안 보입니다 — 화면: {labels()}"
    press(ui("settings_confirm"))                     # 오류 팝업 닫기
    assert ui("settings_nickname_popup_title") in labels(), "오류를 닫은 뒤에도 닉네임 입력창이 남아 있어야 합니다"
    assert client.scene() != "MainMenu"


def test_nickname_with_invalid_characters_shows_error_and_stays():
    assert client.fill_input("a@b#c")
    press(ui("settings_apply"))
    assert norm(ui("err_nickname_chars")) in labels(), f"허용되지 않는 글자 오류 문구가 안 보입니다 — 화면: {labels()}"
    press(ui("settings_confirm"))
    assert ui("settings_nickname_popup_title") in labels()
    assert client.scene() != "MainMenu"


def test_valid_nickname_opens_main_menu():
    assert client.fill_input("자동화QA")
    press(ui("settings_apply"))
    assert client.wait_for_scene("MainMenu", timeout=10), f"올바른 닉네임을 저장했는데 메인 메뉴가 안 나옵니다 — 화면: {labels()}"
    time.sleep(0.8)
    assert ui("settings_nickname_popup_title") not in labels(), "메인 메뉴에 닉네임 팝업이 남아 있습니다"


# ── 20. 온보딩 뒤 첫 PLAY ───────────────────────────────────────────

def test_first_play_after_onboarding_opens_tutorial_stage_one():
    client.tap_mainmenu_play()
    assert client.wait_for_scene("Tutorial", timeout=10), f"처음 PLAY 가 튜토리얼로 가지 않습니다 — 지금 화면: {client.scene()}"
    time.sleep(0.8)
    assert stage_label(0) in labels() and DIALOGUE[0][0] in labels(), f"튜토리얼 1단계 첫 대사가 아닙니다 — 화면: {labels()}"
