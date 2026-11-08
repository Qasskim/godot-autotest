# -*- coding: utf-8 -*-
"""서버 검증 — 기록 저장·서버 점수 재계산(submit_score)·리더보드 순서 데이터·닉네임 (기준 DESIGN.md §5, SUPABASE_ADAPTER_SPEC.md).

개발 서버(Supabase)에 그대로 접속한다(2026-11-08, 사용자 확정). 게임은 고정 테스트 계정(debug_test_account{N}.local.json)으로
로그인하며, 계정 비밀번호는 게임이 직접 읽는다(이 코드는 비밀번호를 다루지 않는다). 계정 ID는 로그인 즉시 장부에 적는다.
저장 결과는 서버 DB를 읽기 전용(`supabase db query --read-only`)으로 직접 읽어 확인한다.

쓰는 채보는 서버에 등록된 시험용 채보(notetest_*)라서 일반 플레이어의 리더보드에 섞이지 않는다.
시험이 끝나면 `python tests/cleanup_server.py` 로 장부에 적힌 계정의 기록 행을 지운다(기본은 목록만, 삭제는 --apply).
"""
import json
import urllib.parse

import pytest

import client
import cleanup_server
import server_ledger

pytestmark = pytest.mark.server

PLATFORM = "android"
# 서버 charts 테이블에 등록돼 있고 lanemix 구간이 없는 시험 채보 (song_id, difficulty, total_notes) — 2026-11-08 서버 조회 기준
CH_4K = ("notetest_chart_4k_ez", "EZ", 10)
CH_5K = ("notetest_chart_5k_nm", "NM", 33)
CH_6K = ("notetest_chart_6k_hd", "HD", 40)
CH_8K = ("notetest_chart_8k_ex", "EX", 20)

ACCT_A, ACCT_B, ACCT_C = 3, 4, 5      # 고정 테스트 계정 test3@·test4@·test5@ (test@ 는 서명 권한을 겸했던 계정이라 쓰지 않는다)
_cleared: set = set()                 # 이 실행에서 이미 기록을 비운 계정


def login(account: int) -> str:
    """고정 테스트 계정으로 로그인하고 장부에 적는다. 이 실행에서 처음이면 그 계정의 서버 기록을 비워 깨끗한 상태에서 시작한다."""
    s = client.debug_login(account)
    uid = s["user_id"]
    assert server_ledger.is_uuid(uid) and s["is_anonymous"] is False, f"실계정이 아닙니다: {s}"
    server_ledger.register(uid, fixed=True, label=f"test{account}")
    if account not in _cleared:
        assert client.clear_server_records(), f"테스트 계정 {account}의 서버 기록을 비우지 못했습니다"
        _cleared.add(account)
    return uid


def seq(judgments: list) -> list:
    return [{"note_index": i, "judgment": j, "delta_ms": None if j == "Miss" else 0} for i, j in enumerate(judgments)]


def mix(wow=0, great=0, good=0, oops=0, miss=0) -> list:
    return ["Wow"] * wow + ["Great"] * great + ["Good"] * good + ["Oops"] * oops + ["Miss"] * miss


def payload(chart, judgments, **extra) -> dict:
    song, diff, _ = chart
    p = {"song_id": song, "difficulty": diff, "platform": PLATFORM, "sequence": seq(judgments),
         "lanemix_log": [], "max_combo": 0, "marks": [], "played_at": "2026-01-01T00:00:00Z", "ended_early": False}
    p.update(extra)
    return p


def submit(p: dict) -> dict:
    return client.debug_submit_score(p)


def db(sql: str) -> list:
    return cleanup_server._query(sql)


def saved_record(uid: str, chart) -> dict:
    song, diff, _ = chart
    rows = db(f"select ex_score, record from public.records where user_id='{uid}' and song_id='{song}' and difficulty='{diff}' and platform='{PLATFORM}'")
    return rows[0] if rows else {}


def saved_sequence_len(uid: str, chart) -> int:
    song, diff, _ = chart
    rows = db(f"select jsonb_array_length(sequence) as n from public.sequences where user_id='{uid}' and song_id='{song}' and difficulty='{diff}' and platform='{PLATFORM}'")
    return rows[0]["n"] if rows else 0


# ── 로그인 ──────────────────────────────────────────────────────────

def test_fixed_account_login_is_real_and_in_ledger():
    uid = login(ACCT_A)
    assert uid in server_ledger.accounts() and server_ledger.accounts()[uid]["fixed"] is True


# ── 서버 점수 재계산 ────────────────────────────────────────────────

