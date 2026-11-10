# -*- coding: utf-8 -*-
"""슬라이드 노트 (Godot 헤드리스, 기준 DESIGN §7) — 장면·방향 값·홀드형 아님. 항목은 godot_unit/unit_slide.gd 가 만든다.
슬라이드의 방향은 모양에만 쓰이고 판정에는 쓰이지 않는다(2026-11-10 코드 확인) — DESIGN '방향 슬라이드'와의 차이는 사용자 결정 대기라 여기서는 현재 구현을 고정만 한다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("slide")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_slide(r):
    assert r["pass"], r["detail"]
