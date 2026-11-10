# -*- coding: utf-8 -*-
"""모듈 16 — 비주얼 테마(팔레트 .tres 3개) 데이터 (Godot 헤드리스, 기준 DESIGN §11·§13-3·§5). 항목은 godot_unit/unit_palette.gd 가 만든다.
테마 ID·키빔 모드·판정 이펙트 5등급·노트 색 순서·마크 8종·등급/게이지 색 조회·투명도을 확인한다(astral_ocean 의 30색은 test_data_palette.py). 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("palette")

# DESIGN §11 의 표는 Great·Good 이 "Wow와 동일 구조, 규모 축소"라고 하고 같은 절 본문은 "Wow/Great/Good이 동일 애니메이션의 크기 차이가 아니라 완전히 다른 연출(motion_type)"이라고 한다.
# 어느 쪽이 기준인지 사용자 결정 대기(2026-11-10). 지금 데이터는 세 테마 모두 Wow·Great·Good 중 연출 종류가 같은 등급이 있다.
KNOWN_ISSUES: dict = {"는 서로 다른 연출 종류": "DESIGN §11 표(규모만 축소)와 본문(완전히 다른 연출)이 서로 달라 기준 결정 대기 — 현재 데이터는 Wow·Great·Good 의 motion_type 이 겹침"}


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_palette(r):
    reason = next((v for k, v in KNOWN_ISSUES.items() if k in r["name"]), None)
    if reason is not None:
        if r["pass"]:
            pytest.fail(f"알려진 문제로 등록돼 있었는데 통과했습니다 — KNOWN_ISSUES에서 지우세요: {r['name']}")
        pytest.xfail(f"{reason} / {r['detail']}")
    assert r["pass"], r["detail"]
