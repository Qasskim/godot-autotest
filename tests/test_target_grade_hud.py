# -*- coding: utf-8 -*-
"""플레이 중 목표 등급 표시 — 곡 선택에서 고른 목표 등급이 HUD 쐐기에 '목표 이름 | ME' 와 점수 차이로 뜨고, 그 차이가 규칙대로인지 (2026-11-09).

규칙(DESIGN §13 GameHUD): 목표 점수 = 목표 등급 커트라인(%) × 노트당 만점(Wow 3점) × 지금까지 판정된 노트 수, 표시 차이 = 내 EX − 목표 점수(0 이상이면 '+').
곡은 목표 등급마다 무작위로 고르고(seed 는 실패 메시지에 남김, 고정은 AUTOTEST_SEED), 한 노트를 WOW 로 쳐서 점수를 0 이 아니게 만든 뒤 일시정지하고 화면 글자와 게임 점수를 같은 순간에 읽어 대조한다.
커트라인은 GameBalance.gd 의 grade_thresholds 를 그대로 읽는다. 고스트 대상은 '없음'(서버·계정 불필요, --no-server).
"""
import math
import os
import random
import re
import time

import pytest

import client
from godot_runner import GAME_PROJECT
from screen_helpers import labels, press, ui, wait_until

SEED = int(os.environ.get("AUTOTEST_SEED", str(int(time.time()))))
TARGETS = ["MAX", "S++", "S+", "S", "A", "B", "C", "D"]      # F 는 기준 점수가 없어 목표로 고를 수 없다


def thresholds() -> dict:
    text = open(os.path.join(GAME_PROJECT, "scripts", "core", "GameBalance.gd"), encoding="utf-8").read()
    return {g: float(v) for g, v in re.findall(r'\{"grade": "([A-Z+]+)",\s*"min_accuracy": ([\d.]+)\}', text)}


def gd_roundi(x: float) -> int:
    """GDScript roundi — 0.5 는 0 에서 먼 쪽으로 (파이썬 round 는 짝수 쪽이라 다르다)."""
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


@pytest.fixture(autouse=True)
def _leave_after():
    yield
    if client.scene() == "GameScene":
        if "PAUSED" not in labels():
            client.tap_pause_toggle()
            time.sleep(0.5)
        client.tap_pause_quit()
        client.wait_for_scene("SongSelect", timeout=10)
    if client.scene() == "SongSelect":
        client.pick_option(2, ui("select_target_grade_none"))
    client.autoplay(False)


def wow_one_note() -> dict:
    client.judge_note(0, True)
    deadline = time.time() + 40
    while time.time() < deadline:
        st = client.judge_note_state()
        if st.get("state") == "done":
            return st
        time.sleep(0.02)
    raise AssertionError("WOW 로 칠 노트를 40초 안에 못 찾았습니다")


@pytest.mark.parametrize("target", TARGETS)
def test_target_line_shows_name_me_and_difference_by_rule(target):
    rng = random.Random(f"{SEED}-{target}")
    client.autoplay(False)
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    titles = client.songs()["songs"]
    title = rng.choice(titles)
    where = f"(seed={SEED}, 곡={title}, 목표={target})"
    client.tap_song_at(titles.index(title))
    time.sleep(0.5)
    assert client.pick_option(2, target)["ok"]
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30), f"플레이 화면이 안 열립니다 {where}"
    assert wait_until(lambda: not any(l in ("3", "2", "1") for l in labels()), timeout=15)
    job = wow_one_note()
    assert job.get("grade") == "Wow", f"점수를 만들려고 친 노트가 WOW 가 아닙니다: {job} {where}"
    client.tap_pause_toggle()
    assert wait_until(lambda: "PAUSED" in labels(), timeout=5), f"일시정지 창이 안 뜹니다 {where}"
    time.sleep(0.5)

    st = client.play_state()
    shown = labels()
    acc = thresholds()[target] / 100.0
    assert abs(st["target_accuracy"] - acc) < 1e-6, f"게임이 쓰는 목표 정확도 {st['target_accuracy']} 가 커트라인 {acc} 와 다릅니다 {where}"
    assert not st["ghost_active"], f"고스트 대상이 없음인데 고스트가 켜져 있습니다 {where}"
    target_ex = gd_roundi(acc * 3 * st["judged"])
    diff = st["ex"] - target_ex
    want_diff = f"{'+' if diff >= 0 else ''}{diff}"
    assert target in shown, f"목표 등급 이름 '{target}' 이 화면에 없습니다: {shown} {where}"
    assert "ME" in shown, f"'ME' 글자가 없습니다: {shown} {where}"
    assert want_diff in shown, (f"점수 차이 '{want_diff}' 가 화면에 없습니다 (내 EX {st['ex']}, 판정된 노트 {st['judged']}, 목표 점수 {target_ex}): {shown} {where}")
    assert "BEST" not in shown and "RIVAL" not in shown, f"고스트가 없는데 BEST/RIVAL 이 보입니다: {shown} {where}"
