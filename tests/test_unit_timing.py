# -*- coding: utf-8 -*-
"""모듈 3 — 박자와 타이밍 (Godot 헤드리스, 기준 DESIGN.md §8 "시퀀서 박자/스냅"·§10).

TimeSignature(meta.meter), ChartTiming(timing_events → 마디 시작 ms·BPM 테이블, 조회)를 검증한다.
게임 창이나 TestServer 없이 돈다. 검사 항목은 godot_unit/unit_timing.gd 가 만든다.
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("timing")

# 명세(DESIGN.md)와 코드가 다른데 어느 쪽이 맞는지 사용자 결정 전인 항목. 키: 케이스 이름 일부, 값: 사유.
KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_timing(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
