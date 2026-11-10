# -*- coding: utf-8 -*-
"""모듈 22 — 게임 설정 저장·적용(GameSettings) (Godot 헤드리스). 항목은 godot_unit/unit_settings.gd 가 만든다. 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("settings")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_settings(r):
    assert r["pass"], r["detail"]
