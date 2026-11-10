# -*- coding: utf-8 -*-
"""리플레이에서 처음 판에 없던 Miss 1개가 어느 노트인지 찾는 도구 (pytest 아님 — 직접 실행). 2026-11-10.
  python probe_replay_miss.py
목표 B 자동 플레이로 한 판 치면서 그 판의 모든 판정(레인·곡 시각)을 /debug_judgment_log 로 기록하고, 같은 판을 리플레이로 다시 열어 같은 방식으로 기록한 뒤
두 기록을 레인별로 나란히 놓고 달라지는 첫 곳을 출력한다. (판정 기록은 예약 입력이 걸려 있어야 켜지므로 절대 닿지 않을 먼 시각의 입력 하나를 예약한다.)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client  # noqa: E402
import godot_runner  # noqa: E402
from screen_helpers import press, wait_until  # noqa: E402

SONG = "SYNTHWAVE"


def attach_log() -> None:
    client._req("POST", "/debug_press_plan?plan=99999999:0")


def main():
    proc = godot_runner.start_game()
    try:
        client.clear_local_records()
        client.navigate("song_select")
        assert client.wait_for_scene("SongSelect", timeout=15)
        assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
        time.sleep(1.2)
        client.tap_song_at(client.songs()["songs"].index(SONG))
        time.sleep(0.5)
        client.autoplay(True)
        client.tap_songselect_debug_open()
        time.sleep(0.3)
        press("B")
        time.sleep(0.2)
        client.tap_songselect_debug_close()
        time.sleep(0.3)
        press("PLAY")
        assert client.wait_for_scene("GameScene", timeout=30)
        attach_log()
        assert client.wait_for_scene("ResultScreen", timeout=900)
        first_log = client._req("GET", "/debug_judgment_log")["judgments"]
        client.autoplay(False)
        time.sleep(2.0)
        client.replay_last()
        assert client.wait_for_scene("GameScene", timeout=30)
        attach_log()
        assert client.wait_for_scene("ResultScreen", timeout=900)
        replay_log = client._req("GET", "/debug_judgment_log")["judgments"]
        print("처음 판 판정 수", len(first_log), "/ 리플레이 판정 수", len(replay_log))
        n = min(len(first_log), len(replay_log))
        shown = 0
        for i in range(n):
            a, b = first_log[i], replay_log[i]
            if a["grade"] != b["grade"] or a["lane"] != b["lane"] or abs(a["music_ms"] - b["music_ms"]) > 400:
                print(f"  #{i}: 처음 {a['grade']} lane={a['lane']} t={a['music_ms']} / 리플레이 {b['grade']} lane={b['lane']} t={b['music_ms']}")
                shown += 1
                if shown >= 6:
                    break
        print("처음 판 마지막 3개:", first_log[-3:])
        print("리플레이 마지막 3개:", replay_log[-3:])
    finally:
        godot_runner.stop_game(proc)


if __name__ == "__main__":
    main()
