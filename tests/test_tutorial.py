# -*- coding: utf-8 -*-
"""튜토리얼 화면 — 화면에 보이는 글자로 확인 (기준 docs/TUTORIAL_SPEC.md, 2026-11-08 사용자와 정한 케이스).

게임 TestServer 의 /screen_texts(화면에 보이는 글자 읽기)·/screen_press(글자로 버튼 누르기)를 쓴다. 대사는 사양서 §4 표 그대로(screen_helpers.DIALOGUE).
소리·모양은 사람이 확인한다. 서버·계정은 쓰지 않는다(--no-server).
"""
import time

import pytest

import client
from screen_helpers import (DIALOGUE, HAS_START, enter_tutorial_via_play, enter_tutorial_via_settings, jump_to_stage,
                            labels, norm, press, stage_label, ui, wait_until)

PREV, NEXT = ui("tutorial_prev_btn"), ui("tutorial_next_btn")
# 각 단계에서 '다음'만 눌러 닿을 수 있는 마지막 대사 번호 — 노트가 있는 단계는 마지막 대사에서 START, 5단계는 1번 대사에서 YES/NO 로 바뀐다
LAST_BY_NEXT = {0: 6, 1: 3, 2: 3, 3: 1, 4: 1}
# 사양서(docs/TUTORIAL_SPEC.md §4 표)와 게임 문구가 다른 두 줄 — (단계, 대사 번호): 게임에 실제로 나오는 문구. 어느 쪽이 맞는지 정해지면 한쪽을 고치고 여기서 지운다.
# 아래 순회 테스트는 이 두 줄을 게임 문구로 비교하고, 사양서 문구와의 비교는 맨 끝 xfail 테스트가 맡는다.
GAME_WORDING = {
    (2, 1): "가운데 버튼을 누르면 준비가 되고, 3, 2, 1 카운트다운 뒤에 레인믹스에 진입해요. 누르지 않으면 지금 레인 그대로 이어져요.",
    (2, 2): "레인믹스를 실행할지는 여러분이 직접 선택할 수 있어요.",
}


def buttons() -> list:
    return client.screen_buttons()


# ── 1. 처음 들어왔을 때 ─────────────────────────────────────────────

def test_entry_shows_skip_stage_label_first_line_and_prev_next():
    enter_tutorial_via_play()
    assert stage_label(0) in labels()
    assert DIALOGUE[0][0] in labels()
    for name in (PREV, NEXT, "SKIP"):
        assert name in buttons(), f"'{name}' 버튼이 보이지 않습니다: {buttons()}"
    for name in ("START", "OK", "YES", "NO"):
        assert name not in buttons(), f"처음 화면에 '{name}' 버튼이 보이면 안 됩니다"


def test_prev_on_first_line_is_disabled_and_changes_nothing():
    """첫 대사에서는 '이전' 버튼이 눌리지 않는 상태(흐리게)로 보이고, 눌러 보려 해도 화면이 그대로다."""
    enter_tutorial_via_play()
    before = client.screen()["items"]
    prev_item = next(i for i in before if i["kind"] == "button" and i["text"] == PREV)
    assert prev_item["disabled"] is True, "첫 대사의 '이전' 버튼은 눌리지 않는 상태여야 합니다"
    assert client.press_text(PREV) is False
    assert client.screen()["items"] == before


# ── 2. 다음·이전을 눌렀을 때 대사 ───────────────────────────────────

@pytest.mark.parametrize("stage", range(5))
def test_next_shows_the_stage_dialogue_in_order(stage):
    """'다음'을 누를 때마다 사양서의 대사가 순서대로 나오고, 화면 위 단계 표시는 그대로다."""
    enter_tutorial_via_play()
    jump_to_stage(stage)
    for i in range(LAST_BY_NEXT[stage] + 1):
        want = GAME_WORDING.get((stage, i), DIALOGUE[stage][i])
        assert want in labels(), f"Stage {stage + 1} {i + 1}번째 대사가 다릅니다 — 화면: {labels()}"
        assert stage_label(stage) in labels()
        if i < LAST_BY_NEXT[stage]:
            press(NEXT)


