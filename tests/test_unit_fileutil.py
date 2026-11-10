# -*- coding: utf-8 -*-
"""모듈 17 — 원자적 파일 저장(FileUtil.write_atomic) (Godot 헤드리스). 항목은 godot_unit/unit_fileutil.gd 가 만든다. 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("fileutil")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_fileutil(r):
    assert r["pass"], r["detail"]
