# -*- coding: utf-8 -*-
"""모듈 25 — 공용 팝업 동작 (Godot 헤드리스): ErrorPopup·ConfirmPopup·ProtoNoticePopup 의 글자·버튼·콜백·물리 뒤로가기·동의 저장. 항목은 godot_unit/unit_popups.gd 가 만든다. 서버에 접속하지 않는다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("popups")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_popups(r):
    assert r["pass"], r["detail"]
