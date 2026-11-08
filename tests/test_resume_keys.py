# -*- coding: utf-8 -*-
"""풀 시나리오 이어하기 키 — 채보 파일이 바뀌면 키가 달라져서 다시 돌아야 한다 (2026-11-08, 사용자 지시 "새로 채보 바뀐 것들 확인").

test_full_scenario._chart_fingerprint 의 규칙만 본다(게임·서버 없이). 이어하기 전체 동작은 run_all.py --resume 으로 풀 시나리오를 두 번 돌려 확인한다.
"""
import pytest

import godot_runner
import test_full_scenario as scenario

pytestmark = pytest.mark.no_server


def make_chart(tmp_path, monkeypatch, content: bytes) -> str:
    monkeypatch.setattr(scenario, "GAME_PROJECT", str(tmp_path))
    (tmp_path / "charts").mkdir(exist_ok=True)
    (tmp_path / "charts" / "a.rgds").write_bytes(content)
    return "res://charts/a.rgds"


def test_same_content_gives_same_fingerprint(tmp_path, monkeypatch):
    p = make_chart(tmp_path, monkeypatch, b"chart-v1")
    assert scenario._chart_fingerprint(p) == scenario._chart_fingerprint(p)


def test_changed_content_changes_fingerprint(tmp_path, monkeypatch):
    p = make_chart(tmp_path, monkeypatch, b"chart-v1")
    before = scenario._chart_fingerprint(p)
    make_chart(tmp_path, monkeypatch, b"chart-v2")
    assert scenario._chart_fingerprint(p) != before


def test_unreadable_or_external_paths_are_never_skipped(tmp_path, monkeypatch):
    """읽을 수 없거나 res:// 가 아닌 채보는 매번 다른 값을 돌려줘서 이어하기에서 건너뛰지 않는다(통과 기록과 절대 일치하지 않음)."""
    monkeypatch.setattr(scenario, "GAME_PROJECT", str(tmp_path))
    import time
    a = scenario._chart_fingerprint("res://charts/missing.rgds")
    time.sleep(0.01)
    assert a != scenario._chart_fingerprint("res://charts/missing.rgds") and a.startswith("unreadable-")
    ext = scenario._chart_fingerprint("user://charts/x.rgds")
    time.sleep(0.01)
    assert ext != scenario._chart_fingerprint("user://charts/x.rgds") and ext.startswith("external-")
