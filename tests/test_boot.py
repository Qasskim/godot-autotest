# -*- coding: utf-8 -*-
"""부팅 화면 — 회사 로고(CI) → 타이틀(화면을 눌러 시작) → 메인 메뉴 (2026-11-08).

회사 로고는 약 4.8초(연출 시간 합) 뒤 자동으로 타이틀로 넘어가고, 누르면 바로 넘어간다. 온보딩을 마친 프로필이면 타이틀은
'화면을 눌러 시작' 한 줄만 보이고 누르면 메인 메뉴로 간다. 로고의 모양·모자이크 연출은 사람이 확인한다. 서버·계정은 쓰지 않는다(--no-server).
"""
import time

import client
from screen_helpers import labels, ui, wait_until


def open_logo() -> float:
    client.navigate("company_logo")
    assert client.wait_for_scene("CompanyLogo", timeout=10), f"회사 로고 화면이 안 열립니다: {client.scene()}"
    return time.time()


def tap_anywhere() -> None:
    w, h = client.viewport()
    client.click(w / 2, h / 2)


def test_company_logo_has_no_text_and_goes_to_title_automatically_after_animation():
    t0 = open_logo()
    time.sleep(0.5)
    assert labels() == [] and client.screen_buttons() == [], f"회사 로고에는 글자·버튼이 없어야 합니다: {labels()}"
    assert not wait_until(lambda: client.scene() != "CompanyLogo", timeout=3.0), "연출이 끝나기 전(3초 안)에 로고가 넘어갔습니다"
    assert wait_until(lambda: client.scene() == "TitleScreen", timeout=8.0), f"연출이 끝났는데 타이틀로 안 넘어갑니다 — 지금 화면: {client.scene()}"
    elapsed = time.time() - t0
    assert 4.0 <= elapsed <= 8.0, f"로고가 {elapsed:.1f}초 만에 넘어갔습니다(연출 합 약 4.8초 기준 4~8초)"


def test_tap_skips_company_logo_immediately():
    t0 = open_logo()
    time.sleep(0.7)
    tap_anywhere()
    assert wait_until(lambda: client.scene() == "TitleScreen", timeout=3.0), f"로고를 눌렀는데 바로 타이틀로 안 넘어갑니다 — 지금 화면: {client.scene()}"
    assert time.time() - t0 < 4.0


def test_title_after_onboarding_shows_press_start_and_subtitle_only():
    client.navigate("title")
    assert client.wait_for_scene("TitleScreen", timeout=10)
    time.sleep(0.8)
    got = labels()
    assert ui("login_press_start") in got, f"'화면을 눌러 시작' 이 안 보입니다: {got}"
    assert ui("title_subtitle") in got, f"서브타이틀이 안 보입니다: {got}"
    assert client.screen_buttons() == [], f"온보딩을 마친 타이틀에 로그인 버튼이 보입니다: {client.screen_buttons()}"


def test_tap_on_title_opens_main_menu():
    client.navigate("title")
    assert client.wait_for_scene("TitleScreen", timeout=10)
    time.sleep(0.8)
    tap_anywhere()
    assert client.wait_for_scene("MainMenu", timeout=10), f"타이틀을 눌렀는데 메인 메뉴가 안 열립니다 — 지금 화면: {client.scene()}"


def test_title_back_once_shows_exit_warning_and_stays():
    client.navigate("title")
    assert client.wait_for_scene("TitleScreen", timeout=10)
    time.sleep(0.8)
    client.back()
    assert wait_until(lambda: ui("menu_exit_warning") in labels(), timeout=3), f"타이틀에서 뒤로가기 한 번에 종료 경고가 안 뜹니다: {labels()}"
    assert client.scene() == "TitleScreen" and client.ping()
