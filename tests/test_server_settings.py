# -*- coding: utf-8 -*-
"""로그인한 계정의 설정 화면 — 로그아웃·계정 탈퇴 버튼과 확인 창 흐름 (2026-11-08).

고정 테스트 계정 3번으로 로그인한 상태. 계정 탈퇴는 실제로 지우면 안 되므로 두 번의 확인 창에서 모두 '취소'만 눌러 확인한다(탈퇴 실행은 하지 않는다).
로그아웃은 실제로 한다 — 이 모듈의 마지막 테스트이고, 다음 서버 테스트는 login() 으로 다시 로그인한다.
"""
import time

import pytest

import client
from screen_helpers import labels, norm, press, ui, wait_until
import server_ledger
from server_helpers import ACCT_A, login

pytestmark = pytest.mark.server


def buttons() -> list:
    return client.screen_buttons()


def open_account_tab() -> None:
    login(ACCT_A)
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15)
    time.sleep(0.8)
    client.tap_mainmenu_settings()
    assert client.wait_for_scene("Settings", timeout=10)
    time.sleep(0.8)


def test_logged_in_account_tab_shows_logout_and_delete_but_not_guest_google_link():
    open_account_tab()
    assert ui("settings_logout_btn") in buttons() and ui("settings_delete_account_btn") in buttons(), f"로그인 상태인데 로그아웃·탈퇴 버튼이 없습니다: {buttons()}"
    assert ui("settings_nickname_btn") in buttons()


def test_logout_confirm_cancel_keeps_session():
    open_account_tab()
    press(ui("settings_logout_btn"))
    assert norm(ui("settings_logout_confirm")) in labels()
    assert ui("settings_confirm") in buttons() and ui("settings_cancel") in buttons()
    press(ui("settings_cancel"))
    time.sleep(0.4)
    assert norm(ui("settings_logout_confirm")) not in labels() and client.scene() == "Settings"
    assert client.supabase_session()["session_ready"] is True


def test_delete_account_two_step_confirm_and_cancel_at_each_step_keeps_account():
    open_account_tab()
    press(ui("settings_delete_account_btn"))
    assert norm(ui("settings_delete_account_confirm1")) in labels(), f"탈퇴 1차 확인 문구가 없습니다: {labels()}"
    press(ui("settings_cancel"))
    time.sleep(0.4)
    assert norm(ui("settings_delete_account_confirm1")) not in labels() and client.scene() == "Settings"
    press(ui("settings_delete_account_btn"))
    press(ui("settings_confirm"))                       # 1차 확인 → 2차 확인 창
    assert wait_until(lambda: norm(ui("settings_delete_account_confirm2")) in labels(), timeout=5), f"탈퇴 2차 확인 문구가 없습니다: {labels()}"
    press(ui("settings_cancel"))                        # 2차에서 취소 — 탈퇴는 실행하지 않는다
    time.sleep(0.4)
    assert norm(ui("settings_delete_account_confirm2")) not in labels() and client.scene() == "Settings"
    assert client.supabase_session()["session_ready"] is True, "취소했는데 세션이 사라졌습니다"


def test_logout_confirm_goes_to_login_screen_with_new_guest_session():
    open_account_tab()
    press(ui("settings_logout_btn"))
    press(ui("settings_confirm"))
    assert client.wait_for_scene("LoginScreen", timeout=15), f"로그아웃했는데 로그인 화면이 안 나옵니다 — 지금 화면: {client.scene()}"
    s = client.supabase_session(wait=15)
    # 게임은 로그아웃 뒤 새 익명(게스트) 계정을 서버에 만든다 — 장부에 적어 정리 때 계정째 지운다
    assert s["session_ready"] and s["is_anonymous"] is True, f"로그아웃 뒤 세션이 익명 계정이 아닙니다: {s}"
    server_ledger.register(s["user_id"], fixed=False, label="logout-anon")

