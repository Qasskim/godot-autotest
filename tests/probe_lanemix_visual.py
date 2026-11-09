# -*- coding: utf-8 -*-
"""레인믹스 구간 끝(원복) 직전·직후에 '이미 떠 있던 노트'가 어느 키 수 배치로 그려지는지 재는 도구 (pytest 아님 — 직접 실행). 2026-11-09.
  python probe_lanemix_visual.py --songs "CITY POP,ROCK" --combo "4K,EZ"
구간 끝 시각 전후로 /debug_notes 를 계속 읽어, 끝 시각 뒤에 칠 기본 노트가 (1) 끝 전에는 어떤 key_mode·cx 로 그려지고 (2) 끝 순간에 어떻게 바뀌는지 기록한다.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client  # noqa: E402
import godot_runner  # noqa: E402
import probe_lanemix_boundary as pb  # noqa: E402


def run(title: str) -> None:
    pb.start_song(title)
    p = pb.wait_state("OFFER", timeout=170)
    sec_start = p["section_starts"][0]
    chart = pb.find_chart(sec_start)
    sec_end = [e["timing_ms"] for e in chart["gimmick_events"] if e.get("action") == "lanemix_end"][0]
    client.click(p["button_x"], p["button_y"])
    pb.wait_state("RETURN", timeout=200)
    track = {}                     # (timing_ms, lane) -> [(music_ms, key_mode, cx)]
    t_end = time.time() + 40
    while time.time() < t_end:
        st = client.notes_on_screen()
        now = st["music_ms"]
        for n in st["notes"]:
            if sec_end <= n["timing_ms"] <= sec_end + 1500 and n["lane"] < 16:
                track.setdefault((round(n["timing_ms"], 1), n["lane"]), []).append((now, n["key_mode"], n["cx"]))
        if now > sec_end + 1800:
            break
        time.sleep(0.03)
    print(f"== {title}: 구간 끝 {sec_end:.0f}ms (기본 {p['from_mode']}키, 구간 {p['to_mode']}키)")
    for (t, lane), rows in sorted(track.items()):
        first, last = rows[0], rows[-1]
        modes = sorted({r[1] for r in rows})
        change = next((r for i, r in enumerate(rows[1:], 1) if r[2] != rows[i - 1][2]), None)
        when = f"{(change[0] - sec_end):+.0f}ms(끝 시각 기준)" if change else "변화 없음"
        fall = (t - first[0]) / 1000
        print(f"  노트 끝+{t - sec_end:5.0f}ms lane={lane:2d}: 처음 보인 때 key_mode={first[1]} cx={first[2]} ({fall:.1f}초 전부터 보임) → 마지막 key_mode={last[1]} cx={last[2]}; 배치가 바뀐 때 {when}; 본 key_mode {modes}")
    pb.leave()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--songs", default="CITY POP")
    ap.add_argument("--combo", default="")
    a = ap.parse_args()
    pb.COMBO = tuple(a.combo.split(",")) if a.combo else None
    proc = godot_runner.start_game()
    try:
        for t in a.songs.split(","):
            run(t)
    finally:
        godot_runner.stop_game(proc)


if __name__ == "__main__":
    main()
