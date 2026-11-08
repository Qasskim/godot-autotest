# -*- coding: utf-8 -*-
"""서버 테스트 공용 도구 — 고정 테스트 계정 로그인(장부 기록·기록 비우기), 판정 시퀀스 만들기, submit_score 호출, 서버 DB 읽기 전용 조회.
test_server_score.py·test_server_social.py 가 같이 쓴다. 한 pytest 실행 안에서 계정마다 처음 로그인할 때 한 번만 서버 기록을 비운다."""
import client
import cleanup_server
import server_ledger

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
