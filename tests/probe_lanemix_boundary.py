# -*- coding: utf-8 -*-
"""레인믹스 구간 경계의 입력 측정 도구 (pytest 아님 — 직접 실행). 2026-11-09.

곡·사용자 보정값·입력 시각(경계 노트 시각 기준 delta ms)을 바꿔 가며 '그 입력이 판정으로 이어지는지 / 사라지는지'를 잰다.
  python probe_lanemix_boundary.py --songs "CITY POP,ROCK" --cals 0,143 --deltas -60,-15,15,60 --edge start
  --edge start : 수락한 구간의 시작(lanemix_start) 시각에 있는 레인믹스 레이어 노트(L16~31)를 누른다.
  --edge end   : 구간 끝(lanemix_end) 직전의 레인믹스 노트와 끝 직후의 기본 노트를 누른다.
각 조합이 게임 한 판이다(수락 안내를 누른 뒤 자동 플레이를 끄고 정해진 시각에 누름). 서버·계정은 쓰지 않는다(--no-server).
출력: 조합마다 한 줄 — 노트별로 JUDGED(등급, 오차) 또는 DROPPED(판정 없음 / Miss).
"""
import argparse
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client  # noqa: E402
import godot_runner  # noqa: E402
from screen_helpers import press, wait_until  # noqa: E402

CHARTS = os.path.join(godot_runner.GAME_PROJECT, "charts", "keysound")


def find_chart(section_start: float):
    diff = COMBO[1] if COMBO else "EZ"
    for f in glob.glob(os.path.join(CHARTS, "*", f"*_{diff}_v8.rgds")):
        d = json.load(open(f, encoding="utf-8"))
        st = [e["timing_ms"] for e in d.get("gimmick_events", []) if e.get("action") == "lanemix_start"]
        if st and abs(st[0] - section_start) < 1.0:
            return d
    return None


COMBO = None          # (키 수 문자열 "6K", 난이도 "EX") — None 이면 곡 선택 화면의 기본(4K EZ)
WINDOW_MS = 0         # 0 이면 시작 시각 정각의 노트만, 양수면 시작 시각부터 그 ms 안의 레인믹스 노트 전부


def select_combo(key: str, diff: str):
    for _ in range(14):
        b = client.screen_buttons()
        if key in b and diff in b:
            break
        # 키 버튼과 난이도 버튼을 번갈아 눌러 원하는 조합이 될 때까지 돌린다(곡 선택의 순환 버튼)
        if key not in b:
            press(next(x for x in b if x[-1] == "K" and x[:-1].isdigit()))
        elif diff not in b:
            press(next(x for x in b if x in ("EZ", "NM", "HD", "EX")))
    time.sleep(0.6)


def start_song(title: str):
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    titles = client.songs()["songs"]
    client.tap_song_at(titles.index(title))
    time.sleep(0.5)
    if COMBO:
        select_combo(*COMBO)
    client.autoplay(True)
    client.autolanemix(False)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30)


def leave():
    if client.scene() == "GameScene":
        client.tap_pause_toggle()
        time.sleep(0.5)
        client.tap_pause_quit()
        client.wait_for_scene("SongSelect", timeout=10)
    client.autoplay(False)


def wait_state(want: str, timeout: float) -> dict:
    deadline = time.time() + timeout
    p = client.lanemix_prompt()
    while time.time() < deadline:
        p = client.lanemix_prompt()
        if p["state"] == want:
            return p
        time.sleep(0.03)
    raise RuntimeError(f"안내 상태 {want} 를 못 봤습니다: {p}")


def outcome(log: dict, lane: int, note_ms: float) -> str:
    for j in log["judgments"]:
        if j["lane"] == lane % 16 and abs(j["music_ms"] - note_ms) < 500:
            return "DROPPED(Miss)" if j["grade"] == "Miss" else f"JUDGED({j['grade']},{j['error_ms']})"
    return "DROPPED(판정 없음)"


def run_one(title: str, cal: float, delta: float, edge: str) -> str:
    start_song(title)
    client.calibration(cal)
    p = wait_state("OFFER", timeout=170)
    sec_start = p["section_starts"][0]
    chart = find_chart(sec_start)
    if chart is None:
        return f"{title} cal={cal} delta={delta}: 채보를 못 찾음(start={sec_start})"
    ends = [e["timing_ms"] for e in chart["gimmick_events"] if e.get("action") == "lanemix_end"]
    sec_end = ends[0] if ends else None
    taps = [n for n in chart["score"] if n.get("type") == "tap" and n["lane"] < 32]
    client.click(p["button_x"], p["button_y"])
    if edge == "start":
        near = [n for n in taps if n["lane"] >= 16 and abs(n["timing_ms"] - sec_start) < 1.0]
        if WINDOW_MS:
            near = [n for n in taps if n["lane"] >= 16 and sec_start - 1.0 <= n["timing_ms"] <= sec_start + WINDOW_MS]
        if not near:
            near = sorted([n for n in taps if n["lane"] >= 16 and n["timing_ms"] >= sec_start], key=lambda n: n["timing_ms"])[:1]
        targets = near
    else:
        wait_state("RETURN", timeout=200)
        lm = sorted([n for n in taps if n["lane"] >= 16 and sec_end - 1200 <= n["timing_ms"] <= sec_end], key=lambda n: n["timing_ms"])[-2:]
        base = sorted([n for n in taps if n["lane"] < 16 and sec_end <= n["timing_ms"] <= sec_end + 1200], key=lambda n: n["timing_ms"])[:2]
        targets = lm + base
    client.autoplay_live(False)
    client.press_plan([(n["timing_ms"] + delta, n["lane"] % 16) for n in targets])
    last = max(n["timing_ms"] for n in targets) + delta
    while client.lanemix_prompt()["music_ms"] < last + 700:
        time.sleep(0.05)
        if client.scene() != "GameScene":
            break
    log = client.judgment_log()
    parts = []
    for n in targets:
        rel = n["timing_ms"] - (sec_start if edge == "start" else sec_end)
        parts.append(f"rel={rel:.0f} lane={n['lane']} {outcome(log, n['lane'], n['timing_ms'])}")
    return f"{title:9s} edge={edge} cal={cal:>5} delta={delta:>5}: " + " | ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--songs", default="CITY POP,ROCK")
    ap.add_argument("--cals", default="0,143")
    ap.add_argument("--deltas", default="-60,-15,15,60")
    ap.add_argument("--edge", default="start", choices=["start", "end"])
    ap.add_argument("--combo", default="", help='예: "6K,EX" (키 수,난이도). 비우면 4K EZ')
    ap.add_argument("--window", type=int, default=0, help="시작 경계: 시작 시각부터 이 ms 안의 레인믹스 노트를 전부 누른다(0=정각 노트만)")
    a = ap.parse_args()
    global COMBO, WINDOW_MS
    COMBO = tuple(a.combo.split(",")) if a.combo else None
    WINDOW_MS = a.window
    proc = godot_runner.start_game()
    try:
        for title in a.songs.split(","):
            for cal in [float(x) for x in a.cals.split(",")]:
                for d in [float(x) for x in a.deltas.split(",")]:
                    try:
                        print(run_one(title, cal, d, a.edge), flush=True)
                    except Exception as e:  # noqa: BLE001 — 한 조합이 실패해도 나머지를 잰다
                        print(f"{title} cal={cal} delta={d}: 오류 {e!r}", flush=True)
                    leave()
    finally:
        godot_runner.stop_game(proc)


if __name__ == "__main__":
    main()
