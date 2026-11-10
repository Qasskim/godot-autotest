# -*- coding: utf-8 -*-
"""모듈 19 — 라이벌/전일 1위 고스트 진행 계산(RivalGhostSystem) (Godot 헤드리스). 항목은 godot_unit/unit_ghost.gd 가 만든다. 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("ghost")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_ghost(r):
    assert r["pass"], r["detail"]