def test_prev_goes_back_one_line_and_crosses_to_previous_stage():
    enter_tutorial_via_play()
    jump_to_stage(0, 2)
    press(PREV)
    assert DIALOGUE[0][1] in labels()
    press(PREV)
    assert DIALOGUE[0][0] in labels()
    jump_to_stage(1)                                       # 2단계 첫 대사에서 이전 → 1단계 마지막 대사
    press(PREV)
    assert stage_label(0) in labels() and DIALOGUE[0][-1] in labels()


# ── 3. 노트가 있는 단계의 START ─────────────────────────────────────

@pytest.mark.parametrize("stage", [s for s, has in enumerate(HAS_START) if has])
def test_note_stage_last_line_shows_start_instead_of_prev_next(stage):
    enter_tutorial_via_play()
    jump_to_stage(stage, len(DIALOGUE[stage]) - 1)
    assert DIALOGUE[stage][-1] in labels()
    assert "START" in buttons()
    assert PREV not in buttons() and NEXT not in buttons()


def test_stage_without_notes_next_on_last_line_moves_to_next_stage():
    enter_tutorial_via_play()
    jump_to_stage(2, 3)
    assert NEXT in buttons() and "START" not in buttons()
    press(NEXT)
    assert stage_label(3) in labels() and DIALOGUE[3][0] in labels()


def test_start_hides_nav_shows_practice_prompt_then_goes_to_next_stage():
    enter_tutorial_via_play()
    jump_to_stage(0, 6)
    press("START")
    assert PREV not in buttons() and NEXT not in buttons() and "START" not in buttons()
    assert "SKIP" in buttons()
    assert DIALOGUE[0][6] not in labels() and stage_label(0) in labels(), f"노트가 나오는 동안에는 대사 상자가 사라지고 단계 표시만 남아야 합니다 — 화면: {labels()}"
    assert wait_until(lambda: stage_label(1) in labels(), timeout=120), f"노트가 끝났는데 2단계로 안 넘어갑니다 — 화면: {labels()}"
    assert DIALOGUE[1][0] in labels()


def test_judgment_demo_shows_auto_play_badge_then_goes_to_next_stage():
    enter_tutorial_via_play()
    jump_to_stage(1, 3)
    press("START")
    assert wait_until(lambda: "AUTO PLAY" in labels(), timeout=15), f"AUTO PLAY 표시가 안 보입니다 — 화면: {labels()}"
    assert wait_until(lambda: stage_label(2) in labels(), timeout=120), f"자동 시연이 끝났는데 3단계로 안 넘어갑니다 — 화면: {labels()}"
    assert DIALOGUE[2][0] in labels()


# ── 4. 예/아니오와 완료 ─────────────────────────────────────────────

def go_to_choice_line() -> None:
    enter_tutorial_via_play()
    jump_to_stage(4, 1)
    assert DIALOGUE[4][1] in labels()
    assert "YES" in buttons() and "NO" in buttons()
    assert NEXT not in buttons() and PREV not in buttons() and "OK" not in buttons()


def finish_with_ok_to_song_select() -> None:
    assert DIALOGUE[4][3] in labels()
    assert "OK" in buttons()
    for name in (NEXT, "YES", "NO"):
        assert name not in buttons()
    press("OK")
    assert client.wait_for_scene("SongSelect", timeout=10), "OK 를 눌렀는데 곡 선택 화면이 나오지 않았습니다"


def play_goes_straight_to_song_select() -> None:
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15)
    time.sleep(0.8)
    client.tap_mainmenu_play()
    assert client.wait_for_scene("SongSelect", timeout=10), "튜토리얼을 마친 뒤 PLAY 가 곡 선택으로 가지 않습니다"


