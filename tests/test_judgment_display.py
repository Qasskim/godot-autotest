# -*- coding: utf-8 -*-
"""입력을 넣었을 때 판정 글자(WOW·GREAT·GOOD·OOPS·MISS)가 플레이 화면에 뜨는지 (2026-11-09).

곡은 실행마다 무작위로 고르고(곡 선택 목록 전체에서), 쓴 곡과 seed 를 실패 메시지에 남긴다. 같은 곡으로 다시 돌리려면 환경변수 AUTOTEST_SEED.
자동 플레이는 끄고, TestServer /debug_judge_note 가 곡 시계로 '노트 시각 + 오프셋' 에 그 레인을 터치한다(HTTP 지연과 무관).
오프셋은 판정 창 안의 한가운데쯤 — WOW ≤32ms / GREAT ≤70 / GOOD ≤170 / OOPS ≤250 (게임 설계 §5). 프레임 한두 개 늦게 처리돼도 같은 등급에 들도록 잡았고,
그래도 밀리면 다음 노트로 최대 3번까지 다시 한다(몇 번째에 성공했는지 실패 메시지에 남김). Miss 는 안 치고 지나가게 둔다.
서버·계정은 쓰지 않는다(--no-server).
"""
import os
import random
import time

import pytest

import client
from screen_helpers import labels, press, wait_until

SEED = int(os.environ.get("AUTOTEST_SEED", str(int(time.time()))))
# (글자, 서버가 돌려주는 등급, 노트 시각에서 더할 ms, 칠지 여부)
CASES = [
    ("WOW", "Wow", 0, True),
    ("GREAT", "Great", 36, True),
    ("GOOD", "Good", 80, True),
    ("OOPS", "Oops", 180, True),
    ("MISS", "Miss", 0, False),
]
ATTEMPTS = 3


@pytest.fixture(autouse=True)
def _leave_after():
    yield
    if client.scene() == "GameScene":
        if "PAUSED" not in labels():
            client.tap_pause_toggle()
            time.sleep(0.5)
        client.tap_pause_quit()
        client.wait_for_scene("SongSelect", timeout=10)
    client.autoplay(False)


def start_random_song() -> str:
    rng = random.Random(SEED)
    client.autoplay(False)
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    titles = client.songs()["songs"]
    title = rng.choice(titles)
    client.tap_song_at(titles.index(title))
    time.sleep(0.5)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30), f"플레이 화면이 안 열립니다 (seed={SEED}, 곡={title})"
    assert wait_until(lambda: not any(l in ("3", "2", "1") for l in labels()), timeout=15), "시작 카운트다운이 안 끝납니다"
    return title


def try_once(word: str, grade: str, offset: float, hit: bool) -> dict:
    """노트 하나에 입력을 넣고 (게임이 낸 등급, 그 직후 화면의 판정 글자)를 돌려준다."""
    client.judge_note(offset, hit)
    deadline = time.time() + 40
    st = {}
    while time.time() < deadline:
        st = client.judge_note_state()
        if st.get("state") == "done":
            break
        if client.scene() != "GameScene":
            return {"grade": None, "on_screen": False, "state": st, "why": f"플레이 화면이 아닙니다({client.scene()})"}
        time.sleep(0.02)
    on_screen = False
    t0 = time.time()
    while time.time() - t0 < 0.5:
        if word in labels():
            on_screen = True
            break
        time.sleep(0.03)
    return {"grade": st.get("grade"), "on_screen": on_screen, "state": st}


def test_each_judgment_word_appears_on_screen_after_matching_input():
    title = start_random_song()
    where = f"(seed={SEED}, 곡={title})"
    summary = []
    for word, grade, offset, hit in CASES:
        tries = []
        for attempt in range(1, ATTEMPTS + 1):
            r = try_once(word, grade, offset, hit)
            tries.append(r)
            if r["grade"] == grade and r["on_screen"]:
                summary.append(f"{word}: {attempt}번째에 성공(오차 {r['state'].get('error_ms')})")
                break
        else:
            pytest.fail(f"{word} 가 {ATTEMPTS}번 시도에도 안 나옵니다 {where}: {tries} 앞서 성공한 것: {summary}")
    print("\n".join(summary), where)
