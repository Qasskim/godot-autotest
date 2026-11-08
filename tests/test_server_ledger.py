# -*- coding: utf-8 -*-
"""서버 테스트 계정 장부와 정리 루틴의 규칙 (서버·게임 없이 도는 순수 파이썬 검사).

정리 루틴이 외부 플레이어 데이터를 지우지 않도록 하는 장치이므로: 장부에 적힌 것만 대상이 되는지, 고정 계정이 계정째 지워지지 않는지,
깨진 장부 값이 SQL 에 들어가지 못하는지를 확인한다. 실제 서버에 보내는 쓰기는 하지 않는다.
"""
import pytest
import cleanup_server
import server_ledger as L

pytestmark = pytest.mark.no_server

A = "aaaaaaaa-0000-4000-8000-000000000001"
B = "bbbbbbbb-0000-4000-8000-000000000002"
C = "cccccccc-0000-4000-8000-000000000003"


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))


def test_empty_ledger_has_no_accounts():
    assert L.accounts() == {} and L.first_run_start() == ""


def test_register_records_account_once():
    L.register(A, fixed=False, label="launch")
    L.register(A, fixed=False, label="launch")
    assert len(L.rows()) == 1 and L.accounts()[A] == {"fixed": False, "label": "launch"}


def test_fixed_flag_is_sticky():
    """한 번 고정 계정으로 적히면 나중에 익명으로 다시 적혀도 계속 고정이다(계정째 지우지 않기 위해)."""
    L.register(A, fixed=True, label="test2")
    L.register(A, fixed=False, label="launch")
    assert L.accounts()[A]["fixed"] is True


def test_cleaned_drops_anonymous_but_keeps_fixed():
    L.register(A, fixed=False, label="launch")
    L.register(B, fixed=True, label="test2")
    L.append("cleaned")
    assert list(L.accounts()) == [B]


def test_first_run_start_is_after_last_cleaned():
    L.append("run_start")
    first = L.first_run_start()
    assert first
    L.append("cleaned")
    assert L.first_run_start() == ""
    L.append("run_start")
    assert L.first_run_start() != ""


@pytest.mark.parametrize("bad", ["", "not-a-uuid", "x' or 1=1 --", A + "'; drop table records; --", A.upper()])
def test_non_uuid_is_rejected(bad):
    with pytest.raises(ValueError):
        L.register(bad, fixed=False, label="x")
    with pytest.raises(AssertionError):
        cleanup_server._arr([bad])


def test_delete_sql_touches_only_ledger_ids():
    sql = cleanup_server.delete_sql([A], [B])
    assert A in sql and B in sql and C not in sql
    low = sql.lower()
    assert low.count("delete from") == 5                                   # 행 4종 + 익명 계정째 1개, 그 밖의 삭제문 없음
    assert "delete from auth.users where id = any(array['" + A + "']" in low
    for table in ("records", "sequences", "rivals", "rival_notices"):
        assert f"delete from public.{table} where user_id = any(array['{B}']" in low   # 행 삭제는 고정 계정 쪽에만
    assert "truncate" not in low and "drop " not in low


def test_fixed_accounts_are_never_deleted_whole():
    """auth.users 삭제문의 대상 배열에는 고정 계정이 들어가지 않는다(서명 권한·로그인 보존)."""
    sql = cleanup_server.delete_sql([A], [B]).lower()
    users_clause = sql.split("delete from auth.users")[1]
    assert B not in users_clause


def test_counts_and_suspects_sql_are_read_only():
    for sql in (cleanup_server.counts_sql([A], [B]), cleanup_server.suspects_sql([A, B], "2026-11-08T00:00:00+0900")):
        low = sql.lower()
        assert low.lstrip().startswith("select") and "delete from" not in low and "update " not in low and "insert " not in low
