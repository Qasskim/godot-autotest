# -*- coding: utf-8 -*-
"""서버 검증 — 전일 1위 조회·라이벌 기록 조회·실패 기록 판별·라이벌 알림 확인·계정 복구(기록 내려받기)·서버 시퀀스 리플레이 (2026-11-10).
기준: LeaderboardService(get_top1·get_rival_best·is_failed_record·check_rival_notices·dismiss_rival_notice), RecordService.sync_down_all_from_server(로그아웃 뒤 재로그인한 계정의
서버 기록을 로컬로 받음), GameManager 리플레이(전일 1위/라이벌의 서버 시퀀스를 판정 그대로 재생, 결과 화면 '리플레이 보기'와 같은 호출).

개발 서버에 그대로 접속하고 고정 테스트 계정 3(나)·4(1위/라이벌)·5로 로그인한다. 시험 기록은 배포 곡 'ARTCORE' 4K EZ 한 곡(pc 플랫폼)에만 만들고 끝에 지운다.
A: Wow(전체-20)·Great15·Good5, B: 전부 Wow(= 1위, MAX). 라이벌 탈퇴 알림은 라이벌이 실계정을 탈퇴해야 생겨서 시험하지 않는다(test_na_user_areas 의 N/A).
이 시험의 판정 구성(A, B)은 test_server_screens 와 같고 시험 작성자가 정했다.
"""
import time
import urllib.parse

import pytest

import client
from screen_helpers import labels, wait_until
from server_helpers import ACCT_A, ACCT_B, ACCT_C, login, mix
from test_server_screens import SONG_ID, submit_pc, total_notes
from test_server_social import account_row, remove_all_rivals

pytestmark = pytest.mark.server

CHART_RES = "res://charts/keysound/artcore_Gmin_174_006/artcore_Gmin_174_006_EZ_v8.rgds"
CHART_ARGS = {"song_id": SONG_ID, "difficulty": "EZ", "platform": "pc"}


@pytest.fixture(scope="module")
def seeded():
    total = total_notes()
    ex_max = total * 3
    a_ex = 3 * (total - 20) + 15 * 2
    login(ACCT_B)
    client.clear_server_records()
    login(ACCT_A)
    client.clear_server_records()
    a_resp = submit_pc(ACCT_A, mix(wow=total - 20, great=15, good=5))
    b_resp = submit_pc(ACCT_B, mix(wow=total))
    login(ACCT_A)
    remove_all_rivals()
    yield {"total": total, "ex_max": ex_max, "a_ex": a_ex, "a_resp": a_resp, "b_resp": b_resp, "a": account_row(ACCT_A), "b": account_row(ACCT_B), "c": account_row(ACCT_C)}
    try:
        if client.scene() == "GameScene":
            if "PAUSED" not in labels():
                client.tap_pause_toggle()
                time.sleep(0.5)
            client.tap_pause_quit()
            client.wait_for_scene("SongSelect", timeout=10)
        login(ACCT_A)
        remove_all_rivals()
        client.clear_server_records()
        login(ACCT_B)
        client.clear_server_records()
        login(ACCT_A)
    except Exception:  # noqa: BLE001 — 정리 실패가 결과를 덮지 않게
        pass


def local_best() -> dict:
    try:
        return client.best(SONG_ID, "EZ", "pc")
    except Exception:  # noqa: BLE001 — 기록이 없으면 404
        return {}


# ── 전일 1위 ──────────────────────────────────────────────────────

def test_top1_is_the_number_one_record_with_name_rate_and_grade(seeded):
    login(ACCT_A)
    top = client.service("top1", **CHART_ARGS)["top1"]
    assert top["rank"] == 1 and top["user_id"] == seeded["b"]["id"] and top["display_name"] == seeded["b"]["name"], top
    assert top["ex_score"] == seeded["ex_max"] and top["grade"] == seeded["b_resp"]["record"]["grade"], top


def test_top1_of_a_chart_without_records_is_empty(seeded):
    login(ACCT_A)
    assert client.service("top1", song_id="keysound_autotest_no_such_song", difficulty="EZ", platform="pc")["top1"] == {}


