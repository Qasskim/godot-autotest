# -*- coding: utf-8 -*-
"""모듈 4 — 레인믹스 상태·진입 안내·노트 랜덤 (Godot 헤드리스, 기준 DESIGN.md §9·§7).

LaneMixState(섹션·키모드 랜덤/슈퍼랜덤·구간 경계·활성화), LaneMixEntry(안내 시작·수락·미리보기),
NoteRandomizer(RANDOM/S-RANDOM)를 검증한다. 게임 창이나 TestServer 없이 돈다. 항목은 godot_unit/unit_lanemix.gd 가 만든다.
"""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("lanemix")

# 명세(DESIGN.md)와 코드가 다른데 어느 쪽이 맞는지 사용자 결정 전인 항목. 키: 케이스 이름 일부, 값: 사유.
KNOWN_ISSUES: dict = {}      # 슈퍼랜덤 풀 1개 결함은 2026-11-10 수정(LaneMixState._resolve_super_sequence)으로 목록에서 뺐다


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_lanemix(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
