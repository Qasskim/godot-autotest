# -*- coding: utf-8 -*-
"""모듈 8 — 공식 채보 서명 검증 (Godot 헤드리스, 기준 docs/phase2/PACKAGE_SIGNING_SPEC.md).

게임이 쓰는 검증 함수(ChartLoader._verify_signature)로 수록 곡의 manifest.json·채보 서명이 현재 파일과 맞는지 확인한다.
항목은 godot_unit/unit_signing.gd 가 만든다. 읽기 전용이며 서버에 접속하지 않는다(공개키는 게임에 내장).
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("signing")

KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_signing(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