def test_server_recomputes_score_and_ignores_client_values():
    """클라이언트가 점수·등급을 속여 보내도 서버는 판정 시퀀스로 EX를 다시 계산해 저장한다 (EX 가중치 Wow 3·Great 2·그 외 0)."""
    uid = login(ACCT_A)
    js = mix(wow=4, great=3, good=1, oops=1, miss=1)              # 10개: EX = 4×3 + 3×2 = 18, 만점 30
    p = payload(CH_4K, js, max_combo=7, marks=["clear"], ex_score=99999, grade="MAX", ex_rate=1.0)
    r = submit(p)
    assert r["ok"] and r["response"]["ok"] and r["response"]["is_best"] is True, r
    rec = r["response"]["record"]
    assert (rec["ex_score"], rec["ex_max"], rec["grade"]) == (18, 30, "D"), rec          # 60% → D (50 이상 70 미만)
    assert abs(rec["ex_rate"] - 0.6) < 1e-9 and rec["max_combo"] == 7 and rec["marks"] == ["clear"]
    assert rec["judgment_counts"] == {"Wow": 4, "Great": 3, "Good": 1, "Oops": 1, "Miss": 1}
    row = saved_record(uid, CH_4K)
    assert row["ex_score"] == 18 and row["record"]["grade"] == "D" and row["record"]["ex_max"] == 30, row
    assert saved_sequence_len(uid, CH_4K) == 10


def test_best_record_rules_keep_only_higher_scores():
    """더 낮거나 같은 점수는 저장하지 않고(is_best false), 더 높은 점수만 덮어쓴다. 시퀀스도 같이 바뀐다."""
    uid = login(ACCT_A)
    r1 = submit(payload(CH_6K, mix(wow=20, great=10, good=10)))                  # EX 80 / 120
    assert r1["response"]["is_best"] is True and r1["response"]["record"]["ex_score"] == 80, r1
    r2 = submit(payload(CH_6K, mix(miss=40)))                                    # EX 0
    r3 = submit(payload(CH_6K, mix(wow=20, great=10, good=10)))                  # 같은 점수
    assert r2["response"] == {"ok": True, "is_best": False} and r3["response"] == {"ok": True, "is_best": False}, (r2, r3)
    assert saved_record(uid, CH_6K)["ex_score"] == 80
    r4 = submit(payload(CH_6K, mix(wow=40), played_at="2026-02-02T00:00:00Z"))   # EX 120 = 만점
    assert r4["response"]["is_best"] is True and r4["response"]["record"]["grade"] == "MAX", r4
    row = saved_record(uid, CH_6K)
    assert row["ex_score"] == 120 and row["record"]["played_at"] == "2026-02-02T00:00:00Z"
    assert saved_sequence_len(uid, CH_6K) == 40


def test_unknown_judgment_names_count_as_judged_but_add_no_score():
    """알 수 없는 판정 이름은 점수에 넣지 않고 판정 개수에도 세지 않는다(방어적 처리, gameBalance.ts). 시퀀스 길이는 노트 수 검사에 쓰인다."""
    uid = login(ACCT_A)
    r = submit(payload(CH_8K, ["Wow"] * 19 + ["Bogus"]))
    assert r["response"]["is_best"] is True, r
    rec = r["response"]["record"]
    assert rec["ex_score"] == 57 and rec["judgment_counts"]["Wow"] == 19 and sum(rec["judgment_counts"].values()) == 19, rec
    assert saved_record(uid, CH_8K)["ex_score"] == 57


# ── 거부되는 요청 ───────────────────────────────────────────────────

def test_note_count_mismatch_is_rejected_and_nothing_saved():
    uid = login(ACCT_A)
    for n in (CH_5K[2] - 1, CH_5K[2] + 1):
        r = submit(payload(CH_5K, ["Wow"] * n))
        assert r["ok"] is False and r["response"]["error"] == "note_count_mismatch", r
        assert r["response"]["expected"] == CH_5K[2] and r["response"]["got"] == n
    assert saved_record(uid, CH_5K) == {}


def test_unregistered_chart_is_rejected():
    login(ACCT_A)
    r = submit({"song_id": "autotest_chart_that_does_not_exist", "difficulty": "EZ", "platform": PLATFORM, "sequence": seq(["Wow"]), "lanemix_log": []})
    assert r["ok"] is False and r["response"]["error"] == "chart_not_registered", r


@pytest.mark.parametrize("missing", ["song_id", "difficulty", "platform"])
def test_missing_required_field_is_rejected(missing):
    login(ACCT_A)
    p = payload(CH_4K, mix(wow=10))
    del p[missing]
    r = submit(p)
    assert r["ok"] is False and "필수" in str(r["response"]), r


