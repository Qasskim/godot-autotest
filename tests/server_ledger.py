# -*- coding: utf-8 -*-
"""서버에 만든 테스트 계정 장부 (2026-11-08, 사용자 확정 "장부 목록 방식").

게임을 서버 모드로 띄우거나 테스트 계정으로 로그인하면, 그 계정의 user_id를 만드는 즉시 장부 파일에 한 줄 적는다.
정리 루틴(cleanup_server.py)은 **장부에 적힌 계정의 데이터만** 지운다. 장부에 없는 것은 외부 플레이어 것일 수 있으니 절대 건드리지 않는다.

장부 줄 종류(JSON Lines):
- run_start : 서버 모드 게임을 띄우기 직전. 장부 밖 의심 계정을 찾는 시간 기준이 된다.
- account   : user_id, fixed(고정 테스트 계정=true: 계정은 남기고 기록만 지움 / 게임이 만든 익명 계정=false: 계정째 지움), label.
"""
import json
import os
import re
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.environ.get("AUTOTEST_LEDGER", os.path.join(REPO_ROOT, "server_ledger.jsonl"))

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def is_uuid(value: str) -> bool:
    return bool(_UUID.match(value or ""))


def append(kind: str, **fields) -> dict:
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "kind": kind, **fields}
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return row


def rows() -> list:
    if not os.path.exists(LEDGER_PATH):
        return []
    out = []
    with open(LEDGER_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def accounts() -> dict:
    """user_id -> {"fixed": bool, "label": str}. 한 번이라도 fixed로 적힌 계정은 계속 fixed(계정째 지우지 않기 위해)."""
    result: dict = {}
    for r in rows():
        if r.get("kind") == "cleaned":      # 정리(--apply)가 끝난 뒤: 계정째 지운 익명 계정은 장부에서 뺀다 (고정 계정은 남는다)
            result = {u: v for u, v in result.items() if v["fixed"]}
            continue
        if r.get("kind") != "account" or not is_uuid(r.get("user_id", "")):
            continue
        prev = result.get(r["user_id"])
        result[r["user_id"]] = {"fixed": bool(r.get("fixed")) or bool(prev and prev["fixed"]), "label": r.get("label", "")}
    return result


def first_run_start() -> str:
    """마지막 정리(cleaned) 이후 가장 이른 run_start 시각(없으면 빈 문자열). 장부 밖 의심 계정 조회의 기준."""
    since = ""
    for r in rows():
        if r.get("kind") == "cleaned":
            since = ""
        elif r.get("kind") == "run_start" and not since:
            since = r["ts"]
    return since


def register(user_id: str, fixed: bool, label: str) -> None:
    """이미 같은 값으로 적혀 있으면 다시 적지 않는다."""
    if not is_uuid(user_id):
        raise ValueError(f"user_id 형식이 아닙니다: {user_id!r}")
    known = accounts().get(user_id)
    if known and (known["fixed"] or not fixed):
        return
    append("account", user_id=user_id, fixed=fixed, label=label)
