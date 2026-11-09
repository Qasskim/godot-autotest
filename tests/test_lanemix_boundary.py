# -*- coding: utf-8 -*-
"""레인믹스 구간 경계 입력 소실 회귀 시험 (2026-11-09) — 눌렀는데 판정 없이 사라지는 입력이 없어야 한다.

배경: 사용자 보정(user_calibration_ms)이 양수이면 입력 시각(= 곡 위치 + 보정)이 구간 시작 시각을 넘는데 곡 위치는 아직 시작 전이라
레인믹스 노트가 판정 목록에 없다. 이때 입력을 보관하는 조건(GameManager._buffer_early_press)이 '입력 시각 < 시작 시각'만 받아 버려졌다.
실제 유저 제보(테크노 곡 전환 때 터치가 씹힘)의 원인.

방식: 수락한 구간의 시작 시각부터 250ms(Oops 창) 안의 레인믹스 노트 전부를 한 판에서 같은 입력 시각 오차(노트 시각 기준 ms)로 누르고,
눌린 노트가 전부 JUDGED(등급이 나옴)인지 본다. DROPPED(판정 없음 / Miss)가 하나라도 있으면 실패. 4K EZ 는 구간 시작 창 안에 노트가 1개뿐인 곡이 많아서
(2026-11-09 첫 판은 오차를 노트마다 돌려 쓰다 -60ms 만 눌러 수정 전에도 통과한 헛시험이었다) 한 판에 오차 하나를 고정하고 판을 나눈다.
수정 전 측정에서 사라진 조합: 보정 50+오차 +15, 보정 143+오차 +15·+60 (오차는 입력 시각 − 노트 시각).
이 시험의 값(곡·키 수·난이도·보정·오차·250ms)은 사용자가 지정한 것이 아니라 시험 작성자가 정했다.
보정이 음수일 때 늦은 입력이 사라지는 것은 별개 원인(Miss 확정이 곡 위치 150ms 기준 — 판정 규칙이라 사용자 결정 대기)이라 여기서 다루지 않는다.
서버·계정은 쓰지 않는다. 측정 도구는 probe_lanemix_boundary.py 를 그대로 쓴다.
"""
import time

import pytest

import client
import probe_lanemix_boundary as pb

MIXED_DELTAS = [-15.0, 15.0, 60.0]      # 노트가 여럿인 어려운 채보(6K EX)에서 노트마다 돌려 쓴다(-60 은 시작 직전 기본 노트와 분리할 시간이 모자라 뺐다)
WINDOW_MS = 250


@pytest.fixture(autouse=True)
def _leave_after():
    yield
    pb.COMBO = None
    pb.WINDOW_MS = 0
    client.calibration(0.0)      # 보정이 다음 시험으로 새지 않게(2026-11-10: 예전엔 143 이 남아 뒤 시험이 그 보정으로 돌았다)
    try:
        pb.leave()
    except Exception:  # noqa: BLE001 — 정리 실패가 시험 결과를 덮지 않게
        pass
    client.autolanemix(True)


