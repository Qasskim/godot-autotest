# -*- coding: utf-8 -*-
"""튜토리얼 4단계(레인믹스 순차 체험)에서 노트가 구간 끝·단계 시각에 배치가 튀는지 재는 도구 (pytest 아님 — 직접 실행). 2026-11-10.
  python probe_tutorial_layout.py
노트마다 (처음 보인 key_mode·cx → 마지막 key_mode·cx)를 기록한다. 안내 버튼이 나오면 눌러 수락한다.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client  # noqa: E402
import godot_runner  # noqa: E402
from screen_helpers import enter_tutorial_via_settings, jump_to_stage, press  # noqa: E402

CHART_END_MS = 17500      # stage4 채보의 마지막 노트(16500) 뒤


def main():
    proc = godot_runner.start_game()
    try:
        enter_tutorial_via_settings()
        jump_to_stage(3, 1)
        press("START")
        track = {}
        clicked = False
        t_end = time.time() + 60
        while time.time() < t_end:
            st = client._req("GET", "/tutorial_practice_state")
            now = st.get("position_ms", 0)
            if not clicked and st.get("prompt_state") in ("OFFER", "READY"):
                client.click(st["button_x"], st["button_y"])
                clicked = True
            for n in st.get("notes", []):
                track.setdefault((round(n["timing_ms"], 1), n["lane"]), []).append((now, n["key_mode"], n["cx"]))
            if st.get("finished") or now > CHART_END_MS:
                break
            time.sleep(0.03)
        print(f"수락 클릭: {clicked}")
        for (t, lane), rows in sorted(track.items()):
            first, last = rows[0], rows[-1]
            changes = [(rows[i][0], rows[i - 1][1], rows[i][1]) for i in range(1, len(rows)) if rows[i][2] != rows[i - 1][2]]
            ch = ", ".join(f"{m:.0f}ms에 {a}키→{b}키" for m, a, b in changes) or "변화 없음"
            print(f"  노트 {t:7.0f}ms lane={lane:2d}: 처음 {first[1]}키 cx={first[2]} ({(t - first[0]) / 1000:.1f}초 전부터) → 마지막 {last[1]}키 cx={last[2]}; {ch}")
    finally:
        godot_runner.stop_game(proc)


if __name__ == "__main__":
    main()
