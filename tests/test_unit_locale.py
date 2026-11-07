# -*- coding: utf-8 -*-
"""모듈 7(Godot 쪽) — 임포트된 번역이 CSV와 같은지, Locale 함수(t/tf/has/t_or) 동작 (Godot 헤드리스).
항목은 godot_unit/unit_locale.gd 가 만든다. CSV 자체의 형식·키 사용 검증은 test_data_locale.py.
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("locale")

KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_locale(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
