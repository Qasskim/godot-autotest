# -*- coding: utf-8 -*-
"""플레이 중 레인믹스 안내 — 구간 전에 'TAP' 버튼(OFFER)이 뜨고, 누르면 READY → 3·2·1 → 키 수가 바뀌고, 끝날 때 3·2·1(RETURN) 뒤 원래 키 수로 돌아온다. 안 누르면 그대로 (2026-11-09).

곡은 실행마다 무작위로 고르고(EZ 4K 에 레인믹스 구간이 있는 수록곡 17곡 전부가 대상), 쓴 곡과 seed 를 실패 메시지에 남긴다. 같은 곡으로 다시 돌리려면 AUTOTEST_SEED.
자동 플레이는 켜고 '자동 레인믹스 수락'은 끈다(사람이 TAP 을 눌러야 하는 상태). 버튼은 TestServer /debug_lanemix_prompt 가 알려 주는 화면 좌표를 /debug_click 으로 누른다.
서버·계정은 쓰지 않는다(--no-server).
"""
import os
import random
import time

import pytest

import client
from screen_helpers import labels, press, wait_until

SEED = int(os.environ.get("AUTOTEST_SEED", str(int(time.time()))))


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
    client.autolanemix(True)


def start_random_song(offset: int) -> str:
    rng = random.Random(SEED + offset)
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    titles = client.songs()["songs"]
    title = rng.choice(titles)
    client.tap_song_at(titles.index(title))
    time.sleep(0.5)
    client.autoplay(True)
    client.autolanemix(False)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30), f"플레이 화면이 안 열립니다 (seed={SEED}, 곡={title})"
    return title


def wait_state(want: str, timeout: float) -> dict:
    """안내 상태가 want 가 될 때까지 기다려 그 순간의 상태를 돌려준다. 못 되면 마지막 상태로 AssertionError."""
    deadline = time.time() + timeout
    p = client.lanemix_prompt()
    while time.time() < deadline:
        p = client.lanemix_prompt()
        if p["state"] == want:
            return p
        time.sleep(0.05)
    raise AssertionError(f"안내 상태가 {timeout:.0f}초 안에 {want} 가 되지 않았습니다 — 마지막: {p}")


def counts_until_hidden(timeout: float) -> list:
    """안내가 사라질 때까지 보인 카운트다운 숫자(중복 없이 나온 순서)."""
    seen = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        p = client.lanemix_prompt()
        if p["count"] > 0 and p["count"] not in seen:
            seen.append(p["count"])
        if p["state"] == "HIDDEN":
            return seen
        time.sleep(0.03)
    raise AssertionError(f"안내가 {timeout:.0f}초 안에 사라지지 않았습니다 — 본 숫자: {seen}, 마지막: {client.lanemix_prompt()}")


def test_accepting_offer_counts_down_switches_key_mode_and_returns():
    title = start_random_song(0)
    where = f"(seed={SEED}, 곡={title})"
    offer = wait_state("OFFER", timeout=150)
    base, target = offer["from_mode"], offer["to_mode"]
    assert offer["key_mode"] == base, f"안내가 뜬 순간 키 수가 시작 키 수가 아닙니다: {offer} {where}"
    assert target > 0 and target != base, f"전환 목표 키 수가 이상합니다: {offer} {where}"
    client.click(offer["button_x"], offer["button_y"])
    ready = wait_state("READY", timeout=3)
    assert ready["to_mode"] == target, f"수락했는데 목표 키 수가 달라졌습니다: {ready} {where}"
    start_counts = counts_until_hidden(60)
    assert start_counts == [3, 2, 1], f"시작 카운트다운이 3 → 2 → 1 이 아닙니다: {start_counts} {where}"
    assert client.lanemix_prompt()["key_mode"] == target, f"시작 카운트다운이 끝났는데 키 수가 {target} 로 안 바뀌었습니다: {client.lanemix_prompt()} {where}"
    ret = wait_state("RETURN", timeout=150)
    assert ret["key_mode"] == target, f"끝나기 전에는 목표 키 수를 유지해야 합니다: {ret} {where}"
    return_counts = counts_until_hidden(60)
    assert return_counts == [3, 2, 1], f"원복 카운트다운이 3 → 2 → 1 이 아닙니다: {return_counts} {where}"
    assert wait_until(lambda: client.lanemix_prompt()["key_mode"] == base, timeout=5), f"원복 뒤 키 수가 {base} 로 안 돌아왔습니다: {client.lanemix_prompt()} {where}"


def test_ignoring_offer_keeps_base_key_mode_and_hides_prompt():
    title = start_random_song(1)
    where = f"(seed={SEED}, 곡={title})"
    offer = wait_state("OFFER", timeout=150)
    base = offer["from_mode"]
    assert wait_until(lambda: client.lanemix_prompt()["state"] == "HIDDEN", timeout=60, interval=0.1), f"안 눌렀는데 안내가 사라지지 않습니다: {client.lanemix_prompt()} {where}"
    time.sleep(1.0)
    after = client.lanemix_prompt()
    assert after["state"] == "HIDDEN" and after["key_mode"] == base, f"안 눌렀는데 키 수가 바뀌었거나 READY/RETURN 이 떴습니다: {after} {where}"
