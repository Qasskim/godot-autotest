# -*- coding: utf-8 -*-
"""모듈 13 — 로컬 기록 저장 (Godot 헤드리스).

베스트 갱신 규칙(첫 기록은 음수여도 저장, 같거나 낮으면 거부, 높으면 시퀀스·레인믹스 로그까지 교체), 곡·난이도·플랫폼·계정별 분리,
최근 플레이, 전체 삭제, 서버 없는 상태의 RecordService, song_id 규칙. 항목은 godot_unit/unit_records.gd 가 만든다.
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("records")

KNOWN_ISSUES: dict = {}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_records(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
