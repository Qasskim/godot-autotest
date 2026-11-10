# -*- coding: utf-8 -*-
"""모듈 14 — 오프라인 업로드 큐 (Godot 헤드리스, 기준 docs/phase2/SUPABASE_ADAPTER_SPEC.md). 항목은 godot_unit/unit_upload_queue.gd 가 만든다.
서버에 접속하지 않는다(--no-server): 보내기 함수를 시험용으로 바꿔 응답 종류(통신 실패·영구 실패·성공)별로 큐에 남는지 빠지는지 본다."""
import pytest
from godot_runner import run_unit_module

pytestmark = pytest.mark.no_server

_RESULTS = run_unit_module("upload_queue")


@pytest.mark.parametrize("r", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_unit_upload_queue(r):
    assert r["pass"], r["detail"]
