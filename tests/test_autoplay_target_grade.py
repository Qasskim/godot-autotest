# -*- coding: utf-8 -*-
"""디버그 자동 플레이의 목표 등급 모드 — 모든 노트를 쳐서 콤보가 안 끊기고(Miss·Oops 0), 결과 등급이 목표와 같다 (2026-11-09).

원인: 예전엔 목표 등급 커트라인만큼만 Wow 로 치고 나머지 노트를 일부러 안 쳐서 Miss 가 났다(A 등급인데 풀콤보가 안 나옴 → 사용자가 버그로 지정).
곡은 실행마다 무작위로 고르고, 쓴 곡과 seed 를 실패 메시지에 남긴다. 같은 곡으로 다시 돌리려면 환경변수 AUTOTEST_SEED 를 준다.
서버·계정은 쓰지 않는다(--no-server).
"""
import os
import random
import time

import pytest

import client
from screen_helpers import press, wait_until

SEED = int(os.environ.get("AUTOTEST_SEED", str(int(time.time()))))
TARGETS = ["S++", "S+", "S", "A", "B", "C", "D"]


@pytest.mark.parametrize("target", TARGETS)
def test_target_grade_autoplay_hits_every_note_without_breaking_combo(target):
    rng = random.Random(f"{SEED}-{target}")
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    titles = client.songs()["songs"]
    title = rng.choice(titles)
    where = f"(seed={SEED}, 곡={title}, 목표={target})"
    client.tap_song_at(titles.index(title))
    time.sleep(0.5)
    client.autoplay(True)
    try:
        client.tap_songselect_debug_open()
        time.sleep(0.3)
        press(target)
        time.sleep(0.2)
        client.tap_songselect_debug_close()
        time.sleep(0.3)
        press("PLAY")
        assert client.wait_for_scene("ResultScreen", timeout=900), f"결과 화면이 안 나옵니다 {where}"
        time.sleep(2.0)
        r = client.result()
    finally:
        client.autoplay(False)
    hits = r["wow"] + r["great"] + r["good"]
    assert r["miss"] == 0 and r["oops"] == 0, f"Miss/Oops 가 있습니다: {r} {where}"
    assert r["max_combo"] >= hits, f"콤보가 끊겼습니다(최대 콤보 {r['max_combo']} < 친 노트 {hits}): {r} {where}"
    assert r["grade"] == target, f"결과 등급이 목표 {target} 가 아닙니다({r['grade']}, 달성률 {r['accuracy']}): {r} {where}"
