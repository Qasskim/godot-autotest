# -*- coding: utf-8 -*-
"""서버 검증 — 라이벌 등록·해제·제한, 클라이언트 리더보드 조회, 고스트 시퀀스 접근 권한 (기준 LEADERBOARD.md §4, supabase_records_schema.sql RLS).

게임 안의 LeaderboardService 함수를 TestServer /debug_service 로 호출한다(개발 서버에 그대로 접속, 고정 테스트 계정 3·4·5로 로그인).
라이벌에 등록되는 상대 계정은 test2·test6·test7·test@ 의 닉네임을 서버에서 읽어 쓴다(그 계정으로 로그인하지는 않는다).
라이벌 행은 등록한 쪽(3번) 소유라 시험 후 cleanup_server.py(장부)로 지워진다.
"""
import pytest

import client
from server_helpers import CH_8K, PLATFORM, ACCT_A, ACCT_B, ACCT_C, login, mix, payload, submit, db

pytestmark = pytest.mark.server


def account_row(n: int) -> dict:
    """고정 테스트 계정 N(이메일 test@·test2@…)의 user_id 와 서버 닉네임."""
    email = "test@rhythmgame.com" if n == 1 else f"test{n}@rhythmgame.com"
    rows = db(f"select u.id, p.display_name from auth.users u join public.users p on p.user_id = u.id where u.email = '{email}'")
    assert rows, f"{email} 의 서버 닉네임이 없습니다"
    return {"id": rows[0]["id"], "name": rows[0]["display_name"]}


def remove_all_rivals() -> None:
    for r in client.service("rivals")["rivals"]:
        assert client.service("remove_rival", id=r["rival_user_id"])["ok"]


# ── 라이벌 ──────────────────────────────────────────────────────────

def test_rival_add_list_remove():
    login(ACCT_A)
    remove_all_rivals()
    b = account_row(ACCT_B)
    try:
        added = client.service("add_rival", name=b["name"])
        assert added["ok"] and added["rival"]["rival_user_id"] == b["id"] and added["rival"]["display_name"] == b["name"], added
        again = client.service("add_rival", name=b["name"])                      # 이미 등록된 상대를 다시 등록해도 한 명으로 남는다
        assert again["ok"], again
        rivals = client.service("rivals")["rivals"]
        assert [(r["rival_user_id"], r["display_name"]) for r in rivals] == [(b["id"], b["name"])], rivals
    finally:
        removed = client.service("remove_rival", id=b["id"])
    assert removed["ok"] and client.service("rivals")["rivals"] == []


def test_rival_rejections_self_and_unknown_name():
    uid_a = login(ACCT_A)
    remove_all_rivals()
    a = account_row(ACCT_A)
    assert a["id"] == uid_a
    me = client.service("add_rival", name=a["name"])
    assert me["ok"] is False and me["error"] == "self", me
    nobody = client.service("add_rival", name="없는닉네임_autotest_zzz")
    assert nobody["ok"] is False and nobody["error"] == "not_found", nobody
    assert client.service("rivals")["rivals"] == []


def test_rival_limit_is_five():
    login(ACCT_A)
    remove_all_rivals()
    five = [account_row(n) for n in (2, ACCT_B, ACCT_C, 6, 7)]
    sixth = account_row(1)
    try:
        for r in five:
            res = client.service("add_rival", name=r["name"])
            assert res["ok"], (r["name"], res)
        over = client.service("add_rival", name=sixth["name"])
        assert over["ok"] is False and over["error"] == "limit", over
        assert len(client.service("rivals")["rivals"]) == 5
    finally:
        remove_all_rivals()
    assert client.service("rivals")["rivals"] == []


# ── 클라이언트 리더보드 조회 ────────────────────────────────────────

