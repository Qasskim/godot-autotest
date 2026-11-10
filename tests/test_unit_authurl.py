# -*- coding: utf-8 -*-
"""모듈 24 — 로그인 연동 보조 함수(SupabaseHTTP 인증 주소·오류 판별) (Godot 헤드리스). 항목은 godot_unit/unit_authurl.gd 가 만든다. 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("authurl")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_authurl(r):
    assert r["pass"], r["detail"]