def test_ended_early_accepts_short_sequence_and_forces_failed_mark():
    """폭사(ended_early)는 판정이 1개 이상 노트 수 이하일 때만 받고, 클리어 계열 마크를 빼고 failed를 붙인다. 노트 수보다 많거나 0개면 거부."""
    uid = login(ACCT_A)
    marks = ["clear", "perfect", "allgood", "allcombo", "x_test_mark"]
    r = submit(payload(CH_5K, mix(wow=12), ended_early=True, marks=marks))
    assert r["response"]["is_best"] is True, r
    assert r["response"]["record"]["marks"] == ["x_test_mark", "failed"], r
    assert saved_record(uid, CH_5K)["record"]["marks"] == ["x_test_mark", "failed"]
    over = submit(payload(CH_5K, mix(wow=CH_5K[2] + 1), ended_early=True))
    zero = submit(payload(CH_5K, [], ended_early=True))
    assert over["response"]["error"] == "note_count_mismatch" and zero["response"]["error"] == "note_count_mismatch", (over, zero)


# ── 리더보드 순서 데이터 ────────────────────────────────────────────

def test_leaderboard_order_is_score_desc_then_earlier_played_at():
    """리더보드 조회(LeaderboardService.get_leaderboard)와 같은 정렬 — 점수 내림차순, 동점이면 먼저 달성한 기록이 위. 두 계정의 저장 결과를 같은 쿼리로 읽는다.
    (게임 화면에 보이는 모양은 사람이 확인한다. 여기서는 서버에 저장된 데이터가 그 정렬 규칙대로 나오는지만 본다.)"""
    uid_b = login(ACCT_B)
    submit(payload(CH_8K, mix(wow=8, great=6, good=3, oops=2, miss=1), played_at="2026-01-02T00:00:00Z"))     # EX 36, 늦게 달성
    uid_c = login(ACCT_C)
    submit(payload(CH_8K, mix(wow=8, great=6, good=3, oops=2, miss=1), played_at="2026-01-01T00:00:00Z"))     # EX 36, 먼저 달성
    order_sql = (f"select user_id from public.records where song_id='{CH_8K[0]}' and difficulty='{CH_8K[1]}' and platform='{PLATFORM}' "
                 f"and user_id in ('{uid_b}','{uid_c}') order by ex_score desc, record->>'played_at' asc")
    assert [r["user_id"] for r in db(order_sql)] == [uid_c, uid_b], "동점이면 먼저 달성한 C가 위여야 합니다"
    login(ACCT_B)
    r = submit(payload(CH_8K, mix(wow=20), played_at="2026-01-03T00:00:00Z"))                                  # B가 만점으로 갱신
    assert r["response"]["is_best"] is True
    assert [r["user_id"] for r in db(order_sql)] == [uid_b, uid_c], "점수가 높은 B가 위여야 합니다"


# ── 닉네임 ──────────────────────────────────────────────────────────

def _nick(uid: str) -> str:
    rows = db(f"select display_name from public.users where user_id='{uid}'")
    return rows[0]["display_name"] if rows else ""


def _set_nick(name: str) -> dict:
    client._req("POST", f"/debug_set_nickname?name={urllib.parse.quote(name)}")
    import time
    for _ in range(60):
        st = client._req("GET", "/debug_set_nickname")
        if st.get("status") in ("success", "error"):
            return json.loads(st["result"])
        time.sleep(0.3)
    raise AssertionError("닉네임 설정 응답이 오지 않았습니다")


def test_nickname_same_name_is_accepted_and_taken_name_is_refused():
    """자기 닉네임을 그대로 다시 설정하면 통과(변경 아님). 다른 계정이 쓰는 닉네임은 거부(중복 또는 30일 제한)되고 내 닉네임은 그대로다."""
    uid_a = login(ACCT_A)
    uid_b = login(ACCT_B)
    name_a, name_b = _nick(uid_a), _nick(uid_b)
    if not name_a or not name_b:
        pytest.skip("테스트 계정 3·4에 서버 닉네임이 없습니다 — 닉네임 검증 불가")
    login(ACCT_A)
    same = _set_nick(name_a)
    assert same["ok"] is True and same["display_name"] == name_a, same
    taken = _set_nick(name_b)
    assert taken["ok"] is False and taken["error"] in ("duplicate", "cooldown"), taken
    assert _nick(uid_a) == name_a, "거부됐는데 닉네임이 바뀌었습니다"
