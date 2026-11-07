# -*- coding: utf-8 -*-
"""모듈 1 — 판정·점수·등급·게이지·콤보·마크 (Godot 헤드리스, 기준 DESIGN.md §5. §6은 게이지 20% 비중만 포함, 롱/드래그 처리는 미검증).

게임 창이나 TestServer 없이 돈다. 검사 항목은 godot_unit/unit_balance.gd 가 만들고,
여기서는 항목 하나를 pytest 케이스 하나로 바꿔 기존 엑셀 리포트에 같이 기록한다.
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("balance")

# 명세(DESIGN.md)와 코드가 다르다고 확인됐지만 어느 쪽이 맞는지 사용자 결정 전인 항목.
# 키: 케이스 이름 일부, 값: 사유. 결정이 나서 코드나 문서가 맞춰지면 이 목록에서 지운다.
KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_balance(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
