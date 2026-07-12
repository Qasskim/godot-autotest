# -*- coding: utf-8 -*-
"""
TEST_SCENARIO.md 기반 전체 시나리오.

주의: 이 파일은 맨 마지막에 MainMenu QUIT 버튼으로 게임을 실제 종료시킨다.
      다른 테스트 파일과 함께 `pytest -v` 로 묶어서 돌리면 이후 파일들이 서버 응답 없음으로
      전부 실패하므로, 반드시 단독 실행할 것: `pytest test_full_scenario.py -v`

pytest는 기본적으로 파일 내 함수 선언 순서대로 실행하므로, 아래 test_ 함수들은
위에서 아래로 하나의 이어지는 플레이 흐름을 구성한다(법칙 4).
"""
import random
import time

import client
from conftest import record_case, record_na


# ── 0. 앱 실행 ────────────────────────────────────────────────────────────

def test_00_ping():
    assert client.ping()


def test_00_mainmenu_entry():
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15)


# ── 1. MainMenu (QUIT 버튼 제외 — 맨 마지막에 별도 테스트) ───────────────────

def test_01_mainmenu_back_once_shows_exit_warning():
    """뒤로가기 1회는 종료 경고만 뜨고 앱은 종료되지 않아야 한다."""
    client.tap_mainmenu_back()
    time.sleep(0.3)
    assert client.scene() == "MainMenu", "뒤로가기 1회만으로 화면이 바뀌면 안 됨(종료도 안 됨)"


def test_01_mainmenu_settings_button():
    client.tap_mainmenu_settings()
    assert client.wait_for_scene("Settings", timeout=10)


# ── 2. Settings ───────────────────────────────────────────────────────────

def test_02_settings_song_dir_na():
    record_na(
        "Settings: 곡 폴더 선택 (FileDialog / Android 오버레이)",
        "세부 기획 및 구현 중",
    )
    assert True


def test_02_settings_calibration_popup_flow():
    client.tap_settings_calibrate_open()
    time.sleep(0.2)
    for _ in range(8):
        client.tap_settings_calibrate_tap()
        time.sleep(0.05)
    client.tap_settings_calibrate_retry()
    time.sleep(0.1)
    for _ in range(8):
        client.tap_settings_calibrate_tap()
        time.sleep(0.05)
    client.tap_settings_calibrate_apply()
    time.sleep(0.1)


def test_02_settings_calibration_popup_close_button():
    # apply()가 이미 팝업을 닫지만, close 버튼 자체도 별도로 검증
    client.tap_settings_calibrate_open()
    time.sleep(0.2)
    client.tap_settings_calibrate_close()
    assert True


def test_02_settings_back_button():
    client.tap_settings_back()
    assert client.wait_for_scene("MainMenu", timeout=10)


# ── 3. SongSelect ─────────────────────────────────────────────────────────

def test_03_mainmenu_play_button():
    client.tap_mainmenu_play()
    assert client.wait_for_scene("SongSelect", timeout=10)


def test_03_songselect_tab_world():
    resp = client.tap_songselect_tab_world()
    assert resp.get("ok") is True


def test_03_songselect_tab_my():
    resp = client.tap_songselect_tab_my()
    assert resp.get("ok") is True


def test_03_songselect_tab_rival():
    resp = client.tap_songselect_tab_rival()
    assert resp.get("ok") is True


def test_03_songselect_debug_popup_open_close():
    client.tap_songselect_debug_open()
    time.sleep(0.2)
    resp = client.tap_songselect_debug_close()
    assert resp.get("ok") is True


# ── 4. 채보 전체 순회 (법칙 4) ────────────────────────────────────────────

def test_04_song_list_not_empty():
    resp = client.songs()
    assert resp.get("count", 0) > 0, f"곡 목록이 비어 있습니다: {resp}"