def test_client_leaderboard_rows_names_and_rank():
    """게임의 LeaderboardService.get_leaderboard/get_my_rank 가 서버에 저장된 두 계정의 기록을 점수 내림차순·닉네임 포함으로 돌려준다."""
    uid_c = login(ACCT_C)
    submit(payload(CH_8K, mix(wow=8, great=6, good=3, oops=2, miss=1), played_at="2026-01-01T00:00:00Z"))   # EX 36
    uid_b = login(ACCT_B)
    submit(payload(CH_8K, mix(wow=20), played_at="2026-01-03T00:00:00Z"))                                    # EX 60 (만점)
    names = {uid_b: account_row(ACCT_B)["name"], uid_c: account_row(ACCT_C)["name"]}
    res = client.service("leaderboard", song_id=CH_8K[0], difficulty=CH_8K[1], platform=PLATFORM)
    assert res["load_failed"] is False
    rows = res["rows"]
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1)), "순위는 1부터 빠짐없이 이어져야 합니다"
    mine = [r for r in rows if r["user_id"] in names]
    assert [r["user_id"] for r in mine] == [uid_b, uid_c], "점수가 높은 B가 C보다 위여야 합니다"
    b_row, c_row = mine
    assert (b_row["ex_score"], b_row["ex_max"], b_row["grade"], b_row["failed"]) == (60, 60, "MAX", False), b_row
    assert (c_row["ex_score"], c_row["ex_max"], c_row["failed"]) == (36, 60, False), c_row
    assert b_row["display_name"] == names[uid_b] and c_row["display_name"] == names[uid_c]
    assert client.service("my_rank", song_id=CH_8K[0], difficulty=CH_8K[1], platform=PLATFORM)["rank"] == b_row["rank"]
    limited = client.service("leaderboard", song_id=CH_8K[0], difficulty=CH_8K[1], platform=PLATFORM, limit=1)["rows"]
    assert len(limited) == 1 and limited[0]["user_id"] == rows[0]["user_id"], "limit=1 이면 1위 한 줄만"


# ── 고스트 시퀀스 접근 권한 (본인 / 전일 1위 / 내가 등록한 라이벌만) ─────

def test_ghost_sequence_access_rules():
    """다른 사람의 판정 시퀀스는 그 곡의 1위이거나 내가 등록한 라이벌일 때만 읽힌다. 아니면 빈 결과."""
    login(ACCT_C)
    submit(payload(CH_8K, mix(wow=8, great=6, good=3, oops=2, miss=1), played_at="2026-01-01T00:00:00Z"))   # C: EX 36 (2위)
    uid_b = login(ACCT_B)
    submit(payload(CH_8K, mix(wow=20), played_at="2026-01-03T00:00:00Z"))                                    # B: EX 60 (1위)
    uid_c = account_row(ACCT_C)["id"]
    seq_args = dict(song_id=CH_8K[0], difficulty=CH_8K[1], platform=PLATFORM)

    login(ACCT_A)
    remove_all_rivals()
    try:
        assert client.service("sequence", user_id=uid_c, **seq_args)["has"] is False, "1위도 라이벌도 아닌 C의 시퀀스가 읽히면 안 됩니다"
        top = client.service("sequence", user_id=uid_b, **seq_args)
        assert top["has"] is True and top["length"] == CH_8K[2], f"전일 1위 B의 시퀀스는 읽혀야 합니다: {top}"
        assert client.service("add_rival", name=account_row(ACCT_C)["name"])["ok"]
        as_rival = client.service("sequence", user_id=uid_c, **seq_args)
        assert as_rival["has"] is True and as_rival["length"] == CH_8K[2], f"라이벌로 등록한 C의 시퀀스는 읽혀야 합니다: {as_rival}"
    finally:
        remove_all_rivals()
    assert client.service("sequence", user_id=uid_c, **seq_args)["has"] is False, "라이벌 해제 후에는 다시 막혀야 합니다"
    login(ACCT_C)
    own = client.service("sequence", user_id=uid_c, **seq_args)
    assert own["has"] is True, "본인 시퀀스는 항상 읽혀야 합니다"
