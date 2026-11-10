# -*- coding: utf-8 -*-
"""모듈 20 — 채보 불러오기 보조 함수(meta 만 읽기·곡 폴더 찾기·manifest·접근자) (Godot 헤드리스). 항목은 godot_unit/unit_chartloader.gd 가 만든다. 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("chartloader")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_chartloader(r):
    assert r["pass"], r["detail"]
