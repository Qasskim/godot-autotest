# -*- coding: utf-8 -*-
"""플레이 중 고스트 표시 — 곡 선택에서 고른 고스트(전일 1위 / 라이벌)가 HUD 쐐기에 'BEST | ME'·'RIVAL | ME'와 점수 차이로 뜨고, 목표 등급도 함께 고르면 점수 차이 아래에 '목표 이름 차이' 줄이 더해진다 (2026-11-09).

서버 데이터가 있어야 고스트가 생기므로 기개발 서버에 접속하고 고정 테스트 계정 3(나)·4(1위/라이벌)를 쓴다. 곡은 서버에 시험 기록을 만든 배포 곡 'ARTCORE' 4K EZ 로 정해져 있다(무작위로 고를 수 없는 이유).
계정 3 = Wow(전체-20)·Great15·Good5, 계정 4 = 전부 Wow 로 서버에 올린 기록이 고스트가 된다(시험 데이터는 cleanup_server.py 장부가 지운다).
자동 플레이(AUTO)로 켜고 곡을 끝까지 가지 않고 일시정지 → 나가기로 끝내므로 새 기록은 올라가지 않는다. 일시정지한 뒤 화면 글자와 게임 점수를 같은 순간에 읽어 대조한다.
고스트의 같은 시점 점수는 직전 프레임 기준이라 한 노트 차이가 날 수 있어 (현재, 30ms 전) 두 값을 모두 허용한다.
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
from server_helpers import ACCT_A, ACCT_B, login, mix
from test_server_screens import open_select_on_artcore, submit_pc, total_notes
from test_server_social import account_row, remove_all_rivals

pytestmark = pytest.mark.server

SEED = int(os.environ.get("AUTOTEST_SEED", str(int(time.time()))))
TARGETS = ["MAX", "S++", "S+", "S", "A", "B", "C", "D"]


def thresholds() -> dict:
    text = open(os.path.join(GAME_PROJECT, "scripts", "core", "GameBalance.gd"), encoding="utf-8").read()
    return {g: float(v) for g, v in re.findall(r'\{"grade": "([A-Z+]+)",\s*"min_accuracy": ([\d.]+)\}', text)}


def gd_roundi(x: float) -> int:
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def signed(n: int) -> str:
    return f"{'+' if n >= 0 else ''}{n}"


@pytest.fixture(scope="module")
def seeded():
    total = total_notes()
    login(ACCT_A)
    client.clear_server_records()
    submit_pc(ACCT_A, mix(wow=total - 20, great=15, good=5))
    submit_pc(ACCT_B, mix(wow=total))
    login(ACCT_A)
    remove_all_rivals()
    yield {"b": account_row(ACCT_B)}
    # 뒤에 도는 test_server_screens 가 같은 곡에 같은 계정으로 기록을 올리므로, 내가 올린 기록은 치워 둔다(남아 있으면 '기록 갱신 없음'으로 응답이 달라진다)
    login(ACCT_B)
    client.clear_server_records()
    login(ACCT_A)
    client.clear_server_records()


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
        client.pick_option(0, ui("select_ghost_none"))
        client.pick_option(2, ui("select_target_grade_none"))
    client.autoplay(False)
    remove_all_rivals()


def play_with(ghost_item: str, target: str = "") -> dict:
    """곡 선택에서 고스트(와 목표 등급)를 고르고 자동 플레이로 시작해, 고스트 점수가 0 을 넘은 뒤 일시정지한 순간의 게임 상태를 돌려준다."""
    open_select_on_artcore()
    assert client.pick_option(0, ghost_item)["ok"], f"고스트 항목 '{ghost_item}' 을 못 고릅니다: {client.pick_option(0)}"
    assert client.pick_option(2, target or ui("select_target_grade_none"))["ok"]
    client.autoplay(True)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30)
    assert wait_until(lambda: not any(l in ("3", "2", "1") for l in labels()), timeout=15)
    assert wait_until(lambda: client.play_state().get("ghost_active"), timeout=20), "고스트가 켜지지 않았습니다(서버 기록을 못 받음?)"
    assert wait_until(lambda: client.play_state().get("ghost_ex", 0) > 0, timeout=60), "고스트 점수가 0 에서 오르지 않습니다"
    client.tap_pause_toggle()
    assert wait_until(lambda: "PAUSED" in labels(), timeout=5)
    time.sleep(0.5)
    return client.play_state()


def test_best_ghost_shows_best_me_and_difference(seeded):
    st = play_with(ui("select_tab_world"))
    shown = labels()
    wants = {signed(st["ex"] - st["ghost_ex"]), signed(st["ex"] - st["ghost_ex_before"])}
    assert "BEST" in shown and "ME" in shown, f"BEST / ME 글자가 없습니다: {shown}"
    assert "RIVAL" not in shown, f"전일 1위 고스트인데 RIVAL 이 보입니다: {shown}"
    assert wants & set(shown), f"점수 차이 {wants} 중 어느 것도 화면에 없습니다 (내 EX {st['ex']}, 고스트 EX {st['ghost_ex']}): {shown}"


def test_best_ghost_with_target_adds_target_line_under_difference(seeded):
    rng = random.Random(SEED)
    target = rng.choice(TARGETS)
    st = play_with(ui("select_tab_world"), target)
    shown = labels()
    acc = thresholds()[target] / 100.0
    tdiff = st["ex"] - gd_roundi(acc * 3 * st["judged"])
    want_line = f"{target} {signed(tdiff)}"
    wants = {signed(st["ex"] - st["ghost_ex"]), signed(st["ex"] - st["ghost_ex_before"])}
    where = f"(seed={SEED}, 목표={target})"
    assert "BEST" in shown and "ME" in shown, f"BEST / ME 글자가 없습니다: {shown} {where}"
    assert wants & set(shown), f"고스트 점수 차이 {wants} 가 화면에 없습니다: {shown} {where}"
    assert want_line in shown, f"목표 줄 '{want_line}' 이 화면에 없습니다 (내 EX {st['ex']}, 판정된 노트 {st['judged']}): {shown} {where}"


def test_rival_ghost_shows_rival_tag_instead_of_best(seeded):
    b = seeded["b"]
    assert client.service("add_rival", name=b["name"])["ok"]
    st = play_with(b["name"])
    shown = labels()
    wants = {signed(st["ex"] - st["ghost_ex"]), signed(st["ex"] - st["ghost_ex_before"])}
    assert "RIVAL" in shown and "ME" in shown, f"RIVAL / ME 글자가 없습니다: {shown}"
    assert "BEST" not in shown, f"라이벌 고스트인데 BEST 가 보입니다: {shown}"
    assert wants & set(shown), f"점수 차이 {wants} 가 화면에 없습니다 (내 EX {st['ex']}, 고스트 EX {st['ghost_ex']}): {shown}"
