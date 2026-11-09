# -*- coding: utf-8 -*-
"""Miss 확정에도 판정과 같은 보정을 쓰는지 (2026-11-10, 사용자 지시 "miss에도 판정에 넣은 보정과 같은 규칙으로 보정 넣으면 되는 문제 아냐?").

규칙: 입력 시각 = 곡 위치 + 보정, 입력 시각이 노트 시각보다 150ms 넘게 늦으면 Miss (GameManager 의 Miss 확정 루프).
수정 전에는 Miss 확정이 보정 없이 '곡 위치 − 노트 시각 > 150ms'여서, 보정이 음수이면 정상 판정 구간의 늦은 쪽이 먼저 Miss 로 사라졌다.

곡은 곡 목록의 첫 곡. 자동 플레이는 끄고, TestServer /debug_judge_note 가 곡 시계로 '노트 시각 + 오프셋(입력 시각 오차)' 에 그 레인을 터치한다.
이 시험의 값(보정 −100·+100, 오차 +60·+100·+160, 대기 시간)은 사용자가 지정한 것이 아니라 시험 작성자가 정했다.
서버·계정은 쓰지 않는다(--no-server).
"""
import time

import pytest

import client
from screen_helpers import labels, press, wait_until

# (설명, 보정 ms, 노트 시각에 더할 오차 ms, 기대 등급 — None 이면 판정을 못 받아야 함)
CASES = [
    ("보정 −100, 오차 +60: 곡 위치로는 노트+160(150 넘음)이지만 입력 시각 오차는 Great 창 안", -100.0, 60.0, "Great"),
    ("보정 +100, 오차 +60: 곡 위치로는 노트−40", 100.0, 60.0, "Great"),
    ("보정 0, 오차 +100: 150 안이라 이전과 같음(대조)", 0.0, 100.0, "Good"),
    ("보정 +100, 오차 +160: 입력 시각 오차가 150을 넘어 Miss 로 먼저 사라짐", 100.0, 160.0, None),
]
WAIT_DONE_S = 40
WAIT_NONE_S = 12


@pytest.fixture(autouse=True)
def _restore():
    yield
    client.calibration(0.0)
    if client.scene() == "GameScene":
        if "PAUSED" not in labels():
            client.tap_pause_toggle()
            time.sleep(0.5)
        client.tap_pause_quit()
        client.wait_for_scene("SongSelect", timeout=10)
    client.autoplay(False)


def start_song():
    client.autoplay(False)
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    client.tap_song_at(0)
    time.sleep(0.5)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30)
    assert wait_until(lambda: not any(l in ("3", "2", "1") for l in labels()), timeout=15), "시작 카운트다운이 안 끝납니다"


def run_case(cal: float, offset: float, expect_none: bool) -> dict:
    client.calibration(cal)
    client.judge_note(offset, True)
    limit = WAIT_NONE_S if expect_none else WAIT_DONE_S
    deadline = time.time() + limit
    st = {}
    while time.time() < deadline:
        st = client.judge_note_state()
        if st.get("state") == "done":
            return st
        if client.scene() != "GameScene":
            return {"state": "scene-left", "scene": client.scene()}
        time.sleep(0.02)
    return st


def test_miss_uses_same_calibration_as_judgment():
    start_song()
    results = []
    for desc, cal, offset, want in CASES:
        st = run_case(cal, offset, want is None)
        got = st.get("grade") if st.get("state") == "done" else None
        results.append(f"{desc} → {got}")
        assert got == want, f"{desc}: 기대 {want} 실제 {got} / 상태 {st} / 앞선 결과 {results[:-1]}"
