# -*- coding: utf-8 -*-
"""모듈 10 — 드래그 노트 처리 (Godot 헤드리스, 기준 DESIGN.md §6 드래그 노트 처리).

DragNoteVisual 을 곡 시계와 손가락 위치를 직접 움직여 검증한다: 궤적 보간, 정상 홀드, 궤적 이탈, 끝 앞 Oops 창,
헤드 미스와 구제, 재진입, 허용 폭 경계, 오토플레이·키보드. 항목은 godot_unit/unit_drag.gd 가 만든다. 게임 창·서버 없이 돈다.
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("drag")

KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_drag(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
