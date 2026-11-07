# -*- coding: utf-8 -*-
"""모듈 5 — 서버 접속 차단 가드 (--no-server, Godot 헤드리스).

프레임을 실제로 돌려 오토로드 _ready가 실행된 상태에서도 서버 세션이 만들어지지 않고 조회·쓰기가 차단되는지 확인한다.
항목은 godot_unit/unit_offline.gd 가 만든다. 헤드리스 실행기는 항상 --no-server를 붙인다(godot_runner).
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("offline")

KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_offline(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
