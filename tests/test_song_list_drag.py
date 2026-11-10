# -*- coding: utf-8 -*-
"""곡 목록 끌어서 스크롤 — 손가락으로 목록을 끌면 스크롤되고, 끌었을 때 눌려 있던 곡이 선택되지 않는다 (DragScrollContainer, 기준 컴포넌트 설명 2026-10-04 "곡 리스트 드래그 스크롤").

규칙(코드 주석): 임계 거리 이상 움직이면 드래그 → 스크롤만 하고 버튼 클릭은 일어나지 않음 / 목록 영역 밖에서 시작한 끌기는 무시 / 스크롤은 0 ~ 최대 사이.
TestServer /debug_drag 가 터치 누름·끌기·뗌을 보내고 /debug_scroll 이 스크롤 위치·최대·영역·선택된 곡 번호를 읽는다. 모양(관성·부드러움)은 사람이 확인한다.
이 시험의 끌기 거리(영역 높이의 50%)·나눔 횟수(12)·허용 비율(끈 거리의 50%~100%)은 사용자가 정한 값이 아니라 시험 작성자가 정했다. 서버·계정은 쓰지 않는다(--no-server).
"""
import time

import pytest

import client
from screen_helpers import wait_until


def scroll() -> dict:
    return client._req("GET", "/debug_scroll")


def drag(x: float, y1: float, y2: float, steps: int = 12) -> None:
    client._req("POST", f"/debug_drag?x1={x}&y1={y1}&x2={x}&y2={y2}&steps={steps}")
    time.sleep(0.4)


@pytest.fixture(scope="module", autouse=True)
def song_select():
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.5)
    s = scroll()
    if s["max"] <= 0:
        pytest.skip(f"곡 목록이 한 화면에 다 들어가 스크롤할 수 없습니다: {s}")
    return s


def test_dragging_up_scrolls_the_list_down_without_selecting_a_song():
    s0 = scroll()
    x = s0["x"] + s0["w"] / 2
    top = s0["y"] + s0["h"] * 0.15
    bottom = s0["y"] + s0["h"] * 0.85
    dist = (bottom - top) * 0.7
    drag(x, bottom, bottom - dist)
    s1 = scroll()
    moved = s1["scroll"] - s0["scroll"]
    assert moved >= dist * 0.5, f"위로 끌었는데 목록이 충분히 내려가지 않았습니다(끈 거리 {dist:.0f}, 스크롤 변화 {moved}): {s0} → {s1}"
    assert moved <= dist + 1, f"끈 거리보다 더 많이 스크롤됐습니다(끈 거리 {dist:.0f}, 변화 {moved})"
    assert s1["selected"] == s0["selected"], f"끌었더니 곡 선택이 바뀌었습니다: {s0['selected']} → {s1['selected']}"


def test_dragging_down_scrolls_back_and_clamps_at_the_top():
    s0 = scroll()
    x = s0["x"] + s0["w"] / 2
    top = s0["y"] + s0["h"] * 0.1
    bottom = s0["y"] + s0["h"] * 0.9
    for _ in range(6):
        drag(x, top, bottom)
    s1 = scroll()
    assert s1["scroll"] == 0, f"계속 아래로 끌었는데 맨 위(0)에서 멈추지 않았습니다: {s1}"
    assert s1["selected"] == s0["selected"], "끌었더니 곡 선택이 바뀌었습니다"


def test_dragging_far_up_clamps_at_the_end_of_the_list():
    s0 = scroll()
    x = s0["x"] + s0["w"] / 2
    top = s0["y"] + s0["h"] * 0.1
    bottom = s0["y"] + s0["h"] * 0.9
    for _ in range(10):
        drag(x, bottom, top)
    s1 = scroll()
    assert s1["scroll"] == s1["max"], f"계속 위로 끌었는데 목록 끝(최대)에서 멈추지 않았습니다: {s1}"
    for _ in range(10):
        drag(x, top, bottom)


def test_a_drag_that_starts_outside_the_list_does_not_scroll_it():
    s0 = scroll()
    x = s0["x"] + s0["w"] / 2
    outside = max(5.0, s0["y"] - 40)
    drag(x, outside, outside - 4.0 if outside > 9 else outside + 4.0, steps=4)       # 영역 밖에서 짧게 끌기
    client._req("POST", f"/debug_drag?x1={x}&y1={outside}&x2={x}&y2={outside + 200}&steps=12")
    time.sleep(0.4)
    s1 = scroll()
    assert s1["scroll"] == s0["scroll"], f"목록 밖에서 시작한 끌기로 목록이 스크롤됐습니다: {s0['scroll']} → {s1['scroll']}"


def test_a_short_movement_under_the_threshold_is_a_tap_not_a_scroll():
    s0 = scroll()
    x = s0["x"] + s0["w"] / 2
    y = s0["y"] + s0["h"] * 0.5
    drag(x, y, y + 3.0, steps=3)
    s1 = scroll()
    assert s1["scroll"] == s0["scroll"], f"임계값 아래의 작은 움직임으로 목록이 스크롤됐습니다: {s0['scroll']} → {s1['scroll']}"
