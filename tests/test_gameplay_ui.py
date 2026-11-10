# -*- coding: utf-8 -*-
"""게임 플레이 화면의 글자 — 시작 카운트다운, 자동 플레이 표시, 콤보·판정, 일시정지 창(배속·오프셋·재개·곡 선택으로), 재개 카운트다운, 뒤로가기 키 (2026-11-08).

배포 곡 SYNTHWAVE 4K EZ 를 자동 플레이(AUTO)로 켠다. 소리·노트 모양·움직임은 사람이 확인한다. 서버·계정은 쓰지 않는다(--no-server).
"""
import os
import re
import time

import pytest

import client
from godot_runner import GAME_APPDATA_DIR
from screen_helpers import labels, norm, press, ui, wait_until

APP = os.path.join(GAME_APPDATA_DIR, "RhythmGame_New")
SONG = "SYNTHWAVE"
SONG_KEY = "synthwave_Gsmaj_115_473"


def buttons() -> list:
    return client.screen_buttons()


def saved_speed() -> float:
    text = open(os.path.join(APP, "settings.cfg"), encoding="utf-8").read()
    return float(re.search(SONG_KEY + r'": ([\d.]+)', text).group(1))


def calibration_ms() -> float:
    return float(re.search(r"user_calibration_ms=(-?[\d.]+)", open(os.path.join(APP, "calibration.cfg"), encoding="utf-8").read()).group(1))


def speed_on_screen() -> float:
    return float(next(re.search(r"([\d.]+)x", g).group(1) for g in labels() if g.startswith("배속")))


def offset_line(ms: float) -> str:
    return norm(ui("hud_offset") % ms)


def combo_now() -> int:
    nums = [int(l) for l in labels() if l.isdigit() and l not in ("1", "2", "3")]
    return max(nums) if nums else 0


def countdown_sequence(timeout: float) -> list:
    seen = []
    deadline = time.time() + timeout
    while time.time() < deadline and len(seen) < 3:
        for d in ("3", "2", "1"):
            if d in labels() and d not in seen:
                seen.append(d)
        time.sleep(0.15)
    return seen


def start_play() -> None:
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    client.tap_song_at(client.songs()["songs"].index(SONG))
    time.sleep(0.5)
    client.autoplay(True)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30)


def play_until_started() -> None:
    start_play()
    assert wait_until(lambda: "AUTO" in labels() and not any(l in ("3", "2", "1") for l in labels()), timeout=15)
    assert wait_until(lambda: combo_now() >= 3, timeout=40), "자동 플레이 시작 뒤 첫 노트들이 처리되지 않습니다(콤보가 안 오름)"


def pause() -> None:
    client.tap_pause_toggle()
    assert wait_until(lambda: "PAUSED" in labels(), timeout=5), f"일시정지 창이 안 뜹니다: {labels()}"
    time.sleep(0.3)


@pytest.fixture(autouse=True)
def _leave_after():
    yield
    if client.scene() == "GameScene":
        if "PAUSED" not in labels():
            client.tap_pause_toggle()
            time.sleep(0.5)
        client.tap_pause_quit()
        client.wait_for_scene("SongSelect", timeout=10)
    client.autoplay(False)


def test_start_countdown_shows_3_2_1_then_play_hud_with_auto_and_full_gauge():
    start_play()
    assert countdown_sequence(8) == ["3", "2", "1"], "시작 카운트다운이 3 → 2 → 1 순서로 안 보입니다"
    assert wait_until(lambda: not any(l in ("3", "2", "1") for l in labels()), timeout=5)
    assert "AUTO" in labels(), f"자동 플레이인데 AUTO 표시가 없습니다: {labels()}"
    assert "100%" in labels(), f"게이지가 100% 로 시작하지 않습니다: {labels()}"
    assert ui("hud_replay") not in labels()
    assert buttons() == [""], f"플레이 중 보이는 버튼은 일시정지 아이콘 하나여야 합니다: {buttons()}"


def test_combo_counts_up_and_judgment_word_shows_during_autoplay():
    play_until_started()
    first = combo_now()
    time.sleep(3.0)
    second = combo_now()
    assert second > first >= 0, f"자동 플레이인데 콤보가 늘지 않습니다: {first} → {second}"
    assert any(l in ("WOW", "GREAT", "GOOD") for l in labels()), f"판정 글자가 안 보입니다: {labels()}"
    assert "100%" in labels(), f"자동 플레이 게이지가 100% 가 아닙니다: {labels()}"


