# -*- coding: utf-8 -*-
"""화면 뒤집힘 감지 → 자동 일시정지 논리 (GameManager._check_orientation_flip, 기준 DESIGN §2 "플레이 중 뒤집힘 대응", 2026-11-10).

규칙(코드 주석·DESIGN): 중력 센서의 위아래 축 값이 부호가 바뀌면 뒤집힌 것으로 보고 플레이 중이면 자동 일시정지(포즈) 한다.
절대값 5.0 미만은 전환 중의 애매한 값이라 무시, 처음 읽은 부호는 기준만 잡고 일시정지하지 않음, 같은 부호가 이어지면 아무 일 없음,
이미 일시정지 중이거나 카운트다운 중에는 다시 뒤집혀도 포즈를 쌓지 않음.
PC 에는 센서가 없고 이 감지는 Android 에서만 매 프레임 도므로, TestServer /debug_gravity 가 센서 값을 넣고 감지 함수를 한 번 돌린다(Android 에서만 도는 조건 자체는 폰 확인).
이 시험의 센서 값(±9.0, 중간값 2.0)은 시험 작성자가 정했다. 서버·계정은 쓰지 않는다(--no-server).
"""
import time

import pytest

import client
from screen_helpers import labels, press, wait_until

SONG = "SYNTHWAVE"


def gravity(y: float) -> None:
    client._req("POST", f"/debug_gravity?y={y}")
    time.sleep(0.4)


def play_state() -> dict:
    return client._req("GET", "/debug_play_state")


@pytest.fixture
def playing():
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    client.tap_song_at(client.songs()["songs"].index(SONG))
    time.sleep(0.5)
    client.autoplay(True)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30)
    assert wait_until(lambda: "AUTO" in labels() and not any(l in ("3", "2", "1") for l in labels()), timeout=20)
    yield
    gravity(0.0)
    if client.scene() == "GameScene":
        if "PAUSED" not in labels():
            client.tap_pause_toggle()
            time.sleep(0.5)
        client.tap_pause_quit()
        client.wait_for_scene("SongSelect", timeout=10)


def test_first_reading_only_sets_the_reference_and_same_sign_does_nothing(playing):
    gravity(9.0)
    assert play_state()["paused"] is False, "처음 읽은 센서 값에서 일시정지됐습니다(기준만 잡아야 함)"
    gravity(8.0)
    assert play_state()["paused"] is False, "같은 부호가 이어지는데 일시정지됐습니다"


def test_small_readings_during_a_turn_are_ignored(playing):
    gravity(9.0)
    gravity(2.0)
    gravity(-2.0)
    assert play_state()["paused"] is False, "절대값 5 미만의 애매한 값에서 일시정지됐습니다"
    gravity(9.0)
    assert play_state()["paused"] is False, "애매한 값을 건너 같은 부호로 돌아왔는데 일시정지됐습니다"


def test_sign_flip_pauses_the_game(playing):
    gravity(9.0)
    gravity(-9.0)
    assert wait_until(lambda: play_state()["paused"] is True, timeout=5), "부호가 뒤집혔는데 일시정지되지 않았습니다"
    assert "PAUSED" in labels(), f"일시정지 창이 안 보입니다: {labels()}"


def test_another_flip_while_paused_does_not_stack_or_resume(playing):
    gravity(9.0)
    gravity(-9.0)
    assert wait_until(lambda: play_state()["paused"] is True, timeout=5)
    gravity(9.0)
    st = play_state()
    assert st["paused"] is True and st["counting_down"] is False, f"이미 일시정지 중인데 다시 뒤집히자 상태가 바뀌었습니다: {st}"
    assert "PAUSED" in labels()
