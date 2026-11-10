# -*- coding: utf-8 -*-
"""모듈 15 — 곡 패키지(.rgz) 풀기·병합·공식 서명 잠금 (Godot 헤드리스, 기준 ChartLoader.ensure_rgz_extracted 설명·docs/phase2/PACKAGE_SIGNING_SPEC.md).
항목은 godot_unit/unit_package.gd 가 만든다. 경로 조작 거부·song_uid 폴더·병합 규칙·서명 잠금과 거부 격리를 확인한다. 서버에 접속하지 않는다(공개키는 게임에 내장)."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("package")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_package(r):
    assert r["pass"], r["detail"]