def _run(title: str, combo, cal: float, edge: str, deltas: list) -> list:
    """한 판을 돌려 [(노트 설명, 입력 오차, 결과 문자열)]를 돌려준다."""
    pb.COMBO = combo or ("4K", "EZ")      # 항상 명시한다 — 앞 시험이 고른 키 수·난이도가 남아 다른 채보가 뜨는 것을 막는다
    pb.WINDOW_MS = WINDOW_MS
    pb.start_song(title)
    client.calibration(cal)
    p = pb.wait_state("OFFER", timeout=170)
    sec_start = p["section_starts"][0]
    chart = pb.find_chart(sec_start)
    assert chart is not None, f"{title}: 구간 시작 {sec_start} 의 채보를 못 찾음"
    ends = [e["timing_ms"] for e in chart["gimmick_events"] if e.get("action") == "lanemix_end"]
    sec_end = ends[0]
    taps = [n for n in chart["score"] if n.get("type") == "tap" and n["lane"] < 32]
    client.click(p["button_x"], p["button_y"])
    if edge == "start":
        targets = sorted([n for n in taps if n["lane"] >= 16 and sec_start - 1.0 <= n["timing_ms"] <= sec_start + WINDOW_MS],
                         key=lambda n: (n["timing_ms"], n["lane"]))
    else:
        pb.wait_state("RETURN", timeout=200)
        lm = sorted([n for n in taps if n["lane"] >= 16 and sec_end - 1200 <= n["timing_ms"] <= sec_end], key=lambda n: n["timing_ms"])[-2:]
        base = sorted([n for n in taps if n["lane"] < 16 and sec_end <= n["timing_ms"] <= sec_end + 1200], key=lambda n: n["timing_ms"])[:2]
        targets = lm + base
    assert targets, f"{title}: 누를 노트가 없음(edge={edge})"
    print(f"[{title}] 구간 시작 {sec_start:.0f}ms 대상 노트 {[(n['lane'], n['timing_ms']) for n in targets]}")
    plan = [(n["timing_ms"] + deltas[i % len(deltas)], n["lane"] % 16) for i, n in enumerate(targets)]
    if edge == "start":
        # 구간 시작 직전의 기본 노트가 안 쳐진 채로 남아 있으면 시작 부근 입력이 그 노트에 쓰인다(Oops 늦음) — 실제 플레이에서는 이미 쳤을 노트다.
        # 그래서 자동 플레이가 그 노트를 친 뒤에 끈다. 첫 입력보다 20ms 이상 앞서 끌 수 없으면 시험을 만들 수 없는 곡이다.
        first_pos = min(ms for ms, _ in plan) - cal
        prev = [n["timing_ms"] for n in taps if n["lane"] < 16 and first_pos + cal - 250 < n["timing_ms"] < sec_start - 1.0]
        if prev:
            wait_pos = max(prev) + 40
            assert wait_pos <= first_pos - 20, f"{title}: 시작 직전 기본 노트({max(prev):.0f}ms)와 첫 입력({first_pos:.0f}ms)이 너무 가까워 분리할 수 없음"
            while client.lanemix_prompt()["music_ms"] < wait_pos:
                time.sleep(0.01)
    client.autoplay_live(False)
    client.press_plan(plan)
    last = max(ms for ms, _ in plan)
    deadline = time.time() + 120
    while client.lanemix_prompt()["music_ms"] < last + 700 and time.time() < deadline:
        time.sleep(0.05)
        if client.scene() != "GameScene":
            break
    log = client.judgment_log()
    base_for_print = sec_start if edge == "start" else sec_end
    print(f"[{title} cal={cal:g} edge={edge}] 구간 {'시작' if edge == 'start' else '끝'} {base_for_print:.0f}ms 기준 실제 누른 시각(곡 위치): "
          + ", ".join(f"레인{p['lane']} 곡위치 {p['music_ms'] - base_for_print:+.0f}ms(입력시각 {p['ms'] - base_for_print:+.0f}ms)" for p in log["presses"]))
    print(f"[{title} cal={cal:g} edge={edge}] 누른 기록 {len(log['presses'])}건, 판정 {[(j['lane'], j['grade'], j['error_ms']) for j in log['judgments']]}")
    base_ms = sec_start if edge == "start" else sec_end
    return [(f"시작 기준 {n['timing_ms'] - base_ms:+.0f}ms lane={n['lane']}", deltas[i % len(deltas)], pb.outcome(log, n["lane"], n["timing_ms"]))
            for i, n in enumerate(targets)]


def _assert_none_dropped(label: str, rows: list) -> None:
    print(label, rows)
    bad = [f"{what} 입력오차 {d:+.0f}ms → {res}" for what, d, res in rows if not res.startswith("JUDGED")]
    assert not bad, f"{label}: 눌렀는데 판정 없이 사라진 입력 {len(bad)}/{len(rows)}개\n" + "\n".join(bad)


@pytest.mark.slow
@pytest.mark.parametrize("cal,delta", [(0.0, -15.0), (50.0, 15.0), (143.0, 15.0), (143.0, 60.0)])
@pytest.mark.parametrize("title", ["CITY POP", "HARDSTYLE", "TECHNO A"])
def test_start_edge_ez_no_input_lost(title, cal, delta):
    _assert_none_dropped(f"{title} 4K EZ 보정 {cal:g} 오차 {delta:+.0f}", _run(title, None, cal, "start", [delta]))


@pytest.mark.slow
@pytest.mark.parametrize("title", ["ROCK", "HARDSTYLE"])
def test_start_edge_6k_ex_no_input_lost(title):
    _assert_none_dropped(f"{title} 6K EX 보정 143", _run(title, ("6K", "EX"), 143.0, "start", MIXED_DELTAS))


@pytest.mark.slow
def test_end_edge_no_input_lost():
    _assert_none_dropped("ROCK 4K EZ 끝 시점 보정 143", _run("ROCK", None, 143.0, "end", MIXED_DELTAS))