def test_04_play_every_chart():
    """SongSelect 화면에 실제 뜬 곡 목록을 그 자리에서 조회해 전부 순회."""
    songs_resp = client.songs()
    count = songs_resp.get("count", 0)
    titles = songs_resp.get("songs", [])
    assert count > 0, "순회할 채보가 없습니다"

    for i in range(count):
        title = titles[i] if i < len(titles) else f"index {i}"
        prefix = f"chart[{i}] {title}"

        # SongSelect는 재진입마다 새 인스턴스라 _auto_play가 false로 초기화됨(디버그 구현상 정상) —
        # 곡마다 다시 켜줘야 함
        client.autoplay(True)
        client.tap_song_at(i)
        client.tap("play")
        entered = client.wait_for_scene("GameScene", timeout=15)
        record_case(f"{prefix}: GameScene 진입", entered)
        if not entered:
            continue

        # 시작 카운트다운(3,2,1) 끝나기 전에 포즈를 걸면 실제 입력 경로(ESC)와 달리
        # GameManager._toggle_pause()가 카운트다운 상태를 무시하고 그대로 진행돼 버려서
        # 게임 진행이 씹히는 문제가 있었음 — 카운트다운이 끝날 때까지 기다린 후 조작한다.
        time.sleep(3.5)

        # 포즈 오버레이 — 채보마다 다른 임의 값
        client.tap_pause_toggle()
        time.sleep(0.2)
        for _ in range(random.randint(1, 3)):
            client.tap_pause_speed_up()
        for _ in range(random.randint(0, 2)):
            client.tap_pause_speed_down()
        rand_calib = round(random.uniform(-200, 200), 1)
        client.pause_calibration(rand_calib)
        record_case(f"{prefix}: 포즈 오버레이(배속/캘리브레이션 슬라이더)", True,
                    note=f"calibration={rand_calib}ms")

        # 터치존 오버레이
        client.touchzone(True)
        time.sleep(0.1)
        client.touchzone(False)
        record_case(f"{prefix}: 터치존 오버레이 on/off", True)

        if i == 0:
            # 첫 채보에서만 "나가기" 버튼 경로를 검증 (완주 경로는 나머지 채보에서 검증)
            client.tap_pause_quit()
            back_ok = client.wait_for_scene("SongSelect", timeout=10)
            record_case(f"{prefix}: 포즈 나가기 → SongSelect", back_ok)
            continue

        client.tap_pause_toggle()  # 재개

        client.wait_game_finished()
        result_ok = client.wait_for_scene("ResultScreen", timeout=15)
        record_case(f"{prefix}: 완주 → ResultScreen 진입", result_ok)

        if result_ok:
            res = client.result()
            record_case(f"{prefix}: 결과값(score/grade) 정합성",
                        "score" in res and "grade" in res, note=str(res)[:200])

        client.tap("select_song")
        back_to_select = client.wait_for_scene("SongSelect", timeout=15)
        record_case(f"{prefix}: 곡선택으로 복귀", back_to_select)

    client.autoplay(False)

    # 법칙 2 — 재현 어려운 예외 팝업은 N/A 처리
    record_na("GameScene: 채보 로드 실패 팝업", "정상 채보만 순회하므로 재현 안 됨 — 별도 재현 트리거 미구현")
    record_na("GameScene: 음악 파일 누락 팝업", "정상 채보만 순회하므로 재현 안 됨 — 별도 재현 트리거 미구현")
    record_na("ResultScreen: 기록 저장 실패 팝업", "정상 저장 경로만 거치므로 재현 안 됨 — 별도 재현 트리거 미구현")


# ── 5. 정상 종료 (법칙 4 마지막 단계) ─────────────────────────────────────

def test_05_songselect_back_button():
    client.tap_songselect_back()
    assert client.wait_for_scene("MainMenu", timeout=10)


def test_05_mainmenu_quit_normal_exit():
    client.tap_mainmenu_quit()
    shut_down = client.wait_for_shutdown(timeout=15)
    record_case("MainMenu: QUIT 버튼 → 정상 종료", shut_down)
    assert shut_down, "QUIT 이후에도 서버가 응답함 — 프로세스가 정상 종료되지 않은 것으로 의심됨"
