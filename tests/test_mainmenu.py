# -*- coding: utf-8 -*-
"""메인 메뉴(모드 선택 캐러셀) — 타일 글자, 화살표·스와이프로 옮기기, 가운데 타일 누르기, 준비중 안내, 뒤로가기 경고 (2026-11-08).

화면 안 좌표로 터치를 보내 실제 누르기 경로로 확인한다. 서버·계정은 쓰지 않는다(--no-server).
"""
import time

import client
from screen_helpers import labels, press, ui, wait_until


def open_menu() -> None:
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15)
    time.sleep(1.0)


def tap_center() -> None:
    w, h = client.viewport()
    client.click(w / 2, h / 2)
    time.sleep(0.4)


def swipe(dx: float) -> None:
    w, h = client.viewport()
    y = h / 2
    client.click(w / 2 - dx / 2, y, no_release=True)
    client.click(w / 2 + dx / 2, y, release_only=True)
    time.sleep(0.5)


def right_arrow() -> None:
    assert client.press_nth_button(1)
    time.sleep(0.5)


def left_arrow() -> None:
    assert client.press_nth_button(0)
    time.sleep(0.5)


def test_tiles_show_four_mode_names_and_two_coming_soon_badges():
    open_menu()
    got = labels()
    for name in (ui("menu_free_mode"), ui("menu_arcade_mode"), ui("menu_course_mode"), ui("menu_settings")):
        assert name in got, f"'{name}' 타일 글자가 없습니다: {got}"
    assert got.count(ui("menu_coming_soon_badge")) == 2, f"준비중 표시가 아케이드·코스 두 곳에만 있어야 합니다: {got}"
    assert [g for g in got if g in (ui("menu_free_mode"), ui("menu_arcade_mode"), ui("menu_course_mode"), ui("menu_settings"))] == \
        [ui("menu_free_mode"), ui("menu_arcade_mode"), ui("menu_course_mode"), ui("menu_settings")], "타일 순서가 프리모드·아케이드·코스·설정이 아닙니다"


def test_center_tile_tap_opens_free_mode_song_select():
    open_menu()
    tap_center()
    assert client.wait_for_scene("SongSelect", timeout=10), f"가운데(프리모드) 타일을 눌렀는데 곡 선택이 안 열립니다 — 지금 화면: {client.scene()}"


def test_right_arrow_moves_to_arcade_then_course_and_both_show_coming_soon_toast():
    open_menu()
    for _ in range(2):
        right_arrow()
        tap_center()
        assert ui("menu_coming_soon_toast") in labels(), f"준비중 타일을 눌렀는데 '준비 중입니다' 안내가 안 뜹니다: {labels()}"
        assert client.scene() == "MainMenu"
        time.sleep(2.0)


def test_right_arrow_three_times_reaches_settings_and_tap_opens_settings():
    open_menu()
    for _ in range(3):
        right_arrow()
    tap_center()
    assert client.wait_for_scene("Settings", timeout=10), f"설정 타일을 눌렀는데 설정 화면이 안 열립니다 — 지금 화면: {client.scene()}"


def test_left_arrow_wraps_from_first_tile_to_settings():
    open_menu()
    left_arrow()
    tap_center()
    assert client.wait_for_scene("Settings", timeout=10), "첫 타일에서 왼쪽 화살표를 눌렀을 때 설정 타일로 돌지 않습니다"


def test_right_arrow_four_times_wraps_back_to_free_mode():
    open_menu()
    for _ in range(4):
        right_arrow()
    tap_center()
    assert client.wait_for_scene("SongSelect", timeout=10), "오른쪽 화살표를 4번 눌렀는데 처음(프리모드)으로 돌아오지 않습니다"


def test_swipe_left_moves_to_next_tile_and_swipe_right_to_previous():
    open_menu()
    swipe(-400)                                         # 왼쪽으로 밀면 다음 타일(아케이드)
    tap_center()
    assert ui("menu_coming_soon_toast") in labels(), f"왼쪽 스와이프 뒤 가운데가 아케이드(준비중)가 아닙니다: {labels()}"
    time.sleep(2.0)
    open_menu()
    swipe(400)                                          # 오른쪽으로 밀면 이전 타일(설정)
    tap_center()
    assert client.wait_for_scene("Settings", timeout=10), "오른쪽 스와이프 뒤 가운데가 설정이 아닙니다"


def test_short_drag_under_threshold_does_not_move_tiles():
    open_menu()
    swipe(-30)
    tap_center()
    assert client.wait_for_scene("SongSelect", timeout=10), "짧은 드래그(임계 미만)로 타일이 움직였습니다"


def test_back_once_shows_exit_warning_toast_and_stays():
    open_menu()
    client.tap_mainmenu_back()
    assert wait_until(lambda: ui("menu_exit_warning") in labels(), timeout=3), f"뒤로가기 한 번에 종료 경고가 안 뜹니다: {labels()}"
    assert client.scene() == "MainMenu" and client.ping()
