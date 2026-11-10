# -*- coding: utf-8 -*-
"""리플레이 재생 — 저장된 판정을 그대로 재현하는지 (기준 DESIGN §14 "1위 리플레이 감상", GameManager._process_replay, 2026-11-10).

목표 등급 B 자동 플레이(Wow·Great·Good 가 섞임)로 SYNTHWAVE 4K EZ 를 한 판 끝까지 치고 로컬 기록(판정 시퀀스)을 남긴 뒤,
같은 판을 리플레이로 열어(리플레이는 저장된 최고 기록의 시퀀스를 재생하므로 시작 전에 로컬 기록을 비운다) 끝까지 재생하고 결과를 비교한다: 점수·판정 개수·최대 콤보·등급이 처음 판과 같아야 하고, 리플레이는 기록을 다시 저장하지 않는다(is_best 아님).
결과 화면의 '리플레이 보기' 버튼은 서버 원격 설정이 켜져야 보이므로(--no-server 에서는 항상 꺼짐) 같은 호출을 TestServer /debug_replay_last 로 부른다.
버튼 표시 조건 자체는 서버 시험(test_server_screens)이 본다. 서버·계정은 쓰지 않는다(--no-server). 이 시험의 값(곡 SYNTHWAVE, 목표 B)은 시험 작성자가 정했다.
"""
import time

import client
from screen_helpers import labels, press, wait_until

SONG = "SYNTHWAVE"
KEYS = ("score", "max_ex", "wow", "great", "good", "oops", "miss", "max_combo", "grade", "clear_grade")


def play_with_target_b() -> dict:
    client.clear_local_records()      # 앞 시험이 남긴 더 높은 기록이 있으면 이 판이 최고 기록이 못 돼 리플레이가 그 기록을 재생한다(첫 실행에서 확인)
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    client.tap_song_at(client.songs()["songs"].index(SONG))
    time.sleep(0.5)
    client.autoplay(True)
    try:
        client.tap_songselect_debug_open()
        time.sleep(0.3)
        press("B")
        time.sleep(0.2)
        client.tap_songselect_debug_close()
        time.sleep(0.3)
        press("PLAY")
        assert client.wait_for_scene("ResultScreen", timeout=900), "첫 판 결과 화면이 안 나옵니다"
        time.sleep(2.0)
        return client.result()
    finally:
        client.autoplay(False)


# 2026-11-10 시험이 결함을 찾았고 같은 날 고쳤다(사용자 선택 가): 레인믹스 구간 시작 시각에 기본 레이어 노트가 있으면 리플레이가 그 노트에 기록 하나를 먼저 쓰고
# 같은 프레임의 구간 시작이 그 노트를 치워 이후 기록이 한 칸씩 밀렸다(수정 전: 판정 139개 vs 처음 판 138개, 마지막 롱 머리 Miss 1개 추가).
# 수정: GameManager._process 에서 리플레이 판정 적용을 레인믹스 이벤트 처리 뒤로 옮김. 측정 도구: probe_replay_miss.py.
def test_replay_reproduces_the_recorded_judgments_and_does_not_save_again():
    first = play_with_target_b()
    assert first["wow"] > 0 and first["great"] + first["good"] > 0, f"판정이 섞이지 않은 판은 리플레이 비교가 약하다: {first}"
    client.replay_last()
    assert client.wait_for_scene("GameScene", timeout=30), "리플레이가 시작되지 않습니다"
    assert wait_until(lambda: "REPLAY" in labels(), timeout=20), f"리플레이 표시(REPLAY)가 없습니다: {labels()}"
    assert client.wait_for_scene("ResultScreen", timeout=900), "리플레이 결과 화면이 안 나옵니다"
    time.sleep(2.0)
    second = client.result()
    diff = {k: (first[k], second[k]) for k in KEYS if first[k] != second[k]}
    assert not diff, f"리플레이 결과가 처음 판과 다릅니다(처음, 리플레이): {diff}"
    assert second["is_best"] is False, "리플레이가 기록을 다시 저장했습니다(is_best)"
