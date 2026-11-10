# -*- coding: utf-8 -*-
"""모듈 16 — 비주얼 테마(팔레트 .tres 3개) 데이터 (Godot 헤드리스, 기준 DESIGN §11·§13-3·§5). 항목은 godot_unit/unit_palette.gd 가 만든다.
테마 ID·키빔 모드·판정 이펙트 5등급·노트 색 순서·마크 8종·등급/게이지 색 조회·투명도을 확인한다(astral_ocean 의 30색은 test_data_palette.py). 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("palette")

KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_palette(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
