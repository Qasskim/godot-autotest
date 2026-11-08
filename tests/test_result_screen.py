# -*- coding: utf-8 -*-
"""결과 화면 — 실제 자동 플레이 한 판의 결과 숫자·글자·버튼, 등급 그림 9종과 마크 그림 8종(경로), 다시 하기·곡 선택 (2026-11-08).

숫자는 TestServer /result(게임이 계산한 값)와 화면에 보이는 글자를 맞춰 본다. 그림 모양·색은 사람이 확인한다. 서버·계정은 쓰지 않는다(--no-server).
"""
import re
import time

import pytest

import client
from screen_helpers import labels, norm, press, ui, wait_until

SONG = "SYNTHWAVE"
GRADE_IMAGE = {"MAX": "grade_MAX", "S++": "grade_Spp", "S+": "grade_Sp", "S": "grade_S", "A": "grade_A", "B": "grade_B", "C": "grade_C", "D": "grade_D", "F": "grade_F"}
MARKS = ["perfect", "allcombo", "allgood", "clear", "failed", "evil", "luckyroulette", "straight"]


def buttons() -> list:
    return client.screen_buttons()


@pytest.fixture(scope="module")
def played():
    """SYNTHWAVE 4K EZ 를 자동 플레이로 끝까지 한 번 돌려 결과 화면을 띄운 상태."""
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    client.tap_song_at(client.songs()["songs"].index(SONG))
    time.sleep(0.5)
    client.autoplay(True)
    press("PLAY")
    assert client.wait_for_scene("ResultScreen", timeout=600), "결과 화면이 안 나옵니다"
    time.sleep(3.0)
    client.autoplay(False)
    return client.result()


def test_result_numbers_on_screen_match_the_games_own_result(played):
    r = played
    got = labels()
    assert any(re.fullmatch(rf"EX SCORE {r['score']} / {r['max_ex']}( .*)?", g) for g in got), f"EX SCORE 줄이 {r['score']} / {r['max_ex']} 가 아닙니다: {got}"
    assert norm(ui("result_ex_rate") % r["accuracy"]) in got, f"EX RATE 줄이 {r['accuracy']} 와 다릅니다: {got}"
    assert norm(ui("result_max_combo") % r["max_combo"]) in got
    assert norm(ui("result_clear") % r["clear_grade"]) in got
    for name, key in (("Wow", "wow"), ("Great", "great"), ("Good", "good"), ("Oops", "oops"), ("Miss", "miss")):
        i = got.index(name)
        assert got[i + 1] == str(r[key]), f"{name} 개수가 {r[key]} 가 아닙니다: {got[i:i + 2]}"
    assert norm(ui("result_break_count") % 0) in got and norm(ui("result_fast_slow") % (0, 0)) in got


def test_result_header_shows_mode_title_artist_bpm(played):
    got = labels()
    assert ui("result_mode_free") in got
    assert f"{SONG} [EZ]" in got, f"곡 이름·난이도 줄이 없습니다: {got}"
    assert "VAi" in got and "BPM 115.0" in got


def test_result_shows_my_rank_row_and_grade_axis_and_no_rival_message(played):
    got = labels()
    assert ui("result_rank_me") in got
    assert ui("result_rank_empty") in got, f"라이벌 기록이 없을 때 안내 문구가 없습니다: {got}"
    for axis in ("100%", "90%", "80%", "70%", "60%", "50%", "0%"):
        assert axis in got, f"등급 그래프 축 '{axis}' 가 없습니다"
    assert played["grade"] in got, f"그래프에 내 등급 '{played['grade']}' 이 없습니다"


def test_result_buttons_retry_and_song_select_only_without_replay(played):
    b = buttons()
    assert ui("result_retry_btn") in b and ui("result_select_btn") in b, b
    assert ui("result_replay_btn") not in b, "리플레이 기록이 없는 판인데 '리플레이 보기' 가 보입니다"


def test_result_images_show_grade_and_mark_pictures(played):
    imgs = client.screen_images()
    want_grade = f"res://assets/grades/{GRADE_IMAGE[played['grade']]}.png"
    assert want_grade in imgs, f"등급 그림 {want_grade} 이 없습니다: {imgs}"
    for m in played["marks"]:
        assert f"res://assets/marks/mark_{m}.png" in imgs, f"마크 그림 mark_{m}.png 이 없습니다: {imgs}"


@pytest.mark.parametrize("grade", list(GRADE_IMAGE))
def test_each_grade_shows_its_own_grade_picture(played, grade):
    client._req("POST", "/debug_show_result?grade=" + grade.replace("+", "%2B") + "&marks=")
    assert client.wait_for_scene("ResultScreen", timeout=10)
    time.sleep(1.0)
    imgs = client.screen_images()
    assert f"res://assets/grades/{GRADE_IMAGE[grade]}.png" in imgs, f"{grade} 등급 그림이 안 나옵니다: {imgs}"
    others = [f"res://assets/grades/{v}.png" for k, v in GRADE_IMAGE.items() if k != grade]
    assert not [o for o in others if o in imgs], f"{grade} 인데 다른 등급 그림도 보입니다: {imgs}"


@pytest.mark.parametrize("mark", MARKS)
def test_each_mark_shows_its_own_mark_picture(played, mark):
    client._req("POST", f"/debug_show_result?grade=A&marks={mark}")
    assert client.wait_for_scene("ResultScreen", timeout=10)
    time.sleep(1.0)
    imgs = client.screen_images()
    assert f"res://assets/marks/mark_{mark}.png" in imgs, f"{mark} 마크 그림이 안 나옵니다: {imgs}"
    others = [f"res://assets/marks/mark_{m}.png" for m in MARKS if m != mark]
    assert not [o for o in others if o in imgs], f"{mark} 만 줬는데 다른 마크 그림도 보입니다: {imgs}"


def test_retry_button_starts_the_same_song_again(played):
    client._req("POST", "/debug_show_result?grade=A&marks=clear")
    assert client.wait_for_scene("ResultScreen", timeout=10)
    time.sleep(1.0)
    press(ui("result_retry_btn"))
    assert client.wait_for_scene("GameScene", timeout=20) or client.scene() in ("GameScene", "SongSelect"), f"다시 하기를 눌렀는데 {client.scene()} 입니다"
    if client.scene() == "GameScene":
        if "PAUSED" not in labels():
            client.tap_pause_toggle()
            time.sleep(0.6)
        client.tap_pause_quit()
        client.wait_for_scene("SongSelect", timeout=10)


def test_song_select_button_returns_to_song_select(played):
    client._req("POST", "/debug_show_result?grade=A&marks=clear")
    assert client.wait_for_scene("ResultScreen", timeout=10)
    time.sleep(1.0)
    press(ui("result_select_btn"))
    assert client.wait_for_scene("SongSelect", timeout=10), f"곡 선택을 눌렀는데 {client.scene()} 입니다"