def test_choice_no_goes_to_completion_lines_then_ok_opens_song_select():
    go_to_choice_line()
    press("NO")
    assert DIALOGUE[4][2] in labels()
    press(NEXT)
    finish_with_ok_to_song_select()
    play_goes_straight_to_song_select()


def test_choice_yes_runs_practice_then_completion_lines_then_ok_opens_song_select():
    go_to_choice_line()
    press("YES")
    assert DIALOGUE[4][1] not in labels() and "YES" not in buttons(), f"실전 중에는 대사 상자가 사라져야 합니다 — 화면: {labels()}"
    assert wait_until(lambda: DIALOGUE[4][2] in labels(), timeout=300), f"실전이 끝났는데 완료 대사가 안 나옵니다 — 화면: {labels()}"
    press(NEXT)
    finish_with_ok_to_song_select()
    play_goes_straight_to_song_select()


# ── 5. 스킵 ─────────────────────────────────────────────────────────

def test_skip_opens_song_select_and_play_no_longer_opens_tutorial():
    enter_tutorial_via_play()
    press("SKIP")
    assert client.wait_for_scene("SongSelect", timeout=10), "스킵을 눌렀는데 곡 선택 화면이 나오지 않았습니다"
    play_goes_straight_to_song_select()


# ── 6. BGM ──────────────────────────────────────────────────────────

def test_next_does_not_restart_bgm():
    enter_tutorial_via_play()
    time.sleep(1.5)
    pos = lambda: client._req("GET", "/tutorial_state")["bgm"]["playback_position"]
    before = pos()
    for _ in range(3):
        press(NEXT)
    after = pos()
    assert after > before, f"다음을 눌렀더니 BGM 재생 위치가 처음으로 돌아갔습니다: {before:.2f}초 → {after:.2f}초"


# ── 7. 설정 → 튜토리얼 다시보기 ─────────────────────────────────────

def test_settings_replay_opens_stage_list_popup():
    enter_tutorial_via_settings()
    assert ui("settings_tutorial_popup_title") in labels()
    for i, title in enumerate(["기본 노트", "판정 등급", "레인믹스 안내", "레인믹스 모드 체험", "실전 체험"]):
        assert f"{i + 1}. {title}" in buttons(), f"스테이지 목록에 '{i + 1}. {title}' 가 없습니다: {buttons()}"
    assert ui("settings_cancel") in buttons()


def test_settings_replay_picking_a_stage_shows_its_first_line():
    enter_tutorial_via_settings()
    press("3. 레인믹스 안내")
    assert stage_label(2) in labels() and DIALOGUE[2][0] in labels()


def test_settings_replay_cancel_returns_to_settings():
    enter_tutorial_via_settings()
    press(ui("settings_cancel"))
    assert client.wait_for_scene("Settings", timeout=10), "취소를 눌렀는데 설정 화면으로 돌아오지 않았습니다"


def test_settings_replay_skip_returns_to_settings_not_song_select():
    enter_tutorial_via_settings()
    press("1. 기본 노트")
    press("SKIP")
    assert client.wait_for_scene("Settings", timeout=10), "스킵했는데 설정 화면으로 돌아오지 않았습니다"


def test_settings_replay_finish_returns_to_settings_not_song_select():
    enter_tutorial_via_settings()
    press("5. 실전 체험")
    press(NEXT)
    press("NO")
    press(NEXT)
    assert "OK" in buttons()
    press("OK")
    assert client.wait_for_scene("Settings", timeout=10), "끝까지 마쳤는데 설정 화면으로 돌아오지 않았습니다"


@pytest.mark.parametrize("line", [1, 2])
@pytest.mark.xfail(strict=True, reason="사양서 §4 표와 게임 문구가 다름(Stage 3의 2·3번째 대사) — 어느 쪽이 맞는지 사용자 결정 대기")
def test_known_wording_difference_stage3_matches_spec_exactly(line):
    enter_tutorial_via_play()
    jump_to_stage(2, line)
    assert DIALOGUE[2][line] in labels()
