# -*- coding: utf-8 -*-
"""모듈 12(게임 쪽) — 키음 음량·pan 공식 (Godot 헤드리스, 기준 DESIGN.md §8). 시퀀서(C#)와의 비교는 test_cross_formula.py."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("audio")

KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_audio(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
