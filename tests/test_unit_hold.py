# -*- coding: utf-8 -*-
"""모듈 9 — 롱노트 처리 (Godot 헤드리스, 기준 DESIGN.md §6 롱노트 처리).

LongNoteVisual 을 곡 시계와 입력을 직접 움직여 검증한다: 정상 홀드, 끝 앞 창 밖 이탈, 끝 앞 Oops 창 안에서 뗌(경계 포함),
헤드 미스와 구제, 이탈 뒤 재진입, 오토플레이·키보드. 항목은 godot_unit/unit_hold.gd 가 만든다. 게임 창·서버 없이 돈다.
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("hold")

# 명세(DESIGN.md)와 코드가 다른데 어느 쪽이 맞는지 사용자 결정 전인 항목. 키: 케이스 이름 일부, 값: 사유.
KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_hold(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
