# -*- coding: utf-8 -*-
"""모듈 11 — 스크롤 계산·화면 비례 레이아웃·도트 폰트 크기 (Godot 헤드리스, 기준 DESIGN.md §10·§1·§4·§13-2·§13-3).

NotePositionCalculator(누적 스크롤 테이블·노트 Y·원근 배율), ScreenLayout._rebuild(11가지 해상도 비례 계산, 비정상 크기 무시),
ScreenLayout.pixel_font_spec(설계 크기의 정수 배수 규칙)을 검증한다. 항목은 godot_unit/unit_scroll.gd 가 만든다. 게임 창·서버 없이 돈다.
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("scroll")

KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_scroll(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
