# -*- coding: utf-8 -*-
"""1.0.0(2026-11-05 itch 판) 형식 보정 파일의 업데이트 처리 (2026-11-11 사용자 결정 "0으로 초기화 + 첫 실행 때 보정 화면 한 번").

1.0.0 은 보정 파일에 calibration_rule 키가 없다. 그런 파일에 값이 있으면 게임은 시작할 때 0으로 되돌리고(측정값과 슬라이더 값을 구별할 수 없음),
모드 선택 화면에서 캘리브레이션 팝업(업데이트 안내 포함)을 한 번 띄운다. 건너뛰면 다시 띄우지 않는다. 값이 0이었으면 띄우지 않는다.
이 파일이 게임을 직접 띄운다(보정 파일을 미리 써 두어야 해서 — keep_calibration=True). 시험값(+40ms)은 사용자가 정한 값이 아니라 시험 작성자가 정했다.
서버·계정은 쓰지 않는다(--no-server).
"""
import os
import time

import pytest

import client
from godot_runner import GAME_APPDATA_DIR, calibration_path, read_calibration, start_game, stop_game
from screen_helpers import calibration_panel_shown, labels, skip_calibration_panel, ui, wait_until

pytestmark = pytest.mark.no_server      # 이 파일이 게임을 직접 띄운다(포트 5000을 쓰므로 다른 게임이 있으면 중단)


def write_old_format(value_ms: float) -> None:
    path = calibration_path(GAME_APPDATA_DIR)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"[audio]\n\nuser_calibration_ms={value_ms}\n")


def open_main_menu() -> None:
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15), "모드 선택 화면이 열리지 않았습니다"
    time.sleep(1.0)


def test_old_format_value_is_reset_and_prompt_shows_once():
    write_old_format(40.0)
    proc = start_game(keep_calibration=True)
    try:
        saved = read_calibration()
        assert saved.get("calibration_rule") == "2", f"시작할 때 현재 형식으로 바꿔 저장해야 합니다: {saved}"
        assert float(saved.get("user_calibration_ms", "999")) == 0.0, f"1.0.0 보정값을 0으로 되돌려야 합니다: {saved}"
        assert saved.get("recalibration_prompt") == "true", f"한 번 띄울 표시가 저장돼야 합니다: {saved}"
        open_main_menu()
        skip_calibration_panel(update=True)
        assert wait_until(lambda: not calibration_panel_shown(update=True), timeout=5), f"건너뛰었는데 팝업이 남아 있습니다 — 화면: {labels()}"
        assert read_calibration().get("recalibration_prompt") == "false", f"건너뛴 뒤 다시 띄우지 않도록 저장돼야 합니다: {read_calibration()}"
    finally:
        stop_game(proc)
    proc = start_game(keep_calibration=True)
    try:
        open_main_menu()
        time.sleep(1.0)
        assert not calibration_panel_shown(update=True), "한 번 건너뛴 뒤 다시 켰는데 업데이트 팝업이 또 나왔습니다"
    finally:
        stop_game(proc)


def test_old_format_zero_value_has_no_prompt():
    write_old_format(0.0)
    proc = start_game(keep_calibration=True)
    try:
        saved = read_calibration()
        assert saved.get("calibration_rule") == "2", f"시작할 때 현재 형식으로 바꿔 저장해야 합니다: {saved}"
        assert saved.get("recalibration_prompt") == "false", f"값이 0이었으면 다시 잴 필요가 없습니다: {saved}"
        open_main_menu()
        time.sleep(1.0)
        assert not calibration_panel_shown(update=True), "보정값이 0이었는데 업데이트 팝업이 나왔습니다"
    finally:
        stop_game(proc)


def test_update_popup_buttons_stay_on_screen_after_measuring():
    """업데이트 뒤 팝업은 안내 글이 가장 많다 — 8번 탭 결과까지 나와도 버튼이 화면 안(1920x864)에 있어야 한다(2026-11-15 폰에서 밀렸다)."""
    write_old_format(40.0)
    proc = start_game(keep_calibration=True)
    try:
        open_main_menu()
        assert wait_until(lambda: calibration_panel_shown(update=True), timeout=10), f"업데이트 팝업이 없습니다 — 화면: {labels()}"
        for _ in range(8):
            client.press_text("TAP")
            time.sleep(0.1)
        assert wait_until(lambda: ui("settings_measure_done") in labels(), timeout=5)
        time.sleep(0.8)
        for name in ("TAP", ui("settings_retry"), ui("settings_apply"), ui("calib_skip")):
            rect = client.button_rect(name)
            assert len(rect) == 4, f"'{name}' 버튼 위치를 읽지 못했습니다 — 버튼: {client.screen_buttons()}"
            x, y, w, h = rect
            assert 0 <= x and x + w <= 1920 and 0 <= y and y + h <= 864, f"'{name}' 버튼이 화면(1920x864) 밖에 있습니다: {rect}"
        skip_calibration_panel(update=True)
    finally:
        stop_game(proc)