def test_pause_overlay_texts_speed_offset_buttons_and_combo_stops():
    play_until_started()
    pause()
    # 매 시험 전 보정 0 복원(conftest)은 이번 실행 메모리만 바꾸고 calibration.cfg 는 그대로라 파일에 옛 값(196 등)이 남는다.
    # 슬라이더 값이 바뀌어야 저장되므로(같은 값이면 저장 안 됨) 한 번 움직였다가 0 으로 돌려 파일에도 0 을 쓴다(2026-11-10 풀 테스트에서 발견).
    assert client.set_slider(0, 1.0)["ok"]
    assert client.set_slider(0, 0.0)["ok"]
    got = labels()
    assert norm(ui("hud_speed") % saved_speed()) in got, f"배속 줄이 저장값 {saved_speed()} 와 다릅니다: {got}"
    assert offset_line(calibration_ms()) in got, f"오프셋 줄이 저장값 {calibration_ms()} 와 다릅니다: {got}"
    for b in (" - ", " + ", ui("hud_resume"), ui("hud_quit_select")):
        assert b in buttons(), f"일시정지 창에 '{b}' 버튼이 없습니다: {buttons()}"
    c1 = combo_now()
    time.sleep(2.0)
    assert combo_now() == c1, "일시정지 중인데 콤보가 올랐습니다"


def test_pause_speed_buttons_step_quarter_save_and_clamp():
    play_until_started()
    pause()
    start = speed_on_screen()
    press(" + ")
    assert speed_on_screen() == start + 0.25, f"+ 를 눌렀는데 배속이 0.25 안 올랐습니다: {start} → {speed_on_screen()}"
    assert saved_speed() == start + 0.25, f"올린 배속이 settings.cfg 에 저장되지 않았습니다: {saved_speed()}"
    press(" - ")
    assert speed_on_screen() == start and saved_speed() == start
    for _ in range(45):
        press(" - ")
    assert speed_on_screen() == 0.25, f"최소 배속이 0.25 가 아닙니다: {speed_on_screen()}"
    for _ in range(45):
        press(" + ")
    assert speed_on_screen() == 10.0, f"최대 배속이 10.0 이 아닙니다: {speed_on_screen()}"
    while speed_on_screen() > start:
        press(" - ")
    assert speed_on_screen() == start and saved_speed() == start


def test_pause_offset_slider_changes_label_and_saves_calibration_then_restores():
    play_until_started()
    pause()
    start = calibration_ms()
    try:
        assert client.set_slider(0, 25.0)["ok"]
        assert offset_line(25.0) in labels(), f"오프셋 줄이 +25ms 로 안 바뀝니다: {labels()}"
        assert calibration_ms() == 25.0, f"오프셋이 calibration.cfg 에 저장되지 않았습니다: {calibration_ms()}"
        top = client.set_slider(0, 9999.0)["value"]
        low = client.set_slider(0, -9999.0)["value"]
        assert top > 0 > low and top == -low, f"오프셋 범위가 좌우 대칭이 아닙니다: {low} ~ {top}"
        assert calibration_ms() == low
    finally:
        client.set_slider(0, start)
    assert calibration_ms() == start


def test_resume_shows_countdown_3_2_1_then_hides_overlay_and_combo_continues():
    play_until_started()
    pause()
    c1 = combo_now()
    press(ui("hud_resume"))
    assert countdown_sequence(6) == ["3", "2", "1"], "재개 카운트다운이 3 → 2 → 1 이 아닙니다"
    assert "PAUSED" not in labels(), "재개했는데 일시정지 창이 남아 있습니다"
    time.sleep(2.5)
    assert combo_now() > c1, f"재개 뒤 콤보가 다시 오르지 않습니다: {c1} → {combo_now()}"


def test_pause_during_resume_countdown_returns_to_pause_overlay():
    play_until_started()
    pause()
    press(ui("hud_resume"))
    assert wait_until(lambda: "3" in labels() or "2" in labels(), timeout=3)
    client.tap_pause_toggle()
    assert wait_until(lambda: "PAUSED" in labels(), timeout=3), f"재개 카운트다운 중 다시 누르면 일시정지 창으로 돌아와야 합니다: {labels()}"
    assert not any(l in ("3", "2", "1") for l in labels())


def test_pause_icon_button_opens_overlay_and_back_key_toggles_pause():
    play_until_started()
    assert client.press_nth_button(0)
    assert wait_until(lambda: "PAUSED" in labels(), timeout=3), "일시정지 아이콘을 눌렀는데 창이 안 뜹니다"
    client.back()                                               # 일시정지 중 뒤로가기 키 = 재개
    assert wait_until(lambda: "PAUSED" not in labels(), timeout=3), "일시정지 중 뒤로가기 키가 재개로 동작하지 않습니다"
    assert wait_until(lambda: not any(l in ("3", "2", "1") for l in labels()), timeout=8)
    time.sleep(1.0)
    client.back()                                               # 플레이 중 뒤로가기 키 = 일시정지
    assert wait_until(lambda: "PAUSED" in labels(), timeout=3), "플레이 중 뒤로가기 키가 일시정지로 동작하지 않습니다"


def test_quit_button_returns_to_song_select_with_same_song_selected():
    play_until_started()
    pause()
    press(ui("hud_quit_select"))
    assert client.wait_for_scene("SongSelect", timeout=10), f"곡 선택으로를 눌렀는데 곡 선택이 안 열립니다 — 지금 화면: {client.scene()}"
    time.sleep(1.0)
    assert SONG in labels(), f"돌아온 곡 선택에서 직전 곡({SONG})이 선택돼 있지 않습니다: {labels()}"
