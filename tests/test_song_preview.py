# -*- coding: utf-8 -*-
"""곡 미리듣기 재생 — 곡을 고르면 preview/preview.ogg 를 1번 재생하고 곡 선택 BGM 은 줄었다가(ducking) 끝나면 돌아온다 (기준 DESIGN §13-3 "곡 미리듣기",
SongSelect._play_song_preview, BgmPlayer.play_preview, 2026-11-10).

TestServer /bgm 이 지금 재생 중인 재생기(스트림 이름·음량 dB·재생 위치)와 현재 곡(track)을 돌려준다. 소리가 실제로 들리는지는 사람이 확인한다.
확인하는 것: (1) 곡 선택 화면에 들어오면 곡 선택 BGM(bgm_free)이 재생된다 (2) 곡을 고르면 재생기가 하나 더 켜지고(미리듣기) 그 위치가 앞으로 간다
(3) 그동안 곡 선택 BGM 은 평소 음량보다 줄어 있다 (4) 미리듣기 길이가 지나면 재생기가 다시 하나가 되고 곡 선택 BGM 음량이 평소로 돌아온다.
이 시험의 값(곡 SYNTHWAVE, 대기 시간)은 시험 작성자가 정했다. 서버·계정은 쓰지 않는다(--no-server).
"""
import time

import client
from screen_helpers import wait_until

SONG = "SYNTHWAVE"
PREVIEW_START_WAIT = 4.0
PREVIEW_LENGTH_PAD = 8.0


def bgm() -> dict:
    return client._req("GET", "/bgm")


def preview_seconds() -> float:
    """곡 폴더 preview/preview.ogg 의 길이(초) — Ogg 마지막 페이지의 granule 위치 ÷ 샘플레이트."""
    import glob
    import os
    import struct
    from godot_runner import GAME_PROJECT
    path = glob.glob(os.path.join(GAME_PROJECT, "charts", "keysound", "synthwave_*", "preview", "preview.ogg"))[0]
    data = open(path, "rb").read()
    i = data.find(b"\x01vorbis")
    rate = struct.unpack("<I", data[i + 12:i + 16])[0]
    last = data.rfind(b"OggS")
    return struct.unpack("<q", data[last + 6:last + 14])[0] / rate


def test_choosing_a_song_plays_preview_once_then_bgm_returns():
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.5)
    base = bgm()
    assert any(p["stream"] == "bgm_free.ogg" for p in base["playing"]), f"곡 선택 BGM(bgm_free)이 재생 중이 아닙니다: {base}"
    normal_db = next(p["volume_db"] for p in base["playing"] if p["stream"] == "bgm_free.ogg")

    client.tap_song_at(client.songs()["songs"].index(SONG))
    assert wait_until(lambda: len(bgm()["playing"]) >= 2, timeout=PREVIEW_START_WAIT), f"곡을 골랐는데 미리듣기 재생기가 켜지지 않습니다: {bgm()}"
    first = bgm()
    prev = next(p for p in first["playing"] if p["stream"] != "bgm_free.ogg")
    duck = next(p for p in first["playing"] if p["stream"] == "bgm_free.ogg")
    time.sleep(1.5)
    second = bgm()
    prev2 = next(p for p in second["playing"] if p["stream"] != "bgm_free.ogg")
    assert prev2["pos"] > prev["pos"], f"미리듣기 재생 위치가 앞으로 가지 않습니다: {prev} → {prev2}"
    duck2 = next(p for p in second["playing"] if p["stream"] == "bgm_free.ogg")
    assert duck2["volume_db"] < normal_db - 1.0, f"미리듣기 동안 곡 선택 BGM 이 줄어들지 않았습니다: 평소 {normal_db}dB, 지금 {duck2['volume_db']}dB (처음 {duck['volume_db']})"

    length = preview_seconds()
    assert wait_until(lambda: len(bgm()["playing"]) == 1, timeout=length + PREVIEW_LENGTH_PAD), f"미리듣기가 끝나도 재생기가 하나로 돌아오지 않습니다: {bgm()}"
    assert wait_until(lambda: abs(next(p["volume_db"] for p in bgm()["playing"] if p["stream"] == "bgm_free.ogg") - normal_db) < 1.0, timeout=5), f"미리듣기 뒤 곡 선택 BGM 음량이 평소({normal_db}dB)로 돌아오지 않습니다: {bgm()}"
    time.sleep(2.0)
    assert len(bgm()["playing"]) == 1, "미리듣기가 한 번 끝난 뒤 다시 재생됐습니다(1번만 재생해야 함)"
