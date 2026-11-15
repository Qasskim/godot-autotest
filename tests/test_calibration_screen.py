# -*- coding: utf-8 -*-
"""튜토리얼 끝의 캘리브레이션 팝업 (2026-11-11 사용자 결정: 처음 PLAY로 들어온 튜토리얼이 끝나면 캘리브레이션을 거쳐 곡 선택으로,
건너뛸 수 있고 나중에 다시 하는 곳을 알려 준다).

게임 TestServer 의 /screen_texts·/screen_press 로 화면 글자와 버튼을 본다. 측정 탭 시각은 시험이 정하지 못하므로(버튼을 연달아 누름)
저장되는 값의 크기는 보지 않고, 적용하면 현재 형식(calibration_rule=2)으로 저장되는지만 본다. 서버·계정은 쓰지 않는다(--no-server).
"""
import time

import client
from godot_runner import read_calibration
from screen_helpers import (calibration_panel_shown, enter_tutorial_via_play, enter_tutorial_via_settings, labels, press,
                            skip_calibration_panel, ui, wait_until)


def test_skip_tutorial_then_calibration_skip_opens_song_select():
    enter_tutorial_via_play()
    press("SKIP")
    assert wait_until(lambda: calibration_panel_shown(), timeout=10), f"캘리브레이션 팝업이 출력되지 않았습니다 — 화면: {labels()}"
    assert client.scene() == "Tutorial", "캘리브레이션 팝업은 튜토리얼 화면 위에 떠야 합니다(아직 곡 선택으로 넘어가면 안 됨)"
    assert ui("calib_update_notice") not in labels(), "튜토리얼 끝 팝업에 업데이트 안내가 나오면 안 됩니다"
    skip_calibration_panel()
    assert client.wait_for_scene("SongSelect", timeout=10), "건너뛰기를 눌렀는데 곡 선택 화면으로 가지 않았습니다"


def test_calibration_apply_after_tutorial_saves_current_format():
    enter_tutorial_via_play()
    press("SKIP")
    assert wait_until(lambda: calibration_panel_shown(), timeout=10), f"캘리브레이션 팝업이 출력되지 않았습니다 — 화면: {labels()}"
    for _ in range(8):
        press("TAP")
        time.sleep(0.1)
    assert wait_until(lambda: ui("settings_measure_done") in labels(), timeout=5), f"8번 탭했는데 측정 완료가 안 나옵니다 — 화면: {labels()}"
    press(ui("settings_apply"))
    assert client.wait_for_scene("SongSelect", timeout=10), "적용을 눌렀는데 곡 선택 화면으로 가지 않았습니다"
    saved = read_calibration()
    assert saved.get("calibration_rule") == "2", f"적용한 보정이 현재 형식으로 저장되지 않았습니다: {saved}"
    assert abs(float(saved.get("user_calibration_ms", "999"))) <= 200, f"보정값이 범위(±200ms)를 벗어났습니다: {saved}"


def test_back_key_on_calibration_after_tutorial_opens_song_select():
    enter_tutorial_via_play()
    press("SKIP")
    assert wait_until(lambda: calibration_panel_shown(), timeout=10), f"캘리브레이션 팝업이 출력되지 않았습니다 — 화면: {labels()}"
    client.back()
    assert client.wait_for_scene("SongSelect", timeout=10), "뒤로가기 키로 건너뛰었는데 곡 선택 화면으로 가지 않았습니다"


def test_settings_tutorial_replay_skip_has_no_calibration_panel():
    enter_tutorial_via_settings()
    press("1. 기본 노트")
    press("SKIP")
    assert client.wait_for_scene("Settings", timeout=10), "설정에서 다시 본 튜토리얼을 건너뛰었는데 설정으로 돌아오지 않았습니다"
    time.sleep(0.5)
    assert not calibration_panel_shown(), "설정에서 다시 본 튜토리얼 뒤에는 캘리브레이션 팝업이 나오면 안 됩니다"


def test_popup_buttons_stay_on_screen_after_measuring():
    """측정을 끝내 8번 탭 결과와 안내 글이 다 나와도 TAP·다시·적용·건너뛰기 버튼이 화면 안에 있어야 한다(2026-11-15 폰에서 버튼이 화면 밖으로 밀렸다).
    시험 창은 1920x864(godot_runner)."""
    enter_tutorial_via_play()
    press("SKIP")
    assert wait_until(lambda: calibration_panel_shown(), timeout=10), f"캘리브레이션 팝업이 출력되지 않았습니다 — 화면: {labels()}"
    for _ in range(8):
        press("TAP")
        time.sleep(0.1)
    assert wait_until(lambda: ui("settings_measure_done") in labels(), timeout=5)
    time.sleep(0.8)      # 글 영역 높이를 다시 맞추는 두 프레임을 기다린다
    for name in ("TAP", ui("settings_retry"), ui("settings_apply"), ui("calib_skip")):
        rect = client.button_rect(name)
        assert len(rect) == 4, f"'{name}' 버튼 위치를 읽지 못했습니다 — 버튼: {client.screen_buttons()}"
        x, y, w, h = rect
        assert 0 <= x and x + w <= 1920 and 0 <= y and y + h <= 864, f"'{name}' 버튼이 화면(1920x864) 밖에 있습니다: {rect}"
    press(ui("calib_skip"))
    assert client.wait_for_scene("SongSelect", timeout=10)