# ── 실패 기록 판별(게임이 리더보드 줄에 FAILED 를 붙이는 기준) ──────────────

def test_failed_record_detection_by_flag_and_marks():
    assert client.service("is_failed", failed="1")["failed"] is True
    assert client.service("is_failed", marks="clear,failed")["failed"] is True
    assert client.service("is_failed", marks="clear,perfect")["failed"] is False
    assert client.service("is_failed")["failed"] is False


# ── 라이벌 기록 ───────────────────────────────────────────────────

def test_rival_best_returns_the_rivals_record_and_empty_for_nobody(seeded):
    login(ACCT_A)
    remove_all_rivals()
    assert client.service("add_rival", name=seeded["b"]["name"])["ok"]
    rec = client.service("rival_best", user_id=seeded["b"]["id"], **CHART_ARGS)["record"]
    assert rec.get("ex_score") == seeded["ex_max"] and rec.get("grade") == seeded["b_resp"]["record"]["grade"], rec
    nobody = client.service("rival_best", user_id=seeded["c"]["id"], **CHART_ARGS)["record"]
    assert nobody == {}, f"기록이 없는 라이벌인데 기록이 돌아왔습니다: {nobody}"


# ── 라이벌 알림 ───────────────────────────────────────────────────

def test_rival_notices_are_empty_and_dismissing_an_unknown_one_is_harmless(seeded):
    login(ACCT_A)
    assert client.service("notices")["notices"] == []
    assert client.service("dismiss_notice", id="00000000-0000-0000-0000-000000000000")["ok"] is True
    assert client.service("notices")["notices"] == []


# ── 계정 복구: 서버 기록을 로컬로 내려받기 ─────────────────────────────

def test_sync_down_restores_the_servers_records_into_the_empty_local_store(seeded):
    login(ACCT_A)
    client._req("POST", "/debug_clear_records")
    assert local_best() in ({}, {"error": "no record"}) or "ex_score" not in local_best(), f"로컬 기록을 비웠는데 남아 있습니다: {local_best()}"
    assert client.service("sync_down")["ok"] is True, "서버 기록 내려받기가 실패했습니다"
    got = local_best()
    assert got.get("ex_score") == seeded["a_ex"], f"내려받은 로컬 기록이 서버 기록(EX {seeded['a_ex']})과 다릅니다: {got}"


# ── 서버 시퀀스 리플레이(1위 / 라이벌) ───────────────────────────────────

def replay_from_server(extra: dict) -> dict:
    q = {"chart": CHART_RES, "music": "", "key_mode": 4, "replay": 1, **extra}
    client._req("POST", "/debug_goto_gameplay?" + urllib.parse.urlencode(q))
    assert client.wait_for_scene("GameScene", timeout=30), "리플레이 화면이 열리지 않습니다"
    assert wait_until(lambda: "REPLAY" in labels(), timeout=30), f"REPLAY 표시가 없습니다: {labels()}"
    assert client.wait_for_scene("ResultScreen", timeout=900), "리플레이 결과 화면이 안 나옵니다"
    time.sleep(2.0)
    return client.result()


def test_top1_replay_plays_the_number_one_judgments_exactly(seeded):
    login(ACCT_A)
    r = replay_from_server({"ghost": "top1"})
    assert r["wow"] == seeded["total"] and r["great"] == r["good"] == r["oops"] == r["miss"] == 0, f"1위(전부 Wow) 리플레이의 판정이 다릅니다: {r}"
    assert r["score"] == seeded["ex_max"] and r["grade"] == seeded["b_resp"]["record"]["grade"], r
    assert r["is_best"] is False, "리플레이가 기록을 저장했습니다"


def test_rival_replay_plays_the_registered_rivals_judgments(seeded):
    login(ACCT_A)
    remove_all_rivals()
    assert client.service("add_rival", name=seeded["b"]["name"])["ok"]
    r = replay_from_server({"ghost": "rival", "rival_user_id": seeded["b"]["id"]})
    assert r["wow"] == seeded["total"] and r["miss"] == 0 and r["score"] == seeded["ex_max"], f"라이벌(전부 Wow) 리플레이의 판정이 다릅니다: {r}"
    assert r["is_best"] is False
