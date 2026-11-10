# -*- coding: utf-8 -*-
"""모듈 18 — 오디오 버스 적용(AudioManager 음량·음소거·이퀄라이저·키음 음량) (Godot 헤드리스). 항목은 godot_unit/unit_audiobus.gd 가 만든다. 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("audiobus")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_audiobus(r):
    assert r["pass"], r["detail"]
