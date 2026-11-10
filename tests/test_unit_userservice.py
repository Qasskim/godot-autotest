# -*- coding: utf-8 -*-
"""모듈 26 — 유저 프로필·닉네임 (Godot 헤드리스, 기준 docs/phase2/USER_SYSTEM.md §4-1): 표시폭·허용 글자·게스트 로컬 저장·프로필 복원·게스트 로그아웃/탈퇴. 항목은 godot_unit/unit_userservice.gd 가 만든다. 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("userservice")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_userservice(r):
    assert r["pass"], r["detail"]
